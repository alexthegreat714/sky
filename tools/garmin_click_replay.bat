@echo off
setlocal
set "SCRIPT=C:\Users\blyth\Desktop\Engineering\Sky\tools\garmin_click_replay.ps1"
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT%" %*
echo.
echo (Press any key to close)
pause >nul
