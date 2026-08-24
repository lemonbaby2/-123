param(
  [string]$Origin='http://127.0.0.1:8117',
  [string]$StateDirectory=(Join-Path $env:LOCALAPPDATA 'NingboSOPUnifiedV3\cloudflare-quick')
)
$ErrorActionPreference='Stop'
$cloudflared=(Get-Command cloudflared -ErrorAction SilentlyContinue).Source
if(-not $cloudflared){$cloudflared='C:\Program Files (x86)\cloudflared\cloudflared.exe'}
if(-not(Test-Path -LiteralPath $cloudflared)){throw 'cloudflared is not installed.'}
if(Test-Path (Join-Path $env:USERPROFILE '.cloudflared\config.yml')){throw 'Quick Tunnel cannot run while ~/.cloudflared/config.yml exists.'}
New-Item -ItemType Directory -Force -Path $StateDirectory|Out-Null
$stamp=Get-Date -Format 'yyyyMMdd_HHmmss';$errorLog=Join-Path $StateDirectory "v3_$stamp.stderr.log";$outputLog=Join-Path $StateDirectory "v3_$stamp.stdout.log"
$process=Start-Process -FilePath $cloudflared -ArgumentList @('tunnel','--url',$Origin,'--no-autoupdate','--loglevel','info') -RedirectStandardOutput $outputLog -RedirectStandardError $errorLog -WindowStyle Hidden -PassThru
$deadline=(Get-Date).AddSeconds(40);$url=''
do{Start-Sleep -Milliseconds 500;$content=[string](Get-Content -LiteralPath $errorLog -Raw -ErrorAction SilentlyContinue);if($content){$match=[regex]::Match($content,'https://[a-z0-9-]+\.trycloudflare\.com');if($match.Success){$url=$match.Value}}}while(-not $url -and (Get-Date)-lt $deadline)
if(-not $url){if(Get-Process -Id $process.Id -ErrorAction SilentlyContinue){Stop-Process -Id $process.Id -Force};throw "Tunnel URL timeout; inspect $errorLog"}
$v2State=Join-Path $env:LOCALAPPDATA 'NingboSOPUnified\cloudflare-quick\quick-tunnel-state.json';$cvat='http://10.70.102.210:8081'
if(Test-Path -LiteralPath $v2State){$existing=Get-Content -LiteralPath $v2State -Raw|ConvertFrom-Json;if($existing.cvat_url){$cvat=[string]$existing.cvat_url}}
$unified="$url/unified-v3/?cvat=$([uri]::EscapeDataString($cvat))"
[ordered]@{pid=$process.Id;url=$url;unified_url=$unified;cvat_url=$cvat;origin=$Origin;started_at=(Get-Date).ToString('yyyy-MM-dd HH:mm:ss');log=$errorLog}|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $StateDirectory 'v3-tunnel-state.json') -Encoding utf8
Write-Host "V3 public URL: $url";Write-Host "V3 unified URL: $unified";Write-Warning 'Quick Tunnel is for acceptance testing only.'
