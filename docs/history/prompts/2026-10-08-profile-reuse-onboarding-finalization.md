# Profile reuse onboarding v1 — Completion and Finalization

Assignment `DJC-CORE-PROFILE-REUSE-ONBOARDING-V1-20261008`; original base
`3488fd82ed04804973039b909f61a34e76379659`; source branch
`codex/profile-reuse-onboarding-v1`. Canonical host verify exit0/MATCH,
onboarding4.5.3, clean synchronized main, origin `pcvantol/djconnect` and one
free Core writer were verified before mutation. Sole writer used the existing
isolated checkout `/private/tmp/djc-native-moment-core`; primary tracked source
remained safe. Native-Moment predecessor #1128/#1129 was terminal and was not
reopened. ACK [6061434492](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6061434492)
and first material source [6061530456](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6061530456)
register the pickup; [exact-ready6063380404](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6063380404)
binds candidate, review and software/browser receipts.

PR [#1130](https://github.com/pcvantol/djconnect/pull/1130) protected merged as
`3bb6bb8a9cb3e87ebb1bb51c0cf99dfbe572c283` from exact reviewed candidate
`162104d625f26a281cb20897ea5365c10bbdabff`; source and main trees are
`8a9dd2353eaf30edbba1b24a32d191691dc689d0`. The owner directly approved
this exact source merge and automatic internal SHA-prerelease in this chat.
Finalization starts from that merge on `codex/profile-reuse-onboarding-finalization`;
its distinct publication requires fresh concrete approval. This immutable
history cannot contain its own final SHA; review/PR/terminal #1101 bind it externally.

## Product outcome

Profile choice uses current exact Profile IDs in existing HA forms/selectors
before provider/account setup. Empty Households directly create a Profile.
Explicit reuse adds only the new Device mapping; names never authorize reuse.
Existing Profile/account/backend/device/fallback state stays intact. Shared
entries reference their existing HA-owned provider, without copied credentials
or unnecessary OAuth. New drafts remain flow-local until final confirmation.
Selection is refreshed after removal/change; names retain strip/casefold rules.
Duplicate errors explain selecting the existing Profile or choosing another name.
All new forms, field descriptions, selectors and errors are localized in the
existing en/nl/de/fr/es contract. Manual, Spotify Direct, Music Assistant and
applicable Assist configuration remain within existing adapters/ownership.

## Before and after proof

Five behavioral scenarios were defined first and run against exact base:
missing early choice, generic duplicate-name failure, premature persistence,
missing preserved reuse and unavailable selection. Corrected valid base fixtures
produce2 assertion failures and3 missing-choice errors. Initial fixture setup
was corrected before the final before proof; that harness error is not claimed
as a product regression. Two independent before-failing Repair cases reproduce
incorrect Spotify OAuth prerequisites for manual/shared ESP entries.

The real HA browser before sequence runs the exact base with existing Home:
pairing → backend → profile details → same-name generic base failure. Before
screenshots show no early profile choice and the unhelpful failure.

The exact-source after sequence uses existing pair HTTP, config-flow HTTP,
frontend forms and persistent Household readback, with synthetic app devices:

1. Empty Household: pairing → new Profile Home → manual backend → final
   confirmation → entry. One Profile, one Device mapping.
2. Second device: pairing → actual profile dropdown → Home explicitly selected
   → final confirmation → entry, with no backend/OAuth step. One Profile, two
   mappings; Profile/account/backend/fallback structured state equals step1.
3. Third device: choose New → ` HOME ` → localized profile-name error.
   Household remains exactly equal to step2. Existing Home selection on the
   same form → confirmation → entry. One Profile, three mappings; existing
   Profile/account/backend/fallback state preserved again.

All130 actual HA lab integration files hash-equal frozen reviewed source.
Five actual frontend locales render profile choice, new Profile and duplicate
error: en/nl/de/fr/es PASS. Screenshots are real HA frontend, not a mockscreen.
The read-only independent reviewer inspected20 before/after/localized PNGs.
Browser harness navigation and initial restart-readiness mistakes were corrected;
failed diagnostics were retained rather than described as product failures.
Synthetic auth/config-entry secrets stayed outside artifacts; no raw auth store
or credential-bearing config-entry export is included.

## Review and technical validation

Three independent draft P2 findings were corrected before the frozen candidate:
retained provider views now revalidate unload/replacement/current authority;
legacy missing account IDs qualify only through a closed canonical single-account
and provider-client chain; final persistence shields the pending write and restores
current disk/cache state on cancellation while retaining concurrent Profile edits.
Event-controlled regressions prove these effects. Explicit caller account binding
and original provider revision/cache/lock/rotation ownership also remain guarded.

Independent exact technical GO and UX GO:249tests PASS, no unresolved findings.
Whole exact source and main suites1628tests PASS,7existing skips; coverage XML,
whole Ruff and GoldenSmoke PASS. Required source/main governance, trusted delivery,
security, HA validation and verification checks PASS. Optional local pytest probe
lacked pytest; required CI verification-framework tests PASS, with no fabricated
local pytest claim. Before/after receipts, source hashes, review and screenshots
are retained under `artifacts/verification/profile-reuse-onboarding`.

Recent read-only HA-dev logging contained ordinary custom-component warnings,
an external Spotify HTTP500 and a missing-bearer rejection. These do not establish
integration defects. Only reproduced manual/shared ESP OAuth Repair defects in
this onboarding path changed; original owner issues remain owned by that source.
No generic retries, weakened authentication or logging reconstruction.

## Exact publication and main readback

Exact source/main suites: 1,628 tests, seven existing skips, PASS; Ruff,
coverage, Golden Smoke and required source/main checks PASS. Independent exact
technical and UX review GO,249 independently executed tests,20 inspected real
HA screenshots. The exact internal archive contains130 safe byte-equal files;
SHA256 `d2ab2cd702d71e2f92b7ab4c03831aca2098e5034a6e7dc7853b56a7f18dff66`.
Canonical qualification JSON SHA256
`242d0d483d67fe1d81a5a221609a3f3f79420fba45743107528b1e7b64731c9c`:
integrity and every required check PASS. Coverage artifact digest
`4a002cdd29b9c48c0a8accb6de3883667f02162bb8ad9008e4feaa1bc47dd658`.
Automatic package and evidence workflows passed first attempt; no extra manual
Validate run, retry or evidence replacement was needed.

[Automatic main validation](https://github.com/pcvantol/djconnect/actions/runs/37803383562),
[internal package](https://github.com/pcvantol/djconnect/actions/runs/37803704625)
and [canonical evidence](https://github.com/pcvantol/djconnect/actions/runs/37803705290)
complete on this exact merge. Archive safety/file bytes and durable record
integrity/redaction, exact SHA and all required PASS fields were verified locally.

## Reconciliation and boundaries

Decision: source software/browser `PASS`; Finalization delivery and workspace
completion remain pending their actual externally recorded receipts. Finalization
changes eight documents: four identical current rolling handoffs, product backlog,
roadmap, selected contract and this immutable history. Broader `HA-ONBOARDING-001`
assessment stays Planned; the canonical next five are freshly read from
`PLATFORM_EVOLUTION_BACKLOG.md`, with no execution priority override. No new
engineering workflow, foundation ownership or Profile architecture is introduced.

No Swift/client source, new durable knowledge migration, playback/Session mutation,
live Spotify/MA qualification, native-client acceptance, Pi/hardware run or next
assignment. HA-dev stays installed at predecessor3488fd82; current candidate
installation/deployment was neither authorized nor performed. Pi capture/frame-rate
remains PARTIAL/parked. Source/Finalization branches need exact objective cleanup
proof and main synchronization; `MERGED_RECONCILED` follows Finalization,
`WORKSPACE_READY` follows safe cleanup. Stop after this one Profile reuse slice.
