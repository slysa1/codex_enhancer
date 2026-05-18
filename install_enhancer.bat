@echo off
setlocal EnableExtensions

set "SCRIPT_DIR=%~dp0"
set "GUI_SCRIPT=%SCRIPT_DIR%scripts\install_enhancer_web_gui.py"

where pyw >nul 2>nul
if not errorlevel 1 (
    where py >nul 2>nul
    if not errorlevel 1 (
        py -3 -c "import sys" >nul 2>nul
        if not errorlevel 1 (
            start "" pyw -3 "%GUI_SCRIPT%"
            exit /b 0
        )
    )
)

where pythonw >nul 2>nul
if not errorlevel 1 (
    start "" pythonw "%GUI_SCRIPT%"
    exit /b 0
)

where py >nul 2>nul
if not errorlevel 1 (
    py -3 -c "import sys" >nul 2>nul
    if not errorlevel 1 (
        py -3 "%GUI_SCRIPT%"
        exit /b
    )
)

where python3 >nul 2>nul
if not errorlevel 1 (
    python3 "%GUI_SCRIPT%"
    exit /b
)

where python >nul 2>nul
if not errorlevel 1 (
    python "%GUI_SCRIPT%"
    exit /b
)

echo Python was not found by this cmd launcher.
echo Install Python 3.13+, enable the Windows Python Launcher, or use:
echo   py -3 scripts\install_enhancer.py --help
echo   python scripts\install_enhancer.py --help
pause
exit /b 1
