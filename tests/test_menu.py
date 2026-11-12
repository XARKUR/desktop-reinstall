import contextlib
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import installer

ROOT=Path(__file__).resolve().parents[1]


class MenuTests(unittest.TestCase):
    def setUp(self):
        self.edition=installer.load(ROOT/'profiles/arch.json')
        self.common=installer.load(ROOT/'profiles/common.json')

    def menu(self, text, **kwargs):
        captured=[]
        def apply(obj):captured.append(obj.selected)
        with patch.object(installer.Installer,'preflight'), \
             patch.object(installer.Installer,'apply',apply), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            code=installer.run_menu(self.edition,self.common,ROOT/'profiles/arch.json',terminal=io.StringIO(text),**kwargs)
        return code,captured,output.getvalue()

    def test_numbers_ranges_names_and_groups(self):
        self.assertEqual(installer.menu_selection('1，2 7-9'),{'cleanup','locale','appearance','weather','lunar'})
        self.assertEqual(installer.menu_selection('fnm, extensions'),{'fnm','lunar','monitor','dock','appindicator'})
        for invalid in ['0','13','4-2','1,not-a-module','1;echo danger']:
            with self.assertRaises(ValueError):installer.menu_selection(invalid)

    def test_preview_and_toggle_install_only_final_selection_in_canonical_order(self):
        code,calls,output=self.menu('4-6\np\n4\n9\ni\n')
        self.assertEqual(code,0)
        self.assertEqual(calls,[['fnm','uv','lunar']])
        self.assertIn('仅预览，未执行安装',output)

    def test_cancel_empty_input_and_invalid_choices_never_install(self):
        for text in ['q\n','','i\nq\n','1 invalid\np\nq\n']:
            with self.subTest(text=text):
                _,calls,_=self.menu(text)
                self.assertEqual(calls,[])

    def test_clear_and_explicit_exclusions_are_respected(self):
        self.assertEqual(self.menu('r\nc\n9\ni\n')[1],[['lunar']])
        _,calls,output=self.menu('4\np\ni\n',only='environment',skip='docker')
        self.assertEqual(calls,[['fnm','uv']])
        self.assertIn('--skip 已排除',output)

    def test_no_controlling_terminal_is_an_error_not_a_read_from_piped_stdin(self):
        with patch.object(installer.Installer,'preflight'), \
             patch('builtins.open',side_effect=OSError('no tty')), \
             patch('sys.stdin',io.StringIO('i\n')):
            with self.assertRaisesRegex(ValueError,'需要终端'):
                installer.run_menu(self.edition,self.common,ROOT/'profiles/arch.json')
