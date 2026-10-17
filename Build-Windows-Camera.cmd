@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv-windows\Scripts\python.exe" (
  echo Run Run-Windows.cmd once to prepare Python dependencies, then close the app.
  pause
  exit /b 1
)
".venv-windows\Scripts\python.exe" desktop\native\windows\build.py
if errorlevel 1 (
  echo Camera build failed. See the error above. Nothing was installed.
  pause
  exit /b 1
)
echo Camera build ready. Run Run-Windows.cmd and choose Install camera.
pause
