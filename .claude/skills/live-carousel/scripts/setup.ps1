<#
  live-carousel setup for Windows (replaces the kit's macOS/bash setup.sh). Safe to re-run.

  Run from the repo root:
    powershell -ExecutionPolicy Bypass -File .claude\skills\live-carousel\scripts\setup.ps1

  What it does (nothing global is installed or changed):
    1. checks Node.js 22+ (runs the HyperFrames CLI through npx)
    2. checks ffmpeg + ffprobe on PATH
    3. creates the skill's private venv .claude\skills\live-carousel\.venv with the SIGNED
       python.org Python 3.12 (%LOCALAPPDATA%\Programs\Python\Python312\python.exe) and installs
       numpy + opencv-python-headless into it. (Smart App Control blocks DLLs in uv-downloaded Pythons,
       so never use `uv python install` here.)
    4. checks the already-installed HyperFrames CLI (`npx hyperframes`) and its headless Chrome
    5. reports whether the free media-use SFX pack is present (synthesized stand-ins otherwise)
    6. creates work\live-carousel\ (gitignored) where every carousel project goes
#>
param(
  [switch]$Recreate  # delete and rebuild the venv
)
$ErrorActionPreference = "Continue"
$Skill = Split-Path -Parent $PSScriptRoot
$Repo = (Resolve-Path (Join-Path $Skill "..\..\..")).Path
$Venv = Join-Path $Skill ".venv"
$VenvPy = Join-Path $Venv "Scripts\python.exe"
$Py312 = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"
$HF = if ($env:LIVE_CAROUSEL_HF) { $env:LIVE_CAROUSEL_HF } else { "hyperframes" }
$script:problems = 0
function Ok($m) { Write-Host "  [ok] $m" -ForegroundColor Green }
function Bad($m) { Write-Host "  [!!] $m" -ForegroundColor Red; $script:problems++ }
function Note($m) { Write-Host "       $m" }

Write-Host "live-carousel setup  ($Skill)"

# 1. Node.js 22+
if (Get-Command node -ErrorAction SilentlyContinue) {
  $major = [int](& node -p "process.versions.node.split('.')[0]")
  if ($major -ge 22) { Ok "Node.js $(& node -v)" } else { Bad "Node.js $(& node -v) is too old (need 22+)"; Note "winget install OpenJS.NodeJS.LTS" }
} else {
  Bad "Node.js not found"; Note "winget install OpenJS.NodeJS.LTS   (free), then reopen the terminal"
}

# 2. ffmpeg + ffprobe
if ((Get-Command ffmpeg -ErrorAction SilentlyContinue) -and (Get-Command ffprobe -ErrorAction SilentlyContinue)) {
  $v = ((& ffmpeg -version | Select-Object -First 1) -split " ")[2]
  Ok "ffmpeg $v"
} else {
  Bad "ffmpeg/ffprobe not found on PATH"; Note "winget install Gyan.FFmpeg   (free), then reopen the terminal"
}

# 3. Private venv with the signed Python 3.12 + numpy/opencv
if ($Recreate -and (Test-Path $Venv)) { Remove-Item -Recurse -Force $Venv }
$venvOk = $false
if (Test-Path $VenvPy) {
  & $VenvPy -c "import numpy, cv2" 2>$null
  if ($LASTEXITCODE -eq 0) { $venvOk = $true }
}
if ($venvOk) {
  Ok "Python venv with numpy + opencv ($Venv)"
} elseif (-not (Test-Path $Py312)) {
  Bad "signed Python 3.12 not found at $Py312"
  Note "winget install Python.Python.3.12   (python.org build, signed), then re-run"
} else {
  Write-Host "  ... creating the private venv with $Py312 (numpy, opencv; ~150 MB)"
  if (-not (Test-Path $VenvPy)) { & $Py312 -m venv $Venv }
  & $VenvPy -m pip install -q --disable-pip-version-check --upgrade pip
  & $VenvPy -m pip install -q --disable-pip-version-check -r (Join-Path $Skill "requirements.txt")
  & $VenvPy -c "import numpy, cv2; print('       numpy', numpy.__version__, '| opencv', cv2.__version__)"
  if ($LASTEXITCODE -eq 0) { Ok "Python packages installed in $Venv" } else { Bad "could not install/import numpy + opencv in $Venv" }
}

# 4. HyperFrames CLI (already installed via npx cache) + its headless Chrome
if (Get-Command npx.cmd -ErrorAction SilentlyContinue) {
  $ver = & npx.cmd --yes $HF --version 2>$null | Select-Object -Last 1
  if ($LASTEXITCODE -eq 0 -and $ver) {
    Ok "HyperFrames CLI $ver  (npx $HF; set LIVE_CAROUSEL_HF=hyperframes@<version> to pin)"
    $chrome = & npx.cmd --yes $HF browser ensure 2>$null | Select-Object -Last 1
    if ($LASTEXITCODE -eq 0) { Ok "headless Chrome for rendering" } else { Bad "Chrome for HyperFrames missing"; Note "npx hyperframes browser ensure --force" }
  } else {
    Bad "could not run the HyperFrames CLI through npx (network on first use?)"
  }
} else {
  Bad "npx not found (comes with Node.js)"
}
$sysChrome = "C:\Program Files\Google\Chrome\Application\chrome.exe"
if (Test-Path $sysChrome) { Ok "system Chrome (for opening preview.html): $sysChrome" }

# 5. Optional: the free media-use SFX pack (Pixabay licence) used instead of synthesized stand-ins
$sfx = @("$env:USERPROFILE\.claude\skills\media-use\audio\assets\sfx", "$env:USERPROFILE\.agents\skills\media-use\audio\assets\sfx") | Where-Object { Test-Path $_ } | Select-Object -First 1
if ($sfx) { Ok "real SFX pack found: $sfx" } else { Note "optional: HyperFrames' media-use skill adds a real SFX pack (synthesized stand-ins are used otherwise)" }

# 6. Output folder
$work = Join-Path $Repo "work\live-carousel"
New-Item -ItemType Directory -Force $work | Out-Null
Ok "projects go to $work"

Write-Host ""
if ($script:problems -eq 0) {
  Write-Host "All set. Try: /live-carousel  ""make me a live carousel about <topic>""" -ForegroundColor Green
  exit 0
} else {
  Write-Host "$($script:problems) thing(s) to fix above, then run this again." -ForegroundColor Yellow
  exit 1
}
