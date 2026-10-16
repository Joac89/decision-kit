import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from decision_kit.installer import install, RESOURCES
from decision_kit.cli import configure

sys.path.insert(0, str(RESOURCES / 'decision/scripts'))
import execute
from provenance import record
from verify_case import verify_case


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / 'home'
        install(self.home)

    def test_install_update_preserve_configuration_and_profiles(self):
        self.assertFalse((self.home / 'config.toml').exists())
        self.assertFalse((self.home / 'decision.config.toml').exists())
        custom = self.home / 'expert.config.toml'
        custom.write_text('model="example"')
        configure(self.home, 'https://example.com/providers/microsoft/v1/systemone', 'Example', 'MY_KEY')
        config = (self.home / 'decision/executor.toml').read_bytes()
        update = install(self.home, update=True)
        self.assertEqual((self.home / 'decision/executor.toml').read_bytes(), config)
        self.assertEqual(custom.read_text(), 'model="example"')
        self.assertTrue(Path(update['backup']).is_dir())
        self.assertTrue((self.home / 'skills/spec-decision/assets/.artifacts/input.json').is_file())

    def test_update_rejects_modified_resource(self):
        script = self.home / 'decision/scripts/execute.py'
        script.write_text('custom')
        with self.assertRaises(ValueError):
            install(self.home, update=True)
        self.assertEqual(script.read_text(), 'custom')

    def test_profile_is_opt_in(self):
        other = self.root / 'other'
        install(other, profile=True)
        profile = (other / 'decision.config.toml').read_text()
        self.assertNotIn('network', profile)
        self.assertFalse((other / 'config.toml').exists())

    def test_explicit_configuration_and_iteration_without_codex(self):
        configure(self.home, 'https://example.com/providers/microsoft/v1/systemone', 'Example', 'MY_KEY')
        case = self.root / 'case'
        artifacts = case / '.artifacts'
        artifacts.mkdir(parents=True)
        (case / 'context.md').write_text('Context')
        (artifacts / 'status.md').write_text('Prepared')
        (artifacts / 'input.md').write_text('A or B')
        payload = {'state': 'Context', 'questions': {'q': {'type': 'choice', 'instructions': 'Choose', 'criteria': {'a': 'A', 'b': 'B'}}}}
        (artifacts / 'input.json').write_text(json.dumps(payload))
        record(case, 'omitted')
        raw = b'{"answers":{"q":{"type":"choice","choice":"a","probabilities":{"a":0.8,"b":0.2}}}}'
        config = self.home / 'decision/executor.toml'
        with patch.dict('os.environ', {'CODEX_HOME': str(self.root / 'not-codex'), 'MY_KEY': 'fake'}), patch.object(execute, 'call_systemone', return_value=raw) as transport:
            execute.execute(case, config_file=config)
            self.assertTrue(verify_case(case)['valid'])
            (case / 'insights.md').write_text('Editorial')
            self.assertTrue(verify_case(case)['valid'])
            (case / 'context.md').write_text('Changed')
            with self.assertRaises(ValueError):
                execute.execute(case, config_file=config)
            self.assertEqual(transport.call_count, 1)


if __name__ == '__main__':
    unittest.main()
