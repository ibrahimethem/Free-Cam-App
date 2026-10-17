import Foundation
import Security

struct SavedPairing: Codable, Equatable {
    let address: String
    let key: String
    let usesUSB: Bool

    init(address: String, key: String, usesUSB: Bool) throws {
        let key = key.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !key.isEmpty, key.count <= 256 else { throw ReceiverConnection.ConnectionError.invalidAddress }
        if !usesUSB { _ = try ReceiverConnection(address: address, key: key) }
        self.address = address.trimmingCharacters(in: .whitespacesAndNewlines)
        self.key = key
        self.usesUSB = usesUSB
    }
}

struct PairingKeychain {
    private let service = "com.ethem.nosubcam.pairing"
    private let account = "last-computer"

    private var query: [String: Any] {
        [kSecClass as String: kSecClassGenericPassword,
         kSecAttrService as String: service, kSecAttrAccount as String: account,
         kSecAttrSynchronizable as String: false]
    }

    func load() throws -> SavedPairing? {
        var request = query
        request[kSecReturnData as String] = true
        request[kSecMatchLimit as String] = kSecMatchLimitOne
        var result: CFTypeRef?
        let status = SecItemCopyMatching(request as CFDictionary, &result)
        if status == errSecItemNotFound { return nil }
        guard status == errSecSuccess, let data = result as? Data else { throw StoreError.unavailable }
        let saved = try JSONDecoder().decode(SavedPairing.self, from: data)
        // Revalidate even a decoded item rather than treating arbitrary stored data as an endpoint.
        return try SavedPairing(address: saved.address, key: saved.key, usesUSB: saved.usesUSB)
    }

    func save(_ pairing: SavedPairing) throws {
        let data = try JSONEncoder().encode(pairing)
        let attributes: [String: Any] = [kSecValueData as String: data,
            kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly]
        let status = SecItemUpdate(query as CFDictionary, attributes as CFDictionary)
        if status == errSecItemNotFound {
            let addition = query.merging(attributes) { _, new in new }
            guard SecItemAdd(addition as CFDictionary, nil) == errSecSuccess else { throw StoreError.unavailable }
        } else if status != errSecSuccess { throw StoreError.unavailable }
    }

    func forget() throws {
        let status = SecItemDelete(query as CFDictionary)
        guard status == errSecSuccess || status == errSecItemNotFound else { throw StoreError.unavailable }
    }

    enum StoreError: LocalizedError {
        case unavailable
        var errorDescription: String? { "Secure pairing storage is unavailable. You can still connect for this session." }
    }
}
