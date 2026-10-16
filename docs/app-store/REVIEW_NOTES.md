# NoSub Cam App Review notes draft

Replace all bracketed fields and verify every step on the submitted build.

## Suggested Notes field

NoSub Cam turns an iPhone into a camera source for a user-operated macOS or Windows
receiver. It has no account or login.

The free NoSub Studio companion app is required to exercise the complete feature:
https://ibrahimethem.github.io/Free-Cam-App/download/

Test using Wi-Fi:

1. Install and open NoSub Studio on a Mac or Windows PC on the same private network
   as the review iPhone.
2. Keep “NoSub Cam - Wi-Fi” selected in NoSub Studio.
3. In NoSub Cam, select WI-FI and enter the receiver address and pairing key shown by
   NoSub Studio.
4. Tap Start streaming and approve Camera and Local Network permissions.
5. The live preview and camera capabilities appear in NoSub Studio. Camera settings
   can then be changed from its right panel.

Direct USB is optional for review and requires an unlocked/trusted physical iPhone.
The app's core experience can be reviewed over local Wi-Fi.

Privacy behavior:

- No account, analytics, advertising, tracking, or publisher-operated backend.
- Camera frames go directly to the reviewer-operated desktop receiver.
- Wi-Fi uses local unencrypted HTTP. The pairing key authenticates but does not
  encrypt the stream.
- The receiver keeps only the latest frame in memory and does not intentionally
  record video.

The iOS Simulator cannot provide real camera capture. A physical iPhone and the
companion app are needed for an end-to-end test.

Review contact:

- Name: İbrahim Ethem Karalı
- Email: nosubcam-support@ethemkarali.com
- Phone: [REVIEW_CONTACT_PHONE_IN_INTERNATIONAL_FORMAT]

## Review-readiness warning

Do not submit until the companion URL is public, stable, HTTPS, and points to a
signed/notarized package with straightforward installation instructions. Test the
URL and the exact review steps from a clean Mac or Windows account.
