# Shared settings migration and ordinary Pi onboarding — 21 October 2026

## Admission and existing product

Same sole Core writer, selected twelve-hour window ends19:10:02UTC. Qualified
clean main `d7673a751cfab4c42b288673723fec2ca40e2e02` after protected history
source1255 and distinct Final1256; both actual canonical receipts QUALIFIED and
232-file/schema12/6-entry/HTTP HA-dev readback PASS. Fresh actual SharedData-root
hostverify MATCH/exit0/onboarding4.5.4. No second writer or consumer-source writes.

The delivered six-field settings3 producer1193/e8cc70dd already provides Persona,
voice, gender, Mood, Presence and announcement output. Do not reimplement it or
rewrite its dated inventory/immutable receipts. This increment closes concrete
ordinary Pi admission and current verification gaps within Core migration.
The whole SETTINGS migration remains dependent on owning-client adoption.

## Actual blockers, before failures and bounded correction

The existing Pi owner reproduced normal Add device/local/Linux-Raspberry Pi with
a real temporary code and manual URL: invalid_client_type, without a pair POST.
No mDNS defaults meant ConfigFlow invented djconnect-{pair_code} and then rejected
that invalid Pi ID. A changed manual URL could also retain another discovered ID.
The causal new no-mDNS test failed against the exact base with abort versus next
step. The new current-configured-device options test separately failed because a
legacy Household had no row for that already configured stable Pi ID.

ConfigFlow now resolves only a manual/changed Pi endpoint's own stable ID from
its ordinary pairing-info GET, preserving the submitted endpoint. The whole read
is bounded to3seconds/16KiB, disallows redirects, and requires canonical Pi type,
matching stable ID shape and the exact submitted temporary code. Failure remains
a translated form error, preserves input and caches no borrowed identity. Existing
HA uniqueness and explicit Profile choice still precede the normal pairing owner;
no fabricated identity, other client type, reset, ad-hoc pair route or blind retry.

The ordinary final Pi pair owner rereads the same bounded metadata and rejects a
changed ID/type/code before POST. It retains the submitted endpoint and disallows
redirects; an advertised foreign URL cannot replace it. ESP and inbound app paths
keep their existing semantics. The normal device endpoint still validates its
code, ID and client type; this correction grants no new device authority.

Profile Platform options show device names plus exact IDs, and explicitly offer
the current supported configured identity even when its Household row is absent.
Rendering performs no link and selects no Profile. A user's explicit choice uses
the existing Store owner; a similarly named historical code-derived row is never
an identity alias or silently moved. Real HA form validation, explicit link,
subsequent Store reload and unchanged legacy row are qualified with synthetic
data. No real mapping, context clear, token export or rollback was performed by
Core. A Pi-owner UI misidentification was investigated with narrowly authorized
private metadata/earlier backup only; those personal identifiers are not fixtures.
That backup proves an earlier durable state, not the immediately preceding state.

The existing settings lab also asserted zero Moments for Music-only. The newer
canonical [opening contract](../product/SESSION_OPENING_MOMENT_V1.md) explicitly
permits one informative visual opening with zero automatic speech. The verifier
now requires exactly that original Session opening, visual-only, with immutable
ID/body/metadata and zero synthesis/speaker fetch or catch-up on a Presence raise.
No Presence/runtime/speech policy was relaxed to pass the probe.

## Actual current qualification

Existing bounded real HA2026.10.0 image
`sha256:1b64d38f38d922bf9d59336451fd6453e1d614f934456af4ee3d2a51061be3a4`,
network none, read-only source, disposable isolated config, dropped capabilities,
no-new-privileges,2GiB/2CPU/256PIDs. No live HA-dev configuration or credentials.
Real HA loader/core/local built-in conversation agent and a separately selected
real local conversation pipeline qualify ConfigFlow admission; the original
speech-only preferred pipeline is not changed or its gate mocked. Only external
music/waveform/speaker boundaries are fixtures. No paid/model matrix enabled.

Actual raw receipt SHA256
`cb03dd743b94689c89dfa60f1855389db7860541177061570e9f1f78e328fd44`;
204 actual Python/helper hashes equal before/after and match candidate bytes.
[Credential-free derivative](../../examples/client_contracts/profile_session_settings_v3/current-migration-20261021.json).


- 13 real-HA manual Pi cases: actual type/details/Profile-choice flow and final
 normal pair owner, real HA duplicate rejection, wrong ID/type/code, oversized
 and split valid-prefix bodies, no redirect follow, whole-body deadline3.006s,
 changed final identity/type/code, exact-ID configured-device UI selection and
 explicit durable link with the older same-name row unchanged.13 actual metadata
 GETs and one synthetic loopback pair POST; no physical pairing/native UI claim.
- All six choices propagate over three ordinary paired owner TLS surfaces; the
 other Profile receives no invalidation. Read/reconnect soak120.898s,354 owner
 reads/two actual TLS reconnects, exactly unchanged SQL row counts.
- Real Store/SQLite acceptance/replay/restart boundaries, original immutable receipt
 after Session end, legacy partial-selection refusal and qualified cleanup,
 source/voice/provider withdrawal, text_only zero synthesis/old media denial,
 actual constrained anonymous speaker fetch/operation retry and exactly one new
 publication delivery with no read/output-switch catch-up remain PASS.
- One informative Music-only opening, zero automatic speech and no replay on
 raising Presence. Source/provider waveform fixtures prove no audible output.

Some existing case IDs contain the historical label all_five; their actual
closed defaults and six individual TLS patches are checked as six fields. Old
committed fixtures are retained byte-identically, never reinterpreted.

Earlier failures are retained: stale Music-only assertion; the new ConfigFlow
probe initially lacked the real HA conversation setup/loader/core exposure and
used the intentional no-conversation preferred speech fixture. Its setup now uses
real HA bootstrap plus an explicit qualified local pipeline. No product gate was
mocked or loosened. The passing receipt belongs to the complete corrected run.

Final local candidate validation: 2986 tests PASS in104.350s,7 existing skips;
260 focused identity/Profile/runtime tests PASS in4.734s, changed Ruff/diff PASS,
CI-pinned Bandit1.9.4 PASS with0findings/0errors. The initial full suite correctly
failed three current evidence bindings after the runtime helper changed. Both
history producers were then freshly qualified against the current source in
isolated actual HA:46 individual and37 archive HTTP requests, TLS WebSocket,
Store/SQLite and separate-process recovery all PASS,0 model calls. New derivatives
preserve all previous wire evidence byte-identically:
[individual](../../examples/client_contracts/session_conversation_history/content-deletion-v1-settings-migration-20261021.json)
(raw SHA256 `545f48a446a48ca7061041bcdbd8036f97fd8d9d669f4e1f2e3712d6ea890ea7`)
and [archive](../../examples/client_contracts/session_conversation_history/archive-deletion-v1-settings-migration-20261021.json)
(raw SHA256 `37ebdcccfb8a74f63f3fe5b8c37e1518138b14463aa493dfeeb41739358a24b3`).
Current reference hash and its deterministic source view were regenerated;
historical snapshots, statuses and delivery evidence remain unchanged. No test
assertion, owner/source boundary or completion status was weakened.

## Migration disposition and Golden relationship

Keep the exact six shared fields, explicit initial complete selection where legacy
evidence exists, accepted immutable settings2 outcomes and settings3 upgrade rules.
Do not infer Persona/output from old tone, device flags or the last online client.
HA pipeline/provider/physical speaker/ESP administration remain HA-only; local
playback/autoplay/permissions remain device-owned. Portability remains parked.

The dated inventory remains the original census. Its receiver-end-authority row
is explicitly superseded by the separately delivered retirement contract; it is
not a remaining authority or a roaming setting. Current receiver owner reports
protected abf69b68/renderer1.1.3 contains no shared-settings/Profile reader or old
end grant; that is a static owning-source census, not new native/runtime GO.
Apple/Pi adoption and complete legacy removal require their own protected/native
and explicit operation reconciliation evidence. ESP/website owning gates remain
open. No consumer pickup or source ownership is transferred by this Core record.

The current standard Golden inventory remains44families/385steps/87issues;
42Core/29quality findings remain OPEN. The direct regression relationship is
ordinary identity/Profile admission and existing settings owner acceptance,
qualified here through actual HA controls plus the full standard unit/CI schedule.
It adds no AI behavior, Planner/Horizon or editorial scenario, no paid run and no
new musical/fact/quality GO. Do not force a duplicate Golden family for this gate.

## Delivery and installed boundary

Exactly three integration files change (__init__, config_flow, discovery); all
other229 of232 installed product files are unchanged. No new endpoint/schema,
settings field, operational manifest, consumer code or device configuration.
Independent exact review, applicable exact Owner Authorization, normal protected
source/actual canonical receipt, distinct documentary Finalization and controlled
HA-dev installation are still gates at this source freeze. The actual installed
predecessor remains232-file payload90766c59/schema12. A fresh full stopped-owner
code/config/SQLite/WAL/Store backup and matching immutable new payload precede
restart/file-integrity/real runtime/HTTP/SQL readback. Pi owner has reported a safe
checkpoint with no live intents; coordinate again before any actual interruption.
Only that owning lane retries the ordinary manual route with a current displayed
code after delivery. Core performs no physical device pairing or mapping action.
