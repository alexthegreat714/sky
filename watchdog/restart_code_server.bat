@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title Restart Code Server (VS Code Web)

echo [Sky Watchdog] Restarting VS Code Web Server...

set "CODE_ROOT=C:\Users\blyth\Desktop\Engineering\Code"
set "PORT=8080"

REM Close any existing VS Code Server windows (SURGICAL)
for /f "usebackq tokens=*" %%P in (`powershell -NoProfile -Command "Get-Process cmd -ErrorAction SilentlyContinue ^| Where-Object { $_.MainWindowTitle -match '^(VS Code Web|VS Code Server|Code Server)$' } ^| ForEach-Object { $_.Id }"`) do (
  echo  - Closing VS Code Server window PID %%P
  taskkill /T /F /PID %%P >nul 2>&1
)

REM Free the port if held by stray processes
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":%PORT% " ^| findstr /I LISTENING') do (
  echo  - Terminating PID %%P bound to port %PORT%
  taskkill /F /PID %%P >nul 2>&1
)

timeout /t 2 /nobreak >nul

REM Start VS Code Web Server
set "VSCODE_CLI=%CODE_ROOT%\bin\vscode-cli\code.exe"

if exist "%VSCODE_CLI%" (
  echo [*] Launching VS Code Web on http://127.0.0.1:%PORT%...
  start "VS Code Web" "%VSCODE_CLI%" serve-web --host 127.0.0.1 --port %PORT% --server-data-dir "%CODE_ROOT%\userdata" --connection-token 610b6e847f3c85604b9e1269260964f3 --accept-server-license-terms
  echo [OK] VS Code Web Server restarted.
  exit /b 0
) else (
  echo [X] VS Code CLI not found at %VSCODE_CLI%
  exit /b 1
)
