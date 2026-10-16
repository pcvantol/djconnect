# Profile and Session settings consolidation

Assignment `DJC-PROFILE-SESSION-SETTINGS-CONSOLIDATION-V1-20261016`.
Owner decision [6214905647](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6214905647)
supersedes assessment6209817556 for this successor. Design precedes runtime.
Admission base `148bd5aee3110c1a1ab13e7c463a164c99d79b70`; same Core writer,
branch `codex/profile-session-settings-consolidation-v1`. Earlier source and
Finalization1191/1192, speech and provider-gender releases remain history.

## Current owner addenda: shared output and strict setting boundaries

Owner decisions [6220504359](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6220504359),
[6220590330](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6220590330),
[6220625247](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6220625247),
[6220695648](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6220695648),
[6220756856](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6220756856)
and [6220784635](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6220784635)
refine this same assignment. They add `announcement_output` to the original five
shared parameters. The earlier local contract2 checkpoints below prove five
parameters only; they are not six-parameter or protected consumer qualification.
No reviewed final candidate is being extended. New output runtime work follows
this design and requires new exact reviews.

The next owner settings contract is **version3**, with the same existing owner
HTTP/paired live routes, Profile/Session/operation owners and atomic acceptance.
It adds one closed field `announcement_output`, default `client_device`, to
both defaults and effective Session settings. This version is implemented in the
local unpublished Core candidate; it is not merged, installed or consumer-qualified.
Prepare-version2 remains
its existing local shared-voice checkpoint; target-aware speech uses a separately
negotiated prepare-version3. Delivered public version1 contracts are not silently
reinterpreted. Local five-field contract2 producer pins and fixtures remain
historical; consumers wait for the exact replacement producer/schema pin.

| Profile output | Automatic delivery permission | Explicit valid Moment replay |
| --- | --- | --- |
| `client_device` | Relevant owner clients may play subject to each device's local autoplay | Local client |
| `both` | Owner clients and the configured usable HA-speaker | Local / HA-speaker / both, only authorized usable targets |
| `ha_speaker` | Configured usable HA-speaker | Local / HA-speaker / both; unavailable speaker never blocks local replay |
| `text_only` | No announcement synthesis, assets or delivery | No speech/replay action or accessibility speech action |

New Profiles use `client_device` even when a HA-speaker exists. No provider or
speaker selection is inferred from the output. Preserve an unavailable saved
mode and expose a closed reason plus separate target availability; do not rename
it `text_only`, overwrite it, or silently reroute a speaker-only choice locally.
No-target automatic delivery performs no synthesis. Local autoplay defaults OFF
on each new Apple installation, preserves existing explicit local choices and
never changes Profile output. Voice and gender remain saved in `text_only`, with
reason `not_applicable_text_only`; leaving that mode does not mass-generate audio.
The renderer removes speech controls immediately when output is `text_only`,
while retaining text, artwork, links and ordinary OS VoiceOver support.

Settings updates and source/provider changes fence pending work and old assets.
Apply the authoritative output before cache lookup or TTS and again before
asset acceptance, byte reads and speaker dispatch. Capture the same existing
settings revision/generation guard; `audio_response:always`, stale clients,
old snapshots and alternate endpoints cannot bypass `text_only`. Expiry and
source rights remain those of the original contribution. Never rewrite an
accepted Moment body to change its speech controls.

A manual target selection is an explicit owner action for one qualified,
still-valid Moment identity, not a Profile setting mutation, Session restart,
playback transfer, broadcast-to-all or autoplay change. Target-aware prepare3
uses the existing operation/effect recovery owner and an exact target-bound
operation ID. A retry returns its outcome without repeating speaker dispatch.
Report `accepted`/`queued`/`unknown`/`failed` separately; service acceptance does
not prove audible playback. A successful local target and failed speaker target
must not be collapsed into an overall played claim.

Automatic HA-speaker output is scheduled only from a newly committed live
Moment publication, once by that Session's existing publication owner. Joining,
reading, reconnecting or changing output never schedules older contributions.
Use the existing bounded operation journal with a stable publication identity;
clients cannot request automatic speaker effects through arbitrary operation IDs.
Capture Session/settings/target admission at publication and recheck it before
synthesis, dispatch and media fetch. A skipped or uncertain delivery is never
retried as a new automatic operation. Local client autoplay remains independent.

Private POST speechassets cannot be handed to a speaker as anonymous legacy GET
URLs. A speaker adapter must qualify a separate short-lived, bounded, revocable
media-fetch grant inside the existing byte owner, scoped to accepted reference,
owner/Profile, settings generation and chosen speaker target. Revalidate it on
actual media fetch; never expose the grant or target entity to shared displays,
Profile exports or generic diagnostics. Until that adapter and actual HA fetch
are qualified, speaker-target delivery remains unavailable; do not claim it
works from a mocked service call. No second synthesis engine or text archive.

### Allowlists and migration boundaries

The shared settings allowlist is exactly Persona, voice, gender, Mood, Presence
and announcement output. Physical HA speaker target, Assist pipeline/provider
configuration and every ESP firmware/provisioning/hardware setting remain
HA-only. Deny them on Profile PATCH and omit them from Profile reads, live
hints, snapshots, roaming caches and ordinary client exports. Expose only useful
closed capability/health reasons, not pipeline selectors, entity IDs, credentials
or ESP settings. Apple profile name/backend status are read-only. OS permission
grants, volume/output routes, microphone, haptics and presentation remain local;
joining a Profile must not overwrite them. Test allowlist denial on each boundary.

Legacy per-entry announcement output is evidence requiring explicit conflict
resolution, never last-online-device-wins. Do not auto-map factory `both` or an
old client UserDefaults value to a human Profile choice. Initial migration
review covers all six fields and uses the existing final on-loop admission
fence. Version-bound storage migration assigns a factory `client_device` only
where no canonical output existed; original accepted receipts remain immutable
historical outcomes, not replay instructions. A version3 PATCH must not treat
a pre-upgrade contract2 receipt as new version3 acceptance: return a typed
contract-change result, allow authorized readback of the original receipt, and
require reconciliation from a current snapshot before a new explicit operation.
No blind retry, rewritten receipt or partial active/default save.

The old `dj_response_enabled=false` flag is also legacy output evidence, not
a second global override of the accepted six-field policy. Preserve it pending
explicit migration review; never infer a whole-Profile `text_only` choice from
one old device flag. Once the owner accepts settings3, audio uses only the
canonical output and cleanup may retire that obsolete flag. New setup/options
must not mint the hidden flag again. The legacy route without a connected
settings owner retains its historical behavior until its consumer boundary is
retired; that boundary does not override settings3.

The active VibeCast end-session checkbox is separately inventoried as an active
legacy authority seam ([6220433459](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6220433459)),
not a roaming Profile field and not assumed dead. Its proposed removal needs
issuer/consumer/dependency qualification; owner Session-end remains intact.
The portability decision [6220817753](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6220817753)
is **parked**: retain existing chat/DNA import/export/clear controls and warnings;
no integrated backup/restore implementation is admitted in this assignment.
Existing schema1 Profile/household/integration export remains unchanged; it is
not a backup of the new shared DJ defaults. The earlier unpublished local
schema2-export prototype is superseded and removed from active output. A local
schema2 input remains explicitly rejected with `profile_settings_restore_required`
without mutation. Existing chat/DNA formats and controls remain intact. A
defaults-bearing backup/restore needs its separately admitted portability slice.

### Consumer labels and predetermined output acceptance

| Language | client_device | both | ha_speaker | text_only |
| --- | --- | --- | --- | --- |
| en | My DJConnect devices | My DJConnect devices + HA speaker | HA speaker only | Text only (no speech) |
| nl | Mijn DJConnect-apparaten | Mijn DJConnect-apparaten + HA-speaker | Alleen HA-speaker | Alleen tekst (geen spraak) |
| de | Meine DJConnect-Geräte | Meine DJConnect-Geräte + HA-Lautsprecher | Nur HA-Lautsprecher | Nur Text (keine Sprachausgabe) |
| fr | Mes appareils DJConnect | Mes appareils DJConnect + enceinte HA | Enceinte HA uniquement | Texte uniquement (sans voix) |
| es | Mis dispositivos DJConnect | Mis dispositivos DJConnect + altavoz HA | Solo altavoz HA | Solo texto (sin voz) |

Qualify six-field atomic defaults/session/restart and two-Profile isolation;
legacy output conflicts; local autoplay ON/OFF on different protocol surfaces;
configured/unavailable speaker; local replay in speaker-only mode; target-bound
retry/cancellation and uncertain dispatch; `text_only` zero synthesis through
all alternate routes, old assets and in-flight changes; renderer live removal,
reconnect, expiry and end in portrait/landscape. HA-only payloads must never leak
through settings read/write/events/cache or migration. Native UI, audible speaker
and physical device outcomes need their own evidence. The local software proof
below does not establish those consumer or physical outcomes.

## Local six-field software checkpoint

Source `187d2cd126c5db1a2791e1d47d80d803aafc5cc1` connects settings3,
SQLite migration8 and target-aware speech3. [Pinned real HA fixtures](../../examples/client_contracts/profile_session_settings_v3/connected-ha-transport.json)
keep original contract2 fixtures unchanged. Exact source/helper hashes match.

Actual paired HTTP/three TLS protocol surfaces share all six values. The bounded
120.049-second run made351 owner reads and two TLS reconnects with unchanged
row counts; another Profile received zero change events. Actual generic HA
Cloud inventory and synthesis choose the confirmed voice/gender without changing
the global Assist pipeline. External waveforms and speaker sink remain fixtures.

The existing HA media-player service fetched a private speaker grant exactly
once for a manual replay despite a repeated operation. An actual new Session
opening fetched once automatically, including lowercase HTTP authorization;
reads and output switches caused zero catch-up. Text-only and Session end denied
old grants with404. Queued, unavailable and unknown outcomes are distinct from
local-ready and audible playback. A failed speaker target does not discard a
still-authorized local result. No shared display receives settings or grants.

These are local Core software checkpoints. Final exact independent reviews, protected
source delivery, Finalization and any installed/native/audible acceptance remain
open; the SETTINGS family is not Completed.

### Legacy authority and shared-screen qualification

A pre-activation Session may have genuinely unknown Mood. Its settings read
retains the Session identity/generation/revision, but returns `settings: null`,
`selection_required: true` and `selection_basis: legacy_mood_unknown`. Separate
factory defaults are proposals, not a measured/effective Session Mood. Reads,
Ask DJ1 and prepare1 preserve existing unknown-Mood behavior without activation
or fabricated summary coverage. Prepare3 and the first shared mutation require
all six explicit fields in this case; acceptance then materializes the typed
Session and defaults in the existing transaction. No partial voice edit may
silently turn unknown Mood into a factory Mood.

Profile-ID creation/replacement must fail closed while an existing canonical
SQLite service is unavailable: orphan erasure/accepted-default checks cannot
be skipped. A genuinely absent service during first-install bootstrap retains
the existing creation route. Existing owner identity and defaults survive a
failed attempt and remain valid after storage recovers.

Source `62047f49cd5e3a7516bca90897a67ebaa027c7ca` closes the old
`dj_response_enabled=false` authority gap. Before explicit six-field acceptance,
old bound-entry evidence requires review for every prepare version and legacy
generation route. The same evidence is checked again during synthesis and on
private asset access. Once contract3 is explicitly accepted, that old flag
cannot override canonical output. Factory reads and contract1 prepare neither
activate contract3 nor invent an accepted choice; only explicit acceptance
changes the old consumer mutation boundary. Twenty-five focused speech tests
cover these boundaries, withdrawal, races, exact voice and output behavior.

The actual isolated HA/Broadcast browser run reaches both unchanged maintained
renderer builds in portrait and landscape. All four views preserve the actual
current track, immutable Moment text, source link, Spotify mark and readable
layout, through offline/reconnect, original expiry, reload without resurrection
and Session end. Switching text-only/client output causes no speech requests,
audio controls, private settings projection or catch-up synthesis. The CAF
adapter is modeled; this is browser software compatibility, not receiver
deployment, native adoption, audible playback or physical hardware acceptance.

All46 Core constant settings have a source setter/storage/reader/effect
classification in the inventory. Existing active legacy locale, tone and
playback-output adapters retain explicit owning-consumer migration boundaries;
they are not labelled dead merely because no current HA form writes them.
Unchanged administrative paths have source classification, not new physical
acceptance. Platform-wide removal and joint acceptance remain dependency-gated.

## Original five-parameter foundation and local checkpoint history

The following original contract2 implementation notes and fixtures predate the
output addendum. The current version3 delta above takes precedence where scope
differs; their measured acceptance is retained without retroactive expansion.

## One model and five independent parameters

Core owns one typed selection per installation/Profile and one confirmed
effective selection for its active Session/generation. Devices render that
authority; iCloud, local defaults and HA ConfigEntries are not competing stores.

| Parameter | Closed meaning | Effect owner |
| --- | --- | --- |
| `persona` | home_dj/radio_dj/club_dj/festival_dj | Existing Moment realization and common Ask DJ style |
| `voice` | Explicit provider-default, or exact provider-bound concrete voice ID | Existing generic HA TTS processor |
| `gender` | default/no preference, female, male; qualified metadata required for non-default | Exact compatible voice realization, never inference |
| `mood` | chill/groove/energy/party | Existing Session Runtime/Planner and confirmed Mood history |
| `presence` | Existing five Presence policy values | Existing shared budgets and in-flight admission fences |

Persona, Mood, Presence, voice and gender never overwrite one another. Concrete
voice IDs are opaque, bounded and provider-bound; labels are not identities.
Voice selection does not choose an output or enable local autoplay elsewhere.

An explicit accepted field patch changes only those fields and automatically
remembers them as Profile defaults. In an active Session it changes both that
Session and the defaults atomically; without a Session it changes defaults only
and starts no Session or music. New Session start reads the committed defaults
server-side. An explicitly declared start override is a user choice; implicit
client initialization is not. Join/reconnect is read-only. Automatic Mood,
guest signals, refresh, provider fallback and capability restoration do not
write personal defaults. Reset is an explicit operation, not background repair.

Factory values are home_dj/provider-default/default/groove plus the existing
Presence default. They carry factory provenance, never invented user history.
Explicit same-value choice may establish provenance/default even when an
automatic Session value already matches; exact duplicate operation does not.

### Legacy choice review and retirement

The owner read reports a bounded migration assessment before first activation.
It inspects only the resolved Profile's non-default legacy response/voice tone,
its old numeric Mood (without inferring a new default), and tone configuration
of configured entries whose paired device is actually bound to this Profile.
No device name, token, prompt, provider configuration or arbitrary entry value
is exported by that assessment. Different old device tones are conflicting
evidence, never a last-online-device preference or a Persona mapping.

Where such evidence exists, the first contract2 acceptance requires an explicit
complete five-field selection. A partial patch returns
`settings_migration_choice_required`, changes nothing and supplies the review
state. After activation ordinary per-field patches apply. A new Profile with
no non-default legacy evidence can use ordinary patches immediately. Profile
factory response/voice defaults are not proof of an earlier human choice.
The assessment runs under Runtime admission and is revalidated on the HA loop
after SQL staging. An intervening legacy-entry change rolls back a partial
initial choice; an accepted receipt remains immutable recovery evidence.

HA setup/options no longer offer the old voice-profile or response-style knobs
and cannot create fresh copies of those settings. Existing unresolved values
are retained for review. Only after canonical SQL activation may maintenance
retire Profile tone fields and bound-entry tone configuration. The Profile
retirement marker is schema metadata, not another settings authority; reads
still resolve the canonical SQL revision. New factory Profiles omit the retired
keys immediately without activating shared settings; explicit legacy inputs
retain their evidence for review. A failed cleanup never undoes an
accepted choice or reports the whole migration complete. Repeated cleanup,
restart and schema1 import must not resurrect retired keys. Old tone readers
remain isolated compatibility work until their actual consumers have a
qualified replacement; the platform-wide migration node stays open.

## Durable acceptance and existing owners

Reuse Profile authorization/storage ownership, the existing persistence service
and its single DJConnect SQLite database, Runtime lifecycle lock, generic HA
speech owner and existing hybrid transport recovery. No second Planner,
conversation engine, event bus, preference database or arbitrary dictionary.

The current Profile JSON owns identity/accounts/privacy. New five-parameter
defaults have one typed repository under that same Profile domain, backed by
the existing persistence service. Do not duplicate their authoritative values
in HA JSON, ConfigEntry or Runtime serialization. Existing Profile export/import
and deletion must compose this repository through the Profile owner; a stored
JSON preference is not automatically a functional product setting.

Profile lifecycle reconciliation uses the existing Profile write lock followed
by the existing Runtime lifecycle lock, then the persistence provider lock.
Settings acceptance never awaits a Profile write lock while holding the Runtime
lock. A Profile with an active Runtime cannot be deleted or replaced by import;
the owner must explicitly end it first. No implicit Session end is hidden in an
import or deletion. Profile-ID collision is not an implicit overwrite operation.
Deleting the Profile first revokes access; its five-value defaults, effective
settings and operation receipts must then be purged, never reassigned together
with devices. Failure to purge is reported and retried by existing maintenance.
Before a newly created/imported Profile ID becomes visible, purge orphaned
settings for that ID under the same locks. Existing hourly maintenance also removes
orphaned rows in bounded batches: a crash between identity deletion and physical erasure cannot
make old preferences visible if that ID is later reused.

Historical contract2 prototype, superseded by the portability boundary above:
an export captured only typed defaults, not active Runtime settings, receipts,
binding epochs, provider credentials or provider configuration. Full personal export fails closed with `settings_export_unavailable` if canonical
SQLite cannot be read; unavailability never becomes a successful identity-only
export. Explicitly redacted export can omit the private read. The versioned
import disposition must distinguish a defaults-bearing export from historical
identity-only v1 exports. An identity-only overwrite must not silently retain
unrelated defaults. A defaults-bearing restore must not report success before
both Profile identity and canonical defaults have a recoverable accepted state;
if that owner-coordinated restore cannot be qualified, reject it explicitly
rather than silently drop the preferences. Provider-bound voices remain exact
selected intent on restore; availability is independently qualified on the
target installation. No provider-default substitution or Persona inference.

Forward-only migration7 adds typed Profile selections, bounded accepted
operation receipts and Session settings commit metadata to the existing schema.
One short database transaction accepts the changed defaults, effective Session
selection/revision and any confirmed Mood summary interval. Existing Mood
summary `mood_tx` is reused inside this transaction, not called as a separate
best-effort save. No Moment text, provider payload, audio or credentials stored.

Order: existing manager lifecycle lock → provider transaction lock → SQL staging
with expected revisions → synchronous final HA-loop admission → durable commit.
SQL workers never inspect HA entries, Profile owners or provider inventories.
While the provider lock and SQL transaction remain held, the HA loop checks
original entry generation, Profile authority A→B→A, Session identity/generation,
owner policy and relevant voice inventory. That final fence orders admission;
no await separates its decision from creating the definitive commit task.
Revocation before admission rolls back. Revocation after admission cannot undo
an accepted durable operation, but still blocks its private response and audio.
Both successful and conflict responses recheck authority and delivery admission.
Acceptance time uses current UTC after lock waits, bounded below by durable
clock highwater; a second deadline check after SQL staging rolls back expired
requests, including their staged Mood interval. No speculative Runtime state is
published.
Persistence failure before commit leaves both defaults and Runtime unchanged.

After durable commit, apply all effective fields under the same Runtime lock,
invalidate old in-flight presentation/audio and publish the confirmed revision.
Do not call three separately locking public setters or reset Presence budgets.
A cancellation during durable acceptance is resolved before releasing the lock;
the operation receipt distinguishes accepted from rejected/unknown. A committed
operation is never reported as a known rejection or executed a second time.
Broadcast failure after commit does not undo acceptance: read/receipt/resume
returns the committed values. Unexpected apply failure fences further writes
and projects the durable accepted selection before serving confirmed success.

Crash/restart follows existing interruption rules: restore defaults and receipt
outcomes, never resurrect a Runtime. Old Session-scoped operations cannot target
a successor. A Session ending before commit rejects that stale intent; ending
after a valid commit retains the accepted defaults and closes the old Runtime.

### Durable authority generation

An old pending operation must not gain authority merely because a device returns
to its original Profile. The existing Device mapping therefore retains a server-
owned `binding_generation`, persisted once for legacy mappings before Profile
storage becomes ready. It rotates on device identity/type, linked Profile,
pairing state or relevant Profile permission changes. Ordinary display-name and
metadata changes preserve it. Restart preserves the committed generation;
household import cannot supply one and rotates it. Exports omit this authority
metadata. It is not a user preference, credential or new pairing mechanism.

Existing Profile setters stage immutable candidates. Storage must expose only
the latest committed Household while awaiting a write, reject a stale second
candidate after another commit, and preserve old state on failure. Publication
and media withdrawal follow definitive storage acceptance. Onboarding retains
its separate existing cancellation/rollback contract. Settings authorization
combines this durable mapping generation with the existing entry/pairing and
Profile checks; it does not use the broad RAM authority revision as the settings
concurrency token or regenerate persistent identity on every read.

## Versioned owner transport and synchronization

### Connected local contract2 wire (not protected delivery)

The local producer implements `GET /api/djconnect/v1/profile/settings`,
`PATCH /api/djconnect/v1/profile/settings`, and the pure receipt read
`POST /api/djconnect/v1/profile/settings/operation`. GET has exactly
`contract_version=2`, `device_id`, `client_type` query fields. PATCH has those
three identity fields, `binding`, UUIDv7 `operation_id`, a non-empty closed
`patch`, `expected_defaults_revision`, and `expected_session`. The latter is
either explicit null or exactly `session_id`, `generation`, `revision`.
Receipt read has identity, binding and operation_id only. No caller Profile ID,
save-as-default switch, autoplay or arbitrary HA command belongs to this schema.

Each successful read/update includes `snapshot.defaults` (all five typed
values), `defaults_revision`, `activated`, `updated_at`, and nullable `session`.
An active session has its immutable identity/generation, all five `settings`,
its independent `revision`, the accepted `defaults_revision` and `updated_at`.
The owner envelope supplies opaque `binding`, allowed values and provider voice
labels, `writable_fields`, `voice_revision`, selected voice availability/reason,
`as_of`, and private/no-store policy. Machine codes remain untranslated;
presentation owners render canonical terminology in all five languages.

An update adds `accepted`, `replayed`, original operation identity and expiry.
A repeated operation returns its immutable earlier snapshot; it never rolls
current Runtime state back. Read current settings separately. Receipt read
returns `accepted` with the original receipt, `not_accepted` for live absence
under the same serialized owner, or `unknown` for expired absence. An expired
absence is not evidence that an earlier mutation never happened.

The existing paired TLS action socket retains its protocol1 envelope. Existing
`djconnect/read` gains operations `profile/settings` and
`profile/settings/operation`. The narrow contract2 write command is
`djconnect/profile/settings/update` with one `payload` using the same owner
schema. `djconnect/profile/settings/subscribe` has `contract_version:2` and
boolean `enabled`; opt-in avoids sending new event types to old consumers.
An enabled socket receives only `profile/settings/changed` invalidation hints,
including without a Session, then reads current state through the same owner.
Hints carry no preferences or Profile identity. Existing queue/capacity/TLS,
final ingress checks and per-recipient paired authority still apply. The
existing HA event infrastructure carries an owner equality hash only; there is
no new bus or polling monitor.

`POST /speech/prepare` accepts contract2 identity, accepted `reference` and
`processor:ha_configured`; caller voice_id/voice_preference are forbidden.
Core reads the confirmed shared choice. The same existing speech owner handles
source admission and synthesis. Original `/speech/audio` uses its unchanged
contract1 asset-read envelope; its internal source/settings/provider guards
fence every byte. The cache key includes the confirmed settings equality token.
Unqualified local OS voice equivalence is not a roaming fallback. After shared
activation, old speech preparation and old explicit Session-setting mutations
return `settings_contract_upgrade_required` (426); accepted question text is
not regenerated. Common Ask DJ supports speech negotiation1/2 and reads shared
Profile Persona/Mood even with no active Session; numeric client initialization
and legacy response_style no longer override that confirmed state.

The connected producer is still local and unpublished. Discovery now advertises
settings2 and supported speech preparation1/2 without changing speech1 scope.
The isolated HA checkpoint includes all-five TLS propagation, source/voice
fencing and a120-second read/reconnect soak with unchanged settings/receipt row
counts. These protocol surfaces are not physical Apple acceptance.

The local legacy-retirement checkpoint `f5d9e6c770f425cc367ec55101854f4d4bbb98d5` additionally
qualifies real HA Profile Store/ConfigEntry evidence, rejected partial activation
with unchanged SQL, full five-field acceptance and retryable retirement with
unchanged binding/defaults. Its [transport fixture](../../examples/client_contracts/profile_session_settings_v2/connected-ha-legacy-migration.json)
is separate from the earlier 120-second soak fixture. Eleven migration tests
cover held Store writes, entry changes after SQL staging, immutable replay,
factory creation and untrusted import markers. The full local suite ran 2120
tests: 2113 passed and 7 existing tests skipped. These are local Core checkpoints,
not a final candidate review, installed client or audible voice qualification.

Profile deletion/recreation and identity-only replacement are locally connected.
The superseded unpublished contract2 export prototype contained typed defaults;
it is removed from active output under the parked portability decision. In that
historical checkpoint, schema1 remained the
historical identity-only format. Schema2 restore currently returns
`profile_settings_restore_required` without mutation. Schema1 replacement of an
activated Profile also rejects rather than silently retaining unrelated defaults.
Owner-coordinated defaults restoration and complete legacy disposition remain
open deliverables, along with final exact candidate reviews and protected
source delivery. This section does not declare family closure.

Speech discovery keeps its original version1 envelope and explicitly scopes
legacy local voice options to prepare-version1. A per-prepare-version descriptor
is authoritative: version2 has only `ha_configured`, Core-owned shared selections,
no caller voice override and retained Profile defaults after Session end. The
presence of old top-level voice keys never grants version2 local authority.

New settings contract2 describes exactly these five values and their semantics;
do not relabel the old voice/device contract1 as roaming. Ordinary existing
paired-device auth resolves the bound Profile; caller profile_id grants nothing.
Return closed allowed-values, per-field writable/reason, selected/effective
values, availability/provenance, opaque binding/generation, independent
settings/default/Session revisions and server time. Profile settings work with
no active Session. Guests/shared screens get no owner preference projection.

Read, partial write and operation readback use the existing HTTP/WS adapters and
hybrid recovery discipline. Writes carry a bounded UUIDv7 operation identity,
creation/expiry, expected defaults revision and explicit expected active-Session
identity/revision (or confirmed absence). Unknown fields and invalid types fail
closed. An immutable digest binds patch, purpose, Profile authority and Session.
Receipt replay with a different digest conflicts; expiry never becomes a new
operation. Reuse five-minute validity and bounded transport receipt policy;
retain dedup evidence while any accepted request may still legally replay.

One coherent read snapshot reports either pending/recovery or confirmed durable
values. A conflict returns current authorized revision without silent merge.
Two devices editing different fields still require an explicit fresh revision;
never replay an uncertain mutation blindly from WS to HTTP. All reads are
no-store and cause no provider lookup, synthesis, playback or preference write.

Existing authenticated owner transport gains Profile invalidation even with no
Session. Reuse the existing HA/transport event infrastructure with recipient
authorization, not a second bus/polling service. Event hints expose no private
payload to shared receivers; reconnect/foreground uses exact current readback.
Mac/iPhone/iPad receive one confirmed choice; an unopened or offline client
does not become an authority. Late old-generation responses are discarded.

## Voice availability, revision and privacy

Reuse the actual configured Assist pipeline, generic provider inventory and
explicit gender metadata. Stable chosen voice identity is distinct from the
current inventory/configuration revision. A provider swap or removed voice
retains the selection as selected-but-unavailable with a functional reason.
Do not erase it, substitute another voice or write the global HA pipeline.

Validate voice and gender together. A concrete voice incompatible with the
retained gender rejects the entire patch; the user can explicitly patch both.
Provider-default plus qualified gender resolves through current advertised
targets. A provider offering voices without gender retains concrete choices;
unsupported gender is visible, never inferred from name/pitch/Persona. If two
devices use different configured providers, the same saved provider-bound
selection may be unavailable on one; it must not become a local substitute.

Future generation and synthesis capture settings/voice/provider revisions and
revalidate at acceptance and audio delivery. Old bytes cannot be presented as
the newly selected voice. Already accepted text/history remains immutable; no
playback effect is repeated to repair presentation. Original source grants,
expiry, bounded RAM cache and withdrawal fences remain mandatory. No provider
credentials, private grants or preference documents enter passive surfaces.

## Migration, old consumers and platform cleanup

The [inventory](PROFILE_SESSION_SETTINGS_INVENTORY_V1.json) records static source
evidence separately from qualified setter→store→reader→effect proof. Initial
STATIC_ONLY rows are unfinished work, not a zero-dead-settings claim. Every
active lane must receive KEEP/REPLACE-MIGRATE/REMOVE plus its owning writer;
retired Windows gets legacy recognition/removal disposition, no new feature.

Investigate voice_profile, voice_style, response_style, numeric Ask DJ Mood and
Mood→voice overrides. Similar labels never justify a Persona conversion. Migrate
only valid explicit evidence once; conflicting device/HA values need a surfaced
choice, not last-online-device-wins. Delete obsolete keys only after qualified
acceptance and export/import/restart proof. Do not erase history/DNA/pairing.

Old contract1 reads retain their frozen meaning. Old mutation adapters have an
explicit bounded transition: before Profile migration they retain documented
legacy behavior; after a confirmed contract2 activation they reject conflicting
legacy five-parameter writes with a typed upgrade requirement rather than
silently changing contract1 semantics or maintaining a second authority.
A client without the shared editor must show the typed upgrade requirement,
preserve its confirmed selection and offer reopening a supported client followed
by owner readback. It must not claim a new editor is already installed, reset
choices, retry a legacy write blindly or reconstruct a Profile default.
All actual setting application uses the shared existing Runtime owners. These
adapters are not permission to declare platform cleanup complete: removal is
required once all supported owning consumers have adopted contract2. No new
consumer writes legacy fields. Local autoplay/output/volume/microphone/haptics
remain truly device-owned and are not swept into roaming defaults.

## UX, delivery and predetermined acceptance

Apple Instellingen → Profiel → Jouw DJ and Session quick controls use one shared
service/state for all five, en/nl/de/fr/es and accessible pending/error/conflict/
unavailable/reset states. During a Session explain now-and-next-Session behavior;
without one edit defaults without starting playback. Keep drafts/scroll/output.
Apple/Watch/Pi/ESP/web/website changes belong to existing owning lane writers;
Core does not absorb their WIP or expand reviewed candidates silently.

Required evidence includes each of five changed from one paired owner device,
automatic confirmed selection on two other same-Profile devices, actual effect,
end/new Session from another device and restart persistence. Also prove no-
Session edits; per-field retention; no replay/init/default pollution; two-Profile
and guest isolation; A→B→A; concurrent edits; before/after-commit failure,
cancellation, crash/reload and receipt recovery; automatic Mood isolation;
voice/gender conflict/provider withdrawal/in-flight synthesis; original expiry;
legacy migration/import/removal; all five languages. Only external provider
boundaries may be fixtures in isolated real HA acceptance.

Linked packages must separately track Core all-five producer/consolidation,
Apple editor/adoption, other active consumer dispositions, migration/removal and
joint acceptance. Source/fixture, native, installed, audible and hardware claims
stay separate. Core producer delivery is not completion of the whole family.
Normal exact-candidate protected publication, independent technical/privacy and
product/UX reviews, actual artifact readback and separate Finalization apply.
