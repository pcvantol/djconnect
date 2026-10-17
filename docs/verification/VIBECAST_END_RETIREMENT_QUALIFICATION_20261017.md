# VibeCast receiver end-authority retirement — current-main qualification

This is the bounded retirement described in
[the current contract](../product/VIBECAST_RECEIVER_END_AUTHORITY_RETIREMENT_V1.md),
from reconciled main `0adaef7d5acd9cbe84b97d2f684c6f2e705dc27c`.
It extracts the already selected end-authority correction from the unpublished
personal-DJ branch without publishing its failed narrative-quality work.
Source, exact reviews, protected merge, Finalization and installation are distinct
gates. This report records local qualification; final pins belong in the delivery
readback. No consumer or physical-screen acceptance is implied.

## Requirements and observed results

| Requirement | Executed evidence | Result |
| --- | --- | --- |
| Remove the obsolete HA checkbox in all languages | Config-flow tests exercise saved true/false, missing setting, visible schema and normal options save; source/translation inspection covers en/nl/de/fr/es | No exposed, accepted or saved setting; stale stored values inert |
| Remove authority completely | Handoff/Runtime tests and source search; normal pairing, Session start, owner approval and handoff collection in isolated HA | No grant field, issuer, grant store or end-with-grant API |
| Deny cached or hostile old controls without Session disclosure | Actual HA HTTP requests using stale grant, read token, missing token, other Session and malformed body | Five HTTP410 responses; no-store/no-referrer; identical Session and Broadcast before/after |
| Preserve owner end and unload fences | Actual paired owner end; existing non-Spotify and pending-subscription/unload regressions | Owner end succeeds; generic entry generation/subscription invalidation retained |
| Remove renderer interaction | 13 Node contracts and eight headless Chrome portrait/landscape captures | Injected legacy handoff ignored; no button or end request; real server-end snapshot renders idle |
| Preserve surrounding behavior | Full host regression | 2,182 tests run, seven existing skips, no failures/errors |

The isolated HA2026.10.0 image is pinned to
`sha256:1b64d38f38d922bf9d59336451fd6453e1d614f934456af4ee3d2a51061be3a4`.
The candidate is mounted readonly; `/lab` is isolated, network disabled,
capabilities dropped, no-new-privileges enabled, and resource limits set.
The probe verifies the 154 Python/helper source hashes before/after against the
host. Normal Core registration, authorization, handoff, Runtime and HTTP are
executed; external provider I/O alone uses fixtures. Zero paid/model calls and
zero provider-playback mutations. This is not a live HA-dev/prod result.

The browser fixture proves renderer interaction and layout in software. Its
source facts are simulated; it does not qualify real facts, prose, audible TTS,
TV hardware or native applications. The pre-existing eight captures cover four
independent fact/source cases across Track, Album and Artist in both orientations; this retirement does not add or qualify
new Moment families.

Additional current gates: 172 verification-framework tests and 172 living-DAG tests, schema/document hashes and all
23 regenerated views pass. The 11 onboarding-package tests and tracked package
freshness check pass; no package regeneration was required. Ruff passes across
integration and tests; Bandit reports zero Medium/High issues (13 Low findings).
The full 2,182-test rerun used the existing isolated regression interpreter with
PyYAML6.0.3; an earlier bare-interpreter attempt lacked PyYAML and is retained
as an environment failure, not successful evidence.

## Golden relationship and compatibility

This is removal of receiver write authority, not a Planner, Knowledge, Ask DJ,
Persona/Mood, TTS or generation change. The proportionate Golden relationship
is the existing receiver/Broadcast/owner-end safety contracts plus real paired
HA and browser execution. Paid editorial Golden failures remain release blockers
for the separate personal-DJ corrective branch; they are not bypassed or claimed
fixed by these unrelated bytes. Existing normal suites continue to run.

No storage schema migration or rewrite is needed. Previously saved true/false
values cannot grant authority; the next normal save drops the obsolete option.
No Profile, pairing, historical Session or receipt is deleted. The dated settings
inventory and its delivery hash remain byte-identical; its earlier legacy-row
disposition is explicitly superseded by the current retirement contract.
Receiver repository import remains consumer-owned. A cached older screen can
still show its old control until refreshed, but Core always returns410.

## Evidence and remaining delivery gates

Private reproducible evidence is retained under
`/private/tmp/djc-ready-vibecast-end-retirement`: `full-regression.log`,
`node-tests.log`, `evidence/ha/vibecast-end-retired.json`,
`evidence/browser/acceptance.json`, captures and renderer output. The initial
probe harness error and sandbox-blocked browser launch are separately preserved;
neither is a PASS. Both were corrected/re-executed before the results above.
No credentials, raw user history, bodies or live device identifiers are published.

Required before closure: current DAG/schema/generated-document checks,
onboarding-package verification, exact independent technical/privacy and
product/UX reviews, normal protected source checks and merge, exact artifact/main
readback, separate Finalization and authorized installed readback. Deployment
must coordinate existing Apple/live-resource leases. Broader Ask DJ prose,
retained Flow/art, speech, LAN/WebSockets, VibeCast rendezvous and native/OS/push/
Watch/performance acceptance remain as recorded in the
[dated integral audit](../governance/DJC_PLATFORM_OPEN_WORK_20261017.md).
