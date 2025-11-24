import Foundation

/// Client for communicating with Managed Nebula server API
class APIClient {
    private let serverURL: String
    private let session: URLSession
    
    init(serverURL: String) {
        self.serverURL = serverURL
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 30
        self.session = URLSession(configuration: config)
    }
    
    /// Fetch configuration from server
    func fetchConfig(token: String, publicKey: String, clientVersion: String? = nil, nebulaVersion: String? = nil) async throws -> ClientConfigResponse {
        let url = URL(string: "\(serverURL.trimmingCharacters(in: CharacterSet(charactersIn: "/")))/v1/client/config")!
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let requestBody = ClientConfigRequest(token: token, publicKey: publicKey, clientVersion: clientVersion, nebulaVersion: nebulaVersion)
        request.httpBody = try JSONEncoder().encode(requestBody)
        
        let (data, response) = try await session.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        
        switch httpResponse.statusCode {
        case 200:
            let decoder = JSONDecoder()
            return try decoder.decode(ClientConfigResponse.self, from: data)
        case 401:
            throw APIError.unauthorized
        case 403:
            throw APIError.clientBlocked
        case 409:
            throw APIError.noIPAssignment
        case 503:
            throw APIError.noCA
        default:
            let message = String(data: data, encoding: .utf8) ?? "Unknown error"
            throw APIError.serverError(httpResponse.statusCode, message)
        }
    }
}

enum APIError: Error, LocalizedError {
    case invalidResponse
    case unauthorized
    case clientBlocked
    case noIPAssignment
    case noCA
    case serverError(Int, String)
    
    var errorDescription: String? {
        switch self {
        case .invalidResponse:
            return "Invalid response from server"
        case .unauthorized:
            return "Invalid client token"
        case .clientBlocked:
            return "Client is blocked on server"
        case .noIPAssignment:
            return "Client has no IP assignment"
        case .noCA:
            return "Server CA not configured"
        case .serverError(let code, let message):
            return "Server error (\(code)): \(message)"
        }
    }
}
