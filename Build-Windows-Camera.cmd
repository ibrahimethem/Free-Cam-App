@echo off
setlocal
cd /d "%~dp0"
set "STUDIO_PYTHON=%~dp0.venv-windows\Scripts\python.exe"
"%STUDIO_PYTHON%" -c "import sys; assert sys.platform == 'win32'" >nul 2>nul
if not errorlevel 1 goto build
set "STUDIO_PYTHON=%~dp0.venv\Scripts\python.exe"
"%STUDIO_PYTHON%" -c "import sys; assert sys.platform == 'win32'" >nul 2>nul
if not errorlevel 1 goto build
echo Run Run-Windows.cmd once to prepare Python dependencies, then quit the app.
pause
exit /b 1

:build
"%STUDIO_PYTHON%" desktop\native\windows\build.py
if errorlevel 1 (
  echo Camera build failed. See the error above. Nothing was installed.
  pause
  exit /b 1
)
echo Camera build ready. Run Run-Windows.cmd and choose Install camera.
pause
