import hashlib
import io
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import installer
from sources import fetch_deb

ROOT=Path(__file__).resolve().parents[1]


class DeskflowTests(unittest.TestCase):
    def instance(self,edition='debian13'):
        return installer.Installer(installer.load(ROOT/'profiles'/f'{edition}.json'),
            installer.load(ROOT/'profiles/common.json'),['deskflow'],ROOT/'profiles'/f'{edition}.json')

    def test_deskflow_is_menu_item_13_and_in_apps_and_defaults(self):
        obj=self.instance()
        self.assertEqual(installer.menu_selection('13'),{'deskflow'})
        self.assertIn('deskflow',installer.select_modules(obj.common))
        self.assertIn('deskflow',installer.select_modules(obj.common,'apps'))

    def test_arch_uses_official_package_without_debian_download(self):
        obj=self.instance('arch')
        with patch.object(obj,'ensure_packages') as packages, patch.object(obj,'run') as run:
            obj.execute('deskflow')
        packages.assert_called_once_with(['deskflow']);run.assert_not_called()

    def test_existing_debian_version_is_compared_without_downgrading(self):
        obj=self.instance();config=obj.common['system_apps']['Deskflow']['debian13']
        query=subprocess.CompletedProcess([],0,stdout='1.28.0 hi ')
        comparison=subprocess.CompletedProcess([],0,stdout='')
        with patch('subprocess.run',side_effect=[query,comparison]) as run:
            self.assertTrue(obj.deskflow_satisfied(config))
        self.assertEqual(run.call_args.args[0],['dpkg','--compare-versions','1.28.0','ge',config['version']])
        with patch.object(obj,'deskflow_satisfied',return_value=True), patch.object(obj,'ensure_packages') as packages, patch.object(obj,'run') as run:
            obj.execute('deskflow');run.assert_not_called();packages.assert_called_once_with(['qt6-wayland'])

    def test_missing_debian_package_is_prepared_and_metadata_checked_before_installing(self):
        obj=self.instance();config=obj.common['system_apps']['Deskflow']['debian13']
        with tempfile.TemporaryDirectory() as temp, patch.object(obj,'deskflow_satisfied',return_value=False), \
             patch('installer.fetch_deb',return_value=Path(temp)/'deskflow.deb') as fetch, \
             patch.object(obj,'read',side_effect=[config['package'],config['version'],config['architecture']]), \
             patch.object(obj,'run',side_effect=AssertionError('mutation')):
            obj.prepare(temp)
            self.assertEqual(obj.prepared['deskflow'],Path(temp)/'deskflow.deb')
            fetch.assert_called_once()
        with tempfile.TemporaryDirectory() as temp, patch.object(obj,'deskflow_satisfied',return_value=False), \
             patch('installer.fetch_deb',return_value=Path(temp)/'deskflow.deb'), \
             patch.object(obj,'read',side_effect=[config['package'],config['version'],'arm64']):
            with self.assertRaisesRegex(ValueError,'架构不符'):obj.prepare(temp)

    def test_debian_install_uses_verified_cache_and_prevents_package_removal(self):
        obj=self.instance();obj.prepared['deskflow']=Path('/fixture/deskflow.deb')
        with patch.object(obj,'deskflow_satisfied',return_value=False), patch.object(obj,'run') as run:
            obj.execute('deskflow')
        commands=[call.args[0] for call in run.call_args_list]
        self.assertEqual(commands[0][:5],['sudo','install','-D','-m','0644'])
        self.assertIn('--no-remove',commands[-1])
        self.assertEqual(commands[-1][-2].parent,Path('/var/cache/apt/archives'))
        self.assertEqual(commands[-1][-1],'qt6-wayland')
        with patch.object(obj,'deskflow_satisfied',return_value=False), patch.object(obj,'run') as run:
            obj.prepared.clear()
            with self.assertRaisesRegex(RuntimeError,'状态在准备后发生变化'):obj.execute('deskflow')
            run.assert_not_called()

    def test_preparation_skips_download_for_already_installed_debian_package(self):
        obj=self.instance()
        with tempfile.TemporaryDirectory() as temp, patch.object(obj,'deskflow_satisfied',return_value=True), \
             patch('installer.fetch_deb',side_effect=AssertionError('download')):
            obj.prepare(temp)
            self.assertNotIn('deskflow',obj.prepared)

    def test_asset_checksum_and_cache_reuse(self):
        content=b'fixture deb'
        config={'url':'https://github.com/deskflow/deskflow/releases/download/v1.27.0/test.deb',
                'sha256':hashlib.sha256(content).hexdigest()}
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            with patch('urllib.request.urlopen',return_value=io.BytesIO(content)):
                fetch_deb(config,root/'first.deb',root/'cache')
            with patch('urllib.request.urlopen',side_effect=AssertionError('network')):
                fetch_deb(config,root/'second.deb',root/'cache')
            self.assertEqual((root/'second.deb').read_bytes(),content)
            config['sha256']='0'*64
            with patch('urllib.request.urlopen',return_value=io.BytesIO(content)):
                with self.assertRaisesRegex(ValueError,'SHA256'):fetch_deb(config,root/'bad.deb',root/'cache')
            self.assertFalse((root/'bad.deb').exists())
