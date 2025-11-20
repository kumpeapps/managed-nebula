#!/bin/bash
# Create an uninstaller app bundle for ManagedNebula

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
UNINSTALLER_APP="${SCRIPT_DIR}/Uninstall ManagedNebula.app"

echo "Creating Uninstaller app bundle..."

# Remove existing
rm -rf "${UNINSTALLER_APP}"

# Create app bundle structure
mkdir -p "${UNINSTALLER_APP}/Contents/MacOS"
mkdir -p "${UNINSTALLER_APP}/Contents/Resources"

# Create Info.plist
cat > "${UNINSTALLER_APP}/Contents/Info.plist" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>uninstaller</string>
    <key>CFBundleIdentifier</key>
    <string>com.managednebula.uninstaller</string>
    <key>CFBundleName</key>
    <string>Uninstall ManagedNebula</string>
    <key>CFBundleDisplayName</key>
    <string>Uninstall ManagedNebula</string>
    <key>CFBundleVersion</key>
    <string>1.0.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleSignature</key>
    <string>????</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.15</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
EOF

# Create the uninstaller executable script
cat > "${UNINSTALLER_APP}/Contents/MacOS/uninstaller" << 'EOF'
#!/bin/bash

# Uninstaller script with GUI dialogs

# Function to show dialog
show_dialog() {
    osascript -e "display dialog \"$1\" buttons {\"$2\"} default button \"$2\" with icon caution"
}

show_question() {
    osascript -e "display dialog \"$1\" buttons {\"Cancel\", \"$2\"} default button \"$2\" with icon caution" 2>/dev/null
    return $?
}

# Check for admin privileges
if [ "$EUID" -ne 0 ]; then
    # Relaunch with admin privileges, preserving all arguments
    # Properly escape arguments for shell script execution
    ESCAPED_ARGS=""
    for arg in "$@"; do
        ESCAPED_ARGS="$ESCAPED_ARGS '$(echo "$arg" | sed "s/'/'\\\\''/g")'"
    done
    osascript -e "do shell script \"'$0'$ESCAPED_ARGS\" with administrator privileges"
    exit $?
fi

# Ask what to remove
RESPONSE=$(osascript -e 'display dialog "What would you like to remove?" buttons {"Cancel", "Uninstall Only", "Uninstall + Settings"} default button "Uninstall Only" with icon caution' 2>&1)

if [ $? -ne 0 ]; then
    exit 0  # User cancelled
fi

PURGE=false
if echo "$RESPONSE" | grep -q "Uninstall + Settings"; then
    PURGE=true
fi

# Find the uninstall script
UNINSTALL_SCRIPT=""
if [ -f "/usr/local/bin/managednebula-uninstall.sh" ]; then
    UNINSTALL_SCRIPT="/usr/local/bin/managednebula-uninstall.sh"
elif [ -f "$(dirname "$0")/../Resources/uninstall.sh" ]; then
    UNINSTALL_SCRIPT="$(dirname "$0")/../Resources/uninstall.sh"
fi

if [ -z "$UNINSTALL_SCRIPT" ]; then
    osascript -e 'display dialog "Uninstall script not found. Please run:\nsudo bash /usr/local/bin/managednebula-uninstall.sh" buttons {"OK"} default button "OK" with icon stop'
    exit 1
fi

# Run uninstall
if [ "$PURGE" = true ]; then
    bash "$UNINSTALL_SCRIPT" --purge > /tmp/managednebula-uninstall.log 2>&1
else
    bash "$UNINSTALL_SCRIPT" > /tmp/managednebula-uninstall.log 2>&1
fi

if [ $? -eq 0 ]; then
    if [ "$PURGE" = true ]; then
        osascript -e 'display dialog "ManagedNebula has been completely removed, including all settings and configuration." buttons {"OK"} default button "OK"'
    else
        osascript -e 'display dialog "ManagedNebula has been uninstalled. Your settings and configuration were preserved.\n\nTo remove settings, run:\nsudo bash /usr/local/bin/managednebula-uninstall.sh --purge" buttons {"OK"} default button "OK"'
    fi
else
    osascript -e 'display dialog "Uninstall encountered errors. Check /tmp/managednebula-uninstall.log for details." buttons {"OK"} default button "OK" with icon stop'
    exit 1
fi

exit 0
EOF

chmod +x "${UNINSTALLER_APP}/Contents/MacOS/uninstaller"

# Copy the uninstall script into Resources as backup
cp "${SCRIPT_DIR}/uninstall.sh" "${UNINSTALLER_APP}/Contents/Resources/"

echo "✓ Uninstaller app created: ${UNINSTALLER_APP}"
