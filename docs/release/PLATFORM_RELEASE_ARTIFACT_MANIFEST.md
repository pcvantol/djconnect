# Platform Release 3.3 — Artifact Manifest

Execution state: `MANIFEST_APPROVED_DEPLOYMENT_DISPATCH_PENDING`.

The requested `3.3.0` `INTERNAL_RELEASE` now has immutable, checksum-bound
artifacts for every required deployment target. The Raspberry Pi artifact was
republished from a newly qualified source candidate and the canonical,
machine-readable binding has been explicitly reapproved:
[`PLATFORM_3_3_CURRENT_MAIN_MANIFEST_PROPOSAL.json`](PLATFORM_3_3_CURRENT_MAIN_MANIFEST_PROPOSAL.json).
It is checksum-verified release evidence, not a deployment dispatch authorization.

| Surface | Exact candidate SHA | Artifact ID | SHA-256 |
| --- | --- | --- | --- |
| Home Assistant | `0227e95b` | `8347737416` | `88c065ca672e7ba7155a30aa7b4737075d41e629cc748c8a60385ae1a3464aa9` |
| API | `6f6dee8a` | `8323208436` | `f9d8c29787297a939d16e6f3fab3f9cd4455518def4565830b5ca57f76a80819` |
| Website | `64f95dcb` | `8346470431` | `dff7ba59c2cf3cd299670487d09ba6e98d845659736dfd0e9770e884e8127027` |
| ESP32 LilyGO T-Embed S3 | `9f8a3248` | `djconnect-lilygo-t-embed-s3-v3.3.0.bin` | `c25444d3ef414489848fd2d8de624785c82eb90195cc861bcb63085e0df3ceeb` |
| Raspberry Pi | `661e26e7` | `djconnect-pi-3.3.0.tar.gz` | `6fa3f2f3de6062b8d69c48886bf04374592bbbe404a2856b89450e1acbe1422a` |
| macOS | `dffdeb17` | `DJConnect-macOS-3.3.0-unsigned.zip` | `41137dfd346372a73ef0789394015fd94bfa6d7f416821dec65d58ab461b519a` |
| iPhone/iPad + paired Watch validation | `dffdeb17` | `DJConnect-iOS-3.3.0-unsigned.zip` | `f007fa2d5c95fc79a0c87ac51664365dd4ca059371eb57c0e84a7838ca695959` |
| Windows ARM64 | `6c0c3c34` | `DJConnect-Windows-arm64-3.3.0-unsigned.zip` | `cbe379826731deb1d16c8af5510b4190a4f4949b1bf6589925de5d1eb66c5b47` |

The ESP32, Pi and unsigned Apple/Windows artifacts are published through their
approved distribution repositories. HA, API and Website artifacts remain
immutable GitHub Actions artifacts consumed by their manifest-bound workflows.
The separate Windows x64 asset is intentionally not a required target binding.

The Pi target and API Worker target are already deployment-operational with
separately recorded deployment and smoke evidence. The rebound API artifact
exposes exact runtime release identity. The rebound exact manifest was
explicitly reapproved at `2026-07-14T20:03:33Z`; each remaining deployment and
its subsequent smoke still requires separate target-scoped authorization.
