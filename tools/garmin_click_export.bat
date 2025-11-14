@echo off
setlocal ENABLEDELAYEDEXPANSION
title Sky: Garmin Sleep menu clicker (experimental)

rem === Paths / folders ===
set "ROOT=C:\Users\blyth\Desktop\Engineering"
set "SKY=%ROOT%\Sky"
set "INBOX=%SKY%\downloads\garmin"
set "TOOLS=%SKY%\tools"
set "LINKS=%TOOLS%\links"
set "SECONDARY=%USERPROFILE%\Downloads"
set "CHROME1=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
set "CHROME2=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
set "CHROME_EXE=%CHROME1%"
if not exist "%CHROME_EXE%" set "CHROME_EXE=%CHROME2%"
if not exist "%CHROME_EXE%" set "CHROME_EXE=chrome"
set "CHROME_PROFILE=%USERPROFILE%\AppData\Local\Sky\profiles\garmin"
set "CHROME_POSITION=1920,0"
set "CHROME_SIZE=1920,1080"
for /f "tokens=1,2 delims=," %%A in ("%CHROME_POSITION%") do (
    set "POS_X=%%A"
    set "POS_Y=%%B"
)
for /f "tokens=1,2 delims=," %%A in ("%CHROME_SIZE%") do (
    set "WIN_W=%%A"
    set "WIN_H=%%B"
)

if not exist "%INBOX%" mkdir "%INBOX%"
if not exist "%LINKS%" mkdir "%LINKS%"
if not exist "%CHROME_PROFILE%" mkdir "%CHROME_PROFILE%"

rem === Coordinates (adjust if needed for your display) ===
set "MENU_X=1850"
set "MENU_Y=170"
set "EXPORT_X=1810"
set "EXPORT_Y=260"

rem === Date selection ===
set "WHEN=%~1"
if /I "%WHEN%"=="YESTERDAY" (
  for /f "delims=" %%D in ('powershell -NoProfile -Command "(Get-Date).AddDays(-1).ToString('yyyy-MM-dd')"') do set "ISO=%%D"
) else (
  for /f "delims=" %%D in ('powershell -NoProfile -Command "(Get-Date).ToString('yyyy-MM-dd')"') do set "ISO=%%D"
)

set "URL=https://connect.garmin.com/modern/sleep/%ISO%/0"

cls
echo ----------------------------------------------------
echo Sky Garmin Manual Export Helper
echo Target date : %ISO%
echo URL         : %URL%
echo Inbox       : %INBOX%
echo Fallback    : %SECONDARY%
echo Menu coords : %MENU_X%x%MENU_Y%
echo Export coords: %EXPORT_X%x%EXPORT_Y%
echo ----------------------------------------------------
echo.

echo [open] Launching Garmin sleep page in Chrome...
start "" "%CHROME_EXE%" --new-window --user-data-dir="%CHROME_PROFILE%" --profile-directory="Default" --window-position=%CHROME_POSITION% --window-size=%CHROME_SIZE% "%URL%"
rem force window placement in case Chrome ignores switches
powershell -NoProfile -ExecutionPolicy Bypass -File "%TOOLS%\window_pos.ps1" -PosX %POS_X% -PosY %POS_Y% -Width %WIN_W% -Height %WIN_H%

echo [info] Bring the browser window to the foreground (maximized is best).
echo [info] Script will click the 3-dot menu then the "Export CSV" item.
echo [info] You have 5 seconds to position the pointer away from the target area.
powershell -NoProfile -Command "Start-Sleep -Seconds 5"

echo [click] Attempting automated clicks...
powershell -NoProfile -Command ^
  "$sig = @'
  using System;
  using System.Runtime.InteropServices;
  public static class User32 {
      [DllImport(\"user32.dll\")]
      public static extern bool SetCursorPos(int X, int Y);
      [DllImport(\"user32.dll\")]
      public static extern void mouse_event(uint dwFlags, uint dx, uint dy, uint dwData, IntPtr dwExtraInfo);
  }
'@;
  Add-Type -TypeDefinition $sig -Name Native -Namespace Sky;
  function Invoke-Click([int]$x,[int]$y) {
      [Sky.Native]::SetCursorPos($x,$y) | Out-Null
      Start-Sleep -Milliseconds 300
      $down = 0x0002
      $up = 0x0004
      [Sky.Native]::mouse_event($down,0,0,0,[IntPtr]::Zero)
      Start-Sleep -Milliseconds 80
      [Sky.Native]::mouse_event($up,0,0,0,[IntPtr]::Zero)
  }
  Invoke-Click %MENU_X% %MENU_Y%
  Start-Sleep -Milliseconds 700
  Invoke-Click %EXPORT_X% %EXPORT_Y%
"

if errorlevel 1 (
    echo [warn] PowerShell click routine reported an error. Adjust coordinates and retry.
    goto :post
)

echo [wait] Waiting for Garmin to generate CSV (watching downloads)...
set "FOUND="
for /l %%S in (1,1,120) do (
    for /f "delims=" %%F in ('dir /b /a:-d "%INBOX%\sleep-%ISO%*.csv" 2^>nul') do (
        set "FOUND=%INBOX%\%%F"
        goto :found
    )
    for /f "delims=" %%F in ('dir /b /a:-d "%SECONDARY%\sleep-%ISO%*.csv" 2^>nul') do (
        copy /y "%SECONDARY%\%%F" "%INBOX%" >nul
        set "FOUND=%INBOX%\%%F"
        goto :found
    )
    powershell -NoProfile -Command "Start-Sleep -Seconds 1" >nul
)

echo [timeout] Did not see sleep-%ISO%*.csv after 120 seconds. Verify clicks or download manually.
goto :post

:found
echo [ok] CSV detected: %FOUND%

:post
echo.
echo Done. Verify the download folder. Close this window when finished.
pause >nul
exit /b 0
