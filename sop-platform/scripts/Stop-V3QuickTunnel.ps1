param([string]$StateDirectory=(Join-Path $env:LOCALAPPDATA 'NingboSOPUnifiedV3\cloudflare-quick'))
$ErrorActionPreference='Stop';$statePath=Join-Path $StateDirectory 'v3-tunnel-state.json'
if(-not(Test-Path -LiteralPath $statePath)){Write-Host 'No V3 tunnel state file found.';exit 0}
$state=Get-Content -LiteralPath $statePath -Raw|ConvertFrom-Json;$process=Get-Process -Id ([int]$state.pid) -ErrorAction SilentlyContinue
if($process){if($process.ProcessName -ne 'cloudflared'){throw "PID $($process.Id) is not cloudflared."};Stop-Process -Id $process.Id -Force;Write-Host "Stopped V3 tunnel PID $($process.Id)."}
Remove-Item -LiteralPath $statePath -Force
