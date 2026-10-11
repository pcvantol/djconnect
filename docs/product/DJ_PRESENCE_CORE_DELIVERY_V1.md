# DJ presence v1 — Core candidate qualification

Assignment `DJC-CORE-DJ-PRESENCE-V1-20261011`; same sole Core writer;
base `9cdee0602b2ff0db99c433f2a3f2eb6d5ba8fe4e`, branch
`codex/dj-presence-v1`. Early local contract pin
`1d5e8c2518db5902031898991b7f4857d5263a5c`, handed to
[Apple87/6111453713](https://github.com/pcvantol/djconnect-app/issues/87#issuecomment-6111453713).
**Phase: local implementation/qualification; source publication gate pending.**
No source PR/main delivery or Finalization is claimed by this document.

## Actual implementation

Independent presence v1 capability, six-field ordinary paired-owner POST,
strict schema/CAS/no-op, final owner/lifecycle fence and additive active/live
readback. Existing Mood transport reuses the same internal owner validator;
its separate path, fields, revision and all nineteen real transport receipts
remain qualified. Windows retirement blocks the new presence mutation.

The Runtime admits work before insight/Knowledge and fences the final commit
against presence, Mood and Persona revisions. Off/on ABA rejects old work.
Cancelled coordinator/fallback work restores only its current retry marker;
late current-track cancellation releases its unspent opportunity. Every
substantive proactive family debits one shared published-only ledger. Silence
and explicit Ask DJ do not. Settings, no-ops, reconnect, seek and old-track
revisits never reset those debits.

The existing Planner still selects qualified content and existing relations.
An ordinary/Discover Transition approval may occupy one current-track opportunity
for at most90s; the Moment is created at a fresh readable observation. No created
Moment backlog, new scheduler, planner or knowledge family. Changes, intervening
Flow, track/output/seek/pause, expiry and end invalidate the approval. Root
publication also checks the authoritative current Broadcast and private Persona
epoch: retained Runtime objects reject Off, Off/on, Mood/Persona changes and end. Old semantic Moments remain
immutable; operational currentness/expiry follows existing native_delivery.

## Measured policy, real isolated HA

Same four source-rich three-minute tracks, same Radio DJ/groove/nl, same qualified
synthetic catalog/recording/work/artist data, production HA pairing/router/owner,
Runtime/Planner/Knowledge/Moment/Flow/Broadcast. Provider fixture boundary is
explicit; no HA user credential, new provider/model or installation.

| Presence | Published contributions | Main observation times (seconds) |
| --- | ---: | --- |
| music_only | 0 | None |
| occasional | 2 | 0,180 |
| balanced | 6 | 0,45,90,180,225,270 |
| talkative | 10 | See full timestamp/type ledger |
| presenter | 16 | 0,45,90,135 within each eligible track |

Counts are observed outcomes, not quotas. Published Track/Album/Artist facts keep
source URLs and40s readable durations. Shared cap/interval suppression is recorded.
Calm Mood + Club DJ + presenter yields12; energetic Mood + Festival DJ + occasional
 yields2. Conflicting source-poor input at maximum produces0. No personality,
Mood, Session identity/start, playback or Profile preference is overwritten.
`balanced` intentionally reduces high-density old six-card opportunities to a
safe3/track and6/600s combined maximum; it is not universal legacy timing parity.

Long trial:120 modeled minutes,40 observed tracks,400 intra observations,
160 publications, maximum4 tasks, fixed64KiB ledger and at most16 rolling debits.
The recorded real duration is3.328s and process peak248283136 bytes
(236.8MiB); exact measured values are in the receipt. No external provider calls or retries. This exercises
bounded bookkeeping, not two hours of physical playback or native expiry.
A separate240-identity revisit test retains the old exhausted track debit.
Hash collisions conservatively suppress; they never grant extra contributions.

## Transport, preservation and consumers

Nineteen actual presence transport receipts cover ordinary pairing/persistence,
owner→Broadcast, no-op, two-clients/CAS, malformed input, read-only tokens,
reconnect, six authority-withdrawal races, final-lock withdrawal, late replies,
wrong/ended/replacement Sessions. Thirty-four sanitized real request/response
fixtures accompany the contract. Existing Mood transport was independently rerun.

A separate real HA run ordinarily pairs, sets music_only through the production
owner route and proves explicit text/voice, Profile history, completed-session
lookup and free text search:27 requests. Only source/account input and STT
completion are synthetic; no microphone/provider/native claim. Private question
text and archives remain outside shared Broadcast.

Four actual browser sequences: local/static × portrait/landscape, multiple
Track/Album contributions on one track, confirmed presence change, off mid-track,
unchanged old cards, source links, readable geometry/opacity, reconnect, expiry
and end. Real HA transport; modeled CAF delivery only. Shared renderer sources
are unchanged, version1.1.0; no receiver HTML edit, push or Pages deployment.
Screenshots and build/checksum output are retained in the own private lab.

## Owning quality and delivery boundary

Full owning regression and historical/current DAG tests pass. Line/branch
coverage is reported per changed production file in the evidence, not replaced
by an aggregate claim: ledger and presence adapter100%/100%; shared owner
validator about93%/88%; Runtime93.9%/84.5%. Broad existing HTTP/init coverage
is reported separately. No production exclusions or lowered gates were added.
Ruff passes; security scan has zero medium/high findings and eight unchanged
low baseline findings outside changed production files.

Independent technical/privacy and consumer/experience final review must bind
the frozen source candidate before publication. Protected PR/required checks,
automatic internal-ha147-file archive/formal evidence, exact-main readback and
separate Finalization each follow their normal gates. Source and Finalization
require separate fresh exact-SHA owner grants; no old Mood/documentary grant.

The maintained DAG uses explicit delta/2, retains the original design delta and
all original3October JSON/audit/projections. Only Core contract/policy nodes are
In progress. Joint product and Apple native acceptance remain Planned/open.
Core software evidence does not close native, installed, hardware, Cast/LG or
public distribution acceptance. No next slice is started.

Evidence: [session_presence_v1](../../examples/client_contracts/session_presence_v1),
[ownercontract](DJ_PRESENCE_OWNER_CONTRACT_V1.md), [policy](DJ_PRESENCE_CORE_POLICY_V1.md).
