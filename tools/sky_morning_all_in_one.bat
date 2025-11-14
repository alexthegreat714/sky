@echo off
setlocal ENABLEDELAYEDEXPANSION
title Sky Morning — Pull+Stage → Reporter
color 0A

rem ===== Paths =====
set "ROOT=C:\Users\blyth\Desktop\Engineering"
set "SKY=%ROOT%\Sky"
set "TOOLS=%SKY%\tools"

rem Your working pull+stage script (clicks Export, keeps original in Downloads, copies to Sky\downloads\garmin)
set "PULL_STAGE=%TOOLS%\garmin_pull_and_stage.bat"

rem Your working reporter runner .bat (the one you said "it works so leave it")
rem If you saved it under a different name, update this path:
set "RUN_REPORTER=%TOOLS%\run_morning_reporter.bat"

rem Fallback: if RUN_REPORTER .bat isn't found, we'll call morning_reporter.py directly
set "REPORTER=%SKY%\agents\morning_reporter.py"

rem ===== Date arg (default YESTERDAY; accepts TODAY or YYYY-MM-DD) =====
set "WHEN=%~1"
if "%WHEN%"=="" set "WHEN=YESTERDAY"

if /I "%WHEN%"=="TODAY" (
  for /f "delims=" %%D in ('powershell -NoProfile -Command "(Get-Date).ToString('yyyy-MM-dd')"') do set "ISO=%%D"
) else if /I "%WHEN%"=="YESTERDAY" (
  for /f "delims=" %%D in ('powershell -NoProfile -Command "(Get-Date).AddDays(-1).ToString('yyyy-MM-dd')"') do set "ISO=%%D"
) else (
  set "ISO=%WHEN%"
)

echo ----------------------------------------------------
echo Sky Morning — Pull+Stage → Reporter
echo Target date : %ISO%
echo Pull+Stage  : %PULL_STAGE%
echo ReporterRun : %RUN_REPORTER%
echo ----------------------------------------------------

rem ===== [1/2] Pull + Stage =====
if not exist "%PULL_STAGE%" (
  echo [error] Missing pull+stage script: %PULL_STAGE%
  echo (Press any key)
  pause >nul
  exit /b 40
)

echo [1/2] Running pull+stage...
echo [cmd] "%PULL_STAGE%" %ISO%
START "" /WAIT "%PULL_STAGE%" %ISO%
set "RC_STAGE=%ERRORLEVEL%"
echo [pull-stage] exit code %RC_STAGE%
if not "%RC_STAGE%"=="0" (
  echo [abort] Pull/stage failed.
  echo (Press any key)
  pause >nul
  exit /b %RC_STAGE%
)

rem ===== [2/2] Reporter =====
set "PYEXE=%ROOT%\venv\Scripts\python.exe"
set "OWUI_DAILY=%ROOT%\open-webui-full\backend\data\sky_daily"
set "REPORT_PATH=%OWUI_DAILY%\%ISO%.json"
set "SKY_GARMIN_TARGET_DATE=%ISO%"
set "PYTHONPATH=%ROOT%"

echo.
echo [2/2] Running reporter...

if exist "%RUN_REPORTER%" (
  echo [cmd] "%RUN_REPORTER%" %ISO%
  START "" /WAIT "%RUN_REPORTER%" %ISO%
  set "RC_REP=%ERRORLEVEL%"
) else (
  echo [info] Reporter runner .bat not found, calling morning_reporter.py directly
  if exist "%PYEXE%" ( set "RUNNER=%PYEXE%" ) else ( set "RUNNER=python" )
  echo [cmd] %RUNNER% "%REPORTER%"
  %RUNNER% "%REPORTER%"
  set "RC_REP=%ERRORLEVEL%"
)

echo [reporter] exit code %RC_REP%

if exist "%REPORT_PATH%" (
  echo [path] Report: %REPORT_PATH%
) else (
  echo [path] Expected (verify): %REPORT_PATH%
)

if "%RC_REP%"=="0" (
  echo [done] Morning sweep complete.
) else (
  echo [done] Reporter failed with %RC_REP%.
)

echo.
echo (Press any key to close)
pause >nul
exit /b %RC_REP%
