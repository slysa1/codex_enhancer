@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "GUI_SCRIPT=%SCRIPT_DIR%scripts\install_enhancer_gui.py"

where pyw >nul 2>nul
if %errorlevel%==0 (
    start "" pyw "%GUI_SCRIPT%"
    exit /b 0
)

where pythonw >nul 2>nul
if %errorlevel%==0 (
    start "" pythonw "%GUI_SCRIPT%"
    exit /b 0
)

where python >nul 2>nul
if %errorlevel%==0 (
    python "%GUI_SCRIPT%"
    exit /b %errorlevel%
)

echo Python was not found on PATH.
echo Install Python 3.13+ and rerun this launcher, or use:
echo   python scripts\install_enhancer.py --help
pause
exit /b 1
