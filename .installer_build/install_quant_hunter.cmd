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
