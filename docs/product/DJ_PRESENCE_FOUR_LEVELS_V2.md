# DJ Presence: four choices and policy2 — 18 October2026

Status: owner-requested correction inside the existing Core settings/Session
writer. Design before implementation; no producer pin or installed claim yet.
This supersedes the five-choice policy in DJ_PRESENCE_CORE_POLICY_V1.md and
DJ_PRESENCE_OWNER_CONTRACT_V1.md. Historical delivery receipts remain unchanged.

## Canonical selection and real server policy

Exactly four selectable/written canonical codes, in this order:
`music_only`, `occasional`, `balanced`, `presenter`. Default `balanced`.
Persona controls the host, Mood its expression; Presence controls frequency.

| Code | nl | Minimum interval seconds | Maximum per track | Maximum per rolling600s |
| --- | --- | ---: | ---: | ---: |
| music_only | Alleen muziek | 0 | 0 | 0 |
| occasional | Af en toe | 180 | 1 | 2 |
| balanced | Gebalanceerd | 90 | 2 | 4 |
| presenter | Presentator | 45 | 4 | 8 |

All actual substantive proactive families share the existing Runtime ledger.
These are ceilings, never targets or a schedule. Existing read-time spacing,
source/rights eligibility, tail fit, deduplication and final owner/revision fences
remain. One logical contribution is charged once even when both text and speech
are available. Suppressed opportunities are not queued or caught up after a
setting change; no client may recreate the frequency policy with timers.
Music-only retains the existing suppression of unsolicited substantive Moments
and speech. Intentional Silence, explicit Ask DJ and authorized manual replay
keep their existing separate semantics and output-policy checks.

## Backend compatibility and migration

The one retired input alias is `talkative → presenter`. Existing high-density
preferences stay at the high spoken level; the new high level has a lower cap
than either former high-density mode. No other unknown spelling is normalized.
Older writes may supply this alias through existing authenticated/CAS boundaries;
all new accepted settings and current snapshots return canonical `presenter`.
Only the four canonical values appear in selectable/allowed-value arrays.

Forward-only persistence migration10 rewrites only the Presence field of saved
Profile defaults and currently ACTIVE persisted Session settings. It preserves
the other five settings, owner/generation, acceptance revisions, timestamps and
contract versions. This is compatibility spelling normalization, not a new user
choice. Completed/interrupted Session history and immutable accepted operation
receipts are not rewritten. Historical receipts remain historical proof and may
still contain `talkative`; replay never rolls Runtime back.

A legacy active in-memory Runtime is normalized under the existing lifecycle
lock before ordinary reads/updates and proactive work. It keeps Session identity,
playback, Flow, immutable Moments and the exact ledger/debits. Presence revision
increments once to invalidate pending work; prepared/pending opportunities are
discarded and one canonical `presence_changed` event can notify subscribers.
Shared settings revision/defaults revision do not pretend another user save.
Repeated normalization is a no-op. Pure projection and ledger compatibility
also recognize the alias, so an older retained Runtime cannot crash or expose a
fifth current selectable state before its locked normalization.

## Capability and wire contract

`active_session_presence.available=true`, capability `version=2`, and matching
capability-contract version2 advertise the four-value policy. Add
`transport_contract_version=1`: POST `/api/djconnect/v1/session/presence` keeps
its existing six-field request `contract_version:1`, owner authorization, CAS,
errors and upgrade requirements. Capability1/five values remains a historical
producer contract; a strict consumer must recognize capability2 explicitly.

The primary Profile/Session settings contract remains3; GET
`/api/djconnect/v1/profile/settings` serves exactly the same four Presence codes
in `allowed_values.presence`. No Swift mapping, local timer or invented
selection is needed. A contract fixture and exact source pin follow qualified
implementation; design availability is not producer or installed availability.

| Code | en | nl | de | fr | es |
| --- | --- | --- | --- | --- | --- |
| music_only | Music only | Alleen muziek | Nur Musik | Musique uniquement | Solo música |
| occasional | Occasionally | Af en toe | Gelegentlich | De temps en temps | De vez en cuando |
| balanced | Balanced | Gebalanceerd | Ausgewogen | Équilibré | Equilibrado |
| presenter | Presenter | Presentator | Moderator | Présentateur | Presentador |

## Qualification and delivery

Exercise the same rich Runtime input against all four policies and measure
actual publication timestamps/types, track and rolling bounds. Verify database
upgrade/reopen, ACTIVE versus completed rows, receipt preservation, legacy input
aliases, active migration once, retained debits, in-flight cancellation, CAS,
no-op, owner withdrawal, music-only and capability/Profile discovery. Retain
existing independently owned narrative WIP. Full regressions, static/security,
current documentation/DAG checks and independent review precede delivery.
Source pin, installed readback and native/audible acceptance remain distinct.

## Local qualification readback

The implemented producer fixture is
`examples/client_contracts/session_presence_v2/capability.json`; its measured
Runtime trace is adjacent. Identical four-track observations publish0,2,4,8
substantive Moments across the four settings, with unchanged source/read-time
fences and retained debits. The eight new contract/migration/race tests and
existing SQLite acceptance suite preserve immutable receipts, completed rows,
owner denial, CAS/no-op and current history. Full combined regression:
2473 tests PASS, seven existing skips. Static checks PASS; Bandit medium/high
findings0. Independent review is a scoped Presence source GO, not final combined
candidate, native, installed or narrative-quality acceptance.

Existing source/mechanism probes with45-second opportunities now explicitly
select Presenter. SI-GOLDEN-002 retains its fixed61-second scenario through the
same explicit choice; no production default or clock/ledger is bypassed. The
new owner Golden bindings include the four-level policy and migrations while
retaining the46 reported issues/36 families/136-step inventory.

Source delivery and installed producer readback are still pending. The broader
personal-DJ correction remains NO_GO: the latest real source-ID model trial
could not create its isolated container (Docker metadata read-only), so no new
paid-model answer, installed story or audible proof is claimed.
