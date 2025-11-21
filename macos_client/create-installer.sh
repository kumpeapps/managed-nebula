#!/bin/bash
# Script to create a complete installer package (PKG and DMG) for ManagedNebula

set -e

# Add error handler to show which command failed
trap 'echo "Error on line $LINENO: Command exited with status $?"' ERR

APP_NAME="ManagedNebula"
# Use VERSION from environment if provided, otherwise default to 1.0.0
VERSION="${VERSION:-1.0.0}"
# PKG_VERSION is for pkgbuild (numeric only), strip any suffix after first dash
PKG_VERSION="${VERSION%%-*}"
BUNDLE_ID="com.managednebula.client"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DIST_DIR="${SCRIPT_DIR}/dist"
NEBULA_VERSION="v1.8.2"

echo "=== ManagedNebula Installer Creator ==="
echo "VERSION: ${VERSION}"
echo "PKG_VERSION: ${PKG_VERSION}"
echo ""

# Clean previous builds
echo "Step 1: Cleaning previous builds..."
rm -rf "${DIST_DIR}"
mkdir -p "${DIST_DIR}"
# Also clean any previous local app bundle which might be root-owned
if [ -d "${SCRIPT_DIR}/${APP_NAME}.app" ]; then
    if ! rm -rf "${SCRIPT_DIR}/${APP_NAME}.app" 2>/dev/null; then
        chmod -R u+w "${SCRIPT_DIR}/${APP_NAME}.app" 2>/dev/null || true
        if ! rm -rf "${SCRIPT_DIR}/${APP_NAME}.app" 2>/dev/null; then
            echo "Permission denied cleaning ${APP_NAME}.app; attempting sudo rm -rf..."
            sudo rm -rf "${SCRIPT_DIR}/${APP_NAME}.app"
        fi
    fi
fi
echo "✓ Clean complete"
echo ""

# Create app bundle
echo "Step 2: Creating app bundle..."
if [ ! -f "${SCRIPT_DIR}/create-app-bundle.sh" ]; then
    echo "Error: create-app-bundle.sh not found"
    exit 1
fi

VERSION="${VERSION}" bash "${SCRIPT_DIR}/create-app-bundle.sh"

if [ ! -d "${SCRIPT_DIR}/${APP_NAME}.app" ]; then
    echo "Error: App bundle creation failed"
    exit 1
fi

echo "✓ App bundle created"
echo ""

# Sign app bundle (if identity provided) before packaging
if [ -n "${APP_IDENTITY_HASH}" ]; then
    echo "Signing app bundle with identity ${APP_IDENTITY_HASH}..."
    xattr -cr "${SCRIPT_DIR}/${APP_NAME}.app" 2>/dev/null || true
    codesign --deep --force --verify --verbose --sign "${APP_IDENTITY_HASH}" --options runtime --timestamp "${SCRIPT_DIR}/${APP_NAME}.app"
    codesign --verify --deep --strict --verbose=2 "${SCRIPT_DIR}/${APP_NAME}.app"
    echo "✓ App bundle signed"
else
    echo "Skipping app bundle code signing (APP_IDENTITY_HASH not set)"
fi

# Download Nebula binaries
echo "Step 3: Downloading Nebula binaries..."
NEBULA_URL="https://github.com/slackhq/nebula/releases/download/${NEBULA_VERSION}/nebula-darwin.zip"
NEBULA_TMP="${DIST_DIR}/nebula-tmp"
mkdir -p "${NEBULA_TMP}"

curl -L -o "${NEBULA_TMP}/nebula.zip" "$NEBULA_URL"
cd "${NEBULA_TMP}"
unzip -q nebula.zip
cd "${SCRIPT_DIR}"

if [ ! -f "${NEBULA_TMP}/nebula" ] || [ ! -f "${NEBULA_TMP}/nebula-cert" ]; then
    echo "Error: Failed to extract Nebula binaries"
    exit 1
fi

echo "✓ Nebula binaries downloaded"
echo ""

# Create payload directory for PKG
echo "Step 4: Creating PKG payload..."
PKG_ROOT="${DIST_DIR}/pkg-root"
mkdir -p "${PKG_ROOT}/Applications"
mkdir -p "${PKG_ROOT}/usr/local/bin"
mkdir -p "${PKG_ROOT}/Library/LaunchDaemons"

# Copy app bundle
if [ ! -d "${SCRIPT_DIR}/${APP_NAME}.app" ]; then
    echo "Error: ${APP_NAME}.app not found!"
    exit 1
fi

cp -R "${SCRIPT_DIR}/${APP_NAME}.app" "${PKG_ROOT}/Applications/"

# Verify copy succeeded
if [ ! -d "${PKG_ROOT}/Applications/${APP_NAME}.app" ]; then
    echo "Error: Failed to copy app bundle to PKG_ROOT"
    exit 1
fi

echo "✓ App bundle copied: $(du -sh ${PKG_ROOT}/Applications/${APP_NAME}.app | cut -f1)"

# Copy Nebula binaries
cp "${NEBULA_TMP}/nebula" "${PKG_ROOT}/usr/local/bin/"
cp "${NEBULA_TMP}/nebula-cert" "${PKG_ROOT}/usr/local/bin/"
chmod +x "${PKG_ROOT}/usr/local/bin/nebula"
chmod +x "${PKG_ROOT}/usr/local/bin/nebula-cert"

# Optionally sign Nebula binaries if an Application identity is provided
if [ -n "${APP_IDENTITY_HASH}" ]; then
    echo "Signing Nebula binaries with identity ${APP_IDENTITY_HASH}..."
    codesign --force --verify --verbose --sign "${APP_IDENTITY_HASH}" --options runtime --timestamp "${PKG_ROOT}/usr/local/bin/nebula"
    codesign --force --verify --verbose --sign "${APP_IDENTITY_HASH}" --options runtime --timestamp "${PKG_ROOT}/usr/local/bin/nebula-cert"
    # Verify signatures
    codesign --verify --strict --verbose=2 "${PKG_ROOT}/usr/local/bin/nebula"
    codesign --verify --strict --verbose=2 "${PKG_ROOT}/usr/local/bin/nebula-cert"
    echo "✓ Nebula binaries signed"
else
    echo "Skipping code signing of Nebula binaries (APP_IDENTITY_HASH not set)"
fi

# Copy helper script
cp "${SCRIPT_DIR}/nebula-helper.sh" "${PKG_ROOT}/usr/local/bin/"
chmod +x "${PKG_ROOT}/usr/local/bin/nebula-helper.sh"

echo "✓ PKG payload created"
echo ""

# Create LaunchDaemon plists
echo "Step 5: Creating LaunchDaemons..."
cat > "${PKG_ROOT}/Library/LaunchDaemons/com.managednebula.helper.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.managednebula.helper</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/nebula-helper.sh</string>
    </array>
    
    <key>RunAtLoad</key>
    <true/>
    
    <key>KeepAlive</key>
    <true/>
    
    <key>StandardOutPath</key>
    <string>/var/log/nebula-helper.log</string>
    
    <key>StandardErrorPath</key>
    <string>/var/log/nebula-helper.error.log</string>
</dict>
</plist>
EOF

cat > "${PKG_ROOT}/Library/LaunchDaemons/com.managednebula.nebula.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.managednebula.nebula</string>

    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/nebula</string>
        <string>-config</string>
        <string>/etc/nebula/config.yml</string>
    </array>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>StandardOutPath</key>
    <string>/var/log/nebula.log</string>

    <key>StandardErrorPath</key>
    <string>/var/log/nebula.log</string>
</dict>
</plist>
EOF

echo "✓ LaunchDaemons created"
echo ""

# Create scripts directory
echo "Step 6: Creating installer scripts..."
PKG_SCRIPTS="${DIST_DIR}/pkg-scripts"
mkdir -p "${PKG_SCRIPTS}"

# Add log rotation helper script to payload
cat > "${PKG_ROOT}/usr/local/bin/nebula-logrotate.sh" << 'LREOF'
#!/bin/bash
set -e
/usr/sbin/newsyslog || true
# Restart Nebula to ensure launchd reopens log files
/bin/launchctl kickstart -k system/com.managednebula.nebula || true
LREOF
chmod +x "${PKG_ROOT}/usr/local/bin/nebula-logrotate.sh"

# Install uninstall helper into payload for easy removal
cp "${SCRIPT_DIR}/uninstall.sh" "${PKG_ROOT}/usr/local/bin/managednebula-uninstall.sh"
chmod +x "${PKG_ROOT}/usr/local/bin/managednebula-uninstall.sh"
ln -sf "/usr/local/bin/managednebula-uninstall.sh" "${PKG_ROOT}/usr/local/bin/managednebula-uninstall"

# Add log rotation LaunchDaemon
cat > "${PKG_ROOT}/Library/LaunchDaemons/com.managednebula.logrotate.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.managednebula.logrotate</string>

    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/nebula-logrotate.sh</string>
    </array>

    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>3</integer>
        <key>Minute</key>
        <integer>5</integer>
    </dict>

    <key>RunAtLoad</key>
    <true/>

    <key>StandardOutPath</key>
    <string>/var/log/nebula-helper.log</string>

    <key>StandardErrorPath</key>
    <string>/var/log/nebula-helper.error.log</string>
</dict>
</plist>
EOF

# Postinstall script
cat > "${PKG_SCRIPTS}/postinstall" << 'POSTEOF'
#!/bin/bash
# Postinstall script

echo "Configuring ManagedNebula..."

# Verify app was copied
if [ ! -d "/Applications/ManagedNebula.app" ]; then
    echo "ERROR: ManagedNebula.app not found in /Applications/"
    echo "This may be a Gatekeeper issue. Checking alternate locations..."
    
    # Check if it's in the package receipt location
    if [ -d "/private/var/folders" ]; then
        APP_LOCATION=$(find /private/var/folders -name "ManagedNebula.app" -type d 2>/dev/null | head -1)
        if [ -n "$APP_LOCATION" ]; then
            echo "Found app at: $APP_LOCATION"
            echo "Copying to /Applications/..."
            cp -R "$APP_LOCATION" /Applications/
        fi
    fi
fi

# Verify app is now present
if [ -d "/Applications/ManagedNebula.app" ]; then
    echo "✓ ManagedNebula.app installed to /Applications/"
    
    # Remove quarantine attribute
    xattr -dr com.apple.quarantine /Applications/ManagedNebula.app 2>/dev/null || true
    
    # Fix permissions
    chmod -R 755 /Applications/ManagedNebula.app
    chown -R root:wheel /Applications/ManagedNebula.app
else
    echo "WARNING: Could not verify ManagedNebula.app installation"
    echo "You may need to manually copy ManagedNebula.app to /Applications/"
fi

# Set correct permissions on Nebula binaries
chmod +x /usr/local/bin/nebula
chmod +x /usr/local/bin/nebula-cert
chmod +x /usr/local/bin/nebula-helper.sh

# Set correct permissions on LaunchDaemons
chmod 644 /Library/LaunchDaemons/com.managednebula.helper.plist
chown root:wheel /Library/LaunchDaemons/com.managednebula.helper.plist
chmod 644 /Library/LaunchDaemons/com.managednebula.nebula.plist
chown root:wheel /Library/LaunchDaemons/com.managednebula.nebula.plist
chmod 644 /Library/LaunchDaemons/com.managednebula.logrotate.plist
chown root:wheel /Library/LaunchDaemons/com.managednebula.logrotate.plist

# Create configuration directory
mkdir -p /etc/nebula
chmod 755 /etc/nebula

# Create log directory
mkdir -p /var/log
touch /var/log/nebula-helper.log
touch /var/log/nebula-helper.error.log
touch /var/log/nebula.log

# Configure newsyslog rotation (daily at midnight, keep 7, compress)
mkdir -p /etc/newsyslog.d
cat > /etc/newsyslog.d/nebula.conf << 'NSLEOF'
/var/log/nebula.log	root:wheel	644	7	*	$D0	Z
NSLEOF

# Create IPC control file
touch /tmp/nebula-control
chmod 666 /tmp/nebula-control

# Load helper daemon (nebula service will be loaded on demand via helper)
launchctl load /Library/LaunchDaemons/com.managednebula.helper.plist

# Load log rotation daemon
launchctl load /Library/LaunchDaemons/com.managednebula.logrotate.plist
POSTEOF

chmod +x "${PKG_SCRIPTS}/postinstall"

# Preinstall script
cat > "${PKG_SCRIPTS}/preinstall" << 'PREEOF'
#!/bin/bash
# Pre-installation script
# Note: PKG installers run non-interactively, so we just upgrade in-place
# Users should run the uninstaller app first if they want a clean install

echo "Pre-installation: Stopping existing services..."

# Check if ManagedNebula is already installed
if [ -d "/Applications/ManagedNebula.app" ] || \
   [ -f "/Library/LaunchDaemons/com.managednebula.helper.plist" ]; then
    echo "Existing installation detected. Performing upgrade (preserves settings)."
    echo "To perform a clean install, run 'Uninstall Managed Nebula.app' first."
fi

# Stop existing helper daemon if running
launchctl unload /Library/LaunchDaemons/com.managednebula.helper.plist 2>/dev/null || true

# Stop existing nebula daemon if running and unload it
launchctl unload /Library/LaunchDaemons/com.managednebula.nebula.plist 2>/dev/null || true

# Stop existing logrotate daemon
launchctl unload /Library/LaunchDaemons/com.managednebula.logrotate.plist 2>/dev/null || true

# Stop any stray processes
pkill -f "nebula -config" 2>/dev/null || true
pkill -f "nebula-helper" 2>/dev/null || true

exit 0
PREEOF

chmod +x "${PKG_SCRIPTS}/preinstall"

echo "✓ Installer scripts created"
echo ""

# Build PKG
echo "Step 7: Building PKG installer..."
PKG_FILE="${DIST_DIR}/${APP_NAME}-macos-${VERSION}.pkg"

pkgbuild \
    --root "${PKG_ROOT}" \
    --scripts "${PKG_SCRIPTS}" \
    --identifier "${BUNDLE_ID}" \
    --version "${PKG_VERSION}" \
    --install-location "/" \
    "${PKG_FILE}"

if [ ! -f "${PKG_FILE}" ]; then
    echo "Error: PKG creation failed"
    exit 1
fi

echo "✓ PKG created: ${PKG_FILE}"
echo ""

# Create DMG
echo "Step 8: Creating DMG installer..."
DMG_DIR="${DIST_DIR}/dmg-contents"
mkdir -p "${DMG_DIR}"

# Copy PKG installer
cp "${PKG_FILE}" "${DMG_DIR}/"

# Copy uninstaller app if it exists
if [ -d "${SCRIPT_DIR}/Uninstall ManagedNebula.app" ]; then
    cp -R "${SCRIPT_DIR}/Uninstall ManagedNebula.app" "${DMG_DIR}/"
    echo "✓ Uninstaller app included in DMG"
else
    echo "⚠ Uninstaller app not found, skipping..."
fi

# Copy app bundle (for manual installation option)
cp -R "${SCRIPT_DIR}/${APP_NAME}.app" "${DMG_DIR}/"

# Create symlink to Applications
ln -s /Applications "${DMG_DIR}/Applications"

# Create README
cat > "${DMG_DIR}/README.txt" << 'READMEEOF'
ManagedNebula Installation
==========================

RECOMMENDED: Complete Installation (Using PKG)
----------------------------------------------
1. Double-click the ManagedNebula-[VERSION].pkg file to install
2. Follow the installer prompts
3. Open ManagedNebula from Applications
4. Enter your server URL and client token

The PKG installer includes:
- ManagedNebula app
- Nebula binaries (nebula, nebula-cert)
- System LaunchDaemons for background operation
- Uninstall script

UPGRADING: Uninstall First
--------------------------
If you have a previous version installed:
1. Double-click "Uninstall Managed Nebula.app"
2. Choose "Uninstall Only" to keep your settings, or
   "Uninstall + Settings" for a clean slate
3. Then run the PKG installer

ALTERNATIVE: Manual Installation
---------------------------------
Advanced users can drag ManagedNebula.app to Applications, but
you'll need to install Nebula binaries separately:
  brew install nebula

Uninstalling
------------
Use the included "Uninstall Managed Nebula.app" or run in Terminal:

    sudo managednebula-uninstall

To remove all settings and keychain data:

    sudo managednebula-uninstall --purge

Troubleshooting
---------------
- Check logs: /var/log/nebula.log
- Check status: launchctl list | grep managednebula
- Support: https://github.com/kumpeapps/managed-nebula

READMEEOF

DMG_FILE="${DIST_DIR}/${APP_NAME}-macos-${VERSION}.dmg"

hdiutil create \
    -volname "${APP_NAME}" \
    -srcfolder "${DMG_DIR}" \
    -ov \
    -format UDZO \
    "${DMG_FILE}"

if [ ! -f "${DMG_FILE}" ]; then
    echo "Error: DMG creation failed"
    exit 1
fi

echo "✓ DMG created: ${DMG_FILE}"
echo ""

# Cleanup
echo "Step 9: Cleaning up temporary files..."
rm -rf "${PKG_ROOT}"
rm -rf "${PKG_SCRIPTS}"
rm -rf "${NEBULA_TMP}"
rm -rf "${DMG_DIR}"
echo "✓ Cleanup complete"
echo ""

# Summary
echo "=== Build Complete ==="
echo ""
echo "Installer packages created in: ${DIST_DIR}/"
echo ""
echo "Files:"
echo "  - ${APP_NAME}-${VERSION}.dmg (Contains PKG installer, uninstaller app, and manual app)"
echo "  - ${APP_NAME}-${VERSION}.pkg (Standalone PKG installer with Nebula binaries)"
echo ""
echo "DMG Contents:"
echo "  - ${APP_NAME}-${VERSION}.pkg (Main installer)"
echo "  - Uninstall Managed Nebula.app (GUI uninstaller)"
echo "  - ${APP_NAME}.app (For manual installation)"
echo "  - README.txt (Installation instructions)"
echo ""
echo "Recommended distribution: Use the DMG file"
echo ""
echo "Next steps for distribution:"
echo "  1. Code sign PKG: codesign --deep --force --verify --verbose --sign 'Developer ID' ${PKG_FILE}"
echo "  2. Code sign uninstaller: codesign --deep --force --sign 'Developer ID' 'Uninstall Managed Nebula.app'"
echo "  3. Notarize PKG: xcrun notarytool submit ${PKG_FILE} --wait"
echo "  4. Staple PKG: xcrun stapler staple ${PKG_FILE}"
echo "  5. Distribute: ${DMG_FILE}"
echo ""
