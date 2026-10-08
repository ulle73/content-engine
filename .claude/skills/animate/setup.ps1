# Animate skill - local setup for content-engine on Windows (replaces the upstream `npm i -g playwright`).
# Run from the repo root:  powershell -ExecutionPolicy Bypass -File .claude/skills/animate/setup.ps1 [-Whisper] [-BundledChromium]
#   - checks node, ffmpeg/ffprobe and Google Chrome
#   - installs the Playwright npm package LOCALLY into work/animate/node_modules (gitignored), without a browser download:
#     the tools launch the system Chrome (tools/pw.mjs)
#   - -Whisper: adds faster-whisper (word timing for voice-overs) to library/.venv, created with the signed Python 3.12
#     (Smart App Control blocks uv-downloaded Pythons). Optional; without it word times are estimated.
#   - -BundledChromium: also downloads Playwright's own Chromium (~150 MB), only if the system Chrome can't be used
# Installs nothing globally.
param([switch]$Whisper, [switch]$BundledChromium)
$ErrorActionPreference = 'Stop'
$skill = Split-Path -Parent $MyInvocation.MyCommand.Path
$repo = (Resolve-Path (Join-Path $skill '..\..\..')).Path
$work = Join-Path $repo 'work\animate'
$ok = $true

function Check($name, $cmd) {
  $c = Get-Command $cmd -ErrorAction SilentlyContinue
  if ($c) { Write-Host ("ok   {0,-8} {1}" -f $name, $c.Source) } else { Write-Host ("MISS {0,-8} (install it, e.g. winget)" -f $name); $script:ok = $false }
}
Check 'node' 'node'
Check 'npm' 'npm'
Check 'ffmpeg' 'ffmpeg'
Check 'ffprobe' 'ffprobe'
$chrome = @($env:ANIMATE_CHROME, "$env:ProgramFiles\Google\Chrome\Application\chrome.exe", "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe", "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe") |
  Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
if ($chrome) { Write-Host "ok   chrome   $chrome" } elseif (-not $BundledChromium) { Write-Host 'MISS chrome    (install Google Chrome, set ANIMATE_CHROME, or rerun with -BundledChromium)'; $ok = $false }

New-Item -ItemType Directory -Force $work | Out-Null
if (-not (Test-Path (Join-Path $work 'node_modules\playwright'))) {
  $env:PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD = '1'
  Push-Location $work
  try {
    if (-not (Test-Path 'package.json')) { npm init -y | Out-Null }
    npm i -D playwright@1.63.0
  } finally { Pop-Location }
}
Write-Host "ok   playwright $(Join-Path $work 'node_modules\playwright')"
if ($BundledChromium) {
  Push-Location $work
  try { Remove-Item Env:\PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD -ErrorAction SilentlyContinue; npx playwright install chromium } finally { Pop-Location }
}

if ($Whisper) {
  $venv = Join-Path $repo 'library\.venv'
  $py312 = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'
  if (-not (Test-Path (Join-Path $venv 'Scripts\python.exe'))) {
    if (-not (Test-Path $py312)) { throw "signed Python 3.12 not found at $py312" }
    & $py312 -m venv $venv
  }
  & (Join-Path $venv 'Scripts\python.exe') -m pip install faster-whisper
  Write-Host "ok   faster-whisper in $venv (voice.mjs uses it automatically)"
}

if ($ok) { Write-Host "`nReady. Try: node .claude/skills/animate/tools/gallery.mjs work/animate/styles.png" } else { Write-Host "`nSomething is missing (see MISS above)."; exit 1 }
