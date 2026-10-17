import Foundation
import CoreMediaIO

private var lastStartError: Int32 = 0

private func objectIDs(_ object: CMIOObjectID, _ selector: CMIOObjectPropertySelector,
                       _ scope: CMIOObjectPropertyScope = UInt32(kCMIOObjectPropertyScopeGlobal)) -> [CMIOObjectID] {
    var address = CMIOObjectPropertyAddress(mSelector: selector, mScope: scope, mElement: UInt32(kCMIOObjectPropertyElementMain))
    var size: UInt32 = 0
    guard CMIOObjectGetPropertyDataSize(object, &address, 0, nil, &size) == 0 else { return [] }
    var values = [CMIOObjectID](repeating: 0, count: Int(size) / MemoryLayout<CMIOObjectID>.size)
    guard !values.isEmpty else { return [] }
    let result = values.withUnsafeMutableBytes { bytes in
        CMIOObjectGetPropertyData(object, &address, 0, nil, size, &size, bytes.baseAddress!)
    }
    return result == 0 ? values : []
}

private func deviceUID(_ device: CMIOObjectID) -> String? {
    var address = CMIOObjectPropertyAddress(mSelector: UInt32(kCMIODevicePropertyDeviceUID),
        mScope: UInt32(kCMIOObjectPropertyScopeGlobal), mElement: UInt32(kCMIOObjectPropertyElementMain))
    var value: Unmanaged<CFString>?
    var size = UInt32(MemoryLayout<Unmanaged<CFString>?>.size)
    guard CMIOObjectGetPropertyData(device, &address, 0, nil, size, &size, &value) == 0 else { return nil }
    return value?.takeRetainedValue() as String?
}

@_cdecl("nosub_camera_available")
public func cameraAvailable() -> Int32 {
    objectIDs(CMIOObjectID(kCMIOObjectSystemObject), UInt32(kCMIOHardwarePropertyDevices))
        .contains(where: { deviceUID($0) == "com.ethem.nosubcam.camera" }) ? 1 : 0
}

private final class CameraOutput {
    let device: CMIODeviceID
    let stream: CMIOStreamID
    let queue: CMSimpleQueue
    var pool: CVPixelBufferPool!
    var format: CMFormatDescription!

    init?() {
        guard let device = objectIDs(CMIOObjectID(kCMIOObjectSystemObject), UInt32(kCMIOHardwarePropertyDevices))
                .first(where: { deviceUID($0) == "com.ethem.nosubcam.camera" }) else { lastStartError = -1001; return nil }
        guard let stream = objectIDs(device, UInt32(kCMIODevicePropertyStreams), UInt32(kCMIODevicePropertyScopeOutput)).first
            else { lastStartError = -1002; return nil }
        self.device = device
        self.stream = stream
        var bufferQueue: Unmanaged<CMSimpleQueue>?
        let queueStatus = CMIOStreamCopyBufferQueue(stream, { _, _, _ in }, nil, &bufferQueue)
        guard queueStatus == 0, let bufferQueue else { lastStartError = queueStatus == 0 ? -1003 : queueStatus; return nil }
        queue = bufferQueue.takeRetainedValue()
        CMVideoFormatDescriptionCreate(allocator: kCFAllocatorDefault, codecType: kCVPixelFormatType_32BGRA,
            width: Int32(frameWidth), height: Int32(frameHeight), extensions: nil, formatDescriptionOut: &format)
        CVPixelBufferPoolCreate(kCFAllocatorDefault, nil, [
            kCVPixelBufferWidthKey: frameWidth, kCVPixelBufferHeightKey: frameHeight,
            kCVPixelBufferPixelFormatTypeKey: kCVPixelFormatType_32BGRA,
            kCVPixelBufferIOSurfacePropertiesKey: [:]
        ] as CFDictionary, &pool)
        let startStatus = CMIODeviceStartStream(device, stream)
        guard startStatus == 0 else { lastStartError = startStatus; return nil }
    }

    func send(_ pixels: UnsafeRawPointer?) -> Int32 {
        // Bounded queue: drop rather than delay the camera/GUI when a consumer stalls.
        guard CMSimpleQueueGetCount(queue) < CMSimpleQueueGetCapacity(queue) else { return 0 }
        var buffer: CVPixelBuffer?
        guard CVPixelBufferPoolCreatePixelBufferWithAuxAttributes(kCFAllocatorDefault, pool,
            [kCVPixelBufferPoolAllocationThresholdKey: 5] as CFDictionary, &buffer) == 0,
              let buffer else { return 0 }
        CVPixelBufferLockBaseAddress(buffer, [])
        if let destination = CVPixelBufferGetBaseAddress(buffer) {
            let stride = CVPixelBufferGetBytesPerRow(buffer)
            for row in 0..<frameHeight {
                if let pixels { memcpy(destination + row * stride, pixels + row * frameWidth * 4, frameWidth * 4) }
                else { memset(destination + row * stride, 0, frameWidth * 4) }
            }
        }
        CVPixelBufferUnlockBaseAddress(buffer, [])
        var timing = CMSampleTimingInfo(duration: CMTime(value: 1, timescale: 30),
            presentationTimeStamp: CMClockGetTime(CMClockGetHostTimeClock()), decodeTimeStamp: .invalid)
        var sample: CMSampleBuffer?
        guard CMSampleBufferCreateForImageBuffer(allocator: kCFAllocatorDefault, imageBuffer: buffer,
            dataReady: true, makeDataReadyCallback: nil, refcon: nil, formatDescription: format,
            sampleTiming: &timing, sampleBufferOut: &sample) == 0, let sample else { return -2 }
        let pointer = Unmanaged.passRetained(sample).toOpaque()
        let result = CMSimpleQueueEnqueue(queue, element: pointer)
        if result != 0 { Unmanaged<CMSampleBuffer>.fromOpaque(pointer).release() }
        return result == 0 ? 1 : 0
    }

    deinit {
        CMIODeviceStopStream(device, stream)
        while let pointer = CMSimpleQueueDequeue(queue) {
            Unmanaged<CMSampleBuffer>.fromOpaque(pointer).release()
        }
    }
}

private var output: CameraOutput?
private let outputLock = NSLock()

@_cdecl("nosub_camera_output_start")
public func startCameraOutput() -> Int32 {
    outputLock.lock(); defer { outputLock.unlock() }
    if output != nil { return 1 }
    lastStartError = 0
    output = CameraOutput()
    return output == nil ? lastStartError : 1
}

@_cdecl("nosub_camera_output_send")
public func sendCameraOutput(_ pixels: UnsafeRawPointer?, _ length: Int32) -> Int32 {
    outputLock.lock(); defer { outputLock.unlock() }
    guard length == frameBytes || (pixels == nil && length == 0) else { return -2 }
    return output?.send(pixels) ?? -1
}

@_cdecl("nosub_camera_output_stop")
public func stopCameraOutput() {
    outputLock.lock(); defer { outputLock.unlock() }
    output = nil
}
