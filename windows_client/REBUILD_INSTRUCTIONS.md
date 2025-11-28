# Windows Client Rebuild Instructions

## Issue #114 - Service Installation Fix

The service executable (`NebulaAgentService.exe`) had missing dependencies that prevented it from running without Python installed. This has been fixed in the build script.

## What Was Fixed

1. **PyInstaller Hidden Imports** - Added all required dependencies:
   - `httpx` and its transports (h11, certifi, charset_normalizer)
   - Windows security modules (win32api, win32security, ntsecuritycon)
   - Used `--collect-all` for httpx and certifi to ensure complete packaging

2. **Wintun Driver** - Now automatically downloads and packages wintun.dll
   - Downloads from wintun.net during build
   - Packages correct architecture (amd64) into installer
   - Nebula requires this for tunnel interface creation

3. **Service Installation** - GUI now has proper error handling:
   - Corrected install command arguments (`--startup auto` not `--startup=auto`)
   - Python fallback for development/testing
   - Detailed progress logging

## How to Rebuild

### Prerequisites

On your **development Windows machine**:

```batch
pip install pyinstaller pywin32 httpx pyyaml pystray pillow
```

### Build Steps

1. **Clone/Pull Latest Code**:
   ```batch
   cd C:\path\to\managed-nebula
   git pull
   cd windows_client
   ```

2. **Run Build Script**:
   ```batch
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
