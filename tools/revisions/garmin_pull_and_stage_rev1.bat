@echo off
setlocal ENABLEDELAYEDEXPANSION
title Sky Garmin Pull + Stage
color 0A

rem ===== Paths =====
set "ROOT=C:\Users\blyth\Desktop\Engineering"
set "SKY=%ROOT%\Sky"
set "TOOLS=%SKY%\tools"
set "CLICK_PS1=%TOOLS%\garmin_click_replay.ps1"
set "STAGE_BAT=%TOOLS%\move_garmin_csv.bat"

if not exist "%CLICK_PS1%" (
  echo [error] Missing PowerShell click script: %CLICK_PS1%
  pause
  exit /b 90
)
if not exist "%STAGE_BAT%" (
  echo [error] Missing staging batch script: %STAGE_BAT%
  pause
  exit /b 91
)

rem ===== Date arg (TODAY, YESTERDAY, or ISO) =====
set "WHEN=%~1"
if "%WHEN%"=="" set "WHEN=YESTERDAY"

echo ----------------------------------------------------
echo Sky Garmin Pull + Stage
echo Target date: %WHEN%
echo ----------------------------------------------------

echo [1/2] Launching click replay (PowerShell) to export CSV...
powershell -NoProfile -ExecutionPolicy Bypass -File "%CLICK_PS1%" -When %WHEN%
set "RC1=%ERRORLEVEL%"
echo [click] exit code %RC1%
if not "%RC1%"=="0" (
  echo [warn] Click replay reported non-zero exit. Continuing to staging step.
)

echo [2/2] Staging downloaded CSV into Sky inbox...
call "%STAGE_BAT%" %WHEN%
set "RC2=%ERRORLEVEL%"
echo [stage] exit code %RC2%

if "%RC2%"=="0" (
  echo [done] Pull+stage succeeded.
) else (
  echo [done] Staging step exited with %RC2%.
)
echo (Press any key to close)
pause >nul
exit /b %RC2%
