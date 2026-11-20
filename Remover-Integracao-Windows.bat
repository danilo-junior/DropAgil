@echo off
chcp 65001 >nul
cd /d "%~dp0"
if exist "%~dp0DropAgil.exe" (
  start /wait "" "%~dp0DropAgil.exe" --uninstall
  exit /b 0
)
python desktop.py --uninstall
pause
