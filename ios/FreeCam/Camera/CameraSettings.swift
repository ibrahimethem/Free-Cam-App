import AVFoundation

enum CameraFrameRates {
    static let choices = [24, 30, 60]

    static func supported(by device: AVCaptureDevice, resolution: String) -> [Int] {
        guard let dimensions = dimensions(for: resolution) else { return [] }
        return choices.filter { frameRate in
            device.formats.contains { format in
                matches(format, dimensions: dimensions, frameRate: frameRate)
            }
        }
    }

    static func format(for device: AVCaptureDevice, resolution: String,
                       frameRate: Int) -> AVCaptureDevice.Format? {
        guard choices.contains(frameRate), let dimensions = dimensions(for: resolution) else { return nil }
        if matches(device.activeFormat, dimensions: dimensions, frameRate: frameRate) {
            return device.activeFormat
        }
        let candidates = device.formats.filter {
            matches($0, dimensions: dimensions, frameRate: frameRate)
        }
        // Avoid high-speed/binned formats when a conventional format can provide
        // the requested rate. Among equivalent formats, choose the lowest ceiling.
        return candidates.min {
            if $0.isVideoBinned != $1.isVideoBinned { return !$0.isVideoBinned }
            return maximumFrameRate($0) < maximumFrameRate($1)
        }
    }

    private static func dimensions(for resolution: String) -> CMVideoDimensions? {
        guard let choice = CameraResolution.choices.first(where: { $0.id == resolution }) else { return nil }
        return CMVideoDimensions(width: Int32(choice.width), height: Int32(choice.height))
    }

    private static func matches(_ format: AVCaptureDevice.Format,
                                dimensions: CMVideoDimensions, frameRate: Int) -> Bool {
        let actual = CMVideoFormatDescriptionGetDimensions(format.formatDescription)
        return actual.width == dimensions.width && actual.height == dimensions.height
            && format.videoSupportedFrameRateRanges.contains {
                $0.minFrameRate <= Double(frameRate) && $0.maxFrameRate >= Double(frameRate)
            }
    }

    private static func maximumFrameRate(_ format: AVCaptureDevice.Format) -> Double {
        format.videoSupportedFrameRateRanges.map(\.maxFrameRate).max() ?? 0
    }
}

struct CameraRange: Codable {
    let min: Double
    let max: Double

    func contains(_ value: Double) -> Bool {
        value.isFinite && value >= min && value <= max
    }
}

struct CameraCapabilities: Encodable {
    let cameraPositions: [String]
    let orientations = ["landscape", "portrait"]
    let manualExposure: Bool
    let autoExposure: Bool
    let manualFocus: Bool
    let autoFocus: Bool
    let manualWhiteBalance: Bool
    let autoWhiteBalance: Bool
    let canZoom: Bool
    let iso: CameraRange
    let shutterMs: CameraRange
    let focus: CameraRange
    // Temperature and tint are UI ranges, not sensor-specified ranges.
    // Converted gains are bounded separately to the camera's hardware limits.
    let temperature = CameraRange(min: 2000, max: 10000)
    let tint = CameraRange(min: -150, max: 150)
    let zoom: CameraRange
    let resolutions: [CameraResolution]
    let frameRates: [Int]

    init(device: AVCaptureDevice, resolution: String? = nil) {
        cameraPositions = [("rear", AVCaptureDevice.Position.back),
                           ("front", AVCaptureDevice.Position.front)].compactMap { name, position in
            AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: position) == nil ? nil : name
        }
        resolutions = CameraResolution.supported(by: device)
        let activeDimensions = CMVideoFormatDescriptionGetDimensions(device.activeFormat.formatDescription)
        let activeResolution = resolution ?? "\(activeDimensions.width)x\(activeDimensions.height)"
        frameRates = CameraFrameRates.supported(by: device, resolution: activeResolution)
        manualExposure = device.isExposureModeSupported(.custom)
        autoExposure = device.isExposureModeSupported(.continuousAutoExposure)
        manualFocus = device.isFocusModeSupported(.locked) && device.isLockingFocusWithCustomLensPositionSupported
        autoFocus = device.isFocusModeSupported(.continuousAutoFocus)
        manualWhiteBalance = device.isWhiteBalanceModeSupported(.locked) && device.isLockingWhiteBalanceWithCustomDeviceGainsSupported
        autoWhiteBalance = device.isWhiteBalanceModeSupported(.continuousAutoWhiteBalance)
        iso = CameraRange(min: Double(device.activeFormat.minISO), max: Double(device.activeFormat.maxISO))
        shutterMs = CameraRange(min: device.activeFormat.minExposureDuration.seconds * 1000,
                                max: device.activeFormat.maxExposureDuration.seconds * 1000)
        focus = CameraRange(min: 0, max: 1)
        zoom = CameraRange(min: Double(device.minAvailableVideoZoomFactor),
                           max: Double(device.maxAvailableVideoZoomFactor))
        canZoom = zoom.max > zoom.min
    }
}

struct CameraReadings: Encodable {
    let cameraPosition: String
    let orientation: String
    let resolution: String
    let frameRate: Int
    let exposureAuto: Bool
    let iso: Double
    let shutterMs: Double
    let focusAuto: Bool
    let focus: Double
    let whiteBalanceAuto: Bool
    let temperature: Double
    let tint: Double
    let zoom: Double

    static func safeWhiteBalanceGains(
        _ gains: AVCaptureDevice.WhiteBalanceGains,
        maximum: Float
    ) -> AVCaptureDevice.WhiteBalanceGains {
        let upper = maximum.isFinite ? max(maximum, 1) : 1
        func bounded(_ value: Float) -> Float {
            guard value.isFinite else { return 1 }
            return min(max(value, 1), upper)
        }
        return .init(redGain: bounded(gains.redGain),
                     greenGain: bounded(gains.greenGain),
                     blueGain: bounded(gains.blueGain))
    }

    init(device: AVCaptureDevice, resolution: String, frameRate: Int,
         cameraPosition: String, orientation: String) {
        self.cameraPosition = cameraPosition
        self.orientation = orientation
        self.resolution = resolution
        self.frameRate = frameRate
        exposureAuto = device.exposureMode != .custom && device.exposureMode != .locked
        iso = Double(device.iso)
        shutterMs = device.exposureDuration.seconds * 1000
        focusAuto = device.focusMode != .locked
        focus = Double(device.lensPosition)
        whiteBalanceAuto = device.whiteBalanceMode != .locked
        // During camera/format switches AVFoundation can briefly expose gains
        // outside 1...maxWhiteBalanceGain. Passing those values back into the
        // conversion API raises an Objective-C exception instead of Swift Error.
        let safeGains = Self.safeWhiteBalanceGains(device.deviceWhiteBalanceGains,
                                                   maximum: device.maxWhiteBalanceGain)
        let values = device.temperatureAndTintValues(for: safeGains)
        temperature = Double(values.temperature)
        tint = Double(values.tint)
        zoom = Double(device.videoZoomFactor)
    }
}

struct DesiredCameraSettings: Codable {
    let cameraPosition: String?
    let orientation: String?
    let resolution: String?
    let frameRate: Int?
    let exposureAuto: Bool?
    let iso: Double?
    let shutterMs: Double?
    let focusAuto: Bool?
    let focus: Double?
    let whiteBalanceAuto: Bool?
    let temperature: Double?
    let tint: Double?
    let zoom: Double?

    init(cameraPosition: String? = nil, orientation: String? = nil,
         resolution: String? = nil, frameRate: Int? = nil,
         exposureAuto: Bool? = nil, iso: Double? = nil, shutterMs: Double? = nil,
         focusAuto: Bool? = nil, focus: Double? = nil,
         whiteBalanceAuto: Bool? = nil, temperature: Double? = nil,
         tint: Double? = nil, zoom: Double? = nil) {
        self.cameraPosition = cameraPosition
        self.orientation = orientation
        self.resolution = resolution
        self.frameRate = frameRate
        self.exposureAuto = exposureAuto
        self.iso = iso
        self.shutterMs = shutterMs
        self.focusAuto = focusAuto
        self.focus = focus
        self.whiteBalanceAuto = whiteBalanceAuto
        self.temperature = temperature
        self.tint = tint
        self.zoom = zoom
    }

    static func sensorSnapshot(device: AVCaptureDevice) -> DesiredCameraSettings {
        let readings = CameraReadings(device: device, resolution: "cached", frameRate: 30,
                                      cameraPosition: "cached", orientation: "cached")
        return DesiredCameraSettings(
            exposureAuto: readings.exposureAuto,
            iso: readings.iso,
            shutterMs: readings.shutterMs,
            focusAuto: readings.focusAuto,
            focus: readings.focus,
            whiteBalanceAuto: readings.whiteBalanceAuto,
            temperature: readings.temperature,
            tint: readings.tint,
            zoom: readings.zoom
        )
    }

    func apply(to device: AVCaptureDevice) throws {
        let caps = CameraCapabilities(device: device)
        func require(_ condition: Bool, _ message: String) throws {
            if !condition {
                throw NSError(domain: "FreeCam.Settings", code: 1,
                              userInfo: [NSLocalizedDescriptionKey: message])
            }
        }
        // Validate the whole command before changing any hardware property.
        if let auto = exposureAuto {
            try require(auto ? caps.autoExposure : caps.manualExposure, "Exposure mode unsupported.")
            if !auto {
                try require(iso.map(caps.iso.contains) == true && shutterMs.map(caps.shutterMs.contains) == true,
                            "ISO or shutter is outside this camera's range.")
            }
        }
        if let auto = focusAuto {
            try require(auto ? caps.autoFocus : caps.manualFocus, "Focus mode unsupported.")
            if !auto { try require(focus.map(caps.focus.contains) == true, "Focus is outside this camera's range.") }
        }
        if let auto = whiteBalanceAuto {
            try require(auto ? caps.autoWhiteBalance : caps.manualWhiteBalance, "White balance mode unsupported.")
            if !auto {
                try require(temperature.map(caps.temperature.contains) == true && tint.map(caps.tint.contains) == true,
                            "White balance is outside the supported range.")
            }
        }
        if let zoom { try require(caps.canZoom && caps.zoom.contains(zoom), "Zoom is outside this camera's range.") }
        var gains: AVCaptureDevice.WhiteBalanceGains?
        if whiteBalanceAuto == false, let temperature, let tint {
            let converted = device.deviceWhiteBalanceGains(for: .init(temperature: Float(temperature), tint: Float(tint)))
            try require(converted.redGain.isFinite && converted.greenGain.isFinite && converted.blueGain.isFinite,
                        "White balance conversion failed.")
            func bound(_ gain: Float) -> Float { min(max(gain, 1), device.maxWhiteBalanceGain) }
            gains = .init(redGain: bound(converted.redGain), greenGain: bound(converted.greenGain),
                          blueGain: bound(converted.blueGain))
        }
        try device.lockForConfiguration()
        defer { device.unlockForConfiguration() }
        if let auto = exposureAuto {
            if auto { device.exposureMode = .continuousAutoExposure }
            else if let iso, let shutterMs {
                var duration = CMTime(seconds: shutterMs / 1000, preferredTimescale: 1_000_000_000)
                // Preserve inclusive hardware boundaries after time-base rounding.
                if CMTimeCompare(duration, device.activeFormat.minExposureDuration) < 0 {
                    duration = device.activeFormat.minExposureDuration
                }
                if CMTimeCompare(duration, device.activeFormat.maxExposureDuration) > 0 {
                    duration = device.activeFormat.maxExposureDuration
                }
                device.setExposureModeCustom(duration: duration, iso: Float(iso), completionHandler: nil)
            }
        }
        if let auto = focusAuto {
            if auto { device.focusMode = .continuousAutoFocus }
            else if let focus { device.setFocusModeLocked(lensPosition: Float(focus), completionHandler: nil) }
        }
        if let auto = whiteBalanceAuto {
            if auto { device.whiteBalanceMode = .continuousAutoWhiteBalance }
            else if let gains { device.setWhiteBalanceModeLocked(with: gains, completionHandler: nil) }
        }
        if let zoom { device.videoZoomFactor = CGFloat(zoom) }
    }
}
