param([switch]$SkipInstaller)

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path -LiteralPath $PSScriptRoot).Path
$pyinstallerExe = 'D:\Anaconda\envs\dl\Scripts\pyinstaller.exe'
$innoExe = Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe'
$distDir = Join-Path $projectRoot 'dist'
$workDir = Join-Path $projectRoot 'build\pyinstaller'
$specDir = Join-Path $projectRoot 'build\spec'
$releaseDir = Join-Path $projectRoot 'release'

if (-not (Test-Path -LiteralPath $pyinstallerExe)) { throw "未找到 dl 环境中的 PyInstaller：$pyinstallerExe" }

foreach ($target in @($distDir, $workDir, $specDir)) {
  $parent = [System.IO.Path]::GetFullPath($projectRoot).TrimEnd('\') + '\'
  $resolved = [System.IO.Path]::GetFullPath($target)
  if (-not $resolved.StartsWith($parent, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "拒绝清理项目目录之外的路径：$resolved"
  }
  if (Test-Path -LiteralPath $resolved) { Remove-Item -LiteralPath $resolved -Recurse -Force }
}

New-Item -ItemType Directory -Path $distDir, $workDir, $specDir, $releaseDir -Force | Out-Null

& $pyinstallerExe `
  --noconfirm `
  --clean `
  --windowed `
  --name NingboSOPCVAT `
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
  --exclude-module qtpy `
  --exclude-module torch `
  --exclude-module torchvision `
  --exclude-module torchaudio `
  --exclude-module ultralytics `
  --exclude-module tensorflow `
  --exclude-module keras `
  --exclude-module onnxruntime `
  --exclude-module transformers `
  --exclude-module cv2 `
  --exclude-module numpy `
  --exclude-module pandas `
  --exclude-module scipy `
  --exclude-module matplotlib `
  --exclude-module sklearn `
  --exclude-module pyarrow `
  --exclude-module datasets `
  --exclude-module IPython `
  --exclude-module pytest `
  --add-data "$projectRoot\server.py;." `
  --add-data "$projectRoot\web;web" `
  --add-data "$projectRoot\config;config" `
  --add-data "$projectRoot\models;models" `
  --add-data "$projectRoot\docs;docs" `
  --add-data "$projectRoot\scripts;scripts" `
  --add-data "$projectRoot\datasets;datasets" `
  --add-data "$projectRoot\camera-gateway;camera-gateway" `
  --add-data "$projectRoot\offline_delivery;offline_delivery" `
  desktop_app.py

if ($LASTEXITCODE -ne 0) { throw "PyInstaller 构建失败，退出码：$LASTEXITCODE" }

$desktopExe = Join-Path $distDir 'NingboSOPCVAT\NingboSOPCVAT.exe'
if (-not (Test-Path -LiteralPath $desktopExe)) { throw "桌面 EXE 未生成：$desktopExe" }

if (-not $SkipInstaller) {
  if (-not (Test-Path -LiteralPath $innoExe)) { throw "未找到 Inno Setup：$innoExe" }
  & $innoExe (Join-Path $projectRoot 'installer\NingboSOPCVAT.iss')
  if ($LASTEXITCODE -ne 0) { throw "安装程序构建失败，退出码：$LASTEXITCODE" }
}

Write-Host "桌面程序：$desktopExe"
if (-not $SkipInstaller) {
  Write-Host "安装程序：$(Join-Path $releaseDir '宁波视觉SOP_CVAT闭环平台_完整安装程序_20260824.exe')"
}
