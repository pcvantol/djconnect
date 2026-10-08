# Native Moment delivery

Selected increment: DJC-CORE-NATIVE-MOMENT-DELIVERY-V1-20261008.
Existing owner authorization, Runtime → Planner → Knowledge → Moment → Flow →
Presentation/Broadcast remain authoritative. No additional endpoint or local
consumer intelligence. This contract describes bounded active-Session display,
not durable history, speech/model permission or a new source family.

## Field-specific source basis

Primary terms checked 2026-10-08; local owner consent does not replace them.

| Existing normalized fields | Basis | Native visual current | Active-Flow recall |
| --- | --- | --- | --- |
| MusicBrainz recording artist relationships/credits, work composer relationships, artist begin/type dates | CC0 core entities and relationships | Yes, qualified identity/role/date precision and original links | Same active Session, published Flow membership and original 30-minute source deadline |
| Wikidata artist entity description | CC0 structured entity namespace | Yes, qualified entity and source link | Same bounded active Session and original 30-minute deadline |
| Spotify album release metadata | Spotify display terms | Current associated playback only; Spotify attribution/mark and album link retained | No additional historical-display qualification |
| Runtime-authored Session Direction updates | Existing internal Session context | Same active Session, original card duration | Same active Flow only |
| Unknown source, unqualified Track Insight/provider result or derived Transition | No native field-specific qualification supplied | Denied | Denied |

MusicBrainz [database field breakdown](https://musicbrainz.org/doc/MusicBrainz_Database)
and [data license](https://musicbrainz.org/doc/About/Data_License) distinguish CC0
entities/relationships from supplementary annotations/tags/ratings. None of the
latter is admitted. Wikidata [copyright](https://www.wikidata.org/wiki/Wikidata:Copyright)
covers structured entity data; article text is not substituted.
Spotify [developer terms](https://developer.spotify.com/terms),
[policy](https://developer.spotify.com/policy) and
[design rules](https://developer.spotify.com/documentation/design) require
appropriate associated-content display, attribution and links and constrain
retention. Current-only admission is a conservative implementation boundary.
No new provider access, model processing, TTS, training, imagery rights or
external historical-use permission is inferred.

## Admission and lifecycle

`native_delivery.schema_version=1` is an additive renderer-safe projection,
separate from immutable `dj_moments`. Its current ID must match current playback,
playing state, original presentation deadline and source validity. Active-Flow
IDs refer only to published eligible Moments still in this Runtime's Flow.
The accompanying admissions specify original source expiry, display expiry,
qualification, attribution needs and allowed actions. Retain every source URL,
including both recordings for shared producer. Unknown/malformed evidence is
denied, never reconstructed from generated text. Shortest of both source
observations controls shared producer. Reconnect does not renew either clock.

Source expiry removes rendered source content and associated Presentation/Flow
labels from delivered snapshots/events/recovery. Lifetime projection does not
rewrite semantic Moments, Planner placement or its Flow revision. Native
admission revision and Broadcast watermark have distinct meanings. Pending
subscription delivery is rechecked. Recovery falls back to a fresh snapshot if
its retained source-bound events cannot safely be replayed. End removes every
admission and disposes subscriptions/replay; Profile authorization and entry
unload retain their existing owners. Individual source revocation is not
implemented or claimed; Session disposal is the available revocation boundary.

Native consumers replace admission state, never restore excluded cards from
local history. Deadlines additionally bound offline/background display;
reconnect requires fresh owner authorization and projection. No-store applies
to all existing Session JSON responses including errors. It does not replace
authentication or guarantee deletion from an already cached older client.

## Actions

Current Moment actions are semantic suggestions. No generic executable Moment
route exists. Native executable allowlist is empty; unsupported actions remain
hidden/non-executable, without interpreting their payload as a command. Existing
Ask DJ, queue, player and handoff routes retain their own authorization and UI
ownership. No playback mutation occurs from display or navigation.

## Before / after qualification

Before: native cannot qualify source cards; snapshot/recovery retains source
text after expiry; owning Session HTTP success/error lacks explicit no-store.
After must prove through the real Runtime and transports: qualified current
credit and two-source callback, permitted prior active-Flow recall, unchanged
text/links/persona, unknown/expired/shortest-source rejection, no TTL renewal,
pause/track change/end/profile isolation, pending/recovery safety, no-store and
empty executable-action admission. Software/source-shaped examples are separate
from Apple native readback, live providers, installed HA and parked Pi evidence.

## Wire fields (v1)

The existing `dj_moments`, `presentations`, `playback`, `session_flow` and
`broadcast.snapshot_watermark` retain their shapes. `native_delivery` appears
in the snapshot and incremental event payload. It contains:

- `schema_version: 1`, exact `session_id`, `revocation_scope: "session"`
  (or `"subscription"` for channel withdrawal);
- `revision`: deterministic opaque hash of admission state, not a delivery
  sequence, authorization credential or a Planner Flow revision;
- `current_moment_id`: newest admissible contribution for current playback,
  or null; superseded cards never become current again;
- `active_flow_moment_ids`: publication-order eligible IDs for bounded recall;
- `admissions[]`: `moment_id`, `qualification` (`qualified`, `unqualified`,
  `expired`), `current_display_allowed`, `active_flow_display_allowed`,
  `source_expires_at`, `display_expires_at`, `executable_actions: []`,
  `requires_spotify_attribution`.

UTC deadlines are anchored once at original publication and the original
monotonic observations; never at snapshot retrieval. Internal Session context
has null source expiry and remains subject to the active authenticated Session.
Source expiry and presentation timeout withdraw current authority independently;
presentation timeout alone does not revoke allowed CC0 Flow recall. Pause,
item/output change and the existing seek invalidation withdraw old current-card
authority permanently; permitted Flow recall may remain. New published content
has its own original boundary. Unsupported/additive fields never grant access.

Native consumers must treat the current ID and allowed Flow IDs as replacement
state. They use the unchanged corresponding Moment text, Persona, HA meaning,
playback binding and both attribution URLs. Missing/unknown schema, admission,
source deadline or required attribution means suppression. Cards are ephemeral
memory-only. On background/disconnect or lost authenticated Session authority,
clear display authority and require a fresh authorized projection to resume;
never reconstruct it from local history or invoke a semantic action payload.
Receiver events are independently visibility-scoped, including pending setup.
Source-bound recovery deliberately returns existing `snapshot_required` so
retained source event text cannot revive old content. Internal-only replay
reprojects admission at delivery and includes original delivery sequences.

Entry unload uses its existing entry-generation revocation boundary to stop
live/pending/recovery owner subscriptions bound to that authorized entry, as
well as its observer and late opportunities. Each revoked channel receives
`broadcast_stopped` with empty native authority; another entry's authorized
stream and the Profile Session remain intact. Unloaded-entry authentication is
unavailable and stale in-flight generation cannot register. Options reload intentionally
preserves the Profile's active Session and original source deadlines; it is not
an individual source revocation. No individual source-revoke API/status is
claimed. Session end is the implemented content revocation boundary; terminal
snapshots/events contain no admissions or old rendered source copies.

The Golden Scenario connection is safe server-authoritative Session delivery:
existing playback/Ask DJ/Track Insight controls remain independently qualified;
this increment proves Runtime/owner-contract behavior and makes no installed,
live-provider, native-render or physical-Pi Golden Scenario claim.

A revoked pending subscription discards its queued source frames and delivers
only the terminal withdrawal after its initial result, then unregisters. Entry
withdrawal uses one real Broadcast delivery boundary; unaffected subscribers
receive ordinary Flow state with that sequence. If Session end wins during
initial transport result delivery, failed activation emits a terminal
`broadcast_stopped` denial with complete empty native authority and no invented
sequence/replay boundary. Consumers must process terminal denial before
ordinary card ordering: it grants no text or action and can only clear
visibility. This is an existing subscription lifecycle repair, not an
individual source-revocation API, generic authorization engine or new event type.

Session Flow as a reference is not by itself a native external-source rights
basis: derived Transitions whose underlying knowledge lacks native field
qualification are not admitted merely by declaring them internal. Their
existing semantic publication, Genre→Track/Recommendation selection and
VibeCast behavior remain unchanged. Only the actual validated Session Direction
Moment family qualifies as source-free Runtime context here.
