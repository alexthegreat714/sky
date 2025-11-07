@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title Sky Watchdog - Continuous Monitor

set "WATCHDOG_SCRIPT=C:\Users\blyth\Desktop\Engineering\Sky\watchdog\watchdog.py"
set "INTERVAL_SECONDS=180"

echo ============================================================
echo Sky Watchdog - Continuous Monitoring
echo ============================================================
echo Script: %WATCHDOG_SCRIPT%
echo Check Interval: %INTERVAL_SECONDS% seconds (3 minutes)
echo Started: %DATE% %TIME%
echo ============================================================
echo.

:loop
    echo [%DATE% %TIME%] Running watchdog check...
    python "%WATCHDOG_SCRIPT%"

    if %errorlevel% neq 0 (
        echo [!] Watchdog detected issues (exit code: %errorlevel%)
    ) else (
        echo [OK] All checks passed
    )

    echo.
    echo Waiting %INTERVAL_SECONDS% seconds until next check...
    echo Press Ctrl+C to stop the watchdog
    echo.
    timeout /t %INTERVAL_SECONDS% /nobreak >nul
goto loop
