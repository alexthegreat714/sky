@echo off
setlocal ENABLEDELAYEDEXPANSION
title Sky Garmin Pull → Stage → Report
color 0A

set "ROOT=C:\Users\blyth\Desktop\Engineering"
set "SKY=%ROOT%\Sky"
set "TOOLS=%SKY%\tools"
set "PULL_STAGE=%TOOLS%\garmin_pull_and_stage.bat"
set "REPORTER=%SKY%\agents\morning_reporter.py"

if not exist "%PULL_STAGE%" (
  echo [error] Missing pull+stage script: %PULL_STAGE%
  pause
  exit /b 90
)
if not exist "%REPORTER%" (
  echo [error] Missing reporter script: %REPORTER%
  pause
  exit /b 91
)

set "WHEN=%~1"
if "%WHEN%"=="" set "WHEN=YESTERDAY"

rem resolve ISO string for reporter logging
if /I "%WHEN%"=="TODAY" (
  for /f "delims=" %%D in ('powershell -NoProfile -Command "(Get-Date).ToString('yyyy-MM-dd')"') do set "ISO=%%D"
) else if /I "%WHEN%"=="YESTERDAY" (
  for /f "delims=" %%D in ('powershell -NoProfile -Command "(Get-Date).AddDays(-1).ToString('yyyy-MM-dd')"') do set "ISO=%%D"
) else (
  set "ISO=%WHEN%"
)

set "PYEXE=%ROOT%\venv\Scripts\python.exe"
if exist "%PYEXE%" (
  set "RUNNER=%PYEXE%"
) else (
  set "RUNNER=python"
)
set "REPORT_PATH=%SKY%\tools\open-webui-full\backend\data\sky_daily\%ISO%.json"

echo ----------------------------------------------------
echo Sky Garmin Pull → Stage → Report
echo Target date : %ISO%
echo ----------------------------------------------------

echo [1/2] Pull + Stage …
call "%PULL_STAGE%" %ISO%
set "RC1=%ERRORLEVEL%"
echo [pull-stage] exit code %RC1%
if not "%RC1%"=="0" (
  echo [abort] Pull/stage failed.
  pause
  exit /b %RC1%
)

echo ----------------------------------------------------
echo Sky Morning Reporter Runner
echo Target date : %ISO%
echo Reporter    : %REPORTER%
echo ----------------------------------------------------
set SKY_GARMIN_TARGET_DATE=%ISO%
echo [run] %RUNNER% "%REPORTER%"
%RUNNER% "%REPORTER%"
set "RC2=%ERRORLEVEL%"
if exist "%REPORT_PATH%" (
  echo [path] Report saved at: %REPORT_PATH%
) else (
  echo [path] Expected report path (verify): %REPORT_PATH%
)
echo [report] exit code %RC2%

if "%RC2%"=="0" (
  echo [done] Sweep complete.
) else (
  echo [done] Reporter failed with %RC2%.
)
echo (Press any key to close)
pause >nul
exit /b %RC2%
