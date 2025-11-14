param(
    [int]$PosX = 0,
    [int]$PosY = 0,
    [int]$Width = 1920,
    [int]$Height = 1080
)

Start-Sleep -Milliseconds 700

Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class Win32Move {
    [DllImport("user32.dll")]
    public static extern bool MoveWindow(IntPtr hWnd, int X, int Y, int nWidth, int nHeight, bool bRepaint);
}
"@

$chrome = Get-Process chrome -ErrorAction SilentlyContinue | Sort-Object StartTime -Descending | Select-Object -First 1
if ($chrome -and $chrome.MainWindowHandle -ne 0) {
    [Win32Move]::MoveWindow($chrome.MainWindowHandle, $PosX, $PosY, $Width, $Height, $true) | Out-Null
}
