import ast
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import installer
from test_locales import locales

ROOT = Path(__file__).resolve().parents[1]


class ArchLocaleTests(unittest.TestCase):
    def instance(self):
        return installer.Installer(installer.load(ROOT/'profiles/arch.json'),
            installer.load(ROOT/'profiles/common.json'), ['locale'], ROOT/'profiles/arch.json')

    def test_arch_installs_missing_official_packages_without_refreshing_or_upgrading_system(self):
        obj = self.instance()
        with patch.object(obj,'read',side_effect=['ibus\nnoto-fonts-emoji\n','repo package info']) as read, \
             patch.object(obj,'run') as run:
            obj.ensure_packages(['ibus','ibus-libpinyin','noto-fonts-cjk','noto-fonts-emoji'])
        self.assertEqual(read.call_args_list[1].args[0], ['pacman','-Si','--','ibus-libpinyin','noto-fonts-cjk'])
        self.assertEqual(run.call_args.args[0], ['sudo','pacman','-S','--needed','--noconfirm','--','ibus-libpinyin','noto-fonts-cjk'])
        with patch.object(obj,'read',return_value='ibus\nibus-libpinyin\n'), patch.object(obj,'run') as run:
            obj.ensure_packages(['ibus','ibus-libpinyin'])
            run.assert_not_called()

    def test_input_sources_are_merged_and_existing_choices_survive_repeat_installation(self):
        obj = self.instance()
        for before in ["[('xkb', 'us'), ('xkb', 'de')]", "[('xkb', 'us'), ('ibus', 'libpinyin')]"]:
            with patch.object(obj,'read',return_value=before), patch.object(obj,'setting') as setting, \
                 patch.object(obj,'run') as run, patch.object(obj,'ensure_packages'):
                obj.locale()
            sources = ast.literal_eval(setting.call_args_list[-1].args[2])
            self.assertEqual(sources.count(('ibus','libpinyin')),1)
            self.assertEqual(sources.count(('xkb','us')),1)
            if "'de'" in before: self.assertIn(('xkb','de'),sources)
            self.assertIn(ROOT/'modules/locales-root.py',run.call_args.args[0])
            self.assertIn(ROOT/'profiles/arch.json',run.call_args.args[0])

    def test_arch_locale_generation_preserves_system_default_and_other_locales(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'etc').mkdir()
            (root/'etc/os-release').write_text('ID=arch\n')
            (root/'etc/locale.conf').write_text('LANG=en_US.UTF-8\n')
            target=root/'etc/locale.gen'
            original='en_US.UTF-8 UTF-8  \nfr_FR.UTF-8 UTF-8\n#zh_CN.UTF-8 UTF-8\n'
            target.write_text(original)
            profile=root/'arch.json';profile.write_text((ROOT/'profiles/arch.json').read_text())
            def filesystem(value):
                path=Path(value)
                return root/str(path).lstrip('/') if str(path).startswith(('/etc/','/var/')) else path
            with patch.object(locales,'Path',side_effect=filesystem), \
                 patch.object(locales.os,'geteuid',return_value=0), \
                 patch.object(locales.pwd,'getpwnam',return_value=SimpleNamespace(pw_uid=1000)), \
                 patch.object(locales.subprocess,'check_output',return_value='C\nen_US.utf8\nfr_FR.utf8\n'), \
                 patch.object(locales.subprocess,'run') as run, \
                 patch('sys.argv',['locales-root.py','--profile',str(profile),'--user','tester']):
                locales.main()
            self.assertIn('fr_FR.UTF-8 UTF-8',target.read_text())
            self.assertIn('en_US.UTF-8 UTF-8  ',target.read_text())
            self.assertIn('\nzh_CN.UTF-8 UTF-8\n',target.read_text())
            self.assertEqual((root/'etc/locale.conf').read_text(),'LANG=en_US.UTF-8\n')
            commands=[call.args[0] for call in run.call_args_list]
            self.assertEqual(commands[0],['locale-gen'])
            self.assertEqual(commands[-1][-3:],['SetLanguage','s','zh_CN.UTF-8'])
            backup=next((root/'var/backups/desktop-reinstall').glob('*/locale.gen'))
            self.assertEqual(backup.read_text(),original)

    def test_arch_locale_preflight_accepts_logged_in_gnome_session(self):
        obj=self.instance()
        obj.environment['DBUS_SESSION_BUS_ADDRESS']='unix:path=/fixture/bus'
        with patch.object(installer.platform,'freedesktop_os_release',return_value={'ID':'arch'}), \
             patch.object(installer.platform,'machine',return_value='x86_64'), \
             patch.object(installer.os,'geteuid',return_value=1000), \
             patch.object(installer.shutil,'which',return_value='/fixture/command'), \
             patch.object(obj,'read',return_value='GNOME Shell 51.1'):
            obj.preflight()
