import XCTest
import AVFoundation
@testable import FreeCam

final class ReceiverConnectionTests: XCTestCase {
    func testWhiteBalanceReadingsClampTransientHardwareValues() {
        let invalid = AVCaptureDevice.WhiteBalanceGains(
            redGain: 0, greenGain: .nan, blueGain: 99)
        let safe = CameraReadings.safeWhiteBalanceGains(invalid, maximum: 8)
        XCTAssertEqual(safe.redGain, 1)
        XCTAssertEqual(safe.greenGain, 1)
        XCTAssertEqual(safe.blueGain, 8)

        let invalidMaximum = CameraReadings.safeWhiteBalanceGains(
            .init(redGain: 2, greenGain: 3, blueGain: 4), maximum: .nan)
        XCTAssertEqual(invalidMaximum.redGain, 1)
        XCTAssertEqual(invalidMaximum.greenGain, 1)
        XCTAssertEqual(invalidMaximum.blueGain, 1)
    }

    func testPrivateNetworkAddressesAndBonjourAreAccepted() throws {
        for host in ["10.0.0.2", "192.168.1.10", "172.16.0.5", "172.31.255.254", "studio.local"] {
            let connection = try ReceiverConnection(address: " http://\(host):8765/ ", key: " secret ")
            let request = connection.request(path: "camera", contentType: "application/json")
            XCTAssertEqual(request.url?.path, "/camera")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer secret")
        }
    }

    func testPublicAndMalformedEndpointsAreRejected() {
        for address in ["http://8.8.8.8", "http://172.15.1.1", "http://172.32.1.1",
                        "http://10.0.0.256", "http://10..0.0.1", "http://10.bad.0.0.1",
                        "https://192.168.1.10", "http://user:pass@192.168.1.10",
                        "http://192.168.1.10/frame", "http://192.168.1.10?key=test",
                        "http://192.168.1.10#fragment"] {
            XCTAssertThrowsError(try ReceiverConnection(address: address, key: "secret"), address)
        }
        XCTAssertThrowsError(try ReceiverConnection(address: "http://192.168.1.10", key: "  "))
    }

    func testDesktopCommandsRetainWireCompatibility() throws {
        let manual = Data(#"{"revision":7,"settings":{"exposureAuto":false,"iso":400,"shutterMs":8.33}}"#.utf8)
        let command = try JSONDecoder().decode(CameraCommand.self, from: manual)
        XCTAssertEqual(command.revision, 7)
        XCTAssertEqual(command.settings.exposureAuto, false)
        XCTAssertEqual(command.settings.iso, 400)
        XCTAssertEqual(command.settings.shutterMs, 8.33)
        XCTAssertNil(command.settings.resolution)
        XCTAssertNil(command.settings.frameRate)
        XCTAssertNil(command.settings.cameraPosition)
        XCTAssertNil(command.settings.orientation)
        let resolution = Data(#"{"revision":8,"settings":{"resolution":"1920x1080"}}"#.utf8)
        let change = try JSONDecoder().decode(CameraCommand.self, from: resolution)
        XCTAssertEqual(change.settings.resolution, "1920x1080")
        XCTAssertNil(change.settings.exposureAuto)
        let camera = Data(#"{"revision":9,"settings":{"cameraPosition":"front"}}"#.utf8)
        let cameraChange = try JSONDecoder().decode(CameraCommand.self, from: camera)
        XCTAssertEqual(cameraChange.settings.cameraPosition, "front")
        let orientation = Data(#"{"revision":10,"settings":{"orientation":"landscape"}}"#.utf8)
        let orientationChange = try JSONDecoder().decode(CameraCommand.self, from: orientation)
        XCTAssertEqual(orientationChange.settings.orientation, "landscape")
        let frameRate = Data(#"{"revision":11,"settings":{"frameRate":60}}"#.utf8)
        let frameRateChange = try JSONDecoder().decode(CameraCommand.self, from: frameRate)
        XCTAssertEqual(frameRateChange.settings.frameRate, 60)
    }

    func testDetailedCameraSettingsCanBeCachedLocally() throws {
        let settings = DesiredCameraSettings(
            exposureAuto: false, iso: 320, shutterMs: 8.33,
            focusAuto: true, whiteBalanceAuto: false,
            temperature: 5200, tint: 4, zoom: 1.5
        )
        let restored = try JSONDecoder().decode(
            DesiredCameraSettings.self,
            from: JSONEncoder().encode(settings)
        )
        XCTAssertEqual(restored.exposureAuto, false)
        XCTAssertEqual(restored.iso, 320)
        XCTAssertEqual(restored.shutterMs, 8.33)
        XCTAssertEqual(restored.focusAuto, true)
        XCTAssertEqual(restored.whiteBalanceAuto, false)
        XCTAssertEqual(restored.temperature, 5200)
        XCTAssertEqual(restored.tint, 4)
        XCTAssertEqual(restored.zoom, 1.5)
        XCTAssertNil(restored.resolution)
        XCTAssertNil(restored.frameRate)
    }

    func testPairingQRCodeParsesWiFiAndUSBPayloads() {
        let wifi = PairingCode(value: "nosubcam://pair?mode=wifi&key=abc123&address=http%3A%2F%2F192.168.1.20%3A8765")
        XCTAssertEqual(wifi, PairingCode(mode: .wifi, address: "http://192.168.1.20:8765", key: "abc123"))

        let usb = PairingCode(value: "nosubcam://pair?mode=usb&key=temporary-key")
        XCTAssertEqual(usb, PairingCode(mode: .usb, address: "", key: "temporary-key"))
    }

    func testPairingQRCodeRejectsForeignOrUnsafePayloads() {
        for value in ["https://example.com/pair?mode=usb&key=test",
                      "nosubcam://pair?mode=wifi&key=test&address=https://192.168.1.20",
                      "nosubcam://pair?mode=wifi&key=test&address=http://8.8.8.8",
                      "nosubcam://pair?mode=usb&key="] {
            XCTAssertNil(PairingCode(value: value), value)
        }
    }

    func testPrimaryActionExplainsCameraPermissionState() {
        XCTAssertEqual(CameraPrimaryAction(authorization: .notDetermined, isStreaming: false),
                       .requestPermission)
        XCTAssertEqual(CameraPrimaryAction(authorization: .denied, isStreaming: false),
                       .openSettings)
        XCTAssertEqual(CameraPrimaryAction(authorization: .restricted, isStreaming: false),
                       .unavailable)
        XCTAssertEqual(CameraPrimaryAction(authorization: .authorized, localNetwork: .allowed,
                                           isStreaming: false),
                       .startStreaming)
        XCTAssertEqual(CameraPrimaryAction(authorization: .denied, isStreaming: true),
                       .stopStreaming)
        XCTAssertEqual(CameraPrimaryAction(authorization: .notDetermined, isStreaming: false,
                                           snapshotMode: true), .startStreaming)
    }

    func testPrimaryActionRequestsLocalNetworkAfterCameraForWiFiOnly() {
        XCTAssertEqual(CameraPrimaryAction(authorization: .authorized, localNetwork: .unknown,
                                           usesUSB: false, isStreaming: false),
                       .requestLocalNetwork)
        XCTAssertEqual(CameraPrimaryAction(authorization: .authorized, localNetwork: .requesting,
                                           usesUSB: false, isStreaming: false),
                       .requestingLocalNetwork)
        XCTAssertEqual(CameraPrimaryAction(authorization: .authorized, localNetwork: .denied,
                                           usesUSB: false, isStreaming: false),
                       .openLocalNetworkSettings)
        XCTAssertEqual(CameraPrimaryAction(authorization: .authorized, localNetwork: .unknown,
                                           usesUSB: true, isStreaming: false),
                       .startStreaming)
    }
}
