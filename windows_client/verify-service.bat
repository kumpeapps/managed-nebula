@echo off
REM Verify the service executable was built correctly
REM This checks if the executable can run and import required modules

echo ===================================================
echo Service Executable Verification
echo ===================================================
echo.

set "EXE_PATH=C:\Program Files (x86)\ManagedNebula\NebulaAgentService.exe"

if not exist "%EXE_PATH%" (
    set "EXE_PATH=C:\Program Files\ManagedNebula\NebulaAgentService.exe"
)

if not exist "%EXE_PATH%" (
    echo ERROR: NebulaAgentService.exe not found in:
    echo   C:\Program Files (x86)\ManagedNebula\
    echo   C:\Program Files\ManagedNebula\
    echo.
    echo You need to rebuild the service executable first.
    echo Run: rebuild-service.bat
    echo.
    pause
    exit /b 1
)

echo Found service executable: %EXE_PATH%
echo.

REM Get file date
echo Checking file date...
for %%A in ("%EXE_PATH%") do (
    echo   Modified: %%~tA
    echo   Size: %%~zA bytes
)
echo.

REM Try to run with status command to see if it works
echo Testing executable...
"%EXE_PATH%" status 2>&1

echo.
echo ===================================================
echo.
echo If you see "Service Status: Error" or similar, the executable works.
echo If you see "Usage: 'NebulaAgentService.exe [options]...", 
echo   this is the OLD broken executable.
echo.
echo To rebuild:
echo   1. Pull latest code: git pull
echo   2. Run: rebuild-service.bat
echo   3. Copy dist\NebulaAgentService.exe to "%EXE_PATH%"
echo   4. Run this verification script again
echo.
pause
