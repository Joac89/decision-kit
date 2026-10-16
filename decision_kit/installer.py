"""Instalación con propiedad explícita de archivos y preservación de configuración."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

RESOURCES = Path(__file__).parent / 'resources'
CONFIGS = {'decision/settings.toml', 'decision/executor.toml'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def install(target, update=False, profile=False):
    target = Path(target).expanduser().resolve()
    manifest_path = target / 'decision/install-manifest.json'
    previous = json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists() else None
    if bool(previous) != update:
        raise ValueError('Usa update para una instalación existente; install para una nueva.')
    sources = {p.relative_to(RESOURCES).as_posix(): p for p in RESOURCES.rglob('*') if p.is_file()}
    owned = previous.get('files', {}) if previous else {}
    for name in sources:
        destination = target / name
        if destination.is_symlink() or not destination.resolve().is_relative_to(target):
            raise ValueError(f'Destino fuera de la instalación: {name}')
        if destination.exists() and name not in CONFIGS:
            if name not in owned or sha(destination) != owned[name]:
                raise ValueError(f'Archivo ajeno o modificado: {name}; conserva o combina sus cambios antes de actualizar.')
    profile_path = target / 'decision.config.toml'
    if profile and profile_path.exists():
        raise ValueError('El perfil decision ya existe; el instalador no lo sobrescribe. Omite --profile.')
    backup = target / 'decision-backups' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    if update:
        for name in sources:
            destination = target / name
            if destination.is_file() and name not in CONFIGS:
                saved = backup / name
                saved.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(destination, saved)
        backup.mkdir(parents=True, exist_ok=True)
        shutil.copy2(manifest_path, backup / 'install-manifest.json')
    installed = dict(owned)
    for name, source in sources.items():
        destination = target / name
        if name in CONFIGS and destination.exists():
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        installed[name] = sha(destination)
    if profile:
        # Explicit Codex adapter opt-in. Base config and network permissions are untouched.
        text = 'developer_instructions = "Para decisiones lee $CODEX_HOME/decision/instructions.md."\n'
        for skill in sorted((target / 'skills').glob('spec-decision*')):
            text += f"\n[[skills.config]]\npath = 'skills/{skill.name}/SKILL.md'\nenabled = true\n"
        profile_path.write_text(text, encoding='utf-8')
    manifest_path.write_text(json.dumps({'version': '0.1.0', 'files': installed}, indent=2) + '\n', encoding='utf-8')
    return {'installed': True, 'target': str(target), 'profile_created': profile,
            'network_permissions_changed': False, 'backup': str(backup) if update else None}
