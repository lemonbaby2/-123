param(
  [string]$StateDirectory = (Join-Path $env:LOCALAPPDATA 'NingboSOPUnified\cloudflare-quick')
)

$ErrorActionPreference = 'Stop'
$statePath = Join-Path $StateDirectory 'quick-tunnel-state.json'
if (-not (Test-Path -LiteralPath $statePath)) {
  Write-Host "没有找到本工具生成的运行状态：$statePath"
  exit 0
}

$state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
foreach ($processId in @([int]$state.sop_pid, [int]$state.cvat_pid)) {
  if ($processId -le 0) { continue }
  $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
  if (-not $process) { continue }
  if ($process.ProcessName -ne 'cloudflared') {
    throw "PID $processId 当前不是 cloudflared，拒绝停止。"
  }
  Stop-Process -Id $processId -Force
  Write-Host "已停止 cloudflared PID：$processId"
}

Remove-Item -LiteralPath $statePath -Force
Write-Host 'Quick Tunnel 已停止。日志保留在状态目录中。'
