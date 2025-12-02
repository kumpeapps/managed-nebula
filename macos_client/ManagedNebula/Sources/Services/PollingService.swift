import Foundation

/// Service that polls the server for configuration updates
class PollingService {
    private var timer: Timer?
    private let nebulaManager: NebulaManager
    private let keychainService: KeychainService
    private var configuration: Configuration
    private var isManuallyDisconnected: Bool = false
    
    var onStatusChange: ((ConnectionStatus) -> Void)?
    
    init(nebulaManager: NebulaManager, keychainService: KeychainService, configuration: Configuration) {
        self.nebulaManager = nebulaManager
        self.keychainService = keychainService
        self.configuration = configuration
        self.isManuallyDisconnected = configuration.isManuallyDisconnected ?? false
    }
    
    /// Get client version from application bundle
    private func getClientVersion() -> String {
        // Check for environment override (for testing)
        if let override = ProcessInfo.processInfo.environment["CLIENT_VERSION_OVERRIDE"] {
            return override
        }
        
        // Try to get version from app bundle Info.plist (when running as .app)
        if let version = Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String {
            return version
        }
        
        // Fall back to reading from VERSION file next to executable
        if let executablePath = Bundle.main.executablePath {
            let executableURL = URL(fileURLWithPath: executablePath)
            let versionURL = executableURL.deletingLastPathComponent().appendingPathComponent("VERSION")
            if let versionString = try? String(contentsOf: versionURL, encoding: .utf8) {
                return versionString.trimmingCharacters(in: .whitespacesAndNewlines)
            }
        }
        
        return "unknown"
    }
    
    /// Start polling for configuration updates
    func startPolling() {
        // VERSION MARKER: If you see this, you're running the NEW Dec 1 19:58 build
        print("🔴🔴🔴 BUILD MARKER: Dec 1 19:58 - HOME EXPANSION CODE PRESENT 🔴🔴🔴")
        // Perform initial check immediately
        Task {
            await checkForUpdates()
        }
        
        // Schedule periodic checks
        let interval = TimeInterval(configuration.pollIntervalHours * 3600)
        timer = Timer.scheduledTimer(withTimeInterval: interval, repeats: true) { [weak self] _ in
            Task {
                await self?.checkForUpdates()
            }
        }
        
        print("[PollingService] Started polling every \(configuration.pollIntervalHours) hours")
    }
    
    /// Stop polling
    func stopPolling() {
        timer?.invalidate()
        timer = nil
        print("[PollingService] Stopped polling")
    }

    /// Set manual disconnect state; when true, avoid auto (re)starts
    func setManualDisconnect(_ value: Bool) {
        isManuallyDisconnected = value
    }
    
    /// Check for configuration updates
    func checkForUpdates() async {
        do {
            // Get token from keychain
            guard let token = try keychainService.loadToken() else {
                onStatusChange?(.error("No token configured"))
                return
            }
            
            // Generate keypair if needed
            try nebulaManager.generateKeypair()
            
            // Read public key
            let publicKey = try nebulaManager.readPublicKey()
            
            // Detect versions
            let clientVersion = getClientVersion()
            let nebulaVersion = nebulaManager.getNebulaVersion()
            let nebulaVersionStr = nebulaVersion ?? "nil"
            print("[PollingService] Detected client version: \(clientVersion), nebula version: \(nebulaVersionStr)")
            
            // Fetch config from server
            onStatusChange?(.connecting)
            let apiClient = APIClient(serverURL: configuration.serverURL)
            let response = try await apiClient.fetchConfig(token: token, publicKey: publicKey, clientVersion: clientVersion, nebulaVersion: nebulaVersion)
            
            // Write configuration and check if it changed
            let pollingDebug = "[PollingService] About to call writeConfiguration at \(Date())\n"
            try? pollingDebug.write(toFile: "/tmp/nebula-polling-debug.log", atomically: true, encoding: .utf8)
            let configChanged = try nebulaManager.writeConfiguration(response)
            let pollingDebug2 = pollingDebug + "writeConfiguration returned: \(configChanged)\n"
            try? pollingDebug2.write(toFile: "/tmp/nebula-polling-debug.log", atomically: true, encoding: .utf8)

            try handlePostFetch(configChanged: configChanged)
            print("[PollingService] Configuration check completed successfully")
            
        } catch let error as APIError {
            let message = error.localizedDescription
            onStatusChange?(.error(message))
            print("[PollingService] API error: \(message)")
        } catch let error as NebulaError {
            let message = error.localizedDescription
            onStatusChange?(.error(message))
            print("[PollingService] Nebula error: \(message)")
        } catch {
            onStatusChange?(.error(error.localizedDescription))
            print("[PollingService] Error: \(error.localizedDescription)")
        }
    }
    
    /// Update configuration
    func updateConfiguration(_ config: Configuration) {
        self.configuration = config
        
        // Restart polling with new interval if timer is active
        if timer != nil {
            stopPolling()
            startPolling()
        }
    }

    // MARK: - Internal helpers
    private func handlePostFetch(configChanged: Bool) throws {
        if isManuallyDisconnected {
            print("[PollingService] Manual disconnect active; skipping (re)start")
            onStatusChange?(.disconnected)
            return
        }
        if configChanged {
            print("[PollingService] Configuration changed, restarting Nebula")
            try nebulaManager.restartNebula()
            onStatusChange?(.connected)
            return
        }
        if !nebulaManager.isRunning() && configuration.isAutoStartEnabled {
            print("[PollingService] Nebula not running, starting it")
            try nebulaManager.startNebula()
        }
        onStatusChange?(.connected)
    }
}
