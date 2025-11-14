@echo off
setlocal ENABLEDELAYEDEXPANSION
title Sky Morning: Garmin pull → move → report
color 0A

rem ====== Paths ======
set "ROOT=C:\Users\blyth\Desktop\Engineering"
set "SKY=%ROOT%\Sky"
set "TOOLS=%SKY%\tools"
set "CLICKER=%TOOLS%\garmin_click_export.bat"
set "INBOX=%SKY%\downloads\garmin"
set "USERDL=%USERPROFILE%\Downloads"
set "REPORTER=%SKY%\agents\morning_reporter.py"
set "LOGDIR=%SKY%\logs\morning_orchestrator"

if not exist "%INBOX%" mkdir "%INBOX%"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

rem ====== Timestamp + logs (also drop a copy next to script) ======
for /f "tokens=1-4 delims=/ " %%a in ("%date%") do set "D=%%a-%%b-%%c-%%d"
set "T=%time: =0%"
set "T=%T::=-%"
set "STAMP=%D%_%T%"
set "LOG=%LOGDIR%\run_%STAMP%.txt"
set "LOCAL_LOG=%~dp0run_%STAMP%.txt"
type nul > "%LOG%" & type nul > "%LOCAL_LOG%"

rem ====== logger helper ======
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

rem ====== date select: default TODAY, allow YESTERDAY as %1 ======
set "WHEN=%~1"
if /I "%WHEN%"=="YESTERDAY" (
  for /f "delims=" %%D in ('powershell -NoProfile -Command "(Get-Date).AddDays(-1).ToString('yyyy-MM-dd')"') do set "ISO=%%D"
) else (
  for /f "delims=" %%D in ('powershell -NoProfile -Command "(Get-Date).ToString('yyyy-MM-dd')"') do set "ISO=%%D"
)

call :log ----------------------------------------------------
call :log  Sky Morning pull → move → report
call :log  Target date: %ISO%
call :log  Inbox: %INBOX%
call :log  Downloads: %USERDL%
call :log  Log: %LOG%
call :log  Local log: %LOCAL_LOG%
call :log ----------------------------------------------------

rem ====== Step 1: run clicker to open page & export CSV ======
if not exist "%CLICKER%" (
  call :log [error] Missing clicker: %CLICKER%
  goto :exit40
)

call :log [run] Launching clicker (.bat) to export CSV…
call "%CLICKER%" %ISO%
set "RC_CLICK=%ERRORLEVEL%"
call :log [clicker] exit code %RC_CLICK%

rem ====== Step 2: wait for CSV in Downloads ======
set "FOUND="
set "WAIT_SECS=300"
set "POLL=2"

call :log [wait] Watching for sleep-%ISO%*.csv (max %WAIT_SECS%s) …
for /l %%S in (1,1,%WAIT_SECS%) do (
  for /f "delims=" %%F in ('dir /b /a:-d /o:-d "%USERDL%\sleep-%ISO%*.csv" 2^>nul') do (
    set "FOUND=%USERDL%\%%F"
    goto :found
  )
  >nul powershell -NoProfile -Command "Start-Sleep -Seconds %POLL%"
)

call :log [timeout] No CSV detected after %WAIT_SECS%s. Aborting.
goto :exit30

:found
call :log [ok] Detected download: %FOUND%

rem ====== Step 3: rename + move into Sky inbox ======
for /f "delims=" %%Z in ('powershell -NoProfile -Command "(Get-Date).ToString('yyyyMMdd_HHmmss')"') do set "TS=%%Z"
set "DEST=%INBOX%\sleep-%ISO%_Sky_%TS%.csv"

copy /y "%FOUND%" "%DEST%" >nul
if errorlevel 1 (
  call :log [error] Copy to inbox failed: %DEST%
  goto :exit31
)
call :log [copy] Saved to: %DEST%

rem ====== Step 4: run the reporter ======
set "PYEXE=%ROOT%\venv\Scripts\python.exe"
set "PYTHONPATH=%ROOT%"

if exist "%PYEXE%" (
  call :log [run] Reporter via venv python …
  "%PYEXE%" "%REPORTER%"
) else (
  call :log [run] Reporter via system python …
  python "%REPORTER%"
)
set "RC_REP=%ERRORLEVEL%"

if not "%RC_REP%"=="0" (
  call :log [error] Reporter failed with exit code %RC_REP%
  goto :exit50
)

call :log [done] Morning digest built. (Reporter exit 0)

rem ====== Done ======
:exit0
call :log .
call :log [exit] code 0
echo (Press any key to close)
pause >nul
exit /b 0

:exit30
call :log [exit] code 30 (no CSV detected)
echo (Press any key to close)
pause >nul
exit /b 30

:exit31
call :log [exit] code 31 (copy failed)
echo (Press any key to close)
pause >nul
exit /b 31

:exit40
call :log [exit] code 40 (clicker missing)
echo (Press any key to close)
pause >nul
exit /b 40

:exit50
call :log [exit] code 50 (reporter failed)
echo (Press any key to close)
pause >nul
exit /b 50
