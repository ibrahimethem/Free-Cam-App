import AVFoundation

// All methods and device reads run on the streaming engine's serial queue.
final class CameraCapture {
    private static let cachedSensorSettingsKey = "cachedSensorSettings.v1"
    let session = AVCaptureSession()
    private let queue: DispatchQueue
    private let output = AVCaptureVideoDataOutput()
    private var device: AVCaptureDevice?
    private var currentResolution = "1280x720"
    private var currentFrameRate = 30
    private var currentPosition = "rear"
    // AVCapture's native, unrotated video buffer is landscape. Keep that as the
    // default to preserve the camera's 16:9 field of view and avoid a per-frame
    // pixel rotation in the common webcam setup.
    private var currentOrientation = "landscape"
    var frameRate: Int { currentFrameRate }

    init(queue: DispatchQueue) { self.queue = queue }

    func configure(delegate: AVCaptureVideoDataOutputSampleBufferDelegate) throws {
        session.beginConfiguration()
        var committed = false
        defer {
            if !committed { session.commitConfiguration() }
        }
        session.inputs.forEach { session.removeInput($0) }
        session.outputs.forEach { session.removeOutput($0) }
        session.sessionPreset = .hd1280x720
        currentResolution = "1280x720"
        currentFrameRate = 30
        currentPosition = "rear"
        currentOrientation = "landscape"
        guard let device = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video,
                                                   position: .back) else {
            throw NSError(domain: "FreeCam", code: 1, userInfo: [NSLocalizedDescriptionKey: "Camera unavailable."])
        }
        let input = try AVCaptureDeviceInput(device: device)
        guard session.canAddInput(input), session.canAddOutput(output) else {
            throw NSError(domain: "FreeCam", code: 2, userInfo: [NSLocalizedDescriptionKey: "Cannot configure camera."])
        }
        session.addInput(input)
        self.device = device
        output.alwaysDiscardsLateVideoFrames = true
        // The camera produces YUV natively. Keeping that format avoids a costly
        // full-resolution BGRA conversion before Core Image encodes the JPEG.
        let preferredPixelFormat = kCVPixelFormatType_420YpCbCr8BiPlanarFullRange
        let pixelFormat = output.availableVideoPixelFormatTypes.contains(preferredPixelFormat)
            ? preferredPixelFormat : kCVPixelFormatType_32BGRA
        output.videoSettings = [kCVPixelBufferPixelFormatTypeKey as String: pixelFormat]
        output.setSampleBufferDelegate(delegate, queue: queue)
        session.addOutput(output)
        session.commitConfiguration()
        committed = true
        try setFrameRate(currentFrameRate, device: device)
        try setOutputOrientation("landscape")
        restoreSensorSettings(on: device)
    }

    func start() { session.startRunning() }

    func enableMultitaskingCameraAccessWhenSupported() {
        if session.isMultitaskingCameraAccessSupported {
            session.isMultitaskingCameraAccessEnabled = true
        }
    }

    func stop() {
        if session.isRunning { session.stopRunning() }
    }

    func report(session id: String, revision: Int, error: String) -> CameraReport? {
        guard let device else { return nil }
        return CameraReport(session: id,
                            capabilities: CameraCapabilities(device: device, resolution: currentResolution),
                            current: CameraReadings(device: device, resolution: currentResolution,
                                                    frameRate: currentFrameRate,
                                                    cameraPosition: currentPosition,
                                                    orientation: currentOrientation),
                            appliedRevision: revision, error: error)
    }

    func apply(_ settings: DesiredCameraSettings) throws {
        if let position = settings.cameraPosition { try setCameraPosition(position) }
        guard let device else { return }
        if let resolution = settings.resolution { try setResolution(resolution, device: device) }
        if let frameRate = settings.frameRate { try setFrameRate(frameRate, device: device) }
        if let orientation = settings.orientation { try setOutputOrientation(orientation) }
        try settings.apply(to: device)
        persistSensorSettings(from: device)
    }

    private func setCameraPosition(_ value: String) throws {
        guard value != currentPosition else { return }
        let position: AVCaptureDevice.Position
        switch value {
        case "rear": position = .back
        case "front": position = .front
        default:
            throw NSError(domain: "FreeCam.Camera", code: 1,
                          userInfo: [NSLocalizedDescriptionKey: "Camera position is unsupported."])
        }
        guard let nextDevice = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video,
                                                        position: position) else {
            throw NSError(domain: "FreeCam.Camera", code: 2,
                          userInfo: [NSLocalizedDescriptionKey: "Selected camera is unavailable."])
        }
        let nextInput = try AVCaptureDeviceInput(device: nextDevice)
        let previousInput = session.inputs.compactMap { $0 as? AVCaptureDeviceInput }.first
        session.beginConfiguration()
        if let previousInput { session.removeInput(previousInput) }
        guard session.canAddInput(nextInput) else {
            if let previousInput, session.canAddInput(previousInput) { session.addInput(previousInput) }
            session.commitConfiguration()
            throw NSError(domain: "FreeCam.Camera", code: 3,
                          userInfo: [NSLocalizedDescriptionKey: "Cannot switch camera."])
        }
        session.addInput(nextInput)
        session.sessionPreset = .hd1280x720
        session.commitConfiguration()
        device = nextDevice
        currentPosition = value
        currentResolution = "1280x720"
        currentFrameRate = 30
        try setFrameRate(currentFrameRate, device: nextDevice)
        try setOutputOrientation(currentOrientation)
    }

    private func setOutputOrientation(_ value: String) throws {
        let angle: CGFloat
        switch value {
        case "landscape": angle = 0 // Native sensor orientation; no pixel rotation.
        case "portrait": angle = 90
        default:
            throw NSError(domain: "FreeCam.Orientation", code: 1,
                          userInfo: [NSLocalizedDescriptionKey: "Output orientation is unsupported."])
        }
        guard let connection = output.connection(with: .video),
              connection.isVideoRotationAngleSupported(angle) else {
            throw NSError(domain: "FreeCam.Orientation", code: 2,
                          userInfo: [NSLocalizedDescriptionKey: "Output rotation is unavailable."])
        }
        connection.videoRotationAngle = angle
        currentOrientation = value
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
        currentFrameRate = 30
        try setFrameRate(currentFrameRate, device: device)
        try setOutputOrientation(currentOrientation)
    }

    private func setFrameRate(_ frameRate: Int, device: AVCaptureDevice) throws {
        guard let format = CameraFrameRates.format(for: device, resolution: currentResolution,
                                                   frameRate: frameRate) else {
            throw NSError(domain: "FreeCam.FrameRate", code: 1,
                          userInfo: [NSLocalizedDescriptionKey:
                                     "\(frameRate) FPS is unavailable at \(currentResolution)."])
        }
        let duration = CMTime(value: 1, timescale: CMTimeScale(frameRate))
        if session.sessionPreset != .inputPriority {
            session.beginConfiguration()
            session.sessionPreset = .inputPriority
            session.commitConfiguration()
        }
        if device.activeFormat == format,
           CMTimeCompare(device.activeVideoMinFrameDuration, duration) == 0,
           CMTimeCompare(device.activeVideoMaxFrameDuration, duration) == 0 {
            currentFrameRate = frameRate
            return
        }
        try device.lockForConfiguration()
        device.activeFormat = format
        device.activeVideoMinFrameDuration = duration
        device.activeVideoMaxFrameDuration = duration
        device.unlockForConfiguration()
        currentFrameRate = frameRate
    }

    private func restoreSensorSettings(on device: AVCaptureDevice) {
        let defaults = UserDefaults.standard
        guard let data = defaults.data(forKey: Self.cachedSensorSettingsKey),
              let settings = try? JSONDecoder().decode(DesiredCameraSettings.self, from: data) else {
            return
        }
        do {
            try settings.apply(to: device)
        } catch {
            // Hardware ranges can change across devices or iOS updates. Invalid
            // cached values are discarded instead of blocking camera startup.
            defaults.removeObject(forKey: Self.cachedSensorSettingsKey)
        }
    }

    private func persistSensorSettings(from device: AVCaptureDevice) {
        let snapshot = DesiredCameraSettings.sensorSnapshot(device: device)
        guard let data = try? JSONEncoder().encode(snapshot) else { return }
        UserDefaults.standard.set(data, forKey: Self.cachedSensorSettingsKey)
    }

}
