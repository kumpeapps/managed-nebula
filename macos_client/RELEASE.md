# Release Process for macOS Client

This document describes how to create and publish releases of the ManagedNebula macOS client.

## Quick Release

### 1. Build Installers Locally

```bash
cd macos_client
make package
```

This creates in `dist/`:
- `ManagedNebula-1.0.0.pkg` - Complete installer (~26MB with Nebula binaries)
- `ManagedNebula-1.0.0.dmg` - App bundle only (~100KB, requires Homebrew)

### 2. Test the Installers

**Test PKG:**
```bash
# Install
sudo installer -pkg dist/ManagedNebula-1.0.0.pkg -target /

# Verify
ls -la /Applications/ManagedNebula.app
ls -la /usr/local/bin/nebula*
ls -la /Library/LaunchDaemons/com.managednebula.client.plist

# Test run
open /Applications/ManagedNebula.app
```

**Test DMG:**
```bash
# Open DMG
open dist/ManagedNebula-1.0.0.dmg

# Drag to Applications manually
# Then test launch
```

### 3. Create GitHub Release

```bash
# Tag the release
git tag -a macos-v1.0.0 -m "macOS Client v1.0.0"
git push origin macos-v1.0.0
```

The GitHub Actions workflow (`.github/workflows/macos-release.yml`) will automatically:
- Build the app
- Create installers
- Create a GitHub release
- Upload both PKG and DMG files

## Manual Release (Without GitHub Actions)

If you need to create a release manually:

1. **Build installers**:
   ```bash
   cd macos_client
   make package
   ```

2. **Create release on GitHub**:
   - Go to https://github.com/kumpeapps/managed-nebula/releases/new
   - Tag: `macos-v1.0.0`
   - Title: `ManagedNebula macOS Client v1.0.0`
   - Description: Use template below
   - Upload: `dist/ManagedNebula-1.0.0.pkg` and `dist/ManagedNebula-1.0.0.dmg`

### Release Description Template

```markdown
# ManagedNebula macOS Client v1.0.0

## Installation Options

### PKG Installer (Recommended)
- **Complete installation** with Nebula binaries and LaunchDaemon
- **Download**: `ManagedNebula-1.0.0.pkg` (26MB)
- **Install**: Double-click to install
- **Includes**: App + Nebula v1.8.2 + Auto-start configuration

### DMG Installer
- **For users who already have Nebula via Homebrew**
- **Download**: `ManagedNebula-1.0.0.dmg` (100KB)
- **Install**: Drag to Applications folder
- **Requires**: `brew install nebula`

## What's New

- Initial release of native macOS client
- Menu bar integration with system tray
- Secure Keychain storage for tokens
- Automatic configuration updates from server
- Native Nebula daemon management

## System Requirements

- macOS 12 (Monterey) or later
- Intel or Apple Silicon Mac
- Administrator access for installation

## Quick Start

1. Download and install using PKG or DMG
2. Launch ManagedNebula from Applications
3. Click the menu bar icon → Preferences
4. Enter your server URL and client token
5. Click Connect!

## Documentation

- [Full README](https://github.com/kumpeapps/managed-nebula/blob/main/macos_client/README.md)
- [Troubleshooting Guide](https://github.com/kumpeapps/managed-nebula/blob/main/macos_client/TROUBLESHOOTING.md)
- [Implementation Details](https://github.com/kumpeapps/managed-nebula/blob/main/macos_client/IMPLEMENTATION_SUMMARY.md)

## Checksums

### SHA256
```
# Generate with: shasum -a 256 dist/*
<paste checksums here>
```
```

## Code Signing (For Distribution)

For official distribution outside of GitHub releases, you should code sign and notarize:

### 1. Code Sign

```bash
# Sign the app bundle
codesign --deep --force --verify --verbose \
  --sign "Developer ID Application: Your Name (TEAM_ID)" \
  --options runtime \
  ManagedNebula.app

# Sign the PKG
productsign --sign "Developer ID Installer: Your Name (TEAM_ID)" \
  ManagedNebula-1.0.0.pkg \
  ManagedNebula-1.0.0-signed.pkg
```

### 2. Notarize

```bash
# Submit for notarization
xcrun notarytool submit ManagedNebula-1.0.0-signed.pkg \
  --apple-id "your@email.com" \
  --team-id "TEAM_ID" \
  --password "app-specific-password" \
  --wait

# Staple the ticket
xcrun stapler staple ManagedNebula-1.0.0-signed.pkg
```

### 3. Verify

```bash
# Verify code signature
codesign --verify --deep --strict --verbose=2 ManagedNebula.app

# Verify notarization
spctl --assess --verbose=2 --type install ManagedNebula-1.0.0-signed.pkg
```

## Version Numbering

Follow semantic versioning:
- **Major**: Breaking changes (e.g., 2.0.0)
- **Minor**: New features (e.g., 1.1.0)
- **Patch**: Bug fixes (e.g., 1.0.1)

Update version in:
- `create-installer.sh` - `VERSION="x.y.z"`
- `create-app-bundle.sh` - `VERSION="x.y.z"`
- `Info.plist.example` - `CFBundleShortVersionString`

## Automated Release Workflow

The GitHub Actions workflow (`.github/workflows/macos-release.yml`) is triggered by:

```bash
# Create and push a tag starting with 'macos-v'
git tag -a macos-v1.0.0 -m "Release v1.0.0"
git push origin macos-v1.0.0
```

The workflow will:
1. ✓ Checkout code
2. ✓ Setup Xcode
3. ✓ Build the Swift app
4. ✓ Create installers
5. ✓ Create GitHub release
6. ✓ Upload PKG and DMG files

## Troubleshooting

### Build fails in GitHub Actions
- Check macOS runner version compatibility
- Verify Swift version requirements
- Check Nebula download URL is still valid

### PKG installation fails
- Verify pre/post install scripts have correct permissions
- Check LaunchDaemon plist syntax
- Test locally before releasing

### DMG won't open
- Verify hdiutil command succeeded
- Check DMG format (UDZO is universal)
- Test on both Intel and Apple Silicon Macs

## Rollback

If you need to rollback a release:

1. Delete the GitHub release and tag
2. Fix the issue
3. Increment the patch version
4. Create a new release

Never modify an existing release - always create a new version.
