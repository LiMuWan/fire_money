param(
    [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$DistRoot = "dist",
    [string]$AppFolderName = "quant_hunter",
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"

function New-Directory([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path | Out-Null
    }
}

function Copy-LatestArtifact([string]$SourcePath, [string]$LatestFileName) {
    if (-not (Test-Path -LiteralPath $SourcePath)) {
        return
    }

    $latestPath = Join-Path (Split-Path -Parent $SourcePath) $LatestFileName
    Copy-Item -LiteralPath $SourcePath -Destination $latestPath -Force
}

function Find-SevenZipExecutable {
    $candidates = @(
        "C:\Program Files\7-Zip\7z.exe",
        "C:\Program Files (x86)\7-Zip\7z.exe",
        "C:\Program Files\Tencent\Androws\Application\5.10.5600.5370\7z.exe"
    )

    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
    }

    $command = Get-Command 7z.exe -ErrorAction SilentlyContinue
    if ($command -and $command.Source) {
        return $command.Source
    }

    return $null
}

function Find-SevenZipSfxModule([string]$SevenZipExe) {
    if (-not $SevenZipExe) {
        return $null
    }

    $baseDir = Split-Path -Parent $SevenZipExe
    foreach ($name in @("7zCon.sfx", "7z.sfx", "7zS.sfx")) {
        $candidate = Join-Path $baseDir $name
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
    }

    return $null
}

function Find-InnoSetupCompiler {
    $candidates = @(
        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        "C:\Program Files\Inno Setup 6\ISCC.exe"
    )

    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
    }

    $command = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($command -and $command.Source) {
        return $command.Source
    }

    return $null
}

function Get-ShortPath([string]$Path) {
    $result = cmd /c "for %I in (""$Path"") do @echo %~sI" 2>$null
    if (-not $result) {
        throw "Unable to resolve short path for: $Path"
    }
    return ($result | Select-Object -Last 1).Trim()
}

$projectRoot = (Resolve-Path $ProjectRoot).Path
$distDir = Join-Path $projectRoot $DistRoot
$appDir = Join-Path $distDir $AppFolderName
$releaseDir = Join-Path $projectRoot "releases"
$stageDir = Join-Path $projectRoot ".installer_build"
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

if (-not $SkipBuild) {
    $buildScript = Join-Path $projectRoot "build_exe.bat"
    if (-not (Test-Path -LiteralPath $buildScript)) {
        throw "Build script not found: $buildScript"
    }
    Write-Host "Building application with PyInstaller..."
    & $buildScript --app-only
    if ($LASTEXITCODE -ne 0) {
        throw "build_exe.bat failed with exit code $LASTEXITCODE"
    }
}

if (-not (Test-Path -LiteralPath $appDir)) {
    throw "Application folder not found: $appDir"
}

New-Directory $releaseDir
if (Test-Path -LiteralPath $stageDir) {
    Remove-Item -LiteralPath $stageDir -Recurse -Force
}
New-Directory $stageDir

$portableZipName = "quant_hunter_portable_$timestamp.zip"
$portableZipPath = Join-Path $releaseDir $portableZipName
$bundleZipName = "quant_hunter_bundle_$timestamp.zip"
$bundleZipPath = Join-Path $releaseDir $bundleZipName
$installerName = "quant_hunter_setup_$timestamp.exe"
$installerPath = Join-Path $releaseDir $installerName
$sfxName = "quant_hunter_self_extract_$timestamp.exe"
$sfxPath = Join-Path $releaseDir $sfxName
$sedPath = Join-Path $stageDir "quant_hunter_installer.sed"
$issPath = Join-Path $stageDir "quant_hunter_installer.iss"
$installScriptPath = Join-Path $stageDir "install_quant_hunter.cmd"
$readmePath = Join-Path $stageDir "README.txt"

if (Test-Path -LiteralPath $portableZipPath) {
    Remove-Item -LiteralPath $portableZipPath -Force
}

Write-Host "Creating portable ZIP..."
Compress-Archive -Path (Join-Path $appDir "*") -DestinationPath $portableZipPath -CompressionLevel Optimal
Copy-LatestArtifact -SourcePath $portableZipPath -LatestFileName "quant_hunter_portable_latest.zip"

$installScript = @'
@echo off
setlocal

set "APP_NAME=Quant Hunter"
set "SOURCE_DIR=%~dp0"
set "ZIP_PATH=%SOURCE_DIR%quant_hunter_portable.zip"
set "INSTALL_DIR=%LocalAppData%\Programs\QuantHunter"
set "DESKTOP_LINK=%UserProfile%\Desktop\Quant Hunter.lnk"
set "START_MENU_DIR=%AppData%\Microsoft\Windows\Start Menu\Programs"
set "START_MENU_LINK=%START_MENU_DIR%\Quant Hunter.lnk"

echo Installing %APP_NAME%...

if not exist "%ZIP_PATH%" (
  echo Package archive not found: %ZIP_PATH%
  exit /b 1
)

if exist "%INSTALL_DIR%" (
  rmdir /s /q "%INSTALL_DIR%"
)
mkdir "%INSTALL_DIR%"

powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -LiteralPath '%ZIP_PATH%' -DestinationPath '%INSTALL_DIR%' -Force"
if errorlevel 1 (
  echo Failed to unpack application files.
  exit /b 1
)

if not exist "%START_MENU_DIR%" (
  mkdir "%START_MENU_DIR%"
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $desktop = $ws.CreateShortcut($env:DESKTOP_LINK); $desktop.TargetPath = Join-Path $env:INSTALL_DIR 'quant_hunter.exe'; $desktop.WorkingDirectory = $env:INSTALL_DIR; $desktop.IconLocation = Join-Path $env:INSTALL_DIR 'quant_hunter.exe'; $desktop.Save(); $start = $ws.CreateShortcut($env:START_MENU_LINK); $start.TargetPath = Join-Path $env:INSTALL_DIR 'quant_hunter.exe'; $start.WorkingDirectory = $env:INSTALL_DIR; $start.IconLocation = Join-Path $env:INSTALL_DIR 'quant_hunter.exe'; $start.Save();"
if errorlevel 1 (
  echo Installed, but failed to create shortcuts.
)

echo.
echo %APP_NAME% installed to:
echo   %INSTALL_DIR%
echo.
echo Launching %APP_NAME%...
start "" "%INSTALL_DIR%\quant_hunter.exe"
exit /b 0
'@
Set-Content -LiteralPath $installScriptPath -Value $installScript -Encoding ASCII

$readme = @'
Quant Hunter package contents

- quant_hunter_portable.zip: portable build
- install_quant_hunter.cmd: per-user installer

The installer copies the app to:
%LocalAppData%\Programs\QuantHunter
'@
Set-Content -LiteralPath $readmePath -Value $readme -Encoding ASCII

Copy-Item -LiteralPath $portableZipPath -Destination (Join-Path $stageDir "quant_hunter_portable.zip") -Force

$payloadDir = Join-Path $stageDir "payload"
$payloadAppDir = Join-Path $payloadDir "QuantHunter"
New-Directory $payloadDir
Copy-Item -LiteralPath $appDir -Destination $payloadAppDir -Recurse -Force

$bundleOpenScript = @'
@echo off
setlocal
start "" "%~dp0QuantHunter\quant_hunter.exe"
'@
$payloadOpenScriptPath = Join-Path $payloadDir "OpenQuantHunter.cmd"
Set-Content -LiteralPath $payloadOpenScriptPath -Value $bundleOpenScript -Encoding ASCII

$payloadInstallScript = @'
@echo off
setlocal

set "SOURCE_DIR=%~dp0QuantHunter"
set "INSTALL_DIR=%LocalAppData%\Programs\QuantHunter"
set "DESKTOP_LINK=%UserProfile%\Desktop\Quant Hunter.lnk"
set "START_MENU_DIR=%AppData%\Microsoft\Windows\Start Menu\Programs"
set "START_MENU_LINK=%START_MENU_DIR%\Quant Hunter.lnk"

if not exist "%SOURCE_DIR%\quant_hunter.exe" (
  echo Application files are missing.
  exit /b 1
)

if exist "%INSTALL_DIR%" (
  rmdir /s /q "%INSTALL_DIR%"
)
mkdir "%INSTALL_DIR%"
xcopy "%SOURCE_DIR%\*" "%INSTALL_DIR%\" /E /I /Y >nul

if not exist "%START_MENU_DIR%" (
  mkdir "%START_MENU_DIR%"
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $desktop = $ws.CreateShortcut($env:DESKTOP_LINK); $desktop.TargetPath = Join-Path $env:INSTALL_DIR 'quant_hunter.exe'; $desktop.WorkingDirectory = $env:INSTALL_DIR; $desktop.IconLocation = Join-Path $env:INSTALL_DIR 'quant_hunter.exe'; $desktop.Save(); $start = $ws.CreateShortcut($env:START_MENU_LINK); $start.TargetPath = Join-Path $env:INSTALL_DIR 'quant_hunter.exe'; $start.WorkingDirectory = $env:INSTALL_DIR; $start.IconLocation = Join-Path $env:INSTALL_DIR 'quant_hunter.exe'; $start.Save();"

echo Installed to:
echo   %INSTALL_DIR%
start "" "%INSTALL_DIR%\quant_hunter.exe"
exit /b 0
'@
Set-Content -LiteralPath (Join-Path $payloadDir "InstallQuantHunter.cmd") -Value $payloadInstallScript -Encoding ASCII

$bundleReadme = @'
Quant Hunter release bundle

1. Extract to any folder on the target PC.
2. If you want a portable run, open:
   OpenQuantHunter.cmd
3. If you want a per-user install with shortcuts, run:
   InstallQuantHunter.cmd
'@
Set-Content -LiteralPath (Join-Path $payloadDir "README.txt") -Value $bundleReadme -Encoding ASCII

if (Test-Path -LiteralPath $bundleZipPath) {
    Remove-Item -LiteralPath $bundleZipPath -Force
}
Write-Host "Creating release bundle ZIP..."
Compress-Archive -Path (Join-Path $payloadDir "*") -DestinationPath $bundleZipPath -CompressionLevel Optimal
Copy-LatestArtifact -SourcePath $bundleZipPath -LatestFileName "quant_hunter_bundle_latest.zip"

$shortProjectRoot = Get-ShortPath $projectRoot
$payloadDirForSed = "$shortProjectRoot\.installer_build\payload\"
$installerPathForSed = "$shortProjectRoot\releases\$installerName"
$payloadFiles = Get-ChildItem -LiteralPath $payloadDir -Recurse -File | Sort-Object FullName
$fileStringLines = @()
$sourceFileLines = @()
for ($index = 0; $index -lt $payloadFiles.Count; $index++) {
    $relative = $payloadFiles[$index].FullName.Substring($payloadDir.Length).TrimStart('\')
    $relative = $relative -replace '/', '\'
    $fileStringLines += "FILE$index=""$relative"""
    $sourceFileLines += "%FILE$index%="
}

$sed = @"
[Version]
Class=IEXPRESS
SEDVersion=3

[Options]
PackagePurpose=InstallApp
ShowInstallProgramWindow=1
HideExtractAnimation=1
UseLongFileName=1
InsideCompressed=1
CAB_FixedSize=0
CAB_ResvCodeSigning=0
RebootMode=N
InstallPrompt=%InstallPrompt%
DisplayLicense=%DisplayLicense%
FinishMessage=%FinishMessage%
TargetName=%TargetName%
FriendlyName=%FriendlyName%
AppLaunched=%AppLaunched%
PostInstallCmd=%PostInstallCmd%
AdminQuietInstCmd=%AdminQuietInstCmd%
UserQuietInstCmd=%UserQuietInstCmd%
SourceFiles=SourceFiles

[Strings]
InstallPrompt=
DisplayLicense=
FinishMessage=Quant Hunter installation is complete.
TargetName=$installerPathForSed
FriendlyName=Quant Hunter Installer
AppLaunched=cmd /c InstallQuantHunter.cmd
PostInstallCmd=<None>
AdminQuietInstCmd=cmd /c InstallQuantHunter.cmd
UserQuietInstCmd=cmd /c InstallQuantHunter.cmd
$($fileStringLines -join "`r`n")

[SourceFiles]
SourceFiles0=$payloadDirForSed

[SourceFiles0]
$($sourceFileLines -join "`r`n")
"@
Set-Content -LiteralPath $sedPath -Value $sed -Encoding ASCII

$escapedAppDir = $appDir -replace "'", "''"
$escapedReleaseDir = $releaseDir -replace "'", "''"
$escapedInstallerBaseName = [System.IO.Path]::GetFileNameWithoutExtension($installerName) -replace "'", "''"
$escapedAppExePath = (Join-Path $appDir "quant_hunter.exe") -replace "'", "''"
$escapedProjectRoot = $projectRoot -replace "'", "''"

$iss = @"
#define MyAppName "Quant Hunter"
#define MyAppVersion "$timestamp"
#define MyAppPublisher "Quant Hunter"
#define MyAppExeName "quant_hunter.exe"
#define MyBuildRoot "$escapedAppDir"
#define MyOutputDir "$escapedReleaseDir"
#define MyOutputBaseName "$escapedInstallerBaseName"
#define MySetupIconFile "$escapedAppExePath"

[Setup]
AppId={{9C7D2A28-B8F5-4D1A-BF3A-A0CB0B3F6D21}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Quant Hunter
DefaultGroupName=Quant Hunter
AllowNoIcons=yes
DisableProgramGroupPage=yes
OutputDir={#MyOutputDir}
OutputBaseFilename={#MyOutputBaseName}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
SetupIconFile={#MySetupIconFile}

[Languages]
Name: "chinesesimp"; MessagesFile: "compiler:Default.isl"
Name: "english"; MessagesFile: "compiler:Languages\English.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#MyBuildRoot}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Quant Hunter"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Quant Hunter"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Quant Hunter"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{localappdata}\QuantHunterInstallerTemp"
"@
Set-Content -LiteralPath $issPath -Value $iss -Encoding ASCII

$innoCompiler = Find-InnoSetupCompiler
if ($innoCompiler) {
    Write-Host "Creating installer EXE with Inno Setup..."
    & $innoCompiler "/Qp" $issPath
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Inno Setup failed with exit code $LASTEXITCODE"
    }
}
else {
    Write-Warning "Inno Setup compiler not found. Falling back to legacy installer builders."
}

if (-not (Test-Path -LiteralPath $installerPath)) {
    Write-Host "Creating installer EXE with IExpress..."
    $iexpressExe = Join-Path $env:SystemRoot "SysWOW64\iexpress.exe"
    if (-not (Test-Path -LiteralPath $iexpressExe)) {
        $iexpressExe = Join-Path $env:SystemRoot "System32\iexpress.exe"
    }
    if (Test-Path -LiteralPath $iexpressExe) {
        & $iexpressExe /N /Q $sedPath
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "IExpress failed with exit code $LASTEXITCODE"
        }
    }
    else {
        Write-Warning "IExpress is not available on this machine."
    }
}

if (-not (Test-Path -LiteralPath $installerPath)) {
    Write-Warning "IExpress did not create the installer EXE. Falling back to PyInstaller installer stub."
    $pythonExe = Join-Path $env:LocalAppData "Programs\Python\Python313\python.exe"
    if (-not (Test-Path -LiteralPath $pythonExe)) {
        $pythonExe = "python"
    }
    $installerStub = Join-Path $projectRoot "tools\install_bundle_stub.py"
    $installerWorkDir = Join-Path $stageDir "installer_stub"
    $installerSpecDir = $stageDir
    $installerBaseName = [System.IO.Path]::GetFileNameWithoutExtension($installerName)
    $runtimeTmpDir = Join-Path $env:LocalAppData "QuantHunterInstallerTemp"
    & $pythonExe -m PyInstaller --noconfirm --clean --onefile --runtime-tmpdir $runtimeTmpDir --name $installerBaseName --distpath $releaseDir --workpath $installerWorkDir --specpath $installerSpecDir $installerStub --add-data "${portableZipPath};."
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "PyInstaller installer stub creation failed with exit code $LASTEXITCODE"
    }
}

if (Test-Path -LiteralPath $installerPath) {
    Copy-LatestArtifact -SourcePath $installerPath -LatestFileName "quant_hunter_setup_latest.exe"
}
else {
    throw "Installer EXE was not created: $installerPath"
}

$sevenZip = Find-SevenZipExecutable
$sevenZipSfxModule = Find-SevenZipSfxModule -SevenZipExe $sevenZip
if ($sevenZip -and $sevenZipSfxModule) {
    if (Test-Path -LiteralPath $sfxPath) {
        Remove-Item -LiteralPath $sfxPath -Force
    }
    Write-Host "Creating self-extracting EXE..."
    Push-Location $payloadDir
    try {
        & $sevenZip a -t7z -mx=9 "-sfx$sevenZipSfxModule" $sfxPath *
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "7-Zip SFX creation failed with exit code $LASTEXITCODE"
        }
        elseif (Test-Path -LiteralPath $sfxPath) {
            Copy-LatestArtifact -SourcePath $sfxPath -LatestFileName "quant_hunter_self_extract_latest.exe"
        }
    }
    finally {
        Pop-Location
    }
}
elseif ($sevenZip) {
    Write-Warning "7-Zip was found, but no SFX module was available. Skipping self-extracting EXE."
}
else {
    Write-Warning "7-Zip was not found. Skipping self-extracting EXE."
}

Write-Host ""
Write-Host "Release artifacts created:"
Write-Host "  Portable ZIP: $portableZipPath"
Write-Host "  Bundle ZIP:   $bundleZipPath"
if (Test-Path -LiteralPath $installerPath) {
    Write-Host "  Installer EXE: $installerPath"
}
if (Test-Path -LiteralPath $sfxPath) {
    Write-Host "  Self-extracting EXE: $sfxPath"
}
