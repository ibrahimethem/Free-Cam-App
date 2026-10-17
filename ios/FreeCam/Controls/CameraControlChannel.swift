import Foundation

// Periodic telemetry, command delivery and acknowledgements share the capture queue.
final class CameraControlChannel {
    private let queue: DispatchQueue
    private let capture: CameraCapture
    private var connection: ReceiverConnection?
    private var generation = 0
    private var controlTimer: DispatchSourceTimer?
    private var controlTask: URLSessionDataTask?
    private var captureID = ""
    private var appliedRevision = 0
    private var controlError = ""
    private var pollingControls = false
    private lazy var controlClient: URLSession = {
        let config = URLSessionConfiguration.ephemeral
        config.timeoutIntervalForRequest = 3
        config.timeoutIntervalForResource = 4
        return URLSession(configuration: config)
    }()

    init(queue: DispatchQueue, capture: CameraCapture) {
        self.queue = queue
        self.capture = capture
    }

    func start(connection: ReceiverConnection) {
        stop()
        self.connection = connection
        generation += 1
        captureID = UUID().uuidString
        appliedRevision = 0
        controlError = ""
        let timer = DispatchSource.makeTimerSource(queue: queue)
        timer.schedule(deadline: .now(), repeating: .milliseconds(500))
        timer.setEventHandler { [weak self] in self?.exchangeControls() }
        controlTimer = timer
        timer.resume()
    }

    func stop() {
        generation += 1
        connection = nil
        controlTimer?.cancel()
        controlTimer = nil
        controlTask?.cancel()
        controlTask = nil
        pollingControls = false
    }

    private func exchangeControls() {
        guard !pollingControls, let connection,
              let report = capture.report(session: captureID, revision: appliedRevision,
                                          error: controlError) else { return }
        guard let data = try? JSONEncoder().encode(report) else { return }
        var request = connection.request(path: "camera", contentType: "application/json")
        request.httpBody = data
        pollingControls = true
        let currentGeneration = generation
        let currentCaptureID = captureID
        controlTask = controlClient.dataTask(with: request) { data, response, _ in
            self.queue.async {
                guard currentGeneration == self.generation, currentCaptureID == self.captureID, self.connection != nil else { return }
                self.pollingControls = false
                guard (response as? HTTPURLResponse)?.statusCode == 200, let data,
                      let command = try? JSONDecoder().decode(CameraCommand.self, from: data) else { return }
                // A receiver restart resets revisions but keeps the saved pairing key.
                guard command.revision > self.appliedRevision else { return }
                do {
                    try self.capture.apply(command.settings)
                    self.controlError = ""
                } catch {
                    self.controlError = error.localizedDescription
                }
                // Acknowledge processing, including errors; readings report the actual hardware state.
                self.appliedRevision = command.revision
            }
        }
        controlTask?.resume()
    }

}
