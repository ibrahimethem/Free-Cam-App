import SwiftUI

struct ConnectionForm: View {
    @Binding var address: String
    @Binding var key: String
    @Binding var frontCamera: Bool
    @Binding var usb: Bool

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("CONNECTION")
                .font(.caption.weight(.semibold))
                .tracking(1.2)
                .foregroundStyle(StudioTheme.muted)
            Toggle("Direct USB connection", isOn: $usb)
            Text("Receiver address").font(.caption).foregroundStyle(StudioTheme.muted)
            TextField("http://192.168.1.10:8765", text: $address)
                .keyboardType(.URL)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .textFieldStyle(.plain)
                .font(.system(.body, design: .monospaced))
                .studioField()
                .accessibilityLabel("Receiver address")
                .disabled(usb)
                .opacity(usb ? 0.5 : 1)
            Text("Pairing key").font(.caption).foregroundStyle(StudioTheme.muted)
            SecureField("Pairing key from desktop", text: $key)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .textFieldStyle(.plain)
                .studioField()
            Toggle("Use front camera", isOn: $frontCamera)
        }
        .foregroundStyle(StudioTheme.text)
        .studioPanel()
    }
}
