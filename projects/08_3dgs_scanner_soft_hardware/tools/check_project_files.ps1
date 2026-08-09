param(
  [string]$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
)

$required = @(
  'README.md',
  'PROJECT_MANIFEST.md',
  'docs/hardware_overview.md',
  'docs/safety/battery_and_power.md',
  'docs/references/research_repositories.md',
  'docs/references/reference_projects.csv',
  'hardware/altium_sources/README.md',
  'hardware/production/README.md',
  'software/README.md',
  'firmware/README.md'
)

$missing = @()
foreach ($rel in $required) {
  $path = Join-Path $Root $rel
  if (-not (Test-Path -LiteralPath $path)) {
    $missing += $rel
  }
}

if ($missing.Count -gt 0) {
  Write-Host 'Missing required project files:'
  $missing | ForEach-Object { Write-Host " - $_" }
  exit 1
}

Write-Host "Project file check passed: $($required.Count) required files present."
