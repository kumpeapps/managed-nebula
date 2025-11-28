# Windows Installer and Service Setup - New Workflow

## Overview

The Windows installer no longer automatically installs the Windows Service. Instead, the service installation is handled through the GUI application, providing better error handling, user control, and automatic dependency checking.

## Why This Change?

### Previous Issues:
- Installer couldn't build `NebulaAgentService.exe` (requires PyInstaller)
- Service installation during setup was error-prone
- Users had no visibility into service installation problems
- No easy way to reinstall service if it failed

### Benefits of New Approach:
- ✅ GUI can search for service executable in multiple locations
- ✅ Clear error messages if executable not found
- ✅ Progress feedback during installation
- ✅ Service can be reinstalled anytime from GUI
- ✅ Admin privilege checking before attempting installation
- ✅ Automatic service configuration (type=share, auto-start)

## Installation Workflow

### 1. Build Installer
```cmd
cd windows_client
build-installer.bat
```

This creates `dist\ManagedNebulaInstaller-X.X.X.exe` with all executables including `NebulaAgentService.exe`.

### 2. Run Installer
- Double-click the installer
- Follow wizard to install files
- **Service is NOT installed yet**
- Check "Launch Managed Nebula GUI to complete setup" on finish page

### 3. Complete Setup via GUI
Launch `NebulaAgentGUI.exe` (automatically if checked):

1. **Configure Connection**:
   - Enter Server URL (e.g., `https://nebula.example.com:8080`)
   - Enter Client Token (from web interface)
   - Click "Save"

2. **Install Service**:
   - GUI shows "Windows Service: Service Not Installed" in red
   - Click "Install Service" button
   - UAC prompt for admin privileges
   - Progress window shows installation steps:
     ```
     Searching for NebulaAgentService.exe...
     Found: C:\Program Files\ManagedNebula\NebulaAgentService.exe
     
     Creating Windows Service...
     ✓ Service created successfully
     
     Starting service...
     ✓ Service started successfully
     
     Service installation complete!
     ```
   - Status changes to "Windows Service: Service Running" in green

3. **Done!**
   - Service now runs automatically on boot
   - Tunnel connects automatically
   - GUI can monitor status from system tray

## GUI Service Management

### Service Status Indicators

The GUI Configuration window shows service status:

| Status | Color | Meaning |
|--------|-------|---------|
| Service Running | Green | Service active and managing tunnel |
| Service Stopped | Orange | Service installed but not running |
| Service Installed | Orange | Service exists but in unknown state |
| Service Not Installed | Red | Service needs to be installed |
| Unknown | Red | Cannot determine status |

### Available Actions

**When Not Installed:**
- "Install Service" button appears
- Searches for `NebulaAgentService.exe` in:
  - `C:\Program Files\ManagedNebula\`
  - Same directory as GUI
  - `C:\ProgramData\Nebula\bin\`
  - Python executable directory

**When Stopped:**
- "Start Service" button appears
- Starts the existing service

**When Running:**
- No button (service is operational)
- Can stop via Windows Services or `sc stop NebulaAgent`

### Error Handling

**Service Executable Not Found:**
```
NebulaAgentService.exe not found!

Please build the service executable first by running:
  build-installer.bat

Or ensure it's in one of these locations:
  C:\Program Files\ManagedNebula\NebulaAgentService.exe
  C:\ProgramData\Nebula\bin\NebulaAgentService.exe
  ...
```

**Not Running as Administrator:**
```
Installing the service requires administrator privileges.

Please run this application as Administrator.
```

**Service Creation Failed:**
Shows detailed error from `sc create` command with stderr output.

## Manual Service Management

### PowerShell Commands

```powershell
# Check status
Get-Service NebulaAgent

# Start service
Start-Service NebulaAgent

# Stop service
Stop-Service NebulaAgent

# View service properties
Get-Service NebulaAgent | Format-List *
```

### Command Prompt Commands

```cmd
# Query status
sc query NebulaAgent

# Start service
sc start NebulaAgent

# Stop service
sc stop NebulaAgent

# Delete service (if you need to reinstall)
sc delete NebulaAgent
```

### Event Viewer
Service events logged to:
- Application Log
- Source: NebulaAgent
- Right-click Start → Event Viewer → Windows Logs → Application

## Troubleshooting

### Service Won't Install

**Check 1: Is service executable present?**
```cmd
dir "C:\Program Files\ManagedNebula\NebulaAgentService.exe"
```

If missing, rebuild installer:
```cmd
cd windows_client
build-installer.bat
```

**Check 2: Running as admin?**
- Right-click GUI → Run as Administrator
- Or use elevated PowerShell:
  ```powershell
  Start-Process "C:\Program Files\ManagedNebula\NebulaAgentGUI.exe" -Verb RunAs
  ```

**Check 3: Old service exists?**
```cmd
sc query NebulaAgent
```

If service exists but broken, delete and reinstall:
```cmd
sc stop NebulaAgent
sc delete NebulaAgent
```
Then use GUI "Install Service" button again.

### Service Installed But Won't Start

**Check configuration:**
```cmd
notepad "C:\ProgramData\Nebula\agent.ini"
```

Ensure `server_url` and `client_token` are set.

**Test service manually:**
```cmd
"C:\Program Files\ManagedNebula\NebulaAgentService.exe" debug
```

This runs service in console mode showing real-time output.

**Check logs:**
```cmd
notepad "C:\ProgramData\Nebula\logs\agent.log"
```

### GUI Can't Find Service Executable

The GUI searches these locations:
1. Same directory as Python executable
2. Same directory as gui.py
3. `C:\Program Files\ManagedNebula\`
4. `C:\ProgramData\Nebula\bin\`

Copy `NebulaAgentService.exe` to one of these locations, or rebuild with `build-installer.bat`.

## Files and Locations

### Installed by Installer

```
C:\Program Files\ManagedNebula\
├── NebulaAgent.exe              (CLI agent)
├── NebulaAgentService.exe       (Windows Service)
├── NebulaAgentGUI.exe           (GUI application)
├── nebula.exe                   (Nebula daemon)
├── nebula-cert.exe              (Certificate tool)
├── wintun.dll                   (Network driver)
├── nebula.ico                   (Icon)
└── README.md                    (Documentation)
```

### Created at Runtime

```
C:\ProgramData\Nebula\
├── agent.ini                    (Configuration)
├── config.yml                   (Nebula config)
├── host.key                     (Private key)
├── host.pub                     (Public key)
├── host.crt                     (Certificate)
├── ca.crt                       (CA chain)
├── logs\
│   ├── agent.log               (Agent logs)
│   └── nebula.log              (Nebula logs)
└── dist\
    └── windows\
        └── wintun\
            └── bin\
                └── amd64\
                    └── wintun.dll  (Driver copy)
```

## Service Configuration

Service is created with these settings:

```cmd
sc create NebulaAgent ^
    binPath= "C:\Program Files\ManagedNebula\NebulaAgentService.exe" ^
    start= auto ^
    type= share ^
    DisplayName= "Managed Nebula Agent"
```

- **start=auto**: Starts automatically on boot
- **type=share**: Runs in shared process (LocalSystem)
- **Runs as**: LocalSystem account (full privileges)

## Development Notes

### Building from Source

```cmd
# Install dependencies
pip install pyinstaller pywin32 httpx pystray pyyaml

# Build all executables and installer
cd windows_client
build-installer.bat

# Output: dist\ManagedNebulaInstaller-X.X.X.exe
```

### Testing Service Installation

1. Build installer
2. Run installer (no admin required for file copy)
3. Launch GUI normally (not as admin)
4. Try to install service → should prompt for admin
5. Right-click GUI → Run as Administrator
6. Install service → should succeed

### Code Locations

- GUI service management: `windows_client/gui.py` → `ConfigWindow` class
  - `is_admin()` - Check admin privileges
  - `get_service_status()` - Query service state
  - `_install_service()` - Install service with progress dialog
  - `_start_service()` - Start existing service
  
- Service implementation: `windows_client/service.py`
  - `NebulaAgentService` class extends `win32serviceutil.ServiceFramework`
  
- Installer script: `windows_client/installer/installer.nsi`
  - Copies files but does NOT install service
  - Finish page encourages launching GUI

## Migration from Old Installers

If you previously had auto-installed service:

1. Uninstall old version OR manually remove service:
   ```cmd
   sc stop NebulaAgent
   sc delete NebulaAgent
   ```

2. Install new version

3. Launch GUI and click "Install Service"

Configuration and certificates are preserved in `C:\ProgramData\Nebula\`.

## Summary

| Task | Tool | Requires Admin |
|------|------|----------------|
| Build installer | build-installer.bat | No |
| Run installer (copy files) | Installer .exe | No |
| Configure server/token | GUI | No |
| Install Windows Service | GUI "Install Service" button | Yes |
| Start/stop service | GUI or Services.msc | Yes |
| View status | GUI | No |
| View logs | GUI → View Logs | No |

This workflow gives users control over when and how the service is installed, with clear feedback at each step.
