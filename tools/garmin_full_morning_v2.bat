@echo off
setlocal ENABLEDELAYEDEXPANSION
title Sky Garmin Full Morning Sweep v2
color 0A

rem ========= Paths =========
set "ROOT=C:\Users\blyth\Desktop\Engineering"
set "SKY=%ROOT%\Sky"
set "TOOLS=%SKY%\tools"
set "CLICK_PS1=%TOOLS%\garmin_click_replay.ps1"
set "STAGE_RUN_BAT=%TOOLS%\garmin_stage_and_run.bat"

if not exist "%CLICK_PS1%" (
  echo [error] Missing click script: %CLICK_PS1%
  goto :halt
)
if not exist "%STAGE_RUN_BAT%" (
  echo [error] Missing stage+run script: %STAGE_RUN_BAT%
  goto :halt
)

rem ========= Date handling =========
set "ARG=%~1"
if "%ARG%"=="" set "ARG=YESTERDAY"

if /I "%ARG%"=="TODAY" (
  for /f "delims=" %%D in ('
    powershell -NoProfile -Command "(Get-Date).ToString('yyyy-MM-dd')"
  ') do set "ISO=%%D"
) else if /I "%ARG%"=="YESTERDAY" (
  for /f "delims=" %%D in ('
    powershell -NoProfile -Command "(Get-Date).AddDays(-1).ToString('yyyy-MM-dd')"
  ') do set "ISO=%%D"
) else (
  set "ISO=%ARG%"
)

echo =====================================================
echo Sky Garmin Full Morning Sweep v2
echo ROOT  = %ROOT%
echo SKY   = %SKY%
echo DATE  = %ISO%
echo =====================================================
echo.

rem ========= Step 1: Click replay (export) =========
echo [1/2] Running Garmin click replay (PowerShell)...
powershell -NoProfile -ExecutionPolicy Bypass -File "%CLICK_PS1%" -When %ISO%
set "RC_CLICK=%ERRORLEVEL%"
echo [click] exit code: %RC_CLICK%
if not "%RC_CLICK%"=="0" (
  echo [abort] Click replay failed. Aborting full sweep.
  set "RC=%RC_CLICK%"
  goto :end
)

rem ========= Step 2: Stage CSV + run reporter =========
echo.
echo [2/2] Running stage + morning reporter pipeline...
call "%STAGE_RUN_BAT%" %ISO%
set "RC_STAGE=%ERRORLEVEL%"
echo [stage+run] exit code: %RC_STAGE%
set "RC=%RC_STAGE%"

if not "%RC_STAGE%"=="0" (
  echo [warn] Stage+run pipeline returned non-zero RC. Check output above.
) else (
  echo [done] Full morning sweep completed successfully.
)

goto :end

:halt
set "RC=1"
echo [halt] Full morning sweep aborted due to a setup error.

:end
echo.
echo =====================================================
echo Full-morning v2 finished. Exit code: %RC%
echo Press any key to close this window.
echo =====================================================
pause >nul
endlocal & exit /b %RC%
