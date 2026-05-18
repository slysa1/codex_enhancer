@echo off
setlocal EnableExtensions

set "CLI_SCRIPT=%~dp0scripts\codex_enhancer_cli.py"

where py >nul 2>nul
if not errorlevel 1 (
    py -3 -c "import sys" >nul 2>nul
    if not errorlevel 1 (
        py -3 "%CLI_SCRIPT%" %*
        exit /b
    )
)

where python3 >nul 2>nul
if not errorlevel 1 (
    python3 "%CLI_SCRIPT%" %*
    exit /b
)

where python >nul 2>nul
if not errorlevel 1 (
    python "%CLI_SCRIPT%" %*
    exit /b
)

echo Python was not found by this cmd launcher.
echo Install Python 3.13+, enable the Windows Python Launcher, or use:
echo   py -3 scripts\codex_enhancer_cli.py --help
echo   python scripts\codex_enhancer_cli.py --help
exit /b 1
