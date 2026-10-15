# Hybrid transport source qualification — 2026-10-15

Assignment `DJC-CORE-HYBRID-TRANSPORT-CONVERGENCE-V1-20261013`, same sole
Core writer and branch `codex/hybrid-transport-convergence-v1`.
Admission base `9efd1977768d2574b66c16de9c5d8ba53e9157b1`; current reviewed
main ancestry includes `2ad7b85f79b7f76e51913006d430ba7ac7eb1024` through local
merge `11c90e8cd363f0f8799533154f0922e0bcabca46`. Its only incoming changes
are the existing dependency/onboarding update from #1096, retained without
modification. No workflow, runner, host-service configuration or installation changed.
`services.yaml` changes only user-facing help text; action schemas stay intact.

## Actual producer proof

The [public-safe synthetic fixture](../../tests/fixtures/hybrid_transport_v1.json)
records 54 real isolated HA/TLS/HTTP/WS cases. The networkless owned lab uses the
existing pinned image, 1 GiB/2 CPU/256 PID bounds, temporary test-only TLS trust,
real HA/router/auth/pairing/Profile/Store and existing Runtime/Planner/Moment/
Broadcast owners. Only external music/source provider I/O is explicitly fixed.
It is a verification composition, not an installed HA integration test.

Exact run fingerprint:
`616e9fdbf82261f26660bba9420c5dd08cd5fa0e803ae820e5f01d9ef638f381`.
All 163 integration-file SHA256 values and the canonical verifier hash match
current source. The full-worktree fingerprint also includes the then-current
documentation snapshot; later evidence-only edits do not change tested runtime
or verifier bytes. The fixture excludes authentication frames, paired tokens,
credentials and real account material.

Fixture SHA256: `56194457132eb329a81e240ebc0e116bfab600574223ec757c7d76d3d42f2474`.

- Four deliberate provider mutation acceptances; reconciliation/duplicate attempts
  add zero effects. No real model calls. No provider exactly-once guarantee.
- Production idle music-only lease: 300.010418 seconds. Authentication deadline:
  5.011397 seconds. Missing-pong close: 23.489158 seconds.
- Idle source withdrawal: 1.004832 seconds; token rotation: 1.006995 seconds.
- Real maximum process RSS: 251,360 KiB under the explicit container bound.
- Journal before idle expiry: 16,349 bytes; after expiry/GC: 879 bytes. This is
  measured sample storage, not a claim that the final file is peak storage.
- Actual out-of-order held-effect/fast-read replies and replacement socket
  original-ID status; exactly one provider completion survives waiter disconnect.
- Actual oversize admitted queue result becomes confirmed receipt-only with both
  availability flags false; duplicate recovery performs no extra provider query.

## Regression, owning coverage and design consistency

Full current-main regression: 1,914 tests PASS, seven existing skips. Twenty-four
journal/service owning units PASS. All 142 living-DAG tests, schema/reference/
acyclicity/generation checks, package snapshot and offline governance projection
checks pass. Changed Python passes Ruff; the new transport implementation passes
Bandit. Fresh hostverify exits zero/MATCH on developer onboarding 4.5.3.

Combined branch-aware full-unit plus real HA coverage for the new modules:
89% overall; hybrid service90%, action HTTP/WS adapter86%, journal88%,
delivery97%, contract100%, five-language synchronous labels100%. Exact module
hashes accompany the fixture; coverage does not substitute for an unexecuted
native, installed or physical test.

Owner-requested [localization](INTEGRATION_UX_LOCALIZATION_20261015.md) is separately
committed and independently reviewed, with 157 focused tests/2,991 subtests.
Historical roadmap snapshots and all prior delivered product changes remain
preserved. Live JSON maintenance v10 and generated views retain source In progress,
Apple/joint Planned/open and family PARTIAL until their actual delivery gates.

## Publication and consumer boundary

Independent technical/privacy and product/network-UX review applies to the
consolidated exact candidate after this evidence commit. Earlier checkpoints
cannot authorize or qualify a changed candidate. Publication/protected delivery,
exact-main/internal artifact/formal readback and separate Finalization are still
required under the assignment's candidate-specific gates. No push or installation
is implied by this local source qualification.

Apple [early handoff](https://github.com/pcvantol/djconnect-app/issues/87#issuecomment-6185756317)
and [explicit implementation/test matrix](https://github.com/pcvantol/djconnect-app/issues/87#issuecomment-6186713492)
are posted and read back. They preserve the existing Apple writer and WIP; no
Swift changes or consumer start is claimed. Final published producer/main/artifact
pins follow protected source delivery. Automatic native LAN/external/return,
suspension/foreground, actual view continuity and native energy measurements
remain Apple-owned OPEN. Installed/hardware/joint acceptance is NOT_RUN/OPEN;
no HA-dev/prod restart, deployment, Pages, signing or hardware effects occurred.

## Exact hassfest repair

PR #1170 remains on the original approved candidate pending a separate repair
publication grant. Its genuine hassfest failure was confined to English service
text formatting: trailing YAML block-string newlines and two literal JSON
examples interpreted as invalid placeholders. The repair changes only
`strings.json` and `translations/en.json` within the integration, plus a regression
and refreshed evidence. All Python runtime and four other locales are unchanged.
The full 54-case production-lease proof is repeated on the repaired catalogue
bytes, and the official exact CI hassfest image passes locally (one integration,
zero invalid). New remote checks and exact Owner Authorization are still required
on the repair SHA; no old candidate grant or failed check is bypassed.
