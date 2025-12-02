import Foundation

extension FileManager {
    /// Application support directory for ManagedNebula (system-level)
    static var managedNebulaDirectory: URL {
        // Use system-level directory so Nebula can access files
        let managedNebula = URL(fileURLWithPath: "/Library/Application Support/Managed Nebula")
        
        // Create directory if it doesn't exist (requires admin privileges)
        try? FileManager.default.createDirectory(at: managedNebula, withIntermediateDirectories: true)
        
        return managedNebula
    }
    
    /// Logs directory for ManagedNebula
    static var managedNebulaLogsDirectory: URL {
        let library = FileManager.default.urls(for: .libraryDirectory, in: .userDomainMask)[0]
        let logs = library.appendingPathComponent("Logs/ManagedNebula")
        
        // Create directory if it doesn't exist
        try? FileManager.default.createDirectory(at: logs, withIntermediateDirectories: true)
        
        return logs
    }
    
    /// Configuration file paths
    struct NebulaFiles {
        static let configFile = FileManager.managedNebulaDirectory.appendingPathComponent("config.yml")
        static let privateKey = FileManager.managedNebulaDirectory.appendingPathComponent("host.key")
        static let publicKey = FileManager.managedNebulaDirectory.appendingPathComponent("host.pub")
        static let certificate = FileManager.managedNebulaDirectory.appendingPathComponent("host.crt")
        static let caCertificate = FileManager.managedNebulaDirectory.appendingPathComponent("ca.crt")
        static let logFile = FileManager.managedNebulaLogsDirectory.appendingPathComponent("nebula.log")
    }
}

extension FileManager {
    /// Write string to file with specific permissions
    func writeSecure(_ content: String, to url: URL, permissions: Int16) throws {
        try content.write(to: url, atomically: true, encoding: .utf8)
        try setAttributes([.posixPermissions: permissions], ofItemAtPath: url.path)
    }
}
