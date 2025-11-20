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
    
    /// Start polling for configuration updates
    func startPolling() {
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
            
            // Fetch config from server
            onStatusChange?(.connecting)
            let apiClient = APIClient(serverURL: configuration.serverURL)
            let response = try await apiClient.fetchConfig(token: token, publicKey: publicKey)
            
            // Write configuration and check if it changed
            let configChanged = try nebulaManager.writeConfiguration(response)

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
