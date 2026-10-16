# NoSub Cam Support

**Public-page draft — replace bracketed fields before publication**

NoSub Cam turns an iPhone into a local camera source for macOS and Windows. It
requires the free NoSub Studio companion app on the receiving computer.

## Contact

- Support email: nosubcam-support@ethemkarali.com
- Typical response target: 5 business days
- Publisher: İbrahim Ethem Karalı

When asking for help, include the iPhone model, iOS version, computer operating
system, connection mode, and the exact error message. Do not send pairing keys,
private stream URLs, camera footage, or other sensitive content.

## Requirements

- iPhone running iOS 26 or later.
- macOS or Windows computer running NoSub Studio.
- For Wi-Fi: both devices on the same trusted private network.
- For Direct USB: a data-capable cable, an unlocked and trusted iPhone, and the
  Apple USB service available on the computer.
- OBS Studio is currently required when the stream must appear as a virtual webcam
  in conferencing or other applications.

## Quick setup

1. Install and open NoSub Studio on the computer.
2. Select Wi-Fi or Direct USB.
3. Enter the displayed receiver address and pairing key in NoSub Cam.
4. Grant camera and local-network permission when requested.
5. Tap **Start streaming** and keep NoSub Cam in the foreground.

## Common issues

### The iPhone cannot connect over Wi-Fi

Confirm both devices are on the same private Wi-Fi, local-network permission is
enabled for NoSub Cam, and the computer firewall allows NoSub Studio. Do not use
`127.0.0.1` as the receiver address on the iPhone.

### Direct USB does not list the iPhone

Unlock the iPhone, reconnect a data-capable cable, accept the Trust prompt, and
refresh devices in NoSub Studio. On Windows, Apple Mobile Device drivers/service
must be installed. On macOS the service is supplied by the operating system.

### Camera permission was denied

Open iOS **Settings > Privacy & Security > Camera** and enable NoSub Cam.

### Local-network permission was denied

Open iOS **Settings > Privacy & Security > Local Network** and enable NoSub Cam.

## Privacy and terms

- Privacy Policy: https://ibrahimethem.github.io/Free-Cam-App/privacy/
- Terms of Use: https://ibrahimethem.github.io/Free-Cam-App/terms/
