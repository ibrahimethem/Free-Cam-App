import Foundation
import CoreMediaIO

func values(_ object: UInt32, _ selector: Int, _ scope: Int = kCMIOObjectPropertyScopeGlobal) -> [UInt32] {
    var address = CMIOObjectPropertyAddress(mSelector: UInt32(selector), mScope: UInt32(scope), mElement: UInt32(kCMIOObjectPropertyElementMain))
    var size: UInt32 = 0
    let status = CMIOObjectGetPropertyDataSize(object, &address, 0, nil, &size)
    guard status == 0 else { print("property \(selector) status \(status)"); return [] }
    var ids = [UInt32](repeating: 0, count: Int(size) / 4)
    guard !ids.isEmpty else { return [] }
    let result = ids.withUnsafeMutableBytes { CMIOObjectGetPropertyData(object, &address, 0, nil, size, &size, $0.baseAddress!) }
    return result == 0 ? ids : []
}
for device in values(UInt32(kCMIOObjectSystemObject), kCMIOHardwarePropertyDevices) {
    var address = CMIOObjectPropertyAddress(mSelector: UInt32(kCMIODevicePropertyDeviceUID), mScope: UInt32(kCMIOObjectPropertyScopeGlobal), mElement: UInt32(kCMIOObjectPropertyElementMain))
    var uid: Unmanaged<CFString>?
    var size = UInt32(MemoryLayout<Unmanaged<CFString>?>.size)
    guard CMIOObjectGetPropertyData(device, &address, 0, nil, size, &size, &uid) == 0,
          let identifier = uid?.takeRetainedValue() as String?, identifier.contains("nosubcam") else { continue }
    print("NoSub device \(device) UID \(identifier)")
    for scope in [kCMIOObjectPropertyScopeGlobal, kCMIODevicePropertyScopeInput, kCMIODevicePropertyScopeOutput] {
        print("scope \(scope) streams \(values(device, kCMIODevicePropertyStreams, scope))")
    }
    if let sink = values(device, kCMIODevicePropertyStreams, kCMIODevicePropertyScopeOutput).first {
        var queue: Unmanaged<CMSimpleQueue>?
        let status = CMIOStreamCopyBufferQueue(sink, { _, _, _ in }, nil, &queue)
        print("copy queue status \(status), present \(queue != nil)")
        if let queue { let object = queue.takeRetainedValue(); print("capacity \(CMSimpleQueueGetCapacity(object))") }
    }
}
