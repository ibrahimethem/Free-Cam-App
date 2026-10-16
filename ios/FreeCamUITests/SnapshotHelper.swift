import Foundation
import XCTest

private var snapshotApp: XCUIApplication?
private var snapshotDirectory: URL?

@MainActor
func setupSnapshot(_ app: XCUIApplication, waitForAnimations: Bool = true) {
    snapshotApp = app
    guard let hostHome = ProcessInfo.processInfo.environment["SIMULATOR_HOST_HOME"] else { return }
    let cache = URL(fileURLWithPath: hostHome)
        .appendingPathComponent("Library/Caches/tools.fastlane", isDirectory: true)
    snapshotDirectory = cache.appendingPathComponent("screenshots", isDirectory: true)

    if let language = try? String(contentsOf: cache.appendingPathComponent("language.txt"), encoding: .utf8)
        .trimmingCharacters(in: .whitespacesAndNewlines), !language.isEmpty {
        app.launchArguments += ["-AppleLanguages", "(\(language))"]
    }
    if let locale = try? String(contentsOf: cache.appendingPathComponent("locale.txt"), encoding: .utf8)
        .trimmingCharacters(in: .whitespacesAndNewlines), !locale.isEmpty {
        app.launchArguments += ["-AppleLocale", "\"\(locale)\""]
    }
    app.launchArguments += ["-FASTLANE_SNAPSHOT", "YES", "-ui_testing"]
}

@MainActor
func snapshot(_ name: String) {
    guard snapshotApp != nil,
          let directory = snapshotDirectory,
          var simulator = ProcessInfo.processInfo.environment["SIMULATOR_DEVICE_NAME"] else {
        XCTFail("Fastlane snapshot environment is unavailable")
        return
    }
    simulator = simulator.replacingOccurrences(
        of: "Clone [0-9]+ of ",
        with: "",
        options: .regularExpression
    )
    do {
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        let image = XCUIScreen.main.screenshot().image
        let path = directory.appendingPathComponent("\(simulator)-\(name).png")
        try image.pngData()?.write(to: path, options: .atomic)
        NSLog("snapshot: \(name)")
    } catch {
        XCTFail("Could not save snapshot \(name): \(error.localizedDescription)")
    }
}

// SnapshotHelperVersion [1.30]
