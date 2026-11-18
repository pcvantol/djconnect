# Cross-Repository CI Governance Rollout Report

Status: complete with documented action-pinning follow-up
Date: 2026-07-12
Prompt: Software Assurance Generation 1, Prompt 2

## Result

All ten active repositories now consume the canonical reusable Software
Assurance governance workflow. The seven repositories that already contained
workflows have a governance job in every existing workflow; the three
distribution repositories received a standalone governance workflow.

The canonical consumer is pinned to
`pcvantol/djconnect/.github/workflows/software-assurance-governance.yml@b02217ab54ff5a93e9ba5ae406ac608f43ff8792`.
It validates the Prompt 1 policy source at
`pcvantol/djconnect@3fc4f0835fe4068b73a30c7fb2db3318600a3f6f`.

## Inventory and Compliance Matrix

| Repository | Existing workflows | Rollout result | Profile classes | Override / follow-up |
| --- | ---: | --- | --- | --- |
| `djconnect` | 8 | All consume policy | Balanced, Release | Existing action aliases remain a follow-up. |
| `djconnect-api` | 3 | All consume policy | Balanced | Existing action aliases remain a follow-up. |
| `djconnect-app` | 6 | All consume policy | Balanced, Release | macOS release and TestFlight behavior preserved. |
| `djconnect-app-releases` | 0 | Standalone workflow created | Balanced | Distribution-only repository. |
| `djconnect-esp32` | 4 | All consume policy | Balanced, Release | Hardware/release behavior preserved. |
| `djconnect-firmware` | 0 | Standalone workflow created | Balanced | Distribution-only repository. |
| `djconnect-pi` | 4 | All consume policy | Balanced, Release | Existing local `.coverage` left untouched. |
| `djconnect-pi-releases` | 0 | Standalone workflow created | Balanced | Distribution-only repository. |
| `djconnect-website` | 4 | All consume policy | Balanced, Release | Production deployment profile is Release. |
| `djconnect-windows` | 4 | All consume policy | Balanced, Release | Windows/macOS release behavior preserved. |

## Override Register

- Apple release/TestFlight workflows use the Release profile and retain macOS
  runner requirements.
- ESP32 firmware release uses the Release profile; hardware-specific execution
  remains owned by its existing workflow.
- Website deployment uses the Release profile.
- Distribution repositories have no pre-existing workflow inventory; their
  new standalone governance workflow provides policy consumption without
  inventing a release pipeline.
- Existing third-party action aliases are recorded as a documented action-
  pinning follow-up. No alias was silently changed during this rollout because
  every action update requires repository-specific compatibility review.

## Validation

- all workflow files parse as YAML;
- every workflow contains the pinned governance consumer, except the canonical
  reusable workflow that is itself the consumed implementation;
- policy self-validation passes;
- repository settings, rulesets, branch protection and CODEOWNERS were not
  changed.

## Platform Cleanup & Evidence Workflow Conformance Repair — 2026-07-27

**Decision:** `GO_CLEANUP_WORKFLOW_PLATFORM_CONFORMANT`

The active DJConnect platform now uses the same qualified cleanup and durable
evidence contract. Cleanup remains limited to transient Actions workflow runs;
it cannot delete qualification records, release evidence, immutable prompt
history, release assets or post-merge evidence. Durable evidence is published
and read back as an append-only release asset before the qualified status is
emitted.

| Repository | Role | Cleanup contract | Evidence / owner revision | Exact-main evidence |
| --- | --- | --- | --- | --- |
| `djconnect` | active source | Canonical | `4931f1371b53159d837968955a7b4972051bdcbe` | Reconciled by this record; next main validation uses the aligned dispatcher. |
| `djconnect-api` | active source | Canonical | `4931f1371b53159d837968955a7b4972051bdcbe` | Run `30262200374` successful. |
| `djconnect-app` | active source | Canonical | `4931f1371b53159d837968955a7b4972051bdcbe` | Run `30264664846` successful. |
| `djconnect-app-releases` | distribution | Equivalent release-role contract | `4931f1371b53159d837968955a7b4972051bdcbe` | Run `30262171116` successful. |
| `djconnect-esp32` | active source | Canonical | `4931f1371b53159d837968955a7b4972051bdcbe` | Run `30262551584` successful. |
| `djconnect-firmware` | distribution | Equivalent release-role contract | `4931f1371b53159d837968955a7b4972051bdcbe` | Run `30262186203` successful. |
| `djconnect-pi` | active source | Canonical | `4931f1371b53159d837968955a7b4972051bdcbe` | Run `30262251000` successful. |
| `djconnect-pi-releases` | distribution | Equivalent release-role contract | `4931f1371b53159d837968955a7b4972051bdcbe` | Run `30262199634` successful. |
| `djconnect-website` | active source | Canonical | `4931f1371b53159d837968955a7b4972051bdcbe` | Run `30262411162` successful. |
| `djconnect-windows` | active source | Canonical | `4931f1371b53159d837968955a7b4972051bdcbe` | Run `30262532163` successful. |

The three distribution repositories intentionally do not model source-build
coverage. Their existing release-role integrity artifact is the qualified
equivalent evidence source; this is a role boundary, not a workflow
divergence. No evidence-loss finding was observed.
