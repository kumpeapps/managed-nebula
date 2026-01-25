@echo off
REM Managed Nebula Windows Client Build Script
REM This script builds the Windows installer using PyInstaller

setlocal EnableDelayedExpansion

echo ===================================================
echo Managed Nebula Windows Client Builder
echo ===================================================
echo.

REM Configuration
set "VERSION=1.0.0"
set "NEBULA_VERSION=1.10.1"
set "APP_NAME=NebulaAgent"
set "SCRIPT_DIR=%~dp0"
set "DIST_DIR=%SCRIPT_DIR%dist"
set "BUILD_DIR=%SCRIPT_DIR%build"

REM Parse command line arguments
:parse_args
if "%~1"=="" goto :done_args
if /i "%~1"=="--version" (
    set "VERSION=%~2"
    shift
    shift
    goto :parse_args
)
if /i "%~1"=="--nebula-version" (
    set "NEBULA_VERSION=%~2"
    shift
    shift
    goto :parse_args
)
shift
goto :parse_args
:done_args

echo Version: %VERSION%
echo Nebula Version: %NEBULA_VERSION%
echo.

REM Check for Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found in PATH
    exit /b 1
)

REM Check for required packages
echo Step 1: Checking dependencies...
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

pip show pywin32 >nul 2>&1
if errorlevel 1 (
    echo Installing pywin32...
    pip install pywin32
)

pip show httpx >nul 2>&1
if errorlevel 1 (
    echo Installing httpx...
    pip install httpx
)

echo Dependencies OK
echo.

REM Clean previous builds
echo Step 2: Cleaning previous builds...
if exist "%DIST_DIR%" rmdir /s /q "%DIST_DIR%"
if exist "%BUILD_DIR%" rmdir /s /q "%BUILD_DIR%"
mkdir "%DIST_DIR%"
echo Clean complete
echo.

REM Download Nebula binaries
echo Step 3: Downloading Nebula binaries...
set "NEBULA_URL=https://github.com/slackhq/nebula/releases/download/v%NEBULA_VERSION%/nebula-windows-amd64.zip"
set "NEBULA_TMP=%DIST_DIR%\nebula-tmp"
mkdir "%NEBULA_TMP%"

echo   Downloading Nebula version v%NEBULA_VERSION%
echo   URL: %NEBULA_URL%
curl -L -o "%NEBULA_TMP%\nebula.zip" "%NEBULA_URL%"
if errorlevel 1 (
    echo Error: Failed to download Nebula binaries from %NEBULA_URL%
    echo.
    echo Please verify:
    echo   1. Version %NEBULA_VERSION% exists at https://github.com/slackhq/nebula/releases
    echo   2. Internet connection is working
    echo.
    exit /b 1
)

REM Extract Nebula binaries
echo   Extracting Nebula binaries...
powershell -Command "Expand-Archive -Path '%NEBULA_TMP%\nebula.zip' -DestinationPath '%NEBULA_TMP%' -Force"
if not exist "%NEBULA_TMP%\nebula.exe" (
    echo Error: Failed to extract Nebula binaries
    exit /b 1
)

echo Nebula binaries downloaded
echo.

REM Build the agent executable
echo Step 4: Building agent executable...
cd /d "%SCRIPT_DIR%"

pyinstaller --onefile ^
    --name "%APP_NAME%" ^
    --icon=installer\nebula.ico ^
    --add-data "config.py;." ^
    --hidden-import=win32timezone ^
    --hidden-import=win32serviceutil ^
    --hidden-import=win32service ^
    --hidden-import=win32event ^
    --hidden-import=servicemanager ^
    agent.py

if errorlevel 1 (
    echo Error: PyInstaller build failed
    exit /b 1
)

echo Agent executable built
echo.

REM Build the service executable
echo Step 5: Building service executable...
pyinstaller --onefile ^
    --name "%APP_NAME%Service" ^
    --icon=installer\nebula.ico ^
    --add-data "config.py;." ^
    --add-data "agent.py;." ^
    --hidden-import=win32timezone ^
    --hidden-import=win32serviceutil ^
    --hidden-import=win32service ^
    --hidden-import=win32event ^
    --hidden-import=servicemanager ^
    service.py

if errorlevel 1 (
    echo Error: PyInstaller service build failed
    exit /b 1
)

echo Service executable built
echo.

REM Build the GUI executable
echo Step 6: Building GUI executable...
pyinstaller --onefile --windowed ^
    --name "%APP_NAME%GUI" ^
    --icon=installer\nebula.ico ^
    --add-data "config.py;." ^
    --add-data "agent.py;." ^
    --add-data "installer\nebula.ico;installer" ^
    --hidden-import=win32timezone ^
    --hidden-import=pystray._win32 ^
    gui.py

if errorlevel 1 (
    echo Error: PyInstaller GUI build failed
    exit /b 1
)

echo GUI executable built
echo.

REM Prepare distribution package
echo Step 7: Preparing distribution package...
set "PKG_DIR=%DIST_DIR%\%APP_NAME%-%VERSION%"
mkdir "%PKG_DIR%"

REM Copy executables
copy "%DIST_DIR%\%APP_NAME%.exe" "%PKG_DIR%\"
copy "%DIST_DIR%\%APP_NAME%Service.exe" "%PKG_DIR%\"
copy "%DIST_DIR%\%APP_NAME%GUI.exe" "%PKG_DIR%\"

REM Copy Nebula binaries
copy "%NEBULA_TMP%\nebula.exe" "%PKG_DIR%\"
copy "%NEBULA_TMP%\nebula-cert.exe" "%PKG_DIR%\"

REM Copy installer scripts
copy "%SCRIPT_DIR%\installer\install.ps1" "%PKG_DIR%\"
copy "%SCRIPT_DIR%\installer\uninstall.ps1" "%PKG_DIR%\"

REM Copy icon
copy "%SCRIPT_DIR%\installer\nebula.ico" "%PKG_DIR%\"

REM Create version file
echo %VERSION%> "%PKG_DIR%\VERSION"

REM Create default config
echo [agent]> "%PKG_DIR%\agent.ini.example"
echo server_url = https://your-server.example.com:8080>> "%PKG_DIR%\agent.ini.example"
echo client_token = your-client-token-here>> "%PKG_DIR%\agent.ini.example"
echo poll_interval_hours = 24>> "%PKG_DIR%\agent.ini.example"
echo log_level = INFO>> "%PKG_DIR%\agent.ini.example"
echo auto_start_nebula = true>> "%PKG_DIR%\agent.ini.example"

REM Copy README
copy "%SCRIPT_DIR%\README.md" "%PKG_DIR%\"

echo Distribution package prepared
echo.

REM Create ZIP archive
echo Step 8: Creating ZIP archive...
powershell -Command "Compress-Archive -Path '%PKG_DIR%\*' -DestinationPath '%DIST_DIR%\%APP_NAME%-%VERSION%.zip' -Force"

echo ZIP archive created: %DIST_DIR%\%APP_NAME%-%VERSION%.zip
echo.

REM Cleanup
echo Step 9: Cleaning up...
rmdir /s /q "%NEBULA_TMP%"
rmdir /s /q "%BUILD_DIR%"
del /q "%DIST_DIR%\%APP_NAME%.exe" 2>nul
del /q "%DIST_DIR%\%APP_NAME%Service.exe" 2>nul
del /q "%DIST_DIR%\%APP_NAME%GUI.exe" 2>nul

echo Cleanup complete
echo.

REM Summary
echo ===================================================
echo Build Complete!
echo ===================================================
echo.
echo Versions:
echo   Package Version: %VERSION%
echo   Nebula Version: %NEBULA_VERSION%
echo.
echo Output files:
echo   %DIST_DIR%\%APP_NAME%-%VERSION%.zip
echo   %PKG_DIR%\
echo.
echo Package contents:
echo   - %APP_NAME%.exe (Agent CLI)
echo   - %APP_NAME%Service.exe (Windows Service)
echo   - %APP_NAME%GUI.exe (GUI Configuration App)
echo   - nebula.exe (Nebula VPN binary)
echo   - nebula-cert.exe (Nebula certificate tool)
echo   - install.ps1 (PowerShell installer)
echo   - uninstall.ps1 (PowerShell uninstaller)
echo   - nebula.ico (Application icon)
echo   - agent.ini.example (Example configuration)
echo   - README.md (Documentation)
echo.
echo Next steps:
echo   1. Copy the package to target Windows machine
echo   2. Run install.ps1 as Administrator
echo   3. Run NebulaAgentGUI.exe to configure
echo   4. Or manually edit agent.ini and start the service
echo.

endlocal
