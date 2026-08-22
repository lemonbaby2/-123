$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$BackupRoot = Join-Path $Root "backup"
$DataArchive = Join-Path $BackupRoot "cvat_data.tar.gz"
$DbArchive = Join-Path $BackupRoot "cvat_db.tar.gz"

if (-not (Test-Path $DataArchive)) { throw "Missing $DataArchive" }
if (-not (Test-Path $DbArchive)) { throw "Missing $DbArchive" }

docker volume create cvat_cvat_data | Out-Null
docker volume create cvat_cvat_db | Out-Null

docker run --rm `
    -v "cvat_cvat_data:/target" `
    -v "${BackupRoot}:/backup:ro" `
    cvat-offline/alpine:3.22-amd64 sh -c "cd /target && tar -xzf /backup/cvat_data.tar.gz"

docker run --rm `
    -v "cvat_cvat_db:/target" `
    -v "${BackupRoot}:/backup:ro" `
    cvat-offline/alpine:3.22-amd64 sh -c "cd /target && tar -xzf /backup/cvat_db.tar.gz"

Write-Host "CVAT data volumes restored. Start the launcher from $Root"
