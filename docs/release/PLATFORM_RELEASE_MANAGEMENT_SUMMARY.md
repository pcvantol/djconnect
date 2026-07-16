# Platform Release 3.3 — Management Summary

Current decision: `PLATFORM_RELEASE_3_3_MANIFEST_APPROVED_PARTIAL_DEPLOYMENT_OPERATIONAL`

Historical decision: `PLATFORM_RELEASE_DRY_RUN_PASSED`

## Current release position

Platform Release Engineering is qualified as a reusable Generation 1
capability. Platform Release 3.3 has an approved exact-artifact Internal
Release manifest and six successfully completed target-scoped operations. The
prior candidate branches remain historical evidence and do not replace the
approved manifest binding.

The Generation 1 release architecture and policy contracts are qualified and
frozen. The current manifest records successful manifest-bound deployment and
separate post-deployment smoke for `cloudflare_workers_production`,
`cloudflare_pages_production`, `rbpi-djconnect` and
`esp32_lilygo_t_embed_s3`, `apple_private_device/macbook` and
`apple_private_device/iphone` with required paired-Watch validation. Their
exact workflow evidence is recorded in
`PLATFORM_3_3_CURRENT_MAIN_MANIFEST_PROPOSAL.json` and the target completion
records. Home Assistant and Windows ARM64 targets remain open. No complete
release or operational burn-in evidence exists.

Before the Internal Release can be closed, the platform must:

1. obtain exact, target-scoped authorization and complete manifest-bound
   deployment plus smoke for Home Assistant;
2. complete the now separately authorized Windows ARM64 operation; and
3. reconcile all target evidence before considering release burn-in.

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

This historical dry-run paragraph is not a statement about the current
manifest-bound operations above.

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

The approved current manifest is
`release-3.3.0-internal-20260714`, status
`APPROVED_PARTIAL_DEPLOYMENT_OPERATIONAL`. Its six completed target operations
do not waive the remaining target-specific prerequisites. Release certification
is still blocked until every required target is qualified and burn-in evidence
has been collected.
