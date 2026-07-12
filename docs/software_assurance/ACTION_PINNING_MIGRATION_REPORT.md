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

## Batch 2 — Security Scanners

Decision: `ACTION_PINNING_BATCH_2_COMPLETE`
Central branch: `codex/trusted-delivery-platform`
Date: 2026-07-12

Batch 2 pins only the scanner actions in the canonical inventory. It preserves
all existing scanner configuration, events, language choices, checkout depth,
failure behavior and permission grants. SHA-pinning enforcement remains
disabled.

### Exact approved scanner pins

| Dependency | Intended line | Approved release | Immutable SHA |
| --- | --- | --- | --- |
| `github/codeql-action` | v3 | `v3.37.0` | `02c5e83432fe5497fd85b873b6c9f16a8578e1d9` |
| `github/codeql-action` | v4 | `v4.37.0` | `99df26d4f13ea111d4ec1a7dddef6063f76b97e9` |
| `gitleaks/gitleaks-action` | v2 | `v2.3.9` | `ff98106e4c7b2bc287b24eaf42907196329070c7` |
| `semgrep/semgrep-action` | v1 | `v1` | `713efdd345f3035192eaa63f56867b88e63e4e5d` |

GitHub release/tag metadata and annotated-tag dereferences were read directly
from each upstream repository. `action.yml` was reviewed for all action
components used by the workflows: CodeQL `init`, `autobuild` and `analyze`,
Semgrep, and Gitleaks.

### Scope and coordination

Affected repositories: `djconnect`, `djconnect-api`, `djconnect-app`,
`djconnect-esp32`, `djconnect-pi`, `djconnect-website` and
`djconnect-windows`.

Thirteen direct scanner-action references are now immutable: nine CodeQL,
one Semgrep and one Gitleaks reference, plus two additional CodeQL v4
references refreshed from a previous immutable v4 SHA to the approved v4.37.0
release. Six immutable reusable-workflow consumer references were advanced to
the central Batch 2 source commit `7cff5e8f77b13075062a8d5bf8a803959a3b54af`.
The canonical registry records the exact consumers, permissions, secret use,
fork behavior and validation evidence for the four unique approved dependency
lines.

### Compatibility, permissions and fork safety

CodeQL retains `contents: read` and `security-events: write`; no language,
build mode, scheduled scan or upload behavior changed. The Apple workflow
remains on v3 and retains `autobuild`; the other CodeQL workflows remain on
v4. Semgrep retains the canonical configuration and OSS mode with no
`publishToken`; existing `continue-on-error` behavior is unchanged. Gitleaks
retains `fetch-depth: 0`, its default action configuration and the
GitHub-provided token only.

All scanner jobs use GitHub-hosted runners. Untrusted fork pull requests do
not receive repository secrets, Trusted AI credentials or a write token, and
the scanner workflows do not publish artifacts or releases. `security-events:
write` is retained for code-scanning results and is not reduced to make
pinning easier.

### Validation and residual risk

Validation passed for every affected repository: workflow YAML parsing,
scanner immutable-reference scan, required-permission review, scanner
configuration review, canonical governance policy validation, secret-safe
diff review and `git diff --check`. The canonical Semgrep configuration exists
at `.semgrep/djconnect-security.yml`; Gitleaks intentionally retains its
existing action defaults because no repository configuration file is declared.

Representative branch runs were dispatched without merging: Semgrep completed
successfully at [run 29207926270](https://github.com/pcvantol/djconnect/actions/runs/29207926270)
and Gitleaks completed successfully at [run 29207928443](https://github.com/pcvantol/djconnect-esp32/actions/runs/29207928443).
ESP32 CodeQL was also dispatched at [run 29207927305](https://github.com/pcvantol/djconnect-esp32/actions/runs/29207927305);
its governance job and pinned-action initialization succeeded, while the
firmware build and analysis remain GitHub-runner work in progress at this
recording. Residual risk is limited to that still-running end-to-end CodeQL
execution and Semgrep action v1's upstream container-image reference, which
is not migrated because Docker/image migration is explicitly outside Batch 2.
No Batch 2 scanner reference remains unresolved. Docker, packaging, release,
HACS, hassfest and all other third-party action migrations remain out of scope.

### Coordinated branches

| Repository | Branch | Commit |
| --- | --- | --- |
| `djconnect-api` | `codex/action-pinning-batch-2` | `bf6d41fa1991c2f80817c9940fb36b487d08a105` |
| `djconnect-app` | `codex/action-pinning-batch-2` | `d1cfaf4032fc2f1cb54954df89edd0da7847dc2c` |
| `djconnect-esp32` | `codex/action-pinning-batch-2` | `a858bdb9cda8c9e493aca09f9a96e2a1dccc9d93` |
| `djconnect-pi` | `codex/action-pinning-batch-2` | `fb96aa8e095256574bb62a92fef565d387382cb8` |
| `djconnect-website` | `codex/action-pinning-batch-2` | `dc160215b153921f0831b803ebc40109f88aacdb` |
| `djconnect-windows` | `codex/action-pinning-batch-2` | `eae824465986f07909528882e9c9735fd102521d` |

All listed sibling branches are pushed to `origin`; none was merged. The final
central coordination commit records the registry and this report.
