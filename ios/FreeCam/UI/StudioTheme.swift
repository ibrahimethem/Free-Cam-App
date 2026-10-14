import SwiftUI

// The same neutral surfaces and warm accent as the desktop studio theme.
enum StudioTheme {
    static let background = Color(red: 41 / 255.0, green: 43 / 255.0, blue: 44 / 255.0)
    static let surface = Color(red: 52 / 255.0, green: 54 / 255.0, blue: 55 / 255.0)
    static let input = Color(red: 36 / 255.0, green: 38 / 255.0, blue: 39 / 255.0)
    static let border = Color(red: 85 / 255.0, green: 88 / 255.0, blue: 89 / 255.0)
    static let text = Color(red: 236 / 255.0, green: 238 / 255.0, blue: 234 / 255.0)
    static let muted = Color(red: 181 / 255.0, green: 185 / 255.0, blue: 181 / 255.0)
    static let accent = Color(red: 255 / 255.0, green: 177 / 255.0, blue: 107 / 255.0)
}

private struct StudioSurface: ViewModifier {
    let field: Bool

    func body(content: Content) -> some View {
        content
            .padding(field ? 12 : 16)
            .background(field ? StudioTheme.input : StudioTheme.surface,
                        in: RoundedRectangle(cornerRadius: 4))
            .overlay(RoundedRectangle(cornerRadius: 4).stroke(StudioTheme.border, lineWidth: 1))
    }
}

extension View {
    func studioPanel() -> some View { modifier(StudioSurface(field: false)) }
    func studioField() -> some View { modifier(StudioSurface(field: true)) }
}
