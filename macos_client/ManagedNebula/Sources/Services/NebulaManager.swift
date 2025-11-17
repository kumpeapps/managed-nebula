import Foundation
import CryptoKit

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
        // Calculate hash of new configuration
        let newHash = calculateConfigHash(
            config: response.config,
            cert: response.clientCertPem,
            caCerts: response.caChainPems
        )
        
        // Calculate hash of current configuration
        let currentHash = getCurrentConfigHash()
        
        // Check if configuration has changed
        if newHash == currentHash {
            print("[NebulaManager] Configuration unchanged, no restart needed")
            return false
        }
        
        print("[NebulaManager] Configuration changed, writing new files")
        
        // Write config file
        try fileManager.writeSecure(
            response.config,
            to: FileManager.NebulaFiles.configFile,
            permissions: 0o644
        )
        
        // Write client certificate
        try fileManager.writeSecure(
            response.clientCertPem,
            to: FileManager.NebulaFiles.certificate,
            permissions: 0o644
        )
        
        // Write CA certificate chain
        let caChain = response.caChainPems.joined(separator: "\n")
        try fileManager.writeSecure(
            caChain,
            to: FileManager.NebulaFiles.caCertificate,
            permissions: 0o644
        )
        
        // Update config.yml to use correct paths
        var config = response.config
        config = config.replacingOccurrences(
            of: "/var/lib/nebula/host.key",
            with: FileManager.NebulaFiles.privateKey.path
        )
        config = config.replacingOccurrences(
            of: "/etc/nebula/ca.crt",
            with: FileManager.NebulaFiles.caCertificate.path
        )
        config = config.replacingOccurrences(
            of: "/etc/nebula/host.crt",
            with: FileManager.NebulaFiles.certificate.path
        )
        
        try fileManager.writeSecure(
            config,
            to: FileManager.NebulaFiles.configFile,
            permissions: 0o644
        )
        
        return true
    }
    
    /// Start Nebula daemon
    func startNebula() throws {
        // Stop existing process if running
        stopNebula()
        
        let configPath = FileManager.NebulaFiles.configFile
        guard fileManager.fileExists(atPath: configPath.path) else {
            throw NebulaError.configNotFound
        }
        
        let logPath = FileManager.NebulaFiles.logFile
        
        process = Process()
        process?.executableURL = URL(fileURLWithPath: nebulaBinaryPath)
        process?.arguments = ["-config", configPath.path]
        
        // Redirect output to log file
        let logFileHandle = try FileHandle(forWritingTo: logPath)
        process?.standardOutput = logFileHandle
        process?.standardError = logFileHandle
        
        try process?.run()
        print("[NebulaManager] Nebula daemon started")
    }
    
    /// Stop Nebula daemon
    func stopNebula() {
        guard let process = process, process.isRunning else {
            return
        }
        
        // Try graceful termination first
        process.terminate()
        
        // Wait up to 2 seconds
        DispatchQueue.global().asyncAfter(deadline: .now() + 2) {
            if process.isRunning {
                // Force kill if still running
                kill(process.processIdentifier, SIGKILL)
            }
        }
        
        self.process = nil
        print("[NebulaManager] Nebula daemon stopped")
    }
    
    /// Check if Nebula is running
    func isRunning() -> Bool {
        return process?.isRunning ?? false
    }
    
    /// Restart Nebula daemon
    func restartNebula() throws {
        stopNebula()
        try startNebula()
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
        }
    }
}
