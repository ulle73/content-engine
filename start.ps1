$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$taskPort = if ($env:PORT) { [int]$env:PORT } else { 8765 }
if (Get-NetTCPConnection -LocalPort $taskPort -State Listen -ErrorAction SilentlyContinue) {
    throw "Port $taskPort används redan. Stäng den befintliga servern innan du startar en ny instans."
}
& .\.venv\Scripts\python.exe server.py
