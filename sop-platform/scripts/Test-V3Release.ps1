param([string]$ProjectRoot=(Split-Path -Parent $PSScriptRoot))
$ErrorActionPreference='Stop'
$root=(Resolve-Path -LiteralPath $ProjectRoot).Path
$manifestPath=Join-Path $root 'web\unified-v3\legacy-manifest.json'
if(-not(Test-Path -LiteralPath $manifestPath)){throw "missing manifest: $manifestPath"}
$manifest=Get-Content -LiteralPath $manifestPath -Raw|ConvertFrom-Json
foreach($entry in $manifest.files.PSObject.Properties){
  $path=Join-Path $root ($entry.Name -replace '/','\')
  if(-not(Test-Path -LiteralPath $path)){throw "legacy file missing: $($entry.Name)"}
  $actual=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
  if($actual -ne [string]$entry.Value){throw "legacy file changed: $($entry.Name) expected=$($entry.Value) actual=$actual"}
}
$required=@(
  'server.py','unified_v3_desktop.py','web\unified-v3\index.html','web\unified-v3\v3.css',
  'web\unified-v3\v3.js','scripts\provision_annotation_accounts.py',
  'docs\40_V3多人标注审计与公网部署说明_20260824.md'
)
foreach($relative in $required){if(-not(Test-Path -LiteralPath (Join-Path $root $relative))){throw "required V3 file missing: $relative"}}
Write-Host "V3 release integrity PASS: legacy pages unchanged; required files present."
