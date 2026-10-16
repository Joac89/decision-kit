"""Instala el wheel en un entorno nuevo, sin red ni dependencias externas."""
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

wheel = next((Path(__file__).resolve().parents[1] / 'dist').glob('*.whl'))
with zipfile.ZipFile(wheel) as archive:
    names = archive.namelist()
    assert 'decision_kit/resources/skills/spec-decision/assets/.artifacts/input.json' in names
    assert 'decision_kit/resources/skills/spec-decision/assets/insights.md' in names
    assert not any(name.endswith('.jsonl') for name in names)
    assert not any('__pycache__' in name or name.endswith('.pyc') for name in names)
with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    subprocess.run([sys.executable, '-m', 'venv', str(root / 'venv')], check=True, capture_output=True)
    python = root / 'venv' / ('Scripts/python.exe' if sys.platform == 'win32' else 'bin/python')
    def run(*args):
        result = subprocess.run([str(python), *args], cwd=root, check=True, capture_output=True, text=True)
        return result.stdout
    run('-m', 'pip', 'install', '--no-index', '--no-deps', str(wheel))
    run('-m', 'decision_kit', 'install', '--target', str(root / 'home'))
    run('-m', 'decision_kit', 'configure', '--home', str(root / 'home'), '--endpoint', 'https://example.com/providers/microsoft/v1/systemone', '--deployment', 'Example')
    before = (root / 'home/decision/executor.toml').read_bytes()
    run('-m', 'decision_kit', 'update', '--target', str(root / 'home'))
    assert before == (root / 'home/decision/executor.toml').read_bytes()
    assert not (root / 'home/config.toml').exists()
    run('-m', 'decision_kit', 'execute', '--help')
print('Wheel verificado: recursos completos, instalación y actualización aisladas sin red.')
