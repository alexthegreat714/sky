@echo off
title Detect Idle vs Active CMD Windows

echo ============================================================
echo Analyzing CMD Windows
echo ============================================================
echo.

powershell -NoProfile -Command "$cmds = Get-Process cmd -ErrorAction SilentlyContinue; foreach ($c in $cmds) { $title = $c.MainWindowTitle; $children = (Get-CimInstance Win32_Process -Filter \"ParentProcessId=$($c.Id)\" -ErrorAction SilentlyContinue); $childCount = if ($children) { $children.Count } else { 0 }; $status = if ($childCount -eq 0) { 'IDLE' } else { 'ACTIVE' }; $childNames = if ($children) { ($children | Select-Object -ExpandProperty Name) -join ', ' } else { 'none' }; Write-Host \"PID $($c.Id) | $status | Title: [$title] | Children: $childNames\" }"

echo.
echo ============================================================
echo Legend:
echo   IDLE   = Empty CMD window (no child processes)
echo   ACTIVE = Running something (has child processes)
echo ============================================================
echo.
echo Safe to close: IDLE windows with empty titles
echo Keep open: ACTIVE windows or those with titles
echo.
pause
