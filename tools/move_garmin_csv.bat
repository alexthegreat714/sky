@echo off
setlocal ENABLEDELAYEDEXPANSION
title Sky Garmin CSV Stager
color 0A

rem ===== Paths =====
set "ROOT=C:\Users\blyth\Desktop\Engineering"
set "SKY=%ROOT%\Sky"
set "INBOX=%SKY%\downloads\garmin"
set "USERDL=%USERPROFILE%\Downloads"

if not exist "%INBOX%" mkdir "%INBOX%"

rem ===== Target date (default: today; pass YESTERDAY or YYYY-MM-DD) =====
set "WHEN=%~1"
if /I "%WHEN%"=="YESTERDAY" (
  for /f "delims=" %%D in ('powershell -NoProfile -Command "(Get-Date).AddDays(-1).ToString('yyyy-MM-dd')"') do set "ISO=%%D"
) else if "%WHEN%"=="" (
  for /f "delims=" %%D in ('powershell -NoProfile -Command "(Get-Date).ToString('yyyy-MM-dd')"') do set "ISO=%%D"
) else (
  set "ISO=%WHEN%"
)

echo ----------------------------------------------------
echo Sky Garmin CSV Stager
echo Target date : %ISO%
echo Source dir  : %USERDL%
echo Inbox dir   : %INBOX%
echo ----------------------------------------------------

set "FOUND="
set "PATTERN=%USERDL%\sleep-%ISO%*.csv"
for /f "delims=" %%F in ('dir /b /a:-d /o:-d "%PATTERN%" 2^>nul') do (
  if not defined FOUND set "FOUND=%%F"
)
if not defined FOUND (
  if exist "%USERDL%\Sleep.csv" (
    set "FOUND=Sleep.csv"
  ) else (
    echo [error] No files matching sleep-%ISO%*.csv or Sleep.csv were found in %USERDL%.
    echo (Press any key to close)
    pause >nul
    exit /b 1
  )
)

:found
set "SOURCE=%USERDL%\%FOUND%"
for /f "delims=" %%T in ('powershell -NoProfile -Command "(Get-Date).ToString('yyyyMMdd_HHmmss')"') do set "STAMP=%%T"
set "DEST=%INBOX%\sleep-%ISO%_Sky_%STAMP%.csv"

echo [copy] %SOURCE%  -->  %DEST%
copy /y "%SOURCE%" "%DEST%" >nul
if errorlevel 1 (
  echo [error] Failed to copy file.
  echo (Press any key to close)
  pause >nul
  exit /b 2
)

echo [done] Staged CSV at: %DEST%
echo (Original file left in Downloads.)
if /I not "%~2"=="NOPAUSE" (
  echo (Press any key to close)
  pause >nul
)
exit /b 0
