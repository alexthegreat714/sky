@echo off
setlocal ENABLEDELAYEDEXPANSION

REM === Paths ===
set ROOT=C:\Users\blyth\Desktop\Engineering
set SKY=%ROOT%\Sky
set DOWNLOADER=%SKY%\agents\garmin_sleep_downloader.py
set REPORTER=%SKY%\agents\morning_reporter.py
set GARMIN_DOWNLOADS=%SKY%\downloads\garmin
set LOGDIR=%SKY%\logs\morning_digest

REM === Ensure dirs ===
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

REM === Timestamp for log and run id ===
for /f "tokens=1-4 delims=/ " %%a in ("%date%") do (set d=%%a-%%b-%%c-%%d)
set t=%time: =0%
set t=%t::=-%
set RUN_ID=%d%_%t%
set LOG=%LOGDIR%\run_%RUN_ID%.txt

echo [run] %date% %time% starting garmin+digest >> "%LOG%"

REM === Python path hygiene (absolute imports) ===
setx /M PYTHONPATH "%ROOT%" >NUL 2>&1
set PYTHONPATH=%ROOT%

REM === Optional venv activation (no-op if absent) ===
if exist "%ROOT%\venv\Scripts\activate.bat" call "%ROOT%\venv\Scripts\activate.bat"

REM === Step 1: Download (unless skipped) ===
if "%SKY_SKIP_GARMIN_AGENT%"=="1" (
  echo [run] SKY_SKIP_GARMIN_AGENT=1 - skipping downloader >> "%LOG%"
  set DOWNLOAD_SKIPPED=1
) else (
  echo [run] invoking legacy downloader >> "%LOG%"
  python "%DOWNLOADER%" >> "%LOG%" 2>&1
  if errorlevel 1 (
    echo [error] downloader failed, see log: "%LOG%" >> "%LOG%"
    echo [exit] code 20 >> "%LOG%"
    exit /b 20
  )
)

REM === Step 2: Verify we have a CSV in downloads\garmin ===
pushd "%GARMIN_DOWNLOADS%"
set LATEST_CSV=
for /f "delims=" %%f in ('dir /b /a:-d /o:-d "sleep-*.csv" 2^>NUL') do (
  if not defined LATEST_CSV set LATEST_CSV=%%f
)
popd

if not defined LATEST_CSV (
  echo [error] no sleep-*.csv found in "%GARMIN_DOWNLOADS%" >> "%LOG%"
  echo [hint] ensure downloader saved to downloads\garmin OR unset SKY_SKIP_GARMIN_AGENT >> "%LOG%"
  echo [exit] code 30 >> "%LOG%"
  exit /b 30
)

echo [ok] newest csv: "%GARMIN_DOWNLOADS%\%LATEST_CSV%" >> "%LOG%"

REM === Step 3: Build & POST Morning Digest ===
echo [run] executing morning_reporter.py >> "%LOG%"
python "%REPORTER%" >> "%LOG%" 2>&1
if errorlevel 1 (
  echo [error] morning_reporter.py failed >> "%LOG%"
  echo [exit] code 40 >> "%LOG%"
  exit /b 40
)

echo [done] digest built and (if router loaded) POSTed to OWUI >> "%LOG%"

REM === Exit codes ===
if defined DOWNLOAD_SKIPPED (
  echo [exit] code 10 (download skipped, digest built) >> "%LOG%"
  exit /b 10
)

echo [exit] code 0 >> "%LOG%"
exit /b 0

