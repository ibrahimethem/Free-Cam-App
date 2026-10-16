@echo off
setlocal
cd /d "%~dp0"

rem Validate interpreters: Windows Store aliases and copied environments may exist but fail.
set "STUDIO_PYTHON=%~dp0.venv\Scripts\python.exe"
"%STUDIO_PYTHON%" -c "import sys; assert sys.platform == 'win32'" >nul 2>nul
if not errorlevel 1 goto install
set "STUDIO_PYTHON=%~dp0.venv-windows\Scripts\python.exe"
"%STUDIO_PYTHON%" -c "import sys; assert sys.platform == 'win32'" >nul 2>nul
if not errorlevel 1 goto install
py -3 -c "import sys; assert sys.platform == 'win32'" >nul 2>nul
if errorlevel 1 goto use_python
py -3 -m venv .venv-windows
if errorlevel 1 goto failed
set "STUDIO_PYTHON=%~dp0.venv-windows\Scripts\python.exe"
goto install

:use_python
python -c "import sys; assert sys.platform == 'win32'" >nul 2>nul
if errorlevel 1 goto missing_python
python -m venv .venv-windows
if errorlevel 1 goto failed
set "STUDIO_PYTHON=%~dp0.venv-windows\Scripts\python.exe"

:install
echo Using Python: "%STUDIO_PYTHON%"
"%STUDIO_PYTHON%" -m pip install -r desktop\requirements.txt
if errorlevel 1 goto failed
echo.
echo Starting NoSub Studio. Keep this window open while testing.
"%STUDIO_PYTHON%" "%~dp0desktop\app.py" %*
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
