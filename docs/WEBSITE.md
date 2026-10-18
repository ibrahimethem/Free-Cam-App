# Website screenshots

The static website is deployed from `site/` through GitHub Pages, not Sites.
Keep the existing dark/orange visual language; screenshots are actual app
captures, not redrawn mockups.

Updated October 18, 2026:

- `site/assets/ios-preview.png` is an unmodified copy of the current English
  Fastlane iPhone 17 Pro Max `01WiFiConnection` capture (1320 × 2868). It uses
  snapshot-mode sample data, with no personal camera image or visible pairing key.
- `site/assets/studio-preview.png` is an unmodified copy of the packaged Windows
  public beta 1 demo capture (1400 × 900), from successful CI run `39158635643`,
  artifact `NoSub-Studio-Windows-x64-installer-test`, `windows-packaged-demo.png`.
  The capture shows the latest left-hand controls/presets and right-hand pairing/
  webcam section. No iPhone is connected. Sensor values/image are simulated;
  the demo deliberately disables native camera setup/output. The page says so.

No new iOS or desktop build is required just to reuse these captures. Do not
capture the running user's desktop session, expose live QR/pairing credentials,
or remove the simulated/demo disclosure to imply a real hardware test. For a
later desktop capture, use the actual packaged demo rather than an old installed
development app, with disposable settings and no private footage.

Each image URL includes the first 12 characters of its SHA-256 as `?v=...` so
browsers do not keep the previous screenshot after deployment. Image width and
height attributes match the PNG header. Update them when replacing assets.
`node site-tests/content.cjs` checks these facts and the current mobile source;
`node site-tests/downloads.cjs` checks signed/beta download separation.
