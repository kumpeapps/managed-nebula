# Release Notes - ManagedNebula macOS Client v1.0.0

**Release Date**: January 15, 2024

## Overview

The ManagedNebula macOS Client v1.0.0 is a native menu bar application that provides seamless integration with Managed Nebula VPN networks on macOS. This release addresses the Docker networking limitations on macOS by running Nebula directly on the host system.

## What's New

### 🎉 Initial Release

This is the first official release of the ManagedNebula macOS client.

### ✨ Key Features

#### Native macOS Integration
- **Menu Bar Application**: Runs as a native macOS menu bar app with system tray icon
- **Status Indicators**: Real-time connection status displayed in menu bar
- **Native UI**: Preferences window using native macOS controls
- **Launch at Login**: Optional automatic startup on user login

#### Secure Authentication
- **Keychain Integration**: Client tokens stored securely in macOS Keychain
- **File Permissions**: Private keys protected with 0600 permissions
- **No Plaintext Secrets**: Sensitive data never logged or stored in plaintext

#### Nebula VPN Management
- **Automatic Keypair Generation**: Uses `nebula-cert` to generate Ed25519 keypairs
- **Configuration Management**: Fetches and manages Nebula configuration from server
- **TUN Interface**: Creates native macOS TUN interfaces for VPN connectivity
- **Smart Restart**: Hash-based change detection prevents unnecessary restarts

#### Automatic Updates
- **Periodic Polling**: Configurable interval for checking config updates (default: 24 hours)
- **Manual Updates**: "Check for Updates" option for immediate update check
- **Certificate Rotation**: Automatically handles certificate renewal

#### User Experience
- **Simple Setup**: Easy-to-use preferences dialog
- **Quick Actions**: Connect, Disconnect, View Logs, Check for Updates
- **Error Handling**: Clear, user-friendly error messages
- **Log Access**: One-click access to Nebula logs for troubleshooting

## System Requirements

### Minimum Requirements
- **Operating System**: macOS 12 (Monterey) or later
- **Processor**: Intel or Apple Silicon (M1/M2/M3)
- **RAM**: 50 MB minimum
- **Disk Space**: 100 MB (including Nebula binaries)
- **Network**: Internet connection to reach Managed Nebula server

### Required Software
- **Nebula**: v1.6.0 or later (included in installation script)
- **nebula-cert**: v1.6.0 or later (included in installation script)

## Installation

### Automated Installation (Recommended)

```bash
git clone https://github.com/kumpeapps/managed-nebula.git
cd managed-nebula/macos_client
./install.sh
```

The installer will:
1. Download and install Nebula binaries
2. Build the ManagedNebula client
3. Install to `/usr/local/bin` (optional)

### Manual Installation

1. Install Nebula binaries:
   ```bash
   curl -LO https://github.com/slackhq/nebula/releases/latest/download/nebula-darwin.tar.gz
   tar xzf nebula-darwin.tar.gz
   sudo mv nebula nebula-cert /usr/local/bin/
   ```

2. Build the client:
   ```bash
   make build
   ```

3. Run or install:
   ```bash
   # Run from build directory
   ./.build/release/ManagedNebula
   
   # Or install globally
   sudo make install
   ManagedNebula
   ```

## Configuration

### First-Time Setup

1. Launch ManagedNebula
2. Click menu bar icon → Preferences
3. Enter:
   - **Server URL**: Your Managed Nebula server (e.g., `https://nebula.example.com`)
   - **Client Token**: Token from server web interface
   - **Poll Interval**: How often to check for updates (default: 24 hours)
4. Enable options:
   - ✓ Auto-start Nebula (recommended)
   - ✓ Launch at login (optional)
5. Click Save

### Obtaining a Client Token

1. Log in to Managed Nebula web interface
2. Navigate to Clients
3. Create or select a client
4. Click "Generate Token"
5. Copy token and paste into macOS client preferences

## Usage

### Connecting to VPN

1. Click menu bar icon
2. Select "Connect"
3. Wait for status to change to "Connected"

### Disconnecting

1. Click menu bar icon
2. Select "Disconnect"

### Checking for Updates

Click menu bar icon → "Check for Updates"

### Viewing Logs

Click menu bar icon → "View Logs"

This opens Finder at the log file location.

## File Locations

### Configuration and Certificates
```
~/Library/Application Support/ManagedNebula/
├── config.yml      # Nebula configuration
├── host.key        # Private key (0600 permissions)
├── host.pub        # Public key
├── host.crt        # Client certificate
└── ca.crt          # CA certificate chain
```

### Logs
```
~/Library/Logs/ManagedNebula/
└── nebula.log      # Nebula daemon output
```

### Secure Storage
- **Client Token**: Stored in macOS Keychain
  - Service: `com.managednebula.client`
  - Account: `client-token`

## Advantages Over Docker Client

### Direct Host Networking
- **No VM Layer**: Docker Desktop on macOS uses a Linux VM, isolating network interfaces
- **Native TUN**: Creates TUN interface directly on macOS, accessible from host
- **Full Connectivity**: Other applications on macOS can use VPN directly

### Better Integration
- **Menu Bar**: Always accessible from system tray
- **Keychain**: Secure token storage using macOS Keychain
- **Native UI**: Follows macOS design patterns and conventions
- **Launch at Login**: Standard macOS functionality

### Lower Overhead
- **No Container**: Runs directly on macOS without container overhead
- **Lower Memory**: ~30 MB vs ~100+ MB for Docker container
- **Lower CPU**: Minimal CPU usage when idle

## Known Limitations

### Version 1.0.0
1. **No Automatic Updates**: Application must be updated manually
2. **Limited UI**: Basic menu bar interface, no detailed statistics
3. **No System VPN**: Doesn't use Network Extension framework
4. **Manual Nebula Install**: Nebula binaries must be installed separately
5. **No GUI Editor**: Configuration editing requires text editor

### Workarounds
- **Updates**: Check GitHub releases for new versions
- **Statistics**: View logs for connection details
- **System VPN**: Planned for future release
- **Nebula Install**: Use included `install.sh` script

## Troubleshooting

### Common Issues

#### "Invalid client token"
**Solution**: Verify token in preferences matches server, generate new token if needed

#### "Nebula binary not found"
**Solution**: Install Nebula binaries:
```bash
curl -LO https://github.com/slackhq/nebula/releases/latest/download/nebula-darwin.tar.gz
tar xzf nebula-darwin.tar.gz
sudo mv nebula nebula-cert /usr/local/bin/
```

#### Can't reach other clients
**Solution**: 
1. Verify connection status shows "Connected"
2. Check firewall rules on server
3. Ensure clients are in same IP pool
4. Verify lighthouse configuration

For more troubleshooting, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

## Documentation

- **README.md**: Complete user documentation
- **QUICKSTART.md**: 5-minute quick start guide
- **TROUBLESHOOTING.md**: Detailed troubleshooting guide
- **CONTRIBUTING.md**: Developer contribution guidelines
- **TEST_PLAN.md**: Comprehensive test plan

## Security Considerations

### What We Do
✅ Store tokens in macOS Keychain
✅ Set private keys to 0600 permissions
✅ Never log sensitive data
✅ Validate SSL certificates
✅ Use secure subprocess management

### What We Don't Do
❌ Store passwords in UserDefaults
❌ Disable SSL verification
❌ Log tokens or private keys
❌ Transmit private keys to server
❌ Run with unnecessary privileges

### Best Practices
1. **Use HTTPS**: Always configure server URL with HTTPS in production
2. **Rotate Tokens**: Regularly generate new client tokens
3. **Update Regularly**: Keep client and Nebula binaries updated
4. **Monitor Logs**: Check logs for suspicious activity
5. **Secure Server**: Ensure server has proper firewall rules

## Reporting Issues

### Before Reporting
1. Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
2. Search existing GitHub issues
3. Verify you're on latest version

### When Reporting
Include:
- macOS version
- Hardware (Intel vs Apple Silicon)
- ManagedNebula client version
- Nebula binary version
- Steps to reproduce
- Relevant logs (sanitized)

### Where to Report
- **Bugs**: [GitHub Issues](https://github.com/kumpeapps/managed-nebula/issues)
- **Questions**: [GitHub Discussions](https://github.com/kumpeapps/managed-nebula/discussions)

## Future Roadmap

### Planned for v1.1
- [ ] .app bundle distribution
- [ ] Code signing and notarization
- [ ] Automatic update mechanism
- [ ] Connection statistics in menu
- [ ] Traffic monitoring

### Planned for v2.0
- [ ] Network Extension framework
- [ ] Multi-profile support
- [ ] GUI configuration editor
- [ ] Touch Bar support
- [ ] AppleScript integration

## Credits

### Development
- **Author**: ManagedNebula Team
- **License**: MIT License

### Dependencies
- **Nebula**: [github.com/slackhq/nebula](https://github.com/slackhq/nebula)
- **Swift**: Apple Inc.
- **macOS**: Apple Inc.

### Community
- **Contributors**: See [CONTRIBUTING.md](CONTRIBUTING.md)
- **Testers**: Community beta testers
- **Feedback**: GitHub issue reporters

## License

Copyright © 2025 KumpeApps

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

---

**Download**: [GitHub Releases](https://github.com/kumpeapps/managed-nebula/releases)

**Documentation**: [README.md](README.md)

**Support**: [GitHub Issues](https://github.com/kumpeapps/managed-nebula/issues)
