import Foundation
import Network

// Loopback listener reached through the host's USB multiplexing service.
// State and camera access remain on the engine's serial queue.
final class USBChannel {
    private let queue: DispatchQueue
    private let capture: CameraCapture
    private let status: (String, Bool) -> Void
    private var listener: NWListener?
    private var peer: NWConnection?
    private var timer: DispatchSourceTimer?
    private var authenticated = false
    private var framePending = false
    private var reportPending = false
    private var frameSequence = 0
    private var captureID = ""
    private var revision = 0
    private var commandError = ""
    private var key = ""

    init(queue: DispatchQueue, capture: CameraCapture, status: @escaping (String, Bool) -> Void) {
        self.queue = queue
        self.capture = capture
        self.status = status
    }

    func start(key: String) throws {
        stop()
        self.key = key
        let parameters = NWParameters.tcp
        parameters.requiredLocalEndpoint = .hostPort(host: "127.0.0.1", port: 8766)
        let listener = try NWListener(using: parameters)
        self.listener = listener
        listener.newConnectionHandler = { [weak self] connection in self?.accept(connection) }
        listener.stateUpdateHandler = { [weak self, weak listener] state in
            guard let self, let listener, self.listener === listener else { return }
            if case .failed(let error) = state {
                self.status("USB listener failed: \(error.localizedDescription)", false)
                self.stop()
                self.capture.stop()
            }
        }
        listener.start(queue: queue)
        status("USB ready. Connect from Free Cam on your computer.", true)
    }

    func stop() {
        listener?.cancel()
        listener = nil
        disconnect()
    }

    private func disconnect() {
        peer?.cancel()
        peer = nil
        timer?.cancel()
        timer = nil
        authenticated = false
        framePending = false
        reportPending = false
    }

    private func accept(_ connection: NWConnection) {
        guard peer == nil else { connection.cancel(); return }
        peer = connection
        connection.stateUpdateHandler = { [weak self, weak connection] state in
            guard let self, let connection, self.peer === connection else { return }
            if case .failed = state { self.lost(connection) }
            else if case .cancelled = state { self.lost(connection) }
        }
        connection.start(queue: queue)
        receiveHeader(connection)
        queue.asyncAfter(deadline: .now() + 5) { [weak self, weak connection] in
            guard let self, let connection, self.peer === connection, !self.authenticated else { return }
            self.lost(connection)
        }
    }

    private func lost(_ connection: NWConnection) {
        guard peer === connection else { return }
        disconnect()
        if listener != nil { status("USB disconnected. Reconnect from your computer.", true) }
    }

    private func receiveHeader(_ connection: NWConnection) {
        connection.receive(minimumIncompleteLength: 4, maximumLength: 4) { [weak self] data, _, complete, error in
            guard let self, self.peer === connection else { return }
            guard error == nil, let data, data.count == 4 else { self.lost(connection); return }
            let length = data.reduce(0) { ($0 << 8) | Int($1) }
            guard (1...65537).contains(length) else { self.lost(connection); return }
            connection.receive(minimumIncompleteLength: length, maximumLength: length) { [weak self] data, _, _, error in
                guard let self, self.peer === connection else { return }
                guard error == nil, let data, data.count == length else { self.lost(connection); return }
                self.process(data, connection: connection)
                if self.peer === connection { self.receiveHeader(connection) }
            }
        }
    }

    private func process(_ packet: Data, connection: NWConnection) {
        let body = Data(packet.dropFirst())
        if !authenticated {
            struct Hello: Decodable { let version: Int; let key: String }
            guard packet.first == 1, let hello = try? JSONDecoder().decode(Hello.self, from: body),
                  hello.version == 1, hello.key == key else {
                lost(connection)
                status("USB pairing key rejected. Check the desktop key.", true)
                return
            }
            authenticated = true
            captureID = UUID().uuidString
            revision = 0
            commandError = ""
            send(kind: 5, data: Data(#"{"version":1}"#.utf8), connection: connection)
            let timer = DispatchSource.makeTimerSource(queue: queue)
            timer.schedule(deadline: .now(), repeating: .milliseconds(500))
            timer.setEventHandler { [weak self] in self?.report() }
            self.timer = timer
            timer.resume()
            status("Live - Direct USB", true)
        } else if packet.first == 6 && body.isEmpty {
            framePending = false
        } else if packet.first == 4, let command = try? JSONDecoder().decode(CameraCommand.self, from: body) {
            reportPending = false
            if command.revision > revision {
                do { try capture.apply(command.settings); commandError = "" }
                catch { commandError = error.localizedDescription }
                revision = command.revision
            }
        } else { lost(connection) }
    }

    var canSendFrame: Bool { authenticated && !framePending }

    func sendFrame(_ data: Data) {
        guard canSendFrame, let peer, data.count <= 8_000_000 else { return }
        framePending = true
        frameSequence += 1
        let sentSequence = frameSequence
        send(kind: 2, data: data, connection: peer)
        queue.asyncAfter(deadline: .now() + 5) { [weak self, weak peer] in
            guard let self, let peer, self.peer === peer, self.framePending,
                  self.frameSequence == sentSequence else { return }
            // A stalled desktop must not leave the capture pipeline permanently blocked.
            self.lost(peer)
        }
    }

    private func report() {
        guard authenticated, !reportPending, let peer,
              let report = capture.report(session: captureID, revision: revision, error: commandError),
              let data = try? JSONEncoder().encode(report) else { return }
        reportPending = true
        send(kind: 3, data: data, connection: peer)
    }

    private func send(kind: UInt8, data: Data, connection: NWConnection) {
        let length = UInt32(data.count + 1)
        var packet = Data([UInt8((length >> 24) & 255), UInt8((length >> 16) & 255),
                           UInt8((length >> 8) & 255), UInt8(length & 255), kind])
        packet.append(data)
        connection.send(content: packet, completion: .contentProcessed { [weak self] error in
            if error != nil { self?.lost(connection) }
        })
    }
}
