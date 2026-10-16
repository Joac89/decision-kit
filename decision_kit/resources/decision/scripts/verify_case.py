"""Verifica entradas y resultados existentes sin red ni credenciales."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

from execute import strict_json, validate_input, validate_response
from provenance import verify as verify_provenance


def verify_case(case_path: str | Path) -> dict:
    case = Path(case_path).resolve(strict=True) / '.artifacts'
    metadata = (case / 'execution.md').read_text(encoding='utf-8-sig')
    provenance = re.findall(r'SHA-256 de provenance.json:\s*([0-9a-fA-F]{64})\b', metadata)
    if len(provenance) != 1 or verify_provenance(case.parent) != provenance[0].lower():
        raise ValueError('La ejecución no acredita las fuentes actuales. Conserva el resultado como histórico; revisa con analysis antes de una nueva ejecución.')
    hashes = {}
    for name in ('input.json', 'input.md', 'request.json', 'response.json'):
        matches = re.findall(r'SHA-256 de ' + re.escape(name) + r':\s*([0-9a-fA-F]{64})\b', metadata)
        if len(matches) != 1:
            raise ValueError(f'No hay un hash único registrado para {name}.')
        actual = hashlib.sha256((case / name).read_bytes()).hexdigest()
        if actual != matches[0].lower():
            raise ValueError(f'El hash de {name} no coincide: la ejecución no está vigente.')
        hashes[name] = actual
    original = strict_json((case / 'input.json').read_text(encoding='utf-8-sig'))
    request = strict_json((case / 'request.json').read_text(encoding='utf-8-sig'))
    if not isinstance(request, dict) or set(request) != {'model', 'state', 'questions'} or not isinstance(request['model'], str) or not request['model'].strip():
        raise ValueError('La petición guardada no tiene el contrato esperado.')
    expected = validate_input(original, request['model'])
    if request != expected:
        raise ValueError('La petición enviada no corresponde a la entrada guardada.')
    response = strict_json((case / 'response.json').read_text(encoding='utf-8-sig'))
    validate_response(response, request)
    embedded = re.findall(r'```json\s*\n(.*?)\n```', metadata, re.DOTALL)
    if len(embedded) != 1 or strict_json(embedded[0]) != response:
        raise ValueError('El JSON mostrado en execution.md no corresponde a la respuesta original.')
    kinds = {key: question['type'] for key, question in request['questions'].items()}
    return {'valid': True, 'questions': len(kinds), 'question_types': kinds,
            'score_requested': 'score' in kinds.values(), 'deployment': request['model'],
            'model_returned': response.get('model'), 'hashes': hashes}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(verify_case(args.case), ensure_ascii=False, indent=2))
    except (ValueError, OSError, KeyError) as error:
        print(json.dumps({'valid': False, 'error': str(error)}, ensure_ascii=False), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
