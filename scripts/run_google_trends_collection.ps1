param(
    [string]$ValiExecutable = "work\.venv\Scripts\vali.exe",
    [string]$OutputRoot = "data\google_trends",
    [string]$Manifest = ""
)

$ErrorActionPreference = "Stop"

if ($env:VALI_ENABLE_GOOGLE_TRENDS_COLLECTION -ne "1") {
    throw "Google Trends collection is disabled. Set VALI_ENABLE_GOOGLE_TRENDS_COLLECTION=1 only after official alpha access, authentication, and quota handling are configured."
}

$arguments = @("trends", "collect", "--out", $OutputRoot)
if ($Manifest) {
    $arguments += @("--manifest", $Manifest)
}

& $ValiExecutable @arguments
