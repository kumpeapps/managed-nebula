# Managed Nebula Windows Client

A native Windows client for Managed Nebula that manages Nebula mesh VPN connections on Windows workstations and servers.

## Features

- **Automatic Configuration**: Polls the Managed Nebula server for configuration updates
- **Windows Service**: Runs as a Windows Service that starts automatically on boot
- **GUI Configuration**: System tray application for easy configuration and monitoring
- **Certificate Management**: Automatically generates and manages Nebula certificates
- **Version Reporting**: Reports client and Nebula versions to the server for monitoring
- **Secure Storage**: Uses Windows ACLs to protect private keys and configuration

## Requirements

- Windows 10/11 or Windows Server 2019/2022
- Administrator privileges for installation
- Network access to Managed Nebula server
- Client token from Managed Nebula web interface

## Installation

### Download Pre-built Release

Pre-built Windows executables are available from the [GitHub Releases](https://github.com/kumpeapps/managed-nebula/releases) page.

1. Download `NebulaAgent-windows-X.X.X.zip` from the latest release
2. Extract the ZIP file
3. Follow the Quick Install steps below

### Quick Install (PowerShell)

1. Download the latest release ZIP file
2. Extract to a temporary directory
3. Open PowerShell as Administrator
4. Run the installer:

```powershell
# Basic installation
.\install.ps1

# Then run the GUI to configure
.\NebulaAgentGUI.exe

# Or install with token via command line
.\install.ps1 -Token "your-client-token" -ServerUrl "https://your-server:8080"
```

## GUI Application

The Windows client includes a system tray GUI application (`NebulaAgentGUI.exe`) that provides:

- **System Tray Icon**: Shows connection status (green = connected, gray = disconnected)
- **Quick Actions**: Connect/Disconnect, Check for Updates, View Logs
- **Configuration Window**: Easy setup of server URL, client token, and other settings
- **Status Display**: Shows current connection status, agent version, and Nebula version

### Using the GUI

1. Run `NebulaAgentGUI.exe`
2. The app will appear in the system tray
3. Right-click the tray icon to access the menu
4. Select "Configuration..." to open the settings window
5. Enter your Server URL and Client Token
6. Click "Save" to apply settings

### Manual Installation

1. Create directory: `C:\ProgramData\Nebula`
2. Copy binaries to: `C:\ProgramData\Nebula\bin\`
3. Create configuration file: `C:\ProgramData\Nebula\agent.ini`
4. Install the Windows Service:
   ```cmd
   sc create NebulaAgent binPath="C:\ProgramData\Nebula\bin\NebulaAgentService.exe" start=auto
   ```
5. Start the service:
   ```cmd
   sc start NebulaAgent
   ```

## Configuration

Configuration is stored in `C:\ProgramData\Nebula\agent.ini`:

```ini
[agent]
# Managed Nebula server URL
server_url = https://your-server.example.com:8080

# Client authentication token
client_token = your-client-token-here

# How often to check for updates (hours)
poll_interval_hours = 24

# Logging level: DEBUG, INFO, WARNING, ERROR
log_level = INFO

# Automatically start Nebula daemon
auto_start_nebula = true
```

### Environment Variables

Configuration can also be set via environment variables (takes precedence):

| Variable | Description |
|----------|-------------|
| `CLIENT_TOKEN` | Client authentication token |
| `SERVER_URL` | Managed Nebula server URL |
| `POLL_INTERVAL_HOURS` | Update check interval (hours) |
| `LOG_LEVEL` | Logging level |
| `ALLOW_SELF_SIGNED_CERT` | Set to `true` to allow self-signed SSL certificates |

## File Locations

| Path | Description |
|------|-------------|
| `C:\ProgramData\Nebula\config.yml` | Nebula configuration |
| `C:\ProgramData\Nebula\host.key` | Private key (restricted permissions) |
| `C:\ProgramData\Nebula\host.pub` | Public key |
| `C:\ProgramData\Nebula\host.crt` | Client certificate |
| `C:\ProgramData\Nebula\ca.crt` | CA certificate chain |
| `C:\ProgramData\Nebula\agent.ini` | Agent configuration |
| `C:\ProgramData\Nebula\logs\agent.log` | Agent logs |
| `C:\ProgramData\Nebula\bin\` | Binary files |

## Service Management

### PowerShell

```powershell
# Check service status
Get-Service NebulaAgent

# Start service
Start-Service NebulaAgent

# Stop service
Stop-Service NebulaAgent

# Restart service
Restart-Service NebulaAgent
```

### Command Prompt

```cmd
sc query NebulaAgent
sc start NebulaAgent
sc stop NebulaAgent
```

### Services Console

1. Press `Win + R`
2. Type `services.msc`
3. Find "Managed Nebula Agent"
4. Right-click to Start/Stop/Restart

## CLI Commands

```powershell
# Show status
NebulaAgent.exe --status

# Show version
NebulaAgent.exe --version

# Run once (fetch config)
NebulaAgent.exe --once

# Run once and restart Nebula if config changed
NebulaAgent.exe --once --restart

# Run in debug mode
NebulaAgent.exe --loop --log-level DEBUG
```

## Uninstallation

### Using Uninstaller Script

```powershell
# Uninstall (keep configuration)
.\uninstall.ps1

# Uninstall and remove all data
.\uninstall.ps1 -Purge
```

### Manual Uninstallation

1. Stop and remove the service:
   ```cmd
   sc stop NebulaAgent
   sc delete NebulaAgent
   ```
2. Kill any running Nebula process:
   ```cmd
   taskkill /IM nebula.exe /F
   ```
3. Remove the installation directory:
   ```cmd
   rmdir /s /q "C:\ProgramData\Nebula"
   ```

## Building from Source

### Prerequisites

- Python 3.11+
- pip
- Internet access (for downloading Nebula binaries)

### Build Steps

1. Clone the repository:
   ```cmd
   git clone https://github.com/kumpeapps/managed-nebula.git
   cd managed-nebula\windows_client
   ```

2. Install dependencies:
   ```cmd
   pip install -r requirements.txt
   ```

3. Run the build script:
   ```cmd
   build.bat --version 1.0.0 --nebula-version 1.9.7
   ```

4. The built package will be in `dist\`

## Troubleshooting

### Service Won't Start

1. Check the event log:
   ```powershell
   Get-EventLog -LogName Application -Source NebulaAgent -Newest 10
   ```

2. Check agent log:
   ```powershell
   Get-Content "C:\ProgramData\Nebula\logs\agent.log" -Tail 50
   ```

3. Verify configuration:
   ```powershell
   NebulaAgent.exe --status
   ```

### Connection Issues

1. Test connectivity to server:
   ```powershell
   Test-NetConnection your-server.example.com -Port 8080
   ```

2. Check Nebula config:
   ```powershell
   nebula.exe -config "C:\ProgramData\Nebula\config.yml" -test
   ```

### Permission Denied

1. Ensure running as Administrator
2. Check file permissions:
   ```powershell
   Get-Acl "C:\ProgramData\Nebula"
   ```

### Nebula Won't Start

1. Validate configuration:
   ```cmd
   "C:\ProgramData\Nebula\bin\nebula.exe" -config "C:\ProgramData\Nebula\config.yml" -test
   ```

2. Check Windows Firewall:
   ```powershell
   New-NetFirewallRule -DisplayName "Nebula VPN" -Direction Inbound -Protocol UDP -LocalPort 4242 -Action Allow
   ```

## Security

- Private keys are stored with restricted ACLs (SYSTEM and Administrators only)
- Configuration file is stored in a protected directory
- Service runs as LocalSystem account
- Supports HTTPS with certificate validation
- Client token should be kept confidential

## Logging

Logs are written to `C:\ProgramData\Nebula\logs\agent.log`

To enable debug logging, edit `agent.ini`:
```ini
log_level = DEBUG
```

Or set environment variable:
```cmd
set LOG_LEVEL=DEBUG
```

## Related

- [Managed Nebula Server](../server/README.md)
- [macOS Client](../macos_client/README.md)
- [Linux Client](../client/README.md)
- [Nebula VPN](https://github.com/slackhq/nebula)

## License

See [LICENSE](../LICENSE) for details.
