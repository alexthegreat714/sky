@echo off
setlocal
cd /d %~dp0
echo.
echo Garmin Sleep Downloader - Yesterday (headless)
echo.
python "%~dp0garmin_sleep_downloader.py"
echo.
echo Done. Press any key to exit.
pause >nul

