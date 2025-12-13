# ManagedNebula macOS Client

Native macOS menu bar application for connecting to Managed Nebula VPN networks.

## Overview

The ManagedNebula macOS client provides a native macOS experience for connecting to Nebula mesh VPN networks managed by a Managed Nebula server. Unlike the Docker-based client, this application:

- Creates TUN interfaces directly on macOS (no Docker networking limitations)
- Runs as a menu bar application with system tray integration
- Stores credentials securely in macOS Keychain
- Supports automatic configuration updates via polling
- Provides a native macOS user interface

## Features

- **Native Nebula Integration**: Runs Nebula daemon directly on macOS
- **Menu Bar Application**: System tray icon with connection status
- **Secure Token Storage**: Uses macOS Keychain for client token
- **Automatic Updates**: Polls server for configuration changes
- **Configuration Management**: Persists settings between app launches
- **User-Friendly UI**: Preferences window for easy setup
- **Launch at Login**: Optional automatic startup on login
- **Log Viewing**: Quick access to Nebula logs for troubleshooting

## Requirements

### System Requirements
- macOS 12 (Monterey) or later
- Intel or Apple Silicon processor

### Dependencies
- **Nebula binary**: Download from [Nebula releases](https://github.com/slackhq/nebula/releases)
- **nebula-cert binary**: Included with Nebula distribution
- **Swift 5.9+**: For building from source (included with Xcode)

## Installation

### Option 1: PKG Installer (Recommended for Complete Installation)

The PKG installer includes everything you need: the ManagedNebula app, Nebula binaries, and automatic LaunchDaemon setup.

1. **Download** the latest `.pkg` installer from [releases](https://github.com/kumpeapps/managed-nebula/releases)
2. **Double-click** the PKG file to install
3. **Follow** the installation wizard
4. **Launch** ManagedNebula from Applications
5. **Configure** your server URL and client token in the preferences

The PKG installer will:
- Install ManagedNebula.app to /Applications
- Install Nebula binaries to /usr/local/bin
- Create the LaunchDaemon for auto-start
- Set up necessary directories and permissions

### Option 2: DMG Installer (For Homebrew Users)

If you already have Nebula installed via Homebrew, use the DMG:

1. **Download** the latest `.dmg` from [releases](https://github.com/kumpeapps/managed-nebula/releases)
2. **Open** the DMG file
3. **Drag** ManagedNebula.app to the Applications folder
4. **Install Nebula** via Homebrew if not already installed:
   ```bash
   brew install nebula
   ```
5. **Launch** ManagedNebula from Applications

### Option 3: Build from Source

For developers or those who want to build from source:

1. **Clone the repository**:
   ```bash
   git clone https://github.com/kumpeapps/managed-nebula.git
   cd managed-nebula/macos_client
   ```

2. **Run the automated installer** (builds and installs everything):
   ```bash
   ./install.sh
   ```
   
   Or use Make targets:
   ```bash
   # Create app bundle only
   make app-bundle
   
   # Create both PKG and DMG installers
   make package
   
   # Create just the PKG installer
   make pkg
   
   # Create just the DMG installer
   make dmg
   ```

3. **Manual build steps**:
   ```bash
   # Build release binary
   make build
   
   # Or with Swift directly
   swift build -c release
   
   # Run the application
   .build/release/ManagedNebula
   ```

## Configuration

### First-Time Setup

1. Launch the ManagedNebula application
2. Click the menu bar icon and select **Preferences...**
3. Enter your configuration:
   - **Server URL**: Your Managed Nebula server (e.g., `https://nebula.example.com`)
   - **Client Token**: Token generated from the server web interface
   - **Poll Interval**: How often to check for updates (default: 24 hours)
4. Enable **Auto-start Nebula** to automatically connect
5. Enable **Launch at login** to start the app on login (optional)
6. Click **Save**

### Obtaining a Client Token

1. Log in to your Managed Nebula web interface
2. Navigate to **Clients**
3. Create a new client or select an existing one
4. Click **Generate Token** and copy the token
5. Paste the token into the ManagedNebula preferences

## Usage

### Connecting

After configuration:
1. Click the menu bar icon
2. Select **Connect**
3. The status will change to "Connected" when successful

The application will:
- Generate a keypair if needed (`host.key`, `host.pub`)
- Contact the server and fetch configuration
- Write configuration files to `~/Library/Application Support/ManagedNebula/`
- Start the Nebula daemon
- Create a TUN interface for VPN connectivity

### Disconnecting

1. Click the menu bar icon
2. Select **Disconnect**

This will stop the Nebula daemon and tear down the VPN connection.

### Checking for Updates

The client automatically checks for configuration updates based on the poll interval. To manually check:
1. Click the menu bar icon
2. Select **Check for Updates**

### Viewing Logs

To view Nebula daemon logs:
1. Click the menu bar icon
2. Select **View Logs**

This opens Finder at `~/Library/Logs/ManagedNebula/nebula.log`.

## File Locations

The application stores files in standard macOS locations:

### Configuration and Certificates
- **Base Directory**: `~/Library/Application Support/ManagedNebula/`
- **config.yml**: Nebula configuration file
- **host.key**: Private key (permissions: 0600)
- **host.pub**: Public key
- **host.crt**: Client certificate
- **ca.crt**: CA certificate chain

### Logs
- **Log Directory**: `~/Library/Logs/ManagedNebula/`
- **nebula.log**: Nebula daemon output

### Secure Storage
- **Client Token**: Stored in macOS Keychain
  - Service: `com.managednebula.client`
  - Account: `client-token`

## Troubleshooting

### Connection Issues

**Problem**: "Invalid client token" error

**Solution**: Verify your token in Preferences is correct and hasn't been revoked on the server.

---

**Problem**: "Client is blocked on server"

**Solution**: Contact your Nebula administrator to unblock your client.

---

**Problem**: "Server CA not configured"

**Solution**: The server administrator needs to create a Certificate Authority.

### Nebula Binary Issues

**Problem**: "Nebula binary not found"

**Solution**: Install Nebula and nebula-cert to `/usr/local/bin/`:
```bash
curl -LO https://github.com/slackhq/nebula/releases/latest/download/nebula-darwin.tar.gz
tar xzf nebula-darwin.tar.gz
sudo mv nebula nebula-cert /usr/local/bin/
sudo chmod +x /usr/local/bin/nebula /usr/local/bin/nebula-cert
```

### Permission Issues

**Problem**: Nebula fails to create TUN interface

**Solution**: Run the application with appropriate permissions. The Nebula binary may need elevated privileges to create network interfaces. Consider:
1. Running Nebula as root (not recommended for general use)
2. Setting proper capabilities on the binary
3. Using a privileged helper tool (advanced)

### Network Issues

**Problem**: Can't reach other Nebula clients

**Solution**:
1. Check connection status in menu bar
2. View logs for errors
3. Verify firewall rules on server
4. Ensure client is assigned to correct groups
5. Check lighthouse configuration

### Logs and Debugging

To enable verbose logging:
1. Stop the Nebula daemon
2. Edit `~/Library/Application Support/ManagedNebula/config.yml`
3. Find the `logging` section and set `level: debug`
4. Restart the application

View logs:
```bash
tail -f ~/Library/Logs/ManagedNebula/nebula.log
```

## Security Considerations

### Token Security
- Client tokens are stored in macOS Keychain with `kSecAttrAccessibleAfterFirstUnlock`
- Tokens are never logged or displayed after initial entry
- Rotate tokens regularly for best security

### File Permissions
- Private keys (`host.key`) are set to mode 0600 (owner read/write only)
- Configuration and certificates are world-readable (mode 0644)

### Network Security
- Always use HTTPS for server URLs
- The application validates SSL certificates by default
- Never disable certificate verification in production

## Architecture

### Components

1. **App**: Main application entry point and delegate
2. **Services**:
   - `APIClient`: Communicates with Managed Nebula server
   - `NebulaManager`: Manages Nebula daemon lifecycle
   - `KeychainService`: Secure token storage
   - `PollingService`: Automatic configuration updates
3. **Models**: Data structures for configuration and API responses
4. **UI**: Menu bar and preferences window controllers

### Workflow

```
Launch App
    ↓
Initialize Menu Bar
    ↓
Load Configuration
    ↓
User Clicks "Connect"
    ↓
Load Token from Keychain
    ↓
Generate Keypair (if needed)
    ↓
POST /v1/client/config
    ↓
Write Config Files
    ↓
Start Nebula Daemon
    ↓
Create TUN Interface
    ↓
Connected!
    ↓
Periodic Polling for Updates
```

## API Integration

The client communicates with the Managed Nebula server via REST API:

### Endpoint
```
POST /v1/client/config
```

### Request
```json
{
  "token": "client_token_here",
  "public_key": "-----BEGIN NEBULA ED25519 PUBLIC KEY-----\n...\n-----END NEBULA ED25519 PUBLIC KEY-----\n",
  "client_version": "1.0.0",
  "nebula_version": "1.9.7"
}
```

**Note**: `client_version` and `nebula_version` are optional fields. The macOS client automatically detects:
- Client version from the application bundle (`CFBundleShortVersionString`)
- Nebula version by executing `nebula -version`

These versions are reported to the server for tracking and security advisory purposes.

### Response
```json
{
  "config": "# Nebula Configuration\npki:\n  ca: /etc/nebula/ca.crt\n...",
  "client_cert_pem": "-----BEGIN NEBULA CERTIFICATE-----\n...\n-----END NEBULA CERTIFICATE-----\n",
  "ca_chain_pems": ["-----BEGIN NEBULA CERTIFICATE-----\n...\n-----END NEBULA CERTIFICATE-----\n"],
  "cert_not_before": "2024-01-15T10:30:00Z",
  "cert_not_after": "2024-07-15T10:30:00Z",
  "lighthouse": false,
  "key_path": "/var/lib/nebula/host.key"
}
```

### Error Codes
- `401`: Invalid token
- `403`: Client blocked on server
- `409`: Client has no IP assignment
- `503`: Server CA not configured

## Development

### Project Structure
```
macos_client/
├── Package.swift                # Swift Package Manager manifest
├── ManagedNebula/
│   └── Sources/
│       ├── App/                 # Application entry point
│       │   ├── main.swift
│       │   └── AppDelegate.swift
│       ├── Services/            # Business logic
│       │   ├── APIClient.swift
│       │   ├── NebulaManager.swift
│       │   ├── KeychainService.swift
│       │   ├── PollingService.swift
│       │   └── FileManager+ManagedNebula.swift
│       ├── Models/              # Data models
│       │   └── Configuration.swift
│       └── UI/                  # User interface
│           ├── MenuBarController.swift
│           └── PreferencesWindowController.swift
└── README.md
```

### Building
```bash
# Debug build
swift build

# Release build
swift build -c release

# Run tests (if available)
swift test
```

### Building Installers

To create PKG and DMG installers:

```bash
# Build both PKG and DMG
./create-installer.sh

# For production builds with code signing
./create-installer-prod.sh
```

**Environment Variables:**
- `VERSION`: Set the app version (default: 1.0.0)
- `NEBULA_VERSION`: Set Nebula version to download (default: v1.10.0)
- `ALLOW_SUDO=1`: Enable automatic sudo elevation for cleaning root-owned files (not recommended for CI/CD)

**Note for CI/CD:** The build script will fail with a clear error if it cannot remove root-owned files from previous builds. This prevents builds from hanging indefinitely waiting for password input. To clean manually:
```bash
sudo rm -rf dist/
```

Or enable automatic elevation (not recommended for unattended builds):
```bash
ALLOW_SUDO=1 ./create-installer.sh
```

### Code Style
- Follow Swift API Design Guidelines
- Use SwiftLint for consistent formatting (optional)
- Document public APIs with Swift DocC comments

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly on macOS
5. Submit a pull request

## License

This project is licensed under the MIT License. See the [LICENSE](../LICENSE) file for details.

## Support

For issues and questions:
- **GitHub Issues**: Report bugs and feature requests
- **Documentation**: Check the main [README](../README.md)
- **Server Issues**: See server documentation in `server/README.md`

## Acknowledgments

- [Nebula](https://github.com/slackhq/nebula) - The excellent mesh VPN by Slack
- Managed Nebula server and web interface developers
- macOS community for frameworks and tools
