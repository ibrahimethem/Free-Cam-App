import Foundation
import CoreMediaIO

let source = CameraProvider()
CMIOExtensionProvider.startService(provider: source.provider)
dispatchMain()
