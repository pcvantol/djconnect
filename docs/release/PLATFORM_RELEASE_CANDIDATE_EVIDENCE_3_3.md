# Platform Release 3.3 — Candidate Evidence

All participating repositories resolve to exactly one commit on
`release/platform-3.3-dryrun`:

| Repository | Qualified candidate SHA |
| --- | --- |
| `pcvantol/djconnect` | `7411a82e5534d512969e70d32bcbc35fadbd4f74` |
| `pcvantol/djconnect-api` | `4279a6c01ea94aa2f94973ad27b7bd7084a3d748` |
| `pcvantol/djconnect-app` | `9e870d5b6a2544461ac45c9dd3ceafd8252ce9a2` |
| `pcvantol/djconnect-windows` | `b81467808a3430689e1db32e18fc00958dd569de` |
| `pcvantol/djconnect-pi` | `b61348670f85a413502fa2a28d4f386c0d53630d` |
| `pcvantol/djconnect-esp32` | `5ccfd47853f9c8dd5f365bcd675200c9cde8ea7f` |
| `pcvantol/djconnect-website` | `fcaa0bf9f83c9838bf2867b58d6b9a234f9bce2a` |
| `pcvantol/djconnect-firmware` | `8a5fadd7606dbb4a4d5376e0c0f383aab53980bd` |
| `pcvantol/djconnect-app-releases` | `6c3c5cf8bc49321f85970da71cc4b9c51d7649d1` |
| `pcvantol/djconnect-pi-releases` | `3d27d48437968c892aa9982d66d2e2478e8d91f4` |

The hashes were resolved from the local branches after their remote tracking
branches were pushed. They are supplied unchanged to the simulation input.

## Coverage evidence

The Verification Runtime ingested a fresh Cobertura report for candidate
`7411a82e5534d512969e70d32bcbc35fadbd4f74` with the expected SHA match:

- run: `platform-release-3.3`;
- scope: `release_candidate`;
- qualification: `COVERAGE_VALID`;
- validation issues: none;
- line coverage: `48.98%`; branch coverage: `16.55%`;
- report: `/private/tmp/djconnect-3.3-coverage.xml`;
- runtime evidence: `artifacts/verification/evidence/platform-release-3.3/coverage/coverage-summary.json`.

The artifact paths are intentionally untracked runtime evidence. This document
is the durable release-evidence index; it does not represent publication.

## Reproducibility correction

The original coverage attempt exposed a missing-tooling root cause: the active
Python environment and CI test setup installed `pytest` but did not declare or
install `coverage`. `requirements-dev.txt` now pins the verification tooling,
and the reusable Python CI paths install it before tests. A fresh local install
and the 15 coverage/release-runtime tests passed with `coverage 7.15.1`.
