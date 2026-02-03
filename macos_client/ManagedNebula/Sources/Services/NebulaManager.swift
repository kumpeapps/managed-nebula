import Foundation
import CryptoKit
import Darwin

/// Manages Nebula binary execution and lifecycle
class NebulaManager {
    private var process: Process?
    private let nebulaBinaryPath: String
    private let keychainService = KeychainService()
    private let fileManager = FileManager.default
    
    init(nebulaBinaryPath: String = "/usr/local/bin/nebula") {
        self.nebulaBinaryPath = nebulaBinaryPath
    }
    
    /// Generate keypair using nebula-cert
    func generateKeypair() throws {
        let keyPath = FileManager.NebulaFiles.privateKey
        let pubPath = FileManager.NebulaFiles.publicKey
        
        // Skip if keypair already exists
        if fileManager.fileExists(atPath: keyPath.path) && 
           fileManager.fileExists(atPath: pubPath.path) {
            print("[NebulaManager] Keypair already exists, skipping generation")
            return
        }
        
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/local/bin/nebula-cert")
        process.arguments = [
            "keygen",
            "-out-key", keyPath.path,
            "-out-pub", pubPath.path
        ]
        
        try process.run()
        process.waitUntilExit()
        
        guard process.terminationStatus == 0 else {
            throw NebulaError.keypairGenerationFailed
        }
        
        // Set proper permissions on private key (0600)
        try fileManager.setAttributes(
            [.posixPermissions: 0o600],
            ofItemAtPath: keyPath.path
        )
        
        print("[NebulaManager] Keypair generated successfully")
    }
    
    /// Read public key from file
    func readPublicKey() throws -> String {
        let pubPath = FileManager.NebulaFiles.publicKey
        guard fileManager.fileExists(atPath: pubPath.path) else {
            throw NebulaError.publicKeyNotFound
        }
        return try String(contentsOf: pubPath, encoding: .utf8)
    }
    
    /// Write configuration files
    func writeConfiguration(_ response: ClientConfigResponse) throws -> Bool {
        // Debug log
        let debugEntry = "[writeConfiguration] Called at \(Date())\n"
        try? debugEntry.write(toFile: "/tmp/nebula-flow-debug.log", atomically: true, encoding: .utf8)
        
        // Cache the config response for fallback
        saveCachedConfig(response)
        
        // Calculate hash of new configuration
        let newHash = calculateConfigHash(
            config: response.config,
            cert: response.clientCertPem,
            caCerts: response.caChainPems
        )
        
        // Calculate hash of current configuration
        let currentHash = getCurrentConfigHash()
        
        // Debug log
        let hashDebug = debugEntry + "New hash: \(newHash)\nCurrent hash: \(currentHash ?? "nil")\n"
        try? hashDebug.write(toFile: "/tmp/nebula-flow-debug.log", atomically: true, encoding: .utf8)
        
        // Check if configuration has changed
        if newHash == currentHash {
            let unchangedDebug = hashDebug + "Config unchanged, returning false\n"
            try? unchangedDebug.write(toFile: "/tmp/nebula-flow-debug.log", atomically: true, encoding: .utf8)
            print("[NebulaManager] Configuration unchanged, no restart needed")
            return false
        }
        
        print("[NebulaManager] Configuration changed, writing new files")
        let changedDebug = hashDebug + "Config changed, calling writeUserConfig\n"
        try? changedDebug.write(toFile: "/tmp/nebula-flow-debug.log", atomically: true, encoding: .utf8)
        
        // 1) Write user-viewable config and local certs
        try writeUserConfig(response.config)
        let caChain = response.caChainPems.joined(separator: "\n")
        try writeCertificates(certPem: response.clientCertPem, caChain: caChain)

        // 2) Stage root-owned copies for the helper daemon
        try stageRootConfig(rawConfig: response.config, certPem: response.clientCertPem, caChain: caChain)
        
        return true
    }

    // MARK: - Config Caching
    
    /// Save config response to cache file for fallback
    private func saveCachedConfig(_ response: ClientConfigResponse) {
        do {
            let encoder = JSONEncoder()
            encoder.outputFormatting = .prettyPrinted
            let data = try encoder.encode(response)

            let cacheFileURL = FileManager.NebulaFiles.cachedConfigFile
            let cacheDirectoryURL = cacheFileURL.deletingLastPathComponent()

            // Ensure cache directory exists before writing
            if !fileManager.fileExists(atPath: cacheDirectoryURL.path) {
                try fileManager.createDirectory(at: cacheDirectoryURL, withIntermediateDirectories: true, attributes: nil)
            }

            // Write atomically to avoid partial writes of sensitive config
            try data.write(to: cacheFileURL, options: .atomic)

            // Harden permissions on directory and file to limit exposure
            do {
                // Restrict directory to user-only access (rwx------)
                try fileManager.setAttributes(
                    [.posixPermissions: NSNumber(value: Int16(0o700))],
                    ofItemAtPath: cacheDirectoryURL.path
                )

                // Restrict file to user-only access (rw-------)
                try fileManager.setAttributes(
                    [.posixPermissions: NSNumber(value: Int16(0o600))],
                    ofItemAtPath: cacheFileURL.path
                )
            } catch {
                // Don't fail caching if permission tightening fails, but log a warning
                print("[NebulaManager] Warning: Cached config written but failed to harden permissions: \(error)")
            }

            print("[NebulaManager] Config cached successfully")
        } catch {
            print("[NebulaManager] Warning: Failed to cache config: \(error)")
        }
    }
    
    /// Load cached config response as fallback
    func loadCachedConfig() -> ClientConfigResponse? {
        do {
            guard fileManager.fileExists(atPath: FileManager.NebulaFiles.cachedConfigFile.path) else {
                return nil
            }
            let data = try Data(contentsOf: FileManager.NebulaFiles.cachedConfigFile)
            let decoder = JSONDecoder()
            return try decoder.decode(ClientConfigResponse.self, from: data)
        } catch {
            print("[NebulaManager] Warning: Failed to load cached config: \(error)")
            return nil
        }
    }

    // MARK: - File writing helpers

    private func writeUserConfig(_ raw: String) throws {
        // Expand $HOME in config paths since Nebula doesn't do environment variable expansion
        let homeDir = FileManager.default.homeDirectoryForCurrentUser.path
        
        // Write debug log to file we can check
        let debugLog = """
        [writeUserConfig] Called at \(Date())
        Home directory: \(homeDir)
        Raw config contains $HOME: \(raw.contains("$HOME"))
        Raw config first 300 chars: \(String(raw.prefix(300)))
        """
        try? debugLog.write(toFile: "/tmp/nebula-debug.log", atomically: true, encoding: .utf8)
        
        // Simple string replacement
        let expandedConfig = raw.replacingOccurrences(of: "$HOME", with: homeDir)
        
        let debugLog2 = debugLog + "\nExpanded contains $HOME: \(expandedConfig.contains("$HOME"))\nExpanded first 300 chars: \(String(expandedConfig.prefix(300)))"
        try? debugLog2.write(toFile: "/tmp/nebula-debug.log", atomically: true, encoding: .utf8)
        
        try fileManager.writeSecure(
            expandedConfig,
            to: FileManager.NebulaFiles.configFile,
            permissions: 0o644
        )
    }

    private func writeCertificates(certPem: String, caChain: String) throws {
        try fileManager.writeSecure(
            certPem,
            to: FileManager.NebulaFiles.certificate,
            permissions: 0o644
        )
        try fileManager.writeSecure(
            caChain,
            to: FileManager.NebulaFiles.caCertificate,
            permissions: 0o644
        )
    }

    private func stageRootConfig(rawConfig: String, certPem: String, caChain: String) throws {
        let stagingDir = URL(fileURLWithPath: "/tmp/managed-nebula")
        try? fileManager.createDirectory(at: stagingDir, withIntermediateDirectories: true)
        let stagedConfig = stagingDir.appendingPathComponent("config.yml")
        let stagedCert = stagingDir.appendingPathComponent("host.crt")
        let stagedCA = stagingDir.appendingPathComponent("ca.crt")
        let stagedKey = stagingDir.appendingPathComponent("host.key")

        // Do not force a specific utun; allow Nebula to choose a free device
        let rootConfig: String = stripTunDev(from: rawConfig)
        try rootConfig.write(to: stagedConfig, atomically: true, encoding: .utf8)
        try certPem.write(to: stagedCert, atomically: true, encoding: .utf8)
        try caChain.write(to: stagedCA, atomically: true, encoding: .utf8)
        if fileManager.fileExists(atPath: FileManager.NebulaFiles.privateKey.path) {
            let keyData = try Data(contentsOf: FileManager.NebulaFiles.privateKey)
            try keyData.write(to: stagedKey)
        }
    }

    private func stripTunDev(from raw: String) -> String {
        return raw
            .components(separatedBy: "\n")
            .filter { line in
                let trimmed = line.trimmingCharacters(in: .whitespaces)
                return !trimmed.hasPrefix("dev:")
            }
            .joined(separator: "\n")
    }

    // No explicit injection of dev: utunX; let Nebula allocate automatically
    
    /// Safely write a command to the control file with proper error handling
    private func writeControlCommand(_ command: String) throws {
        let controlFile = "/tmp/nebula-control"
        let fileURL = URL(fileURLWithPath: controlFile)
        let tempFileURL = URL(fileURLWithPath: controlFile + ".tmp")
        
        guard let data = command.data(using: .utf8) else {
            throw NebulaError.controlFileWriteFailed(reason: "Failed to encode command")
        }
        
        do {
            // First, ensure the control file exists with proper permissions
            if !fileManager.fileExists(atPath: controlFile) {
                // Create the file if it doesn't exist
                fileManager.createFile(atPath: controlFile, contents: nil, attributes: [
                    .posixPermissions: 0o666
                ])
                print("[NebulaManager] Created control file: \(controlFile)")
            }
            
            // Try atomic write first (preferred method)
            do {
                try data.write(to: tempFileURL, options: .atomic)
                
                // If temp file exists, try to replace the original
                if fileManager.fileExists(atPath: tempFileURL.path) {
                    _ = try? fileManager.removeItem(at: fileURL)
                    try fileManager.moveItem(at: tempFileURL, to: fileURL)
                    print("[NebulaManager] Sent \(command) command to helper daemon (atomic write)")
                    return
                }
            } catch {
                print("[NebulaManager] Atomic write failed: \(error), trying direct write")
            }
            
            // Fallback: Direct write if atomic write fails
            try data.write(to: fileURL, options: [])
            print("[NebulaManager] Sent \(command) command to helper daemon (direct write)")
            
        } catch {
            print("[NebulaManager] Failed to write \(command) command: \(error)")
            throw NebulaError.controlFileWriteFailed(reason: error.localizedDescription)
        }
    }
    
    /// Start Nebula daemon
    func startNebula() throws {
        // Ensure config exists before asking helper to start
        let configPath = FileManager.NebulaFiles.configFile
        guard fileManager.fileExists(atPath: configPath.path) else {
            throw NebulaError.configNotFound
        }

        // Ask the root helper daemon to start Nebula
        try writeControlCommand("start")
        
        // Wait for Nebula to actually start and be running
        // Poll on background thread to avoid blocking UI
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            guard let self = self else { return }
            var attempts = 0
            let maxAttempts = 20 // 20 * 500ms = 10 seconds
            while attempts < maxAttempts {
                usleep(500_000) // 500ms
                if self.isRunning() {
                    print("[NebulaManager] Nebula is now running")
                    break
                }
                attempts += 1
            }
            
            if attempts >= maxAttempts {
                print("[NebulaManager] Warning: Nebula didn't start within 10 seconds")
            }
        }
    }
    
    /// Stop Nebula daemon
    func stopNebula() {
        // Ask the root helper daemon to stop Nebula
        do {
            try writeControlCommand("stop")
        } catch {
            print("[NebulaManager] Failed to send stop command: \(error)")
        }
        
        // Wait for Nebula to actually stop
        // Poll on background thread to avoid blocking UI
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            guard let self = self else { return }
            var attempts = 0
            let maxAttempts = 10 // 10 * 500ms = 5 seconds
            while attempts < maxAttempts {
                usleep(500_000) // 500ms
                if !self.isRunning() {
                    print("[NebulaManager] Nebula has stopped")
                    break
                }
                attempts += 1
            }
            
            if attempts >= maxAttempts {
                print("[NebulaManager] Warning: Nebula didn't stop within 5 seconds")
            }
        }
        self.process = nil
    }
    
    /// Check if Nebula is running
    func isRunning() -> Bool {
        // Check system processes for a running nebula daemon
        let check = Process()
        check.executableURL = URL(fileURLWithPath: "/usr/bin/pgrep")
        check.arguments = ["-f", "nebula -config"]
        let pipe = Pipe()
        check.standardOutput = pipe
        try? check.run()
        check.waitUntilExit()
        return check.terminationStatus == 0
    }
    
    /// Restart Nebula daemon
    func restartNebula() throws {
        stopNebula()
        try startNebula()
    }
    
    /// Get Nebula binary version
    func getNebulaVersion() -> String {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: nebulaBinaryPath)
        process.arguments = ["-version"]
        
        let pipe = Pipe()
        process.standardOutput = pipe
        process.standardError = pipe
        
        do {
            try process.run()
            process.waitUntilExit()
            
            let data = pipe.fileHandleForReading.readDataToEndOfFile()
            if let output = String(data: data, encoding: .utf8) {
                // Parse version from output like "Version: 1.8.2"
                let lines = output.components(separatedBy: "\n")
                for line in lines {
                    if line.hasPrefix("Version:") {
                        return line.replacingOccurrences(of: "Version:", with: "").trimmingCharacters(in: .whitespaces)
                    }
                }
                // Fallback: return first non-empty line
                return lines.first(where: { !$0.isEmpty })?.trimmingCharacters(in: .whitespaces) ?? "Unknown"
            }
        } catch {
            print("[NebulaManager] Failed to get Nebula version: \(error)")
        }
        
        return "Unknown"
    }
    
    /// Check server's Nebula version and auto-update if different
    /// Returns true if update was performed
    func checkAndUpdateNebula(serverURL: String) async -> Bool {
        print("[NebulaManager] Checking for Nebula version updates...")
        
        do {
            // Get server version (public endpoint, no auth required)
            let versionURL = URL(string: "\(serverURL.trimmingCharacters(in: CharacterSet(charactersIn: "/")))/v1/version")!
            
            let (data, response) = try await URLSession.shared.data(from: versionURL)
            
            guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else {
                print("[NebulaManager] Failed to fetch server version")
                return false
            }
            
            let versionInfo = try JSONDecoder().decode(VersionResponse.self, from: data)
            let serverVersion = versionInfo.nebulaVersion.trimmingCharacters(in: CharacterSet(charactersIn: "v"))
            let localVersion = getNebulaVersion().trimmingCharacters(in: CharacterSet(charactersIn: "v"))
            
            print("[NebulaManager] Nebula version check: local=\(localVersion), server=\(serverVersion)")
            
            // If versions match or local version is unknown, skip update
            if localVersion == "Unknown" {
                print("[NebulaManager] Cannot determine local Nebula version")
                return false
            }
            
            if localVersion == serverVersion {
                print("[NebulaManager] Nebula version matches server, no update needed")
                return false
            }
            
            // Versions differ - download and install matching version
            print("[NebulaManager] Nebula version mismatch detected. Upgrading from \(localVersion) to \(serverVersion)")
            
            // Detect architecture
            var arch = "amd64"
            #if arch(arm64)
            arch = "arm64"
            #endif
            
            // Download Nebula binaries from GitHub
            let downloadURL = URL(string: "https://github.com/slackhq/nebula/releases/download/v\(serverVersion)/nebula-darwin-\(arch).tar.gz")!
            print("[NebulaManager] Downloading Nebula \(serverVersion) from \(downloadURL)")
            
            let (tarData, downloadResponse) = try await URLSession.shared.data(from: downloadURL)
            
            guard let httpDownloadResponse = downloadResponse as? HTTPURLResponse, httpDownloadResponse.statusCode == 200 else {
                print("[NebulaManager] Failed to download Nebula binary")
                return false
            }
            
            print("[NebulaManager] Downloaded \(tarData.count) bytes")
            
            // Create temporary directory
            let tempDir = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
            try FileManager.default.createDirectory(at: tempDir, withIntermediateDirectories: true)
            defer {
                try? FileManager.default.removeItem(at: tempDir)
            }
            
            // Write tar.gz file
            let tarPath = tempDir.appendingPathComponent("nebula.tar.gz")
            try tarData.write(to: tarPath)
            
            // Extract tar.gz
            let extractDir = tempDir.appendingPathComponent("extract")
            try FileManager.default.createDirectory(at: extractDir, withIntermediateDirectories: true)
            
            let extractProcess = Process()
            extractProcess.executableURL = URL(fileURLWithPath: "/usr/bin/tar")
            extractProcess.arguments = ["-xzf", tarPath.path, "-C", extractDir.path]
            try extractProcess.run()
            extractProcess.waitUntilExit()
            
            guard extractProcess.terminationStatus == 0 else {
                print("[NebulaManager] Failed to extract Nebula archive")
                return false
            }
            
            // Find binaries
            let nebulaBin = extractDir.appendingPathComponent("nebula")
            let nebulaCertBin = extractDir.appendingPathComponent("nebula-cert")
            
            guard FileManager.default.fileExists(atPath: nebulaBin.path),
                  FileManager.default.fileExists(atPath: nebulaCertBin.path) else {
                print("[NebulaManager] ERROR: Nebula binaries not found in archive")
                return false
            }
            
            // Stop Nebula before replacing binaries
            print("[NebulaManager] Stopping Nebula daemon before upgrade...")
            stopNebula()
            
            // Wait for Nebula to stop (max 5 seconds)
            var stopAttempts = 0
            while isRunning() && stopAttempts < 10 {
                usleep(500_000) // 500ms
                stopAttempts += 1
            }
            
            // Backup current binaries
            let installDir = URL(fileURLWithPath: "/usr/local/bin")
            let nebulaPath = installDir.appendingPathComponent("nebula")
            let nebulaCertPath = installDir.appendingPathComponent("nebula-cert")
            
            if FileManager.default.fileExists(atPath: nebulaPath.path) {
                let backupPath = nebulaPath.appendingPathExtension("bak")
                try? FileManager.default.removeItem(at: backupPath)
                try? FileManager.default.copyItem(at: nebulaPath, to: backupPath)
                print("[NebulaManager] Backed up nebula to \(backupPath.path)")
            }
            
            if FileManager.default.fileExists(atPath: nebulaCertPath.path) {
                let backupPath = nebulaCertPath.appendingPathExtension("bak")
                try? FileManager.default.removeItem(at: backupPath)
                try? FileManager.default.copyItem(at: nebulaCertPath, to: backupPath)
                print("[NebulaManager] Backed up nebula-cert to \(backupPath.path)")
            }
            
            // Replace binaries (requires root privileges via helper script)
            // Stage the new binaries in a unique temp location for the helper daemon to avoid races
            let upgradeAttemptID = UUID().uuidString
            let stagingDir = URL(fileURLWithPath: "/tmp/managed-nebula-upgrade-\(upgradeAttemptID)")
            try? FileManager.default.createDirectory(at: stagingDir, withIntermediateDirectories: true)
            
            let stagedNebula = stagingDir.appendingPathComponent("nebula")
            let stagedCert = stagingDir.appendingPathComponent("nebula-cert")
            
            try FileManager.default.copyItem(at: nebulaBin, to: stagedNebula)
            try FileManager.default.copyItem(at: nebulaCertBin, to: stagedCert)
            
            // Tell helper to install the upgrades via control file, passing the unique staging path
            try writeControlCommand("upgrade:\(stagingDir.path)")
            
            // Wait a moment for upgrade to complete
            sleep(2)
            
            // Verify new version
            let newVersion = getNebulaVersion().trimmingCharacters(in: CharacterSet(charactersIn: "v"))
            if newVersion == serverVersion {
                print("[NebulaManager] ✓ Nebula successfully upgraded to \(newVersion)")
                return true
            } else {
                print("[NebulaManager] WARNING: Version mismatch after upgrade. Expected \(serverVersion), got \(newVersion)")
                return false
            }
            
        } catch {
            print("[NebulaManager] Failed to update Nebula: \(error)")
            return false
        }
    }
    
    // MARK: - Private Helpers
    
    private func calculateConfigHash(config: String, cert: String, caCerts: [String]) -> String {
        var hasher = SHA256()
        hasher.update(data: Data(config.utf8))
        hasher.update(data: Data(cert.utf8))
        hasher.update(data: Data(caCerts.joined().utf8))
        return hasher.finalize().map { String(format: "%02x", $0) }.joined()
    }
    
    private func getCurrentConfigHash() -> String {
        let configPath = FileManager.NebulaFiles.configFile
        let certPath = FileManager.NebulaFiles.certificate
        let caPath = FileManager.NebulaFiles.caCertificate
        
        guard fileManager.fileExists(atPath: configPath.path) else {
            return ""
        }
        
        let config = (try? String(contentsOf: configPath)) ?? ""
        let cert = (try? String(contentsOf: certPath)) ?? ""
        let ca = (try? String(contentsOf: caPath)) ?? ""
        
        var hasher = SHA256()
        hasher.update(data: Data(config.utf8))
        hasher.update(data: Data(cert.utf8))
        hasher.update(data: Data(ca.utf8))
        return hasher.finalize().map { String(format: "%02x", $0) }.joined()
    }
}

enum NebulaError: Error, LocalizedError {
    case keypairGenerationFailed
    case publicKeyNotFound
    case configNotFound
    case binaryNotFound
    case controlFileWriteFailed(reason: String)
    
    var errorDescription: String? {
        switch self {
        case .keypairGenerationFailed:
            return "Failed to generate keypair with nebula-cert"
        case .publicKeyNotFound:
            return "Public key file not found"
        case .configNotFound:
            return "Configuration file not found"
        case .binaryNotFound:
            return "Nebula binary not found at /usr/local/bin/nebula"
        case .controlFileWriteFailed(let reason):
            return "Failed to write to control file: \(reason)"
        }
    }
}
