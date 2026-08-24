param(
  [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot),
  [string]$RuntimeRoot = (Join-Path $env:LOCALAPPDATA 'NingboSOPCVAT8113\runtime'),
  [int]$Port = 8117
)
$ErrorActionPreference='Stop'
$project=(Resolve-Path -LiteralPath $ProjectRoot).Path
$server=Join-Path $project 'server.py'
$python='D:\Anaconda\envs\dl\python.exe'
if(-not(Test-Path -LiteralPath $server)){throw "server.py not found: $server"}
if(-not(Test-Path -LiteralPath $python)){throw "Python not found: $python"}
$listener=Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue
if($listener){Write-Host "SOP V3 is already listening on port $Port (PID $($listener.OwningProcess)).";exit 0}
New-Item -ItemType Directory -Force -Path $RuntimeRoot|Out-Null
$logRoot=Join-Path $RuntimeRoot 'v3_logs';New-Item -ItemType Directory -Force -Path $logRoot|Out-Null
$env:SOP_HOST='0.0.0.0';$env:SOP_PORT=[string]$Port;$env:SOP_RUNTIME_DIR=$RuntimeRoot
$env:SOP_ANNOTATION_DB=Join-Path $RuntimeRoot 'sop_annotations.sqlite3'
$env:SOP_DESKTOP_DIR=Join-Path (Split-Path -Parent $RuntimeRoot) 'desktop'
$env:SOP_SPARK_MODEL_DIR=Join-Path (Split-Path -Parent $RuntimeRoot) 'model-store'
$env:CVAT_PUBLIC_URL='http://10.70.102.210:8081';$env:CVAT_API_URL='http://10.70.102.210:8081';$env:CVAT_TOKEN=''
$stamp=Get-Date -Format 'yyyyMMdd_HHmmss'
$process=Start-Process -FilePath $python -ArgumentList @($server) -WorkingDirectory $project -RedirectStandardOutput (Join-Path $logRoot "server_$stamp.stdout.log") -RedirectStandardError (Join-Path $logRoot "server_$stamp.stderr.log") -WindowStyle Hidden -PassThru
$deadline=(Get-Date).AddSeconds(45);$ready=$false
do{Start-Sleep -Milliseconds 750;try{$health=Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/health" -TimeoutSec 2;$ready=$health.status -eq 'ok'}catch{$ready=$false}}while(-not $ready -and (Get-Date)-lt $deadline)
if(-not $ready){if(Get-Process -Id $process.Id -ErrorAction SilentlyContinue){Stop-Process -Id $process.Id -Force};throw "SOP V3 failed to start; inspect $logRoot"}
$state=[ordered]@{pid=$process.Id;port=$Port;project_root=$project;runtime_root=$RuntimeRoot;started_at=(Get-Date).ToString('yyyy-MM-dd HH:mm:ss')}
$state|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $RuntimeRoot 'v3_server_state.json') -Encoding utf8
Write-Host "SOP V3 started: http://10.70.102.210:$Port/unified-v3/ (PID $($process.Id))"
