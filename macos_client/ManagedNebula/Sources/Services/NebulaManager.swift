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
        
        // 1) Write user-viewable config and local certs
        try writeUserConfig(response.config)
        let caChain = response.caChainPems.joined(separator: "\n")
        try writeCertificates(certPem: response.clientCertPem, caChain: caChain)

        // 2) Stage root-owned copies for the helper daemon
        try stageRootConfig(rawConfig: response.config, certPem: response.clientCertPem, caChain: caChain)
        
        return true
    }

    // MARK: - File writing helpers

    private func writeUserConfig(_ raw: String) throws {
        try fileManager.writeSecure(
            makeUserReadableConfig(from: raw),
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

    private func makeUserReadableConfig(from raw: String) -> String {
        var config = raw
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
        return config
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
    
    /// Start Nebula daemon
    func startNebula() throws {
        // Ensure config exists before asking helper to start
        let configPath = FileManager.NebulaFiles.configFile
        guard fileManager.fileExists(atPath: configPath.path) else {
            throw NebulaError.configNotFound
        }

        // Ask the root helper daemon to start Nebula
        let controlFile = "/tmp/nebula-control"
        try? "start".write(toFile: controlFile, atomically: true, encoding: .utf8)

        // Small delay to allow daemon to spawn process
        usleep(500_000)
        print("[NebulaManager] Sent start command to helper daemon")
    }
    
    /// Stop Nebula daemon
    func stopNebula() {
        // Ask the root helper daemon to stop Nebula
        let controlFile = "/tmp/nebula-control"
        try? "stop".write(toFile: controlFile, atomically: true, encoding: .utf8)
        usleep(300_000)
        self.process = nil
        print("[NebulaManager] Sent stop command to helper daemon")
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
