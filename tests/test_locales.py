import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('locales_root', ROOT / 'modules/locales-root.py')
locales = importlib.util.module_from_spec(spec)
spec.loader.exec_module(locales)


class LocalesTests(unittest.TestCase):
    def test_generation_preserves_existing_locales_and_does_not_set_language(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'etc').mkdir()
            (root / 'etc/os-release').write_text('ID=debian\nVERSION_ID="13"\n')
            target = root / 'etc/locale.gen'
            original = '# comment\nfr_FR.UTF-8 UTF-8\n# zh_CN.UTF-8 UTF-8\n'
            target.write_text(original)
            profile = root / 'profile.json'
            profile.write_text(json.dumps({'localization': {
                'language': 'zh_CN.UTF-8',
                'generated_locales': ['zh_CN.UTF-8', 'en_US.UTF-8']}}))
            def filesystem(value):
                path = Path(value)
                return root / str(path).lstrip('/') if str(path).startswith(('/etc/', '/var/')) else path
            with patch.object(locales, 'Path', side_effect=filesystem), \
                 patch.object(locales.os, 'geteuid', return_value=0), \
                 patch.object(locales.pwd, 'getpwnam', return_value=SimpleNamespace(pw_uid=1000)), \
                 patch.object(locales.subprocess, 'check_output', return_value='C\nfr_FR.utf8\n'), \
                 patch.object(locales.subprocess, 'run') as run, \
                 patch('sys.argv', ['locales-root.py', '--profile', str(profile), '--user', 'tester', '--generate-only']):
                locales.main()
            self.assertIn('fr_FR.UTF-8 UTF-8', target.read_text())
            self.assertIn('\nzh_CN.UTF-8 UTF-8\n', target.read_text())
            self.assertIn('en_US.UTF-8 UTF-8', target.read_text())
            self.assertEqual(run.call_args_list[0].args[0], ['locale-gen'])
            self.assertEqual(run.call_count, 1)
            backups = list((root / 'var/backups/desktop-reinstall').glob('*/locale.gen'))
            self.assertEqual(backups[0].read_text(), original)
