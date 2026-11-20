@echo off
chcp 65001 >nul
cd /d "%~dp0"
if exist "%~dp0DropAgil.exe" (
  start /wait "" "%~dp0DropAgil.exe" --install
  start "" "%~dp0DropAgil.exe"
  exit /b 0
)
python -m pip install -r requirements.txt
if errorlevel 1 goto :error
python desktop.py --install
if errorlevel 1 goto :error
start "" pythonw "%~dp0desktop.py" --background
echo DropAgil instalado. Procure o icone perto do relogio.
echo No Windows 11, a opcao pode ficar em Mostrar mais opcoes.
pause
exit /b 0
:error
echo A instalacao nao terminou. Confira a mensagem acima.
pause
exit /b 1
