# Platform Release 3.3 — Management Summary

Current decision: `PLATFORM_RELEASE_3_3_CANDIDATE_BLOCKED`

Historical decision: `PLATFORM_RELEASE_DRY_RUN_PASSED`

## Current release position

Platform Release Engineering is qualified as a reusable Generation 1
capability, but Platform Release 3.3 is not authorized for operational
execution. The prior candidate branches and their exact-SHA evidence were
merged and removed; they are historical evidence and cannot qualify the
current `main` commits.

The Generation 1 release architecture and policy contracts are qualified and
frozen. They do not constitute operational deployment consumers or smoke
capability for Release 3.3. Those consumers must still be implemented and
qualified for the approved manifest before an operational release can be
authorized. No production target has been mutated, no tag or GitHub Release
has been created, and no operational deployment or burn-in evidence exists.

Before an Internal Release can be authorized, the platform must:

1. complete and qualify the manifest-bound deployment and smoke consumers for
   every required target in the approved release manifest;
2. reconstruct a fresh 3.3 candidate manifest from the exact current `main`
   SHAs;
3. bind new verification, coverage, Software Assurance and Trusted Delivery
   evidence to that candidate; and
4. obtain explicit authorization for the bounded manifest-bound deployment
   dispatches.

Platform Release Certification is deferred until after a successful
operational release and sufficient burn-in evidence. It cannot substitute for
any of the prerequisites above.

The historical 3.3 release-candidate dry run resolved exactly the three
recorded findings:

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
GitHub-hosted Linux work. The resulting historical capability decision is
`NATIVE_RUNNER_ALIGNMENT_COMPLETE`. It does not make Release 3.3 operationally
ready: the current Release 3.3 decision remains
`PLATFORM_RELEASE_3_3_CANDIDATE_BLOCKED` pending qualified deployment consumers,
smoke capability and current-main candidate evidence.

## Current candidate reconstruction

The historical dry-run candidates are no longer current `main` commits and
cannot authorize an operational release. Fresh 3.3 candidate branches have
been reconstructed from current main, with the discovered Home Assistant,
Apple and Windows runtime metadata corrections applied. Their current
readiness decision is `PLATFORM_RELEASE_3_3_CANDIDATE_BLOCKED`: no fresh
candidate has yet qualified evidence, and the new per-repository workflow
contracts intentionally fail closed for `execute` until native build,
publication, deployment and rollback actions are qualified.
