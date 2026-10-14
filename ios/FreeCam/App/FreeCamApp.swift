import SwiftUI

@main
struct FreeCamApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
                .tint(StudioTheme.accent)
                .preferredColorScheme(.dark)
        }
    }
}
