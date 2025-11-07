@echo off
setlocal ENABLEEXTENSIONS ENABLEDELAYEDEXECUTION
cd /d %~dp0
title Garmin Sleep Downloader – Guided Setup

:menu
cls
echo ======================================================
echo  Garmin Sleep Downloader – Guided Setup / Runner
echo ======================================================
echo  This wizard helps you:
echo   1) Persist login (one-time)
echo   2) Verify login and page access (headful)
echo   3) List click candidates (3-dots and CSV)
echo   4) Edit selectors JSON for precise clicks
echo   5) Test download for a specific date (headful)
echo   6) Download yesterday (headless)
echo ------------------------------------------------------
echo  Memory paths:
echo    Profile:   C:\Users\blyth\AppData\Local\Sky\profiles\garmin
echo    Downloads: C:\Users\blyth\Desktop\Engineering\Sky\downloads\garmin
echo    Selectors: %~dp0garmin_selectors.json
echo ======================================================
echo.
echo  1^) One-time login (opens Chrome)
echo  2^) Visual login check (headful)
echo  3^) Print click candidates (headful)
echo  4^) Select clicks (opens yesterday headful; click 3-dots then CSV)
echo  5^) Test download for date (headful)
echo  6^) Download yesterday (headless)
echo  7^) Exit
echo.
set /p opt=Select option [1-7]: 

if "%opt%"=="1" goto login
if "%opt%"=="2" goto check
if "%opt%"=="3" goto candidates
if "%opt%"=="4" goto selectflow
if "%opt%"=="5" goto testdate
if "%opt%"=="6" goto yesterday
if "%opt%"=="7" goto end
goto menu

:login
echo.
echo Opening Chrome to Garmin Connect. Sign in and complete MFA, then close the window.
python "%~dp0garmin_sleep_downloader.py" --init-login
echo.
pause
goto menu

:check
set "DATE="
echo.
set /p DATE=Enter date YYYY-MM-DD (leave blank for yesterday): 
echo.
if "%DATE%"=="" (
  python "%~dp0garmin_sleep_downloader.py" --check-only --no-headless
) else (
  python "%~dp0garmin_sleep_downloader.py" --check-only --no-headless --date %DATE%
)
echo.
echo If CHECK says LOGIN_REQUIRED, run option 1 (One-time login) again.
pause
goto menu

:candidates
set "DATE="
echo.
set /p DATE=Enter date YYYY-MM-DD (leave blank for yesterday): 
echo.
if "%DATE%"=="" (
  python "%~dp0garmin_sleep_downloader.py" --print-candidates --no-headless
) else (
  python "%~dp0garmin_sleep_downloader.py" --print-candidates --no-headless --date %DATE%
)
echo.
echo Copy useful labels from the console into garmin_selectors.json (option 4).
pause
goto menu

:selectflow
echo.
echo This opens yesterday's sleep page headfully.
echo Click the 3-dots/options button in the Chrome window, then the CSV item.
echo The wizard captures your clicks, prints attributes, and writes garmin_selectors.json.
echo.
python "%~dp0garmin_sleep_downloader.py" --capture-clicks --no-headless
echo.
echo If needed, you can still fine-tune selectors later in garmin_selectors.json.
pause
goto menu

:testdate
set "DATE="
echo.
set /p DATE=Enter date YYYY-MM-DD (required): 
if "%DATE%"=="" goto testdate
echo.
python "%~dp0garmin_sleep_downloader.py" --no-headless --date %DATE%
echo.
echo If no file downloaded, refine selectors (option 3 then 4) and retry.
pause
goto menu

:yesterday
echo.
python "%~dp0garmin_sleep_downloader.py"
echo.
echo Check the downloads folder for the saved file.
pause
goto menu

:end
endlocal
exit /b 0
