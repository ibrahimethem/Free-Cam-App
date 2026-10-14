import AVFoundation

struct CameraResolution: Encodable {
    let id: String
    let label: String
    let width: Int
    let height: Int

    var preset: AVCaptureSession.Preset {
        switch id {
        case "640x480": return .vga640x480
        case "1280x720": return .hd1280x720
        case "1920x1080": return .hd1920x1080
        default: return .hd4K3840x2160
        }
    }

    static let choices: [CameraResolution] = [
        .init(id: "640x480", label: "480p  -  640 × 480", width: 640, height: 480),
        .init(id: "1280x720", label: "720p  -  1280 × 720", width: 1280, height: 720),
        .init(id: "1920x1080", label: "1080p  -  1920 × 1080", width: 1920, height: 1080),
        .init(id: "3840x2160", label: "4K  -  3840 × 2160", width: 3840, height: 2160)
    ]

    static func supported(by device: AVCaptureDevice) -> [CameraResolution] {
        choices.filter { device.supportsSessionPreset($0.preset) }
    }
}
