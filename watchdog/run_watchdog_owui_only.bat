@echo off
setlocal
chcp 65001 >nul
title Sky Watchdog (OWUI Only)

set "WATCHDOG_DIR=%~dp0"
pushd "%WATCHDOG_DIR%"

echo ============================================================
echo Sky Watchdog - Open WebUI / Chat Tunnel (manual run)
echo ============================================================
echo.
echo This run checks ONLY the Open WebUI server and chat tunnel,
echo skipping code-server, ping, LLM, and Garmin checks.
echo.

py -3 "%WATCHDOG_DIR%watchdog.py" ^
    --only open-webui-server ^
    --only chat-tunnel ^
    --no-llm ^
    --no-ping ^
    --no-garmin

set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (
    echo [OK] Watchdog completed without critical failures.
) else (
    echo [WARN] Watchdog reported issues. Exit code: %RC%
)

popd
endlocal
exit /b %RC%

