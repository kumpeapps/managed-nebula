import Foundation

/// Application configuration settings
struct Configuration: Codable {
    var serverURL: String
    var pollIntervalHours: Int
    var isAutoStartEnabled: Bool
    var launchAtLogin: Bool
    
    static let `default` = Configuration(
        serverURL: "",
        pollIntervalHours: 24,
        isAutoStartEnabled: true,
        launchAtLogin: false
    )
    
    // UserDefaults key
    private static let configKey = "com.managednebula.configuration"
    
    /// Load configuration from UserDefaults
    static func load() -> Configuration {
        guard let data = UserDefaults.standard.data(forKey: configKey),
              let config = try? JSONDecoder().decode(Configuration.self, from: data) else {
            return .default
        }
        return config
    }
    
    /// Save configuration to UserDefaults
    func save() {
        if let data = try? JSONEncoder().encode(self) {
            UserDefaults.standard.set(data, forKey: Self.configKey)
        }
    }
}

/// Response from /v1/client/config endpoint
struct ClientConfigResponse: Codable {
    let config: String
    let clientCertPem: String
    let caChainPems: [String]
    let certNotBefore: String
    let certNotAfter: String
    let lighthouse: Bool
    let keyPath: String
    
    enum CodingKeys: String, CodingKey {
        case config
        case clientCertPem = "client_cert_pem"
        case caChainPems = "ca_chain_pems"
        case certNotBefore = "cert_not_before"
        case certNotAfter = "cert_not_after"
        case lighthouse
        case keyPath = "key_path"
    }
}

/// Request for /v1/client/config endpoint
struct ClientConfigRequest: Codable {
    let token: String
    let publicKey: String
    
    enum CodingKeys: String, CodingKey {
        case token
        case publicKey = "public_key"
    }
}

/// Connection status
enum ConnectionStatus {
    case disconnected
    case connecting
    case connected
    case error(String)
    
    var displayText: String {
        switch self {
        case .disconnected:
            return "Disconnected"
        case .connecting:
            return "Connecting..."
        case .connected:
            return "Connected"
        case .error(let message):
            return "Error: \(message)"
        }
    }
}
