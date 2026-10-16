import XCTest

@MainActor
final class NoSubCamSnapshotTests: XCTestCase {
    private var app: XCUIApplication!

    override func setUpWithError() throws {
        continueAfterFailure = false
        app = XCUIApplication()
        setupSnapshot(app, waitForAnimations: false)
        app.launchArguments.append("--snapshot")
        app.launch()
        XCTAssertTrue(app.descendants(matching: .any)["nosubcam.root"].waitForExistence(timeout: 15))
    }

    func testAppStoreScreenshots() {
        snapshot("01WiFiConnection")

        let usb = app.buttons["connection.usb"]
        XCTAssertTrue(usb.waitForExistence(timeout: 5))
        usb.tap()
        snapshot("02DirectUSB")

        app.buttons["connection.wifi"].tap()
        snapshot("03WiFiReady")
    }

    func testLegalLinksAreReachable() {
        let privacy = app.descendants(matching: .any)["legal.privacy"]
        for _ in 0..<6 where !privacy.isHittable {
            app.swipeUp()
        }

        XCTAssertTrue(privacy.waitForExistence(timeout: 5))
        XCTAssertTrue(privacy.isHittable)
        XCTAssertTrue(app.descendants(matching: .any)["legal.terms"].isHittable)
        XCTAssertTrue(app.descendants(matching: .any)["legal.support"].isHittable)
    }
}
