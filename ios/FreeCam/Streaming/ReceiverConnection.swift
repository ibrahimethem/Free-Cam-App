import Foundation

struct ReceiverConnection {
    let url: URL
    let key: String

    init(address: String, key: String) throws {
        let address = address.trimmingCharacters(in: .whitespacesAndNewlines)
        let key = key.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let url = URL(string: address), let host = url.host,
              url.scheme == "http", Self.isLocalHost(host), url.user == nil, url.password == nil,
              url.query == nil, url.fragment == nil, url.path.isEmpty || url.path == "/",
              !key.isEmpty else { throw ConnectionError.invalidAddress }
        self.url = url
        self.key = key
    }

    func request(path: String, contentType: String) -> URLRequest {
        var request = URLRequest(url: url.appendingPathComponent(path))
        request.httpMethod = "POST"
        request.setValue(contentType, forHTTPHeaderField: "Content-Type")
        request.setValue("Bearer \(key)", forHTTPHeaderField: "Authorization")
        return request
    }

    private static func isLocalHost(_ host: String) -> Bool {
        if host.lowercased().hasSuffix(".local") { return true }
        let components = host.split(separator: ".", omittingEmptySubsequences: false)
        let parts = components.compactMap { Int($0) }
        guard components.count == 4, parts.count == 4,
              parts.allSatisfy({ (0...255).contains($0) }) else { return false }
        return parts[0] == 10 || (parts[0] == 192 && parts[1] == 168)
            || (parts[0] == 172 && (16...31).contains(parts[1]))
    }

    enum ConnectionError: LocalizedError {
        case invalidAddress
        var errorDescription: String? { "Enter a local receiver address and pairing key." }
    }
}
