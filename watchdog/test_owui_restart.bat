@echo off
title Test OWUI Watchdog Restart
echo ============================================================
echo Testing OWUI Restart Functionality
echo ============================================================
echo.
echo Step 1: Killing OWUI server to simulate failure...
tasklist | findstr /i "uvicorn" >nul
if %errorlevel% == 0 (
    echo Found uvicorn process, terminating...
    taskkill /F /IM uvicorn.exe >nul 2>&1
    timeout /t 3 /nobreak >nul
) else (
    echo OWUI was already down.
)

echo.
echo Step 2: Running watchdog (OWUI only)...
cd /d "C:\Users\blyth\Desktop\Engineering\Sky\watchdog"
python watchdog.py --only open-webui-server --only chat-tunnel

echo.
echo Step 3: Checking if OWUI restarted...
timeout /t 5 /nobreak >nul
curl -s -o nul -w "OWUI Status: %%{http_code}" http://127.0.0.1:3000/
echo.
echo.
echo ============================================================
echo Test Complete! Check watchdog_log.txt for details
echo ============================================================
pause
