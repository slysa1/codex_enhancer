@echo off
setlocal

python "%~dp0scripts\codex_enhancer_cli.py" %*
exit /b %errorlevel%
