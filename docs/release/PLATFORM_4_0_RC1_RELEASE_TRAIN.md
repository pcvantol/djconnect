# Platform 4.0 Release Candidate Train

**Status:** Proposed release train; not a publication or deployment authority.

## Purpose

This document defines the coordinated first DJConnect 4.0 release candidate.
It is required because the architecture and its cross-repository protocol
contracts move together. No individual 3.3 component may be relabelled as 4.0
in isolation.

## Canonical versioning

| Field | Value |
| --- | --- |
| Public candidate tag | `v4.0.0-rc.1` |
| Public display version | `4.0.0-rc.1` |
| Runtime protocol train | `4.0` |
| Stable successor | `4.0.0` |

### Native package mapping

The public platform candidate identity remains `4.0.0-rc.1` everywhere it can
be represented: Git tags, GitHub prereleases, release manifests, checksums and
runtime reporting. Native package formats with numeric-only version fields use
bundle/display version `4.0.0` and build `40001`; their release metadata must
still expose the public candidate identity `4.0.0-rc.1`. This applies to Apple
and Windows package metadata and avoids inventing incompatible platform-local
pre-release syntax.

The protocol train deliberately excludes the prerelease suffix. Every runtime
must parse the public SemVer candidate while enforcing compatibility on
`major.minor == 4.0`. A 3.3 runtime and a 4.0 runtime are incompatible.

## Required release participants

- Home Assistant integration: `pcvantol/djconnect`
- Raspberry Pi native appliance: `pcvantol/djconnect-pi`
- Apple clients: `pcvantol/djconnect-app`
- Windows client: `pcvantol/djconnect-windows`
- ESP32 firmware: `pcvantol/djconnect-esp32`
- Central API / APNs relay: `pcvantol/djconnect-api`
- Receiver presentation artifacts and their source repositories where their
  contract declares a release version.

Each participant owns its source version, parser tests, release artifact,
checksum and release notes. Distribution repositories remain artifact-only.

## Candidate gates

1. Every participant accepts `4.0.0-rc.1` and reports protocol train `4.0`.
2. Cross-client pairing, status and command contracts reject 3.3/4.0 mixes
   with a clear version-mismatch response; credentials remain intact.
3. Pi publishes and verifies both `pi5-arm64` and `pi-zero-2w-arm64` artifacts.
4. Target smoke evidence covers Home Assistant, Pi Zero, Pi 5 wall appliance,
   Apple, Windows and ESP32 paths that are available for the candidate.
5. No public stable tag, HACS publication, OTA promotion or store submission
   occurs before explicit release authorization.

## Execution order

1. Merge and publish the profile-aware Pi artifact pipeline.
2. Make version parsing and protocol-train assertions SemVer-RC aware in every
   source repository.
3. Bump all source display versions to `4.0.0-rc.1` and their runtime protocol
   contracts to `4.0` in coordinated pull requests.
4. Build candidate artifacts, bind them into one immutable platform manifest,
   then deploy only to authorized internal targets.
5. Collect smoke evidence and decide whether to promote `4.0.0-rc.1`, issue a
   further RC, or return to source work.

## Non-goals

- This does not publish, deploy, retag or declare Platform 4.0 qualified.
- This does not weaken the existing 3.3 release evidence.
- This does not turn the marketing website into a runtime distribution owner.
