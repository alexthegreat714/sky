@echo off
setlocal ENABLEDELAYEDEXPANSION
title Sky Morning — Pull+Stage → Reporter (all-in-one)
color 0A

rem ===== Paths =====
set "ROOT=C:\Users\blyth\Desktop\Engineering"
set "SKY=%ROOT%\Sky"
set "TOOLS=%SKY%\tools"

rem Your working pull+stage components (that you said MUST run first)
set "CLICK_PS1=%TOOLS%\garmin_click_replay.ps1"
set "STAGE_BAT=%TOOLS%\move_garmin_csv.bat"

rem Wrapper that does BOTH steps above (optional, but we’ll inline the calls anyway)
set "PULL_STAGE_BAT=%TOOLS%\garmin_pull_and_stage.bat"

rem Reporter bits
set "REPORTER=%SKY%\agents\morning_reporter.py"
rem If you saved a separate “runner” .bat that you said works, point to it here:
set "RUN_REPORTER_BAT=%TOOLS%\run_morning_reporter.bat"

rem OWUI output dir (where the reporter writes JSON)
set "OWUI_DAILY=%ROOT%\open-webui-full\backend\data\sky_daily"

rem ===== Date arg: TODAY, YESTERDAY, or YYYY-MM-DD (default YESTERDAY) =====
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
echo ----------------------------------------------------

rem ---------------------------------------------------------------------------
rem [1/2] PULL + STAGE — DO THIS FIRST (exactly the flow you showed)
rem ---------------------------------------------------------------------------
if exist "%PULL_STAGE_BAT%" (
  echo [1/2] Pull+Stage via %PULL_STAGE_BAT% …
  echo [cmd] "%PULL_STAGE_BAT%" %ISO%
  START "" /WAIT "%PULL_STAGE_BAT%" %ISO%
  set "RC_STAGE=%ERRORLEVEL%"
) else (
  echo [1/2] Pull+Stage (inline) …
  if not exist "%CLICK_PS1%" (
    echo [error] Missing click script: %CLICK_PS1%
    echo (Press any key)
    pause >nul
    exit /b 90
  )
  if not exist "%STAGE_BAT%" (
    echo [error] Missing staging script: %STAGE_BAT%
    echo (Press any key)
    pause >nul
    exit /b 91
  )

  echo [click] Launching PowerShell replay to export CSV…
  powershell -NoProfile -ExecutionPolicy Bypass -File "%CLICK_PS1%" -When %ISO%
  set "RC_CLICK=%ERRORLEVEL%"
  echo [click] exit code %RC_CLICK% (continuing)

  echo [cleanup] Closing Chrome window used for export…
  taskkill /IM chrome.exe /F >nul 2>&1

  echo [stage] Staging downloaded CSV into Sky inbox…
  call "%STAGE_BAT%" %ISO% NOPAUSE
  set "RC_STAGE=%ERRORLEVEL%"
)

echo [pull-stage] exit code %RC_STAGE%
if not "%RC_STAGE%"=="0" (
  echo [abort] Pull+Stage failed (%RC_STAGE%). Check the click/stage logs.
  echo (Press any key)
  pause >nul
  exit /b %RC_STAGE%
)

rem ---------------------------------------------------------------------------
rem [2/2] REPORTER — run the working reporter runner (or direct python fallback)
rem ---------------------------------------------------------------------------
set "PYEXE=%ROOT%\venv\Scripts\python.exe"
set "PYTHONPATH=%ROOT%"
set "SKY_GARMIN_TARGET_DATE=%ISO%"
set "REPORT_PATH=%OWUI_DAILY%\%ISO%.json"

echo.
echo [2/2] Morning Reporter …
if exist "%RUN_REPORTER_BAT%" (
  echo [cmd] "%RUN_REPORTER_BAT%" %ISO%
  START "" /WAIT "%RUN_REPORTER_BAT%" %ISO%
  set "RC_REP=%ERRORLEVEL%"
) else (
  if not exist "%REPORTER%" (
    echo [error] Missing reporter: %REPORTER%
    echo (Press any key)
    pause >nul
    exit /b 92
  )
  if exist "%PYEXE%" ( set "RUNNER=%PYEXE%" ) else ( set "RUNNER=python" )
  echo [cmd] %RUNNER% "%REPORTER%"
  %RUNNER% "%REPORTER%"
  set "RC_REP=%ERRORLEVEL%"
)

echo [report] exit code %RC_REP%
if exist "%REPORT_PATH%" (
  echo [path] Report saved at: %REPORT_PATH%
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
