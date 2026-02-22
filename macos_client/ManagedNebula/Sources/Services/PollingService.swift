import Foundation

/// Service that polls the server for configuration updates
class PollingService {
    private var timer: Timer?
    private var monitorTimer: Timer?
    private let nebulaManager: NebulaManager
    private let keychainService: KeychainService
    private var configuration: Configuration
    private var isManuallyDisconnected: Bool = false
    private var restartInProgress: Bool = false
    private var consecutiveFailures: Int = 0
    private let processCheckInterval: TimeInterval = 10
    private let restartInitTimeout: TimeInterval = 30
    private let maxRestartAttempts: Int = 5
    private let nebulaLogPath: String = "/var/log/nebula.log"
    private var lastNebulaLogOffset: UInt64 = 0
    
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
        startMonitoring()
    }
    
    /// Stop polling
    func stopPolling() {
        timer?.invalidate()
        timer = nil
        stopMonitoring()
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
            
            // Check for Nebula version updates first
            let nebulaUpdated = await nebulaManager.checkAndUpdateNebula(serverURL: configuration.serverURL)
            var forceRestart = nebulaUpdated
            if nebulaUpdated {
                print("[PollingService] Nebula was updated, will restart with new version")
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

            try handlePostFetch(configChanged: configChanged || forceRestart)
            print("[PollingService] Configuration check completed successfully")
            
        } catch let error as APIError {
            // Server returned an API error (401, 403, etc.)
            let message = error.localizedDescription
            onStatusChange?(.error(message))
            print("[PollingService] API error: \(message)")
        } catch let error as NebulaError {
            let message = error.localizedDescription
            onStatusChange?(.error(message))
            print("[PollingService] Nebula error: \(message)")
        } catch {
            // Network error or server unreachable - try to continue with cached config
            let timestamp = ISO8601DateFormatter().string(from: Date())
            print("[PollingService] [\(timestamp)] WARNING: Unable to reach management server: \(error.localizedDescription)")
            print("[PollingService] Attempting to continue with cached configuration")
            
            handleServerUnreachable()
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

    // MARK: - Monitoring & Auto-Heal
    private func startMonitoring() {
        monitorTimer?.invalidate()
        if let attrs = try? FileManager.default.attributesOfItem(atPath: nebulaLogPath),
           let size = attrs[.size] as? NSNumber {
            lastNebulaLogOffset = size.uint64Value
        } else {
            lastNebulaLogOffset = 0
        }
        monitorTimer = Timer.scheduledTimer(withTimeInterval: processCheckInterval, repeats: true) { [weak self] _ in
            Task { await self?.monitorNebula() }
        }
        print("[PollingService] Started process monitoring (every \(processCheckInterval)s)")
    }

    private func stopMonitoring() {
        monitorTimer?.invalidate()
        monitorTimer = nil
        restartInProgress = false
        print("[PollingService] Stopped process monitoring")
    }

    private func monitorNebula() async {
        guard !isManuallyDisconnected else { return }
        if restartInProgress { return }

        let (newLogs, newOffset) = readNewNebulaLogs(fromOffset: lastNebulaLogOffset)
        lastNebulaLogOffset = newOffset
        let goodbyeDetected = newLogs.lowercased().contains("goodbye")

        if nebulaManager.isRunning() { return }
        restartInProgress = true
        onStatusChange?(.connecting)
        if goodbyeDetected {
            print("[PollingService] GOODBYE DETECTED: Nebula exited, attempting recovery")
        } else {
            print("[PollingService] Nebula process not running; attempting recovery")
        }
        let recovered = await restartWithBackoff()
        if recovered {
            print("[PollingService] Recovery successful")
            onStatusChange?(.connected)
        } else {
            print("[PollingService] Recovery failed after \(maxRestartAttempts) attempts")
            onStatusChange?(.error("Failed to restart Nebula"))
        }
        restartInProgress = false
    }

    private func readNewNebulaLogs(fromOffset offset: UInt64) -> (String, UInt64) {
        guard let handle = FileHandle(forReadingAtPath: nebulaLogPath) else {
            return ("", offset)
        }
        defer {
            try? handle.close()
        }

        do {
            let attrs = try FileManager.default.attributesOfItem(atPath: nebulaLogPath)
            let currentSize = (attrs[.size] as? NSNumber)?.uint64Value ?? offset
            let safeOffset = min(offset, currentSize)
            try handle.seek(toOffset: safeOffset)
            let data = handle.readDataToEndOfFile()
            let text = String(data: data, encoding: .utf8) ?? ""
            return (text, currentSize)
        } catch {
            return ("", offset)
        }
    }

    private func restartWithBackoff() async -> Bool {
        for attempt in 0..<maxRestartAttempts {
            let timestamp = ISO8601DateFormatter().string(from: Date())
            print("[PollingService] [\(timestamp)] Restart attempt \(attempt + 1)/\(maxRestartAttempts)")
            do {
                try nebulaManager.restartNebula()
            } catch {
                print("[PollingService] Restart attempt failed: \(error.localizedDescription)")
            }

            var waited: TimeInterval = 0
            while waited < restartInitTimeout {
                try? await Task.sleep(nanoseconds: 500_000_000) // 0.5s
                waited += 0.5
                if nebulaManager.isRunning() {
                    consecutiveFailures = 0
                    return true
                }
            }
            consecutiveFailures += 1
            print("[PollingService] Restart attempt \(attempt + 1) failed - Nebula did not start within \(restartInitTimeout)s")
            if attempt < maxRestartAttempts - 1 {
                let delay = computeBackoff(attempt: attempt, cap: 30)
                print("[PollingService] Waiting \(delay)s before next attempt...")
                try? await Task.sleep(nanoseconds: UInt64(delay) * 1_000_000_000)
            }
        }
        return false
    }

    private func computeBackoff(attempt: Int, base: Int = 1, cap: Int = 60) -> Int {
        return min(base * (1 << attempt), cap)
    }

    // MARK: - Cached Config Fallback
    
    /// Handle server unreachable scenario by attempting to use cached or existing config
    private func handleServerUnreachable() {
        if let cachedResponse = nebulaManager.loadCachedConfig() {
            handleCachedConfigFallback(cachedResponse)
        } else {
            handleExistingConfigFallback()
        }
    }
    
    /// Attempt to apply cached config response as fallback
    private func handleCachedConfigFallback(_ cachedResponse: ClientConfigResponse) {
        print("[PollingService] Using cached config as fallback")
        
        do {
            // Write the cached config (this will be a no-op if config hasn't changed)
            try nebulaManager.writeConfiguration(cachedResponse)
            
            // Check if Nebula is running with the existing config
            if nebulaManager.isRunning() {
                print("[PollingService] Nebula is running with existing configuration")
                onStatusChange?(.connected)
            } else if configuration.isAutoStartEnabled && !isManuallyDisconnected {
                // Try to start Nebula with existing config
                print("[PollingService] Attempting to start Nebula with cached configuration")
                try nebulaManager.startNebula()
                onStatusChange?(.connected)
            } else {
                onStatusChange?(.error("Server unreachable - using cached config"))
            }
        } catch {
            print("[PollingService] Failed to apply cached config: \(error.localizedDescription)")
            onStatusChange?(.error("Server unreachable and failed to apply cached config"))
        }
    }
    
    /// Attempt to continue with existing config files when no cached config is available
    private func handleExistingConfigFallback() {
        print("[PollingService] ERROR: No cached config available and server is unreachable")
        
        // Check if we at least have existing config files to continue with
        guard FileManager.default.fileExists(atPath: FileManager.NebulaFiles.configFile.path) else {
            print("[PollingService] ERROR: No existing config file found and server is unreachable")
            print("[PollingService] Cannot start Nebula without configuration")
            onStatusChange?(.error("Cannot reach server and no configuration available"))
            return
        }
        
        print("[PollingService] Existing config file found, continuing with current configuration")
        
        if nebulaManager.isRunning() {
            print("[PollingService] Nebula is running with existing configuration")
            onStatusChange?(.connected)
        } else if configuration.isAutoStartEnabled && !isManuallyDisconnected {
            print("[PollingService] Attempting to start Nebula with existing configuration")
            do {
                try nebulaManager.startNebula()
                onStatusChange?(.connected)
            } catch {
                print("[PollingService] Failed to start Nebula: \(error.localizedDescription)")
                onStatusChange?(.error("Server unreachable - cannot start Nebula"))
            }
        } else {
            onStatusChange?(.error("Server unreachable - using existing config"))
        }
    }
}

