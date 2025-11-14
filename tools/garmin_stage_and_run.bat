@echo off
setlocal ENABLEDELAYEDEXPANSION
title Sky Garmin Stage + Run (DEBUG)
color 0A

rem ========= Paths =========
set "ROOT=C:\Users\blyth\Desktop\Engineering"
set "SKY=%ROOT%\Sky"
set "INBOX=%SKY%\downloads\garmin"
set "USERDL=%USERPROFILE%\Downloads"
set "REPORTER=%SKY%\agents\morning_reporter.py"
set "DIGEST_DIR=%ROOT%\open-webui-full\backend\data\sky_daily"

if not exist "%INBOX%" mkdir "%INBOX%"

if not exist "%REPORTER%" (
  echo [error] Missing reporter: %REPORTER%
  goto :done
)

echo =====================================================
echo Sky Garmin Manual Stage + Morning Reporter (DEBUG)
echo ROOT      = %ROOT%
echo SKY       = %SKY%
echo INBOX     = %INBOX%
echo DOWNLOADS = %USERDL%
echo =====================================================
echo.

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

echo [info] Target date (ISO) = %ISO%
echo.

rem ========= Step 1: Stage CSV =========
echo [1/2] Looking for Garmin CSV in "%USERDL%"...

set "FOUND="
set "PATTERN=%USERDL%\sleep-%ISO%*.csv"

for /f "delims=" %%F in ('dir /b /a:-d /o:-d "%PATTERN%" 2^>nul') do (
  if not defined FOUND set "FOUND=%%F"
)

if not defined FOUND (
  if exist "%USERDL%\Sleep.csv" (
    set "FOUND=Sleep.csv"
  )
)

if not defined FOUND (
  echo [error] Could not find:
  echo         "%USERDL%\sleep-%ISO%*.csv"
  echo         or "%USERDL%\Sleep.csv"
  goto :done
)

for /f "delims=" %%T in ('powershell -NoProfile -Command "(Get-Date).ToString('yyyyMMdd_HHmmss')"') do set "STAMP=%%T"

set "SOURCE=%USERDL%\%FOUND%"
set "DEST=%INBOX%\sleep-%ISO%_Sky_%STAMP%.csv"

echo [copy] "%SOURCE%"  -->  "%DEST%"
copy /y "%SOURCE%" "%DEST%"
if errorlevel 1 (
  echo [error] Failed to copy CSV.
  goto :done
)

echo [stage] Staged file: "%DEST%"
echo [stage] Original remains in Downloads as visual proof.
echo.

rem ========= Step 2: Build a tiny helper .bat for Python =========
echo [2/2] Launching morning_reporter.py in its own DEBUG window...

set "SKY_GARMIN_TARGET_DATE=%ISO%"
set "PYTHONPATH=%ROOT%"

set "PYEXE=%ROOT%\venv\Scripts\python.exe"
if exist "%PYEXE%" (
  set "RUNNER=%PYEXE%"
) else (
  set "RUNNER=python"
)

echo [run] Using Python runner: %RUNNER%
echo [run] Date arg: %ISO%
echo.

set "TMPBAT=%TEMP%\sky_morning_%ISO%.bat"

(
  echo @echo off
  echo title Sky Morning Reporter DEBUG
  echo color 0A
  echo echo Running morning_reporter.py for %ISO%...
  echo echo.
  echo set SKY_GARMIN_TARGET_DATE=%ISO%
  echo set PYTHONPATH=%ROOT%
  echo cd /d "%ROOT%"
  echo "%RUNNER%" "%REPORTER%" --date %ISO%
  echo set RC=%%ERRORLEVEL%%
  echo echo.
  echo echo Reporter exit code: %%RC%%
  echo echo Expected digest:
  echo echo   "%DIGEST_DIR%\%ISO%.json"
  echo echo.
  echo echo Press any key to close this window.
  echo pause ^>nul
) > "%TMPBAT%"

echo [debug] Helper script written to:
echo         "%TMPBAT%"
echo.

start "Sky Morning Reporter DEBUG" "%TMPBAT%"

echo [hint] Watch the "Sky Morning Reporter DEBUG" window for Python output / errors.
echo [hint] Expected digest (after run) at:
echo        "%DIGEST_DIR%\%ISO%.json"

:done
echo.
echo =====================================================
echo This launcher window can now be closed.
echo (Press any key to close this window)
echo =====================================================
pause >nul
endlocal
