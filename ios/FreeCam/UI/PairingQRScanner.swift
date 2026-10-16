import AVFoundation
import SwiftUI
import UIKit

struct PairingCode: Equatable {
    enum Mode: String {
        case wifi
        case usb
    }

    let mode: Mode
    let address: String
    let key: String

    init(mode: Mode, address: String, key: String) {
        self.mode = mode
        self.address = address
        self.key = key
    }

    init?(value: String) {
        guard let components = URLComponents(string: value),
              components.scheme?.lowercased() == "nosubcam",
              components.host?.lowercased() == "pair" else { return nil }
        let query = components.queryItems ?? []
        func item(_ name: String) -> String? {
            query.first(where: { $0.name == name })?.value?
                .trimmingCharacters(in: .whitespacesAndNewlines)
        }
        guard let rawMode = item("mode"), let mode = Mode(rawValue: rawMode),
              let key = item("key"), !key.isEmpty, key.count <= 256 else { return nil }
        let address = item("address") ?? ""
        if mode == .wifi {
            guard !address.isEmpty,
                  (try? ReceiverConnection(address: address, key: key)) != nil else { return nil }
        }
        self.init(mode: mode, address: address, key: key)
    }
}

struct PairingScannerSheet: View {
    @Environment(\.dismiss) private var dismiss
    @State private var errorMessage = ""
    let onPair: (PairingCode) -> Void

    var body: some View {
        NavigationStack {
            ZStack {
                PairingScannerView { value in
                    guard let pairing = PairingCode(value: value) else {
                        errorMessage = "That is not a valid NoSub Cam pairing code."
                        return false
                    }
                    onPair(pairing)
                    dismiss()
                    return true
                }
                .ignoresSafeArea()

                RoundedRectangle(cornerRadius: 12)
                    .stroke(StudioTheme.accent, lineWidth: 3)
                    .frame(width: 248, height: 248)
                    .accessibilityHidden(true)
            }
            .safeAreaInset(edge: .bottom) {
                Text(errorMessage.isEmpty
                     ? "Point the camera at the QR code shown in NoSub Studio."
                     : errorMessage)
                    .font(.footnote.weight(.medium))
                    .multilineTextAlignment(.center)
                    .foregroundStyle(errorMessage.isEmpty ? StudioTheme.text : StudioTheme.accent)
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(StudioTheme.surface)
            }
            .navigationTitle("Scan pairing QR")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
            }
        }
        .tint(StudioTheme.accent)
    }
}

private struct PairingScannerView: UIViewControllerRepresentable {
    let onCode: (String) -> Bool

    func makeUIViewController(context: Context) -> PairingScannerViewController {
        PairingScannerViewController(onCode: onCode)
    }

    func updateUIViewController(_ controller: PairingScannerViewController, context: Context) {}
}

private final class PairingScannerViewController: UIViewController,
    AVCaptureMetadataOutputObjectsDelegate {
    private let session = AVCaptureSession()
    private let sessionQueue = DispatchQueue(label: "nosubcam.qr-scanner")
    private let onCode: (String) -> Bool
    private var previewLayer: AVCaptureVideoPreviewLayer?
    private var configured = false
    private var delivered = false

    init(onCode: @escaping (String) -> Bool) {
        self.onCode = onCode
        super.init(nibName: nil, bundle: nil)
    }

    @available(*, unavailable)
    required init?(coder: NSCoder) { fatalError("init(coder:) has not been implemented") }

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = .black
        switch AVCaptureDevice.authorizationStatus(for: .video) {
        case .authorized:
            configure()
        case .notDetermined:
            AVCaptureDevice.requestAccess(for: .video) { [weak self] granted in
                DispatchQueue.main.async {
                    if granted { self?.configure() }
                    else { self?.showError("Camera access is required to scan a pairing code.") }
                }
            }
        default:
            showError("Enable camera access in Settings to scan a pairing code.")
        }
    }

    override func viewDidLayoutSubviews() {
        super.viewDidLayoutSubviews()
        previewLayer?.frame = view.bounds
    }

    override func viewWillDisappear(_ animated: Bool) {
        super.viewWillDisappear(animated)
        sessionQueue.async { [session] in
            if session.isRunning { session.stopRunning() }
        }
    }

    private func configure() {
        guard !configured else { return }
        configured = true
        do {
            guard let device = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video,
                                                       position: .back) else {
                showError("No camera is available for QR scanning.")
                return
            }
            let input = try AVCaptureDeviceInput(device: device)
            let output = AVCaptureMetadataOutput()
            session.beginConfiguration()
            guard session.canAddInput(input), session.canAddOutput(output) else {
                session.commitConfiguration()
                showError("The camera cannot scan QR codes on this device.")
                return
            }
            session.addInput(input)
            session.addOutput(output)
            session.commitConfiguration()
            output.setMetadataObjectsDelegate(self, queue: .main)
            guard output.availableMetadataObjectTypes.contains(.qr) else {
                showError("QR scanning is unavailable on this camera.")
                return
            }
            output.metadataObjectTypes = [.qr]
            let layer = AVCaptureVideoPreviewLayer(session: session)
            layer.videoGravity = .resizeAspectFill
            layer.frame = view.bounds
            view.layer.insertSublayer(layer, at: 0)
            previewLayer = layer
            sessionQueue.async { [session] in session.startRunning() }
        } catch {
            showError(error.localizedDescription)
        }
    }

    private func showError(_ message: String) {
        let label = UILabel()
        label.text = message
        label.textColor = .white
        label.textAlignment = .center
        label.numberOfLines = 0
        label.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(label)
        NSLayoutConstraint.activate([
            label.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 28),
            label.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -28),
            label.centerYAnchor.constraint(equalTo: view.centerYAnchor),
        ])
    }

    func metadataOutput(_ output: AVCaptureMetadataOutput,
                        didOutput metadataObjects: [AVMetadataObject],
                        from connection: AVCaptureConnection) {
        guard !delivered,
              let object = metadataObjects.first as? AVMetadataMachineReadableCodeObject,
              object.type == .qr, let value = object.stringValue,
              onCode(value) else { return }
        delivered = true
        sessionQueue.async { [session] in
            if session.isRunning { session.stopRunning() }
        }
    }
}
