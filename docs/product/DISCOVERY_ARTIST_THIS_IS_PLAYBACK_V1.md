# Discovery artist This Is playback repair v1

Owner request: Ontdek artist Play Now resolves the real corresponding This Is
playlist and starts that context in place of the previous selection. This is a
server-owned resolution from the original cached discovery item/section, never
a client URI, guessed playlist ID, playlist creation or top-tracks substitution.
Existing music_discovery/play request shape and ordinary pairing/Profile identity
remain; Apple refreshes status/queue after one successful request with no replay.

## Confirmed defect and scope

The old handler passes context_uri alone to play_context_at for every non-track.
That backend operation requires offset_uri, so artists/albums/playlists fail
before valid context playback. It also unconditionally returns played:true and
records positive DNA feedback even when playback reports failure. Correct both.
Track playback stays an exact one-track selection. Album/playlist context starts
must not use an offset-only operation. Artist selection is resolved separately.

## Exact artist and playlist resolution

Use the server-cached Spotify artist URI, then retrieve that exact artist's
provider identity/name. Bound playlist search to10 results using the canonical
name. A candidate must be an actual playlist with consistent id/URI, exact
canonical This Is title and Spotify owner identity. Qualify artist binding from
provider playlist items' exact credited artist IDs, not display-name similarity.
Unknown, inaccessible, ambiguous, empty, unrelated or missing items fail closed.
No fan playlist, fabricated URI, artist-context shuffle or URI fallback.
Only supported Spotify API routes, no scraped web pages/cookies or credentials.

Current provider limits matter: Spotify's2024 notice excludes Spotify-owned
editorial playlists for new/development-mode use cases, with an existing extended
mode exception. The2026 guide limits search to10 results and playlist-item access
to owned/collaborative playlists, using items endpoint/fields. Restrictions are
not repaired by token rotation, broader scopes or a fabricated playlist. Failure
to qualify must be explicit and must not dispatch or mutate the old queue.

Primary references checked2026-11-06:
- https://developer.spotify.com/blog/2024-11-27-changes-to-the-web-api
- https://developer.spotify.com/documentation/web-api/tutorials/february-2026-migration-guide
- https://developer.spotify.com/documentation/web-api/reference/start-a-users-playback

## Authority and effect boundary

Capture original paired entry/token/owner/Profile/backend/account/consent/privacy
and exact cached item identity before awaits; validate after resolution and after
last token/other await immediately before dispatch. Profile/source replacement,
clear/disable, pairing rotation or stale item aborts without playback or feedback.
Read-only provider resolution does not authorize a new owner or output transfer.

Use one exact context-start PUT for the qualified playlist, never append/enqueue,
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
URI/artist/playlist binding, fan/wrong/same-name/ambiguous/missing/restricted cases,
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
| `music_discovery_this_is_not_found` | No qualified official result in this connection's bounded search; do not claim nonexistence. |
| `music_discovery_playlist_access_denied` | Actual provider403 on direct playlist metadata/items. |
| `music_discovery_playlist_not_found` | Actual provider404; do not fabricate a replacement. |
| `music_discovery_playlist_identity_unqualified` | Metadata/ownership/title/credited-artist evidence did not qualify. |
| `music_discovery_this_is_ambiguous` | Multiple/too many candidates; do not choose one locally. |
| `music_discovery_output_required` | No qualified active unrestricted output; no automatic transfer or synthetic continuation. |
| `music_discovery_context_changed` | Original pairing/Profile/source/consent/item/lease changed; refresh through the normal flow. |
| `music_discovery_already_attempted` | Same original cached card has already reserved a write; no automatic replay. |
| `music_discovery_start_failed` | No qualified successful acknowledgement; no positive signal. |
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
