# Platform Release 3.3 Candidate Reconstruction Report

## Scope and result

Fresh candidate branches named `release/platform-3.3-candidate` were created
from the then-current `origin/main` of every Repository Ownership participant.
Historical dry-run SHAs were deliberately not reused.

The following candidate-source corrections were required:

| Repository | Corrected executable metadata |
| --- | --- |
| `pcvantol/djconnect` | Home Assistant runtime `VERSION` is `3.3.0`. |
| `pcvantol/djconnect-app` | XcodeGen `MARKETING_VERSION` is `3.3.0`. |
| `pcvantol/djconnect-windows` | Windows package and runtime contract are `3.3.0`. |

The Windows candidate also removes one stray closing brace from its existing
CI workflow. That malformed YAML was present on current `main` and prevented
GitHub Actions from planning Windows qualification jobs.

The API, website and Pi source already reported `3.3.0`. ESP32 keeps its
intentional source default `dev`; its release workflow must inject the
candidate version during a qualified GitHub-hosted Linux build. Distribution
repositories retain only their existing published artifacts and do not claim a
nonexistent 3.3 artifact.

No tag, GitHub Release, deployment, publication, firmware rollout or workflow
dispatch occurred.

## Decision

`PLATFORM_RELEASE_3_3_CANDIDATE_BLOCKED`

The branches are fresh and the identified source metadata is aligned, but
candidate qualification and action-owning build/deployment workflows have not
yet produced objective evidence.
