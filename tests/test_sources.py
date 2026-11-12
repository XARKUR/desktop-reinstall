import io
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from sources import fetch_project

PROJECT = {'repository':'example/project','commit':'a'*40}


def archive(name='project-main/project.py', kind=tarfile.REGTYPE):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream,mode='w:gz') as tar:
        member=tarfile.TarInfo(name);member.type=kind
        if kind==tarfile.REGTYPE:
            data=b'# fixture';member.size=len(data);tar.addfile(member,io.BytesIO(data))
        else:
            member.linkname='/tmp/escape';tar.addfile(member)
    return stream.getvalue()


class SourceTests(unittest.TestCase):
    def test_valid_pinned_source_and_cache_reuse(self):
        data=archive()
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            with patch('urllib.request.urlopen',return_value=io.BytesIO(data)) as request:
                first=fetch_project(PROJECT,root/'first',root/'cache')
            self.assertIn('a'*40, request.call_args.args[0].full_url)
            self.assertEqual((first/'project.py').read_bytes(),b'# fixture')
            with patch('urllib.request.urlopen',side_effect=AssertionError('network')):
                second=fetch_project(PROJECT,root/'second',root/'cache')
            self.assertTrue((second/'project.py').is_file())

    def test_traversal_and_link_archives_are_rejected(self):
        for name,kind in [('../escape',tarfile.REGTYPE),('/absolute',tarfile.REGTYPE),
                          ('project-main/link',tarfile.SYMTYPE)]:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp:
                with patch('urllib.request.urlopen',return_value=io.BytesIO(archive(name,kind))):
                    with self.assertRaises(ValueError):
                        fetch_project(PROJECT,Path(temp)/'source',Path(temp)/'cache')

    def test_corrupted_cache_is_downloaded_again(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);cache=root/'cache';cache.mkdir()
            key='example-project-'+'a'*40
            (cache/(key+'.tar.gz')).write_bytes(b'corrupted')
            (cache/(key+'.sha256')).write_text('invalid')
            with patch('urllib.request.urlopen',return_value=io.BytesIO(archive())) as request:
                fetch_project(PROJECT,root/'source',cache)
            request.assert_called_once()

    def test_repository_and_commit_validation_happens_before_writes(self):
        with patch.object(Path,'mkdir',side_effect=AssertionError('write')):
            with self.assertRaises(ValueError):
                fetch_project({'repository':'https://wrong.example/repo','commit':'main'},Path('/fixture'),Path('/cache'))


class ExtensionSourceTests(unittest.TestCase):
    def test_extension_is_checksum_pinned_and_rejects_paths_or_incompatible_shell(self):
        import hashlib,json,zipfile
        from sources import fetch_extension
        uuid='test@example.org'
        for member,versions,valid in [('extension.js',['51'],True),('../escape',['51'],False),('extension.js',['48'],False)]:
            output=io.BytesIO()
            with zipfile.ZipFile(output,'w') as archive:
                archive.writestr('metadata.json',json.dumps({'uuid':uuid,'version':1,'shell-version':versions}))
                archive.writestr(member,'fixture')
            data=output.getvalue()
            config={'url':'https://extensions.gnome.org/download-extension/test.zip?version_tag=1','version':1,'sha256':hashlib.sha256(data).hexdigest()}
            with tempfile.TemporaryDirectory() as temp, patch('urllib.request.urlopen',return_value=io.BytesIO(data)):
                root=Path(temp)
                if valid:
                    self.assertEqual(fetch_extension(config,uuid,'51',root/'source',root/'cache'),root/'source')
                    self.assertTrue((root/'source/extension.js').is_file())
                else:
                    with self.assertRaises(ValueError):fetch_extension(config,uuid,'51',root/'source',root/'cache')
