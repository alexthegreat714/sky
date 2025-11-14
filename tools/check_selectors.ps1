param([string]$When = (Get-Date).ToString(''yyyy-MM-dd''))
$Url = "https://connect.garmin.com/modern/sleep/$When/0"
Write-Host "Selector check for $Url"
$headers = @{ "User-Agent" = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" }
try {
    $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -Headers $headers -TimeoutSec 15
    $body = $resp.Content
} catch {
    Write-Host "[error] Failed to fetch page: $($_.Exception.Message)" -ForegroundColor Red
    exit 2
}
$menu_ok = $body -match "aria-label=\"More options\"" -or $body -match "aria-label='More options'"
$csv_ok = $body -match "Download CSV" -or $body -match "Export CSV"
$code = 0
if ($menu_ok) { Write-Host "[ok] Menu selector detected." } else { Write-Host "[missing] Menu selector not found." -ForegroundColor Yellow; $code = 1 }
if ($csv_ok) { Write-Host "[ok] Export selector detected." } else { Write-Host "[missing] Export selector not found." -ForegroundColor Yellow; $code = 1 }
exit $code
