@echo off
setlocal ENABLEDELAYEDEXPANSION
title Sky Garmin Downloader (manual test, sticky)
color 0A

goto :main

:log
set "_msg=%*"
if "%_msg%"=="" (
  echo.
  >> "%LOGFILE%" echo.
  >> "%LOCAL_LOG%" echo.
) else (
  echo %_msg%
  >> "%LOGFILE%" echo %_msg%
  >> "%LOCAL_LOG%" echo %_msg%
)
goto :eof

:main
rem ===== Paths =====
set "ROOT=C:\Users\blyth\Desktop\Engineering"
set "SKY=%ROOT%\Sky"
set "DOWNLOADER=%SKY%\agents\garmin_sleep_downloader.py"
set "GARMIN_DOWNLOADS=%SKY%\downloads\garmin"
set "LOGDIR=%SKY%\logs\garmin_downloader"
set "SCRIPT_DIR=%~dp0"

rem ===== Timestamp + logs =====
for /f "tokens=1-4 delims=/ " %%a in ("%date%") do set "D=%%a-%%b-%%c-%%d"
set "T=%time: =0%"
set "T=%T::=-%"
set "LOG_TS=%D%_%T%"
set "LOGFILE=%LOGDIR%\run_%LOG_TS%.txt"
set "LOCAL_LOG=%SCRIPT_DIR%run_%LOG_TS%.txt"

rem ===== Ensure dirs =====
if not exist "%GARMIN_DOWNLOADS%" mkdir "%GARMIN_DOWNLOADS%"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

rem ===== Prime logs immediately =====
type nul > "%LOGFILE%"
type nul > "%LOCAL_LOG%"

call :log ----------------------------------------------------
call :log  Sky Garmin Downloader - Manual Test Harness
call :log  Script:      %~f0
call :log  ROOT:        %ROOT%
call :log  Downloader:  %DOWNLOADER%
call :log  Target dir:  %GARMIN_DOWNLOADS%
call :log  Log file:    %LOGFILE%
call :log  Local copy:  %LOCAL_LOG%
call :log ----------------------------------------------------

call :log [status] Setting PYTHONPATH to %ROOT%
set "PYTHONPATH=%ROOT%"

if exist "%ROOT%\venv\Scripts\activate.bat" (
  call :log [status] Activating venv at %ROOT%\venv ...
  call "%ROOT%\venv\Scripts\activate.bat"
) else (
  call :log [status] No venv detected; using system Python.
)

for /f "delims=" %%v in ('python -V 2^>^&1') do set "PYV=%%v"
call :log [python] %PYV%
call :log
call :log [run] Launching garmin_sleep_downloader.py (a Chrome window may open) ...
call :log [run] Live output is being teed to BOTH logs
call :log

powershell -NoProfile -Command ^
  "Write-Output ('[start] ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')) | Tee-Object -FilePath '%LOGFILE%' -Append | Tee-Object -FilePath '%LOCAL_LOG%' -Append; ^
   & python '%DOWNLOADER%' 2>&1 | Tee-Object -FilePath '%LOGFILE%' -Append | Tee-Object -FilePath '%LOCAL_LOG%' -Append; ^
   Write-Output ('[end]   ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')) | Tee-Object -FilePath '%LOGFILE%' -Append | Tee-Object -FilePath '%LOCAL_LOG%' -Append"
set "EXITCODE=%ERRORLEVEL%"

if not "%EXITCODE%"=="0" (
  call :log
  call :log [error] Downloader exited with code %EXITCODE%
  call :log [hint] Check credentials, selectors, or Playwright prompts.
) else (
  call :log
  call :log [ok] Downloader completed (exit code 0)
)

call :log
call :log [status] Most recent sleep-*.csv in %GARMIN_DOWNLOADS% :
pushd "%GARMIN_DOWNLOADS%" >nul 2>&1
set "SHOWN="
for /f "delims=" %%F in ('dir /b /a:-d /o:-d "sleep-*.csv" 2^>nul') do (
  if not defined SHOWN (
    call :log   %%F
    set "SHOWN=1"
  )
)
if not defined SHOWN call :log   (none found)
popd >nul 2>&1

call :log
call :log [info] Final exit code: %EXITCODE%
call :log [info] This window will remain open. Press CTRL+C to stop, or close the window.
:hold
timeout /t 3600 >nul
goto hold
