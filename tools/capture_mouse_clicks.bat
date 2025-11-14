@echo off
setlocal ENABLEDELAYEDEXPANSION
title Sky Mouse Coordinate Capture (Garmin Sleep)

set "ROOT=C:\Users\blyth\Desktop\Engineering"
set "SKY=%ROOT%\Sky"
set "LINKS=%SKY%\tools\links"
set "SCRIPT=%~dp0record_clicks.ps1"
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

if not exist "%LINKS%" mkdir "%LINKS%"
if not exist "%CHROME_PROFILE%" mkdir "%CHROME_PROFILE%"

rem === Date pick (today by default, optional YESTERDAY arg) ===
set "WHEN=%~1"
if /I "%WHEN%"=="YESTERDAY" (
  for /f "delims=" %%D in ('powershell -NoProfile -Command "(Get-Date).AddDays(-1).ToString('yyyy-MM-dd')"') do set "ISO=%%D"
) else (
  for /f "delims=" %%D in ('powershell -NoProfile -Command "(Get-Date).ToString('yyyy-MM-dd')"') do set "ISO=%%D"
)

set "URL=https://connect.garmin.com/modern/sleep/%ISO%/0"
set "LINKFILE=%LINKS%\sleep-%ISO%.url"

> "%LINKFILE%" echo [InternetShortcut]
>> "%LINKFILE%" echo URL=%URL%

cls
echo ----------------------------------------------------
echo Sky Mouse Coordinate Capture (Garmin Sleep)
echo Target date : %ISO%
echo URL         : %URL%
echo ----------------------------------------------------
echo.
echo [open] Launching Garmin Sleep page (same window profile as automation)...
start "" "%CHROME_EXE%" --new-window --user-data-dir="%CHROME_PROFILE%" --profile-directory="Default" --window-position=%CHROME_POSITION% --window-size=%CHROME_SIZE% "%URL%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%TOOLS%\window_pos.ps1" -PosX %POS_X% -PosY %POS_Y% -Width %WIN_W% -Height %WIN_H%

echo.
echo Arrange the browser window exactly how you want it when automation runs.
echo When ready, return here and press ENTER to begin capturing clicks.
echo The recorder will keep running until you come back and press ENTER again.
echo.
pause

cls
echo [info] Recording left-click positions. Press ENTER in this window to stop.
echo [info] Console will show each click as it is captured (with timestamp).
echo ------------------------------------------------------------------------

powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT%"

echo.
echo [done] Copy the coordinates above into garmin_click_export.bat (MENU/EXPORT).
echo Press any key to exit.
pause >nul
