import AVFoundation

struct CameraRange: Codable {
    let min: Double
    let max: Double

    func contains(_ value: Double) -> Bool {
        value.isFinite && value >= min && value <= max
    }
}

struct CameraCapabilities: Encodable {
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

    init(device: AVCaptureDevice) {
        resolutions = CameraResolution.supported(by: device)
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
    let resolution: String
    let exposureAuto: Bool
    let iso: Double
    let shutterMs: Double
    let focusAuto: Bool
    let focus: Double
    let whiteBalanceAuto: Bool
    let temperature: Double
    let tint: Double
    let zoom: Double

    init(device: AVCaptureDevice, resolution: String) {
        self.resolution = resolution
        exposureAuto = device.exposureMode != .custom && device.exposureMode != .locked
        iso = Double(device.iso)
        shutterMs = device.exposureDuration.seconds * 1000
        focusAuto = device.focusMode != .locked
        focus = Double(device.lensPosition)
        whiteBalanceAuto = device.whiteBalanceMode != .locked
        let values = device.temperatureAndTintValues(for: device.deviceWhiteBalanceGains)
        temperature = Double(values.temperature)
        tint = Double(values.tint)
        zoom = Double(device.videoZoomFactor)
    }
}

struct DesiredCameraSettings: Decodable {
    let resolution: String?
    let exposureAuto: Bool?
    let iso: Double?
    let shutterMs: Double?
    let focusAuto: Bool?
    let focus: Double?
    let whiteBalanceAuto: Bool?
    let temperature: Double?
    let tint: Double?
    let zoom: Double?

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
