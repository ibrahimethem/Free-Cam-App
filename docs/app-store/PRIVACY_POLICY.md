# NoSub Cam Privacy Policy

**Draft — review before publication**  
**Effective date:** October 15, 2026  
**Publisher:** İbrahim Ethem Karalı

NoSub Cam turns an iPhone into a camera source for a computer chosen by the user.
The app is designed to work without an account, advertising, analytics, tracking,
or a developer-operated cloud service.

## Information handled by the app

NoSub Cam handles the following information only to provide its camera-streaming
functionality:

- **Camera video.** When the user starts streaming and grants camera permission,
  the app captures video frames from the selected iPhone camera.
- **Camera settings and status.** The app exchanges camera capabilities, current
  sensor readings, requested settings, acknowledgements, and operational errors
  with the selected desktop receiver.
- **Connection information.** The user enters a local receiver address and a
  pairing key. The receiver address is stored in the app's private settings so it
  can be reused. The pairing key is kept only for the current app session and is
  not intentionally persisted by NoSub Cam.

## How information is used and transmitted

Camera video, camera settings, and status are sent directly to the receiver the
user selects:

- over the user's local Wi-Fi network using HTTP; or
- over a direct USB connection through Apple's device communication service.

The publisher does not operate an intermediary relay, account system, analytics
endpoint, advertising network, or storage service for this transmission. The app
does not send camera content to the publisher.

The desktop receiver keeps only the latest video frame in memory for live preview
and streaming. NoSub Cam and its companion receiver do not intentionally record or
archive video. Software chosen by the user, including broadcasting, conferencing,
or recording software, may process or retain video under its own terms and privacy
practices.

## Data collection and tracking

The publisher does not collect personal data through NoSub Cam and does not use
the app for tracking. The app contains no advertising or third-party analytics SDK.
Apple may process App Store, device, diagnostic, or purchase information under
Apple's own policies; that processing is controlled by Apple, not by NoSub Cam.

## Permissions

- **Camera:** required to capture the video selected by the user.
- **Local Network:** required when the user connects to a receiver on the same
  local network.

The user can change these permissions in iOS Settings. If permission is denied,
the related connection mode will not function.

## Security

The pairing key restricts access to the receiver but does not encrypt the video.
Wi-Fi mode uses unencrypted HTTP on the local network. Users should use NoSub Cam
only on a private network they trust and should not expose the receiver port to the
public internet. Direct USB avoids Wi-Fi transport but does not add application-level
encryption.

## Retention and deletion

The app stores the receiver address in its private app settings until the user
changes it or removes the app. The user can clear this information by deleting the
address in the app or uninstalling the app. Camera frames and pairing keys are not
intentionally retained by the app after the active session ends.

Because the publisher does not operate an account or backend and does not collect
app data, there is no publisher-held account or cloud dataset to access, export, or
delete.

## Children's privacy

NoSub Cam is a general-purpose utility and is not directed to children. The app
does not knowingly collect personal information from children.

## International use

The app performs its core processing on the user's devices and local connection.
The publisher does not transfer app content to a developer-operated service in
another country.

## Changes to this policy

This policy may be updated when the app's functionality or legal requirements
change. The effective date above will be updated when a revised policy is published.
Material changes will be described through the app, its website, or App Store
release information when appropriate.

## Contact

Questions about this policy or NoSub Cam can be sent to:

İbrahim Ethem Karalı  
nosubcam-support@ethemkarali.com  
https://ibrahimethem.github.io/Free-Cam-App/support/
