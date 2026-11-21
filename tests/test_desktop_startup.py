"""Startup registration respects a user's explicit opt-out."""
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import MagicMock, patch

import desktop


class StartupTests(unittest.TestCase):
    def test_first_launch_registers_and_existing_entry_does_not_repeat(self):
        registry = types.SimpleNamespace(HKEY_CURRENT_USER=1, OpenKey=MagicMock(), QueryValueEx=MagicMock())
        registry.OpenKey.side_effect = FileNotFoundError
        with tempfile.TemporaryDirectory() as temporary, \
             patch.object(desktop, 'AUTOSTART_DISABLED', Path(temporary) / 'startup-disabled'), \
             patch.dict(sys.modules, {'winreg': registry}), \
             patch.object(desktop, 'install') as install:
            desktop.ensure_autostart()
            install.assert_called_once_with()
            install.reset_mock()
            registry.OpenKey.side_effect = None
            registry.QueryValueEx.return_value = (desktop.subprocess.list2cmdline(desktop.desktop_command('--background')), 1)
            desktop.ensure_autostart()
            install.assert_not_called()

    def test_opt_out_prevents_registration(self):
        with tempfile.TemporaryDirectory() as temporary, \
             patch.object(desktop, 'AUTOSTART_DISABLED', Path(temporary) / 'startup-disabled') as disabled, \
             patch.object(desktop, 'install') as install:
            disabled.write_text('disabled by user', encoding='utf-8')
            desktop.ensure_autostart()
            install.assert_not_called()


if __name__ == '__main__':
    unittest.main()
