import builtins
import contextlib
import io
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
code=(ROOT/'install.sh').read_text().split("<<'PYBOOTSTRAP'\n",1)[1].split('\nPYBOOTSTRAP',1)[0]
scope={'__name__':'bootstrap_test'}
exec(compile(code,'install.sh bootstrap','exec'),scope)
bootstrap=scope['main']


def archive(name='desktop-reinstall-main/installer.py',kind=tarfile.REGTYPE):
    data=io.BytesIO()
    with tarfile.open(fileobj=data,mode='w:gz') as source:
        member=tarfile.TarInfo(name);member.mode=0o755;member.type=kind
        if kind==tarfile.REGTYPE:
            content=b'# fixture installer';member.size=len(content);source.addfile(member,io.BytesIO(content))
        else:
            member.linkname='/tmp/escape';source.addfile(member)
    return data.getvalue()


class BootstrapTests(unittest.TestCase):
    def run_bootstrap(self, release, arguments, data=None, tty=True):
        terminal=io.StringIO('q\n')
        original_open=builtins.open
        def open_file(path,*args,**kwargs):
            if path=='/dev/tty':
                if not tty:raise OSError('no tty')
                return terminal
            return original_open(path,*args,**kwargs)
        with tempfile.TemporaryDirectory() as temp, \
             patch('os.geteuid',return_value=1000), \
             patch('platform.freedesktop_os_release',return_value=release), \
             patch('platform.machine',return_value='x86_64'), \
             patch('builtins.open',side_effect=open_file), \
             patch('urllib.request.urlopen',return_value=io.BytesIO(archive() if data is None else data)) as fetch, \
             patch('subprocess.run',return_value=subprocess.CompletedProcess([],7)) as run, \
             contextlib.redirect_stdout(io.StringIO()):
            result=bootstrap(Path(temp),arguments)
            calls=run.call_args
            self.assertTrue(Path(calls.args[0][1]).is_file())
        return result,calls,terminal

    def test_debian_and_arch_pass_terminal_stdin_to_downloaded_menu(self):
        for release in [{'ID':'debian','VERSION_ID':'13'},{'ID':'arch'}]:
            with self.subTest(release=release):
                result,call,terminal=self.run_bootstrap(release,['--menu'])
                self.assertEqual(result,7)
                self.assertEqual(call.args[0][-1],'--menu')
                self.assertIs(call.kwargs['stdin'],terminal)
                self.assertTrue(terminal.closed)

    def test_noninteractive_plan_uses_devnull_without_a_terminal(self):
        _,call,_=self.run_bootstrap({'ID':'arch'},['--plan','--only','lunar'],tty=False)
        self.assertEqual(call.kwargs['stdin'],subprocess.DEVNULL)
        self.assertEqual(call.args[0][-3:],['--plan','--only','lunar'])

    def test_wrong_system_and_missing_terminal_reject_before_downloading(self):
        for release,tty in [({'ID':'debian','VERSION_ID':'12'},True),({'ID':'arch'},False)]:
            with self.subTest(release=release,tty=tty), \
                 patch('urllib.request.urlopen',side_effect=AssertionError('network')):
                with self.assertRaises(ValueError):
                    # Keep the external network assertion active; no archive can be fetched.
                    with patch('os.geteuid',return_value=1000), patch('platform.machine',return_value='x86_64'), \
                         patch('platform.freedesktop_os_release',return_value=release), \
                         patch('builtins.open',side_effect=OSError('no tty')):
                        bootstrap(Path('/unused'),['--menu'])

    def test_archive_traversal_and_links_cannot_launch_installer(self):
        for data in [archive('../escape'),archive('/absolute'),archive('desktop-reinstall-main/link',tarfile.SYMTYPE)]:
            with self.subTest(data=data[:10]), self.assertRaises(ValueError):
                self.run_bootstrap({'ID':'arch'},['--menu'],data=data)

    def test_streamed_shell_defaults_to_menu_and_cleans_stage_on_child_failure(self):
        import os
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);binary=root/'bin';binary.mkdir();downloads=root/'downloads';downloads.mkdir()
            arguments=root/'args.txt'
            fake=binary/'python3'
            fake.write_text('#!/bin/sh\nprintf \'%s\\n\' "$@" > "$BOOTSTRAP_TEST_ARGS"\nexit 23\n')
            fake.chmod(0o755)
            env=dict(os.environ,PATH=str(binary)+os.pathsep+os.environ.get('PATH',''),
                     TMPDIR=str(downloads),BOOTSTRAP_TEST_ARGS=str(arguments))
            result=subprocess.run(['/bin/sh'],input=(ROOT/'install.sh').read_text(),text=True,
                                  env=env,capture_output=True,cwd=root)
            self.assertEqual(result.returncode,23)
            self.assertEqual(arguments.read_text().splitlines()[-1],'--menu')
            self.assertEqual(list(downloads.iterdir()),[])
