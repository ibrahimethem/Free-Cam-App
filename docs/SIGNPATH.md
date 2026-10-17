# SignPath Foundation preparation

Status: **preparing an eligibility application, not accepted or signed yet**.
Owner approved MIT licensing of original project code and Foundation publisher
identity on October 17, 2026. Third-party software retains its original licenses.

## Public application facts

- Project: NoSub Studio / NoSub Cam
- Repository: https://github.com/ibrahimethem/Free-Cam-App
- Homepage: https://ibrahimethem.github.io/Free-Cam-App/
- Downloads: https://ibrahimethem.github.io/Free-Cam-App/download/
- Privacy: https://ibrahimethem.github.io/Free-Cam-App/privacy/
- Code signing policy: https://ibrahimethem.github.io/Free-Cam-App/code-signing/
- Maintainer / committer / reviewer / approver: İbrahim Ethem Karalı,
  https://github.com/ibrahimethem
- Contact: nosubcam-support@ethemkarali.com (public support contact)
- License: MIT for original code; upstream licenses preserved.
- Build system: GitHub Actions, GitHub-hosted Windows runners.
- Tagline: A subscription-free local iPhone webcam for macOS and Windows.
- Description: NoSub Cam captures video on an iPhone and sends it directly to
  NoSub Studio over a trusted local network or USB. The desktop receiver provides
  camera controls and native webcam output without accounts, a cloud relay,
  advertising, analytics or subscription fees.
- Reputation: New independent project undergoing owner testing on macOS and
  Windows. No established user/download statistics or independent endorsements
  are claimed. Source history and automated checks are public. This is an initial
  eligibility inquiry, not a claim of established reputation.

## Disclosures and prerequisites — do not silently bypass

The Foundation normally expects an already released project with verifiable
reputation. At preparation time there is **no public release**: Mac DMG is locally
signed/notarized, Windows installer exists as an unsigned Actions test artifact.
Do not put an Actions URL forward as a public, account-free release download.
Ask the Foundation whether a new project at this stage is eligible; acceptance
must not be represented as automatic.

`NoSubCamera.dll` contains modified MIT Microsoft Windows-Camera sample code
staged by `prepare_source.py`, not a visibly maintained GitHub fork. Disclose this
and obtain explicit guidance/approval for signing it. Do not claim the standard
Foundation upstream-fork requirements are already satisfied. Do not create a
cosmetic fork merely to misrepresent provenance.

The bundled runtime audit in `THIRD_PARTY_NOTICES.md` is still a public-release
gate. Do not claim MIT covers Qt/Python/FFmpeg or every collected dependency.
MFA must be enabled for repository and signing-service access. The maintainer
must personally approve production signing requests.

## Prepared integration (first phase only)

`windows-camera.yml` has an optional `request_signing` manual input (false by
default). Signing is restricted to `main`, uses GitHub-hosted builds and a
commit-pinned official SignPath Action, and requires all these settings:

- Protected environment: `windows-signing`, deployment branch restricted to
  `main`, maintainer approval required. Creation was blocked pending the owner's
  explicit authorization of this access-control change. It has **not** been
  created or connected to the workflow yet. Do not add credentials or enable
  signing until that protection and workflow binding are in place.
- Environment secret: `SIGNPATH_API_TOKEN` in `windows-signing`, **not** an
  unrestricted repository secret (never commit or print its value).
- Variable: `SIGNPATH_ORGANIZATION_ID` (returned by the accepted account).
- Variable: `SIGNPATH_CERTIFICATE_THUMBPRINT` (approved certificate's public
  40-character SHA-1 identifier, not the private key).
- Project slug: `nosub-studio`.
- Signing policy slug: `release-signing`, configured to require manual approval.
- Artifact configuration slug: `nosub-studio-binaries-v1`, candidate XML in
  `desktop/packaging/signpath-binaries.xml` (Foundation must approve scope).

Exact targets: `FreeCam.exe`, `_internal/native-camera/NoSubCamera.dll` and
`_internal/native-camera/NoSubCameraSetup.exe`. There is deliberately no wildcard
that signs upstream Python/Qt/runtime binaries. Version/product metadata is
provided for all three targets. The workflow verifies Windows trust, pinned
signer, a timestamp and product/version before uploading signed output.

This is **not yet a signed installer pipeline**. Returned files are not silently
inserted into the unsigned TEST installer. After account/scope acceptance:

1. Validate service XML against its actual schema and test the signing request.
2. Integrate signed binaries into both PyInstaller and protected camera payloads.
3. Implement Inno's separately signed, cached uninstaller stage and its
   GitHub-artifact-origin signing request. Verify the signed cache.
4. Build installer with that uninstaller, then sign and verify the outer installer
   via a separate approved artifact configuration/request.
5. Generate checksums only after final signing; rebuild Mac package with the
   approved license/notices before publishing a coordinated release.

Production packaging currently fails closed. The staged signing phase must not
be advertised as completed Windows installer signing.

References: https://signpath.org/terms.html,
https://docs.signpath.io/trusted-build-systems/github,
https://jrsoftware.org/is6help/topic_setup_signeduninstaller.htm
