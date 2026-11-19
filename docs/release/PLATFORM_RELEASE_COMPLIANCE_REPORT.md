# Platform Release Engineering Generation 1 — Compliance Report

Date: 2026-07-13  
Qualification decision: `PLATFORM_RELEASE_QUALIFIED`

| Active repository | Version | Candidate SHA | Verification | Qualification | Coverage | Participation | Compliance |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `pcvantol/djconnect` | 3.3.0 | `7411a82` | Runtime 6 tests; catalog validation | Ready simulation | `COVERAGE_VALID` | Active source | Compliant |
| `pcvantol/djconnect-api` | 3.3.0 | `4279a6c` | 40 tests | Dry-run evidence pass | Consumed platform evidence | Active source | Compliant |
| `pcvantol/djconnect-app` | 3.3.0 | `9e870d5` | Unsigned iOS Release build | Dry-run evidence pass | Consumed platform evidence | Active source | Compliant |
| `pcvantol/djconnect-windows` | 3.3.0 | `b814678` | Release test invocation | Dry-run evidence pass | Consumed platform evidence | Active source | Compliant |
| `pcvantol/djconnect-pi` | 3.3.0 | `b613486` | 46 focused tests | Dry-run evidence pass | Consumed platform evidence | Active source | Compliant |
| `pcvantol/djconnect-esp32` | 3.3.0 | `5ccfd47` | Native release suite and simulation | Dry-run evidence pass | Consumed platform evidence | Active source | Compliant |
| `pcvantol/djconnect-website` | 3.3.0 | `fcaa0bf` | 66 tests and release build | Dry-run evidence pass | Not applicable to runtime code | Active source | Compliant |
| `pcvantol/djconnect-firmware` | 3.3.0 | `8a5fadd` | Distribution metadata validation | Planned, no publication | Consumed platform evidence | Distribution | Compliant |
| `pcvantol/djconnect-app-releases` | 3.3.0 | `6c3c5cf` | Distribution metadata validation | Planned, no publication | Consumed platform evidence | Distribution | Compliant |
| `pcvantol/djconnect-pi-releases` | 3.3.0 | `3d27d48` | Distribution metadata validation | Planned, no publication | Consumed platform evidence | Distribution | Compliant |

All rows align to Major.Minor `3.3`. Candidate SHAs are the immutable
identities used by the passed dry-run simulation. No repository was omitted,
hardcoded or published.
