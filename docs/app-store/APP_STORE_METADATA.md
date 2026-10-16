# NoSub Cam App Store metadata draft

## Identity

- **App name:** NoSub Cam
- **Subtitle:** Local webcam, no subscription
- **Primary language:** English (U.S.)
- **Primary category:** Photo & Video
- **Secondary category:** Utilities
- **Price:** Free
- **SKU:** `nosub-cam-ios-001` (confirm before creating the record; SKU cannot be changed)
- **Bundle ID:** `com.ethem.nosubcam`
- **Copyright:** `2026 İbrahim Ethem Karalı`
- **Made for Kids:** No
- **Content rights:** Does not contain, show, or access third-party content as a core feature

## Promotional text

Turn your iPhone into a local Wi-Fi or USB camera. No account, cloud relay, ads,
tracking, or subscription.

## Description

NoSub Cam turns your iPhone into a camera source for your Mac or Windows PC —
without an account, cloud relay, advertising, or subscription.

Connect over your trusted local Wi-Fi network or use Direct USB. NoSub Studio, the
free desktop companion, shows the live preview and lets you choose the rear or front
camera, portrait or landscape output, and supported settings including ISO, shutter
speed, focus, white balance, zoom, and resolution.

FEATURES

• Local Wi-Fi and Direct USB connections
• Rear and front camera support
• Portrait and landscape output controlled from the desktop
• Manual and automatic camera controls
• Supported 480p, 720p, 1080p, and 4K capture presets
• Pairing key required for each receiver session
• No account, cloud storage, analytics, advertising, or tracking
• No subscription

NoSub Cam does not intentionally record or upload your video to the publisher.
Wi-Fi mode sends video over unencrypted HTTP on your local network, so use a private
network you trust and never expose the receiver port to the public internet.

The free NoSub Studio companion app is required on macOS or Windows. OBS Studio is
currently required to expose the stream as a virtual webcam to other applications.
Availability and frame rate depend on the iPhone, selected resolution, connection,
and computer.

## Keywords

`webcam,iphone camera,usb camera,wifi camera,obs,streaming,local camera,manual focus`

Recheck the final UTF-8 byte count in App Store Connect; the field allows 100 bytes.
Do not add competitor or third-party product names solely for search ranking.

## URLs

- **Privacy Policy URL:** `https://ibrahimethem.github.io/Free-Cam-App/privacy/`
- **Support URL:** `https://ibrahimethem.github.io/Free-Cam-App/support/`
- **Marketing URL:** `https://ibrahimethem.github.io/Free-Cam-App/`
- **User Privacy Choices URL:** omit; there is no account or publisher-held dataset

## App Privacy answers

Proposed answer based on the audited source code:

- **Do you or your third-party partners collect data from this app?** No

Rationale: NoSub Cam has no publisher backend, analytics, ads, tracking SDK, or
account system. The user directs real-time camera content to their own selected
desktop receiver; the publisher and third-party partners cannot access it. Revisit
this answer before every release and whenever an SDK, crash reporter, hosted relay,
support upload, donation analytics, or account feature is added.

## Age rating questionnaire proposal

Answer **None** or **No** for violence, sexual content, profanity, controlled
substances, gambling, horror, medical content, unrestricted web access, loot boxes,
and user-generated content. Confirm the resulting rating in App Store Connect.

## Encryption/export proposal

`ITSAppUsesNonExemptEncryption = NO`. The app implements no proprietary encryption
and currently uses unencrypted local HTTP or Apple's local USB transport. Reassess if
TLS, VPN functionality, or custom cryptography is added.

## Accessibility claims

Do not claim an App Store accessibility feature until it is tested on a physical
device. The current controls include several accessibility labels, but VoiceOver,
Voice Control, Larger Text, sufficient contrast, and reduced-motion behavior still
need a documented audit.
