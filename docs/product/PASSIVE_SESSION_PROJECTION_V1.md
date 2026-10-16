# Passive Session projection v1

Status: selected design and implementation, not delivered or consumer-qualified.
Assignment `DJC-CORE-PASSIVE-SESSION-PROJECTION-V1-20261015`;
[owner selection](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6199213014).
Reuse `SURFACE::CORE::PROJECTION`; no second surface family or Planner.
Actual admission base `9faffe533d4a117eb8ad362e73809d126bdcc9d7`, branch
`codex/passive-session-projection-v1`, same sole Core writer. Predecessor
source #1189 / Finalization #1190 is closed, exact artifacts qualified and
bounded own cleanup complete. This contract precedes runtime changes.

## Experience and inventory

One active Session, one current contribution, independently observed music.
Small/medium/large widgets and an existing Session Activity use the same server
projection; native hosts choose their layouts, never infer facts or summarize.
No active Session means neutral widgets and no active Activity. A pause remains
the same active Session. Navigation opens the exact authorized Session; it
does not play, start, replace, speak, dismiss remotely or send a question.

Reuse Runtime/Planner/Knowledge/Moment/Flow/Broadcast semantic acceptance,
original `MomentDeliveryBoundary`, existing observation work, subject-qualified
Session image registry and ordinary device/Profile authorization. These owners
already supply source identity and pixels. Their foreground/private grants are
**not** passive grants; this contract adds the independent field/purpose decision.
Do not call owner snapshot/history loaders and copy their dictionaries into a
widget cache. Private Ask DJ, history summaries, Music DNA, credentials, full
provider payloads and private Planner/Horizon never enter this projection.

Apple confirms its tracked neutral foundation document at document commit
`9eb912e4c7a111336a509d2dae82ff105890ede6`, current source
`2daf6f4a767673f34d4fbb3bb2e240bfe893e362`, SHA256
`2956fad7776dfc8ea013c8261d9aa205fc8f2202ad07db619dc2d3d234e045b5`.
Its 120-second non-sliding neutral snapshot and `pushType:nil` are separate
evidence, not rich/installed/background/Watch acceptance. The selected
Session-only consolidation supersedes the historical independent-widget KEEP
decision; preserve old kinds as migration aliases, explicit player navigation
and the original dated design. No Swift write or consumer dispatch here.

## Source × field × surface qualification

`allowed` below is conditional on normal private owner authority, explicit
surface consent, exact subject/provenance, unexpired original deadline and the
native attribution/cache obligations. Omission is per field, never a fabricated
all-null completion. `not_qualified` has a concrete missing permission; it is
not inferred permanently forbidden. `unavailable` means evidence or data absent.

| Source / field | Widget + bounded App Group | Activity / locked OS snapshot | Watch / external relay | Decision basis |
| --- | --- | --- | --- | --- |
| Confirmed Session state, closed Mood/revision, Presence, Persona | allowed | allowed only after explicit locked-display consent | not_qualified | Core-authored state; no personal Profile/name/device identifiers |
| Actually published Runtime-authored direction | allowed, exact complete short text | same explicit consent | not_qualified | Existing accepted contribution; no private discovery reasons or internal plan |
| MusicBrainz/Wikidata CC0 normalized factual Moment | allowed, exact complete short text and every original source link | same explicit consent | not_qualified | CC0 fact anchors plus existing local authored expression; not licensed prose or picture inference |
| Spotify observed track/artist/album metadata | allowed as independent currently observed context | same explicit consent | not_qualified | Temporary necessary application presentation, exact source link + Spotify mark, no future/queue claim |
| Spotify exact track/album cover bytes | allowed under independent bounded cover grant | same explicit consent, original source/display expiry | not_qualified | Cover-only temporary necessary application cache; no crops/overlays, no reusable owner URL |
| Spotify artist photograph / Forecast art | not_qualified | not_qualified | not_qualified | Temporary caching clause names metadata and cover art; existing artist-photo owner grant is insufficient for OS retention |
| Provider prose, Spotify genre/biography narrative, Wikipedia summary | not_qualified | not_qualified | not_qualified | No new passive prose/cache permission inferred from native admission |
| MusicBrainz/Wikidata image URL / P18 alone | not_qualified | not_qualified | not_qualified | Database CC0 is not an image licence; no new Commons adapter or name search |
| Missing subject, wrong edition, missing attribution, withdrawn source | unavailable | unavailable | unavailable | Do not substitute current music's image for the contribution subject |
| Ask DJ/private/history/DNA/raw data | not_qualified | not_qualified | not_qualified | Outside selected passive purpose, including first-party generated private answers |

Source-policy read 2026-10-16: [Spotify terms](https://developer.spotify.com/terms),
IV.3 temporary metadata/cover cache necessary for application functionality,
V.8 withdrawal and IX.8 termination; [Spotify policy](https://developer.spotify.com/policy),
II.4 attribution/link and II.5 underlying-content connection;
[MusicBrainz data licence](https://musicbrainz.org/doc/About/Data_License).
The bounded cover interpretation is a product qualification subject to exact
privacy/experience review, not a blanket licence or promise of immediate remote
OS-pixel deletion. Deny any source requiring a stronger withdrawal guarantee.
No processing beyond the current personal application, export, public display,
ad/standalone art service, external relay or indefinite/offline library.

## Transport, consent and authority

Version `1`, advertised only with a connected producer. Ordinary paired device
bearer remains in the foreground app's normal secure storage, never App Group,
deep link, payload or artwork URL. No HA administrative credential substitute.

1. `POST /api/djconnect/v1/session/surface/authorize` accepts exact identity,
   `contract_version`, `session_id`, `surface` (`widget` / `live_activity`),
   `enabled`, `os_snapshot_cache` and `locked_display` booleans. This explicit
   foreground action grants/revokes **only** transient surface presentation.
   Activity requires locked-display consent. No playback/provider preparation,
   model call or semantic publication. No implicit consent from app launch,
   existing pairing or foreground `no-store` owner rights.
2. `POST /api/djconnect/v1/session/surface/read` accepts identity, version,
   exact Session, surface and opaque `grant_id`. It is a pure authorized query;
   no new permission, state write, observation, fetch, artwork preparation or
   publication. Unknown/wrong owner/purpose/old grant returns no rich data.
3. A separate paired image read uses the same exact grant/session/surface and
   asset identity. It serves only already-prepared, independently allowed bytes.
   No external URL is a credential or permission. Transport responses use
   `no-store`; payload's explicit short-lived passive cache grant is the only
   exception for the specified fields and pixels, not the whole HTTP response.

At most 32 transient grants per active Runtime, one per exact paired entry and
surface; no new Store or general eventbus. Capture existing entry generation,
installation, Profile authority revision, exact active Runtime and original
source/account. Pairing rotation, unload, source change or A→B→A invalidates the
captured grant. Reauthorization creates a new opaque generation; cached old
content cannot be accepted under it even when a Profile display name repeats.
The grant is not a standalone bearer and is never valid for another device.
Revocation and Runtime disposal release its small state. Capacity fails closed;
never evict live dedup/authority evidence to make an old grant valid again.

## Projection and ordering

Required envelope: `schema_version`, `surface`, opaque `binding_id`,
`generation`, `session_id`, `delivery_sequence`, opaque equality `revision`,
`as_of`, original `observed_at` / `expires_at`, `state`, `cache_policy`,
`mood {value,revision}`, `presence`, `persona`, typed `open_session` navigation.
No Profile/account/device identifiers in the passive cache. Installation/owner
are represented by the opaque binding; the authenticated app owns its mapping.
`delivery_sequence` is ordered only within the same generation, never compared
across generations. Hash/media revisions are equality tokens, not counters.

Optional independent fields:

- `contribution`: original accepted `moment_id`, `published_at`, complete text,
  Persona at publication, original source links/attribution and expiry. Maximum
  640 characters; omit overlong content instead of chopping a factual sentence
  or dropping a source. No local or new model summarization. Only actually
  published non-Silence, public/shared-qualified facts/direction; no owner-only
  private contribution. Selection uses the existing newest qualified Moment,
  not a second opportunity or catch-up queue.
- `now_playing`: exact accepted item identity, track/artist/album, original
  observation, source link/mark and its own expiry. Never a prediction. Current
  observation B and contextual contribution A keep separate subject identities.
- `artwork`: independently qualified exact cover subject/role, asset revision,
  original capture/source deadline, source URL/attribution, permitted resize,
  dimensions, five-language alt text, and explicit cache/display/OS-snapshot
  rights. Moment cover and current-playback cover are distinct slots. Artist
  photo unavailable leaves text/metadata intact, no wrong-subject fallback.

Server uses original monotonic deadlines and UTC projections; no sliding TTL.
Snapshot/cache lifetime is at most 120 seconds from the relevant original
observation; each field is also bounded by its shorter original source and
presentation deadline. New media revision preserves the same Moment and original
publication/deadline; zero additional semantic publication/summary count.
Reads, reconnect, redraw, Mood/Persona changes and unchanged cached bytes cannot
renew old evidence. Consumer removes expired fields before rendering; clock
uncertainty fails neutral. A missed update never authorizes indefinite richness.

Existing owner Broadcast carries a bounded surface invalidation hint only;
the app rereads the authorized projection. No rich passive payload is added to
shared VibeCast, legacy history or notification diagnostics. Live events and
recovery coalesce current valid state, never replay contributions as new ones.
The same generation/sequence checks apply before writing shared cache or pixels.

## Lifecycle, failures and storage boundaries

| Trigger | Required result |
| --- | --- |
| New accepted contribution | Existing publication/budget first; newest independently eligible short contribution, no extra counter |
| Same Moment / new media | Same identity/text/publication; only image equality revision changes |
| Mood / Persona setting | Confirmed state/revision changes; old contribution's Persona/text remains immutable |
| Music-only / Silence | Clear proactive contribution slot; optional permitted current music/state remain; no fill, push or extra publication |
| Pause | Active paused Session, no fake end; original validity still expires |
| Track B after contribution A | Separate current B context and exact eligible A cover; no image relabeling or false current assertion |
| Provider/media timeout, missing art or rejected licence | Text independently survives; bounded existing media retry/backoff only at owning lifecycle work |
| End / interrupted / replacement | Remove owned transient grant/cache/decoded bytes, end Activity when learned; no Runtime restoration or auto restart |
| Profile / source / pairing withdrawal | Deny read/bytes and old generation, including late completion and A→B→A; no fallback to old grant |
| Offline / missed end | Original expiry → neutral; eventual end converges when learned, no guaranteed deletion of offline OS pixels |
| User dismisses | Local only, Session/music unchanged; no automatic Activity recreation loop |
| App reload/reconnect | Revalidate current binding/generation, coalesce newest eligible state; no catch-up or renewed old deadline |

No passive content archive. Native App Group keeps at most current authorized
snapshot and its required cover files, not history/backup; purge on expiry,
generation change, consent/source withdrawal and end as learned. Transport error
is not a fresh snapshot. OS may retain pixels despite best-effort neutral/end
updates: document that limit in native UX, do not claim synchronous erasure.
No logs/diagnostics contain text, art, grant or private identifiers.

## Separate background and consumer delivery

Existing `SURFACE::APPLE::QUIET-TRANSPORT` is the dependent background package:
ActivityKit versus ordinary APNs token family, rotation/environment/unregister,
Session/generation binding, update/end dedup, expiry/revocation/dismissal, relay
content permission, separate WidgetKit refresh budgets and real OS latency.
Push-to-start and new keys/signing/cost/relay deployment remain unselected.
Foreground, suspended, terminated, locked, offline and Watch are separate
acceptance categories. Watch replication/container has no grant in v1.
Native widget gallery migration and installed rich layouts remain Apple-owned.

Early handoff requires exact local contract/producer SHA, schema/checksum and
real sanitized transport fixtures in Apple #87; final protected main/artifact
replaces provisional pins. No Swift or receiver changes/new consumer writer.

## Qualification plan

Use real isolated HA normal pairing → existing Session/Planner/Knowledge/Moment
acceptance → existing media preparation → authorized passive read/bytes/live
invalidation. Only external provider/CDN may be fixtures. Independently count
model/provider/preparation/publication/playback effects before/after repeated
reads: all deltas zero. Require positive complete text, independent metadata
and permitted cover; no all-neutral PASS. Test two subjects, original expiry,
same Moment/new image revision, wrong purpose/owner/generation, source/license/
attribution denial, A→B→A, music-only, Mood, pause, end/race/reload/cancellation,
bounded memory and existing regression/security/owning gates. Relate indirectly
to Golden Scenarios: no new Planner selection; qualify downstream authority.
Independent exact technical/privacy and product/experience review before any
source publication; source and separate Finalization keep their exact gates.

Core producer, native rich adoption, background, Watch, installed and physical
joint acceptance are reported separately. No pass or delivered node is claimed
by this design-first commit.
