@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 kixware.py
) else (
  python kixware.py
)
if errorlevel 1 (
  echo KixWare could not start. Install Python 3.10+ from python.org with Tcl/Tk and the Python launcher.
  pause
)
