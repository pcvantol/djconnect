# Ask DJ playback request truth v1

Status: current corrective contract; implementation and qualification in progress.
This refines the existing single Ask DJ, command, output-choice and expression
owners. It selects no new assignment, provider, writer, Planner or consumer.

An explicit request such as “Ik wil Nirvana horen” is a playback request just as
“Speel Nirvana” is. Questions about an artist, quotations, negations, conditional
requests and catalogue suggestions are not execution grants. The same distinction
applies to supported English, German, French and Spanish listening requests.
No non-executing request may receive a present-tense playback confirmation.

## One request and an exact target

The original accepted request owns its query, intended media kind and provider
resolution. Correct STT only where necessary through the existing bounded,
qualified Conversation transport; do not reinterpret an already parseable
music request with unrestricted Assist tools. A text correction cannot silently
replace the requested artist or change the requested effect.

Resolve using existing authorised backend data. The actual selected provider
identity, context/track URIs and labels determine the result. Artist search is
not authority to substitute an unrelated artist; top-track requests admit only
tracks credited to that exact artist identity. No remembered playback, prior
query result or generic resume can substitute for this request's result.

An output choice retains the original request and its exact resolved target,
expiry and source/account/Profile authority. Frozen media is supplied only by the
producer resolution, never from a caller's internal-looking payload. Track,
album, playlist and artist requests all use this same boundary. An output
continuation is single-use, including after an uncertain dispatch; another
client message ID cannot replay the effect. Selecting an output does not pick a
new song. Revalidate the selected speaker and target before the existing effect
boundary; no new search or model reinterpretation after a frozen resolution.
If the original target is no longer usable, report that and request a new choice.
Do not resume the old Spotify queue as a fallback for a failed request.

## Truthful result and personal DJ response

Distinguish a required choice, an actual failed request, an accepted provider
start request and observed playback. An API success/204 proves dispatch only.
The optional response `playback_outcome` (schema_version1) records its state,
exact requested identity, selected target and separate observed-match boolean.
A stale different current track is never evidence that this request started.
A provider failure or absent semantic effect is never `started`.

The answer names the actual selected track, album, artist collection or playlist
and its type, rather than echoing only the user's artist name. For an artist
collection, name the first actual submitted track and collection scope; do not
promise its order when shuffle/readback does not support that claim. A matching
observed track may be named as playing. If shuffle selects another admitted
track, name and illustrate that actual readback; never label the first submitted
item as playing merely because another item from the collection is observed. Otherwise clearly state the pending or
failed state, including when different music is still observed.

Use the existing shared Persona/Mood expression owner. Only Core-owned semantic
instructions and opaque required placeholders go to enrichment without an
additional source-processing grant; catalog labels are bound locally afterwards.
Never invent a song-selection rationale, biography, sonic property or historical
fact. The normal two-call budget remains unchanged for reads, lookup and pre-effect
interpretation. An actually accepted, exact-target playback dispatch admits at
most one additional call: total three per turn, allowing one interpretation and
two calls through the existing realization/assessment owner. This allowance
exists only after Core dispatch evidence and an existing authorised effect; no
client flag, failed dispatch or model claim admits it. It is never a new
provider/model route or an extra retry. Preserve selected language, source links,
TTS/output policy and private archival rules. Clear failure guidance needs no
joke. A safe fallback may be brief but must retain target and outcome truth.

Art accompanies the exact selected/observed media using the existing private
proxy and attribution/expiry boundary. Missing art has an explicit safe state;
never borrow the old/current cover when it is a different recording. An image,
model sentence or completed speaker transfer is not playback proof.

## Acceptance

Reproduce text and voice variants of both reported requests with unrelated
previous Guns N’ Roses playback. Exercise direct output and missing-output→choice,
original-request replay, duplicate tap, no-active-device, provider failure,
timeout/uncertain dispatch, stale readback, wrong-artist result, STT entity rewrite,
track/album/playlist requests, all five languages and Persona/Mood expression.
Assert actual backend effects and exact identities, not only response text.
Negation and information-only requests produce zero playback effects; music-only
presence does not suppress an explicitly requested command. Keep historical,
native, installed and audible acceptance separate. Golden named routes must
execute these scenarios and reject a fabricated successful acknowledgement.

## Output-local failures

Every explicit manual/dialogue output request uses a fresh provider inventory;
missing, cached, restricted or ambiguous targets never fall back to an active or
first device. Clients send the stable ID from the admitted inventory; a missing
ID cannot be reinterpreted as another output's display name. A 404 is `output_unavailable`; provider
5xx/transport timeouts are `output_transfer_failed` with uncertain outcome. Both
are action-local, preserve existing global backend-health evidence, provide
five-language functional guidance and prohibit automatic retry. Dispatch and
matching target readback remain separate `action_outcome` evidence. A selected
speaker, successful204 or unchanged older track never claims confirmed music.


## Named artist and failure-language correction — 18October2026

The shared Spotify owner uses a quoted artist-field query and at most ten
candidates, independently requiring the requested normalized artist identity.
This applies to artist top-track resolution and named-artist media/URI lookups;
related artists and tribute acts never substitute for an explicit requested name.
Natural-language parsing remains in the existing shared command owner. The
backend's catalogue-query field is not authority to start an unrelated result
from an unparsed sentence. Original selected-artist credits fence the track list.

Common Ask DJ failure text follows its confirmed turn language; raw calls use
valid explicit requestlocale before legacy defaults. These are repairs to
existing identity/localization requirements, not a new wire/action contract.
[Original cause and qualification](../verification/ASK_DJ_NAMED_ARTIST_FAILURE_20261018.md).
