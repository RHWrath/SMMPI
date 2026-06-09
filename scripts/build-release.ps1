# Builds the stakeholder Windows release ZIP (same layout as .github/workflows/release-windows.yml).
# From the SMMPI repo root:
#   .\scripts\build-release.ps1
#   .\scripts\build-release.ps1 -Version "1.0.1"
# If the repo path contains spaces, use: scripts\build-release.cmd

#requires -Version 5.1
param(
    [string]$Version = "1.0.0"
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

$publishDir = "artifacts/publish"
$releaseRoot = "artifacts/release-root"
$zipName = "SMMPI-Operator-windows-v$Version.zip"

$required = @(
    "tools/adb.exe",
    "tools/scrcpy.exe",
    "tools/scrcpy-server",
    "tools/SDL3.dll",
    "packages/Prototype/ffmpeg/ffmpeg.exe",
    "packages/Prototype/ffmpeg/ffprobe.exe"
)
$missing = $required | Where-Object { -not (Test-Path $_) }
if ($missing.Count -gt 0) {
    throw "Missing files required for release packaging:`n$($missing -join "`n")"
}

Write-Host "Publishing SMMPI (self-contained win-x64)..." -ForegroundColor Cyan
dotnet publish "src/Presentation/SMMPI.App/SMMPI.App.csproj" `
    -c Release `
    -r win-x64 `
    --self-contained true `
    /p:PublishSingleFile=false `
    -o $publishDir
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Assembling release folder..." -ForegroundColor Cyan
if (Test-Path $releaseRoot) { Remove-Item $releaseRoot -Recurse -Force }
New-Item -ItemType Directory -Path $releaseRoot | Out-Null

Copy-Item "$publishDir/*" $releaseRoot -Recurse -Force
Copy-Item "tools" "$releaseRoot/tools" -Recurse -Force
New-Item -ItemType Directory -Path "$releaseRoot/packages/Prototype/ffmpeg" -Force | Out-Null
Copy-Item "packages/Prototype/ffmpeg/*" "$releaseRoot/packages/Prototype/ffmpeg/" -Force
Copy-Item "docs/Opstarten.md" "$releaseRoot/Opstarten.md" -Force

Write-Host "Creating ZIP..." -ForegroundColor Cyan
if (Test-Path $zipName) { Remove-Item $zipName -Force }
Compress-Archive -Path "$releaseRoot/*" -DestinationPath $zipName

$zip = Get-Item $zipName
Write-Host ""
Write-Host "Done." -ForegroundColor Green
Write-Host "  ZIP:     $($zip.FullName) ($([math]::Round($zip.Length / 1MB, 2)) MB)"
Write-Host "  Unpacked: $(Resolve-Path $releaseRoot)"
Write-Host "  Run:     $(Join-Path $releaseRoot 'SMMPI.exe')"
