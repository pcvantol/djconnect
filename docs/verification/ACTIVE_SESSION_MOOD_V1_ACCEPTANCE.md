# Active Session Mood v1 acceptance

Assignment: `DJC-CORE-ACTIVE-SESSION-MOOD-V1-20261011`, Core #1101
comment6108886915. Base `72598682010683b9276a8bec2a76a0f33bbb9a2b`;
sole branch `codex/active-session-mood-v1`. ACK6110003232 and first material
contract change6110038834. Separate Discovery artwork dependency excluded.

## Qualified outcome

The ordinary paired owner updates one active Session with the existing four
symbolic moods. A changed value publishes one atomic mood/revision through
Runtime/Broadcast; same-value is a no-op, stale revision conflicts. No restart,
playback/queue control, Profile preference, provider call, TTS or forced Moment
is introduced. Existing immutable Moments and their presentation contexts remain
unchanged. Async candidates compare the captured revision, including ABA changes,
before merging or consuming state; rejected track candidates remain retryable.

The route, schema, capability and consumer ordering rules are in
[Active Session Mood v1](../product/ACTIVE_SESSION_MOOD_V1.md).

## Evidence and boundaries

Tracked evidence is under `examples/client_contracts/active_session_mood_v1/`:

- `baseline.json`: actual missing owner route/capability and duplicate internal
  same-value event before producer mutation.
- `early-acceptance.json` and `early-manifest.json`: 19 actual HA SDK receipts,
  135 producer source hashes; early local immutable candidate
  `ad178c7b88d8f2e502c2930afe95352554838572`.
- `browser-acceptance.json`: four real HA owner POST/Broadcast/browser sequences,
  local HA-hosted and static Cast renderer, portrait and landscape. Cards and
  attribution remain intact, future eligible Album uses party, reconnect,
  expiry and Session end pass. Screenshot hashes are recorded; temporary images
  remain in the owning lab. Images were inspected after the transition reached
  full opacity.
- `renderer-build-manifest.json`: unchanged deterministic shared build 1.1.0,
  generated from the early pin; no receiver-repo push or HTML patch.
- `qualification.json`: independent review, checks and outcome categories.

Configured slots, linked Profiles/backend, source-shaped music facts, elapsed
music time and management-state withdrawal are explicit bounded synthetic input.
Actual isolated HA2026.10 router, ordinary pair/token persistence, device-bound
owner resolution, Runtime and live transport are exercised without substituting
HA user credentials. Token-withdrawal fixture does not claim options-flow rotation.
The separate existing conversation/history regression retains its original
fixture authority; it is not used to prove ordinary mood authentication.

The private lab binds only loopback. Browser Node requests trust the owned CA;
Chrome permits only the owned server certificate SPKI. CAF message transport is
modeled, while HA HTTP/WebSocket and renderer are real. This proves software
compatibility, not real CAF, native Apple, installed HA, Pi/TV or physical hardware.
No shared Apple/HA-dev lab, Pages, signing, service or paid-provider effect occurred.

## Verification

- 1,697 unittest cases run, seven skipped; no failures.
- 172 Verification Program pytest cases pass.
- Five meaningful Runtime concurrency tests pass: CAS/no-op, final authority
  lock fence, coordinator/fallback/intra-track ABA and same-track retry.
- 19 actual HA mood receipts pass: pairing, two-client CAS, validation/privacy,
  Profile switch/disable/archive, runtime/unload/token withdrawal, final-lock
  authority, delayed acknowledgement, lost-reply snapshot, Session end/replacement.
- Existing real paired-live/auth regression passes; existing real
  conversation/history HTTP regression passes all 24 requests.
- Ruff passes; Bandit reports zero medium/high findings.
- Actual HA route coverage is approximately 91% including branches. This is
  route-focused coverage, not a claim that the entire Runtime is fully covered.
- Independent technical/privacy review fixed three findings before bounded GO;
  separate consumer/UX review gave bounded GO and improved old-Session/conflict
  guidance. Browser evidence remains distinct from native/installed acceptance.

## Delivery boundary

Early contract/producer/receipt handoff is Apple #87 comment6110323886, tied to
existing `codex/apple-session-newest-first`; no second Apple writer or Swift delta.
The exact local final source pin must obtain its own publication authorization,
required checks and protected delivery. Exact-main/package readback and separate
Finalization follow that merge. None is claimed complete by this source report.
The assignment stops after its one Core delivery and own safe cleanup.

## Reproduction

Use a fresh owning temporary directory, the existing HA SDK dependency environment
and `DJC_SOURCE_ROOT` pointing to the exact reviewed checkout. Run
`scripts/verification/verify_active_session_mood.py` with `DJC_LAB_ROOT` set.
It neither accepts installed HA endpoints nor reuses their credentials.

For browser qualification, generate the shared build into `$DJC_LAB_ROOT/build`,
provide an owned localhost TLS certificate/CA in that directory, and run the same
script with `DJC_MOOD_BROWSER=1`. It binds18203/18204 and writes a ready marker.
Run `tests/browser/active_session_mood_browser.mjs` with `DJC_PLAYWRIGHT` set to
the available module, `DJC_CHROMIUM` set to the available browser and
`DJC_LAB_SPKI` set to that certificate's digest. The browser uses a fresh private
context, never a user profile. Stop only these owned processes after the run.
