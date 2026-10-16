import Observation
import UIKit

// UI owns this observable session; hardware and networking remain off the main actor.
@MainActor
@Observable
final class StreamingSession {
    private(set) var isStreaming = false
    private(set) var status = "Ready to connect"
    @ObservationIgnored private lazy var engine = StreamingEngine { [weak self] message, streaming in
        DispatchQueue.main.async { [weak self] in
            guard let self else { return }
            self.status = message
            self.isStreaming = streaming
            UIApplication.shared.isIdleTimerDisabled = streaming
        }
    }
    func start(address: String, key: String, usb: Bool) {
        do {
            let key = key.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !key.isEmpty else { throw ReceiverConnection.ConnectionError.invalidAddress }
            let connection: ReceiverConnection?
            if usb { connection = nil }
            else { connection = try ReceiverConnection(address: address, key: key) }
            isStreaming = true
            status = "Requesting camera..."
            UIApplication.shared.isIdleTimerDisabled = true
            engine.start(connection: connection, key: key)
        } catch { status = error.localizedDescription }
    }

    func stop() {
        isStreaming = false
        status = "Stopped"
        UIApplication.shared.isIdleTimerDisabled = false
        engine.stop()
    }

    func resumeIfNeeded() {
        guard isStreaming else { return }
        engine.resumeCaptureIfNeeded()
    }
}
