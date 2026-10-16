import Network

enum LocalNetworkPermissionState: String {
    case unknown
    case requesting
    case allowed
    case denied
}

// iOS has no public Local Network authorization-status API. A user-initiated
// Bonjour browse is the documented local operation that presents the system prompt.
@MainActor
final class LocalNetworkPermissionRequester {
    private let queue = DispatchQueue(label: "nosubcam.local-network-permission")
    private var browser: NWBrowser?
    private var continuation: CheckedContinuation<Bool, Never>?

    func request() async -> Bool {
        cancel(result: false)
        return await withCheckedContinuation { continuation in
            self.continuation = continuation
            let browser = NWBrowser(for: .bonjour(type: "_nosubcam._tcp", domain: nil),
                                    using: .tcp)
            self.browser = browser
            browser.stateUpdateHandler = { [weak self] state in
                Task { @MainActor in self?.handle(state) }
            }
            browser.start(queue: queue)
        }
    }

    private func handle(_ state: NWBrowser.State) {
        switch state {
        case .ready:
            cancel(result: true)
        case .waiting(let error):
            if case .dns(let code) = error,
               code == DNSServiceErrorType(kDNSServiceErr_PolicyDenied) {
                cancel(result: false)
            }
        case .failed:
            cancel(result: false)
        case .cancelled:
            if continuation != nil { cancel(result: false) }
        case .setup:
            break
        @unknown default:
            cancel(result: false)
        }
    }

    private func cancel(result: Bool) {
        browser?.stateUpdateHandler = nil
        browser?.cancel()
        browser = nil
        let pending = continuation
        continuation = nil
        pending?.resume(returning: result)
    }
}
