import AVFoundation
import SwiftUI
import UIKit

struct ContentView: View {
    @Environment(\.scenePhase) private var scenePhase
    @Environment(\.openURL) private var openURL
    @State private var camera = StreamingSession()
    @State private var cameraAuthorization = AVCaptureDevice.authorizationStatus(for: .video)
    @State private var localNetworkRequester = LocalNetworkPermissionRequester()
    @AppStorage("receiverAddress") private var address = ""
    @AppStorage("localNetworkPermission") private var localNetworkPermissionRaw = LocalNetworkPermissionState.unknown.rawValue
    @State private var key = ""
    @State private var usb = false
    @State private var rememberedPairing: SavedPairing?
    @State private var hasLoadedPairing = false
    @State private var pairingError: String?
    @State private var refreshesLocalNetworkAfterSettings = false
    @State private var showsStopConfirmation = false
    private let snapshotMode = ProcessInfo.processInfo.arguments.contains("--snapshot")

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 14) {
                    ConnectionForm(address: $address, key: $key, usb: $usb,
                                   pairingSaved: pairingMatchesSaved,
                                   hasSavedPairing: rememberedPairing != nil,
                                   pairingError: pairingError,
                                   onPair: savePairing, onForget: forgetPairing)
                        .disabled(camera.isStreaming)
                    HStack(spacing: 10) {
                        Circle().fill(camera.isStreaming ? StudioTheme.accent : StudioTheme.muted)
                            .frame(width: 7, height: 7)
                            .accessibilityHidden(true)
                        Text(permissionStatus)
                            .font(.subheadline)
                            .foregroundStyle(StudioTheme.text)
                            .accessibilityLabel("Status: \(permissionStatus)")
                        Spacer(minLength: 0)
                    }
                    .studioPanel()
                    Text(usb ? "Connect a USB data cable, trust your computer and connect from NoSub Studio. The session stays ready when you switch apps." : "Your iPhone and computer must use the same Wi-Fi. The session stays ready when you switch apps.")
                        .font(.footnote)
                        .foregroundStyle(StudioTheme.muted)
                    Text("For native 16:9 framing and the best performance, place your iPhone horizontally and select Landscape · native in NoSub Studio.")
                        .font(.footnote)
                        .foregroundStyle(StudioTheme.accent)
                    Text("Adjust ISO, shutter speed, focus, white balance, and zoom from the desktop receiver's camera settings panel.")
                        .font(.footnote)
                        .foregroundStyle(StudioTheme.muted)
                    LegalLinks()
                }
                .padding()
                .padding(.bottom, 96)
            }
            .background(StudioTheme.background)
            .navigationTitle("NoSub Cam")
            .navigationBarTitleDisplayMode(.inline)
            .toolbarBackground(StudioTheme.surface, for: .navigationBar)
            .toolbarBackground(.visible, for: .navigationBar)
        }
        .tint(StudioTheme.accent)
        .accessibilityIdentifier("nosubcam.root")
        .alert("Stop streaming?", isPresented: $showsStopConfirmation) {
            Button("Keep streaming", role: .cancel) {}
            Button("Stop streaming", role: .destructive) {
                camera.stop()
            }
        } message: {
            Text("Your camera feed will be disconnected from NoSub Studio.")
        }
        .safeAreaInset(edge: .bottom, spacing: 0) {
            VStack(spacing: 0) {
                Divider().overlay(StudioTheme.border)
                Button {
                    performPrimaryAction()
                } label: {
                    Label(primaryAction.title, systemImage: primaryAction.systemImage)
                        .font(.headline)
                        .foregroundStyle(StudioTheme.input)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 15)
                        .background(
                            StudioTheme.accent,
                            in: RoundedRectangle(cornerRadius: StudioTheme.cornerRadius)
                        )
                }
                .buttonStyle(.plain)
                .disabled(primaryAction == .unavailable || primaryAction == .requestingLocalNetwork)
                .accessibilityIdentifier("stream.primary")
                .padding(.horizontal)
                .padding(.top, 12)
                .padding(.bottom, 8)
            }
            .background(StudioTheme.surface)
        }
        .onChange(of: scenePhase) { _, phase in
            if phase == .inactive {
                showsStopConfirmation = false
            }
            else if phase == .active {
                refreshCameraAuthorization()
                camera.resumeIfNeeded()
                if refreshesLocalNetworkAfterSettings {
                    refreshesLocalNetworkAfterSettings = false
                    requestLocalNetworkPermission()
                }
            }
        }
        .onChange(of: camera.isStreaming) { _, isStreaming in
            if !isStreaming { showsStopConfirmation = false }
        }
        .onAppear {
            refreshCameraAuthorization()
            if localNetworkPermission == .requesting {
                localNetworkPermissionRaw = LocalNetworkPermissionState.unknown.rawValue
            }
            if snapshotMode {
                address = "http://192.168.1.24:8765"
                key = "NOSUB-DEMO"
            } else if !hasLoadedPairing {
                hasLoadedPairing = true
                do {
                    if let saved = try PairingKeychain().load() {
                        rememberedPairing = saved
                        address = saved.address
                        key = saved.key
                        usb = saved.usesUSB
                    }
                } catch { pairingError = "Saved pairing could not be loaded. Scan the QR code to connect." }
            }
        }
    }

    private var primaryAction: CameraPrimaryAction {
        CameraPrimaryAction(authorization: cameraAuthorization,
                            localNetwork: localNetworkPermission,
                            usesUSB: usb,
                            isStreaming: camera.isStreaming,
                            snapshotMode: snapshotMode)
    }

    private var localNetworkPermission: LocalNetworkPermissionState {
        LocalNetworkPermissionState(rawValue: localNetworkPermissionRaw) ?? .unknown
    }

    private var permissionStatus: String {
        switch primaryAction {
        case .requestPermission:
            "Camera access is required before streaming."
        case .openSettings:
            "Camera access is off. Enable it in Settings."
        case .requestLocalNetwork:
            "Local Network access is required for Wi-Fi streaming."
        case .requestingLocalNetwork:
            "Waiting for Local Network permission..."
        case .openLocalNetworkSettings:
            "Local Network access is off. Enable it in Settings."
        case .unavailable:
            "Camera access is restricted on this device."
        default:
            camera.status
        }
    }

    private func performPrimaryAction() {
        switch primaryAction {
        case .stopStreaming:
            showsStopConfirmation = true
        case .startStreaming:
            savePairing()
            camera.start(address: address, key: key, usb: usb)
        case .requestPermission:
            Task { @MainActor in
                _ = await AVCaptureDevice.requestAccess(for: .video)
                refreshCameraAuthorization()
            }
        case .openSettings:
            guard let settings = URL(string: UIApplication.openSettingsURLString) else { return }
            openURL(settings)
        case .requestLocalNetwork:
            requestLocalNetworkPermission()
        case .requestingLocalNetwork:
            break
        case .openLocalNetworkSettings:
            guard let settings = URL(string: UIApplication.openSettingsURLString) else { return }
            refreshesLocalNetworkAfterSettings = true
            openURL(settings)
        case .unavailable:
            break
        }
    }

    private var pairingMatchesSaved: Bool {
        guard let rememberedPairing else { return false }
        return rememberedPairing.key == key.trimmingCharacters(in: .whitespacesAndNewlines)
            && rememberedPairing.address == address.trimmingCharacters(in: .whitespacesAndNewlines)
            && rememberedPairing.usesUSB == usb
    }

    private func savePairing() {
        guard !snapshotMode else { return }
        do {
            let saved = try SavedPairing(address: address, key: key, usesUSB: usb)
            try PairingKeychain().save(saved)
            rememberedPairing = saved
            pairingError = nil
        } catch { pairingError = "Pairing was not saved securely. You can still connect for this session." }
    }

    private func forgetPairing() {
        guard !snapshotMode else { return }
        do {
            try PairingKeychain().forget()
            rememberedPairing = nil
            key = ""
            address = ""
            usb = false
            pairingError = nil
        } catch { pairingError = "Saved pairing could not be removed. Please try again." }
    }

    private func refreshCameraAuthorization() {
        cameraAuthorization = AVCaptureDevice.authorizationStatus(for: .video)
    }

    private func requestLocalNetworkPermission() {
        localNetworkPermissionRaw = LocalNetworkPermissionState.requesting.rawValue
        Task { @MainActor in
            let allowed = await localNetworkRequester.request()
            localNetworkPermissionRaw = (allowed
                ? LocalNetworkPermissionState.allowed
                : LocalNetworkPermissionState.denied).rawValue
        }
    }
}

enum CameraPrimaryAction: Equatable {
    case requestPermission
    case openSettings
    case requestLocalNetwork
    case requestingLocalNetwork
    case openLocalNetworkSettings
    case unavailable
    case startStreaming
    case stopStreaming

    init(authorization: AVAuthorizationStatus,
         localNetwork: LocalNetworkPermissionState = .allowed,
         usesUSB: Bool = false,
         isStreaming: Bool,
         snapshotMode: Bool = false) {
        if isStreaming {
            self = .stopStreaming
        } else if snapshotMode {
            self = .startStreaming
        } else {
            switch authorization {
            case .notDetermined: self = .requestPermission
            case .denied: self = .openSettings
            case .restricted: self = .unavailable
            case .authorized:
                if usesUSB {
                    self = .startStreaming
                } else {
                    switch localNetwork {
                    case .unknown: self = .requestLocalNetwork
                    case .requesting: self = .requestingLocalNetwork
                    case .allowed: self = .startStreaming
                    case .denied: self = .openLocalNetworkSettings
                    }
                }
            @unknown default: self = .unavailable
            }
        }
    }

    var title: String {
        switch self {
        case .requestPermission: "Allow camera access"
        case .openSettings: "Open camera settings"
        case .requestLocalNetwork: "Allow local network access"
        case .requestingLocalNetwork: "Waiting for permission..."
        case .openLocalNetworkSettings: "Open local network settings"
        case .unavailable: "Camera access unavailable"
        case .startStreaming: "Start streaming"
        case .stopStreaming: "Stop streaming"
        }
    }

    var systemImage: String {
        switch self {
        case .requestPermission: "camera.badge.ellipsis"
        case .openSettings: "gearshape.fill"
        case .requestLocalNetwork, .requestingLocalNetwork: "wifi"
        case .openLocalNetworkSettings: "gearshape.fill"
        case .unavailable: "camera.fill"
        case .startStreaming: "play.fill"
        case .stopStreaming: "stop.fill"
        }
    }
}

private struct LegalLinks: View {
    private let privacy = URL(string: "https://ibrahimethem.github.io/Free-Cam-App/privacy/")!
    private let terms = URL(string: "https://ibrahimethem.github.io/Free-Cam-App/terms/")!
    private let support = URL(string: "https://ibrahimethem.github.io/Free-Cam-App/support/")!

    var body: some View {
        VStack(alignment: .leading, spacing: 9) {
            Text("LEGAL & SUPPORT")
                .font(.caption.weight(.semibold))
                .tracking(1.2)
                .foregroundStyle(StudioTheme.muted)
            HStack(spacing: 16) {
                Link("Privacy Policy", destination: privacy)
                    .accessibilityIdentifier("legal.privacy")
                Link("Terms of Use", destination: terms)
                    .accessibilityIdentifier("legal.terms")
                Link("Support", destination: support)
                    .accessibilityIdentifier("legal.support")
            }
            .font(.footnote.weight(.semibold))
            .foregroundStyle(StudioTheme.accent)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.top, 6)
    }
}
