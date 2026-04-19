param(
    [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$OutputDir = "",
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

$projectRoot = (Resolve-Path $ProjectRoot).Path
if (-not $OutputDir) {
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $OutputDir = Join-Path $projectRoot "exports\ai_inbox_release_$timestamp"
}

New-Directory $OutputDir
$docsOut = Join-Path $OutputDir "docs"
$demoOut = Join-Path $OutputDir "demo"
New-Directory $docsOut

$copiedDocs = @(
    "docs\AI_INBOX_ACCEPTANCE_QUICKSTART.md",
    "docs\RELEASE_NOTES_2026-04-19_AI_INBOX.md",
    "docs\product\iteration-83-message-driven-workflow-acceptance.md",
    "docs\product\iteration-84-message-workflow-manual-checklist.md",
    "docs\product\iteration-85-ai-review-and-message-center-inbox.md",
    "docs\product\iteration-86-message-center-dashboard-and-sort.md",
    "docs\product\iteration-87-demo-and-acceptance-playbook.md"
)

Write-Step "Collecting documentation"
foreach ($relativePath in $copiedDocs) {
    $source = Join-Path $projectRoot $relativePath
    if (-not (Test-Path -LiteralPath $source)) {
        continue
    }
    $destination = Join-Path $docsOut (Split-Path $relativePath -Leaf)
    Copy-Item -LiteralPath $source -Destination $destination -Force
}

if (-not $SkipDemoSuite) {
    Write-Step "Running AI inbox demo suite"
    & powershell -ExecutionPolicy Bypass -File (Join-Path $projectRoot "tools\run_ai_inbox_demo_suite.ps1") -ProjectRoot $projectRoot -OutputDir $demoOut
}

if (-not $SkipQuickTests) {
    Write-Step "Running quick AI inbox verification tests"
    $quickTestOut = Join-Path $OutputDir "quick_unittest.txt"
    $quickTestCommand = 'python -m unittest -v tests.test_message_center tests.test_ai_review 2>&1'
    $quickTestResult = cmd /c $quickTestCommand
    $quickTestResult | Set-Content -LiteralPath $quickTestOut -Encoding UTF8
}

if ($IncludeFullTests) {
    Write-Step "Running full unittest discover suite"
    $fullTestOut = Join-Path $OutputDir "full_unittest.txt"
    $fullTestCommand = 'python -m unittest discover -s tests -v 2>&1'
    $fullTestResult = cmd /c $fullTestCommand
    $fullTestResult | Set-Content -LiteralPath $fullTestOut -Encoding UTF8
}

$readmePath = Join-Path $OutputDir "README.txt"
$readme = @"
AI Inbox release materials

Generated at: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

Contents:
- docs\
- demo\
- quick_unittest.txt
- full_unittest.txt (only when -IncludeFullTests is used)

Recommended order:
1. Read RELEASE_NOTES_2026-04-19_AI_INBOX.md
2. Read AI_INBOX_ACCEPTANCE_QUICKSTART.md
3. Review the demo outputs under demo\
4. If needed, re-run:
   python .\tools\demo_ai_inbox_flow.py --scenario default
"@
Set-Content -LiteralPath $readmePath -Value $readme -Encoding UTF8

Write-Step "Done"
Get-ChildItem -LiteralPath $OutputDir | Select-Object Name, Length, LastWriteTime
