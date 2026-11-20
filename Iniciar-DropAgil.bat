@echo off
chcp 65001 >nul
cd /d "%~dp0"
title DropAgil - Central de arquivos
where python >nul 2>nul
if errorlevel 1 (
  echo Instale o Python 3.11 ou superior, marcando "Add Python to PATH".
  echo Depois abra este arquivo novamente.
  pause
  exit /b 1
)
echo Abrindo DropAgil na bandeja do Windows...
start "" pythonw "%~dp0desktop.py"
