@echo off
setlocal
set "ROOT=C:\Users\blyth\Desktop\Engineering\Sky"
set "PARENT=C:\Users\blyth\Desktop\Engineering"
title Sky Flask Launcher
color 0A

echo ----------------------------------------------------
echo Sky Flask Launcher
echo Root: %ROOT%
echo ----------------------------------------------------
cd /d "%ROOT%"

set "PYEXE=%ROOT%\venv\Scripts\python.exe"
if exist "%PYEXE%" (
set "RUNNER=%PYEXE%"
) else (
  set "RUNNER=python"
)

set "PYTHONPATH=%PARENT%;%PYTHONPATH%"
echo [env] PYTHONPATH=%PYTHONPATH%
echo [run] %RUNNER% -m Sky.app
%RUNNER% -m Sky.app
set "RC=%ERRORLEVEL%"
echo [exit] Flask process ended with code %RC%
echo (Press any key to close)
pause >nul
exit /b %RC%
