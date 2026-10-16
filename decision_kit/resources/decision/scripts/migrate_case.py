"""Migra nombres y vínculos sin cambiar entradas ni respuestas JSON."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

NAMES = {'00-status.md': '.artifacts/status.md', '01-context.md': 'context.md',
         '02-research.md': 'research.md', '03-input.md': '.artifacts/input.md',
         '03-input.json': '.artifacts/input.json', '04-execution.md': '.artifacts/execution.md',
         '04-request.json': '.artifacts/request.json', '04-response.json': '.artifacts/response.json',
         '05-analysis.md': 'analysis.md', '06-result.md': 'report.md', 'result.md': 'report.md'}


def migrate(case):
    case = Path(case).resolve(strict=True)
    moves = {}
    for old, new in NAMES.items():
        candidates = [p for p in (case / old, case / '.artifacts' / old) if p.is_file()]
        destination = case / new
        if destination.exists():
            candidates.append(destination)
        if not candidates:
            continue
        if len({p.read_bytes() for p in candidates}) != 1:
            raise ValueError(f'Hay versiones distintas de {old}; requiere revisión antes de migrar.')
        moves.setdefault(new, []).extend(candidates)
    for new, candidates in moves.items():
        if len({p.read_bytes() for p in candidates}) != 1:
            raise ValueError(f'Hay versiones distintas para {new}; requiere revisión.')
    if not any(p.name in NAMES for paths in moves.values() for p in paths):
        print(json.dumps({'already_migrated': True}))
        return
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backup = case.parent / '.decision-backups' / (case.name + '-' + stamp)
    shutil.copytree(case, backup)
    json_hashes = {}
    for new, candidates in moves.items():
        destination = case / new
        destination.parent.mkdir(parents=True, exist_ok=True)
        content = candidates[0].read_bytes()
        if destination.suffix == '.json':
            json_hashes[new] = hashlib.sha256(content).hexdigest()
        destination.write_bytes(content)
        for old in candidates:
            if old != destination:
                old.unlink()
    for folder in ('logs', 'history'):
        source = case / folder
        if source.exists():
            destination = case / '.artifacts' / folder
            shutil.copytree(source, destination, dirs_exist_ok=True)
            # Remove only the exact, verified case subdirectory copied above.
            if source.resolve().parent != case or not source.is_dir():
                raise ValueError('Ruta de migración inesperada.')
            shutil.rmtree(source)
    # Update public Markdown links. Preserve input bytes: execution hashes depend on them.
    for path in [*case.glob('*.md'), case / '.artifacts/status.md']:
        if not path.is_file():
            continue
        text = path.read_text(encoding='utf-8-sig')
        for old, new in NAMES.items():
            text = text.replace('.artifacts/' + old, new).replace(old, new)
        if path.parent.name == '.artifacts':
            text = text.replace('](.artifacts/', '](')
            for public in ('context.md', 'research.md', 'analysis.md', 'report.md'):
                text = text.replace('](' + public + ')', '](../' + public + ')')
        path.write_text(text, encoding='utf-8')
    execution = case / '.artifacts/execution.md'
    if execution.is_file():
        text = execution.read_text(encoding='utf-8-sig')
        for old, new in NAMES.items():
            text = text.replace(old, Path(new).name)
        execution.write_text(text, encoding='utf-8')
    (case / 'README.md').write_text('# Caso de decisión\n\nEmpieza por [el reporte y las recomendaciones](report.md).\n\n- [Análisis completo](analysis.md)\n- [Contexto](context.md)\n\nLa evidencia técnica y el estado están en `.artifacts/`.\n', encoding='utf-8')
    assert all(hashlib.sha256((case / name).read_bytes()).hexdigest() == value for name, value in json_hashes.items())
    print(json.dumps({'migrated': True, 'backup': str(backup), 'json_hashes': json_hashes}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', required=True)
    migrate(parser.parse_args().case)
