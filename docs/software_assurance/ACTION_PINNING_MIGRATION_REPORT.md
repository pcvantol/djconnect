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
it subsequently completed successfully, including the firmware build, pinned
CodeQL analysis and cleanup job. Residual risk is limited to Semgrep action
v1's upstream container-image reference, which is not migrated because
Docker/image migration is explicitly outside Batch 2.
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

## Batch 3 — Docker, Registry and Packaging

Decision: `ACTION_PINNING_BATCH_3_COMPLETE`
Central branch: `codex/trusted-delivery-platform`
Date: 2026-07-13

Batch 3 found one in-scope action in the canonical inventory and active
workflows: `docker/login-action` in the verification-runtime Docker release
workflow. No Buildx, QEMU, metadata, build-push, signing, provenance, SBOM,
container-packaging or other Docker/registry action is present. Generic
artifact actions were completed by Batch 1 and firmware/Apple/domain-specific
release actions remain out of scope.

| Dependency | Intended line | Approved release | Immutable SHA |
| --- | --- | --- | --- |
| `docker/login-action` | v4 | `v4.4.0` | `af1e73f918a031802d376d3c8bbc3fe56130a9b0` |

The pin changes only the action reference in
`.github/workflows/verification-platform-docker-release.yml`; all inputs,
outputs, image tags, push conditions, cache behavior and artifact behavior are
unchanged. The workflow continues to target Docker Hub by omitting `registry`,
uses only `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN`, and retains the action's
default logout post-step. It has `contents: read` only.

Authentication and every image push remain guarded by
`github.event_name == 'push' || inputs.push`. The workflow has no pull-request
trigger, uses `ubuntu-latest`, has no self-hosted runner or Trusted AI
credential, and cannot supply registry credentials or publish images for an
untrusted fork pull request. It builds and validates five existing tags before
that guarded authentication/push path; no Buildx/QEMU matrix, remote cache or
packaging artifact is configured.

Validation passed: GitHub release/tag and `action.yml` review, YAML parsing,
immutable-reference and guarded-secret validation, canonical policy
validation, Docker release CLI dry-run, secret-safe diff review and
`git diff --check`. Branch dry-run
[29225503583](https://github.com/pcvantol/djconnect/actions/runs/29225503583)
completed successfully with `push=false`, validating the existing
build/label/smoke path without logging in or publishing. The authenticated Docker Hub path is
intentionally not exercised because production publication is prohibited for
this validation. No Batch 3 reference remains unresolved.

No sibling repository contains an in-scope Batch 3 dependency, so no sibling
branch or commit is required. SHA enforcement remains disabled; Batch 4 and
all excluded action classes were not started.

## Batch 4 — Domain-Specific and Release Actions

Decision: `ACTION_PINNING_BATCH_4_COMPLETE`
Central branch: `codex/trusted-delivery-platform`
Date: 2026-07-13

Batch 4 eliminates every remaining non-immutable external `uses:` reference in
the active workflow inventory. Three references across two repositories were
migrated: HACS validation, hassfest validation and firmware-release
publication. Local reusable-workflow paths remain local by design; all remote
reusable workflows were already pinned in Batch 1 or Batch 2.

| Dependency | Previous ref | Approved release/commit | Immutable SHA | Status |
| --- | --- | --- | --- | --- |
| `hacs/action` | `main` | reviewed `main` commit | `1ebf01c408f29afcb6406bd431bc98fd8cbb15aa` | governed exception |
| `home-assistant/actions/hassfest` | `master` | reviewed `master` commit | `f4ca6f671bd429efb108c0f2fa0ae8af0215986c` | governed exception |
| `softprops/action-gh-release` | `v2` | `v2.6.2` | `3bb12739c298aeb8a4eeaf626c5b8d85266b0e65` | approved |

### Compatibility and exceptions

HACS' latest stable tag is 22.5.0 (2022) and its implementation still invokes
`ghcr.io/hacs/action:main`; hassfest's only release tag is 1.0.0 (2020) and
does not contain the current `hassfest/action.yml` path. Pinning their
maintained branch commits preserves the existing current behavior while making
the GitHub Action reference immutable. Both are governed exceptions for the
upstream mutable container-image reference and must be reviewed when upstream
publishes a suitable current release or changes the action/container.

`softprops/action-gh-release` remains on its existing v2 line, now at v2.6.2.
Its target repository, beta prerelease expression, notes, asset set and
`FIRMWARE_RELEASE_TOKEN` use are unchanged. The tag-only trigger remains the
production release guard; no production release was published for validation.
PlatformIO and Apple/TestFlight workflows contain commands rather than
external actions, so no action reference exists to migrate.

### Secret and fork safety

HACS and hassfest retain `contents: read`, use GitHub-hosted Ubuntu runners,
and receive no repository secret or Trusted AI credential on fork PRs. The
firmware release workflow has no pull-request trigger; only trusted tag pushes
can access `FIRMWARE_RELEASE_TOKEN` to publish to `djconnect-firmware`.
No permissions, inputs, outputs, release assets or publication semantics were
broadened or changed.

### Validation

Workflow YAML parsing, immutable-reference scanning, registry validation,
canonical governance policy validation, permissions/secret review,
fork-safety review, secret-safe diff review and `git diff --check` passed.
HACS and hassfest both succeeded in the canonical validation runs
[29226226728](https://github.com/pcvantol/djconnect/actions/runs/29226226728)
and [29226226825](https://github.com/pcvantol/djconnect/actions/runs/29226226825).
The ESP32 publication workflow cannot be safely dispatched without a release
tag and production token, so its compatibility validation is static and
non-publishing by design.

Affected repositories: `djconnect` and `djconnect-esp32`. Total references
migrated: 3. Unique dependencies pinned: 3. Floating references eliminated:
`@main`, `@master` and broad `@v2`. There are no unresolved Batch 4 action
references; the two governed upstream container-image exceptions are recorded
in the registry. SHA enforcement remains disabled. Batch 5 was not started.

### Coordinated branches

| Repository | Branch | Commit |
| --- | --- | --- |
| `djconnect-esp32` | `codex/action-pinning-batch-4` | `e6db66184ecdab78e914adbb21efe0f010064385` |

The final central coordination commit records this registry and report update.

## Batch 5 — Platform-Wide Enforcement and Validation

Decision: `ACTION_PINNING_BATCH_5_BLOCKED`
Readiness decision: `SHA_PINNING_ENFORCEMENT_NOT_READY`
Date: 2026-07-13

Batch 5 performed a live read-back of the ten active repositories discovered
from `REPOSITORY_OWNERSHIP.md`. All Batch 1–4 migration branches and recorded
commits are durable on `origin`, and all local worktrees are clean. However,
none of those migration branches is merged into its repository default branch.
Repository-level SHA enforcement would therefore evaluate still-unpinned
default-branch workflows and block normal CI.

### Default-branch compliance matrix

| Repository | Active workflows | Remote refs | Immutable refs | Non-immutable refs | Enforcement supported | Enforcement enabled | Compliance |
| --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| `djconnect` | 10 | 41 | 11 | 30 | yes | no | blocked: canonical Batch 1–4 branch not merged |
| `djconnect-api` | 3 | 11 | 3 | 8 | yes | no | blocked: Batch 2 branch not merged |
| `djconnect-app` | 6 | 23 | 6 | 17 | yes | no | blocked: Batch 2 branch not merged |
| `djconnect-app-releases` | 1 | 1 | 1 | 0 | yes | no | compliant |
| `djconnect-esp32` | 4 | 29 | 4 | 25 | yes | no | blocked: Batch 4 branch not merged |
| `djconnect-firmware` | 1 | 1 | 1 | 0 | yes | no | compliant |
| `djconnect-pi` | 4 | 15 | 14 | 1 | yes | no | blocked: Batch 2 branch not merged |
| `djconnect-pi-releases` | 1 | 1 | 1 | 0 | yes | no | compliant |
| `djconnect-website` | 4 | 12 | 4 | 8 | yes | no | blocked: Batch 2 branch not merged |
| `djconnect-windows` | 4 | 30 | 4 | 26 | yes | no | blocked: Batch 2 branch not merged |
| **Platform total** | **38** | **164** | **49** | **115** | **10/10** | **0/10** | **not ready** |

The scan distinguishes three local reusable-workflow calls in `djconnect`;
those are not remote pinning violations. All 115 violations are movable tags
or branch refs on `main`, including `@main`, `@master`, broad action tags and
mutable reusable-workflow refs. The Batch 1–4 target branches were previously
validated as immutable. Registry-to-workflow consistency therefore passes for
the migration branches but cannot pass for the active default branches until
the approved branches are integrated.

### Remote durability and required coordination

The following remote branches contain their recorded commits and are not
ancestors of `main`: canonical `codex/trusted-delivery-platform`; API, Apple,
Pi, website and Windows `codex/action-pinning-batch-2`; and ESP32
`codex/action-pinning-batch-4`. Earlier Batch 1–3 evidence branches also
remain durable remotely. The Batch 2 branches contain their respective Batch
1 changes; the ESP32 Batch 4 branch contains its earlier Batch 1 and Batch 2
changes.

Required coordination sequence before enforcement:

1. Review and merge `codex/trusted-delivery-platform` into `djconnect/main`.
2. Review and merge the API, Apple, Pi, website and Windows Batch 2 branches
   into their respective `main` branches.
3. Review and merge ESP32 `codex/action-pinning-batch-4` into `main`.
4. Re-run the live default-branch scan and registry consistency check.
5. Only if the scan reports zero remote non-immutable refs, enable and
   read back `sha_pinning_required` for all ten repositories.
6. Run representative non-production CI after enforcement.

No merge, policy mutation or post-enforcement CI was performed in Batch 5,
because the prerequisite branch integration is outside this authorization.
All repository Actions policies currently retain `allowed_actions: all`,
read-only default workflow tokens, disabled PR-review approval and
`sha_pinning_required: false`.

The governed HACS and hassfest upstream-container exceptions remain compatible
with GitHub Action SHA enforcement: their `uses:` references are full immutable
SHAs, while the separately documented container-image risk requires periodic
upstream review. No registry pin changed in Batch 5. Other Prompt 3 Trusted
Delivery work remains outside action pinning.

### Default-branch integration attempt

On 2026-07-13 the cumulative migration branches were read back before opening
governed PRs. Each selected source is ahead of `main`, has no merge conflict,
and contains all earlier action-pinning changes required for that repository.
No direct push or governance bypass was used.

| Repository | Source branch | Source commit | PR | Current integration state |
| --- | --- | --- | --- | --- |
| `djconnect` | `codex/trusted-delivery-platform` | `30d60a0d149374294b320f6c32e913970a3f9831` | [#78](https://github.com/pcvantol/djconnect/pull/78) | required review; checks running |
| `djconnect-api` | `codex/action-pinning-batch-2` | `bf6d41fa1991c2f80817c9940fb36b487d08a105` | [#34](https://github.com/pcvantol/djconnect-api/pull/34) | required review; checks running |
| `djconnect-app` | `codex/action-pinning-batch-2` | `d1cfaf4032fc2f1cb54954df89edd0da7847dc2c` | [#12](https://github.com/pcvantol/djconnect-app/pull/12) | required review; checks running |
| `djconnect-pi` | `codex/action-pinning-batch-2` | `fb96aa8e095256574bb62a92fef565d387382cb8` | [#34](https://github.com/pcvantol/djconnect-pi/pull/34) | required review; existing Ruff failure |
| `djconnect-website` | `codex/action-pinning-batch-2` | `dc160215b153921f0831b803ebc40109f88aacdb` | [#15](https://github.com/pcvantol/djconnect-website/pull/15) | CI failures require remediation |
| `djconnect-windows` | `codex/action-pinning-batch-2` | `eae824465986f07909528882e9c9735fd102521d` | [#8](https://github.com/pcvantol/djconnect-windows/pull/8) | workflow-hygiene failure requires remediation |
| `djconnect-esp32` | `codex/action-pinning-batch-4` | `e6db66184ecdab78e914adbb21efe0f010064385` | [#15](https://github.com/pcvantol/djconnect-esp32/pull/15) | required review; checks running |

Pre-merge YAML parsing, immutable-reference scans and `git diff --check`
passed for all seven proposed results. Integration remains incomplete and
`SHA_PINNING_ENFORCEMENT_NOT_READY` remains in force for two independent
reasons: required PR approvals are absent, and three repositories have CI
failures.

The inspected failures are not enforcement failures. Pi Ruff reports a
pre-existing duplicate test function in `tests/test_app_backend.py`. Website
tests report an action-pinning-related expectation that still requires
`actions/checkout@v5`, plus the unrelated presence of `SYNC_PROMPTS.md`.
Windows workflow hygiene flags the ordinary word `refresh` in
`WINDOWS_PROFILE_ADOPTION_REPORT.md` as a secret-like string.

### Integration remediation and review coordination

Decision: `INTEGRATION_BLOCKED_PENDING_INDEPENDENT_REVIEW`
Date: 2026-07-13

The focused, explicitly authorized CI remediation completed without changing
platform architecture, Verification Runtime, workflow permissions, branch
protection, enforcement settings or Prompt 4 scope.

| Repository | PR | Remediation commit | Result |
| --- | --- | --- | --- |
| `djconnect-pi` | [#34](https://github.com/pcvantol/djconnect-pi/pull/34) | `6bb3e30` | Removed the byte-identical duplicate Ask DJ revision test; focused pytest and Ruff pass. |
| `djconnect-website` | [#15](https://github.com/pcvantol/djconnect-website/pull/15) | `9a1d8a4` | Updated the action-pinning assertion to the approved checkout and setup-node SHAs; targeted test passes. |
| `djconnect-windows` | [#8](https://github.com/pcvantol/djconnect-windows/pull/8) | `9dadab5`, `5d8f173` | Replaced the broad prose scan with immutable workflow-reference validation and executable regressions for prose, a mutable tag and a SHA pin; corrected its matcher after local reproduction exposed an escaping defect. |

The complete website suite now isolates one remaining failure:
`SYNC_PROMPTS.md` is present despite the existing test and release hygiene
requiring canonical prompt material to remain external. Git history attributes
the file to `5fef283` (`docs: align website repo with DJConnect foundation`),
which predates this action-pinning integration branch. It is unrelated to
action pinning and has deliberately not been deleted, rewritten or otherwise
changed. Explicit approval is required before any remediation of that file or
its canonical-content test.

Live collaborator read-back for `djconnect`, `djconnect-api`, `djconnect-app`,
`djconnect-pi`, `djconnect-website`, `djconnect-windows` and
`djconnect-esp32` lists only `pcvantol` as a direct collaborator. Each PR that
requires review remains unapproved. The configured Trusted Delivery GitHub App
is a least-privilege automation actor, not an independent reviewer, and was
not asked to approve or merge any PR. No self-approval, administrator bypass,
protection change or direct push to `main` was used.

Accordingly, all seven integration PRs remain open. Their checks must finish
successfully, the website canonical-content inconsistency requires separately
authorized resolution, and an independent reviewer must become available
before protected repositories can be merged. `SHA_PINNING_ENFORCEMENT_NOT_READY`
remains in force.
