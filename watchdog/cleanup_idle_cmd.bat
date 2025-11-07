@echo off
REM ============================================================================
REM Smart Idle CMD Cleanup - Closes only truly idle CMD windows
REM ============================================================================
REM This script closes CMD windows that are:
REM   - Empty (no child processes)
REM   - Have no title or default title
REM   - Not running any services
REM
REM Safe to include in autoboot and restart scripts
REM ============================================================================

powershell -NoProfile -Command "& { $cleaned = 0; $skipped = 0; Get-Process cmd -ErrorAction SilentlyContinue | ForEach-Object { $proc = $_; $title = $proc.MainWindowTitle; $children = @(Get-CimInstance Win32_Process -Filter \"ParentProcessId=$($proc.Id)\" -ErrorAction SilentlyContinue); $hasChildren = $children.Count -gt 0; $isEmpty = [string]::IsNullOrWhiteSpace($title); $isDefault = $title -like '*cmd.exe*' -or $title -like '*Command Prompt*' -or $title -like 'C:\*'; $isIdle = (-not $hasChildren) -and ($isEmpty -or $isDefault); if ($isIdle) { try { Stop-Process -Id $proc.Id -Force -ErrorAction Stop; $cleaned++; } catch { $skipped++; } } else { $skipped++; } }; Write-Host \"[Idle Cleanup] Closed: $cleaned idle windows, Kept: $skipped active/titled windows\" }" 2>nul

exit /b 0
