import contextlib
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import plan

ROOT = Path(__file__).resolve().parents[1]


class ArchPreviewTests(unittest.TestCase):
    def setUp(self):
        self.profile = json.loads((ROOT / 'profiles/arch.json').read_text())

    def test_calendar_and_clocks_never_become_removal_targets(self):
        with patch.object(plan, 'read_command', return_value='gnome-calendar\ngnome-clocks\ngnome-shell\n') as read, \
             contextlib.redirect_stdout(io.StringIO()):
            plan.preview_cleanup(self.profile)
        self.assertEqual(read.call_count, 1)
        self.assertEqual(read.call_args.args[0], ['pacman', '-Qq'])
        self.assertTrue({'gnome-calendar', 'gnome-clocks'} <= set(self.profile['cleanup']['protect']))

    def test_current_players_are_previewed_without_recursive_or_cascade_removal(self):
        installed = 'gnome-calendar\ngnome-clocks\nshowtime\ndecibels\nmalcontent\nlibmalcontent\ntecla\n'
        with patch.object(plan, 'read_command', side_effect=[installed, 'decibels\nmalcontent\nshowtime\n']) as read, \
             contextlib.redirect_stdout(io.StringIO()) as output:
            plan.preview_cleanup(self.profile)
        self.assertEqual(read.call_args.args[0], ['pacman', '-Rp', '--print-format', '%n', '--', 'decibels', 'malcontent', 'showtime'])
        self.assertIn('模拟删除 3 项', output.getvalue())

    def test_unexpected_and_protected_removals_are_rejected(self):
        for extra in ('gnome-shell', 'unknown-dependent'):
            with self.subTest(extra=extra), \
                 patch.object(plan, 'read_command', side_effect=['showtime\ngnome-shell\n', 'showtime\n'+extra+'\n']), \
                 contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(ValueError, '模拟结果与清单不符'):
                    plan.preview_cleanup(self.profile)
