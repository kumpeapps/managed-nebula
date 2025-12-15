#!/bin/bash
# Helper script to manage Nebula daemon with root privileges
# This runs as a LaunchDaemon (root) and listens for commands via file-based IPC

CONTROL_FILE="/tmp/nebula-control"
NEBULA_BIN="/usr/local/bin/nebula"
CONFIG_FILE="/etc/nebula/config.yml"
LOG_FILE="/var/log/nebula.log"
STAGING_DIR="/tmp/managed-nebula"
NEBULA_LABEL="com.managednebula.nebula"
NEBULA_PLIST="/Library/LaunchDaemons/${NEBULA_LABEL}.plist"
LOG_LEVEL_FILE="/etc/nebula/log-level"

install_files() {
    mkdir -p /etc/nebula
    mkdir -p /var/lib/nebula
    if [ -f "$STAGING_DIR/config.yml" ]; then
        cp -f "$STAGING_DIR/config.yml" "$CONFIG_FILE"
        chmod 644 "$CONFIG_FILE"
    fi
    if [ -f "$STAGING_DIR/host.crt" ]; then
        cp -f "$STAGING_DIR/host.crt" /etc/nebula/host.crt
        chmod 644 /etc/nebula/host.crt
    fi
    if [ -f "$STAGING_DIR/ca.crt" ]; then
        cp -f "$STAGING_DIR/ca.crt" /etc/nebula/ca.crt
        chmod 644 /etc/nebula/ca.crt
    fi
    if [ -f "$STAGING_DIR/host.key" ]; then
        cp -f "$STAGING_DIR/host.key" /var/lib/nebula/host.key
        chmod 600 /var/lib/nebula/host.key
    fi
    if [ -f "$STAGING_DIR/log-level" ]; then
        cp -f "$STAGING_DIR/log-level" "$LOG_LEVEL_FILE"
        chmod 644 "$LOG_LEVEL_FILE"
    fi
    chown -R root:wheel /etc/nebula /var/lib/nebula 2>/dev/null || true
}
write_nebula_plist() {
    cat > "$NEBULA_PLIST" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${NEBULA_LABEL}</string>

    <key>ProgramArguments</key>
    <array>
        <string>${NEBULA_BIN}</string>
        <string>-config</string>
        <string>${CONFIG_FILE}</string>
    </array>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>StandardOutPath</key>
    <string>${LOG_FILE}</string>

    <key>StandardErrorPath</key>
    <string>${LOG_FILE}</string>
</dict>
</plist>
EOF
    chmod 644 "$NEBULA_PLIST"
    chown root:wheel "$NEBULA_PLIST" 2>/dev/null || true
}

# Ensure control file exists
touch "$CONTROL_FILE"
chmod 666 "$CONTROL_FILE"

start_nebula() {
    # Install latest staged files (does not auto-restart)
    install_files

    if [ ! -f "$CONFIG_FILE" ]; then
        echo "Config file not found: $CONFIG_FILE"
        return 1
    fi

    # Validate config before attempting to start
    "$NEBULA_BIN" -config "$CONFIG_FILE" -test >> "$LOG_FILE" 2>&1 || {
        echo "Config validation failed; see $LOG_FILE" >&2
        return 1
    }

    # Ensure plist exists and reflects desired settings
    write_nebula_plist

    # Load (starts due to RunAtLoad) and kickstart to ensure it's running
    launchctl load -w "$NEBULA_PLIST" 2>/dev/null || true
    launchctl kickstart -k system/"$NEBULA_LABEL" 2>/dev/null || true

    # Report status
    if launchctl print system/"$NEBULA_LABEL" >/dev/null 2>&1; then
        echo "Nebula service loaded"
    else
        echo "Failed to load Nebula service; see $LOG_FILE for details" >&2
        return 1
    fi
}

# Function to stop Nebula
stop_nebula() {
    # Unload to stop and prevent KeepAlive from restarting
    if [ -f "$NEBULA_PLIST" ]; then
        launchctl unload -w "$NEBULA_PLIST" 2>/dev/null || true
    fi
    echo "Nebula stopped"
}

# Function to check status
check_status() {
    if launchctl print system/"$NEBULA_LABEL" >/dev/null 2>&1; then
        echo "running"
    else
        echo "stopped"
    fi
}

# Main loop - watch for commands
echo "Nebula helper daemon started"

while true; do
    if [ -f "$CONTROL_FILE" ]; then
        COMMAND=$(cat "$CONTROL_FILE")
        
        if [ -n "$COMMAND" ]; then
            case "$COMMAND" in
                start)
                    start_nebula
                    > "$CONTROL_FILE"  # Clear command
                    ;;
                stop)
                    stop_nebula
                    > "$CONTROL_FILE"  # Clear command
                    ;;
                restart)
                    stop_nebula
                    sleep 1
                    start_nebula
                    > "$CONTROL_FILE"  # Clear command
                    ;;
                install)
                    install_files
                    > "$CONTROL_FILE"  # Clear command
                    ;;
                upgrade)
                    # Install new Nebula binaries from staging directory
                    UPGRADE_STAGING="/tmp/managed-nebula-upgrade"
                    if [ -f "$UPGRADE_STAGING/nebula" ] && [ -f "$UPGRADE_STAGING/nebula-cert" ]; then
                        stop_nebula
                        sleep 1
                        cp -f "$UPGRADE_STAGING/nebula" /usr/local/bin/nebula
                        cp -f "$UPGRADE_STAGING/nebula-cert" /usr/local/bin/nebula-cert
                        chmod 755 /usr/local/bin/nebula /usr/local/bin/nebula-cert
                        rm -rf "$UPGRADE_STAGING"
                        echo "Nebula binaries upgraded successfully"
                    else
                        echo "Upgrade staging files not found"
                    fi
                    > "$CONTROL_FILE"  # Clear command
                    ;;
                status)
                    check_status > "${CONTROL_FILE}.status"
                    > "$CONTROL_FILE"  # Clear command
                    ;;
            esac
        fi
    fi
    
    sleep 1
done
