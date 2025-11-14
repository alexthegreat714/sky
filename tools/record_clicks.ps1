Add-Type -AssemblyName System.Windows.Forms
[console]::TreatControlCAsInput = $true
$points = @()
$lastState = [System.Windows.Forms.MouseButtons]::None
$startTime = Get-Date
$lastClickTime = $startTime

Write-Host 'Recording... Press ENTER in this window to finish.'

while ($true) {
    if ([console]::KeyAvailable) {
        $key = [console]::ReadKey($true)
        if ($key.Key -eq 'Enter') { break }
    }

    $state = [System.Windows.Forms.Control]::MouseButtons
    if (($state -band [System.Windows.Forms.MouseButtons]::Left) -and `
        -not ($lastState -band [System.Windows.Forms.MouseButtons]::Left)) {
        $pos = [System.Windows.Forms.Cursor]::Position
        $now = Get-Date
        $elapsed = $now - $startTime
        $gap = $now - $lastClickTime
        $lastClickTime = $now

        $points += @{
            Index = $points.Count + 1
            X = $pos.X
            Y = $pos.Y
            Timestamp = $now
            Elapsed = $elapsed
            Gap = $gap
        }

        Write-Host ("[{0}] Click {1}: X={2} Y={3} | since start {4:hh\:mm\:ss\.fff} | since prev {5:hh\:mm\:ss\.fff}" `
            -f $now.ToString('HH:mm:ss.fff'), $points.Count, $pos.X, $pos.Y, $elapsed, $gap)
    }
    $lastState = $state
    Start-Sleep -Milliseconds 20
}

Write-Host ''
if ($points.Count -eq 0) {
    Write-Host 'No clicks captured.'
} else {
    Write-Host ("Captured {0} click(s). Summary:" -f $points.Count)
    foreach ($point in $points) {
        Write-Host ("  Click {0}: X={1} Y={2} | delta-start {3:hh\:mm\:ss\.fff} | delta-prev {4:hh\:mm\:ss\.fff}" `
            -f $point.Index, $point.X, $point.Y, $point.Elapsed, $point.Gap)
    }
}
