param(
    [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$OutputDir = "",
    [switch]$SkipBuild,
    [switch]$SkipDemoSuite,
    [switch]$SkipQuickTests,
    [switch]$IncludeFullTests
)

$ErrorActionPreference = "Stop"

function New-Directory([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path | Out-Null
    }
}

function Write-Step([string]$Message) {
    Write-Host "==> $Message"
}

function Copy-IfExists([string]$SourcePath, [string]$DestinationPath) {
    if (Test-Path -LiteralPath $SourcePath) {
        Copy-Item -LiteralPath $SourcePath -Destination $DestinationPath -Force
    }
}

function Copy-LatestArtifact([string]$SourcePath, [string]$LatestFileName) {
    if (-not (Test-Path -LiteralPath $SourcePath)) {
        return
    }
    $latestPath = Join-Path (Split-Path -Parent $SourcePath) $LatestFileName
    Copy-Item -LiteralPath $SourcePath -Destination $latestPath -Force
}

$projectRoot = (Resolve-Path $ProjectRoot).Path
if (-not $OutputDir) {
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $OutputDir = Join-Path $projectRoot "releases\ai_inbox_release_bundle_$timestamp"
}

New-Directory $OutputDir
$artifactsOut = Join-Path $OutputDir "artifacts"
$materialsOut = Join-Path $OutputDir "materials"
New-Directory $artifactsOut
New-Directory $materialsOut
$buildLogPath = Join-Path $OutputDir "build_release_package.txt"
$materialsLogPath = Join-Path $OutputDir "prepare_ai_inbox_release_materials.txt"

Write-Step "Building / packaging desktop release artifacts"
$buildArgs = @(
    "-ExecutionPolicy", "Bypass",
    "-File", (Join-Path $projectRoot "tools\build_release_package.ps1"),
    "-ProjectRoot", $projectRoot
)
if ($SkipBuild) {
    $buildArgs += "-SkipBuild"
}
$buildCommand = 'powershell.exe ' + (($buildArgs | ForEach-Object { if ($_ -match '\s') { '"' + $_ + '"' } else { $_ } }) -join ' ')
cmd /c "$buildCommand > `"$buildLogPath`" 2>&1"
$buildExitCode = $LASTEXITCODE
if ($buildExitCode -ne 0) {
    throw "build_release_package.ps1 failed. See $buildLogPath"
}

$releaseDir = Join-Path $projectRoot "releases"
$latestPortable = Get-ChildItem -LiteralPath $releaseDir -Filter "quant_hunter_portable_*.zip" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
$latestBundle = Get-ChildItem -LiteralPath $releaseDir -Filter "quant_hunter_bundle_*.zip" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
$latestInstaller = Get-ChildItem -LiteralPath $releaseDir -Filter "quant_hunter_setup_*.exe" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
$latestSfx = Get-ChildItem -LiteralPath $releaseDir -Filter "quant_hunter_self_extract_*.exe" | Sort-Object LastWriteTime -Descending | Select-Object -First 1

Write-Step "Collecting AI inbox materials"
$materialArgs = @(
    "-ExecutionPolicy", "Bypass",
    "-File", (Join-Path $projectRoot "tools\prepare_ai_inbox_release_materials.ps1"),
    "-ProjectRoot", $projectRoot,
    "-OutputDir", $materialsOut
)
if ($SkipDemoSuite) {
    $materialArgs += "-SkipDemoSuite"
}
if ($SkipQuickTests) {
    $materialArgs += "-SkipQuickTests"
}
if ($IncludeFullTests) {
    $materialArgs += "-IncludeFullTests"
}
$materialsCommand = 'powershell.exe ' + (($materialArgs | ForEach-Object { if ($_ -match '\s') { '"' + $_ + '"' } else { $_ } }) -join ' ')
cmd /c "$materialsCommand > `"$materialsLogPath`" 2>&1"
$materialsExitCode = $LASTEXITCODE
if ($materialsExitCode -ne 0) {
    throw "prepare_ai_inbox_release_materials.ps1 failed. See $materialsLogPath"
}

Write-Step "Copying release artifacts into bundle folder"
if ($latestPortable) {
    Copy-IfExists $latestPortable.FullName (Join-Path $artifactsOut $latestPortable.Name)
}
if ($latestBundle) {
    Copy-IfExists $latestBundle.FullName (Join-Path $artifactsOut $latestBundle.Name)
}
if ($latestInstaller) {
    Copy-IfExists $latestInstaller.FullName (Join-Path $artifactsOut $latestInstaller.Name)
}
if ($latestSfx) {
    Copy-IfExists $latestSfx.FullName (Join-Path $artifactsOut $latestSfx.Name)
}

$readmePath = Join-Path $OutputDir "README.txt"
$readme = @"
AI Inbox release bundle

Generated at: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

Folders:
- artifacts\
- materials\

Recommended order:
1. artifacts\quant_hunter_setup_*.exe or quant_hunter_bundle_*.zip
2. materials\docs\RELEASE_NOTES_2026-04-19_AI_INBOX.md
3. materials\docs\AI_INBOX_ACCEPTANCE_QUICKSTART.md
4. materials\demo\
5. build_release_package.txt / prepare_ai_inbox_release_materials.txt for logs

Convenience scripts:
- tools\build_release_package.ps1
- tools\prepare_ai_inbox_release_materials.ps1
- tools\run_ai_inbox_demo_suite.ps1
"@
Set-Content -LiteralPath $readmePath -Value $readme -Encoding UTF8

$zipPath = "${OutputDir}.zip"
if (Test-Path -LiteralPath $zipPath) {
    Remove-Item -LiteralPath $zipPath -Force
}
Write-Step "Creating distributable ZIP"
Compress-Archive -Path (Join-Path $OutputDir "*") -DestinationPath $zipPath -CompressionLevel Optimal
Copy-LatestArtifact -SourcePath $zipPath -LatestFileName "ai_inbox_release_bundle_latest.zip"

Write-Step "Done"
Get-ChildItem -LiteralPath $OutputDir | Select-Object Name, LastWriteTime
Write-Host "ZIP: $zipPath"
