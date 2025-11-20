# ManagedNebula macOS Client - Quick Start Guide

Get up and running with the ManagedNebula macOS client in 5 minutes.

## Prerequisites

- macOS 12 (Monterey) or later
- Admin access to install binaries
- A Managed Nebula server with a client token

## Installation

### Option 1: Automated Installation (Recommended)

```bash
# Clone the repository
git clone https://github.com/kumpeapps/managed-nebula.git
cd managed-nebula/macos_client

# Run the installer
./install.sh
```

The installer will:
- Download and install Nebula binaries
- Build the ManagedNebula client
- Install to `/usr/local/bin`

### Option 2: Manual Installation

1. **Install Nebula**:
   ```bash
   curl -LO https://github.com/slackhq/nebula/releases/latest/download/nebula-darwin.tar.gz
   tar xzf nebula-darwin.tar.gz
   sudo mv nebula nebula-cert /usr/local/bin/
   sudo chmod +x /usr/local/bin/nebula /usr/local/bin/nebula-cert
   ```

2. **Build the client**:
   ```bash
   cd macos_client
   make build
   ```

3. **Install (optional)**:
   ```bash
   sudo make install
   ```

## Configuration

### Step 1: Get Your Client Token

1. Open your Managed Nebula web interface
2. Navigate to **Clients**
3. Create a new client or select an existing one
4. Click **Generate Token** and copy it

### Step 2: Launch the Application

```bash
# If installed globally
ManagedNebula

# Or run from build directory
./.build/release/ManagedNebula
```

The application will appear as a network icon in your menu bar.

### Step 3: Configure Settings

1. Click the menu bar icon
2. Select **Preferences...**
3. Enter your details:
   - **Server URL**: `https://your-nebula-server.com`
   - **Client Token**: Paste the token from Step 1
   - **Poll Interval**: `24` (hours)
4. Enable **Auto-start Nebula** ✓
5. Click **Save**

### Step 4: Connect

1. Click the menu bar icon
2. Select **Connect**
3. Wait for status to change to "Connected"

You're now connected to your Nebula VPN!

## Verification

### Check Connection Status

The menu bar icon shows your connection status:
- Grey icon: Disconnected
- Normal icon: Connected

Click the icon to see detailed status.

### Test Connectivity

```bash
# Check your Nebula IP address
ifconfig | grep -A 5 nebula1

# Ping another Nebula client (replace with actual IP)
ping 10.100.0.2
```

### View Logs

Click the menu bar icon → **View Logs** to open the Nebula log file.

Or view from terminal:
```bash
tail -f ~/Library/Logs/ManagedNebula/nebula.log
```

## Common Issues

### "Nebula binary not found"

**Solution**: Install Nebula to `/usr/local/bin`:
```bash
curl -LO https://github.com/slackhq/nebula/releases/latest/download/nebula-darwin.tar.gz
tar xzf nebula-darwin.tar.gz
sudo mv nebula nebula-cert /usr/local/bin/
```

### "Invalid client token"

**Solution**: 
- Verify you copied the complete token
- Check the token hasn't expired on the server
- Generate a new token if needed

### "Permission denied" when creating TUN interface

**Solution**: Nebula needs elevated privileges to create network interfaces. The application handles this automatically, but you may need to approve the security prompt.

### Can't reach other clients

**Solution**:
1. Verify you're connected (menu bar status)
2. Check firewall rules on the server
3. Ensure clients are in the same IP pool
4. Verify lighthouse configuration

## Next Steps

- **Launch at Login**: Enable in Preferences to auto-start on login
- **Automatic Updates**: The client checks for config updates every 24 hours
- **View Logs**: Use menu bar → View Logs for troubleshooting
- **Disconnect**: Click menu bar icon → Disconnect when not needed

## File Locations

Configuration files are stored at:
```
~/Library/Application Support/ManagedNebula/
  ├── config.yml      # Nebula configuration
  ├── host.key        # Private key (secure)
  ├── host.pub        # Public key
  ├── host.crt        # Client certificate
  └── ca.crt          # CA certificate chain

~/Library/Logs/ManagedNebula/
  └── nebula.log      # Nebula daemon logs
```

Token is stored securely in **macOS Keychain**.

## Support

For more detailed documentation, see [README.md](README.md).

For issues or questions:
- Check [Troubleshooting](README.md#troubleshooting) in README.md
- Open an issue on GitHub
- Review server logs on the Managed Nebula server

## Uninstallation

To remove the application:

```bash
# Remove binary
sudo rm /usr/local/bin/ManagedNebula

# Remove configuration files
rm -rf ~/Library/Application\ Support/ManagedNebula
rm -rf ~/Library/Logs/ManagedNebula

# Remove token from Keychain
# Open Keychain Access app → search "managednebula" → delete item

# Optional: Remove Nebula binaries
sudo rm /usr/local/bin/nebula /usr/local/bin/nebula-cert
```
