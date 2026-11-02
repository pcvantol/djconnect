# Session startup choices and Music DNA surprise mix v2

The owner-selected startup flow has exactly two separate choices after Session
start, until that Session has actually played music or a deliberate play attempt
has reached the normal send boundary. It is not a fourth Ask DJ suggestion.

- **Verras me**: offer three distinct genres from the original owner's Music DNA;
  selecting one starts its backed DJConnect mix of actual Spotify tracks.
- **Selecteer playlist**: the client opens its playlists screen. This is navigation
  only; opening it neither chooses a playlist nor starts playback.

Core provides the choices and authenticated conversation implementation. Apple
owns screen/navigation adoption. Source, protected delivery, installation, real
Spotify access and native/product acceptance are separate claims.

## Discover without effects

Feature-detect `session_start_actions` contract1 and
`session_first_play_surprise_mix` contract2. Existing authenticated Session start
and active responses expose `session_start_actions` plus the compatibility field
`first_play_action` (now schema2). The envelope has schema_version1, available,
automatic_playback:false and exactly two ordered items:

1. `session_first_play_surprise_mix`, kind `conversation_request`, schema2,
   genre_basis `music_dna`, localized label/prompt, available,
   mix_availability `not_queried`, transport `existing_session_conversation`,
   selection_effect `genre_starts_exact_mix` and automatic_playback:false.
2. `session_start_playlists`, kind `navigation`, schema1, destination `playlists`,
   localized label, available and automatic_playback:false.

All five UI language families are explicit. Genre names are original normalized
Music DNA data, not generated acoustic descriptions or invented translations.
Rendering this envelope does not create a Session, load memory, update metadata,
query Spotify, open a screen, request a model or play music. The first item's
available qualifies making the request, not current speaker/provider readiness.
Missing/disabled/unloaded/private-inaccessible DNA or fewer than three usable
owned genres disables the surprise action without disabling playlist navigation.
No fixed Mood fallback, other Profile, device memory, payload music_dna_key,
operator attestation or model-supplied genre list substitutes for original DNA.

## Original read authority

The loaded actual MusicDNAManager reads only `profile:<authenticated owner>`.
Canonical loaded Profile privacy must allow personal reads. Choose the first
three distinct bounded names from favorite_genres followed by listening_profile
inferred_genres, preserving stored preference order. Reject control characters,
invalid query syntax, duplicates and incomplete data. No generic profile getter,
load, setdefault, import or warm-up occurs on this read.

The original manager/data/memories/row/favorite/listening/inferred container
identities, generation, save-failure safety epoch and scalar genre tuple are
captured. Normal listening-profile publication does not always change generation;
container identity also fences unobserved A→B→A. Failed persistence makes this
reader unavailable, and recovery never revives an older captured snapshot.
Unrelated successful metadata saves do not renew the original genre admission.
Profile replacement/privacy/manager/clear/disable/source/history/settings changes
are checked synchronously after awaits and immediately before effect dispatch.
A failed original admission stays withdrawn. No new request or stage renews its
original60-second wall-and-monotonic deadline.

## Deliberate request and selection

The client sends the supplied localized prompt once through the existing owner-
authenticated `ask_dj/message`, with original client_message_id and explicit
conversation_context.session_id. Do not execute catalogue IDs. Arbitrary free
Send and ordinary Mood-feedback suggestions retain their separate semantics.

Core checks fresh provider playback/devices. Playing/unknown state closes the
request; initial paused/stopped/idle can offer startup choices. A missing active
speaker first returns ordinary opaque output choices. Their deliberate selection
transfers with play:false, confirms the actual output and continues the same
original admission. No output guess, lease reset or automatic playback occurs.

With a confirmed output, three bounded parallel Spotify track searches use the
three quoted original DNA genre names (at most8 records each). Only actual,
canonical, unique, non-local, explicitly market-playable, unrestricted track URIs
qualify. Each of the three distinct ordered mixes needs at least two tracks.
Unavailable results produce an honest unavailable response, never fake buttons.
This is a DJConnect-assembled Spotify-track mix, not an assertion of access to
Spotify proprietary Mixes/Recommendations or measured acoustic suitability.

The response's `first_play` schema2 names genre_basis `music_dna` and the state
output/genres/unavailable/requested/uncertain. Existing result_set_id/action_id
freeze the actual three track_mix actions and ordered URI lists. A deliberate
select/play of a genre is the single playback grant; no extra Play Now or caller-
provided URI list is accepted. Informational/negated/activate-on-genre requests
remain nonexecuting. Speaker selection is never a play grant.

Choosing a new mix deliberately starts that context. Existing queued or paused
media can therefore be replaced on this explicit choice. The route does not
claim preservation of an existing Spotify queue or cross-endpoint atomicity;
there is no misleading known-empty-queue prerequisite. Before the genre click,
all existing media/queue state remains unchanged.

The existing real durable reservation and last synchronous source/owner fence
precede I/O. Original pending actor ownership, cancellation and original deadlines
remain enforced. Both a first-play dispatch and an ordinary actual play dispatch
retire the original same-Session startup latch before network/service I/O, even
when its acknowledgement is unknown. A retained callback never rebinds to a
replacement Session. Actual playing closes before history persistence awaits;
later pause/idle/history-clear never reopens it. No automatic retry on unknown ACK.

## Compatibility and delivery

V1 fixed-Mood semantics and their original schema/RAW remain historical under
session_first_play_v1. V2 consumers must require the exact new version; no old
fixture or ordinary installation becomes current DNA2/provider/native proof.
Current original DTOs live under examples/client_contracts/session_first_play_v2.

The owner explicitly requested the coming changes in one PR. This bounded batch
therefore includes implementation, contracts, UI strings, verification and its
closing documentation together; it does not create a separate per-fix or second
documentary PR. Normal fresh native verification, independent whole/exact review,
protected exact-head delivery and original post-merge source qualification still
apply. Post-merge receipt/current-status reconciliation records actual protected
SHAs; no future pin or nonexistent separate Final qualification is claimed.
All existing24 requests/nine gates, numeric Track Insight, Help, Pi, API and
provider/native/install boundaries retain their own evidence scopes.
