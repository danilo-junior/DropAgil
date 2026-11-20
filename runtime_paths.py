"""Writable application files stay beside the executable; bundled assets are read-only."""
from pathlib import Path
import sys
import os

FROZEN = bool(getattr(sys, 'frozen', False))
BASE = Path(sys.executable).resolve().parent if FROZEN else Path(__file__).resolve().parent
RESOURCES = Path(__file__).resolve().parent


def desktop_command(*args):
    if FROZEN:
        return [sys.executable, *args]
    return [str(Path(sys.executable).with_name('pythonw.exe')), str(BASE / 'desktop.py'), *args]


def server_command():
    return desktop_command('--server')


def child_environment():
    env = os.environ.copy()
    if FROZEN: env['PYINSTALLER_RESET_ENVIRONMENT'] = '1'
    return env
