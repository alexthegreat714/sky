@echo off
setlocal
cd /d %~dp0
echo.
echo Garmin Sleep Downloader - First-time Login
echo.
echo This opens Chrome with a persistent Sky profile.
echo Sign in to Garmin and complete MFA, then close the window.
echo.
python "%~dp0garmin_sleep_downloader.py" --init-login
echo.
echo When finished logging in and closing Chrome, press any key to exit.
pause >nul

