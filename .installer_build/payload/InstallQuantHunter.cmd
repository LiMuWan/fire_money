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
