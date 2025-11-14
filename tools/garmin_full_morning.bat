@echo off
setlocal ENABLEDELAYEDEXPANSION
title Sky Garmin Full Morning Sweep
color 0A

rem ========= Paths =========
set "ROOT=C:\Users\blyth\Desktop\Engineering"
set "SKY=%ROOT%\Sky"
set "TOOLS=%SKY%\tools"
set "CLICK_PS1=%TOOLS%\garmin_click_replay.ps1"
set "REPORTER=%SKY%\agents\morning_reporter.py"
set "INBOX=%SKY%\downloads\garmin"
set "USERDL=%USERPROFILE%\Downloads"

if not exist "%CLICK_PS1%" (
  echo [error] Missing click script: %CLICK_PS1%
  goto :halt
)
if not exist "%REPORTER%" (
  echo [error] Missing reporter: %REPORTER%
  goto :halt
)
if not exist "%INBOX%" mkdir "%INBOX%"

rem ========= Date handling =========
set "ARG=%~1"
if "%ARG%"=="" set "ARG=YESTERDAY"

if /I "%ARG%"=="TODAY" (
  for /f "delims=" %%D in ('powershell -NoProfile -Command "(Get-Date).ToString('yyyy-MM-dd')"') do set "ISO=%%D"
) else if /I "%ARG%"=="YESTERDAY" (
  for /f "delims=" %%D in ('powershell -NoProfile -Command "(Get-Date).AddDays(-1).ToString('yyyy-MM-dd')"') do set "ISO=%%D"
) else (
  set "ISO=%ARG%"
)

rem ========= Lockfile =========
set "JOBS=%SKY%\jobs"
if not exist "%JOBS%" mkdir "%JOBS%"
set "LOCK=%JOBS%\morning_%ISO%.lock"
if exist "%LOCK%" (
  echo [skip] Morning sweep already ran for %ISO% (lock %LOCK% exists).
  goto :end
)
echo %DATE% %TIME% > "%LOCK%"

echo ----------------------------------------------------
echo Sky Garmin Full Morning Sweep
echo Target date : %ISO%
echo ----------------------------------------------------

rem ========= Step 1: Click replay =========
echo [1/3] Launching Garmin click replay…
powershell -NoProfile -ExecutionPolicy Bypass -File "%CLICK_PS1%" -When %ISO%
set "RC1=%ERRORLEVEL%"
echo [click] exit code %RC1%
if not "%RC1%"=="0" (
  echo [abort] Click replay failed.
  goto :halt
)
echo [info] Closing Chrome instance…
taskkill /IM chrome.exe /F >nul 2>&1

rem ========= Step 2: Stage CSV =========
echo [2/3] Staging downloaded CSV…
set "FOUND="
set "PATTERN=%USERDL%\sleep-%ISO%*.csv"
for /f "delims=" %%F in ('dir /b /a:-d /o:-d "%PATTERN%" 2^>nul') do if not defined FOUND set "FOUND=%%F"
if not defined FOUND if exist "%USERDL%\Sleep.csv" set "FOUND=Sleep.csv"

if not defined FOUND (
  echo [error] Could not find sleep-%ISO%*.csv or Sleep.csv in %USERDL%.
  goto :halt
)

for /f "delims=" %%T in ('powershell -NoProfile -Command "(Get-Date).ToString('yyyyMMdd_HHmmss')"') do set "STAMP=%%T"
set "SOURCE=%USERDL%\%FOUND%"
set "DEST=%INBOX%\sleep-%ISO%_Sky_%STAMP%.csv"

echo [copy] %SOURCE% --> %DEST%
copy /y "%SOURCE%" "%DEST%" >nul
if errorlevel 1 (
  echo [error] Failed to copy CSV.
  goto :halt
)
echo [stage] Staged file: %DEST%

rem ========= Step 3: Run reporter =========
echo [3/3] Running morning reporter…
set "SKY_GARMIN_TARGET_DATE=%ISO%"
set "PYEXE=%ROOT%\venv\Scripts\python.exe"

if exist "%PYEXE%" (
  set "RUNNER=%PYEXE%"
) else (
  set "RUNNER=python"
)

echo [run] %RUNNER% "%REPORTER%" --date %ISO%
%RUNNER% "%REPORTER%" --date %ISO%
set "RC3=%ERRORLEVEL%"

rem Correct OWUI digest path
set "REPORT_PATH=%ROOT%\open-webui-full\backend\data\sky_daily\%ISO%.json"

if exist "%REPORT_PATH%" (
  echo [path] Report saved at: %REPORT_PATH%
) else (
  echo [path] Report expected at: %REPORT_PATH%
)
echo [report] exit code %RC3%
if not "%RC3%"=="0" (
  echo [done] Reporter failed.
  goto :halt
)

echo [done] Sweep complete.
goto :end

:halt
if defined LOCK if exist "%LOCK%" del "%LOCK%" >nul 2>&1
echo [halt] Sweep aborted.

:end
echo.
echo (Press any key to close)
pause >nul
endlocal
