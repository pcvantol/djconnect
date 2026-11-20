# Live-impressie merged source and internal-publication readback

Core PR [#1661](https://github.com/djconnect-music-dj/djconnect/pull/1661) merged as
`912e1efbd6e9475521779d04f98fd805f0b1f385`, with complete tree
`7a7565d985edd97b2427d70b851033f58605faa1` equal to qualified head
`f1b45dbf5363e87986ab5b8bb2354e5682a1995c`. Apple PR
[#396](https://github.com/djconnect-music-dj/djconnect-app/pull/396) merged as
`8668da1fca60596d99e19c58d9d7c88390c8d21e` with its qualified tree unchanged. [Apple exact-main CI44700356839](https://github.com/djconnect-music-dj/djconnect-app/actions/runs/44700356839),
including unsigned builds/coverage, and [formal publication44701910005](https://github.com/djconnect-music-dj/djconnect-app/actions/runs/44701910005)
passed. Its downloaded durable qualification asset also passed the pinned-policy
validator; this remains software/source evidence.
[Independent Core main validation](https://github.com/djconnect-music-dj/djconnect/actions/runs/44700319366)
and [automatic artifact/evidence publication](https://github.com/djconnect-music-dj/djconnect/actions/runs/44700925335)
passed, including HACS and exact-main coverage. The internal artifact and durable
qualification record were downloaded: all 318 product files match the qualified
source, both asset digests match GitHub, and the pinned-policy evidence validator
passes. This is source/internal-publication evidence, not an installation.

The canonical readback is [merged-source-readback-20261120.json](../../examples/client_contracts/live_impression_v1/merged-source-readback-20261120.json).

| Evidence | Exact result |
| --- | --- |
| Source merge | `912e1efbd6e9475521779d04f98fd805f0b1f385` |
| Qualified complete tree | `7a7565d985edd97b2427d70b851033f58605faa1` |
| Main validation | run44700319366 PASS; full tests, HACS, lint, security, governance and exact-SHA coverage |
| Automatic publication | run44700925335 package and reconciliation PASS |
| Internal integration artifact | SHA256 `d9a35d36ad6058d414d4ff4df0bfa0633fa71709fc9172ce4504a6d75e62ca6d`; all318 product bytes equal qualified source |
| Durable evidence | SHA256 `23ffb9d7a92e6dd06d8133eab5cc081b04ccbcb846bebb2f6631cd51065965e1`; pinned-policy validator PASS |
| Apple durable source evidence | SHA256 `75b5a0d9e0c00ae665d68c2aba6febae330c3c5eb30567b1a7af47fafbb837e4`; run44701910005 and pinned-policy validator PASS |
| Exact post-merge status | `POST_MERGE_RELEASE_EVIDENCE_QUALIFIED` |

The existing automatic workflow published the prerelease/tag
[`internal-ha-912e1efbd6e9475521779d04f98fd805f0b1f385`](https://github.com/djconnect-music-dj/djconnect/releases/tag/internal-ha-912e1efbd6e9475521779d04f98fd805f0b1f385).
The owner expressly authorized these internal source/Finalization publication effects.
The temporary workflow deferral of broad Ask DJ release qualification remains a
qualification deferral; this artifact does not turn it into PASS.

The original source PR's complete four-worker suite accounted for4834 tests with
11skips; the Git-less external snapshot's one Git-dependent branding gate passed
against the exact committed checkout, and GitHub's complete source/main checks
passed. All185 original roadmap tests and45/45 current-owner isolated HA probes
passed. The tracked Live HTTP proof makes34 paired requests using explicitly
synthetic research/photo/narration inputs; actual HTTP-produced Core bytes passed
the compiled Apple528ce0b decoder/admission/history roundtrip. None of these
claims substitutes for real-model editorial or physical/native acceptance.

The historical output-before-search first-play probe remains byte-for-byte
historical and failed on both pristine current main and the candidate. Fresh
current For-you owner evidence qualifies the offer-first producer; no old failure
is relabeled PASS. Every original historical qualification fixture remains intact.

Maintenance18 preserves the exact maintenance17 planning freeze and reconciles
only three source/software delivery leaves. Joint LI01–LI20 ACCEPTANCE remains
Planned/OPEN; live model, installed and shared-TV are NOT_RUN, physical/native
acceptance OPEN. Current-source media/history/Ask/speech rights do not become new
Watch, VibeCast, API or shared-screen grants.

This is the separate governance-only Finalization proposal. Its merge must be
followed by independent exact-main checks and automatic artifact/evidence
readback, then local-only Workspace Cleanup. `MERGED_RECONCILED` is the prospective repository target, effective only after this
Finalization's protected merge and its own independent exact-main CI/publication
PASS. `WORKSPACE_READY` is the separate prospective workspace target, effective
only after the actual task-scoped cleanup report satisfies its criteria. Until
then Source #1661 is `MERGED_UNRECONCILED` and the workspace is `NOT_READY`.
No runtime product file, provider, installation or deployment changes here.


## Observe-only TDE semantic correction

The source and Finalization TDE workflows completed successfully, but their
actual canonical assessments are FAIL / repository qualification FAILED
(exit2/2). Source912 has992 findings/68 failing policy results; Final9486 has994/69.
All906 runtime-component findings and code size118835 are unchanged. Finalization
also introduced a CRITICAL51-complexity governance validator, a TEST HIGH11 case,
and increments in existing maintenance dispatch262→263 and rendering44→45.
These are not an overall technical-debt PASS or an all-baseline-only result.

The [original semantic comparison](../roadmap/v1/history/20261120/live-impression-tde-source-final-comparison.json)
preserves both original canonical FAIL records and digests. A separate
[bounded corrective record](../history/prompts/2026-11-20-live-impression-validator-correction.md)
retains every original guard and admitted rendering result while separating
proof responsibilities. Fresh candidate TDE must be read semantically; existing
observe-only scope remains as defined by
[TDE planning governance](../governance/TDE_1_1_1_PLANNING_RECONCILIATION.md) and
[the canonical backlog boundary](../../PRODUCT_BACKLOG.md#tde-boundary).
No runtime refactor, policy waiver, assessment relabel or new product work follows
from this disclosure.
