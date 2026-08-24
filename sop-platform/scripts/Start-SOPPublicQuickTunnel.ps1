param(
  [int]$Port = 8118,
  [string]$LogFile = ''
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
if (-not $LogFile) {
  $LogFile = Join-Path $projectRoot 'runtime\cloudflared_sop_public_roundtrip.log'
}
$cloudflared = 'C:\Program Files (x86)\cloudflared\cloudflared.exe'
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $LogFile) | Out-Null
& $cloudflared tunnel --url "http://127.0.0.1:$Port" --no-autoupdate --loglevel info 2>&1 | Tee-Object -FilePath $LogFile -Append

