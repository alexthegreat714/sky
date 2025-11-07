@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title Setup Sky Watchdog Scheduled Task

echo ============================================================
echo Sky Watchdog - Windows Task Scheduler Setup
echo ============================================================
echo.

set "WATCHDOG_SCRIPT=C:\Users\blyth\Desktop\Engineering\Sky\watchdog\watchdog.py"
set "TASK_NAME=SkyWatchdog"
set "INTERVAL_MINUTES=3"

echo Task Configuration:
echo - Task Name: %TASK_NAME%
echo - Script: %WATCHDOG_SCRIPT%
echo - Interval: Every %INTERVAL_MINUTES% minutes
echo - Start: At system startup
echo - Run as: Current user (%USERNAME%)
echo.

REM Check if task already exists
schtasks /Query /TN "%TASK_NAME%" >nul 2>&1
if %errorlevel% == 0 (
    echo [!] Task "%TASK_NAME%" already exists. Deleting...
    schtasks /Delete /TN "%TASK_NAME%" /F >nul 2>&1
    echo [OK] Old task deleted.
    echo.
)

echo [*] Creating scheduled task...
schtasks /Create ^
    /TN "%TASK_NAME%" ^
    /TR "python \"%WATCHDOG_SCRIPT%\"" ^
    /SC MINUTE ^
    /MO %INTERVAL_MINUTES% ^
    /F ^
    /RL HIGHEST

if %errorlevel% == 0 (
    echo.
    echo ============================================================
    echo [OK] Watchdog task created successfully!
    echo ============================================================
    echo.
    echo The watchdog will now run every %INTERVAL_MINUTES% minutes automatically.
    echo.
    echo Management Commands:
    echo   View task:     schtasks /Query /TN "%TASK_NAME%" /V /FO LIST
    echo   Run now:       schtasks /Run /TN "%TASK_NAME%"
    echo   Stop:          schtasks /End /TN "%TASK_NAME%"
    echo   Disable:       schtasks /Change /TN "%TASK_NAME%" /DISABLE
    echo   Enable:        schtasks /Change /TN "%TASK_NAME%" /ENABLE
    echo   Delete:        schtasks /Delete /TN "%TASK_NAME%" /F
    echo.
    echo Starting the task now for immediate execution...
    schtasks /Run /TN "%TASK_NAME%"
    echo.
    echo [OK] Watchdog is now running!
) else (
    echo.
    echo [X] Failed to create scheduled task.
    echo     Make sure you're running this as Administrator.
    exit /b 1
)

echo.
pause
