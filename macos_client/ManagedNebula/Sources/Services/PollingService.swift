import Foundation

/// Service that polls the server for configuration updates
class PollingService {
    private var timer: Timer?
    private let nebulaManager: NebulaManager
    private let keychainService: KeychainService
    private var configuration: Configuration
    
    var onStatusChange: ((ConnectionStatus) -> Void)?
    
    init(nebulaManager: NebulaManager, keychainService: KeychainService, configuration: Configuration) {
        self.nebulaManager = nebulaManager
        self.keychainService = keychainService
        self.configuration = configuration
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
            
            // Restart Nebula if config changed
            if configChanged {
                print("[PollingService] Configuration changed, restarting Nebula")
                try nebulaManager.restartNebula()
            } else if !nebulaManager.isRunning() && configuration.isAutoStartEnabled {
                print("[PollingService] Nebula not running, starting it")
                try nebulaManager.startNebula()
            }
            
            onStatusChange?(.connected)
            print("[PollingService] Configuration check completed successfully")
            
        } catch let error as APIError {
            let message = error.localizedDescription ?? "Unknown API error"
            onStatusChange?(.error(message))
            print("[PollingService] API error: \(message)")
        } catch let error as NebulaError {
            let message = error.localizedDescription ?? "Unknown Nebula error"
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
}
