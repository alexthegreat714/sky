@echo off
setlocal

set "SCRIPT=%~dp0echorun_sky.ps1"
if not exist "%SCRIPT%" (
  echo [error] PowerShell helper not found: %SCRIPT%
  exit /b 1
)

set "PS=powershell.exe"
if exist "%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" (
  set "PS=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
)

"%PS%" -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT%" %*
exit /b %ERRORLEVEL%
