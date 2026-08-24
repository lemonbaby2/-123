param(
  [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = 'Stop'
$manifestPath = Join-Path $ProjectRoot 'web\unified\legacy-manifest.json'
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
$failures = @()

foreach ($property in $manifest.files.PSObject.Properties) {
  $relativePath = $property.Name.Replace('/', '\')
  $fullPath = Join-Path $ProjectRoot $relativePath
  if (-not (Test-Path -LiteralPath $fullPath)) {
    $failures += "文件不存在：$relativePath"
    continue
  }
  $actual = (Get-FileHash -LiteralPath $fullPath -Algorithm SHA256).Hash
  if ($actual -ne $property.Value) {
    $failures += "哈希不一致：$relativePath，期望 $($property.Value)，实际 $actual"
  }
}

if ($failures.Count -gt 0) {
  $failures | ForEach-Object { Write-Error $_ }
  exit 1
}

Write-Host '旧网页完整性校验通过：3 个原页面文件均未改动。'
