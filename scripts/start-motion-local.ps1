param([ValidateRange(1,1440)][int]$IdleMinutes = 15)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$credentialPath = Join-Path $taskRoot 'data/motion-local/token.dpapi'
if (-not (Test-Path -LiteralPath $credentialPath)) {
    throw 'Motion-rendering är inte konfigurerad på den här datorn.'
}
$encryptedToken = (Get-Content -LiteralPath $credentialPath -Raw).Trim()
$secureToken = $encryptedToken | ConvertTo-SecureString
$pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureToken)
try {
    $env:MOTION_WORKER_TOKEN = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
}
$env:MOTION_API_URL = 'https://content-engine-mcp.onrender.com'
$env:MOTION_WORKER_MODE = 'pull'
$env:MOTION_IDLE_SECONDS = [string]($IdleMinutes * 60)
$env:MOTION_LICENSE_MODE = Get-Content -LiteralPath (Join-Path $taskRoot 'data/motion-local/license-mode.txt') -Raw
$env:MOTION_LICENSE_MODE = $env:MOTION_LICENSE_MODE.Trim()
$env:PORT = '8787'
$localBinaries = Join-Path $taskRoot 'data/motion-local/binaries'
if (Test-Path -LiteralPath (Join-Path $localBinaries 'ffmpeg.exe')) {
    $env:REMOTION_BINARIES_DIRECTORY = $localBinaries
}
Push-Location (Join-Path $taskRoot 'motion-renderer')
try {
    if (-not (Test-Path 'build/index.html')) { throw 'Bygg renderaren med npm run build först.' }
    Write-Host "Motion-rendering är igång. Öppna projektet och ladda om sidan. Stängs efter $IdleMinutes minuters inaktivitet."
    & node worker.mjs
    if ($LASTEXITCODE -ne 0) { throw 'Motion-renderingen avbröts. Kontrollera loggen.' }
} finally {
    Remove-Item Env:MOTION_WORKER_TOKEN -ErrorAction SilentlyContinue
    Pop-Location
}
