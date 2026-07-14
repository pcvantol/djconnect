# Platform Release 3.3 — Operational Manifest Preparation

Date: 2026-07-14  
Decision: `PLATFORM_RELEASE_3_3_MANIFEST_PREPARATION_BLOCKED`

## Scope

This is the operator-authorized preparation record for the requested `3.3.0`
`INTERNAL_RELEASE`. It records a fresh remote-`main` source snapshot and the
private target scope supplied by the maintainer. It is not an approved
operational manifest, artifact publication request, deployment authorization
or smoke authorization.

No workflow was dispatched, no artifact was built or published, no credential
was read and no target was contacted.

## Exact source snapshot

| Repository | Remote `main` SHA | Release role |
| --- | --- | --- |
| `pcvantol/djconnect` | `ed057cceefccfe982d698da415eb9eae9da4b3ed` | Home Assistant source and canonical platform control |
| `pcvantol/djconnect-api` | `835f682709556c18fbe702ffef358732f8173525` | API source |
| `pcvantol/djconnect-app` | `a2a65f34c3d17403f7b766511ccd80043f486454` | Apple source and unsigned artifact producer |
| `pcvantol/djconnect-windows` | `6c0c3c3478c81472e479184dc03e51fd095dc4b2` | Windows source |
| `pcvantol/djconnect-pi` | `c300a7514daedbffdcc1e21185eca52290954a0c` | Raspberry Pi source and deployment consumer |
| `pcvantol/djconnect-esp32` | `fe4a1dd591c50f1734a37d86e8b8b915f384dc64` | ESP32 source |
| `pcvantol/djconnect-website` | `5630f0cf8497b16428aa62ec4d63a48ee57e8ff3` | Website source |
| `pcvantol/djconnect-firmware` | `f3a6af6eaa9bb7dbfa553201eac971b811b5b9ff` | Firmware distribution |
| `pcvantol/djconnect-app-releases` | `938c8aa73b28e67984301d0943ce4af1a7bd72ac` | Internal Apple handoff metadata; not a public signed distribution target |
| `pcvantol/djconnect-pi-releases` | `c8c1f7fa470ab8de00457d6b201a6563d6eee2d2` | Pi distribution |

## Requested required targets

The maintainer requested private production delivery to the following targets.
These are proposed required targets only until the final manifest receives a
separate explicit approval.

| Surface | Canonical target | Extra binding |
| --- | --- | --- |
| Home Assistant | `home_assistant_pi5` | private installation scope |
| API | `cloudflare_workers_production` | production Worker scope |
| Website | `cloudflare_pages_production` | production Pages scope |
| ESP32 | `esp32_lilygo_t_embed_s3` | approved HA Update entity/hardware scope |
| Raspberry Pi | `rbpi-djconnect` | private relay scope |
| Apple macOS | `apple_private_device` | `target_device=macbook` |
| Apple iOS | `apple_private_device` | `target_device=iphone`, `paired_watch_validation=required` |
| Apple iPadOS | `apple_private_device` | `target_device=ipad` |
| Windows | `windows_internal_arm64` | private ARM64 installation scope |

Apple Watch remains an embedded companion validation for the universal iOS
artifact. It is not a direct deployment target, separate artifact or public
App Store/TestFlight release.

## Artifact-binding status

Every deployable artifact binding remains missing. The GitHub releases visible
at preparation time are 3.2.x or unrelated governance releases; none is a
qualified `3.3.0` artifact bound to the source SHAs above. In particular,
there is no current immutable 3.3 firmware binary, Pi tarball, unsigned Apple
artifact, Windows package, API/website build artifact or Home Assistant
artifact with a SHA-256 digest that can be placed in an operational manifest.

`djconnect-app-releases` is deliberately excluded from signed public
publication for this Internal Release. It may carry non-secret handoff
metadata only after the `djconnect-app` artifact identity is available.

## Required completion conditions

1. Build or publish each required immutable artifact from the exact source
   snapshot, retaining its artifact ID, SHA-256 and provenance.
2. Bind fresh exact-SHA verification, Software Assurance, Trusted Delivery,
   coverage and platform-qualification evidence to those artifacts.
3. Record target-specific installation/credential scopes without exposing
   secrets, and configure the approved manifest source consumed by deployment
   and smoke workflows.
4. Replace the proposal JSON with a complete manifest containing no null or
   placeholder artifact binding.
5. Obtain a separate explicit approval of that complete manifest before any
   artifact publication, deployment or smoke dispatch.

## Current blocker

`PLATFORM_RELEASE_3_3_MANIFEST_PREPARATION_BLOCKED`: target scope and current
source identities are known, but the required immutable artifacts, checksums,
candidate-bound evidence and final manifest approval are absent.
