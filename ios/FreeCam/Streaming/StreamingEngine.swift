import AVFoundation
import CoreImage
import ImageIO

// Capture, encoding and network completion state are confined to one serial queue.
final class StreamingEngine: NSObject, AVCaptureVideoDataOutputSampleBufferDelegate {
    private let queue: DispatchQueue
    private let capture: CameraCapture
    private let controls: CameraControlChannel
    private let onStatus: (String, Bool) -> Void
    var session: AVCaptureSession { capture.session }
    private let context = CIContext()
    private var endpoint: URL?
    private var token = ""
    private var active = false
    private var uploading = false
    private var generation = 0
    private var lastSent = 0.0
    private var task: URLSessionDataTask?
    private var usb: USBChannel?
    private lazy var client: URLSession = {
        let config = URLSessionConfiguration.ephemeral
        config.timeoutIntervalForRequest = 4
        config.timeoutIntervalForResource = 5
        config.httpMaximumConnectionsPerHost = 1
        return URLSession(configuration: config)
    }()

    init(onStatus: @escaping (String, Bool) -> Void) {
        let queue = DispatchQueue(label: "freecam.capture")
        self.queue = queue
        let capture = CameraCapture(queue: queue)
        self.capture = capture
        controls = CameraControlChannel(queue: queue, capture: capture)
        self.onStatus = onStatus
        super.init()
    }

    func start(connection: ReceiverConnection?, key: String, front: Bool) {
        publish("Requesting camera...", streaming: true)
        queue.async {
            self.generation += 1
            let requestedGeneration = self.generation
            AVCaptureDevice.requestAccess(for: .video) { granted in
                self.queue.async {
                    guard requestedGeneration == self.generation else { return }
                    guard granted else {
                        self.publish("Allow camera access in Settings to continue.", streaming: false)
                        return
                    }
                    do {
                        try self.capture.configure(front: front, delegate: self)
                        self.endpoint = connection?.url.appendingPathComponent("frame")
                        self.token = key
                        self.active = true
                        self.lastSent = 0
                        self.capture.start()
                        if let connection {
                            self.controls.start(connection: connection)
                            self.publish("Connecting to receiver...", streaming: true)
                        } else {
                            let usb = USBChannel(queue: self.queue, capture: self.capture, status: self.onStatus)
                            self.usb = usb
                            try usb.start(key: key)
                        }
                    } catch {
                        self.active = false
                        self.usb?.stop()
                        self.usb = nil
                        self.capture.stop()
                        self.publish(error.localizedDescription, streaming: false)
                    }
                }
            }
        }
    }

    func stop() {
        publish("Stopped", streaming: false)
        queue.async {
            self.generation += 1
            self.active = false
            self.task?.cancel()
            self.task = nil
            self.controls.stop()
            self.usb?.stop()
            self.usb = nil
            self.uploading = false
            self.capture.stop()
            self.publish("Stopped", streaming: false)
        }
    }

    func captureOutput(_ output: AVCaptureOutput, didOutput sampleBuffer: CMSampleBuffer,
                       from connection: AVCaptureConnection) {
        let now = ProcessInfo.processInfo.systemUptime
        guard active, !uploading, now - lastSent >= 1.0 / 24,
              usb == nil || usb?.canSendFrame == true,
              let pixelBuffer = CMSampleBufferGetImageBuffer(sampleBuffer),
              let jpeg = context.jpegRepresentation(of: CIImage(cvPixelBuffer: pixelBuffer),
                  colorSpace: CGColorSpaceCreateDeviceRGB(),
                  options: [CIImageRepresentationOption(rawValue: kCGImageDestinationLossyCompressionQuality as String): 0.65]) else { return }
        lastSent = now
        if let usb { usb.sendFrame(jpeg); return }
        guard let endpoint else { return }
        uploading = true
        let currentGeneration = generation
        var request = URLRequest(url: endpoint)
        request.httpMethod = "POST"
        request.setValue("image/jpeg", forHTTPHeaderField: "Content-Type")
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        request.httpBody = jpeg
        task = client.dataTask(with: request) { _, response, error in
            self.queue.async {
                guard currentGeneration == self.generation else { return }
                self.uploading = false
                let code = (response as? HTTPURLResponse)?.statusCode
                if code == 204 { self.publish("Live  -  sending video", streaming: true) }
                else if code == 401 {
                    self.active = false
                    self.controls.stop()
                    self.capture.stop()
                    self.publish("Pairing key rejected. Check the desktop app.", streaming: false)
                } else {
                    self.publish(error == nil ? "Receiver returned \(code ?? 0). Retrying..." : "Receiver unreachable. Retrying...", streaming: true)
                }
            }
        }
        task?.resume()
    }

    private func publish(_ message: String, streaming: Bool) {
        onStatus(message, streaming)
    }
}
