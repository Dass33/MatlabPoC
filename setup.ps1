#Requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path

try {
    docker info | Out-Null
} catch {
    Write-Error "Docker Desktop is not running. Please start it and try again."
    exit 1
}

Write-Host "Building matlab-algorithm image..."
Set-Location "$root\matlab"
docker build -t matlab-algorithm:latest .

Write-Host "Building matlabpoc-streamlit image..."
Set-Location $root
docker build -t matlabpoc-streamlit:latest -f streamlit/Dockerfile .

$envFile = "$root\.env"
if (-not (Test-Path $envFile)) {
    $dataDir = "$root\data" -replace "\\", "/"
    Set-Content -Path $envFile -Value "HOST_DATA_DIR=$dataDir"
    Write-Host ".env created with HOST_DATA_DIR=$dataDir"
}

Set-Location $root
docker compose up -d

Write-Host ""
Write-Host "NSM PoC is running at http://localhost:8501"
