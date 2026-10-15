# Shared-producer continuity v1 — Completion and Finalization

- Assignment: `DJC-CORE-SHARED-PRODUCER-CONTINUITY-V1-20261007`.
- Decision: `GO_FOR_PROTECTED_FINALIZATION`; `MERGED_RECONCILED` follows
  this governance-only merge and `WORKSPACE_READY` follows safe cleanup.
- Base: `7c67352ec94adef25d7825a10eefeab132affdca`; sole Core branch
  `codex/shared-producer-continuity-v1`. Current host verify exit 0/MATCH,
  manifest 3.3.0, bootstrap 2.0.21, onboarding 4.5.3; no repair or required
  drift. Explicit main fetch/ff/readback, clean worktree and one Core writer.
- ACK: [6043785497](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6043785497).
  First material source: [6043846719](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6043846719).
  Exact candidate: [6044174009](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6044174009).
- PR [#1124](https://github.com/pcvantol/djconnect/pull/1124) protected merged as
`c542d8ea9889db3509cab2dd5f19b26dd1a21342` from independently reviewed head
`da309585121d7069c5a56fdd3a0520fc567d2419`; source/merge trees equal
`d8a6d668247ea87d0c6f25d2b58e893b7c9054d9`.
  Merge 2026-10-07 18:25:38 UTC. Owner explicitly approved this exact source
  merge and automatic internal publication in the execution chat. Finalization
  creates a distinct artifact and waits for its own bounded owner decision.
- Finalization branch: `codex/shared-producer-continuity-finalization`, based
  on `c542d8ea9889db3509cab2dd5f19b26dd1a21342`. This document cannot contain its own SHA;
  attached Finalization PR/exact review and #1101 receipt bind that candidate.
- Predecessor #1122/#1123 stays closed. Its missing comment was restored once
  from the real local completion report in
  [6043720078](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6043720078).

## Delivered product and source boundary

[Contract](../../product/SHARED_PRODUCER_CONTINUITY_CONTRACT.md) was fixed
before implementation. Two real-Runtime red scenarios proved absence of the
connection and source-order-dependent producer copy on exact base. Both
recordings use existing unique-ISRC/exact version/artist MusicBrainz retrieval;
structured recording/contributor identity and explicit unqualified producer
role are retained internally. Restricted/ended/conflicting roles are excluded,
never widened into an unqualified producer. No new provider/call/search budget.

A closed typed derived relation offers one existing track Moment only under
Discover AND Exploring. Source/role/locale/capability/read-fit gates precede
ranking; other facts preserve #1122 contextual selection. At most one relation
per current track and no repeated unordered recording-pair/producer relation.
Only actual Flow publication commits proof/use. Minimal historical proof follows
three most recent distinct observed tracks, expires independently in 30 minutes,
never changes its media identity and clears at end. Knowledge handoff is
transient; diagnostic history does not retain proof. Existing six-card limit,
read duration, spacing and all pause/seek/item/source/late-result gates remain.
Genre→Track and Recommendation transitions remain unchanged.

| Visible software sequence | Exact original base | Source candidate |
| --- | --- | --- |
| A credit, then B with shared qualified producer IDs 9/8 | A ordinary credit → B ordinary credit | A credit → B track card explicitly naming A, B and Producer 8 |
| Reversed relation response order | Ordinary copy order changed | Same producer and relation copy |
| Five languages | Two unconnected localized credits | Deterministic en/nl/de/fr/es relation and two recording links |
| Unpublished A, wrong Session/identity/role/label/source or expired proof | No relation | Ordinary fact or silence |
| Read-fit rejection/repeated event/reconnect/pause/seek/late response | Existing gates | No consumed unpublished or stale/duplicate relation |
| Four observed/published tracks, then end | No relational memory | Oldest proof evicted; no proof in Knowledge history; all context cleared at end |

NL after: “Producer 8 staat als producer vermeld bij Recording 1, net als bij
 de eerder besproken opname Recording 0.” This asserts no exclusivity,
collaboration or musical influence. B remains Now Playing/artwork; A appears
only as explicit historical reference. A compatible optional `url_previous`
adds the second public MusicBrainz recording attribution. Owner separately
requested semitransparent glass-like bubbles; tinted translucent fill, blur,
light edge/reflection and stronger fallback preserve existing layout/lifecycle.

## Validation and independent review

- Full repository-venv source/coverage/exact-main suites: 1,572 tests, 7 skips,
  PASS. Initial concurrent system-Python run encountered the existing roadmap
  subprocess timeout; unchanged-source repo-venv and coverage runs passed.
- Runtime/source/contextual 146 PASS; Golden/Discover transition 30 PASS;
  independent exact source suite 179 PASS; independent final CSS delta 21 PASS.
- Ruff whole source/tests, diff whitespace and offline projection PASS.
  Local source coverage: session_facts 81%, session_runtime 90%, combined 89%.
- Existing real browser consumer: 40 en/nl/de/fr/es before/after frames at
  1200×1920 and 1920×1200, exact source hashes, both attribution links, current
  title/artist/artwork, reconnect, end and no-store PASS. Existing owner-refinement
  and contextual ranking/dosage browser regressions PASS with glass styling.
- Independent exact candidate GO/no remaining P1/P2/P3. P2 proof retention in
  Knowledge diagnostics was corrected with a four-published-track/end test.
  Exact source/delta review confirms source hashes, Flow commit and visuals.
- PR checks: every non-skipped source check succeeded; required Trusted Delivery,
  owner status, tests, HACS/hassfest, static/security/dependency, verification and
  advisory Golden green. No policy/protection/workflow change or skipped-check
  upgrade. Exact main [Validate](https://github.com/pcvantol/djconnect/actions/runs/37666748223)
  and [CodeQL](https://github.com/pcvantol/djconnect/actions/runs/37666747230) PASS.

Golden relationship is indirect: this adds one qualified current-source visual
card, not a new Golden lifecycle, Transition or playback action. Existing SI
Golden and Discover transition suites protect the existing owners; dedicated
negative/two-track Runtime and browser cases prove the new relation.

## Authorized source publication and exact readback

Local main == origin/main == protected API main == `c542d8ea9889db3509cab2dd5f19b26dd1a21342`.
Source head/merge tree equality verified. Automatic
[artifact](https://github.com/pcvantol/djconnect/actions/runs/37667043410) and
[durable evidence](https://github.com/pcvantol/djconnect/actions/runs/37667043851)
passed on their first attempts. Downloaded
[internal prerelease](https://github.com/pcvantol/djconnect/releases/tag/internal-ha-c542d8ea9889db3509cab2dd5f19b26dd1a21342)
archive SHA-256 `23376b7c691e7a506ff01daec092b49a68dc51568f19bc22058e84199146bce7`;
127 files, safe paths/types, every file byte-equal to exact merge.
Qualification JSON SHA-256
`59c8f54d68b43b714d1a3c23c8574de635059cb97c27b63feef62c18266caa93`;
canonical integrity, exact commit, redaction and every required check PASS.
Coverage artifact digest
`67fd32248c39a6ede8f3c7ce9761ed19e5d12bdb90c2c068625d294f3e9da578`.
The local readback helper initially used the input-request field `main_sha`
rather than the durable-record field `commit_sha`; correcting that local helper
produced the verified readback above, with no source/workflow/publication change.

## Qualification, records and stop

`SOFTWARE_RUNTIME_BROWSER_QUAL=PASS`; fixtures mock provider data/time.
`LIVE_PROVIDER_QUAL=NOT_RUN`, no HA-dev/production installation or public HACS
release. Prior Pi capture and full-frame-rate motion remain PARTIAL/parked;
no new monitor, hardware run, queue repair, source family, clientlane, durable
learning or next capability is selected.

Finalization updates only rolling Repository/Engineering/Management/Prompt
records, product backlog/roadmap, maturity, the selected contract and this
immutable Completion/Prompt History. The five-item Execution Horizon remains
Apple public distribution; Windows public distribution; public HACS; HACS
3.3.0 visibility; firmware OTA publication/rollback, all with existing gates.
Finalization's own protected review/checks/main/publication and safe cleanup
are recorded in #1101 and the retained local completion report after delivery.
Stop after this one fully delivered shared-producer slice.
