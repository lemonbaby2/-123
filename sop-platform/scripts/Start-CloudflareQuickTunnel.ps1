param(
  [string]$SopOrigin = 'http://127.0.0.1:8113',
  [string]$CvatOrigin = 'http://10.70.102.210:8081',
  [string]$CvatHostHeader = '10.70.102.210',
  [string]$StateDirectory = (Join-Path $env:LOCALAPPDATA 'NingboSOPUnified\cloudflare-quick')
)

$ErrorActionPreference = 'Stop'

function Resolve-Cloudflared {
  $command = Get-Command cloudflared -ErrorAction SilentlyContinue
  if ($command) { return $command.Source }
  $candidates = @(
    'C:\Program Files (x86)\cloudflared\cloudflared.exe',
    'C:\Program Files\cloudflared\cloudflared.exe'
  )
  foreach ($candidate in $candidates) {
    if (Test-Path -LiteralPath $candidate) { return $candidate }
  }
  throw '未找到 cloudflared。请先运行：winget install --id Cloudflare.cloudflared --exact'
}

function Wait-QuickUrl([string]$LogPath, [int]$Seconds = 35) {
  $deadline = (Get-Date).AddSeconds($Seconds)
  do {
    if (Test-Path -LiteralPath $LogPath) {
      $content = [string](Get-Content -LiteralPath $LogPath -Raw -ErrorAction SilentlyContinue)
      if ($content) {
        $match = [regex]::Match($content, 'https://[a-z0-9-]+\.trycloudflare\.com')
        if ($match.Success) { return $match.Value }
      }
    }
    Start-Sleep -Milliseconds 500
  } while ((Get-Date) -lt $deadline)
  throw "等待 Quick Tunnel 地址超时，请检查日志：$LogPath"
}

$defaultConfig = Join-Path $env:USERPROFILE '.cloudflared\config.yml'
$defaultConfigYaml = Join-Path $env:USERPROFILE '.cloudflared\config.yaml'
if ((Test-Path -LiteralPath $defaultConfig) -or (Test-Path -LiteralPath $defaultConfigYaml)) {
  throw '检测到用户目录下的 Cloudflare config.yml/config.yaml。官方 Quick Tunnel 不支持该情形；请改用 Named Tunnel，或临时改名配置文件后再试。'
}

$cloudflared = Resolve-Cloudflared
New-Item -ItemType Directory -Force -Path $StateDirectory | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$sopError = Join-Path $StateDirectory "sop_$stamp.stderr.log"
$sopOutput = Join-Path $StateDirectory "sop_$stamp.stdout.log"
$cvatError = Join-Path $StateDirectory "cvat_$stamp.stderr.log"
$cvatOutput = Join-Path $StateDirectory "cvat_$stamp.stdout.log"

$sop = Start-Process -FilePath $cloudflared `
  -ArgumentList @('tunnel', '--url', $SopOrigin, '--no-autoupdate', '--loglevel', 'info') `
  -RedirectStandardOutput $sopOutput -RedirectStandardError $sopError -WindowStyle Hidden -PassThru

try {
  $cvat = Start-Process -FilePath $cloudflared `
    -ArgumentList @('tunnel', '--url', $CvatOrigin, '--http-host-header', $CvatHostHeader, '--no-autoupdate', '--loglevel', 'info') `
    -RedirectStandardOutput $cvatOutput -RedirectStandardError $cvatError -WindowStyle Hidden -PassThru
  $sopUrl = Wait-QuickUrl $sopError
  $cvatUrl = Wait-QuickUrl $cvatError
} catch {
  if ($sop -and -not $sop.HasExited) { Stop-Process -Id $sop.Id -Force }
  if ($cvat -and -not $cvat.HasExited) { Stop-Process -Id $cvat.Id -Force }
  throw
}

$state = [ordered]@{
  created_at = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
  sop_url = $sopUrl
  cvat_url = $cvatUrl
  unified_url = "$sopUrl/unified/?cvat=$([uri]::EscapeDataString($cvatUrl))"
  sop_pid = $sop.Id
  cvat_pid = $cvat.Id
  sop_origin = $SopOrigin
  cvat_origin = $CvatOrigin
  cvat_host_header = $CvatHostHeader
  sop_log = $sopError
  cvat_log = $cvatError
}
$statePath = Join-Path $StateDirectory 'quick-tunnel-state.json'
$state | ConvertTo-Json | Set-Content -LiteralPath $statePath -Encoding utf8

Write-Host "SOP 公网地址：$sopUrl"
Write-Host "CVAT 公网地址：$cvatUrl"
Write-Host "一体化入口：$($state.unified_url)"
Write-Host "状态文件：$statePath"
Write-Warning 'Quick Tunnel 只适合测试，进程停止后网址会失效；生产环境请使用 Named Tunnel + Cloudflare Access。'
