@echo off
REM Managed Nebula Windows Installer Builder
REM This script builds the complete Windows installer with NSIS
REM 
REM Prerequisites:
REM   - Python 3.9+
REM   - PyInstaller: pip install pyinstaller
REM   - PyWin32: pip install pywin32
REM   - NSIS: https://nsis.sourceforge.io/
REM
REM Usage:
REM   build-installer.bat [--version X.X.X] [--nebula-version X.X.X]
REM
REM This script will:
REM   1. Check all prerequisites
REM   2. Download Nebula binaries
REM   3. Build Python executables with PyInstaller
REM   4. Build NSIS installer
REM   5. Output complete installer

setlocal EnableDelayedExpansion

echo ===================================================
echo Managed Nebula Windows Installer Builder
echo ===================================================
echo.

REM Configuration
set "VERSION=1.0.0"
set "NEBULA_VERSION=1.9.7"
set "WINTUN_VERSION=0.14.1"
set "APP_NAME=NebulaAgent"
set "SCRIPT_DIR=%~dp0"
set "DIST_DIR=%SCRIPT_DIR%dist"
set "BUILD_DIR=%SCRIPT_DIR%build"
set "INSTALLER_DIR=%SCRIPT_DIR%installer"

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
echo Wintun Version: %WINTUN_VERSION%
echo.

REM Check for Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found in PATH
    exit /b 1
)

REM Check for NSIS
where makensis >nul 2>&1
if errorlevel 1 (
    echo Error: NSIS (makensis) not found in PATH
    echo Please install NSIS from https://nsis.sourceforge.io/
    exit /b 1
)

REM Check for required Python packages
echo Step 1: Checking Python dependencies...
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

pip show pystray >nul 2>&1
if errorlevel 1 (
    echo Installing pystray...
    pip install pystray
)

pip show pyyaml >nul 2>&1
if errorlevel 1 (
    echo Installing pyyaml...
    pip install pyyaml
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

echo   Downloading from %NEBULA_URL%
curl -L -o "%NEBULA_TMP%\nebula.zip" "%NEBULA_URL%"
if errorlevel 1 (
    echo Error: Failed to download Nebula binaries
    exit /b 1
)

echo   Extracting Nebula binaries...
powershell -Command "Expand-Archive -Path '%NEBULA_TMP%\nebula.zip' -DestinationPath '%NEBULA_TMP%' -Force"
if not exist "%NEBULA_TMP%\nebula.exe" (
    echo Error: Failed to extract Nebula binaries
    exit /b 1
)

echo Nebula binaries ready
echo.

REM Download Wintun driver
echo Step 3b: Downloading Wintun driver...
set "WINTUN_URL=https://www.wintun.net/builds/wintun-%WINTUN_VERSION%.zip"
set "WINTUN_TMP=%DIST_DIR%\wintun-tmp"
mkdir "%WINTUN_TMP%"

echo   Downloading from %WINTUN_URL%
curl -L -o "%WINTUN_TMP%\wintun.zip" "%WINTUN_URL%"
if errorlevel 1 (
    echo Warning: Failed to download Wintun driver (non-fatal)
    echo Nebula may not work properly without Wintun
) else (
    echo   Extracting Wintun driver...
    powershell -Command "Expand-Archive -Path '%WINTUN_TMP%\wintun.zip' -DestinationPath '%WINTUN_TMP%' -Force"
    
    REM Copy the appropriate architecture DLL to installer directory
    if exist "%WINTUN_TMP%\wintun\bin\amd64\wintun.dll" (
        copy "%WINTUN_TMP%\wintun\bin\amd64\wintun.dll" "%INSTALLER_DIR%\"
        echo Wintun driver ready
    ) else (
        echo Warning: Wintun DLL not found after extraction
    )
)
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
    --hidden-import=yaml ^
    agent.py

if errorlevel 1 (
    echo Error: PyInstaller agent build failed
    exit /b 1
)

echo Agent executable built
echo.

REM Build the service executable
echo Step 5: Building service executable...
pyinstaller --onefile ^
    --name "%APP_NAME%Service" ^
    --icon=installer\nebula.ico ^
    --hidden-import=win32timezone ^
    --hidden-import=win32api ^
    --hidden-import=win32con ^
    --hidden-import=win32security ^
    --hidden-import=ntsecuritycon ^
    --hidden-import=win32serviceutil ^
    --hidden-import=win32service ^
    --hidden-import=win32event ^
    --hidden-import=servicemanager ^
    --hidden-import=yaml ^
    --hidden-import=httpx ^
    --hidden-import=httpx._transports ^
    --hidden-import=httpx._transports.default ^
    --hidden-import=httpx._client ^
    --hidden-import=h11 ^
    --hidden-import=certifi ^
    --hidden-import=charset_normalizer ^
    --collect-all=httpx ^
    --collect-all=certifi ^
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
    --hidden-import=yaml ^
    gui.py

if errorlevel 1 (
    echo Error: PyInstaller GUI build failed
    exit /b 1
)

echo GUI executable built
echo.

REM Copy files to installer directory for NSIS
echo Step 7: Preparing files for NSIS installer...
copy "%DIST_DIR%\%APP_NAME%.exe" "%INSTALLER_DIR%\"
copy "%DIST_DIR%\%APP_NAME%Service.exe" "%INSTALLER_DIR%\"
copy "%DIST_DIR%\%APP_NAME%GUI.exe" "%INSTALLER_DIR%\"
copy "%NEBULA_TMP%\nebula.exe" "%INSTALLER_DIR%\"
copy "%NEBULA_TMP%\nebula-cert.exe" "%INSTALLER_DIR%\"

echo Files copied to installer directory
echo.

REM Update version in NSIS script (in-place)
echo Step 8: Updating version in NSIS script...
powershell -Command "$content = Get-Content '%INSTALLER_DIR%\installer.nsi' -Raw; $content -replace '!define VERSION \".*?\"', '!define VERSION \"%VERSION%\"' | Set-Content '%INSTALLER_DIR%\installer.nsi'"
powershell -Command "$content = Get-Content '%INSTALLER_DIR%\installer.nsi' -Raw; $content -replace '!define NEBULA_VERSION \".*?\"', '!define NEBULA_VERSION \"%NEBULA_VERSION%\"' | Set-Content '%INSTALLER_DIR%\installer.nsi'"

echo Version updated in NSIS script
echo.

REM Build NSIS installer
echo Step 9: Building NSIS installer...
cd /d "%INSTALLER_DIR%"
makensis installer.nsi

if errorlevel 1 (
    echo Error: NSIS build failed
    exit /b 1
)

REM Move installer to dist directory
move "ManagedNebulaInstaller-*.exe" "%DIST_DIR%\"

echo NSIS installer built
echo.

REM Cleanup installer directory (remove temporary copies)
echo Step 10: Cleaning up temporary files...
del /q "%INSTALLER_DIR%\%APP_NAME%.exe" 2>nul
del /q "%INSTALLER_DIR%\%APP_NAME%Service.exe" 2>nul
del /q "%INSTALLER_DIR%\%APP_NAME%GUI.exe" 2>nul
del /q "%INSTALLER_DIR%\nebula.exe" 2>nul
del /q "%INSTALLER_DIR%\nebula-cert.exe" 2>nul

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
echo Installer created:
dir "%DIST_DIR%\ManagedNebulaInstaller-*.exe"
echo.
echo Next steps:
echo   1. Copy the installer to target Windows machine
echo   2. Run as Administrator
echo   3. Service will be installed and configured automatically
echo   4. Use the GUI to configure server URL and token
echo.

endlocal
