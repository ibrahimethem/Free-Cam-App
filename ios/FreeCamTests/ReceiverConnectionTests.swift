import XCTest
@testable import FreeCam

final class ReceiverConnectionTests: XCTestCase {
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
        let resolution = Data(#"{"revision":8,"settings":{"resolution":"1920x1080"}}"#.utf8)
        let change = try JSONDecoder().decode(CameraCommand.self, from: resolution)
        XCTAssertEqual(change.settings.resolution, "1920x1080")
        XCTAssertNil(change.settings.exposureAuto)
    }
}
