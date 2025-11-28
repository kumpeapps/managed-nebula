# Windows Client Rebuild Instructions

## Issue #114 - Service Installation Fix

The service executable (`NebulaAgentService.exe`) had missing dependencies that prevented it from running without Python installed. This has been fixed with a comprehensive PyInstaller spec file.

**CRITICAL: You MUST rebuild the service executable on Windows before it will work!**

## What Was Fixed

1. **Created `service.spec`** - Comprehensive PyInstaller specification:
   - All httpx dependencies (httpx, httpcore, h11, certifi)
   - All win32 service modules (win32serviceutil, win32service, win32event, servicemanager)
   - Windows security (win32security, ntsecuritycon)
   - YAML parser, SSL support, logging

2. **Updated `build-installer.bat`** - Now uses service.spec instead of command-line args

3. **Created `rebuild-service.bat`** - Quick rebuild script for service-only builds (~30 seconds)

4. **Created `verify-service.bat`** - Check if executable is up-to-date

5. **GUI Python Fallback** - Falls back to `python service.py install` if exe missing

## Why You're Seeing the Error

The old `NebulaAgentService.exe` in your `C:\Program Files (x86)\ManagedNebula\` folder was built without the dependencies. The error message shows it's still the old version.

**You must rebuild it on the Windows machine to get the fixed version.**

## How to Rebuild

### Prerequisites

On your **development Windows machine**:

```batch
pip install pyinstaller pywin32 httpx pyyaml pystray pillow
```

### Quick Rebuild (Recommended - 30 seconds)

**This rebuilds ONLY the service executable:**

```batch
cd C:\path\to\managed-nebula
git pull
cd windows_client
rebuild-service.bat
```

Output will be in `dist\NebulaAgentService.exe`

**Then copy to install location:**

```batch
REM Stop old service if running
sc stop NebulaAgent
sc delete NebulaAgent

REM Copy new executable
copy dist\NebulaAgentService.exe "C:\Program Files (x86)\ManagedNebula\"
```

### Full Installer Rebuild (Slower - 2-3 minutes)

**This builds everything - use when creating installer for distribution:**

```batch
cd C:\path\to\managed-nebula
git pull
cd windows_client
build-installer.bat
```

   This will:
   - Download Nebula binaries (v1.9.7)
   - Download Wintun driver (v0.14.1)
   - Build 3 executables with PyInstaller:
     - `NebulaAgent.exe` - CLI agent
     - `NebulaAgentService.exe` - Windows Service (FIXED)
     - `NebulaAgentGUI.exe` - System tray GUI
   - Package everything into NSIS installer
   - Output: `dist\ManagedNebula-1.0.0-Setup.exe`

3. **Test the Installer**:
   - Copy `dist\ManagedNebula-1.0.0-Setup.exe` to target Windows machine
   - Run as Administrator
   - Launch GUI from Start Menu or Desktop
   - Configure Server URL and Token
   - Click "Install Service" - should now work!

## Verification

After installation, verify the service works:

```batch
# Check service status
sc query NebulaAgent

# View service logs
type C:\ProgramData\Nebula\logs\agent.log

# Check if Nebula is running
tasklist | findstr nebula
```

## Troubleshooting

If service still fails to start:

1. **Check Windows Event Viewer**:
   - Open Event Viewer → Windows Logs → Application
   - Look for Python Service errors

2. **Try Manual Service Registration**:
   ```batch
   cd "C:\Program Files\ManagedNebula"
   NebulaAgentService.exe install --startup auto
   sc start NebulaAgent
   ```

3. **Debug Mode** (see detailed errors):
   ```batch
   cd "C:\Program Files\ManagedNebula"
   NebulaAgentService.exe debug
   ```

4. **Verify Dependencies** (check what PyInstaller bundled):
   ```batch
   cd windows_client
   pyinstaller --onefile service.py
   # Check dist\service\ directory for bundled modules
   ```

## Changes Summary

- **File**: `windows_client/build-installer.bat`
  - Added Step 3b: Wintun download
  - Enhanced PyInstaller service build with 10+ hidden imports
  - Added `--collect-all` directives

- **File**: `windows_client/gui.py`
  - Fixed service install command arguments
  - Added Python fallback (development only)
  - Enhanced progress logging with debug output

## Next Steps

1. Rebuild installer with `build-installer.bat`
2. Test on clean Windows machine (no Python)
3. Verify service installs and starts successfully
4. Create GitHub release with working installer
