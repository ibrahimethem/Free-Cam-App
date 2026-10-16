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
    private let colorSpace = CGColorSpaceCreateDeviceRGB()
    private var endpoint: URL?
    private var token = ""
    private var active = false
    private var uploadsInFlight = 0
    private var generation = 0
    private var nextUploadID = 0
    private var frameSequence = 0
    private var frameSession = UUID().uuidString
    private var publishedLive = false
    private var jpegQuality: CGFloat = 0.55
    private var tasks: [Int: URLSessionDataTask] = [:]
    private var usb: USBChannel?
    private lazy var client: URLSession = {
        let config = URLSessionConfiguration.ephemeral
        config.timeoutIntervalForRequest = 4
        config.timeoutIntervalForResource = 5
        config.httpMaximumConnectionsPerHost = 2
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

    func start(connection: ReceiverConnection?, key: String) {
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
                        try self.capture.configure(delegate: self)
                        self.endpoint = connection?.url.appendingPathComponent("frame")
                        self.token = key
                        self.active = true
                        self.uploadsInFlight = 0
                        self.frameSequence = 0
                        self.frameSession = UUID().uuidString
                        self.publishedLive = false
                        self.jpegQuality = 0.55
                        self.capture.enableMultitaskingCameraAccessWhenSupported()
                        self.capture.start()
                        if let connection {
                            self.controls.start(connection: connection)
                            self.publish("Connecting to receiver...", streaming: true)
                        } else {
                            let usb = USBChannel(queue: self.queue, capture: self.capture,
                                                 status: self.onStatus)
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
            self.tasks.values.forEach { $0.cancel() }
            self.tasks.removeAll()
            self.controls.stop()
            self.usb?.stop()
            self.usb = nil
            self.uploadsInFlight = 0
            self.capture.stop()
            self.publish("Stopped", streaming: false)
        }
    }

    func resumeCaptureIfNeeded() {
        queue.async {
            guard self.active, !self.capture.session.isRunning else { return }
            self.publish("Resuming camera...", streaming: true)
            self.capture.start()
        }
    }

    func captureOutput(_ output: AVCaptureOutput, didOutput sampleBuffer: CMSampleBuffer,
                       from connection: AVCaptureConnection) {
        guard active else { return }
        guard uploadsInFlight < 2, usb == nil || usb?.canSendFrame == true else { return }
        guard let pixelBuffer = CMSampleBufferGetImageBuffer(sampleBuffer) else { return }
        guard let jpeg = context.jpegRepresentation(of: CIImage(cvPixelBuffer: pixelBuffer),
                  colorSpace: colorSpace,
                  options: [CIImageRepresentationOption(rawValue: kCGImageDestinationLossyCompressionQuality as String): jpegQuality]) else { return }
        adaptJPEGQuality(afterEncoding: jpeg.count)
        if let usb { usb.sendFrame(jpeg); return }
        guard let endpoint else { return }
        uploadsInFlight += 1
        frameSequence += 1
        nextUploadID += 1
        let uploadID = nextUploadID
        let currentGeneration = generation
        var request = URLRequest(url: endpoint)
        request.httpMethod = "POST"
        request.setValue("image/jpeg", forHTTPHeaderField: "Content-Type")
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        request.setValue(frameSession, forHTTPHeaderField: "X-NoSub-Frame-Session")
        request.setValue(String(frameSequence), forHTTPHeaderField: "X-NoSub-Frame-Sequence")
        request.httpBody = jpeg
        let task = client.dataTask(with: request) { _, response, error in
            self.queue.async {
                guard currentGeneration == self.generation else { return }
                self.tasks.removeValue(forKey: uploadID)
                self.uploadsInFlight = max(0, self.uploadsInFlight - 1)
                let code = (response as? HTTPURLResponse)?.statusCode
                if code == 204 {
                    if !self.publishedLive {
                        self.publishedLive = true
                        self.publish("Live  -  sending video", streaming: true)
                    }
                } else if code == 401 {
                    self.active = false
                    self.tasks.values.forEach { $0.cancel() }
                    self.tasks.removeAll()
                    self.uploadsInFlight = 0
                    self.controls.stop()
                    self.capture.stop()
                    self.publish("Pairing key rejected. Check the desktop app.", streaming: false)
                } else {
                    self.publishedLive = false
                    self.publish(error == nil ? "Receiver returned \(code ?? 0). Retrying..." : "Receiver unreachable. Retrying...", streaming: true)
                }
            }
        }
        tasks[uploadID] = task
        task.resume()
    }

    private func adaptJPEGQuality(afterEncoding byteCount: Int) {
        // Detailed or noisy scenes produce much larger JPEGs than dark/static
        // scenes. Keep a stable bandwidth envelope so a sudden camera move does
        // not fill the transport and collapse the delivered frame rate.
        let targetBitsPerSecond = usb == nil ? 36_000_000 : 96_000_000
        let targetBytes = targetBitsPerSecond / 8 / max(capture.frameRate, 1)
        if byteCount > targetBytes * 11 / 10 {
            jpegQuality = max(0.28, jpegQuality * 0.88)
        } else if byteCount < targetBytes * 7 / 10 {
            // Recover detail slowly after the scene becomes easier to encode;
            // this prevents the next sudden move from creating a large spike.
            jpegQuality = min(0.62, jpegQuality + 0.004)
        }
    }

    private func publish(_ message: String, streaming: Bool) {
        onStatus(message, streaming)
    }
}
