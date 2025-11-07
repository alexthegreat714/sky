@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title Restart Cloudflare Tunnel (Chat/OWUI)

echo [Sky Watchdog] Restarting Cloudflare Tunnel for Chat...

set "CLOUDFLARED=C:\Program Files\cloudflared\cloudflared.exe"
set "CHAT_TUNNEL_CONFIG=%USERPROFILE%\.cloudflared\config.yml"

REM Close existing Chat tunnel windows by title (SURGICAL)
for /f "usebackq tokens=*" %%P in (`powershell -NoProfile -Command "Get-Process cmd -ErrorAction SilentlyContinue ^| Where-Object { $_.MainWindowTitle -match '^(Chat Tunnel|Sky Tunnel)$' } ^| ForEach-Object { $_.Id }"`) do (
  echo  - Closing Chat Tunnel window PID %%P
  taskkill /T /F /PID %%P >nul 2>&1
)

REM Kill cloudflared processes that belong to the chat tunnel only (sky-tunnel)
for /f "usebackq tokens=*" %%P in (`powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='cloudflared.exe'\" ^| Where-Object { $_.CommandLine -match 'sky-tunnel|chat\\.alex-blythe\\.com' } ^| ForEach-Object { $_.ProcessId }"`) do (
  echo  - Killing cloudflared PID %%P (chat tunnel)
  taskkill /F /PID %%P >nul 2>&1
)

timeout /t 2 /nobreak >nul

if not exist "%CLOUDFLARED%" (
  echo [X] cloudflared not found at %CLOUDFLARED%
  exit /b 1
)

if not exist "%CHAT_TUNNEL_CONFIG%" (
  echo [X] Tunnel config not found at %CHAT_TUNNEL_CONFIG%
  exit /b 1
)

echo [*] Launching Cloudflare Chat Tunnel...
start "Chat Tunnel" cmd /k ^
  "%CLOUDFLARED%" tunnel --config "%CHAT_TUNNEL_CONFIG%" run sky-tunnel

echo [OK] Chat tunnel restarted.
exit /b 0
