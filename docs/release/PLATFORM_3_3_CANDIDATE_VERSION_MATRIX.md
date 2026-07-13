# Platform Release 3.3 Candidate Version Matrix

Platform compatibility version: `3.3`. Repository patch versions are
repository-owned. Candidate SHAs are recorded only after each focused PR has a
qualified immutable head; this source document does not self-reference a Git
commit hash.

| Repository | Candidate version | Status | Notes |
| --- | --- | --- | --- |
| `pcvantol/djconnect` | 3.3.0 | aligned | Manifest and runtime constant agree. |
| `pcvantol/djconnect-api` | 3.3.0 | aligned | Package metadata agrees. |
| `pcvantol/djconnect-app` | 3.3.0 | aligned | Universal iOS plus native macOS source version. |
| `pcvantol/djconnect-windows` | 3.3.0 | aligned | Package, project and runtime contract agree. |
| `pcvantol/djconnect-pi` | 3.3.0 | aligned | Runtime and protocol constants agree. |
| `pcvantol/djconnect-esp32` | 3.3.0 at build | pending build | Version is injected only by a release build. |
| `pcvantol/djconnect-website` | 3.3.0 | aligned | Package and generated version pipeline are 3.3. |
| `pcvantol/djconnect-firmware` | no 3.3 artifact | pending build | Current manifest remains published 3.2.11. |
| `pcvantol/djconnect-app-releases` | no 3.3 artifact | pending publication | Distribution repository is intentionally unchanged. |
| `pcvantol/djconnect-pi-releases` | no 3.3 artifact | pending publication | Distribution repository is intentionally unchanged. |

Compatibility is evaluated by Major.Minor only; no patch value is used for
cross-repository compatibility.
