import Foundation
import AVFoundation

// Diagnostic only. Installation runs inside the provisioned host app.
let devices = AVCaptureDevice.DiscoverySession(deviceTypes: [.externalUnknown],
    mediaType: .video, position: .unspecified).devices
print(devices.contains { $0.uniqueID == "com.ethem.nosubcam.camera" } ? "available" : "not-installed")
