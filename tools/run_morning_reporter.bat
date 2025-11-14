@echo off
setlocal
set "ROOT=C:\Users\blyth\Desktop\Engineering"
set "SKY=%ROOT%\Sky"
set "REPORTER=%SKY%\agents\morning_reporter.py"

if not exist "%REPORTER%" (
  echo [error] Missing reporter: %REPORTER%
  pause
  exit /b 1
)

set "DATE_ARG=%~1"
if "%DATE_ARG%"=="" set "DATE_ARG=TODAY"

if /I "%DATE_ARG%"=="TODAY" (
  for /f "delims=" %%D in ('powershell -NoProfile -Command "(Get-Date).ToString('yyyy-MM-dd')"') do set "ISO=%%D"
) else if /I "%DATE_ARG%"=="YESTERDAY" (
  for /f "delims=" %%D in ('powershell -NoProfile -Command "(Get-Date).AddDays(-1).ToString('yyyy-MM-dd')"') do set "ISO=%%D"
) else if "%DATE_ARG%"=="" (
  for /f "delims=" %%D in ('powershell -NoProfile -Command "(Get-Date).ToString('yyyy-MM-dd')"') do set "ISO=%%D"
) else (
  set "ISO=%DATE_ARG%"
)

echo ----------------------------------------------------
echo Sky Morning Reporter Runner
echo Target date : %ISO%
echo Reporter    : %REPORTER%
echo ----------------------------------------------------

set SKY_GARMIN_TARGET_DATE=%ISO%
set "PYEXE=%ROOT%\venv\Scripts\python.exe"
if exist "%PYEXE%" (
  set "RUNNER=%PYEXE%"
) else (
  set "RUNNER=python"
)

set SKY_GARMIN_TARGET_DATE=%ISO%
set "PYEXE=%ROOT%\venv\Scripts\python.exe"
if exist "%PYEXE%" (
  set "RUNNER=%PYEXE%"
) else (
  set "RUNNER=python"
)

set "REPORT_PATH=%SKY%\tools\open-webui-full\backend\data\sky_daily\%ISO%.json"

echo [run] %RUNNER% "%REPORTER%"
%RUNNER% "%REPORTER%"
set "RC=%ERRORLEVEL%"
if exist "%REPORT_PATH%" (
  echo [path] Report saved at: %REPORT_PATH%
) else (
  echo [path] Expected report path (verify): %REPORT_PATH%
)
echo [done] reporter exit code %RC%
echo (Press any key to close)
pause >nul
exit /b %RC%
