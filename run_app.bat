@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "PYTHONW_EXE=%LocalAppData%\Programs\Python\Python313\pythonw.exe"
set "PYTHON_EXE=%LocalAppData%\Programs\Python\Python313\python.exe"
set "DIST_EXE=%SCRIPT_DIR%dist\quant_hunter\quant_hunter.exe"
set "DIST_EXE_LATEST=%SCRIPT_DIR%dist_latest\quant_hunter\quant_hunter.exe"

if exist "%PYTHONW_EXE%" (
  start "" "%PYTHONW_EXE%" "%SCRIPT_DIR%app_qt.py"
  exit /b 0
)

if exist "%PYTHON_EXE%" (
  start "" "%PYTHON_EXE%" "%SCRIPT_DIR%app_qt.py"
  exit /b 0
)

if exist "%DIST_EXE%" (
  start "" "%DIST_EXE%"
  exit /b 0
)

if exist "%DIST_EXE_LATEST%" (
  start "" "%DIST_EXE_LATEST%"
  exit /b 0
)

start "" python "%SCRIPT_DIR%app_qt.py"
