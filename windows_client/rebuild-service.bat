@echo off
REM Quick rebuild of NebulaAgentService.exe only
REM Use this after code changes to quickly rebuild the service executable

echo ===================================================
echo Quick Service Rebuild
echo ===================================================
echo.

cd /d "%~dp0"

REM Check for Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found in PATH
    exit /b 1
)

REM Check for PyInstaller
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

echo Building NebulaAgentService.exe...
pyinstaller service.spec --clean --noconfirm

if errorlevel 1 (
    echo.
    echo ERROR: Build failed!
    echo.
    pause
    exit /b 1
)

echo.
echo ===================================================
echo Build Complete!
echo ===================================================
echo.
echo Service executable: dist\NebulaAgentService.exe
echo.
echo To test the service:
echo   1. Copy dist\NebulaAgentService.exe to C:\Program Files\ManagedNebula\
echo   2. Run as Administrator: NebulaAgentService.exe install --startup auto
echo   3. Start service: sc start NebulaAgent
echo   4. Check status: sc query NebulaAgent
echo.
echo Or use the GUI: python gui.py --config
echo.
pause
