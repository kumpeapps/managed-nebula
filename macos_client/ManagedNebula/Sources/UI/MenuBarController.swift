import Cocoa

/// Controller for the menu bar application
class MenuBarController: NSObject {
    private var statusItem: NSStatusItem!
    private var menu: NSMenu!
    
    private let nebulaManager: NebulaManager
    private let keychainService: KeychainService
    private let pollingService: PollingService
    private var configuration: Configuration
    
    private var statusMenuItem: NSMenuItem!
    private var connectMenuItem: NSMenuItem!
    
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
        
        // Start polling if configured
        if !configuration.serverURL.isEmpty {
            pollingService.startPolling()
        }
    }
    
    private func setupMenuBar() {
        // Create status item
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        
        if let button = statusItem.button {
            button.image = NSImage(systemSymbolName: "network", accessibilityDescription: "Managed Nebula")
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
            nebulaManager.stopNebula()
            pollingService.stopPolling()
            updateStatus(.disconnected)
        } else {
            if configuration.serverURL.isEmpty {
                showAlert(title: "Configuration Required", message: "Please configure the server URL in Preferences.")
                return
            }
            pollingService.startPolling()
        }
    }
    
    @objc private func checkForUpdates() {
        Task {
            await pollingService.checkForUpdates()
        }
    }
    
    @objc private func viewLogs() {
        let logPath = FileManager.NebulaFiles.logFile
        NSWorkspace.shared.selectFile(logPath.path, inFileViewerRootedAtPath: logPath.deletingLastPathComponent().path)
    }
    
    @objc private func openPreferences() {
        let preferencesWindow = PreferencesWindowController(
            configuration: configuration,
            keychainService: keychainService
        )
        preferencesWindow.onSave = { [weak self] newConfig in
            self?.configuration = newConfig
            newConfig.save()
            self?.pollingService.updateConfiguration(newConfig)
            
            // Restart polling if server URL changed
            if !newConfig.serverURL.isEmpty {
                self?.pollingService.startPolling()
            }
        }
        preferencesWindow.showWindow(nil)
        NSApp.activate(ignoringOtherApps: true)
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
