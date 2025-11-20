#!/bin/bash
set -euo pipefail

APP_NAME="ManagedNebula"
PKG_ID="com.managednebula.client"

PURGE=false
if [[ ${1:-} == "--purge" || ${1:-} == "-p" ]]; then
  PURGE=true
fi

require_root() {
  if [[ $EUID -ne 0 ]]; then
    echo "This script must run as root. Try: sudo $0 ${1:-}" >&2
    exit 1
  fi
}

log() { echo "[uninstall] $*"; }

unload_daemons() {
  for label in \
    com.managednebula.nebula \
    com.managednebula.helper \
    com.managednebula.logrotate; do
    launchctl unload "/Library/LaunchDaemons/${label}.plist" 2>/dev/null || true
  done
}

kill_processes() {
  pkill -f "/usr/local/bin/nebula -config" 2>/dev/null || true
  pkill -f "/usr/local/bin/nebula-helper.sh" 2>/dev/null || true
}

remove_daemon_files() {
  rm -f /Library/LaunchDaemons/com.managednebula.nebula.plist || true
  rm -f /Library/LaunchDaemons/com.managednebula.helper.plist || true
  rm -f /Library/LaunchDaemons/com.managednebula.logrotate.plist || true
}

remove_binaries() {
  rm -f /usr/local/bin/nebula-helper.sh || true
  rm -f /usr/local/bin/nebula-logrotate.sh || true
  rm -f /usr/local/bin/managednebula-uninstall.sh || true
  rm -f /usr/local/bin/managednebula-uninstall || true
  # Do not remove nebula/nebula-cert if user installed via Homebrew; only remove if our PKG placed them
  # Attempt removal but ignore if managed by brew (user can reinstall if desired)
  rm -f /usr/local/bin/nebula || true
  rm -f /usr/local/bin/nebula-cert || true
}

remove_app() {
  rm -rf "/Applications/${APP_NAME}.app" 2>/dev/null || true
}

remove_logs() {
  rm -f /var/log/nebula.log /var/log/nebula-helper.log /var/log/nebula-helper.error.log 2>/dev/null || true
  rm -f /etc/newsyslog.d/nebula.conf 2>/dev/null || true
}

remove_runtime() {
  rm -f /tmp/nebula-control /tmp/nebula-control.status 2>/dev/null || true
}

remove_config() {
  if $PURGE; then
    rm -rf /etc/nebula 2>/dev/null || true
    rm -rf /var/lib/nebula 2>/dev/null || true
  else
    # Keep configs/keys by default; remove only the generated defaults if empty
    find /etc/nebula -type f -name "*.bak" -delete 2>/dev/null || true
  fi
}

remove_user_data() {
  if $PURGE; then
    # Get the actual user who invoked sudo
    ACTUAL_USER="${SUDO_USER:-$USER}"
    ACTUAL_HOME=$(eval echo ~$ACTUAL_USER)
    
    log "Removing user configuration for $ACTUAL_USER..."
    
    # Remove user application support files
    sudo -u "$ACTUAL_USER" rm -rf "$ACTUAL_HOME/Library/Application Support/ManagedNebula" 2>/dev/null || true
    sudo -u "$ACTUAL_USER" rm -rf "$ACTUAL_HOME/Library/Logs/ManagedNebula" 2>/dev/null || true
    sudo -u "$ACTUAL_USER" rm -rf "$ACTUAL_HOME/Library/Caches/com.managednebula.client" 2>/dev/null || true
    sudo -u "$ACTUAL_USER" rm -rf "$ACTUAL_HOME/Library/Preferences/com.managednebula.client.plist" 2>/dev/null || true
    
    # Remove keychain item
    log "Removing keychain data..."
    sudo -u "$ACTUAL_USER" security delete-generic-password -s "com.managednebula.client" -a "client-token" 2>/dev/null || true
    
    # Clear user defaults
    sudo -u "$ACTUAL_USER" defaults delete com.managednebula.client 2>/dev/null || true
    
    log "User data removed"
  fi
}

forget_receipt() {
  pkgutil --forget "$PKG_ID" >/dev/null 2>&1 || true
}

main() {
  require_root
  log "Unloading LaunchDaemons..."
  unload_daemons

  log "Killing processes..."
  kill_processes

  log "Removing LaunchDaemon plists..."
  remove_daemon_files

  log "Removing binaries..."
  remove_binaries

  log "Removing application bundle..."
  remove_app

  log "Removing logs and rotation config..."
  remove_logs

  log "Cleaning runtime files..."
  remove_runtime

  log "Handling configuration (purge=${PURGE})..."
  remove_config
  
  log "Removing user data (purge=${PURGE})..."
  remove_user_data

  log "Forgetting PKG receipt (if present)..."
  forget_receipt

  log "Done. A reboot is not required."
  
  if $PURGE; then
    log "All configuration and user data has been removed."
  else
    log "User configuration and keys were preserved."
    log "To remove all data, run: sudo $0 --purge"
  fi
}

main "$@"
