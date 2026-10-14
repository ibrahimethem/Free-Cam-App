import SwiftUI

struct ContentView: View {
    @Environment(\.scenePhase) private var scenePhase
    @State private var camera = StreamingSession()
    @AppStorage("receiverAddress") private var address = ""
    @State private var key = ""
    @State private var frontCamera = false
    @State private var usb = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    HStack {
                        Text("CAMERA MONITOR").font(.caption.weight(.semibold)).tracking(1.2)
                        Spacer()
                        Text(usb ? "USB" : "WI-FI").font(.caption.monospaced())
                    }
                    .foregroundStyle(StudioTheme.muted)
                    CameraPreview(session: camera.captureSession)
                        .frame(height: 300)
                        .background(StudioTheme.input)
                        .clipShape(RoundedRectangle(cornerRadius: 4))
                        .overlay(RoundedRectangle(cornerRadius: 4).stroke(StudioTheme.border, lineWidth: 1))
                        .accessibilityLabel("Camera preview")
                    ConnectionForm(address: $address, key: $key, frontCamera: $frontCamera, usb: $usb)
                        .disabled(camera.isStreaming)
                    HStack(spacing: 10) {
                        Circle().fill(camera.isStreaming ? StudioTheme.accent : StudioTheme.muted)
                            .frame(width: 7, height: 7)
                            .accessibilityHidden(true)
                        Text(camera.status)
                            .font(.subheadline)
                            .foregroundStyle(StudioTheme.text)
                            .accessibilityLabel("Status: \(camera.status)")
                        Spacer(minLength: 0)
                    }
                    .studioPanel()
                    Button {
                        if camera.isStreaming { camera.stop() }
                        else { camera.start(address: address, key: key, front: frontCamera, usb: usb) }
                    } label: {
                        Label(camera.isStreaming ? "Stop streaming" : "Start streaming",
                              systemImage: camera.isStreaming ? "stop.fill" : "play.fill")
                            .font(.headline)
                            .foregroundStyle(StudioTheme.input)
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 16)
                            .background(StudioTheme.accent, in: RoundedRectangle(cornerRadius: 4))
                    }
                    .buttonStyle(.plain)
                    Text(usb ? "Keep Free Cam open. Connect a USB data cable, trust your computer and connect from the desktop app. No hotspot needed." : "Keep Free Cam open. Your iPhone and computer must use the same Wi-Fi. This prototype sends video only.")
                        .font(.footnote)
                        .foregroundStyle(StudioTheme.muted)
                    Text("Adjust ISO, shutter speed, focus, white balance, and zoom from the desktop receiver's camera settings panel.")
                        .font(.footnote)
                        .foregroundStyle(StudioTheme.muted)
                }
                .padding()
            }
            .background(StudioTheme.background)
            .navigationTitle("Free Cam")
            .navigationBarTitleDisplayMode(.inline)
            .toolbarBackground(StudioTheme.surface, for: .navigationBar)
            .toolbarBackground(.visible, for: .navigationBar)
        }
        .onChange(of: scenePhase) { _, phase in
            if phase != .active { camera.stop() }
        }
    }
}
