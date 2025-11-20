import Foundation
import Security
import LocalAuthentication

/// Service for secure storage of client token in macOS Keychain
class KeychainService {
    private let service = "com.managednebula.client"
    private let tokenAccount = "client-token"
    
    /// Save client token to Keychain
    func saveToken(_ token: String) throws {
        let data = token.data(using: .utf8)!
        
        // Delete existing item if present
        let deleteQuery: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: tokenAccount
        ]
        SecItemDelete(deleteQuery as CFDictionary)
        
        // Add new item with accessibility that allows this app to access without prompts
        // Uses WhenUnlockedThisDeviceOnly for security without constant authentication
        let addQuery: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: tokenAccount,
            kSecValueData as String: data,
            kSecAttrAccessible as String: kSecAttrAccessibleWhenUnlockedThisDeviceOnly,
            kSecAttrSynchronizable as String: false
        ]
        
        let status = SecItemAdd(addQuery as CFDictionary, nil)
        guard status == errSecSuccess else {
            throw KeychainError.saveFailed(status)
        }
    }
    
    /// Load client token from Keychain
    func loadToken() throws -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: tokenAccount,
            kSecReturnData as String: true,
            kSecAttrSynchronizable as String: false
        ]
        
        var result: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &result)
        
        if status == errSecItemNotFound {
            return nil
        }
        
        guard status == errSecSuccess,
              let data = result as? Data,
              let token = String(data: data, encoding: .utf8) else {
            throw KeychainError.loadFailed(status)
        }
        
        return token
    }
    
    /// Delete token from Keychain
    func deleteToken() throws {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: tokenAccount
        ]
        
        let status = SecItemDelete(query as CFDictionary)
        guard status == errSecSuccess || status == errSecItemNotFound else {
            throw KeychainError.deleteFailed(status)
        }
    }
}

enum KeychainError: Error {
    case saveFailed(OSStatus)
    case loadFailed(OSStatus)
    case deleteFailed(OSStatus)
    case accessControlFailed(CFError?)
    
    var localizedDescription: String {
        switch self {
        case .saveFailed(let status):
            return "Failed to save token to Keychain (status: \(status))"
        case .loadFailed(let status):
            return "Failed to load token from Keychain (status: \(status))"
        case .deleteFailed(let status):
            return "Failed to delete token from Keychain (status: \(status))"
        case .accessControlFailed(let error):
            if let error = error {
                return "Failed to create keychain access control: \(error.localizedDescription)"
            }
            return "Failed to create keychain access control"
        }
    }
}
