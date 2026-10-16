import argparse
import json
from pathlib import Path
import runpy
import sys
import tomllib
from urllib.parse import urlsplit
from .installer import RESOURCES, install


def configure(home, endpoint, deployment, credential_env):
    endpoint_parts = urlsplit(endpoint)
    if endpoint_parts.scheme != 'https' or not endpoint_parts.hostname or endpoint_parts.username or endpoint_parts.password or endpoint_parts.query or endpoint_parts.fragment or not endpoint_parts.path.rstrip('/').endswith('/systemone'):
        raise ValueError('Indica el endpoint HTTPS completo terminado en /systemone, sin credenciales ni query.')
    if not deployment.strip() or not credential_env.isidentifier():
        raise ValueError('Despliegue o nombre de variable de credencial inválidos.')
    path = Path(home).expanduser().resolve() / 'decision/executor.toml'
    if not path.is_file():
        raise ValueError('Instala el kit antes de configurar la conexión.')
    original = path.read_text(encoding='utf-8')
    data = tomllib.loads(original)
    data.update(endpoint=endpoint, deployment=deployment, credential_env=credential_env)
    # Preserve unrelated fields and TLS policy; replace only three scalar settings.
    import re
    text = original
    for key in ('endpoint', 'deployment', 'credential_env'):
        line = key + ' = ' + json.dumps(data[key], ensure_ascii=False)
        if re.search(r'(?m)^' + key + r'\s*=', text):
            text = re.sub(r'(?m)^' + key + r'\s*=.*$', lambda _: line, text)
        else:
            text += '\n' + line + '\n'
    tomllib.loads(text)
    settings_path = path.parent / 'settings.toml'
    settings_text = settings_path.read_text(encoding='utf-8')
    section = re.search(r'(?ms)^\[execution\]\s*\n(.*?)(?=^\[|\Z)', settings_text)
    if not section:
        raise ValueError('settings.toml no contiene execution.')
    body = section.group(1)
    if re.search(r'(?m)^ready\s*=', body):
        body = re.sub(r'(?m)^ready\s*=.*$', 'ready = true', body)
    else:
        body += '\nready = true\n'
    new_settings = settings_text[:section.start(1)] + body + settings_text[section.end(1):]
    tomllib.loads(new_settings)
    from datetime import datetime, timezone
    import shutil
    backup = path.parent.parent / 'decision-backups' / ('configure-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    backup.mkdir(parents=True)
    shutil.copy2(path, backup / path.name)
    shutil.copy2(settings_path, backup / settings_path.name)
    path.write_text(text, encoding='utf-8')
    settings_path.write_text(new_settings, encoding='utf-8')
    return {'configured': True, 'config': str(path), 'credential_stored': False}


def main():
    parser = argparse.ArgumentParser(prog='decision-kit')
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('install', 'update'):
        sub = commands.add_parser(name)
        sub.add_argument('--target', required=True)
        sub.add_argument('--profile', action='store_true', help='Crear el perfil decision de Codex; no cambia red ni configuración base.')
    sub = commands.add_parser('configure')
    sub.add_argument('--home', required=True)
    sub.add_argument('--endpoint', required=True)
    sub.add_argument('--deployment', required=True)
    sub.add_argument('--credential-env', default='DECISION_API_KEY')
    for command in ('execute', 'verify', 'prepare', 'diagnose'):
        commands.add_parser(command, add_help=False)
    args, remainder = parser.parse_known_args()
    try:
        if args.command in ('install', 'update'):
            if remainder:
                parser.error('Argumentos desconocidos: ' + ' '.join(remainder))
            result = install(args.target, args.command == 'update', args.profile)
        elif args.command == 'configure':
            if remainder:
                parser.error('Argumentos desconocidos')
            result = configure(args.home, args.endpoint, args.deployment, args.credential_env)
        else:
            scripts = RESOURCES / 'decision/scripts'
            sys.path.insert(0, str(scripts))
            script = {'execute': 'execute.py', 'verify': 'verify_case.py', 'prepare': 'provenance.py', 'diagnose': 'execute.py'}[args.command]
            if args.command in ('execute', 'diagnose') and '--config' not in remainder and '--help' not in remainder and '-h' not in remainder:
                raise ValueError('El CLI portable requiere --config /ruta/executor.toml.')
            sys.argv = [script, *remainder] + (['--diagnose-network'] if args.command == 'diagnose' else [])
            runpy.run_path(str(scripts / script), run_name='__main__')
            return
        print(json.dumps(result, ensure_ascii=False))
    except (ValueError, OSError, KeyError) as error:
        print(json.dumps({'error': str(error)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1)
