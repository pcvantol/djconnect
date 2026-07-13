# Native Runner Deployment Matrix

Status: `NATIVE_RUNNER_ALIGNMENT_COMPLETE`

| Platform | Source-build runner | Qualification evidence | Artifact hand-off | Deployment boundary |
| --- | --- | --- | --- | --- |
| Apple | qualified self-hosted macOS | run 29246454969 | unsigned artifact evidence; signed internal delivery remains profile-controlled | Apple deployment consumes the qualified artifact. |
| Windows | qualified self-hosted Windows | run 29246684022 | unsigned Windows ZIP and SHA evidence | Windows deployment consumes the qualified artifact. |
| HA, API, Website, ESP32, Pi | GitHub-hosted Linux, per corrected architecture | outside this native alignment increment | their repository artifact contracts | ESP32/Pi remain artifact-consuming targets. |

The matrix records build locations only. It does not authorize deployment,
publication, TestFlight, App Store, tags or GitHub Releases.
