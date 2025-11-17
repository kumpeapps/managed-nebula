# Changelog - ManagedNebula macOS Client

All notable changes to the ManagedNebula macOS client will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2024-01-15

### Added
- Initial release of native macOS client
- Menu bar application with system tray integration
- Preferences window for configuration
- Secure token storage in macOS Keychain
- Automatic keypair generation with nebula-cert
- Configuration fetching from Managed Nebula server
- Automatic polling for config updates (configurable interval)
- Hash-based change detection to avoid unnecessary restarts
- Nebula daemon lifecycle management
- Connection status tracking and display
- Quick actions: Connect/Disconnect, Check for Updates, View Logs
- Launch at login support (configurable)
- Auto-start Nebula option
- File management with proper permissions (0600 for keys)
- Comprehensive error handling and user-friendly error messages
- macOS 12+ support (Intel and Apple Silicon)

### Documentation
- Comprehensive README.md with installation and usage instructions
- Quick start guide (QUICKSTART.md)
- Troubleshooting guide (TROUBLESHOOTING.md)
- Contributing guidelines (CONTRIBUTING.md)
- Automated installation script (install.sh)
- Makefile for easy building

### Technical Details
- Swift 5.9+ implementation
- URLSession for async API communication
- Security framework for Keychain integration
- CryptoKit for SHA256 hash calculations
- NSStatusBar for menu bar integration
- UserDefaults for configuration persistence
- Subprocess management for Nebula daemon

## Future Enhancements

### Planned Features
- [ ] .app bundle packaging for easier distribution
- [ ] Code signing and notarization for macOS Gatekeeper
- [ ] Automatic update mechanism (Sparkle framework)
- [ ] Network Extension framework for system-level VPN
- [ ] Status bar icon color change based on connection status
- [ ] Detailed connection statistics in menu
- [ ] Traffic monitoring (bytes sent/received)
- [ ] Connected peers list in menu
- [ ] Quick connect/disconnect keyboard shortcut
- [ ] Notification Center integration for status changes
- [ ] Export logs functionality
- [ ] Configuration profile import/export
- [ ] Multi-profile support (switch between servers)

### Potential Improvements
- [ ] Unit tests for services
- [ ] UI tests for menu and preferences
- [ ] CI/CD pipeline for automated builds
- [ ] Crash reporting integration
- [ ] Analytics (opt-in, privacy-respecting)
- [ ] Localization support (internationalization)
- [ ] Dark mode optimization
- [ ] Touch Bar support (for applicable MacBooks)
- [ ] AppleScript/Shortcuts integration
- [ ] Command-line interface for automation

### Known Limitations
- Requires Nebula binaries to be installed separately
- No GUI for viewing/editing configuration directly
- Launch at login requires manual implementation
- No automatic update mechanism yet
- Limited to macOS 12+ (no support for older versions)

## Version History

### [1.0.0] - 2024-01-15
First stable release of the macOS client.

---

For detailed information about changes, see the [Git commit history](https://github.com/kumpeapps/managed-nebula/commits/main/macos_client).
