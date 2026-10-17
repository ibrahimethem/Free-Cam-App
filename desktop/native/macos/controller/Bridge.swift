import Foundation
import SystemExtensions

// Called inside the signed Python app, not an unprovisioned helper process.
public typealias CameraCallback = @convention(c) (Int32, UnsafePointer<CChar>?) -> Void
private var activeRequest: CameraRequest?
private var streamingActivity: NSObjectProtocol?

@_cdecl("nosub_camera_activity")
public func cameraActivity(_ active: Int32) {
    if active != 0, streamingActivity == nil {
        // Avoid App Nap while streaming with the window hidden, without preventing
        // the Mac's normal idle sleep or changing any user power preferences.
        streamingActivity = ProcessInfo.processInfo.beginActivity(
            options: .userInitiatedAllowingIdleSystemSleep, reason: "NoSub Camera video streaming")
    } else if active == 0, let activity = streamingActivity {
        ProcessInfo.processInfo.endActivity(activity)
        streamingActivity = nil
    }
}

private final class CameraRequest: NSObject, OSSystemExtensionRequestDelegate {
    let callback: CameraCallback
    init(callback: @escaping CameraCallback) { self.callback = callback }
    func notify(_ state: Int32, _ message: String) {
        message.withCString { callback(state, $0) }
    }
    func request(_ request: OSSystemExtensionRequest, actionForReplacingExtension existing: OSSystemExtensionProperties,
                 withExtension ext: OSSystemExtensionProperties) -> OSSystemExtensionRequest.ReplacementAction { .replace }
    func requestNeedsUserApproval(_ request: OSSystemExtensionRequest) {
        notify(0, "Approve NoSub Camera in System Settings > Login Items & Extensions > Camera Extensions.")
    }
    func request(_ request: OSSystemExtensionRequest, didFinishWithResult result: OSSystemExtensionRequest.Result) {
        notify(1, result == .completed ? "NoSub Camera installation completed. Enable output and select it in your video app."
            : "Restart your Mac to finish installing NoSub Camera.")
        activeRequest = nil
    }
    func request(_ request: OSSystemExtensionRequest, didFailWithError error: Error) {
        notify(2, "Camera installation failed: \(error.localizedDescription)")
        activeRequest = nil
    }
}

@_cdecl("nosub_camera_request")
public func cameraRequest(_ install: Int32, _ callback: @escaping CameraCallback) {
    guard activeRequest == nil else { return }
    let delegate = CameraRequest(callback: callback)
    activeRequest = delegate
    let identifier = "com.ethem.nosubcam.desktop.camera"
    let request = install != 0
        ? OSSystemExtensionRequest.activationRequest(forExtensionWithIdentifier: identifier, queue: .main)
        : OSSystemExtensionRequest.deactivationRequest(forExtensionWithIdentifier: identifier, queue: .main)
    request.delegate = delegate
    OSSystemExtensionManager.shared.submitRequest(request)
}
