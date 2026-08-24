param([switch]$SkipInstaller)
$ErrorActionPreference='Stop'
$root=(Resolve-Path -LiteralPath $PSScriptRoot).Path
$pyinstaller='D:\Anaconda\envs\dl\Scripts\pyinstaller.exe'
$iscc=Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe'
$dist=Join-Path $root 'dist-v3';$work=Join-Path $root 'build\pyinstaller-v3';$spec=Join-Path $root 'build\spec-v3';$release=Join-Path $root 'release-v3'
if(-not(Test-Path -LiteralPath $pyinstaller)){throw "PyInstaller not found: $pyinstaller"}
$prefix=[IO.Path]::GetFullPath($root).TrimEnd('\')+'\'
foreach($target in @($dist,$work,$spec)){$full=[IO.Path]::GetFullPath($target);if(-not $full.StartsWith($prefix,[StringComparison]::OrdinalIgnoreCase)){throw "unsafe build path: $full"};if(Test-Path -LiteralPath $full){Remove-Item -LiteralPath $full -Recurse -Force}}
New-Item -ItemType Directory -Force -Path $dist,$work,$spec,$release|Out-Null
& $pyinstaller --noconfirm --clean --windowed --name NingboSOPUnifiedV3 --distpath $dist --workpath $work --specpath $spec --collect-data webview --hidden-import webview.platforms.edgechromium --hidden-import webview.platforms.winforms --exclude-module webview.platforms.qt --exclude-module PyQt6 --exclude-module PyQt5 --exclude-module PySide6 --exclude-module PySide2 --exclude-module torch --exclude-module ultralytics --exclude-module cv2 --exclude-module numpy --exclude-module pandas unified_v3_desktop.py
if($LASTEXITCODE -ne 0){throw "PyInstaller failed: $LASTEXITCODE"}
if(-not $SkipInstaller){& $iscc (Join-Path $root 'installer\NingboSOPUnifiedV3.iss');if($LASTEXITCODE -ne 0){throw "Inno Setup failed: $LASTEXITCODE"}}
Write-Host (Join-Path $dist 'NingboSOPUnifiedV3\NingboSOPUnifiedV3.exe')
if(-not $SkipInstaller){Write-Host (Join-Path $release '宁波SOP多人标注与决策平台_V3_安装程序_20260824.exe')}
