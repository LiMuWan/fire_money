param(
    [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$OutputDir = ""
)

$ErrorActionPreference = "Stop"

if (-not $OutputDir) {
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $OutputDir = Join-Path $ProjectRoot "exports\demo_ai_inbox_$timestamp"
}

if (-not (Test-Path -LiteralPath $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir | Out-Null
}

$scenarios = @(
    @{ Name = "default";  Args = @("--scenario", "default") },
    @{ Name = "triage";   Args = @("--scenario", "triage", "--sort", "priority") },
    @{ Name = "resolved"; Args = @("--scenario", "resolved", "--sort", "open", "--only-unhandled") }
)

Write-Host "Running AI inbox demo suite..."
Write-Host "Output directory: $OutputDir"

foreach ($scenario in $scenarios) {
    $name = [string]$scenario.Name
    $args = @(".\tools\demo_ai_inbox_flow.py") + $scenario.Args
    $outputPath = Join-Path $OutputDir "$name.txt"
    Write-Host " - Scenario: $name"
    $result = & python @args 2>&1
    $result | Set-Content -LiteralPath $outputPath -Encoding UTF8
}

$summaryPath = Join-Path $OutputDir "README.txt"
$summary = @"
AI Inbox demo suite output

Generated at: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

Files:
- default.txt
- triage.txt
- resolved.txt

Recommended review order:
1. default
2. triage
3. resolved
"@
Set-Content -LiteralPath $summaryPath -Value $summary -Encoding UTF8

Write-Host "Done."
Write-Host "Artifacts:"
Get-ChildItem -LiteralPath $OutputDir | Select-Object Name, Length
