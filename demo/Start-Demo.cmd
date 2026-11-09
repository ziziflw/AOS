@echo off
setlocal
set "PYTHONHOME="
set "PYTHONPATH="
set "ROOT=%~dp0experiments\p0-08"
"%ROOT%\host\target\debug\host-window.exe" "%ROOT%" "%ROOT%\evidence\session-desktop"
if errorlevel 1 pause
