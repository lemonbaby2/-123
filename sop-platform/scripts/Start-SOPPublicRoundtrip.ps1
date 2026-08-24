param(
  [int]$Port = 8118,
  [string]$CvatPublicUrl = 'https://zum-hugh-focusing-africa.trycloudflare.com',
  [int]$CvatProjectId = 2
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$runtimeRoot = Join-Path $env:LOCALAPPDATA 'NingboSOPCVAT8113\runtime'
$python = 'D:\Anaconda\envs\dl\python.exe'

$env:SOP_HOST = '0.0.0.0'
$env:SOP_PORT = [string]$Port
$env:SOP_RUNTIME_DIR = $runtimeRoot
$env:SOP_CONFIG_DIR = Join-Path $projectRoot 'config'
$env:SOP_BAIDU_DATA_ROOT = 'D:\NingboSOPData\Baidu_20260819_21'
$env:CVAT_PUBLIC_URL = $CvatPublicUrl.TrimEnd('/')
$env:CVAT_API_URL = 'http://10.70.102.210:8081'
$env:CVAT_PROJECT_ID = [string]$CvatProjectId
$env:SOP_SECURE_COOKIE = '0'

Set-Location -LiteralPath $projectRoot
& $python (Join-Path $projectRoot 'server.py')
