# Apple Release Architecture

Status: `ALIGNED`  
Scope: Platform Release Engineering Generation 1

## Canonical artifacts

Apple release engineering produces exactly two canonical artifacts for an
`INTERNAL_RELEASE`:

1. **Universal iOS IPA** — one `DJConnectIOS` archive and IPA for iPhone and
   iPad, containing the DJConnect Apple Watch companion app.
2. **Native macOS application** — the `DJConnectMac` application, distributed
   in the signing/notarization envelope appropriate to the selected internal
   release workflow. A ZIP, DMG or PKG is a transport envelope, not a separate
   platform artifact.

visionOS is deferred for Generation 1. It is not an input to the Apple release
plan and no visionOS artifact is expected.

## Objective project evidence

The evidence was read from live `pcvantol/djconnect-app` `main` at
`d9a9ef944e944ad0f27739ae580b6192ae595172` on 2026-07-13.

- `project.yml` defines one `DJConnectIOS` application target with
  `TARGETED_DEVICE_FAMILY: "1,2"`. Xcode therefore produces one universal iOS
  product for iPhone and iPad; no iPad-only target or scheme exists.
- That target depends on `DJConnectWatch` with `embed: true`. The generated
  project has an `Embed Watch Content` copy phase that embeds the Watch
  `DJConnect.app` in the iOS product. The Watch target is a build component of
  the iOS archive, not a third release artifact.
- `DJConnectMac` is a separate native macOS application target and has its own
  `DJConnectMac` scheme. It is therefore the second canonical artifact.
- The `DJConnectIOS` scheme is archived by the Apple TestFlight workflow and
  exported through `xcodebuild -exportArchive`, which locates one `*.ipa`.
- Apple CI and deployment workflows run on the qualified self-hosted Apple
  runner. The Platform Release Runtime does not build the Apple applications.

Apple's current documentation supports this interpretation: Xcode maps the
Targeted Device Family setting to iPhone (`1`) and iPad (`2`), and its
registered-device distribution guidance describes a single exported iOS App
(`.ipa`) installed through the paired phone for a watchOS device. See
[Apple: iOS Keys](https://developer.apple.com/library/archive/documentation/General/Reference/InfoPlistKeyReference/Articles/iPhoneOSKeys.html) and
[Apple: Distributing your app to registered devices](https://developer.apple.com/documentation/xcode/distributing-your-app-to-registered-devices?changes=_1).

## Runtime contract

The Platform Release Runtime models the Apple repository artifact inventory as:

```text
apple/universal-ios-ipa
  includes: iPhone, iPad, Apple Watch companion app

apple/native-macos-application
  includes: macOS application package
```

It must not request a separate iPad IPA or a separate Apple Watch release
artifact unless a future Apple platform decision objectively changes the target
or packaging model. The Runtime dispatches the approved Apple workflow and
consumes its evidence only; GitHub Actions on the qualified macOS runner owns
archive, signing, export and artifact upload.

## Decision

`APPLE_RELEASE_ARCHITECTURE_ALIGNED`
