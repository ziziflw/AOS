@echo off
setlocal
pwsh -NoProfile -File "%~dp0start-integrated.ps1"
if errorlevel 1 pause
