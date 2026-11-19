# Platform Release 3.3 Candidate Evidence

## Available evidence

- Repository discovery produced one fresh candidate branch from current
  `origin/main` for each of the ten Repository Ownership participants.
- Executable metadata corrections are limited to Home Assistant, Apple and
  Windows sources as documented in the reconstruction report.
- Each candidate branch contains a pinned-action GitHub Actions execution
  contract that validates the bounded request and exact checked-out SHA before
  producing canonical evidence.
- Apple is bound only to the qualified self-hosted macOS runner; Windows only
  to the qualified self-hosted Windows runner; all remaining contracts use
  GitHub-hosted Linux.

## Absent evidence

No workflow was dispatched under this task. Therefore no fresh candidate
workflow run, artifact digest, deployment receipt, release tag, release,
publication, device validation or rollback receipt exists. The absence is
intentional and prevents this preparation task from being misrepresented as
an internal release.
