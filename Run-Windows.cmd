@echo off
setlocal
cd /d "%~dp0"

rem Build a separate environment; macOS virtual environments cannot be reused.
if exist ".venv-windows\Scripts\python.exe" goto install
where py >nul 2>nul
if errorlevel 1 goto use_python
py -3 -m venv .venv-windows
if errorlevel 1 goto failed
goto install

:use_python
where python >nul 2>nul
if errorlevel 1 goto missing_python
python -m venv .venv-windows
if errorlevel 1 goto failed

:install
".venv-windows\Scripts\python.exe" -m pip install -r desktop\requirements.txt
if errorlevel 1 goto failed
echo.
echo Starting NoSub Studio. Keep this window open while testing.
".venv-windows\Scripts\python.exe" desktop\app.py
if errorlevel 1 goto failed
exit /b 0

:missing_python
echo Install 64-bit Python 3.13 from https://www.python.org/downloads/windows/
echo Enable the Python launcher or Add Python to PATH, then run this file again.
pause
exit /b 1

:failed
echo.
echo NoSub Studio could not start. Please copy the error above for troubleshooting.
pause
exit /b 1
