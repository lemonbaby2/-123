param([switch]$SkipInstaller)

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path -LiteralPath $PSScriptRoot).Path
$pyinstallerExe = 'D:\Anaconda\envs\dl\Scripts\pyinstaller.exe'
$innoExe = Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe'
$distDir = Join-Path $projectRoot 'dist-unified'
$workDir = Join-Path $projectRoot 'build\pyinstaller-unified'
$specDir = Join-Path $projectRoot 'build\spec-unified'
$releaseDir = Join-Path $projectRoot 'release-unified'

if (-not (Test-Path -LiteralPath $pyinstallerExe)) { throw "未找到 dl 环境中的 PyInstaller：$pyinstallerExe" }

$projectPrefix = [System.IO.Path]::GetFullPath($projectRoot).TrimEnd('\') + '\'
foreach ($target in @($distDir, $workDir, $specDir)) {
  $resolved = [System.IO.Path]::GetFullPath($target)
  if (-not $resolved.StartsWith($projectPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "拒绝清理项目目录之外的路径：$resolved"
  }
  if (Test-Path -LiteralPath $resolved) { Remove-Item -LiteralPath $resolved -Recurse -Force }
}

New-Item -ItemType Directory -Path $distDir, $workDir, $specDir, $releaseDir -Force | Out-Null

& $pyinstallerExe `
  --noconfirm `
  --clean `
  --windowed `
  --name NingboSOPUnified `
  --distpath $distDir `
  --workpath $workDir `
  --specpath $specDir `
  --collect-data webview `
  --hidden-import webview.platforms.edgechromium `
  --hidden-import webview.platforms.winforms `
  --exclude-module webview.platforms.qt `
  --exclude-module webview.platforms.gtk `
  --exclude-module webview.platforms.cocoa `
  --exclude-module PyQt6 `
  --exclude-module PyQt5 `
  --exclude-module PySide6 `
  --exclude-module PySide2 `
  --exclude-module torch `
  --exclude-module torchvision `
  --exclude-module ultralytics `
  --exclude-module tensorflow `
  --exclude-module cv2 `
  --exclude-module numpy `
  --exclude-module pandas `
  unified_desktop_app.py

if ($LASTEXITCODE -ne 0) { throw "V2 客户端 PyInstaller 构建失败，退出码：$LASTEXITCODE" }

$desktopExe = Join-Path $distDir 'NingboSOPUnified\NingboSOPUnified.exe'
if (-not (Test-Path -LiteralPath $desktopExe)) { throw "V2 桌面 EXE 未生成：$desktopExe" }

if (-not $SkipInstaller) {
  if (-not (Test-Path -LiteralPath $innoExe)) { throw "未找到 Inno Setup：$innoExe" }
  & $innoExe (Join-Path $projectRoot 'installer\NingboSOPUnified.iss')
  if ($LASTEXITCODE -ne 0) { throw "V2 安装程序构建失败，退出码：$LASTEXITCODE" }
}

Write-Host "V2 桌面程序：$desktopExe"
if (-not $SkipInstaller) {
  Write-Host "V2 安装程序：$(Join-Path $releaseDir '宁波SOP_CVAT一体化工作台_V2_安装程序_20260824.exe')"
}
