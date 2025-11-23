# Nebula Version Update Guide

## Current Version
**Nebula v1.9.7** (updated 2025-11-23)

## How to Update Nebula Version

The ManagedNebula macOS client installer includes the Nebula binaries. To update to a new Nebula version:

### 1. Update Installation Scripts

Both scripts now support environment variables for easy version updates:

```bash
# Build with specific Nebula version
NEBULA_VERSION=v1.9.7 ./create-installer.sh

# Or for install.sh
NEBULA_VERSION=v1.9.7 ./install.sh
```

**Default versions are set in:**
- `create-installer.sh` - Line ~17: `NEBULA_VERSION="${NEBULA_VERSION:-v1.9.7}"`
- `install.sh` - Line ~6: `NEBULA_VERSION="${NEBULA_VERSION:-v1.9.7}"`

### 2. Update Documentation (Optional)

If you want to update the documentation to reflect the new default version:

**Files to update:**
- `DEPLOYMENT_READY.md` - Line 8: "Nebula v1.9.7 binaries"
- `RELEASE.md` - Line 85: "Includes: App + Nebula v1.9.7"
- `VERSION_DISPLAY_IMPLEMENTATION.md` - Examples showing version display

### 3. Build New Installer

```bash
# Using default version (v1.9.7)
./create-installer.sh

# Or specify a different version
NEBULA_VERSION=v1.10.0 ./create-installer.sh
```

The installer will:
1. Download the specified Nebula version from GitHub releases
2. Extract nebula and nebula-cert binaries
3. Include them in the PKG installer
4. Sign them if `APP_IDENTITY_HASH` is set
5. Install them to `/usr/local/bin/` when the PKG is run

## Verification After Installation

After installing a new PKG, verify the Nebula version:

```bash
# Check installed version
/usr/local/bin/nebula -version

# Should output:
# Version: 1.9.7
```

## Version Display in App

The ManagedNebula app automatically detects and displays the Nebula version:

1. **Menu Bar**: Shows "Nebula: v{version}" in the menu dropdown
2. **Preferences Window**: Shows "ManagedNebula v{app_version} • Nebula v{version}" at bottom

The version is retrieved by executing `nebula -version` and parsing the output.

## Why the Installer Includes Nebula

The PKG installer includes Nebula binaries to provide a complete, single-step installation experience:

✅ **Advantages:**
- Users don't need to install Nebula separately
- Guarantees compatible Nebula version
- Works on systems without Homebrew
- Simplifies deployment in enterprise environments

⚠️ **Note for Homebrew Users:**
If you already have Nebula installed via Homebrew, the PKG installer will overwrite `/usr/local/bin/nebula` with the bundled version. This is intentional to ensure version compatibility.

## Troubleshooting

### Nebula didn't upgrade after PKG install

The PKG installer should replace the Nebula binaries in `/usr/local/bin/`. If this didn't happen:

1. Check the installation log: `/var/log/install.log`
2. Verify PKG contents: `pkgutil --payload-files ManagedNebula-1.0.0.pkg`
3. Manually check: `ls -la /usr/local/bin/nebula*`
4. Reinstall with verbose output: `sudo installer -pkg ManagedNebula-1.0.0.pkg -target / -verbose`

### Version mismatch between app display and binary

If the app shows a different version than `nebula -version`:

1. The app checks: `/usr/local/bin/nebula -version`
2. Verify which binary is being used: `which nebula`
3. If Homebrew is installed, it might be using: `/opt/homebrew/bin/nebula` or `/usr/local/Cellar/nebula/...`
4. Check PATH order: `echo $PATH`

### Using Homebrew Nebula instead

To use Homebrew's Nebula instead of the bundled version:

```bash
# Unlink the bundled version
sudo rm /usr/local/bin/nebula /usr/local/bin/nebula-cert

# Install via Homebrew
brew install nebula

# Verify
which nebula  # Should show /opt/homebrew/bin/nebula
nebula -version
```

## Release Checklist

When releasing a new version with updated Nebula:

- [ ] Update `NEBULA_VERSION` default in `create-installer.sh`
- [ ] Update `NEBULA_VERSION` default in `install.sh`
- [ ] Update documentation files (DEPLOYMENT_READY.md, RELEASE.md)
- [ ] Build new PKG: `./create-installer.sh`
- [ ] Test installation on clean macOS system
- [ ] Verify Nebula version after install: `nebula -version`
- [ ] Verify app displays correct version in menu bar and preferences
- [ ] Update release notes with Nebula version changes
- [ ] Tag release: `git tag v1.0.1` (if bumping app version)
