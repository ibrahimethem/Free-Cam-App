# NoSub Cam Fastlane workflow

Fastlane manages the English App Store metadata, screenshots, TestFlight builds,
privacy answer, and release upload for `com.ethem.nosubcam`. It never submits a
build for review automatically.

## One-time setup

1. Sign in to the Apple Developer account in Xcode and confirm team
   `G478PYWXZ4` can sign `com.ethem.nosubcam`.
2. Run `bundle install`.
3. Copy `fastlane/.env.example` to `fastlane/.env` and set the App Store Connect
   API key values plus `REVIEW_PHONE` in international format. Never commit this
   file or the `.p8` key.
4. Create the initial App ID/App Store record with
   `bundle exec fastlane ios create_app_record`, or create it manually in App
   Store Connect with SKU `nosub-cam-ios-001`.
5. Enable the included GitHub Pages workflow and confirm the Privacy, Support,
   Terms, Download, and root pages are live under
   `https://ibrahimethem.github.io/Free-Cam-App/` before uploading metadata.

## Commands

```sh
bundle exec fastlane ios validate_release
bundle exec fastlane ios screenshots
bundle exec fastlane ios store_assets
bundle exec fastlane ios privacy
bundle exec fastlane ios beta
bundle exec fastlane ios release
```

`release` captures screenshots, chooses the next TestFlight build number, builds
the signed IPA, and uploads the binary, metadata, and screenshots. It leaves
`submit_for_review` disabled, so the final build selection and App Review
submission remain manual in App Store Connect.

Use `bundle exec fastlane ios release screenshots:false` to reuse existing
screenshots. App Privacy upload currently requires Apple ID authentication because
Apple does not expose that operation through the official App Store Connect API.
