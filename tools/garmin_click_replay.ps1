param(
    [string]$When = "TODAY"
)

$Root  = "C:\Users\blyth\Desktop\Engineering"
$Sky   = Join-Path $Root "Sky"
$Tools = Join-Path $Sky "tools"

function Resolve-ChromeExe {
    $candidates = @(
        "$Env:ProgramFiles\Google\Chrome\Application\chrome.exe",
        "$Env:ProgramFiles(x86)\Google\Chrome\Application\chrome.exe"
    )
    foreach ($path in $candidates) {
        if (Test-Path $path) { return $path }
    }
    return "chrome.exe"
}

$chromeExe   = Resolve-ChromeExe
$profilePath = Join-Path $Env:USERPROFILE "AppData\Local\Sky\profiles\garmin"
$windowPos   = "1920,0"
$windowSize  = "1920,1080"
$clickArgs = @{
    Delay1 = 4368;  X1 = 3797; Y1 = 106
    Delay2 = 1643;  X2 = 2888; Y2 = 564
    Delay3 = 6089;  X3 = 3593; Y3 = 232
    Delay4 = 719;   X4 = 3544; Y4 = 265
    Delay5 = 1473;  X5 = 2954; Y5 = 666
}

if (-not (Test-Path $profilePath)) {
    New-Item -ItemType Directory -Path $profilePath -Force | Out-Null
}

if ($When -match '^(?i)yesterday$') {
    $iso = (Get-Date).AddDays(-1).ToString('yyyy-MM-dd')
} elseif ($When -match '^(?i)today$') {
    $iso = (Get-Date).ToString('yyyy-MM-dd')
} elseif ($When -match '^\d{4}-\d{2}-\d{2}$') {
    $iso = $When
} else {
    $iso = (Get-Date).ToString('yyyy-MM-dd')
}
$url = "https://connect.garmin.com/modern/sleep/$iso/0"

Write-Host "----------------------------------------------------"
Write-Host "Sky Garmin Click Replay (PowerShell)"
Write-Host ("Target date : {0}" -f $iso)
Write-Host ("URL         : {0}" -f $url)
Write-Host ("Chrome exe  : {0}" -f $chromeExe)
Write-Host "----------------------------------------------------"

$chromeArgs = @(
    "--new-window"
    "--user-data-dir=$profilePath"
    "--profile-directory=Default"
    "--window-position=$windowPos"
    "--window-size=$windowSize"
    $url
)

Write-Host "[setup] Launching Chrome..."
Start-Process -FilePath $chromeExe -ArgumentList $chromeArgs | Out-Null

$body = ""
try {
    $headers = @{ "User-Agent" = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" }
    $resp = Invoke-WebRequest -Uri $url -UseBasicParsing -Headers $headers -TimeoutSec 15
    $body = $resp.Content
} catch {
    $body = $_.Exception.Message
}
if ($body -match "Error 1015" -or $body -match "rate limited") {
    Write-Host "[cooldown] Cloudflare 1015 detected. Exiting early." -ForegroundColor Yellow
    exit 42
}

$posParts  = $windowPos.Split(',')
$sizeParts = $windowSize.Split(',')

& (Join-Path $Tools "window_pos.ps1") `
    -PosX ([int]$posParts[0]) -PosY ([int]$posParts[1]) `
    -Width ([int]$sizeParts[0]) -Height ([int]$sizeParts[1])

Write-Host "[info] Bring the Chrome window into focus. Replay starts in 5 seconds..."
Start-Sleep -Seconds 5

Write-Host "[run] Replaying recorded clicks..."
& (Join-Path $Tools "click_sequence.ps1") @clickArgs

Write-Host "[done] Click sequence finished. Inspect the browser for results."
