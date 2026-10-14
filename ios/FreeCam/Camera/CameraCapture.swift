import AVFoundation

// All methods and device reads run on the streaming engine's serial queue.
final class CameraCapture {
    let session = AVCaptureSession()
    private let queue: DispatchQueue
    private let output = AVCaptureVideoDataOutput()
    private var device: AVCaptureDevice?
    private var currentResolution = "1280x720"

    init(queue: DispatchQueue) { self.queue = queue }

    func configure(front: Bool, delegate: AVCaptureVideoDataOutputSampleBufferDelegate) throws {
        session.beginConfiguration()
        defer { session.commitConfiguration() }
        session.inputs.forEach { session.removeInput($0) }
        session.outputs.forEach { session.removeOutput($0) }
        session.sessionPreset = .hd1280x720
        currentResolution = "1280x720"
        guard let device = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video,
                                                   position: front ? .front : .back) else {
            throw NSError(domain: "FreeCam", code: 1, userInfo: [NSLocalizedDescriptionKey: "Camera unavailable."])
        }
        let input = try AVCaptureDeviceInput(device: device)
        guard session.canAddInput(input), session.canAddOutput(output) else {
            throw NSError(domain: "FreeCam", code: 2, userInfo: [NSLocalizedDescriptionKey: "Cannot configure camera."])
        }
        session.addInput(input)
        self.device = device
        output.alwaysDiscardsLateVideoFrames = true
        output.videoSettings = [kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA]
        output.setSampleBufferDelegate(delegate, queue: queue)
        session.addOutput(output)
        if let connection = output.connection(with: .video), connection.isVideoRotationAngleSupported(90) {
            connection.videoRotationAngle = 90
        }
    }

    func start() { session.startRunning() }

    func stop() {
        if session.isRunning { session.stopRunning() }
    }

    func report(session id: String, revision: Int, error: String) -> CameraReport? {
        guard let device else { return nil }
        return CameraReport(session: id, capabilities: CameraCapabilities(device: device),
                            current: CameraReadings(device: device, resolution: currentResolution),
                            appliedRevision: revision, error: error)
    }

    func apply(_ settings: DesiredCameraSettings) throws {
        guard let device else { return }
        if let resolution = settings.resolution { try setResolution(resolution, device: device) }
        try settings.apply(to: device)
    }

    private func setResolution(_ id: String, device: AVCaptureDevice) throws {
        guard id != currentResolution else { return }
        guard let resolution = CameraResolution.supported(by: device).first(where: { $0.id == id }),
              session.canSetSessionPreset(resolution.preset) else {
            throw NSError(domain: "FreeCam.Resolution", code: 1,
                          userInfo: [NSLocalizedDescriptionKey: "Resolution unsupported by this camera."])
        }
        // Reset modes before switching formats so old manual values cannot exceed new limits.
        try device.lockForConfiguration()
        if device.isExposureModeSupported(.continuousAutoExposure) { device.exposureMode = .continuousAutoExposure }
        if device.isFocusModeSupported(.continuousAutoFocus) { device.focusMode = .continuousAutoFocus }
        if device.isWhiteBalanceModeSupported(.continuousAutoWhiteBalance) { device.whiteBalanceMode = .continuousAutoWhiteBalance }
        device.unlockForConfiguration()
        session.beginConfiguration()
        session.sessionPreset = resolution.preset
        session.commitConfiguration()
        currentResolution = id
        if let connection = output.connection(with: .video), connection.isVideoRotationAngleSupported(90) {
            connection.videoRotationAngle = 90
        }
    }

}
