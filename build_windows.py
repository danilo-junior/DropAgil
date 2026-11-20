"""Build the portable desktop executable using official PyInstaller tooling."""
from pathlib import Path
import subprocess
import sys
import os
import ctypes

ROOT=Path(__file__).resolve().parent
environment=os.environ.copy()
if os.name=='nt' and not environment.get('USERPROFILE'):
    profile=ctypes.create_unicode_buffer(260)
    if ctypes.windll.shell32.SHGetFolderPathW(None,40,None,0,profile)==0:
        environment['USERPROFILE']=profile.value
environment['PYINSTALLER_CONFIG_DIR']=str(ROOT/'.work/pyinstaller-cache')
subprocess.run([sys.executable,'-m','PyInstaller','--noconfirm','--clean','--onefile','--windowed',
    '--name','DropAgil','--icon',str(ROOT/'public/dropagil.ico'),
    '--paths',str(ROOT/'vendor'),'--hidden-import','pystray._win32',
    '--add-data',str(ROOT/'public')+';public',
    '--distpath',str(ROOT),'--workpath',str(ROOT/'.work/windows-build'),
    '--specpath',str(ROOT/'.work/windows-build'),str(ROOT/'desktop.py')],cwd=ROOT,env=environment,check=True)
print(ROOT/'DropAgil.exe')
