import Cocoa

/// Controller for the menu bar application
class MenuBarController: NSObject, NSWindowDelegate {
    private var statusItem: NSStatusItem!
    private var menu: NSMenu!
    
    private let nebulaManager: NebulaManager
    private let keychainService: KeychainService
    private let pollingService: PollingService
    private var configuration: Configuration
    
    private var statusMenuItem: NSMenuItem!
    private var connectMenuItem: NSMenuItem!
    private var preferencesWindowController: PreferencesWindowController?
    private var isManuallyDisconnected = false
    
    override init() {
        self.configuration = Configuration.load()
        self.nebulaManager = NebulaManager()
        self.keychainService = KeychainService()
        self.pollingService = PollingService(
            nebulaManager: nebulaManager,
            keychainService: keychainService,
            configuration: configuration
        )
        
        super.init()
        
        setupMenuBar()
        setupPollingService()
        // First launch or missing config: show prefs (keep Dock icon visible)
        if Configuration.isFirstLaunch() || configuration.serverURL.isEmpty {
            NSApp.setActivationPolicy(.regular)
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.4) { [weak self] in
                self?.openPreferences(firstLaunch: true)
            }
        } else {
            // Already configured: hide dock, start polling if token present
            NSApp.setActivationPolicy(.accessory)
            // Respect manual disconnect persisted flag
            isManuallyDisconnected = configuration.isManuallyDisconnected ?? false
            pollingService.setManualDisconnect(isManuallyDisconnected)
            if let token = try? keychainService.loadToken(), !token.isEmpty, !isManuallyDisconnected {
                pollingService.startPolling()
            }
        }
    }
    
    private func setupMenuBar() {
        // Create status item
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        
        if let button = statusItem.button {
            // Attempt to load bundled Icon.icns explicitly (NSImage(named:) may not register .icns)
            var loadedIcon: NSImage? = nil
            if let iconPath = Bundle.main.path(forResource: "Icon", ofType: "icns") {
                loadedIcon = NSImage(contentsOfFile: iconPath)
                if loadedIcon == nil {
                    print("[MenuBarController] Failed to load Icon.icns at path: \(iconPath)")
                } else {
                    print("[MenuBarController] Loaded Icon.icns successfully")
                }
            }
            if loadedIcon == nil {
                // Fallback attempts
                loadedIcon = NSImage(named: "Icon") ?? NSImage(named: "AppIcon")
            }
            if let icon = loadedIcon {
                icon.size = NSSize(width: 18, height: 18)
                icon.isTemplate = false
                button.image = icon
            } else {
                print("[MenuBarController] Using fallback SF Symbol for status bar icon")
                button.image = NSImage(systemSymbolName: "network", accessibilityDescription: "Managed Nebula")
            }
            button.imagePosition = .imageLeading
        }
        
        // Create menu
        menu = NSMenu()
        
        // Status menu item
        statusMenuItem = NSMenuItem(title: "Status: Disconnected", action: nil, keyEquivalent: "")
        statusMenuItem.isEnabled = false
        menu.addItem(statusMenuItem)
        
        menu.addItem(NSMenuItem.separator())
        
        // Connect/Disconnect toggle
        connectMenuItem = NSMenuItem(title: "Connect", action: #selector(toggleConnection), keyEquivalent: "")
        connectMenuItem.target = self
        menu.addItem(connectMenuItem)
        
        menu.addItem(NSMenuItem.separator())
        
        // Check for updates
        let updateMenuItem = NSMenuItem(title: "Check for Updates", action: #selector(checkForUpdates), keyEquivalent: "")
        updateMenuItem.target = self
        menu.addItem(updateMenuItem)
        
        // View logs
        let logsMenuItem = NSMenuItem(title: "View Logs", action: #selector(viewLogs), keyEquivalent: "")
        logsMenuItem.target = self
        menu.addItem(logsMenuItem)
        
        menu.addItem(NSMenuItem.separator())
        
        // Preferences
        let preferencesMenuItem = NSMenuItem(title: "Preferences...", action: #selector(openPreferences), keyEquivalent: ",")
        preferencesMenuItem.target = self
        menu.addItem(preferencesMenuItem)
        
        menu.addItem(NSMenuItem.separator())
        
        // Quit
        let quitMenuItem = NSMenuItem(title: "Quit", action: #selector(quit), keyEquivalent: "q")
        quitMenuItem.target = self
        menu.addItem(quitMenuItem)
        
        statusItem.menu = menu
    }
    
    private func setupPollingService() {
        pollingService.onStatusChange = { [weak self] status in
            DispatchQueue.main.async {
                self?.updateStatus(status)
            }
        }
    }
    
    private func updateStatus(_ status: ConnectionStatus) {
        statusMenuItem.title = "Status: \(status.displayText)"
        
        // Update menu bar icon color
        if let button = statusItem.button {
            switch status {
            case .connected:
                button.appearsDisabled = false
                connectMenuItem.title = "Disconnect"
            case .disconnected:
                button.appearsDisabled = true
                connectMenuItem.title = "Connect"
            case .connecting:
                button.appearsDisabled = false
                connectMenuItem.title = "Connecting..."
            case .error:
                button.appearsDisabled = true
                connectMenuItem.title = "Connect"
            }
        }
    }
    
    @objc private func toggleConnection() {
        if nebulaManager.isRunning() {
            // Manual disconnect - stop everything
            isManuallyDisconnected = true
            configuration.isManuallyDisconnected = true
            configuration.save()
            pollingService.setManualDisconnect(true)
            nebulaManager.stopNebula()
            pollingService.stopPolling()
            updateStatus(.disconnected)
        } else {
            if configuration.serverURL.isEmpty {
                showAlert(title: "Configuration Required", message: "Please configure the server URL in Preferences.")
                return
            }
            // Manual connect - clear disconnect flag and start polling
            isManuallyDisconnected = false
            configuration.isManuallyDisconnected = false
            configuration.save()
            pollingService.setManualDisconnect(false)
            pollingService.startPolling()
        }
    }
    
    @objc private func checkForUpdates() {
        Task {
            await pollingService.checkForUpdates()
        }
    }
    
    @objc private func viewLogs() {
        // Prefer system Nebula log written by helper daemon
        let systemLogPath = URL(fileURLWithPath: "/var/log/nebula.log")
        if FileManager.default.fileExists(atPath: systemLogPath.path) {
            let dir = systemLogPath.deletingLastPathComponent()
            NSWorkspace.shared.selectFile(systemLogPath.path, inFileViewerRootedAtPath: dir.path)
            return
        }

        // Fallback to user-space log location if present
        let logPath = FileManager.NebulaFiles.logFile
        let logDir = logPath.deletingLastPathComponent()

        // Ensure log directory exists
        try? FileManager.default.createDirectory(at: logDir, withIntermediateDirectories: true)

        if FileManager.default.fileExists(atPath: logPath.path) {
            NSWorkspace.shared.selectFile(logPath.path, inFileViewerRootedAtPath: logDir.path)
        } else {
            // Fallback: just open the log directory
            NSWorkspace.shared.open(logDir)
        }
    }
    
    @objc private func openPreferences(firstLaunch: Bool = false) {
        // Reuse existing window if open
        if let existing = preferencesWindowController {
            existing.window?.makeKeyAndOrderFront(nil)
            NSApp.activate(ignoringOtherApps: true)
            return
        }
        // Reload configuration from persisted store before showing UI (ensures latest values)
        configuration = Configuration.load()

        let controller = PreferencesWindowController(
            configuration: configuration,
            keychainService: keychainService
        )
        controller.onSave = { [weak self] newConfig in
            print("[MenuBarController] Saving preferences...")
            self?.configuration = newConfig
            newConfig.save()
            self?.pollingService.updateConfiguration(newConfig)
            // Keep manual disconnect state in sync if present
            self?.isManuallyDisconnected = newConfig.isManuallyDisconnected ?? false
            self?.pollingService.setManualDisconnect(self?.isManuallyDisconnected ?? false)

            // Restart polling if server URL changed
            if !newConfig.serverURL.isEmpty {
                if !(self?.isManuallyDisconnected ?? false) {
                    self?.pollingService.startPolling()
                }
            }
            
            // Show success notification
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) {
                self?.showAlert(title: "Preferences Saved", message: "Your settings have been saved successfully.")
            }
            if !newConfig.serverURL.isEmpty, (try? self?.keychainService.loadToken())??.isEmpty == false {
                NSApp.setActivationPolicy(.accessory)
            }
            // Update status item immediately to reflect potential connection state change
            self?.updateStatus(.disconnected)
        }
        controller.window?.delegate = self
        preferencesWindowController = controller
        controller.showWindow(nil)
        NSApp.activate(ignoringOtherApps: true)
        if firstLaunch {
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.2) { [weak self] in
                self?.showAlert(title: "Welcome to ManagedNebula", message: "Enter your Server URL and Client Token to get connected.")
            }
        }
    }

    // NSWindowDelegate
    func windowWillClose(_ notification: Notification) {
        if let win = notification.object as? NSWindow, win == preferencesWindowController?.window {
            preferencesWindowController = nil
            // If still not configured keep Dock icon visible
            if configuration.serverURL.isEmpty {
                NSApp.setActivationPolicy(.regular)
            }
        }
    }
    
    @objc private func quit() {
        nebulaManager.stopNebula()
        pollingService.stopPolling()
        NSApplication.shared.terminate(self)
    }
    
    private func showAlert(title: String, message: String) {
        let alert = NSAlert()
        alert.messageText = title
        alert.informativeText = message
        alert.alertStyle = .warning
        alert.addButton(withTitle: "OK")
        alert.runModal()
    }
}
