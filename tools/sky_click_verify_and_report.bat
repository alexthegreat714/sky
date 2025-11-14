@echo off
setlocal ENABLEDELAYEDEXPANSION
title Sky: click→verify CSV→(optional) copy+report (sticky)
color 0A

rem ===== Paths =====
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

rem ===== Date: TODAY default, YESTERDAY via arg =====
set "WHEN=%~1"
if /I "%WHEN%"=="YESTERDAY" (
  for /f "delims=" %%D in ('powershell -NoProfile -Command "(Get-Date).AddDays(-1).ToString('yyyy-MM-dd')"') do set "ISO=%%D"
) else (
  for /f "delims=" %%D in ('powershell -NoProfile -Command "(Get-Date).ToString('yyyy-MM-dd')"') do set "ISO=%%D"
)

rem ===== Logging (file + sidecar next to script) =====
for /f "tokens=1-4 delims=/ " %%a in ("%date%") do set "D=%%a-%%b-%%c-%%d"
set "T=%time: =0%"
set "T=%T::=-%"
set "STAMP=%D%_%T%"
set "LOG=%LOGDIR%\verify_run_%STAMP%.txt"
set "LOCAL_LOG=%~dp0verify_run_%STAMP%.txt"
type nul > "%LOG%" & type nul > "%LOCAL_LOG%"

:log
set "_m=%*"
if "%_m%"=="" (echo. & >>"%LOG%" echo. & >>"%LOCAL_LOG%" echo.) else (
  echo %_m%
  >>"%LOG%" echo %_m%
  >>"%LOCAL_LOG%" echo %_m%
)
exit /b 0

call :log ----------------------------------------------------
call :log Sky: click→verify CSV→(optional) copy+report
call :log Target date: %ISO%
call :log Downloads:   %USERDL%
call :log Sky inbox:   %INBOX%
call :log Clicker:     %CLICKER%
call :log Logs:        %LOG%
call :log ----------------------------------------------------

if not exist "%CLICKER%" (
  call :log [error] Missing clicker: %CLICKER%
  goto :stick40
)

rem ===== Step 1: REPLAY RECORDED CLICKS (block until done) =====
call :log [run] Starting clicker (this will open the Sleep page and auto-click Export CSV)…
REM Use START /WAIT so the wrapper doesn't exit immediately even if clicker opens another process
START "" /WAIT "%CLICKER%" %ISO%
set "RC_CLICK=%ERRORLEVEL%"
call :log [clicker] exit code %RC_CLICK%  (file detection will be the truth)

rem ===== Step 2: VERIFY CSV IN DOWNLOADS (do NOT move/delete yet) =====
set "FOUND="
set "WAIT_SECS=300"
set "POLL=2"
call :log [wait] Watching %USERDL%\sleep-%ISO%*.csv (max %WAIT_SECS%s)…

for /l %%S in (1,1,%WAIT_SECS%) do (
  for /f "delims=" %%F in ('dir /b /a:-d /o:-d "%USERDL%\sleep-%ISO%*.csv" 2^>nul') do (
    set "FOUND=%USERDL%\%%F"
    goto :found
  )
  >nul powershell -NoProfile -Command "Start-Sleep -Seconds %POLL%"
)

call :log [timeout] No CSV detected. If Chrome used a different profile or folder, check Downloads.
goto :stick30

:found
call :log [ok] Detected: %FOUND%
echo.
echo Confirm in File Explorer that the CSV is in Downloads.
echo Y = copy to Sky inbox and run reporter
echo N = stop here (leave CSV in Downloads)
choice /c YN /n /m "Proceed (Y/N)? "
if errorlevel 2 goto :stick0

rem ===== Step 3: COPY into Sky inbox (keep original) =====
for /f "delims=" %%Z in ('powershell -NoProfile -Command "(Get-Date).ToString('yyyyMMdd_HHmmss')"') do set "TS=%%Z"
set "DEST=%INBOX%\sleep-%ISO%_Sky_%TS%.csv"
copy /y "%FOUND%" "%DEST%" >nul
if errorlevel 1 (
  call :log [error] Copy failed to: %DEST%
  goto :stick31
)
call :log [copy] Saved: %DEST%

rem ===== Step 4: RUN REPORTER =====
set "PYEXE=%ROOT%\venv\Scripts\python.exe"
set "PYTHONPATH=%ROOT%"
if exist "%PYEXE%" (
  call :log [run] Reporter (venv)…
  "%PYEXE%" "%REPORTER%"
) else (
  call :log [run] Reporter (system)…
  python "%REPORTER%"
)
set "RC_REP=%ERRORLEVEL%"
if not "%RC_REP%"=="0" (
  call :log [error] Reporter exit %RC_REP%
  goto :stick50
)
call :log [done] Reporter completed (exit 0)
goto :stick0

:stick0
call :log .
call :log [exit] code 0
echo (Press any key to close)
pause >nul
exit /b 0

:stick30
call :log [exit] code 30 (no CSV detected)
echo (Press any key to close)
pause >nul
exit /b 30

:stick31
call :log [exit] code 31 (copy failed)
echo (Press any key to close)
pause >nul
exit /b 31

:stick40
call :log [exit] code 40 (clicker missing)
echo (Press any key to close)
pause >nul
exit /b 40

:stick50
call :log [exit] code 50 (reporter error)
echo (Press any key to close)
pause >nul
exit /b 50
