import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import installer

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('arch_cleanup', ROOT / 'modules/cleanup-arch.py')
cleanup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cleanup)


class ArchCleanupTests(unittest.TestCase):
    def setUp(self):
        self.profile = json.loads((ROOT / 'profiles/arch.json').read_text())

    def test_calendar_and_clock_are_protected_even_if_profile_protection_is_edited(self):
        self.profile['cleanup']['protect'] = []
        self.profile['cleanup']['remove_exact'].append('gnome-calendar')
        with self.assertRaisesRegex(RuntimeError, '受保护组件冲突'):
            cleanup.validate_profile(self.profile)

    def test_plan_requires_exact_targets_and_rejects_protected_or_extra_removals(self):
        for output in ['showtime\ngnome-clocks\n', 'showtime\nextra-lib\n', '', 'showtime\nshowtime\n']:
            with self.subTest(output=output), self.assertRaises(RuntimeError):
                cleanup.removal_plan(output, ['showtime'], {'gnome-clocks'})
        self.assertEqual(cleanup.removal_plan('showtime\n', ['showtime'], set()), ['showtime'])

    def test_postcheck_rejects_missing_protected_packages_and_changes_to_other_packages(self):
        before = {'showtime':'1', 'gnome-clocks':'1', 'gnome-calendar':'1'}
        after = {'gnome-clocks':'1', 'gnome-calendar':'1'}
        self.assertEqual(cleanup.verify_after(before, after, ['showtime'], {'gnome-clocks'}), ['showtime'])
        for invalid in [{}, {'gnome-clocks':'2', 'gnome-calendar':'1'}, {**after, 'new-package':'1'}]:
            with self.assertRaises(RuntimeError):
                cleanup.verify_after(before, invalid, ['showtime'], {'gnome-clocks'})

    def run_apply(self, temp, failure=None):
        root = Path(temp)
        profile = root / 'arch.json'
        profile.write_text(json.dumps(self.profile))
        before = {'showtime':'1', 'gnome-calendar':'1', 'gnome-clocks':'1', 'gnome-shell':'51'}
        after = {name:version for name,version in before.items() if name != 'showtime'}
        def filesystem(value):
            path = Path(value)
            if str(path).startswith(('/run/lock/', '/var/log/')):
                path = root / str(path).lstrip('/')
                path.parent.mkdir(parents=True, exist_ok=True)
            return path
        def read(args):
            if args[:2] == ['pacman', '-Rp']: return 'showtime\n'
            if args == ['pacman', '-Qqe']: return '\n'.join(before)+'\n'
            if args == ['pacman', '-Dk']: return 'No database errors have been found!\n'
            raise AssertionError(args)
        with patch.object(cleanup, 'Path', side_effect=filesystem), \
             patch.object(cleanup.platform, 'freedesktop_os_release', return_value={'ID':'arch'}), \
             patch.object(cleanup.os, 'geteuid', return_value=0), \
             patch.object(cleanup, 'installed', side_effect=[before,before,after]), \
             patch.object(cleanup, 'read', side_effect=read), \
             patch.object(cleanup.subprocess, 'run', side_effect=failure) as run, \
             contextlib.redirect_stdout(io.StringIO()):
            if failure:
                with self.assertRaises(subprocess.CalledProcessError):
                    cleanup.main(['--profile', str(profile), '--apply'])
            else:
                cleanup.main(['--profile', str(profile), '--apply'])
        report = next((root / 'var/log/desktop-reinstall').glob('*/result.json'))
        return json.loads(report.read_text()), run.call_args.args[0]

    def test_apply_uses_plain_removal_and_records_verified_result(self):
        with tempfile.TemporaryDirectory() as temp:
            result, command = self.run_apply(temp)
        self.assertEqual(command, ['pacman','-R','--noconfirm','--','showtime'])
        self.assertEqual(result['removed'], ['showtime'])
        self.assertTrue(result['protected_packages_preserved'])
        self.assertEqual(result['status'], 'READY')

    def test_pacman_failure_is_recorded_without_success(self):
        with tempfile.TemporaryDirectory() as temp:
            result, command = self.run_apply(temp, subprocess.CalledProcessError(1, ['pacman']))
        self.assertEqual(result['status'], 'FAILED')
        self.assertNotIn('removed', result)

    def test_repeat_after_cleanup_does_not_mutate_packages(self):
        with patch.object(cleanup.platform, 'freedesktop_os_release', return_value={'ID':'arch'}), \
             patch.object(cleanup.os, 'geteuid', return_value=1000), \
             patch.object(cleanup, 'installed', return_value={'gnome-calendar':'1','gnome-clocks':'1'}), \
             patch.object(cleanup.subprocess, 'run', side_effect=AssertionError('mutation')), \
             contextlib.redirect_stdout(io.StringIO()):
            cleanup.main([])

    def test_arch_controller_accepts_full_module_set_and_delegates_cleanup(self):
        common = installer.load(ROOT / 'profiles/common.json')
        obj = installer.Installer(self.profile, common, ['cleanup'], ROOT / 'profiles/arch.json')
        with patch.object(installer.platform, 'freedesktop_os_release', return_value={'ID':'arch'}), \
             patch.object(installer.platform, 'machine', return_value='x86_64'), \
             patch.object(installer.os, 'geteuid', return_value=1000), \
             patch.object(installer.shutil, 'which', return_value='/fixture/command'):
            obj.preflight()
            obj.selected = ['cleanup','docker','fnm','uv']
            obj.preflight()
        with patch.object(obj, 'run') as run:
            obj.execute('cleanup')
        self.assertEqual(run.call_args.args[0][2], ROOT / 'modules/cleanup-arch.py')

    def test_arch_default_selects_full_workflow_without_executing_commands(self):
        with patch.object(installer.platform, 'freedesktop_os_release', return_value={'ID':'arch'}), \
             patch('subprocess.run', side_effect=AssertionError('mutation')), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(installer.main([]), 0)
        self.assertIn('cleanup', output.getvalue())
        self.assertIn('locale', output.getvalue())
        self.assertIn('docker', output.getvalue())
        self.assertIn('appearance', output.getvalue())
