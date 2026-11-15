@echo off
setlocal
cd /d "%~dp0\.."
where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher was not found. Install Python 3.10+ from python.org first.
  pause
  exit /b 1
)
py -m pip install --upgrade pyinstaller
if errorlevel 1 goto failed
py -m PyInstaller --noconfirm --clean --onefile --windowed --name CyberShieldToolkit src\cybershield_toolkit.py
if errorlevel 1 goto failed
echo.
echo SUCCESS: dist\CyberShieldToolkit.exe
pause
exit /b 0
:failed
echo.
echo BUILD FAILED. Read the error above.
pause
exit /b 1
