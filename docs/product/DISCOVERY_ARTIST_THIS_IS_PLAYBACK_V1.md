# Discovery artist playback repair v1

Owner request, revised 2026-11-06: Ontdek artist Play Now starts the selected
artist directly through Spotify, without a This Is promise. Resolution remains
server-owned from the original cached discovery item/section, never a client URI,
guessed playlist ID, playlist creation or top-tracks substitution. The existing
music_discovery/play request and ordinary pairing/Profile identity remain; Apple
refreshes status/queue after one successful request with no replay.

## Confirmed defect and scope

The old handler passes context_uri alone to play_context_at for every non-track.
That backend operation requires offset_uri, so artists/albums/playlists fail
before valid context playback. It also unconditionally returns played:true and
records positive DNA feedback even when playback reports failure. Correct both.
Track playback stays an exact one-track selection. Album/playlist context starts
must not use an offset-only operation. Artist selection is resolved separately.

## Exact direct artist playback (owner decision 2026-11-06)

The owner explicitly selected direct Spotify artist playback, without promising
This Is. This supersedes the former official-playlist-only resolution for artist
cards. All three actual read-only artist probes (London Grammar, Snow Patrol,
Son Mieux) resolved their artist identities but returned no qualified official
This Is candidate. Search absence is not playlist nonexistence or proof of the
app's quota mode. Reauthorization does not grant editorial catalogue access.

Resolve only the original server-cached Spotify artist URI through the exact
provider artist endpoint. Require consistent provider id/URI/type and a nonempty
name; then dispatch that same artist URI as context_uri on the currently observed
unrestricted output. Never substitute a playlist, top-tracks list, another artist,
fan selection or a URI supplied by the client. There is no playlist search or
playlist-items prerequisite in artist Play Now. Spotify owns the contents and
ordering of its artist context; DJConnect does not label that context This Is.
Track, album and playlist handling and original-card effect fences are unchanged.

The existing explicit playlist-identity diagnostic stays read-only and retains
its exact Spotify owner/title/credited-artist checks. Legacy This Is resolution
utilities are not called by artist Play Now and grant no alternative playback.
Only supported Spotify APIs are used, without scraping or hardcoded playlist IDs.

Primary references checked 2026-11-06:
- https://developer.spotify.com/blog/2024-11-27-changes-to-the-web-api
- https://developer.spotify.com/documentation/web-api/tutorials/february-2026-migration-guide
- https://developer.spotify.com/documentation/web-api/reference/start-a-users-playback

## Authority and effect boundary

Capture original paired entry/token/owner/Profile/backend/account/consent/privacy
and exact cached item identity before awaits; validate after resolution and after
last token/other await immediately before dispatch. Profile/source replacement,
clear/disable, pairing rotation or stale item aborts without playback or feedback.
Read-only provider resolution does not authorize a new owner or output transfer.

Use one exact context-start PUT for the qualified artist/album/playlist, never append/enqueue,
clear/skip loops or client cache replacement as a playback effect. No automatic
output transfer or replay after uncertainty. No active output returns explicit
output-required state; selecting output and retrying remains a new user action.
Provider acknowledgement is dispatch evidence. Exact context/status/queue
readback and audible/native acceptance remain separate; do not claim manual
Spotify queue entries were erased merely because context start returned204.

Only successful dispatch may set played:true, record positive DNA feedback and
invalidate the feed. Resolver/provider failure, uncertain write, output-required
or stale authority returns played:false and no feedback. Provider errors remain
command-scoped with no global backend-health or DJ/voice-state mutation. Internal
error codes stay machine-readable; clients own localized presentation in all five
languages. No raw tokens, search responses or private context in diagnostics.

## Required proof and delivery gates

Causal regressions must demonstrate the old missing-offset failure, real provider
URI/artist binding, independence from editorial search, retained read-only playlist diagnosis, fan/wrong/same-name/ambiguous/missing/restricted cases,
legacy/new item envelopes, one context write replacing the selected context,
no output transfer/replay, failed dispatch without feedback, and stale authority
through token/provider waits. Actual disposable paired HA proof uses synthetic
external wires, original failure evidence and exact current source/harness pins.
No live playback or OAuth change during source qualification. Protected source,
new exact-head owner authorization, separate Finalization, HA-dev-with1439 install
and physical/provider/native acceptance remain independent. Retained-widget
projection4 is not part of this repair and must remain out of the installed main.

## Explicit candidate read-only diagnosis

The existing paired `POST /api/djconnect/v1/command` additionally accepts
`command:"discovery_playlist_identity"`, `play:false`, and a value containing
`artist_uri` and `playlist_uri`. These are explicit read candidates, not play
capabilities. Core validates both URI shapes, retrieves the exact provider artist,
then the exact playlist metadata and at most five item credits through the same
HA-owned credential connection. It returns `read_only:true` and
`dispatch_authority:false`. This route never learns a fallback candidate for a
cached discovery artist, creates an effect receipt, writes the queue, records DNA
feedback or rewrites global health/DJ state. Existing normal token refresh custody
is unchanged. Pairing/Profile/account/source fences still apply across awaits.
A public Spotify page may establish the input candidate; it does not establish
this app's Web API access or authorize replay of an old discovery card.

This separates a successful search with no qualifying official result from a
real direct metadata/items HTTP403 or404. Neither search absence nor an identity
qualification failure means the playlist does not exist. Runtime resolution does
not scrape public pages, hardcode artist/playlist IDs, use this diagnostic route
as an automatic fallback or substitute a fan playlist.

## Typed response and client handoff

The discovery/play body remains unchanged. New failures carry no raw provider or
English-only `message`; Apple owns localized rendering in all five UI languages
from the stable `error` code. All effect failures include `played:false`,
`music_dna_feedback_recorded:false`, `error_scope:"command"` and
`retry_automatically:false`. `action_outcome.state` distinguishes no dispatch,
uncertain attempted transport and acknowledged dispatch before later withdrawal.
An acknowledged effect is not undone or silently repeated after a readback error.

| Machine code | Meaning / required client behavior |
| --- | --- |
| `music_discovery_this_is_not_found` | Legacy official-resolution diagnostic only; artist Play Now no longer depends on this result. |
| `music_discovery_playlist_access_denied` | Actual provider403 on direct playlist metadata/items. |
| `music_discovery_playlist_not_found` | Actual provider404; do not fabricate a replacement. |
| `music_discovery_playlist_identity_unqualified` | Metadata/ownership/title/credited-artist evidence did not qualify. |
| `music_discovery_this_is_ambiguous` | Multiple/too many candidates; do not choose one locally. |
| `music_discovery_output_required` | No qualified active unrestricted output; no automatic transfer or synthetic continuation. |
| `music_discovery_context_changed` | Original pairing/Profile/source/consent/item/lease changed; refresh through the normal flow. |
| `music_discovery_already_attempted` | Same original cached card has already reserved a write; no automatic replay. |
| `music_discovery_write_outcome_unknown` | HTTP client attempted to repeat a write after connection loss; second transport blocked, no replay. |
| `music_discovery_start_failed` | No qualified successful acknowledgement; no positive signal. |
| `music_discovery_backend_unsupported` | Selected backend cannot perform this Spotify Discovery operation; no client/provider substitution. |
| `music_discovery_provider_request_failed` | Other scoped provider failure; retain absence of success, no global outage inference. |
| `music_discovery_artist_invalid` / `music_discovery_playlist_invalid` / `music_discovery_item_not_playable` | Invalid or inconsistent provider identity; no URI repair in the client. |
| `music_discovery_effect_not_authorized` | Private original-task effect scope is absent or does not match the exact selected URI/output. |

Successful playback returns `action_outcome.state:"dispatched"`, separate
`readback_confirmed`, `queue_replacement_verified:false` and no automatic replay.
The adapter sends one context PUT, not enqueue/transfer/skip/clear operations.
Actual native queue refresh and audible acceptance must still verify the user's
requested queue outcome; a successful context acknowledgement alone is not
proof that manually queued Spotify entries were cleared.

Source includes a task-local one-write scope, original cached feed/item/lease and
owner fence, post-token-wait transport check, same-card serialization/deduplication
and guarded positive feedback into the already resolved original record. A child
task or JSON payload cannot mint or retain this capability. A fresh explicit feed
can offer a new choice; an uncertain old write is never automatically retried.


The private write also uses the public aiohttp per-request middleware boundary to
allow only one actual transport attempt. aiohttp may otherwise retry idempotent
PUTs after a pooled connection disconnect; a method-level one-call counter is
insufficient. This middleware rejects a second attempt without changing shared
session flags and disables redirects for the effect. An unsupported middleware
runtime fails closed as backend_unsupported; qualification pins the actual HA
runtime. See https://docs.aiohttp.org/en/stable/client_advanced.html#middleware-chaining.
