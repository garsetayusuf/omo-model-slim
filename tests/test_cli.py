"""Tests for CLI lifecycle subcommands."""

import importlib.machinery
import importlib.util
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
ENTRY = ROOT / 'omo-model-slim'


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.record = base / 'action.txt'
        self.stub = base / 'installer.sh'
        self.stub.write_text('#!/bin/sh\nprintf "%s" "$1" > "$RECORD"\nexit 0\n', encoding='utf-8')
        self.stub.chmod(0o755)
        self.env = {**os.environ, 'OMO_INSTALLER': str(self.stub), 'RECORD': str(self.record)}

    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(ENTRY), *args], env=self.env, capture_output=True, text=True, timeout=30)

    def test_upgrade_runs_installer_install_action(self):
        result = self.run_cli('upgrade')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.record.read_text(), 'install')
        self.assertNotIn('Running installer action', result.stdout + result.stderr)

    def test_update_and_install_aliases(self):
        for alias in ('update', 'install'):
            self.record.unlink(missing_ok=True)
            result = self.run_cli(alias)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(self.record.read_text(), 'install')

    def test_uninstall_runs_installer_uninstall_action(self):
        result = self.run_cli('uninstall')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.record.read_text(), 'uninstall')

    def test_upgrade_fetches_latest_installer_instead_of_pinned_copy(self):
        loader = importlib.machinery.SourceFileLoader('omo_entry', str(ENTRY))
        spec = importlib.util.spec_from_loader('omo_entry', loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        result = subprocess.CompletedProcess(args=[], returncode=0)
        with patch.dict(os.environ, {'OMO_INSTALLER': ''}), \
             patch.object(module.urllib.request, 'urlopen', return_value=io.BytesIO(b'#!/bin/sh\nexit 0\n')) as urlopen, \
             patch.object(module.subprocess, 'run', return_value=result):
            code = module.lifecycle('upgrade')
        self.assertEqual(code, 0)
        self.assertEqual(urlopen.call_args.args[0], module.INSTALLER_URL)

    def test_help_advertises_lifecycle_commands(self):
        result = self.run_cli('--help')
        self.assertIn('upgrade', result.stdout)
        self.assertIn('uninstall', result.stdout)


if __name__ == '__main__':
    unittest.main()
