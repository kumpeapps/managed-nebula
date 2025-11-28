# Windows Service Error 1083 Fix

## Problem
When trying to start the Managed Nebula Agent Windows Service, you receive:

```
Error 1083: The executable program that this service is configured to run in does not implement the service.
```

## Root Cause
The service binary `NebulaAgentService.exe` was missing or wasn't built correctly. The Windows Service requires a special executable that implements the Windows Service Control Manager interface.

## Solution
The `NebulaAgentService.exe` file must be built from `service.py` using PyInstaller with specific parameters.

### Building the Complete Installer

Use the new `build-installer.bat` script which does everything automatically:

```cmd
cd windows_client
build-installer.bat
```

This script:
1. ✅ Downloads Nebula binaries
2. ✅ Builds `NebulaAgent.exe` (CLI)
3. ✅ Builds `NebulaAgentService.exe` (Windows Service) - **This is the key file**
4. ✅ Builds `NebulaAgentGUI.exe` (GUI)
5. ✅ Copies all files to `installer/` directory
6. ✅ Builds NSIS installer
7. ✅ Outputs complete installer: `dist\ManagedNebulaInstaller-X.X.X.exe`

### Manual Build (If Needed)

If you need to rebuild just the service executable:

```cmd
cd windows_client

pyinstaller --onefile ^
    --name NebulaAgentService ^
    --icon=installer\nebula.ico ^
    --add-data "config.py;." ^
    --add-data "agent.py;." ^
    --hidden-import=win32timezone ^
    --hidden-import=win32serviceutil ^
    --hidden-import=win32service ^
    --hidden-import=win32event ^
    --hidden-import=servicemanager ^
    --hidden-import=yaml ^
    service.py
```

The output will be in `dist\NebulaAgentService.exe`.

## Verification

After building and installing, verify the service:

```cmd
# Check if service exists
sc query NebulaAgent

# Try to start service
sc start NebulaAgent

# Check service status
sc query NebulaAgent
```

Or use PowerShell:

```powershell
# Check service
Get-Service NebulaAgent

# Start service
Start-Service NebulaAgent

# Check status
Get-Service NebulaAgent | Select-Object Name, Status, StartType
```

## Technical Details

### Why This Error Happens
- Windows services require a specific interface (`ServiceFramework` from `win32serviceutil`)
- Regular Python scripts or CLI executables don't have this interface
- The service binary must call `win32serviceutil.HandleCommandLine()` and implement `SvcDoRun()` method

### The Service Executable
`service.py` implements the Windows Service interface:
- Uses `win32serviceutil.ServiceFramework` base class
- Implements `SvcDoRun()` - main service loop
- Implements `SvcStop()` - graceful shutdown
- Handles service events properly

### Key Files
- `service.py` - Service implementation source
- `agent.py` - Core agent logic (imported by service)
- `config.py` - Configuration management
- `NebulaAgentService.exe` - Built service executable (required)
- `installer.nsi` - NSIS installer script (expects the .exe file)

## Build Process Flow

```
service.py → PyInstaller → NebulaAgentService.exe → Copy to installer/ → NSIS → Final Installer
```

The installer then:
1. Copies `NebulaAgentService.exe` to `C:\Program Files\ManagedNebula\`
2. Creates service with: `sc create NebulaAgent binPath="..." type=share`
3. Sets service to start automatically on boot

## Troubleshooting

### Service Won't Start After Build
1. Verify the file exists:
   ```cmd
   dir "C:\Program Files\ManagedNebula\NebulaAgentService.exe"
   ```

2. Test the executable directly:
   ```cmd
   "C:\Program Files\ManagedNebula\NebulaAgentService.exe" debug
   ```

3. Check event logs:
   ```powershell
   Get-EventLog -LogName Application -Source NebulaAgent -Newest 10
   ```

### PyInstaller Build Fails
Ensure all dependencies are installed:
```cmd
pip install pyinstaller pywin32 httpx pystray pyyaml
```

### Service Installs But Won't Start
- Ensure service type is `share` (not `own`)
- Verify configuration file exists at `C:\ProgramData\Nebula\agent.ini`
- Check permissions on `C:\ProgramData\Nebula` directory
- Review `C:\ProgramData\Nebula\logs\agent.log`

## References
- [Windows Service Control Manager](https://docs.microsoft.com/en-us/windows/win32/services/service-control-manager)
- [PyWin32 Service Framework](https://mhammond.github.io/pywin32/win32serviceutil.html)
- [PyInstaller Documentation](https://pyinstaller.org/en/stable/)
- [NSIS Documentation](https://nsis.sourceforge.io/Docs/)
