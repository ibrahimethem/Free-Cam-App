import SwiftUI

struct ConnectionForm: View {
    @Binding var address: String
    @Binding var key: String
    @Binding var usb: Bool
    var pairingSaved = false
    var hasSavedPairing = false
    var pairingError: String?
    var onPair: () -> Void = {}
    var onForget: () -> Void = {}
    @State private var showsPairingScanner = false
    @State private var confirmsForget = false

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("CONNECTION")
                .font(.caption.weight(.semibold))
                .tracking(1.2)
                .foregroundStyle(StudioTheme.muted)
            HStack(spacing: 6) {
                connectionModeButton("WI-FI", identifier: "connection.wifi", selected: !usb) { usb = false }
                connectionModeButton("DIRECT USB", identifier: "connection.usb", selected: usb) { usb = true }
            }
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
            if pairingSaved {
                Label("Pairing saved on this iPhone. Ready to reconnect.", systemImage: "checkmark.shield")
                    .font(.footnote)
                    .foregroundStyle(StudioTheme.accent)
            } else {
                Text("Scan once. Your computer and iPhone remember the pairing for next time.")
                    .font(.footnote)
                    .foregroundStyle(StudioTheme.muted)
            }
            if let pairingError {
                Text(pairingError).font(.footnote).foregroundStyle(StudioTheme.muted)
            }
            Button {
                showsPairingScanner = true
            } label: {
                Label(pairingSaved ? "Pair another computer" : "Scan pairing QR", systemImage: "qrcode.viewfinder")
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(StudioTheme.input)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 12)
                    .background(StudioTheme.accent,
                                in: RoundedRectangle(cornerRadius: StudioTheme.cornerRadius))
            }
            .buttonStyle(.plain)
            .accessibilityIdentifier("pairing.scan")
            if hasSavedPairing {
                Button("Forget saved pairing", role: .destructive) { confirmsForget = true }
                    .font(.footnote)
                    .accessibilityIdentifier("pairing.forget")
            }
        }
        .foregroundStyle(StudioTheme.text)
        .tint(StudioTheme.accent)
        .studioPanel()
        .sheet(isPresented: $showsPairingScanner) {
            PairingScannerSheet { pairing in
                usb = pairing.mode == .usb
                key = pairing.key
                if pairing.mode == .wifi { address = pairing.address }
                onPair()
            }
        }
        .confirmationDialog("Forget this computer on this iPhone?", isPresented: $confirmsForget, titleVisibility: .visible) {
            Button("Forget pairing", role: .destructive, action: onForget)
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("You will need to scan its QR code again. To revoke access for every phone, use Reset pairing in NoSub Studio.")
        }
    }

    private func connectionModeButton(
        _ title: String,
        identifier: String,
        selected: Bool,
        action: @escaping () -> Void
    ) -> some View {
        Button(action: action) {
            Text(title)
                .font(.caption.monospaced().weight(.semibold))
                .tracking(0.8)
                .foregroundStyle(selected ? StudioTheme.input : StudioTheme.muted)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 12)
                .background(
                    selected ? StudioTheme.accent : StudioTheme.input,
                    in: RoundedRectangle(cornerRadius: StudioTheme.cornerRadius)
                )
                .overlay(
                    RoundedRectangle(cornerRadius: StudioTheme.cornerRadius)
                        .stroke(selected ? StudioTheme.accent : StudioTheme.border, lineWidth: 1)
                )
        }
        .buttonStyle(.plain)
        .accessibilityIdentifier(identifier)
        .accessibilityAddTraits(selected ? .isSelected : [])
    }
}
