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

## Runtime and secure distribution contract

The Platform Release Runtime models the Apple repository artifact inventory as:

```text
apple/universal-ios-ipa
  includes: iPhone, iPad, Apple Watch companion app

apple/native-macos-application
  includes: macOS application package
```

It must not request a separate iPad IPA or a separate Apple Watch release
artifact unless a future Apple platform decision objectively changes the target
or packaging model.

Apple Internal Distribution is a separate deployment capability:

```text
qualified Apple build -> immutable unsigned artifact + checksum
  -> approved manifest / draft internal release record
  -> Apple Secure Distribution Relay
  -> local signing -> approved private device -> evidence
```

This is the Apple-specific application of the canonical macOS capability
model: Apple Native Build is CI / Qualification or Artifact Build, while Apple
Secure Distribution Relay is Deployment. Private-Network Deployment Relay is a
separate Deployment capability and never shares its credentials or workspace
with Apple signing.

The qualified Apple build workflow is the sole source of unsigned artifacts.
The secure distribution relay consumes only the exact manifest-bound artifact;
it cannot compile source, build an IPA or macOS binary, archive source,
generate unsigned artifacts, choose an artifact, create a GitHub Release,
publish TestFlight or publish to the App Store.

Before local signing, the relay validates the candidate SHA, manifest ID,
artifact ID, SHA-256 checksum, platform version, `INTERNAL_RELEASE` profile
and explicitly allowlisted `target_device`. Generation 1 direct targets are
the maintainer's MacBook, iPhone and iPad, represented by the typed values
`macbook`, `iphone` and `ipad`. They are private Developer provisioning targets
only; TestFlight, App Store and public distribution remain deferred.

Apple Watch is an embedded companion of the universal iOS IPA, not a direct
deployment target, separate artifact, release candidate, signing flow or
manifest node. The manifest binds `paired_watch_validation=required|optional|disabled`
for an iPhone or iPad target. The relay may validate paired-Watch availability,
companion bundle presence/install state, companion bundle version and iOS-app
compatibility. A future standalone watchOS product requires an explicit Apple
architecture decision before direct Watch deployment or an independent Watch
artifact/manifest/signing flow is introduced.

Apple certificates, private signing keys and provisioning profiles remain only
in the qualified macOS runner's local signing environment. They are never
stored in GitHub secrets, exported, uploaded or included in evidence. The
Apple signing job is separate from Apple build, Pi SSH, Home Assistant and ESP
OTA credential scopes.

After installation, the relay reads installed bundle version and identifier,
candidate identity where available, device availability and application launch
where supported. It uploads redacted evidence with the candidate SHA, manifest
and artifact checksum, non-secret signing identity, target device, bundle
version, timestamps, runner/workflow identity, deployment result and health
validation. A failure is fail-closed and never alters build or qualification
evidence.

## Decision

`APPLE_RELEASE_ARCHITECTURE_ALIGNED`
