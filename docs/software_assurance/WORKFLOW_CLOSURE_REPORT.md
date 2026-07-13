# Workflow Closure Report

Date: 2026-07-13  
Status: `WORKFLOW_CLOSURE_REMEDIATION_PENDING_PR_INTEGRATION`

## Purpose

This report replaces the direct-reference-only action-pin check with recursive
workflow closure qualification. A reusable workflow is resolved at the exact
commit specified by its caller, then scanned recursively until only terminal
actions, local actions or container actions remain.

The validator is implemented in
`tools/software_assurance/workflow_closure.py` and has focused cycle,
duplicate-edge, mutable-reference and registry-match tests in
`tests/software_assurance/test_workflow_closure.py`.

## Baseline finding

The direct default-branch scan reported 175 pinned remote references, but it
did not inspect the contents of historical reusable workflow commits. The
representative `djconnect-pi` run `29230909878` exposed the resulting defect:
the pinned historical `djconnect-python-ci.yml` source still used
`actions/checkout@v7` and `actions/setup-python@v6`.

SHA enforcement was therefore rolled back and read back as disabled in every
active repository. This remains the safe state until the remediation PRs are
merged and requalified.

## Recursive scan results

| Repository | Closure result before pointer remediation |
| --- | --- |
| `djconnect` | PASS |
| `djconnect-api` | PASS |
| `djconnect-app` | PASS |
| `djconnect-app-releases` | PASS |
| `djconnect-esp32` | PASS |
| `djconnect-firmware` | PASS |
| `djconnect-pi` | BLOCKED: eight reachable mutable terminal-action edges through the historical Python reusable workflow |
| `djconnect-pi-releases` | PASS |
| `djconnect-website` | PASS |
| `djconnect-windows` | PASS |

The canonical remediation removes historical reusable-workflow pointers from
its own workflows and adds registry records for the previously valid, pinned
Trusted Delivery actions. It does not change Platform Architecture,
Verification Runtime, policy semantics, or Prompt 4.

## Required completion sequence

1. Merge the canonical reusable-workflow closure remediation.
2. Update every active repository consumer to that immutable canonical
   remediation commit; preserve repository-specific runner overrides.
3. Run the recursive validator across every default branch, including cycle,
   duplicate and missing-reference checks.
4. Re-enable SHA enforcement only if every closure passes, read back the live
   setting, and run representative CI.

Until all four steps pass, the governing decision remains
`SHA_PINNING_ENFORCEMENT_NOT_READY`, Prompt 3 remains active and blocked from
completion, and Prompt 4 remains blocked.
