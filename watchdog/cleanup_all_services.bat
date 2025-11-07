@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title Sky Watchdog - Cleanup All Services

echo [Sky Watchdog] NUCLEAR CLEANUP - Closing ALL CLI windows and service processes...

REM ============================================================================
REM NUCLEAR: Close ALL CMD windows except this one
REM ============================================================================
set "THIS_PID=%$"
for /f "usebackq tokens=*" %%P in (`powershell -NoProfile -Command "$thisPid = $PID; Get-Process cmd -ErrorAction SilentlyContinue ^| Where-Object { $_.Id -ne $thisPid -and $_.MainWindowTitle -ne '' } ^| ForEach-Object { $_.Id }"`) do (
  echo  - Closing CMD window PID %%P
  taskkill /T /F /PID %%P >nul 2>&1
)

REM ============================================================================
REM Kill processes by name (more aggressive)
REM ============================================================================
echo [*] Terminating stray processes...

REM Kill all cloudflared processes
tasklist | find /i "cloudflared.exe" >nul
if !errorlevel! == 0 (
  echo  - Killing all cloudflared processes
  taskkill /F /IM cloudflared.exe >nul 2>&1
)

REM Kill processes bound to specific ports
set "PORTS=8080 3000 5000"
for %%P in (%PORTS%) do (
  for /f "tokens=5" %%I in ('netstat -ano ^| findstr /R /C:":%%P " ^| findstr /I LISTENING') do (
    echo  - Freeing port %%P (PID %%I)
    taskkill /F /PID %%I >nul 2>&1
  )
)

timeout /t 2 /nobreak >nul

echo [OK] All services cleaned up.
exit /b 0
