# Action Pinning Migration Report

## Batch 1 — Internal Reusable Workflows and Official `actions/*`

Decision: `ACTION_PINNING_BATCH_1_COMPLETE`
Branch: `codex/trusted-delivery-platform`
Date: 2026-07-12

Batch 1 pins official `actions/*` references while preserving existing major
lines, and pins floating DJConnect reusable workflow consumers to producer
commit `b02217ab54ff5a93e9ba5ae406ac608f43ff8792`. Producer workflow paths were
verified at that commit.

Affected repositories: `djconnect`, `djconnect-api`, `djconnect-app`,
`djconnect-esp32`, `djconnect-pi`, `djconnect-website`, `djconnect-windows`.
Unique dependency families pinned: 10 (7 official action families and 3
internal reusable workflow paths). Exact tag/SHA mappings are in
`software_assurance/action-pinning/batch-1-pins.json`.

Validation: YAML parsing for all affected workflows; producer path validation;
canonical policy validation; immutable-reference scan; secret-safe diff review;
and `git diff --check`.

Out of scope and unresolved: HACS, hassfest, CodeQL, Semgrep, Gitleaks, Docker,
release/publishing and other third-party actions. No third-party ref changed.
SHA enforcement remains disabled because full action migration is incomplete.

### Coordinated sibling commits

| Repository | Branch | Commit |
| --- | --- | --- |
| `djconnect-api` | `codex/action-pinning-batch-1` | `6ec72f8` |
| `djconnect-app` | `codex/action-pinning-batch-1` | `b29ab98` |
| `djconnect-esp32` | `codex/action-pinning-batch-1` | `79f9d71` |
| `djconnect-pi` | `codex/action-pinning-batch-1` | `f8cd6d7` |
| `djconnect-website` | `codex/action-pinning-batch-1` | `efe7a1c` |
| `djconnect-windows` | `codex/action-pinning-batch-1` | `cbf1cc6` |

All listed branches were pushed to `origin`. The canonical coordination commit
records the Batch 1 registry, report, canonical workflow pins and approved
historical Prompt 3 deletion.
