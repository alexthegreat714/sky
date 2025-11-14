@echo off
setlocal ENABLEDELAYEDEXPANSION
title Sky Morning Routine (Garmin pull → digest)
color 0A

rem ===== Paths =====
set "ROOT=C:\Users\blyth\Desktop\Engineering"
set "SKY=%ROOT%\Sky"
set "AGENT=%SKY%\agents\sky_morning_orchestrator.py"
set "LOGDIR=%SKY%\logs\morning_orchestrator"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

rem ===== Target date (default: yesterday) =====
set "WHEN=%~1"
if /I "%WHEN%"=="TODAY" (
  for /f "delims=" %%D in ('powershell -NoProfile -Command "(Get-Date).ToString('yyyy-MM-dd')"') do set "ISO=%%D"
) else if /I "%WHEN%"=="YESTERDAY" (
  for /f "delims=" %%D in ('powershell -NoProfile -Command "(Get-Date).AddDays(-1).ToString('yyyy-MM-dd')"') do set "ISO=%%D"
) else if "%WHEN%"=="" (
  for /f "delims=" %%D in ('powershell -NoProfile -Command "(Get-Date).AddDays(-1).ToString('yyyy-MM-dd')"') do set "ISO=%%D"
) else (
  set "ISO=%WHEN%"
)

rem ===== Logging =====
for /f "tokens=1-4 delims=/ " %%a in ("%date%") do set "D=%%a-%%b-%%c-%%d"
set "T=%time: =0%"
set "T=%T::=-%"
set "STAMP=%D%_%T%"
set "LOG=%LOGDIR%\routine_%STAMP%.txt"
set "LOCAL_LOG=%~dp0routine_%STAMP%.txt"
type nul > "%LOG%" & type nul > "%LOCAL_LOG%"

:log
set "_m=%*"
if "%_m%"=="" (
  echo.
  >>"%LOG%" echo.
  >>"%LOCAL_LOG%" echo.
) else (
  echo %_m%
  >>"%LOG%" echo %_m%
  >>"%LOCAL_LOG%" echo %_m%
)
exit /b 0

call :log ----------------------------------------------------
call :log  Sky Morning Routine
call :log  Target date: %ISO%
call :log  Agent: %AGENT%
call :log  Log:   %LOG%
call :log ----------------------------------------------------

if not exist "%AGENT%" (
  call :log [error] Missing orchestrator script: %AGENT%
  goto :exit90
)

set "PYEXE=%ROOT%\venv\Scripts\python.exe"
if exist "%PYEXE%" (
  set "RUNNER=%PYEXE%"
) else (
  set "RUNNER=python"
)

call :log [run] %RUNNER% "%AGENT%" --date %ISO%
%RUNNER% "%AGENT%" --date %ISO%
set "RC=%ERRORLEVEL%"
call :log [done] orchestrator exit code %RC%

if not "%RC%"=="0" goto :exit_fail

call :log [exit] code 0
echo (Press any key to close)
pause >nul
exit /b 0

:exit_fail
call :log [exit] code %RC%
echo (Press any key to close)
pause >nul
exit /b %RC%

:exit90
call :log [exit] code 90
echo (Press any key to close)
pause >nul
exit /b 90
