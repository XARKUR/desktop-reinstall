import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import installer

ROOT = Path(__file__).resolve().parents[1]


class ArchWorkflowTests(unittest.TestCase):
    def instance(self, selected):
        return installer.Installer(installer.load(ROOT/'profiles/arch.json'),
            installer.load(ROOT/'profiles/common.json'), selected, ROOT/'profiles/arch.json')

    def test_arch_docker_uses_distribution_helper_with_selected_components(self):
        obj=self.instance(['docker'])
        with patch.object(obj,'run') as run:
            obj.execute('docker')
        self.assertEqual(run.call_args.args[0][2],ROOT/'environment/install-docker-arch.sh')
        self.assertEqual(run.call_args.args[0][-3:],['true','true','true'])

    def test_project_dependencies_and_preferences_preserve_existing_user_settings(self):
        obj=self.instance(['lunar'])
        obj.prepared['lunar']=Path('/fixture/lunar')
        with tempfile.TemporaryDirectory() as data, patch.dict(os.environ,XDG_DATA_HOME=data), \
             patch.object(obj,'ensure_packages') as packages, patch.object(obj,'run'), \
             patch.object(obj,'setting') as setting:
            obj.execute('lunar')
        self.assertEqual(packages.call_args.args[0],['gjs','glib2'])
        self.assertTrue(any(call.args[1]=='show-ganzhi' for call in setting.call_args_list))
        with patch.object(obj,'setting') as setting:
            obj.configure_project('lunar',False)
            setting.assert_not_called()
        self.assertNotIn('gtk-engine-murrine',installer.ARCH_PROJECT_PACKAGES['appearance'])
        self.assertNotIn('gtk2-engines-murrine',installer.ARCH_PROJECT_PACKAGES['appearance'])

    def test_gpu_preferences_use_detected_devices_and_do_not_replace_existing_choices(self):
        obj=self.instance(['monitor'])
        detected={'devices':[{'version':2,'type':'gpu','device':'amd:card7','name':'Detected GPU','usage':True,'memory':True}], 'thermal':[]}
        with patch.object(obj,'read',side_effect=['@as []',json.dumps(detected)]) as read, \
             patch.object(obj,'setting') as setting:
            obj.configure_project('monitor',False)
        self.assertIn('Detected GPU',setting.call_args_list[0].args[2])
        self.assertIn('amd:card7',setting.call_args_list[0].args[2])
        self.assertEqual(read.call_count,2)
        with patch.object(obj,'read',return_value="['existing-device']") as read, patch.object(obj,'setting') as setting:
            obj.configure_project('monitor',False)
            setting.assert_not_called();self.assertEqual(read.call_count,1)

    def test_dock_install_backs_up_previous_copy_preserves_other_extensions_and_uses_local_schema(self):
        obj=self.instance(['dock'])
        uuid='dash-to-dock@micxgx.gmail.com'
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'source';source.mkdir();(source/'schemas').mkdir()
            meta={'uuid':uuid,'version':110,'shell-version':['51']}
            (source/'metadata.json').write_text(json.dumps(meta));(source/'extension.js').write_text('new extension')
            target=root/'data/gnome-shell/extensions'/uuid;target.mkdir(parents=True)
            (target/'metadata.json').write_text(json.dumps({**meta,'version':109}))
            (target/'extension.js').write_text('previous extension')
            obj.state=root/'state';obj.prepared['dock']=source
            def read(args):
                if args[0]=='gnome-shell':return 'GNOME Shell 51.1'
                if args[-1]=='enabled-extensions':return "['existing-extension']"
                if args[-1]=='disabled-extensions':return '@as []'
                raise AssertionError(args)
            with patch.dict(os.environ,XDG_DATA_HOME=str(root/'data')), patch.object(obj,'read',side_effect=read), \
                 patch.object(obj,'run'), patch.object(obj,'setting') as setting:
                obj.extension('dock')
            self.assertEqual((target/'extension.js').read_text(),'new extension')
            self.assertEqual((obj.state/'extensions'/uuid/'extension.js').read_text(),'previous extension')
            enable=setting.call_args_list[0].args[2];self.assertIn('existing-extension',enable);self.assertIn(uuid,enable)
            pressure=[call for call in setting.call_args_list if call.args[1]=='require-pressure-to-show'][0]
            self.assertEqual(pressure.args[2],'false');self.assertEqual(pressure.kwargs['schema_dir'],target/'schemas')
