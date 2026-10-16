"""Ejecuta preguntas System One y conserva la respuesta original de Decision-1."""
import argparse
import errno
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from http.client import HTTPException
import json
import math
import os
from pathlib import Path
import shutil
import socket
import ssl
import sys
import tomllib
import uuid
from typing import Any, Literal, TypedDict
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener
from network_diagnostics import NetworkLog, diagnose_network
from provenance import verify as verify_provenance


class DecisionRequest(TypedDict):
    model: str
    state: str | dict[str, Any]
    questions: dict[str, dict[str, Any]]


class DecisionResponse(TypedDict, total=False):
    model: str
    answers: dict[str, dict[str, Any]]
    usage: dict[str, Any]


@dataclass(frozen=True)
class ExecutorConfig:
    endpoint: str
    deployment: str
    credential_env: str
    auth: Literal['api_key', 'bearer_token']
    timeout_seconds: int
    max_response_bytes: int
    ready: bool
    verify_tls: bool = True


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('El endpoint devolvió una redirección; verifica la URL configurada.')


class TransportError(ValueError):
    def __init__(self, message: str, diagnostic: dict[str, Any]):
        super().__init__(message)
        self.diagnostic = diagnostic


def connection_error(error: Exception, endpoint: str) -> TransportError:
    reason = error.reason if isinstance(error, URLError) else error
    diagnostic: dict[str, Any] = {
        'host': urlsplit(endpoint).hostname,
        'exception_type': type(error).__name__,
        'cause_type': type(reason).__name__,
    }
    if isinstance(reason, ssl.SSLCertVerificationError):
        code, explanation = 'TLS_CERTIFICATE_VERIFY_FAILED', 'No se pudo verificar el certificado TLS del endpoint o del proxy.'
        diagnostic['verify_code'] = reason.verify_code
    elif isinstance(reason, ssl.SSLError):
        code, explanation = 'TLS_ERROR', 'Falló la negociación TLS.'
        if isinstance(reason.reason, str):
            diagnostic['tls_reason'] = reason.reason if reason.reason.replace('_', '').isalnum() else 'SSL_ERROR'
    elif isinstance(reason, socket.gaierror):
        code, explanation = 'DNS_ERROR', 'No se pudo resolver el nombre del endpoint o del proxy.'
    elif isinstance(reason, TimeoutError) or isinstance(reason, str) and 'timed out' in reason.lower():
        code, explanation = 'TIMEOUT', 'Se agotó el tiempo de conexión o de lectura.'
    elif isinstance(reason, PermissionError):
        code, explanation = 'ACCESS_DENIED', 'El entorno o el sistema bloqueó el acceso de red.'
    elif isinstance(reason, OSError) and 'tunnel connection failed' in str(reason).lower():
        code, explanation = 'PROXY_ERROR', 'El proxy no pudo establecer el túnel HTTPS.'
    elif isinstance(reason, HTTPException):
        code, explanation = 'HTTP_PROTOCOL_ERROR', 'La conexión terminó con un error del protocolo HTTP.'
    else:
        code, explanation = 'CONNECTION_ERROR', 'No se pudo establecer o mantener la conexión con el servicio.'
    if isinstance(reason, OSError):
        if isinstance(reason.errno, int):
            diagnostic['errno'] = reason.errno
            diagnostic['errno_name'] = errno.errorcode.get(reason.errno, 'OS_ERROR')
        if isinstance(getattr(reason, 'winerror', None), int):
            diagnostic['winerror'] = reason.winerror
    diagnostic['code'] = code
    return TransportError(f'{code}: {explanation} No se modificaron los resultados del caso.', diagnostic)


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def read_user_credential(name: str) -> str:
    if os.name != 'nt':
        return ''
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment') as key:
            value, kind = winreg.QueryValueEx(key, name)
        if kind in (winreg.REG_SZ, winreg.REG_EXPAND_SZ) and isinstance(value, str):
            return value.strip()
    except OSError:
        pass
    return ''


def resolve_credential(name: str) -> tuple[str, str]:
    value = os.environ.get(name, '').strip()
    if value:
        return value, 'process_environment'
    value = read_user_credential(name)
    return (value, 'user_environment') if value else ('', 'missing')


def strict_json(text: str) -> Any:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('JSON con claves duplicadas.')
            result[key] = value
        return result
    def constant(value):
        raise ValueError('JSON con un número no finito.')
    def finite_float(value):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError('JSON con un número no finito.')
        return number
    return json.loads(text, object_pairs_hook=pairs, parse_constant=constant, parse_float=finite_float)


def read_config(kit_home: Path, config_file: str | Path | None = None) -> ExecutorConfig:
    settings = tomllib.loads((kit_home / 'decision/settings.toml').read_text(encoding='utf-8-sig')) if config_file is None else {'execution': {'mode': 'systemone', 'ready': True}}
    execution = settings['execution']
    if execution.get('mode') != 'systemone':
        raise ValueError('Configura execution.mode = "systemone" en settings.toml.')
    relative = Path(execution.get('config', 'decision/executor.toml'))
    config_path = Path(config_file).expanduser().resolve(strict=True) if config_file else (kit_home / relative).resolve()
    if config_file is None and (relative.is_absolute() or not config_path.is_relative_to(kit_home.resolve())):
        raise ValueError('execution.config debe ser una ruta relativa dentro de la instalación del kit.')
    data = tomllib.loads(config_path.read_text(encoding='utf-8-sig'))
    for field in ('endpoint', 'deployment', 'credential_env'):
        if not nonempty(data.get(field)):
            raise ValueError(f'Falta configurar {field} en executor.toml.')
    endpoint = urlsplit(data['endpoint'])
    if endpoint.scheme != 'https' or not endpoint.hostname or endpoint.username or endpoint.password or endpoint.query or endpoint.fragment:
        raise ValueError('El endpoint debe ser una URL HTTPS sin credenciales, query ni fragmento.')
    if not endpoint.path.rstrip('/').endswith('/systemone'):
        raise ValueError('Usa el endpoint completo terminado en /systemone.')
    auth = data.get('auth', 'api_key')
    if auth not in ('api_key', 'bearer_token'):
        raise ValueError('auth debe ser api_key o bearer_token.')
    timeout = data.get('timeout_seconds', 60)
    limit = data.get('max_response_bytes', 5_000_000)
    if type(timeout) is not int or timeout <= 0 or type(limit) is not int or limit <= 0:
        raise ValueError('Los límites de tiempo y tamaño deben ser enteros positivos.')
    if type(execution.get('ready')) is not bool:
        raise ValueError('execution.ready debe ser booleano.')
    verify_tls = data.get('verify_tls', True)
    if type(verify_tls) is not bool:
        raise ValueError('verify_tls debe ser booleano.')
    return ExecutorConfig(data['endpoint'], data['deployment'], data['credential_env'], auth, timeout, limit, execution['ready'], verify_tls)


def validate_input(data: Any, deployment: str) -> DecisionRequest:
    if not isinstance(data, dict) or set(data) != {'state', 'questions'}:
        raise ValueError('input.json debe contener únicamente state y questions.')
    state = data['state']
    if not (nonempty(state) or isinstance(state, dict) and bool(state)):
        raise ValueError('state debe ser texto u objeto JSON no vacío.')
    questions = data['questions']
    if not isinstance(questions, dict) or not questions:
        raise ValueError('questions debe ser un objeto no vacío.')
    for name, question in questions.items():
        if not nonempty(name) or not isinstance(question, dict):
            raise ValueError('Cada pregunta necesita un identificador y un objeto.')
        if set(question) - {'type', 'instructions', 'criteria'} or not nonempty(question.get('instructions')):
            raise ValueError(f'Pregunta {name}: campos desconocidos o instructions vacío.')
        kind, criteria = question.get('type'), question.get('criteria')
        if kind == 'choice':
            valid = isinstance(criteria, dict) and len(criteria) >= 2 and all(nonempty(k) and nonempty(v) for k, v in criteria.items())
        elif kind == 'score':
            valid = isinstance(criteria, list) and len(criteria) >= 2 and all(nonempty(v) for v in criteria) and len(set(criteria)) == len(criteria)
        elif kind == 'noul':
            valid = 'criteria' not in question or isinstance(criteria, dict) and set(criteria) == {'true', 'false'} and all(nonempty(v) for v in criteria.values())
        else:
            valid = False
        if not valid:
            raise ValueError(f'Pregunta {name}: tipo o criterios no válidos para System One.')
    return {'model': deployment, 'state': state, 'questions': questions}


def validate_response(data: Any, request: DecisionRequest) -> DecisionResponse:
    if not isinstance(data, dict) or not isinstance(data.get('answers'), dict):
        raise ValueError('El proveedor no devolvió un objeto answers válido.')
    answers = data['answers']
    if set(answers) != set(request['questions']):
        raise ValueError('La respuesta no corresponde a todas las preguntas enviadas.')
    for name, question in request['questions'].items():
        answer = answers[name]
        if not isinstance(answer, dict) or answer.get('type') != question['type']:
            raise ValueError(f'El proveedor devolvió un tipo de respuesta incompatible en {name}.')
        choice = answer.get('choice')
        if question['type'] == 'choice' and (not isinstance(choice, str) or choice not in question['criteria']):
            raise ValueError(f'El proveedor seleccionó una alternativa desconocida en {name}.')
        def number(value, low, high):
            return type(value) in (int, float) and math.isfinite(value) and low <= value <= high
        if 'confidence' in answer and not number(answer['confidence'], 0, 1):
            raise ValueError(f'Confidence inválido en {name}.')
        if question['type'] == 'noul':
            if not number(answer.get('noul'), 0, 1):
                raise ValueError(f'Noul ausente o fuera de rango en {name}.')
        else:
            levels = set(question['criteria']) if question['type'] == 'choice' else {str(i) for i in range(len(question['criteria']))}
            probabilities = answer.get('probabilities')
            if not isinstance(probabilities, dict) or set(probabilities) != levels or not all(number(p, 0, 1) for p in probabilities.values()) or not math.isclose(sum(probabilities.values()), 1, abs_tol=1e-5):
                raise ValueError(f'Distribución incompleta o inválida en {name}.')
            if question['type'] == 'score':
                score = answer.get('score')
                expected = sum(int(level) * p for level, p in probabilities.items())
                if not number(score, 0, len(levels) - 1) or not math.isclose(score, expected, abs_tol=1e-5):
                    raise ValueError(f'Score ausente, fuera de escala o inconsistente en {name}.')
    return data


def call_systemone(config: ExecutorConfig, body: bytes, credential: str) -> bytes:
    if any(ord(character) < 32 or ord(character) == 127 for character in credential):
        raise ValueError('La credencial contiene caracteres de control no válidos.')
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
    headers['api-key' if config.auth == 'api_key' else 'Authorization'] = credential if config.auth == 'api_key' else f'Bearer {credential}'
    request = Request(config.endpoint, data=body, headers=headers, method='POST')
    context = ssl.create_default_context()
    if not config.verify_tls:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    try:
        with build_opener(NoRedirect(), HTTPSHandler(context=context)).open(request, timeout=config.timeout_seconds) as response:
            raw = response.read(config.max_response_bytes + 1)
    except HTTPError as error:
        raise TransportError(f'Decision-1 devolvió HTTP {error.code}; revisa permisos, despliegue o preguntas. No se modificaron los resultados del caso.',
                             {'code': 'HTTP_ERROR', 'http_status': error.code, 'host': urlsplit(config.endpoint).hostname}) from None
    except (URLError, TimeoutError, HTTPException, OSError) as error:
        raise connection_error(error, config.endpoint) from None
    if len(raw) > config.max_response_bytes:
        raise ValueError('La respuesta supera el límite configurado.')
    return raw


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def execute(case_path: str | Path, dry_run: bool = False, config_file: str | Path | None = None) -> None:
    kit_home = Path(os.environ.get('DECISION_KIT_HOME') or os.environ.get('CODEX_HOME') or Path(__file__).resolve().parents[2])
    config = read_config(kit_home, config_file)
    case = Path(case_path).resolve(strict=True) / '.artifacts'
    provenance_hash = verify_provenance(case.parent)
    for name in ('status.md', 'input.md', 'input.json'):
        if not (case / name).is_file():
            raise ValueError(f'El caso necesita {name}. Ejecuta analysis antes de executor.')
    source = case / 'input.json'
    original = source.read_bytes()
    markdown = (case / 'input.md').read_bytes()
    request = validate_input(strict_json(original.decode('utf-8-sig')), config.deployment)
    credential, credential_source = resolve_credential(config.credential_env)
    summary = {'mode': 'systemone', 'ready': config.ready, 'deployment': config.deployment,
               'tls_verification': config.verify_tls,
               'endpoint_configured': not urlsplit(config.endpoint).hostname.endswith('.invalid'),
               'credential_present': bool(credential), 'questions': len(request['questions']),
               'credential_source': credential_source,
               'input_sha256': digest(original)}
    if dry_run:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return
    if not config.ready or not credential or not summary['endpoint_configured']:
        raise ValueError(f'Conexión pendiente: habilita execution.ready y define {config.credential_env} en el entorno.')
    body = json.dumps(request, ensure_ascii=False, allow_nan=False).encode('utf-8')
    network_log = NetworkLog(case, config.endpoint, 'decision_request')
    network_log.record('request_started', {'credential_source': credential_source, 'credentials_present': bool(credential),
                                            'tls_verification': config.verify_tls})
    try:
        raw = call_systemone(config, body, credential)
    except TransportError as error:
        network_log.record('request_failed', error.diagnostic)
        network_log.dns()
        error.diagnostic.update(network_log.reference())
        raise
    except ValueError:
        network_log.record('request_failed', {'code': 'LOCAL_TRANSPORT_ERROR'})
        raise
    network_log.record('http_completed', {'response_bytes': len(raw)})
    response = validate_response(strict_json(raw.decode('utf-8-sig')), request)
    network_log.record('response_validated', {'questions': len(request['questions'])})
    if source.read_bytes() != original or (case / 'input.md').read_bytes() != markdown:
        raise ValueError('La entrada cambió durante la llamada; no se guardará una ejecución para otra revisión.')
    if verify_provenance(case.parent) != provenance_hash:
        raise ValueError('La procedencia cambió durante la llamada; se conserva la ejecución anterior.')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    metadata = (f'# Ejecución de Decision-1\n\n## Metadatos\n\n'
                f'- Fecha UTC: {stamp}\n- Modo: systemone\n- Despliegue solicitado: {config.deployment}\n'
                f'- Verificación TLS: {"habilitada" if config.verify_tls else "DESHABILITADA temporalmente por configuración"}\n'
                f'- Modelo declarado por el proveedor: {response.get("model", "no informado")}\n'
                f'- SHA-256 de input.json: {digest(original)}\n'
                f'- SHA-256 de input.md: {digest(markdown)}\n'
                f'- SHA-256 de request.json: {digest(body)}\n'
                f'- SHA-256 de response.json: {digest(raw)}\n\n'
                f'- SHA-256 de provenance.json: {provenance_hash}\n\n'
                '## Respuesta estructurada\n\nDecision-1 devuelve decisiones numéricas; '
                'no proporciona una explicación escrita. El análisis posterior corresponde a Codex.\n\n'
                'La respuesta original está en [response.json](response.json).\n\n'
                '```json\n' + json.dumps(response, ensure_ascii=False, indent=2, allow_nan=False) + '\n```\n')
    outputs = {'request.json': body, 'response.json': raw, 'execution.md': metadata.encode('utf-8')}
    pending: dict[str, Path] = {}
    try:
        for name, content in outputs.items():
            path = case / f'.{name}-{uuid.uuid4().hex}.tmp'
            with path.open('xb') as stream:
                pending[name] = path
                stream.write(content)
        existing = [case / name for name in outputs if (case / name).exists()]
        if existing:
            archive = case / 'history' / f'execution-{stamp}'
            archive.mkdir(parents=True, exist_ok=False)
            for path in existing:
                shutil.copy2(path, archive / path.name)
        for name in outputs:
            pending[name].replace(case / name)
    finally:
        for path in pending.values():
            path.unlink(missing_ok=True)
    print(json.dumps({'output': str(case / 'execution.md'), 'input_sha256': digest(original), **network_log.reference()}, ensure_ascii=False))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', required=True)
    parser.add_argument('--config', help='Ruta explícita a executor.toml; no requiere perfil ni CODEX_HOME.')
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument('--dry-run', action='store_true', help='Valida entrada y configuración sin enviar ni modificar archivos.')
    actions.add_argument('--diagnose-network', action='store_true', help='Registra DNS/TCP/HTTPS sin enviar clave ni consultar Decision-1.')
    args = parser.parse_args()
    try:
        if args.diagnose_network:
            kit_home = Path(os.environ.get('DECISION_KIT_HOME') or os.environ.get('CODEX_HOME') or Path(__file__).resolve().parents[2])
            config = read_config(kit_home, args.config)
            result = diagnose_network(Path(args.case).resolve(strict=True), config, connection_error)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if result['reachable'] else 1
        execute(args.case, args.dry_run, args.config)
    except (ValueError, OSError, KeyError) as error:
        output = {'error': str(error)}
        if isinstance(error, TransportError):
            output['diagnostic'] = error.diagnostic
        print(json.dumps(output, ensure_ascii=False), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
