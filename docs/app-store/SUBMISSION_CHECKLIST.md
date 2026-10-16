# NoSub Cam submission checklist

Status date: 2026-10-15. This is a product/compliance working checklist, not legal
advice. Apple requirements and laws may change; recheck official documentation at
submission time.

## Completed in the repository

- [x] Product name selected: **NoSub Cam**; desktop companion: **NoSub Studio**.
- [x] Camera and Local Network purpose strings exist and describe the core use.
- [x] Local networking is limited to user-entered private IPv4/Bonjour receiver
      addresses or direct USB.
- [x] No account, developer backend, ad SDK, analytics SDK, or tracking code found.
- [x] Receiver address is the only app preference intentionally persisted.
- [x] Pairing key remains in session memory and is not intentionally persisted.
- [x] Draft English privacy policy created.
- [x] Draft English supplemental terms created.
- [x] Draft support page, metadata, privacy answers, and review notes created.
- [x] Privacy manifest declares no tracking/data collection and declares the
      app-only UserDefaults reason `CA92.1`.
- [x] Export-compliance plist value added as `ITSAppUsesNonExemptEncryption = NO`.
- [x] iOS project builds and its automated tests pass on iOS Simulator.
- [x] Desktop/receiver automated tests pass on macOS.

## Blocking: owner information and decisions

- [x] Publisher name selected: **İbrahim Ethem Karalı**.
- [x] Public support email selected: **nosubcam-support@ethemkarali.com**.
- [x] Website selected: **https://ibrahimethem.github.io/Free-Cam-App/** with `/privacy/`,
      `/terms/`, `/support/`, and `/download/` paths.
- [x] Governing jurisdiction drafted as the Republic of Türkiye, subject to review.
- [x] Availability decision: use all storefronts that do not require extra filings;
      initially omit China mainland unless its ICP requirement is completed.
- [x] EU DSA recommendation: **non-trader** for this app because it is a personal,
      permanently free, non-commercial project with no ads, purchases, subscription,
      or promotion of paid services. Reassess if the purpose or monetization changes.
- [x] Publisher/account model: individual.
- [x] Use Apple's Standard EULA for v1 and publish the supplemental terms separately.
- [ ] Decide whether the source code will have an open-source license. “Free of
      charge” does not automatically mean “open source.”
- [x] Launch language selected: English only.

## Blocking: product and technical work

- [x] Final bundle ID selected and applied: `com.ethem.nosubcam`.
- [x] Original 1024px App Store icon created in Figma and added to the asset catalog.
- [x] Replace user-visible “Free Cam” branding with NoSub branding. Internal
      source, target, and packaging names remain unchanged for now.
- [ ] Pair the physical iPhone with Xcode, choose the signing team, build, install,
      and complete real Wi-Fi and Direct USB tests.
- [ ] Test permission-denied, wrong-key, disconnect/reconnect, background/foreground,
      front/rear camera, all supported resolutions, and long sessions.
- [ ] Package, sign, notarize, and host NoSub Studio for macOS. Provide an equally
      reviewable Windows download or state supported platforms accurately.
- [ ] Ensure the desktop package has an appropriate local-network usage description,
      camera description, hardened runtime/signing configuration, and update path.
- [ ] Provide a stable HTTPS companion download page. App Review cannot reasonably
      test the iPhone app without the receiver.
- [ ] Consider an on-device demonstration/read-only mode to reduce App Review risk
      when companion installation or physical-camera access is unavailable.
- [ ] Add in-app access to the published Privacy Policy and Terms URLs once known.
- [ ] Perform a VoiceOver, Voice Control, Dynamic Type, contrast, and keyboard audit
      before claiming accessibility support in App Store Connect.
- [ ] Generate an Xcode privacy report/archive and inspect the final binary, including
      every linked SDK, before confirming the privacy answers.

## Blocking: website and legal publication

- [ ] Add the App Review phone number in international format; it is the only
      remaining personal-information placeholder.
- [ ] Have the privacy policy and terms reviewed for the publisher's jurisdictions.
- [ ] Publish Privacy, Terms, and Support at stable public HTTPS URLs without login.
- [ ] Make the Support page show real contact information as required by applicable
      law and App Store Connect.
- [ ] Add policy version/effective date and preserve previous policy versions.
- [ ] Test all URLs from a logged-out browser and a different network.

## Blocking: App Store Connect

- [ ] Enroll/renew the Apple Developer Program and accept current agreements.
- [ ] Create the app record using final name, SKU, bundle ID, primary language, and
      category. SKU and bundle ID choices have long-term consequences.
- [ ] Enter Privacy Policy URL and publish the App Privacy answer.
- [ ] Enter Support URL; Marketing URL is optional.
- [ ] Complete age-rating questionnaire and confirm the generated rating.
- [ ] Complete DSA status and any regional compliance declarations.
- [ ] Confirm content-rights declaration and “Made for Kids: No.”
- [ ] Complete encryption/export questions consistently with the final binary.
- [ ] Add review contact name, email, and international-format phone number.
- [ ] Paste and verify review notes; attach any requested supporting material.
- [ ] Upload at least one accepted iPhone screenshot. Prepare 3–6 polished screenshots
      showing connection, privacy promise, preview, and desktop controls.
- [x] Add English Fastlane metadata and deterministic screenshot automation.
- [x] Run the screenshot lane and visually approve the generated screenshots.
- [ ] Upload the signed archive, select the build, resolve processing warnings, and
      run TestFlight testing before review.
- [ ] Choose manual or automatic release and complete pricing/availability.

## Recommended App Privacy answer for the current build

Select **“No, we do not collect data from this app.”** Apple's definition focuses on
data transmitted off-device in a form accessible to the developer or its partners
beyond servicing the real-time request. Here, the publisher has no backend access;
the user sends video directly to their own receiver. Reassess immediately if crash
reporting, analytics, hosted relay, account, support upload, or remotely measured
donations are added.

## Items not required for v1

- A custom EULA is optional because Apple supplies a Standard EULA.
- A Marketing URL is optional.
- An app preview video is optional.
- An account-deletion flow is not needed while the app has no account creation.
- App Tracking Transparency permission is not needed while there is no tracking.
- A User Privacy Choices URL is optional and unnecessary while the publisher holds no
  user dataset or account.
