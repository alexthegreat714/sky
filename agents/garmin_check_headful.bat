@echo off
setlocal
cd /d %~dp0
echo.
echo Garmin Sleep Downloader - Visual Login Check (headful)
echo.
python "%~dp0garmin_sleep_downloader.py" --check-only --no-headless
echo.
echo The script printed status and saved a screenshot in the downloads folder.
echo Press any key to exit.
pause >nul

