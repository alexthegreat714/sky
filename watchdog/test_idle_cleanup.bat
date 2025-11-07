@echo off
title Test Idle CMD Cleanup
chcp 65001 >nul

echo ============================================================
echo TEST: Idle CMD Window Detection and Cleanup
echo ============================================================
echo.

echo STEP 1: Scanning current CMD windows...
echo.
powershell -NoProfile -Command "$cmds = Get-Process cmd -ErrorAction SilentlyContinue; Write-Host 'Total CMD windows: '$cmds.Count; foreach ($c in $cmds) { $title = $c.MainWindowTitle; $children = @(Get-CimInstance Win32_Process -Filter \"ParentProcessId=$($c.Id)\" -ErrorAction SilentlyContinue); $childCount = $children.Count; $status = if ($childCount -eq 0) { 'IDLE' } else { 'ACTIVE' }; $childNames = if ($children) { ($children | Select-Object -ExpandProperty Name) -join ', ' } else { 'none' }; Write-Host \"  PID $($c.Id.ToString().PadRight(6)) | $status.PadRight(8) | Title: [$title] | Children: $childNames\" }"

echo.
echo ============================================================
echo STEP 2: Launching Chat Tunnel (will create ACTIVE window)...
echo ============================================================
echo.

REM Launch chat tunnel
start "Chat Tunnel TEST" cmd /k "echo Chat tunnel running... && timeout /t 300 /nobreak"
timeout /t 3 /nobreak >nul

echo STEP 3: Scanning again (should show new ACTIVE window)...
echo.
powershell -NoProfile -Command "$cmds = Get-Process cmd -ErrorAction SilentlyContinue; foreach ($c in $cmds) { $title = $c.MainWindowTitle; $children = @(Get-CimInstance Win32_Process -Filter \"ParentProcessId=$($c.Id)\" -ErrorAction SilentlyContinue); $childCount = $children.Count; $status = if ($childCount -eq 0) { 'IDLE' } else { 'ACTIVE' }; if ($title -match 'Chat Tunnel TEST') { Write-Host \"  >>> PID $($c.Id) | $status | Title: [$title] | Children: $childCount <<<\" } }"

echo.
echo ============================================================
echo STEP 4: Killing the chat tunnel process...
echo ============================================================
echo.

powershell -NoProfile -Command "Get-Process cmd | Where-Object { $_.MainWindowTitle -eq 'Chat Tunnel TEST' } | ForEach-Object { Write-Host '  Killing PID '$_.Id' (Chat Tunnel TEST)'; Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue }"
timeout /t 2 /nobreak >nul

echo.
echo STEP 5: Now checking if empty CMD windows remain...
echo.
powershell -NoProfile -Command "$idle = Get-Process cmd -ErrorAction SilentlyContinue | Where-Object { $children = @(Get-CimInstance Win32_Process -Filter \"ParentProcessId=$($_.Id)\" -ErrorAction SilentlyContinue); $children.Count -eq 0 -and ($_.MainWindowTitle -eq '' -or $_.MainWindowTitle -like 'Chat Tunnel TEST*') }; if ($idle) { Write-Host '  Found '$idle.Count' idle/zombie CMD windows'; foreach ($i in $idle) { Write-Host \"    PID $($i.Id) | Title: [$($i.MainWindowTitle)]\" } } else { Write-Host '  No idle/zombie windows found - all cleaned up!' }"

echo.
echo ============================================================
echo STEP 6: Cleaning up idle/zombie CMD windows...
echo ============================================================
echo.

powershell -NoProfile -Command "$cleaned = 0; Get-Process cmd -ErrorAction SilentlyContinue | Where-Object { $children = @(Get-CimInstance Win32_Process -Filter \"ParentProcessId=$($_.Id)\" -ErrorAction SilentlyContinue); $children.Count -eq 0 -and $_.MainWindowTitle -eq '' } | ForEach-Object { Write-Host '  Closing idle CMD PID '$_.Id; Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue; $cleaned++ }; if ($cleaned -eq 0) { Write-Host '  No idle windows to clean' } else { Write-Host \"  Cleaned $cleaned idle windows\" }"

echo.
echo ============================================================
echo STEP 7: Final scan - verifying cleanup...
echo ============================================================
echo.

powershell -NoProfile -Command "$cmds = Get-Process cmd -ErrorAction SilentlyContinue; Write-Host 'Remaining CMD windows: '$cmds.Count; foreach ($c in $cmds) { $title = $c.MainWindowTitle; $children = @(Get-CimInstance Win32_Process -Filter \"ParentProcessId=$($c.Id)\" -ErrorAction SilentlyContinue); $status = if ($children.Count -eq 0) { 'IDLE' } else { 'ACTIVE' }; Write-Host \"  PID $($c.Id) | $status | Title: [$title]\" }"

echo.
echo ============================================================
echo TEST COMPLETE
echo ============================================================
echo.
pause
