@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title Launch Sky Watchdog (Detached)

set "WATCHDOG_SCRIPT=C:\Users\blyth\Desktop\Engineering\Sky\watchdog\watchdog.py"

echo ============================================================
echo Sky Watchdog - Detached Launch
echo ============================================================
echo.
echo This will run the watchdog once in a separate, detached process.
echo The watchdog will complete even if it restarts the Code server.
echo.
echo Script: %WATCHDOG_SCRIPT%
echo.

REM Run Python in a completely detached background process
start "" /B pythonw "%WATCHDOG_SCRIPT%"

echo [OK] Watchdog launched in background (detached process)
echo.
echo Check logs at: Sky\watchdog\watchdog_log.txt
echo Check status at: open-webui-full\backend\data\sky_watchdog\status.json
echo.
timeout /t 3 /nobreak
exit /b 0
