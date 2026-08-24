param([string]$RuntimeRoot = (Join-Path $env:LOCALAPPDATA 'NingboSOPCVAT8113\runtime'))
$ErrorActionPreference='Stop'
$statePath=Join-Path $RuntimeRoot 'v3_server_state.json'
if(-not(Test-Path -LiteralPath $statePath)){Write-Host 'No V3 server state file found.';exit 0}
$state=Get-Content -LiteralPath $statePath -Raw|ConvertFrom-Json
$process=Get-Process -Id ([int]$state.pid) -ErrorAction SilentlyContinue
if($process){
  $details=Get-CimInstance Win32_Process -Filter "ProcessId=$($process.Id)"
  if($process.ProcessName -notlike 'python*' -or $details.CommandLine -notmatch 'server\.py'){throw "PID $($process.Id) is not the expected SOP V3 process."}
  Stop-Process -Id $process.Id -Force;Write-Host "Stopped SOP V3 PID $($process.Id)."
}
Remove-Item -LiteralPath $statePath -Force
