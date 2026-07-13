# Platform Release 3.3 — Management Summary

Historical decision: `PLATFORM_RELEASE_DRY_RUN_PASSED`

The 3.3 release-candidate dry run is ready for the next explicitly authorized
phase. The remediation resolved exactly the three recorded findings:

1. Website release metadata now synchronizes versioned references and the
   displayed release version through all generated localized source pages.
2. The release manifest contains one exact dry-run branch SHA for every
   Repository Ownership participant.
3. Fresh candidate coverage passed runtime ingestion as `COVERAGE_VALID`.

No production release action occurred. Tags, GitHub Releases, deployments,
uploads, firmware rollout and publication remain absent.

## Native runner alignment

Apple and Windows native build paths are now qualified through successful
GitHub Actions runner workflows with uploaded unsigned artifacts and exact
SHA evidence. The architecture assigns Apple to the self-hosted macOS runner
and Windows to the self-hosted Windows runner; other source builds remain
GitHub-hosted Linux work. The resulting decision is
`NATIVE_RUNNER_ALIGNMENT_COMPLETE` and the release platform is
`PLATFORM_RELEASE_3_3_INTERNAL_READY` for the next explicitly authorized
operational Internal Release phase.

## Current candidate reconstruction

The historical dry-run candidates are no longer current `main` commits and
cannot authorize an operational release. Fresh 3.3 candidate branches have
been reconstructed from current main, with the discovered Home Assistant,
Apple and Windows runtime metadata corrections applied. Their current
readiness decision is `PLATFORM_RELEASE_3_3_CANDIDATE_BLOCKED`: no fresh
candidate has yet qualified evidence, and the new per-repository workflow
contracts intentionally fail closed for `execute` until native build,
publication, deployment and rollback actions are qualified.
