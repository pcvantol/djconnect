# Profile and Session settings consolidation

Assignment `DJC-PROFILE-SESSION-SETTINGS-CONSOLIDATION-V1-20261016`.
Owner decision [6214905647](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6214905647)
supersedes assessment6209817556 for this successor. Design precedes runtime.
Admission base `148bd5aee3110c1a1ab13e7c463a164c99d79b70`; same Core writer,
branch `codex/profile-session-settings-consolidation-v1`. Earlier source and
Finalization1191/1192, speech and provider-gender releases remain history.

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

An export captures only typed defaults, not active Runtime settings, receipts,
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

Profile deletion/recreation and identity-only replacement are locally connected.
Export schema2 contains only qualified typed defaults; schema1 remains the
historical identity-only format. Schema2 restore currently returns
`profile_settings_restore_required` without mutation. Schema1 replacement of an
activated Profile also rejects rather than silently retaining unrelated defaults.
Owner-coordinated defaults restoration and complete legacy disposition remain
open deliverables, along with final exact candidate reviews and protected
source delivery. This section does not declare family closure.

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
