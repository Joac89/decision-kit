"""Vincula una entrada preparada con los documentos usados, sin red."""
import argparse
import hashlib
import json
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record(case, research):
    case = Path(case).resolve(strict=True)
    names = ['context.md', '.artifacts/input.md', '.artifacts/input.json']
    if research == 'used':
        names.append('research.md')
    data = {'version': 1, 'research': research,
            'hashes': {name: digest(case / name) for name in names}}
    path = case / '.artifacts/provenance.json'
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return data


def verify(case):
    case = Path(case).resolve(strict=True)
    path = case / '.artifacts/provenance.json'
    if not path.is_file():
        raise ValueError('Falta provenance.json: prepara la entrada con analysis; no reconstruyas procedencia histórica por suposición.')
    data = json.loads(path.read_text(encoding='utf-8'))
    expected = {'context.md', '.artifacts/input.md', '.artifacts/input.json'}
    if data.get('research') == 'used':
        expected.add('research.md')
    elif data.get('research') != 'omitted':
        raise ValueError('Procedencia de investigación inválida.')
    if data.get('version') != 1 or set(data.get('hashes', {})) != expected:
        raise ValueError('Manifiesto de procedencia inválido.')
    for name, saved in data['hashes'].items():
        if not (case / name).is_file() or digest(case / name) != saved:
            raise ValueError(f'Cambió {name}: usa analysis para revisar y regenerar la entrada antes de ejecutar o reportar.')
    return digest(path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', required=True)
    parser.add_argument('--research', required=True, choices=['used', 'omitted'])
    args = parser.parse_args()
    print(json.dumps(record(args.case, args.research), ensure_ascii=False))
