@echo off
setlocal EnableExtensions

set "SCRIPT_DIR=%~dp0"
set "PS_LAUNCHER=%SCRIPT_DIR%scripts\launch_enhancer_gui.ps1"

if not exist "%PS_LAUNCHER%" (
    echo Codex Enhancer launcher helper was not found:
    echo   %PS_LAUNCHER%
    pause
    exit /b 1
)

for /f "delims=" %%P in ('where pwsh 2^>nul') do (
    start "" "%%P" -NoLogo -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%PS_LAUNCHER%" "%SCRIPT_DIR%"
    exit /b 0
)

if exist "%ProgramFiles%\PowerShell\7\pwsh.exe" (
    start "" "%ProgramFiles%\PowerShell\7\pwsh.exe" -NoLogo -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%PS_LAUNCHER%" "%SCRIPT_DIR%"
    exit /b 0
)

if exist "%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" (
    start "" "%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoLogo -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%PS_LAUNCHER%" "%SCRIPT_DIR%"
    exit /b 0
)

where powershell >nul 2>nul
if not errorlevel 1 (
    start "" powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%PS_LAUNCHER%" "%SCRIPT_DIR%"
    exit /b 0
)

echo PowerShell was not found by this cmd launcher.
echo Open PowerShell in this folder and run:
echo   python scripts\install_enhancer_web_gui.py
pause
exit /b 1
