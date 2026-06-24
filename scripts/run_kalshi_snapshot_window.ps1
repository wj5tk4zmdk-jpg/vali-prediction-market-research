param(
    [string]$ValiExecutable = "work\.venv\Scripts\vali.exe",
    [string]$OutputRoot = "data\kalshi",
    [int]$IntervalSeconds = 60
)

$ErrorActionPreference = "Stop"
$zone = [System.TimeZoneInfo]::FindSystemTimeZoneById("Eastern Standard Time")
$nowEastern = [System.TimeZoneInfo]::ConvertTime([DateTimeOffset]::UtcNow, $zone)
$windowStart = $nowEastern.Date.AddHours(15).AddMinutes(55)
$windowEnd = $nowEastern.Date.AddHours(16).AddMinutes(5)

if ($nowEastern -lt $windowStart -or $nowEastern -gt $windowEnd) {
    throw "Snapshot window is 15:55-16:05 America/New_York. Current time: $nowEastern"
}

while ($nowEastern -le $windowEnd) {
    & $ValiExecutable kalshi snapshot --out $OutputRoot
    Start-Sleep -Seconds $IntervalSeconds
    $nowEastern = [System.TimeZoneInfo]::ConvertTime([DateTimeOffset]::UtcNow, $zone)
}

