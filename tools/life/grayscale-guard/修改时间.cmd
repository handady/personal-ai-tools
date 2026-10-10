@echo off
cd /d "%~dp0"
start "" /wait notepad.exe "%~dp0config.json"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\install.ps1"
echo.
pause
