import Foundation
import CoreMediaIO
import IOKit.audio
import Security
import os

final class CameraDevice: NSObject, CMIOExtensionDeviceSource {
    private(set) var device: CMIOExtensionDevice!
    private var source: CameraStream!
    private var pool: CVPixelBufferPool!
    private var videoDescription: CMFormatDescription!
    private let queue = DispatchQueue(label: "com.ethem.nosubcam.camera.frames", qos: .userInteractive)
    private var consumers = 0
    private var timer: DispatchSourceTimer?
    private var sink: CameraSink!
    private var sinkClient: CMIOExtensionClient?
    private var sinkTimer: DispatchSourceTimer?
    private var sinkGeneration = 0
    private var consumePending = false
    private var latest: CVPixelBuffer?
    private var latestTime = CMTime.invalid

    override init() {
        super.init()
        device = CMIOExtensionDevice(localizedName: "NoSub Camera",
            deviceID: UUID(uuidString: "D4B63131-1487-40B3-AFD4-B2283CDCE52D")!,
            legacyDeviceID: "com.ethem.nosubcam.camera", source: self)
        CMVideoFormatDescriptionCreate(allocator: kCFAllocatorDefault, codecType: kCVPixelFormatType_32BGRA,
            width: Int32(frameWidth), height: Int32(frameHeight), extensions: nil, formatDescriptionOut: &videoDescription)
        CVPixelBufferPoolCreate(kCFAllocatorDefault, nil, [
            kCVPixelBufferWidthKey: frameWidth, kCVPixelBufferHeightKey: frameHeight,
            kCVPixelBufferPixelFormatTypeKey: kCVPixelFormatType_32BGRA,
            kCVPixelBufferIOSurfacePropertiesKey: [:]
        ] as CFDictionary, &pool)
        let duration = CMTime(value: 1, timescale: 30)
        let format = CMIOExtensionStreamFormat(formatDescription: videoDescription,
            maxFrameDuration: duration, minFrameDuration: duration, validFrameDurations: nil)
        source = CameraStream(device: device, format: format)
        sink = CameraSink(device: device, format: format)
        do { try device.addStream(source.stream); try device.addStream(sink.stream) }
        catch { fatalError("Cannot add NoSub Camera stream: \(error)") }
    }

    var availableProperties: Set<CMIOExtensionProperty> { [.deviceTransportType, .deviceModel] }
    func deviceProperties(forProperties properties: Set<CMIOExtensionProperty>) throws -> CMIOExtensionDeviceProperties {
        let result = CMIOExtensionDeviceProperties(dictionary: [:])
        result.transportType = kIOAudioDeviceTransportTypeVirtual
        result.model = "NoSub Camera"
        return result
    }
    func setDeviceProperties(_ properties: CMIOExtensionDeviceProperties) throws {}

    func start() {
        queue.sync {
            consumers += 1
            guard timer == nil else { return }
            let next = DispatchSource.makeTimerSource(queue: queue)
            next.schedule(deadline: .now(), repeating: .nanoseconds(33_333_333), leeway: .milliseconds(1))
            next.setEventHandler { [weak self] in self?.sendFrame() }
            timer = next
            next.resume()
        }
    }
    func stop() {
        queue.sync {
            consumers = max(0, consumers - 1)
            if consumers == 0 { timer?.cancel(); timer = nil }
        }
    }

    func startSink(client: CMIOExtensionClient) {
        queue.sync {
            guard sinkTimer == nil else { return }
            sinkClient = client
            sinkGeneration += 1
            let timer = DispatchSource.makeTimerSource(queue: queue)
            timer.schedule(deadline: .now(), repeating: .milliseconds(8))
            timer.setEventHandler { [weak self] in self?.consume() }
            sinkTimer = timer
            timer.resume()
        }
    }
    func stopSink() {
        queue.sync {
            sinkGeneration += 1
            sinkClient = nil
            sinkTimer?.cancel(); sinkTimer = nil
            latest = nil
            latestTime = .invalid
            consumePending = false
        }
    }
    private func consume() {
        guard let client = sinkClient, !consumePending else { return }
        consumePending = true
        let generation = sinkGeneration
        sink.stream.consumeSampleBuffer(from: client) { [weak self] sample, sequence, _, _, error in
            guard let self else { return }
            self.queue.async {
                guard self.sinkGeneration == generation else { return }
                self.consumePending = false
                guard error == nil, let sample, let image = CMSampleBufferGetImageBuffer(sample),
                      CVPixelBufferGetWidth(image) == frameWidth,
                      CVPixelBufferGetHeight(image) == frameHeight,
                      CVPixelBufferGetPixelFormatType(image) == kCVPixelFormatType_32BGRA else { return }
                self.latest = image
                self.latestTime = CMSampleBufferGetPresentationTimeStamp(sample)
                self.sink.stream.notifyScheduledOutputChanged(CMIOExtensionScheduledOutput(sequenceNumber: sequence,
                    hostTimeInNanoseconds: UInt64(CMClockGetTime(CMClockGetHostTimeClock()).seconds * 1_000_000_000)))
            }
        }
    }
    private func sendFrame() {
        var buffer: CVPixelBuffer?
        let now = CMClockGetTime(CMClockGetHostTimeClock())
        let age = CMTimeSubtract(now, latestTime).seconds
        if let latest, latestTime.isValid, age >= 0, age < 1 {
            send(latest)
            return
        }
        let attributes = [kCVPixelBufferPoolAllocationThresholdKey: 5] as CFDictionary
        guard CVPixelBufferPoolCreatePixelBufferWithAuxAttributes(kCFAllocatorDefault, pool, attributes, &buffer) == 0,
              let buffer else { return }
        CVPixelBufferLockBaseAddress(buffer, [])
        if let address = CVPixelBufferGetBaseAddress(buffer) {
            // Black when disconnected/disabled. Never replay a stale camera image.
            memset(address, 0, CVPixelBufferGetBytesPerRow(buffer) * frameHeight)
        }
        CVPixelBufferUnlockBaseAddress(buffer, [])
        send(buffer)
    }
    private func send(_ buffer: CVPixelBuffer) {
        var timing = CMSampleTimingInfo(duration: CMTime(value: 1, timescale: 30),
            presentationTimeStamp: CMClockGetTime(CMClockGetHostTimeClock()), decodeTimeStamp: .invalid)
        var sample: CMSampleBuffer?
        guard CMSampleBufferCreateForImageBuffer(allocator: kCFAllocatorDefault, imageBuffer: buffer,
            dataReady: true, makeDataReadyCallback: nil, refcon: nil, formatDescription: videoDescription,
            sampleTiming: &timing, sampleBufferOut: &sample) == 0, let sample else { return }
        source.stream.send(sample, discontinuity: [],
            hostTimeInNanoseconds: UInt64(timing.presentationTimeStamp.seconds * 1_000_000_000))
    }
}

final class CameraSink: NSObject, CMIOExtensionStreamSource {
    private(set) var stream: CMIOExtensionStream!
    private let device: CMIOExtensionDevice
    private let format: CMIOExtensionStreamFormat
    private var client: CMIOExtensionClient?
    private let logger = Logger(subsystem: "com.ethem.nosubcam.camera", category: "authorization")
    init(device: CMIOExtensionDevice, format: CMIOExtensionStreamFormat) {
        self.device = device; self.format = format
        super.init()
        stream = CMIOExtensionStream(localizedName: "NoSub Camera Input",
            streamID: UUID(uuidString: "D0632B6A-7DF0-4162-B856-C1C7A4143DBC")!,
            direction: .sink, clockType: .hostTime, source: self)
    }
    var formats: [CMIOExtensionStreamFormat] { [format] }
    var availableProperties: Set<CMIOExtensionProperty> {
        [.streamActiveFormatIndex, .streamFrameDuration, .streamSinkBufferQueueSize,
         .streamSinkBuffersRequiredForStartup, .streamSinkBufferUnderrunCount, .streamSinkEndOfData]
    }
    func streamProperties(forProperties properties: Set<CMIOExtensionProperty>) throws -> CMIOExtensionStreamProperties {
        let result = CMIOExtensionStreamProperties(dictionary: [:])
        result.activeFormatIndex = 0
        result.frameDuration = CMTime(value: 1, timescale: 30)
        result.sinkBufferQueueSize = 3
        result.sinkBuffersRequiredForStartup = 1
        result.sinkBufferUnderrunCount = 0
        result.sinkEndOfData = 0
        return result
    }
    func setStreamProperties(_ properties: CMIOExtensionStreamProperties) throws {}
    func authorizedToStartStream(for client: CMIOExtensionClient) -> Bool {
        // Only our signed host may inject frames; ordinary consumers only read.
        if let writer = self.client, writer.clientID != client.clientID {
            logger.error("Sink already has a different writer")
            return false
        }
        // The legacy CMIO bridge reports signingID="unknown" for this Python
        // host. Validate the actual guest code and Apple team, not that hint.
        var code: SecCode?
        var requirement: SecRequirement?
        let rule = "anchor apple generic and identifier \"com.ethem.nosubcam.desktop\" and certificate leaf[subject.OU] = \"G478PYWXZ4\""
        // Validate the kernel's loaded signature rather than opening the host's
        // executable from the role-user sandbox (which returns access error 100001).
        let attributes = [kSecGuestAttributePid: client.pid,
                          kSecGuestAttributeDynamicCode: true] as CFDictionary
        let lookup = SecCodeCopyGuestWithAttributes(nil, attributes, [], &code)
        guard lookup == errSecSuccess, let code else { logger.error("Writer code lookup failed: \(lookup, privacy: .public)"); return false }
        let creation = SecRequirementCreateWithString(rule as CFString, [], &requirement)
        guard creation == errSecSuccess, let requirement else { logger.error("Writer requirement failed: \(creation, privacy: .public)"); return false }
        let validation = SecCodeCheckValidity(code, [], requirement)
        guard validation == errSecSuccess else { logger.error("Writer signature validation failed: \(validation, privacy: .public)"); return false }
        self.client = client
        return true
    }
    func startStream() throws {
        guard let client else { return }
        (device.source as? CameraDevice)?.startSink(client: client)
    }
    func stopStream() throws {
        (device.source as? CameraDevice)?.stopSink()
        client = nil
    }
}

final class CameraStream: NSObject, CMIOExtensionStreamSource {
    private(set) var stream: CMIOExtensionStream!
    let device: CMIOExtensionDevice
    let format: CMIOExtensionStreamFormat
    init(device: CMIOExtensionDevice, format: CMIOExtensionStreamFormat) {
        self.device = device
        self.format = format
        super.init()
        stream = CMIOExtensionStream(localizedName: "NoSub Camera Video",
            streamID: UUID(uuidString: "87C77E2D-9964-4FAA-8467-D22016193E80")!,
            direction: .source, clockType: .hostTime, source: self)
    }
    var formats: [CMIOExtensionStreamFormat] { [format] }
    var availableProperties: Set<CMIOExtensionProperty> { [.streamActiveFormatIndex, .streamFrameDuration] }
    func streamProperties(forProperties properties: Set<CMIOExtensionProperty>) throws -> CMIOExtensionStreamProperties {
        let result = CMIOExtensionStreamProperties(dictionary: [:])
        result.activeFormatIndex = 0
        result.frameDuration = CMTime(value: 1, timescale: 30)
        return result
    }
    func setStreamProperties(_ properties: CMIOExtensionStreamProperties) throws {
        if let index = properties.activeFormatIndex, index != 0 {
            throw NSError(domain: NSOSStatusErrorDomain, code: Int(kCMIOHardwareUnsupportedOperationError))
        }
    }
    func authorizedToStartStream(for client: CMIOExtensionClient) -> Bool { true }
    func startStream() throws { (device.source as? CameraDevice)?.start() }
    func stopStream() throws { (device.source as? CameraDevice)?.stop() }
}

final class CameraProvider: NSObject, CMIOExtensionProviderSource {
    private(set) var provider: CMIOExtensionProvider!
    private let camera = CameraDevice()
    override init() {
        super.init()
        provider = CMIOExtensionProvider(source: self, clientQueue: nil)
        do { try provider.addDevice(camera.device) }
        catch { fatalError("Cannot add NoSub Camera: \(error)") }
    }
    func connect(to client: CMIOExtensionClient) throws {}
    func disconnect(from client: CMIOExtensionClient) {}
    var availableProperties: Set<CMIOExtensionProperty> { [.providerManufacturer] }
    func providerProperties(forProperties properties: Set<CMIOExtensionProperty>) throws -> CMIOExtensionProviderProperties {
        let result = CMIOExtensionProviderProperties(dictionary: [:])
        result.manufacturer = "NoSub Cam"
        return result
    }
    func setProviderProperties(_ properties: CMIOExtensionProviderProperties) throws {}
}
