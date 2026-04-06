@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "PYTHON_EXE=%LocalAppData%\Programs\Python\Python313\python.exe"
set "WORK_DIR=%SCRIPT_DIR%.pyinstaller_build"
set "DIST_DIR=%SCRIPT_DIR%dist"
set "ALT_DIST_DIR=%SCRIPT_DIR%dist_latest"

if not exist "%PYTHON_EXE%" (
  set "PYTHON_EXE=python"
)

"%PYTHON_EXE%" -c "import PySide6" >nul 2>nul
if errorlevel 1 (
  echo PySide6 is not available for:
  echo     %PYTHON_EXE%
  echo.
  echo Install it with:
  echo     "%PYTHON_EXE%" -m pip install PySide6
  exit /b 1
)

"%PYTHON_EXE%" -m PyInstaller --version >nul 2>nul
if errorlevel 1 (
  echo PyInstaller not found for:
  echo     %PYTHON_EXE%
  echo.
  echo Install it with:
  echo     "%PYTHON_EXE%" -m pip install pyinstaller
  exit /b 1
)

if exist "%DIST_DIR%\quant_hunter" (
  rmdir /s /q "%DIST_DIR%\quant_hunter" >nul 2>nul
)

"%PYTHON_EXE%" -m PyInstaller --noconfirm --clean --distpath "%DIST_DIR%" --workpath "%WORK_DIR%" "%SCRIPT_DIR%quant_hunter.spec"
if errorlevel 1 (
  echo Default dist path is busy, retrying with dist_latest...
  if exist "%ALT_DIST_DIR%\quant_hunter" (
    rmdir /s /q "%ALT_DIST_DIR%\quant_hunter" >nul 2>nul
  )
  "%PYTHON_EXE%" -m PyInstaller --noconfirm --clean --distpath "%ALT_DIST_DIR%" --workpath "%WORK_DIR%_latest" "%SCRIPT_DIR%quant_hunter.spec"
  if errorlevel 1 (
    echo Build failed.
    exit /b 1
  )
  echo.
  echo Build complete:
  echo     %ALT_DIST_DIR%\quant_hunter
  echo.
  echo Run this file:
  echo     %ALT_DIST_DIR%\quant_hunter\quant_hunter.exe
  exit /b 0
)

if exist "%WORK_DIR%\quant_hunter\quant_hunter.exe" (
  del /q "%WORK_DIR%\quant_hunter\quant_hunter.exe"
)

echo.
echo Build complete:
echo     %SCRIPT_DIR%dist\quant_hunter
echo.
echo Run this file:
echo     %SCRIPT_DIR%dist\quant_hunter\quant_hunter.exe
