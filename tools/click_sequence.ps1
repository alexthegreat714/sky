param(
    [int]$Delay1,
    [int]$Delay2,
    [int]$Delay3,
    [int]$Delay4,
    [int]$Delay5,
    [int]$X1,
    [int]$Y1,
    [int]$X2,
    [int]$Y2,
    [int]$X3,
    [int]$Y3,
    [int]$X4,
    [int]$Y4,
    [int]$X5,
    [int]$Y5
)

Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public static class User32 {
    [DllImport("user32.dll")]
    public static extern bool SetCursorPos(int X,int Y);
    [DllImport("user32.dll")]
    public static extern void mouse_event(uint dwFlags,uint dx,uint dy,uint dwData,IntPtr dwExtraInfo);
}
"@

function Invoke-Click([int]$x,[int]$y) {
    [User32]::SetCursorPos($x,$y) | Out-Null
    Start-Sleep -Milliseconds 120
    $down = 0x0002
    $up   = 0x0004
    [User32]::mouse_event($down,0,0,0,[IntPtr]::Zero)
    Start-Sleep -Milliseconds 90
    [User32]::mouse_event($up,0,0,0,[IntPtr]::Zero)
}

Write-Host ("[seq] Waiting {0} ms before click 1" -f $Delay1)
Start-Sleep -Milliseconds $Delay1
Write-Host ("[seq] Click 1 at {0},{1}" -f $X1,$Y1)
Invoke-Click $X1 $Y1

Write-Host ("[seq] Waiting {0} ms before click 2" -f $Delay2)
Start-Sleep -Milliseconds $Delay2
Write-Host ("[seq] Click 2 at {0},{1}" -f $X2,$Y2)
Invoke-Click $X2 $Y2

Write-Host ("[seq] Waiting {0} ms before click 3" -f $Delay3)
Start-Sleep -Milliseconds $Delay3
Write-Host ("[seq] Click 3 at {0},{1}" -f $X3,$Y3)
Invoke-Click $X3 $Y3

Write-Host ("[seq] Waiting {0} ms before click 4" -f $Delay4)
Start-Sleep -Milliseconds $Delay4
Write-Host ("[seq] Click 4 at {0},{1}" -f $X4,$Y4)
Invoke-Click $X4 $Y4

Write-Host ("[seq] Waiting {0} ms before click 5" -f $Delay5)
Start-Sleep -Milliseconds $Delay5
Write-Host ("[seq] Click 5 at {0},{1}" -f $X5,$Y5)
Invoke-Click $X5 $Y5
