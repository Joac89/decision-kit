"""Configuración optativa y comprobación de red mediante permisos nativos de Codex."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tomllib

PERMISSION = 'decision-kit-network'


def config_path(home, profile=None):
    home = Path(home).expanduser().resolve(strict=True)
    if profile and not re.fullmatch(r'[a-zA-Z0-9_-]+', profile):
        raise ValueError('Nombre de perfil inválido.')
    path = home / (profile + '.config.toml' if profile else 'config.toml')
    if path.is_symlink() or not path.resolve().is_relative_to(home):
        raise ValueError('La configuración debe estar dentro del home indicado.')
    return home, path


def enable_network(home, profile=None):
    home, path = config_path(home, profile)
    if not (home / 'decision/executor.toml').is_file():
        raise ValueError('Instala el kit en ese home antes de configurar permisos.')
    if profile and not path.is_file():
        raise ValueError('El perfil indicado no existe; este comando no crea perfiles.')
    original = path.read_text(encoding='utf-8-sig') if path.exists() else ''
    config = tomllib.loads(original)
    if profile:
        base = tomllib.loads((home / 'config.toml').read_text(encoding='utf-8-sig')) if (home / 'config.toml').exists() else {}
        for key in ('sandbox_mode', 'sandbox_workspace_write', 'default_permissions', 'permissions'):
            if key in base:
                raise ValueError('La base ya define permisos; revisa su combinación con el perfil antes de cambiar red.')
    active = config.get('default_permissions')
    if active:
        permission = config.get('permissions', {}).get(active, {})
        if permission.get('extends') == ':workspace' and permission.get('network', {}).get('enabled') is True:
            return {'configured': True, 'changed': False, 'permission': active, 'restart_required': True}
        raise ValueError('Ya hay permisos nombrados personalizados; configura su red con Codex sin reemplazarlos automáticamente.')
    if any(key in config for key in ('sandbox_mode', 'sandbox_workspace_write', 'permissions')):
        raise ValueError('Ya hay permisos personalizados; no se sustituyen automáticamente. Revisa la configuración de Codex.')
    updated = f'default_permissions = "{PERMISSION}"\n' + original.rstrip()
    updated += f'\n\n[permissions.{PERMISSION}]\nextends = ":workspace"\n\n[permissions.{PERMISSION}.network]\nenabled = true\n'
    tomllib.loads(updated)
    backup = None
    if path.exists():
        folder = home / 'decision-backups' / ('network-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
        folder.mkdir(parents=True)
        backup = folder / path.name
        shutil.copy2(path, backup)
    path.write_text(updated, encoding='utf-8')
    return {'configured': True, 'changed': True, 'config': str(path), 'permission': PERMISSION,
            'backup': str(backup) if backup else None, 'restart_required': True,
            'scope': 'outbound networking for commands; workspace file restrictions retained',
            'managed_policy_overridden': False}


def native_codex(explicit=None):
    if explicit:
        candidate = Path(explicit).expanduser().resolve(strict=True)
    else:
        found = shutil.which('codex.exe' if os.name == 'nt' else 'codex')
        if found:
            candidate = Path(found)
        elif os.name == 'nt' and shutil.which('codex.cmd'):
            npm = Path(shutil.which('codex.cmd')).parent / 'node_modules/@openai/codex/node_modules/@openai'
            arch = 'arm64' if platform.machine().lower() in ('arm64', 'aarch64') else 'x64'
            triplet = 'aarch64' if arch == 'arm64' else 'x86_64'
            candidate = npm / f'codex-win32-{arch}/vendor/{triplet}-pc-windows-msvc/bin/codex.exe'
        else:
            raise ValueError('No se encontró Codex; instala el CLI o indica --codex con su ejecutable nativo.')
    if not candidate.is_file() or (os.name == 'nt' and candidate.suffix.lower() != '.exe'):
        raise ValueError('Indica --codex con el ejecutable nativo de Codex; no un archivo .bat o .cmd.')
    return str(candidate)


def diagnose_codex(home, case, profile=None, codex=None):
    home, path = config_path(home, profile)
    config = tomllib.loads(path.read_text(encoding='utf-8-sig'))
    base = tomllib.loads((home / 'config.toml').read_text(encoding='utf-8-sig')) if profile and (home / 'config.toml').is_file() else {}
    permission = config.get('default_permissions', base.get('default_permissions'))
    if not isinstance(permission, str) or not permission:
        raise ValueError('Falta un permiso nombrado activo: configura red con configure-codex-network o con las opciones nativas de Codex.')
    case = Path(case).expanduser().resolve(strict=True)
    if not case.is_dir():
        raise ValueError('--case debe ser una carpeta existente.')
    executor = home / 'decision/scripts/execute.py'
    if not executor.is_file():
        raise ValueError('Falta el ejecutor instalado en el home indicado.')
    command = [native_codex(codex), 'sandbox', '-P', permission, '--include-managed-config', '-C', str(case)]
    if profile:
        command += ['-p', profile]
    command += [sys.executable, str(executor), '--case', str(case), '--config', str(home / 'decision/executor.toml'), '--diagnose-network']
    environment = os.environ.copy()
    environment.update(CODEX_HOME=str(home), CODEX_SQLITE_HOME=str(home))
    # Do not remove proxy variables: preserve effective policy and transport settings.
    try:
        result = subprocess.run(command, env=environment, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        return {'reachable': False, 'decision_sent': False, 'stage': 'codex', 'error': 'El diagnóstico de Codex superó 60 segundos.'}
    try:
        diagnostic = json.loads(result.stdout)
        if not isinstance(diagnostic, dict) or diagnostic.get('decision_sent') is not False or not isinstance(diagnostic.get('reachable'), bool):
            raise ValueError('Formato inesperado')
    except (ValueError, TypeError):
        return {'reachable': False, 'decision_sent': False, 'stage': 'codex', 'exit_code': result.returncode,
                'error': 'Codex no completó el diagnóstico. Revisa versión, configuración y política administrada. No se ampliaron permisos ni se envió una decisión.'}
    diagnostic['environment'] = 'codex_sandbox'
    if result.returncode != 0:
        diagnostic['reachable'] = False
    return diagnostic
