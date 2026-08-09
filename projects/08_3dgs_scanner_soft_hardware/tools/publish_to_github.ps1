param(
  [string]$Repo = 'lemonbaby2/-123',
  [string]$ProjectPath = 'projects/08_3dgs_scanner_soft_hardware'
)

$ErrorActionPreference = 'Stop'

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
  throw 'GitHub CLI is not installed or not on PATH.'
}

gh auth status | Out-Null

$root = Resolve-Path (Join-Path $PSScriptRoot '..')

$work = Join-Path ([System.IO.Path]::GetTempPath()) ('publish_3dgs_' + [System.Guid]::NewGuid().ToString('N'))
git clone "https://github.com/$Repo.git" $work
Set-Location $work

$target = Join-Path $work $ProjectPath
New-Item -ItemType Directory -Force -Path (Split-Path $target -Parent) | Out-Null
if (Test-Path -LiteralPath $target) {
  Remove-Item -LiteralPath $target -Recurse -Force
}
Copy-Item -LiteralPath $root -Destination $target -Recurse -Force
Remove-Item -LiteralPath (Join-Path $target '.git') -Recurse -Force -ErrorAction SilentlyContinue

git add $ProjectPath
git commit -m 'add 3dgs scanner soft hardware project'
git push

Write-Host "Published: https://github.com/$Repo/tree/main/$ProjectPath"
