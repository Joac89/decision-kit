import json
import os
from pathlib import Path
import subprocess
import tempfile
import tomllib
import unittest
from unittest.mock import patch
from decision_kit.codex_network import enable_network, diagnose_codex
from decision_kit.installer import install


class CodexNetworkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        install(self.home)
        self.config = self.home / 'config.toml'
        self.config.write_text('model="example"\n[windows]\nsandbox="unelevated"\n', encoding='utf-8')

    def test_enable_is_explicit_preserves_config_and_backs_up(self):
        original = self.config.read_bytes()
        result = enable_network(self.home)
        self.assertEqual(Path(result['backup']).read_bytes(), original)
        parsed = tomllib.loads(self.config.read_text(encoding='utf-8'))
        self.assertEqual(parsed['model'], 'example')
        self.assertEqual(parsed['windows']['sandbox'], 'unelevated')
        self.assertEqual(parsed['permissions'][result['permission']]['extends'], ':workspace')
        self.assertFalse(enable_network(self.home)['changed'])
        self.assertFalse((self.home / 'decision.config.toml').exists())

    def test_custom_permissions_are_not_replaced(self):
        for text in ('sandbox_mode="read-only"', 'default_permissions="company"', '[sandbox_workspace_write]\nnetwork_access=false'):
            self.config.write_text(text, encoding='utf-8')
            with self.assertRaises(ValueError):
                enable_network(self.home)
            self.assertEqual(self.config.read_text(encoding='utf-8'), text)

    def test_profile_only_changes_requested_file(self):
        profile = self.home / 'test.config.toml'
        profile.write_text('model="example"', encoding='utf-8')
        original = self.config.read_bytes()
        enable_network(self.home, 'test')
        self.assertEqual(self.config.read_bytes(), original)
        self.assertIn('default_permissions', profile.read_text(encoding='utf-8'))
        with self.assertRaises(ValueError):
            enable_network(self.home, '../outside')

    def test_probe_uses_managed_policy_and_does_not_bypass_proxy(self):
        enable_network(self.home)
        completed = subprocess.CompletedProcess([], 0, json.dumps({'reachable': True, 'decision_sent': False, 'http_status': 401}), '')
        with patch('decision_kit.codex_network.native_codex', return_value='codex.exe'), patch('decision_kit.codex_network.subprocess.run', return_value=completed) as run, patch.dict(os.environ, {'HTTPS_PROXY': 'http://127.0.0.1:9'}):
            result = diagnose_codex(self.home, self.home)
        command = run.call_args.args[0]
        self.assertIn('--include-managed-config', command)
        self.assertIn('--diagnose-network', command)
        self.assertNotIn('--dangerously-bypass-approvals-and-sandbox', command)
        self.assertEqual(run.call_args.kwargs['env']['HTTPS_PROXY'], 'http://127.0.0.1:9')
        self.assertEqual(result['environment'], 'codex_sandbox')
        self.assertTrue(result['reachable'])

    def test_policy_rejection_is_failure_without_retry(self):
        enable_network(self.home)
        denied = subprocess.CompletedProcess([], 1, '', 'Managed policy denies this permission')
        with patch('decision_kit.codex_network.native_codex', return_value='codex.exe'), patch('decision_kit.codex_network.subprocess.run', return_value=denied) as run:
            result = diagnose_codex(self.home, self.home)
        self.assertFalse(result['reachable'])
        self.assertFalse(result['decision_sent'])
        self.assertEqual(run.call_count, 1)


if __name__ == '__main__':
    unittest.main()
