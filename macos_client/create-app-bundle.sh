#!/bin/bash
# Script to create ManagedNebula.app bundle

set -e

APP_NAME="ManagedNebula"
# Use VERSION from environment if provided, otherwise default to 1.0.0
VERSION="${VERSION:-1.0.0}"
BUNDLE_ID="com.managednebula.client"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "=== Creating ${APP_NAME}.app Bundle ==="
echo ""

# Build release version
echo "Step 1: Building release binary..."
cd "$SCRIPT_DIR"
swift build -c release

if [ ! -f ".build/release/${APP_NAME}" ]; then
    echo "Error: Build failed, binary not found"
    exit 1
fi

echo "✓ Build complete"
echo ""

# Create bundle structure
echo "Step 2: Creating bundle structure..."
BUNDLE_DIR="${SCRIPT_DIR}/${APP_NAME}.app"
# Robustly remove any previous bundle, even if created as root
if [ -d "${BUNDLE_DIR}" ]; then
    if ! rm -rf "${BUNDLE_DIR}" 2>/dev/null; then
        chmod -R u+w "${BUNDLE_DIR}" 2>/dev/null || true
        if ! rm -rf "${BUNDLE_DIR}" 2>/dev/null; then
            echo "Permission denied removing existing app bundle; attempting sudo rm -rf..."
            sudo rm -rf "${BUNDLE_DIR}"
        fi
    fi
fi
mkdir -p "${BUNDLE_DIR}/Contents/MacOS"
mkdir -p "${BUNDLE_DIR}/Contents/Resources"

echo "✓ Bundle structure created"
echo ""

# Copy binary
echo "Step 3: Copying binary..."
cp ".build/release/${APP_NAME}" "${BUNDLE_DIR}/Contents/MacOS/"
chmod +x "${BUNDLE_DIR}/Contents/MacOS/${APP_NAME}"

echo "✓ Binary copied"
echo ""

# Create Info.plist
echo "Step 4: Creating Info.plist..."
cat > "${BUNDLE_DIR}/Contents/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDevelopmentRegion</key>
    <string>en</string>
    <key>CFBundleExecutable</key>
    <string>${APP_NAME}</string>
    <key>CFBundleIdentifier</key>
    <string>${BUNDLE_ID}</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>${APP_NAME}</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>${VERSION}</string>
    <key>CFBundleVersion</key>
    <string>1</string>
    <key>LSApplicationCategoryType</key>
    <string>public.app-category.utilities</string>
    <key>LSMinimumSystemVersion</key>
    <string>12.0</string>
    <!-- Show Dock icon initially so user sees the app on first launch -->
    <key>LSUIElement</key>
    <false/>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSHumanReadableCopyright</key>
    <string>Copyright © 2025 KumpeApps LLC. All rights reserved.</string>
    <key>NSPrincipalClass</key>
    <string>NSApplication</string>
    <!-- App Icon -->
    <key>CFBundleIconFile</key>
    <string>Icon</string>
</dict>
</plist>
EOF

echo "✓ Info.plist created"
echo ""

# Create PkgInfo
echo "Step 5: Creating PkgInfo..."
echo -n "APPL????" > "${BUNDLE_DIR}/Contents/PkgInfo"

echo "✓ PkgInfo created"
echo ""

# Copy icon if available (optional)
if [ -f "${SCRIPT_DIR}/Icon.icns" ]; then
    echo "Step 6: Copying icon..."
    cp "${SCRIPT_DIR}/Icon.icns" "${BUNDLE_DIR}/Contents/Resources/"
    echo "✓ Icon copied"
else
    echo "Step 6: Skipping icon (Icon.icns not found)"
fi
echo ""

# Set bundle bit
echo "Step 7: Setting bundle attributes..."
/usr/bin/SetFile -a B "${BUNDLE_DIR}" 2>/dev/null || echo "⚠ SetFile not found, bundle bit not set"

echo "✓ Bundle attributes set"
echo ""

# Verify bundle
echo "Step 8: Verifying bundle..."
if [ -d "${BUNDLE_DIR}" ] && [ -x "${BUNDLE_DIR}/Contents/MacOS/${APP_NAME}" ]; then
    echo "✓ Bundle verification passed"
else
    echo "✗ Bundle verification failed"
    exit 1
fi

echo ""
echo "=== Bundle Creation Complete ==="
echo ""
echo "Application bundle created at: ${BUNDLE_DIR}"
echo ""
echo "You can now:"
echo "  1. Test: open ${BUNDLE_DIR}"
echo "  2. Move: mv ${BUNDLE_DIR} /Applications/"
echo "  3. Create DMG: hdiutil create -volname '${APP_NAME}' -srcfolder ${BUNDLE_DIR} -ov -format UDZO ${APP_NAME}.dmg"
echo ""
echo "Note: For distribution, you should:"
echo "  - Add an icon (Icon.icns)"
echo "  - Code sign the bundle"
echo "  - Notarize with Apple"
echo ""
