@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title Restart Cloudflare Tunnel (Code)

echo [Sky Watchdog] Restarting Cloudflare Tunnel for Code...

set "CLOUDFLARED=C:\Program Files\cloudflared\cloudflared.exe"
set "CODE_TUNNEL_CONFIG=C:\Users\blyth\Desktop\Engineering\Code\config\cloudflared_config.yml"

REM Close existing Code tunnel windows by title (SURGICAL)
for /f "usebackq tokens=*" %%P in (`powershell -NoProfile -Command "Get-Process cmd -ErrorAction SilentlyContinue ^| Where-Object { $_.MainWindowTitle -match '^(Cloudflared|Code Tunnel)$' } ^| ForEach-Object { $_.Id }"`) do (
  echo  - Closing Code Tunnel window PID %%P
  taskkill /T /F /PID %%P >nul 2>&1
)

REM Kill cloudflared processes that belong to the code tunnel only
for /f "usebackq tokens=*" %%P in (`powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='cloudflared.exe'\" ^| Where-Object { $_.CommandLine -match 'c2bc21df-6083-4b52-b907-1996c611f010|code\\.alex-blythe\\.com' } ^| ForEach-Object { $_.ProcessId }"`) do (
  echo  - Killing cloudflared PID %%P (code tunnel)
  taskkill /F /PID %%P >nul 2>&1
)

timeout /t 2 /nobreak >nul

if not exist "%CLOUDFLARED%" (
  echo [X] cloudflared not found at %CLOUDFLARED%
  exit /b 1
)

if not exist "%CODE_TUNNEL_CONFIG%" (
  echo [X] Tunnel config not found at %CODE_TUNNEL_CONFIG%
  exit /b 1
)

echo [*] Launching Cloudflare Code Tunnel...
start "Cloudflared" cmd /k ^
  "%CLOUDFLARED%" tunnel --config "%CODE_TUNNEL_CONFIG%" run

echo [OK] Code tunnel restarted.
exit /b 0
