import Foundation

struct CameraReport: Encodable {
    let session: String
    let capabilities: CameraCapabilities
    let current: CameraReadings
    let appliedRevision: Int
    let error: String
}

struct CameraCommand: Decodable {
    let revision: Int
    let settings: DesiredCameraSettings
}
