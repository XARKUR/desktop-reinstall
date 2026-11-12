import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

import installer as app

ROOT = Path(__file__).resolve().parents[1]


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.edition = app.load(ROOT / 'profiles/debian13.json')
        self.common = app.load(ROOT / 'profiles/common.json')

    def instance(self, selected):
        return app.Installer(self.edition, self.common, selected, ROOT / 'profiles/debian13.json')

    def test_default_and_group_selection_keep_order_and_skip(self):
        self.assertEqual(app.select_modules(self.common), list(app.MODULES))
        self.assertEqual(app.select_modules(self.common, 'extensions,environment', 'docker'),
                         ['fnm', 'uv', 'lunar', 'monitor', 'dock', 'appindicator'])
        for value in ['nothing', '', 'lunar,']:
            with self.assertRaises(ValueError):
                app.select_modules(self.common, value)
        with self.assertRaises(ValueError):
            app.select_modules(self.common, 'cleanup', 'cleanup')

    def test_default_entry_plan_never_executes_system_commands_or_writes(self):
        with patch('subprocess.run', side_effect=AssertionError('process')), \
             patch('subprocess.check_output', side_effect=AssertionError('query')), \
             patch.object(Path, 'mkdir', side_effect=AssertionError('write')), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(app.main([]), 0)
        self.assertIn('仅预览', output.getvalue())
        self.assertIn('cleanup', output.getvalue())

    def test_non_debian_apply_stops_before_writes_or_processes(self):
        obj = self.instance(['cleanup'])
        with patch.object(app.os, 'geteuid', return_value=1000), \
             patch.object(app.platform, 'freedesktop_os_release', return_value={'ID':'debian','VERSION_ID':'12'}), \
             patch.object(Path, 'mkdir', side_effect=AssertionError('write')), \
             patch('subprocess.run', side_effect=AssertionError('process')):
            with self.assertRaisesRegex(ValueError, 'Debian 13'):
                obj.apply()

    def test_project_download_failure_precedes_any_package_mutation(self):
        obj = self.instance(['cleanup', 'weather'])
        with tempfile.TemporaryDirectory() as temp, \
             patch.dict(os.environ, XDG_STATE_HOME=temp, XDG_CACHE_HOME=temp), \
             patch.object(obj, 'preflight'), \
             patch.object(app, 'fetch_project', side_effect=OSError('network unavailable')), \
             patch.object(obj, 'execute', side_effect=AssertionError('mutation')), \
             contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaisesRegex(OSError, 'network unavailable'):
                obj.apply()
            record = json.loads((obj.state/'run.json').read_text())
            self.assertEqual(record['status'], 'FAILED')
            self.assertEqual(record['completed'], [])

    def test_failed_module_stops_later_modules_and_records_retry_state(self):
        obj = self.instance(['cleanup','locale','tools'])
        executed = []
        def execute(module):
            executed.append(module)
            if module == 'locale':
                raise RuntimeError('fixture failure')
        with tempfile.TemporaryDirectory() as temp, \
             patch.dict(os.environ, XDG_STATE_HOME=temp), patch.object(obj, 'preflight'), \
             patch.object(obj, 'prepare'), patch.object(obj, 'execute', side_effect=execute), \
             contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, 'fixture failure'):
                obj.apply()
            record = json.loads((obj.state/'run.json').read_text())
            self.assertEqual(executed, ['cleanup','locale'])
            self.assertEqual(record['completed'], ['cleanup'])
            self.assertEqual(record['current'], 'locale')

    def test_individual_tools_and_project_use_correct_entry_points(self):
        obj = self.instance(['fnm','uv','appearance','cleanup','docker'])
        obj.prepared['appearance'] = Path('/fixture/appearance')
        with patch.object(obj, 'run') as run, patch.object(obj, 'ensure_packages'):
            obj.execute('fnm')
            self.assertEqual(run.call_args.args[0][-2:], ['--only','fnm'])
            obj.execute('uv')
            self.assertEqual(run.call_args.args[0][-2:], ['--only','uv'])
            obj.execute('appearance')
            self.assertEqual(run.call_args.args[0][-2:], ['setup','--skip-deps'])
            obj.execute('cleanup')
            self.assertIn('--apply', run.call_args.args[0])
            self.assertIn(obj.profile, run.call_args.args[0])
            obj.execute('docker')
            self.assertEqual(run.call_args.args[0][-3:], ['true','true','true'])

    def test_apt_only_installs_missing_packages_and_updates_once(self):
        obj = self.instance(['tools'])
        query = subprocess.CompletedProcess([], 0, stdout='gnome-clocks ii \n', stderr='')
        with patch('subprocess.run', return_value=query), patch.object(obj, 'run') as run:
            obj.ensure_packages(['gnome-clocks', 'gnome-calendar'])
            obj.ensure_packages(['gnome-clocks', 'gnome-tweaks'])
        commands = [call.args[0] for call in run.call_args_list]
        self.assertEqual(commands.count(['sudo','apt-get','update']), 1)
        self.assertEqual(commands[1][-1], 'gnome-calendar')
        self.assertNotIn('gnome-clocks', commands[1])
        with self.assertRaises(ValueError):
            obj.ensure_packages(['--allow-unauthenticated'])

    def test_debian_appindicator_uses_distribution_uuid_and_preserves_other_extensions(self):
        obj = self.instance(['appindicator'])
        uuid = 'ubuntu-appindicators@ubuntu.com'
        def read(args):
            if args[0] == 'gnome-shell': return 'GNOME Shell 48.7'
            if args[-1] == 'enabled-extensions': return "['lunar-calendar@system.local']"
            return repr([uuid,'another-disabled-extension'])
        with patch.object(obj, 'read', side_effect=read), patch.object(obj, 'ensure_packages'), \
             patch.object(obj, 'setting') as setting, \
             patch.object(app, 'load', return_value={'uuid':uuid,'shell-version':['48']}):
            obj.execute('appindicator')
        values = {call.args[1]:call.args[2] for call in setting.call_args_list}
        self.assertIn('lunar-calendar@system.local', values['enabled-extensions'])
        self.assertIn(uuid, values['enabled-extensions'])
        self.assertEqual(values['disabled-extensions'], "['another-disabled-extension']")

    def test_calendar_clock_input_and_credentials_are_protected(self):
        spec = importlib.util.spec_from_file_location('cleanup_module', ROOT/'modules/cleanup.py')
        cleanup = importlib.util.module_from_spec(spec);spec.loader.exec_module(cleanup)
        config = self.edition['cleanup']
        keep = ['gnome-calendar','gnome-clocks','gnome-keyring','ibus-libpinyin','fonts-noto-cjk']
        self.assertEqual(cleanup.selection(dict.fromkeys(keep,'1'),config), [])
        for package in keep:
            with self.assertRaises(RuntimeError):
                cleanup.removal_plan('Remv '+package+' [1]\n',['evolution'],config)

    def test_weather_alone_generates_missing_chinese_locale_without_changing_user_language(self):
        obj = self.instance(['weather'])
        obj.prepared['weather'] = Path('/fixture/weather')
        with patch.object(obj, 'run') as run, patch.object(obj, 'ensure_packages') as packages, \
             patch.object(obj, 'read', return_value='C\nC.utf8\nen_US.utf8\n'):
            obj.execute('weather')
        self.assertIn('locales', packages.call_args.args[0])
        self.assertIn('--generate-only', run.call_args_list[0].args[0])
        self.assertEqual(run.call_args_list[1].args[0][-1], 'setup')
        with patch.object(obj, 'run') as run, patch.object(obj, 'ensure_packages'), \
             patch.object(obj, 'read', return_value='zh_CN.utf8\n'):
            obj.execute('weather')
        self.assertEqual(run.call_count, 1)

    def test_complete_pipeline_dispatches_all_modules_and_records_success(self):
        selected = list(app.MODULES)
        obj = self.instance(selected)
        for module in app.PROJECTS:
            obj.prepared[module] = Path('/fixture') / module
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, XDG_STATE_HOME=temp), \
             patch.object(obj, 'preflight'), patch.object(obj, 'prepare'), \
             patch.object(obj, 'ensure_packages'), patch.object(obj, 'run') as run, \
             patch.object(obj, 'configure_project'), patch.object(obj, 'deskflow') as deskflow, \
             patch.object(obj, 'locale') as locale, patch.object(obj, 'extension') as extension, \
             contextlib.redirect_stdout(io.StringIO()):
            obj.apply()
            record = json.loads((obj.state / 'run.json').read_text())
        self.assertEqual(record['completed'], selected)
        self.assertEqual(record['status'], 'READY')
        locale.assert_called_once()
        deskflow.assert_called_once()
        self.assertEqual([call.args[0] for call in extension.call_args_list], ['dock', 'appindicator'])
        self.assertEqual(run.call_count, 8)
