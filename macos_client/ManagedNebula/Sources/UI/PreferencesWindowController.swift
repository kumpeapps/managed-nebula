import Cocoa

/// Window controller for application preferences
class PreferencesWindowController: NSWindowController, NSWindowDelegate {
    private var configuration: Configuration
    private let keychainService: KeychainService
    
    var onSave: ((Configuration) -> Void)?
    
    // UI Elements
    private let serverURLField = NSTextField()
    private let tokenField = NSSecureTextField()
    private let pollIntervalField = NSTextField()
    private let autoStartCheckbox = NSButton(checkboxWithTitle: "Auto-start Nebula", target: nil, action: nil)
    private let launchAtLoginCheckbox = NSButton(checkboxWithTitle: "Launch at login", target: nil, action: nil)
    
    init(configuration: Configuration, keychainService: KeychainService) {
        self.configuration = configuration
        self.keychainService = keychainService
        
        let window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 480, height: 320),
            styleMask: [.titled, .closable],
            backing: .buffered,
            defer: false
        )
        window.title = "Preferences"
        window.center()
        
        super.init(window: window)
        window.delegate = self
        
        setupUI()
        loadCurrentValues()
    }
    
    required init?(coder: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }
    
    private func setupUI() {
        guard let window = window else { return }
        
        let contentView = NSView(frame: window.contentView!.bounds)
        window.contentView = contentView
        
        // Server URL
        let serverURLLabel = NSTextField(labelWithString: "Server URL:")
        serverURLLabel.frame = NSRect(x: 20, y: 260, width: 120, height: 20)
        contentView.addSubview(serverURLLabel)
        
        serverURLField.frame = NSRect(x: 150, y: 258, width: 310, height: 22)
        serverURLField.placeholderString = "https://nebula.example.com"
        contentView.addSubview(serverURLField)
        
        // Client Token
        let tokenLabel = NSTextField(labelWithString: "Client Token:")
        tokenLabel.frame = NSRect(x: 20, y: 220, width: 120, height: 20)
        contentView.addSubview(tokenLabel)
        
        tokenField.frame = NSRect(x: 150, y: 218, width: 310, height: 22)
        tokenField.placeholderString = "Enter your client token"
        contentView.addSubview(tokenField)
        
        // Poll Interval
        let pollIntervalLabel = NSTextField(labelWithString: "Poll Interval (hours):")
        pollIntervalLabel.frame = NSRect(x: 20, y: 180, width: 150, height: 20)
        contentView.addSubview(pollIntervalLabel)
        
        pollIntervalField.frame = NSRect(x: 180, y: 178, width: 60, height: 22)
        pollIntervalField.placeholderString = "24"
        contentView.addSubview(pollIntervalField)
        
        // Auto-start checkbox
        autoStartCheckbox.frame = NSRect(x: 20, y: 140, width: 200, height: 20)
        autoStartCheckbox.state = configuration.isAutoStartEnabled ? .on : .off
        contentView.addSubview(autoStartCheckbox)
        
        // Launch at login checkbox
        launchAtLoginCheckbox.frame = NSRect(x: 20, y: 110, width: 200, height: 20)
        launchAtLoginCheckbox.state = configuration.launchAtLogin ? .on : .off
        contentView.addSubview(launchAtLoginCheckbox)
        
        // Buttons
        let saveButton = NSButton()
        saveButton.title = "Save"
        saveButton.frame = NSRect(x: 380, y: 20, width: 80, height: 32)
        saveButton.bezelStyle = .rounded
        saveButton.target = self
        saveButton.action = #selector(savePreferences)
        saveButton.keyEquivalent = "\r"
        contentView.addSubview(saveButton)
        
        let cancelButton = NSButton()
        cancelButton.title = "Cancel"
        cancelButton.frame = NSRect(x: 290, y: 20, width: 80, height: 32)
        cancelButton.bezelStyle = .rounded
        cancelButton.target = self
        cancelButton.action = #selector(cancelPreferences)
        cancelButton.keyEquivalent = "\u{1b}"
        contentView.addSubview(cancelButton)
    }
    
    private func loadCurrentValues() {
        serverURLField.stringValue = configuration.serverURL
        pollIntervalField.integerValue = configuration.pollIntervalHours
        autoStartCheckbox.state = configuration.isAutoStartEnabled ? .on : .off
        launchAtLoginCheckbox.state = configuration.launchAtLogin ? .on : .off
        
        // Load token from keychain
        if let token = try? keychainService.loadToken() {
            tokenField.stringValue = token
        }
    }
    
    @objc private func savePreferences() {
        // Validate inputs
        guard !serverURLField.stringValue.isEmpty else {
            showAlert(title: "Validation Error", message: "Server URL is required")
            return
        }
        
        guard pollIntervalField.integerValue > 0 else {
            showAlert(title: "Validation Error", message: "Poll interval must be greater than 0")
            return
        }
        
        // Update configuration
        configuration.serverURL = serverURLField.stringValue
        configuration.pollIntervalHours = pollIntervalField.integerValue
        configuration.isAutoStartEnabled = autoStartCheckbox.state == .on
        configuration.launchAtLogin = launchAtLoginCheckbox.state == .on
        
        // Save token to keychain
        if !tokenField.stringValue.isEmpty {
            do {
                try keychainService.saveToken(tokenField.stringValue)
            } catch {
                showAlert(title: "Keychain Error", message: "Failed to save token: \(error.localizedDescription)")
                return
            }
        }
        
        // Call save callback
        onSave?(configuration)
        
        // Close window
        close()
    }
    
    @objc private func cancelPreferences() {
        close()
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
