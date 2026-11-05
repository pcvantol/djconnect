# Music announcement Moments v1

Owner scope: Core #1101 comments6654758444,6654941875,6655032217 and Apple #87
counterparts. Source candidate; no installed/native/audible acceptance.

## Existing producer and original occurrence

`music_announcement` is a distinct typed DJMoment. Reuse the existing Spotify
observer, Runtime, Planner, semantic SQLite acceptance, Flow/Broadcast, configured
HA narration/reviewer and speech/media owners. No second listener, provider,
audio engine or history store. Existing observation interval3seconds; queue reads
retain their original30-second cache. No announcement pauses, seeks, skips, ducks
or changes music output.

One authorized actual playing sample near start creates an occurrence ID.
Pause/resume, ordinary seek, reconnect, polls and rendering do not create another.
Same-recording natural repetition needs a recent observed playing tail and elapsed
time crossing the known end; ambiguous/missing samples do not mint guessed starts.
Original12-second automatic deadline subtracts already elapsed track time;
stale/late results never catch up.

One bounded realization/review uses confirmed Persona/Mood/locale and the last
eight actually published value-free frames. The model receives track/artist roles
only; exact catalog values are substituted once locally after acceptance. No
private taste, history, lyrics, sonic analysis, biography or DJ selection claim.
Target6–10seconds; character estimates do not prove audible duration. Failure uses
exact names only with explicit `realization:degraded`, never fake generated variety.

Near the current track's end, one next real queue hint can be privately prepared
through the same realizer. Internal queue window at most three URIs, no future
occurrence ID. Unchanged reads do not regenerate. No publication/count/archive,
push or audio before an actual observed start. Original queue deadline,
source/command/context/reorder checks fence reuse; voice-only changes do not change
text context. Queue position is not a future occurrence or Forecast promise.

## Presence, retention and media

Baseline text is independent of extra-story quotas. Music-only keeps baseline
text and suppresses extra stories. A separate successful-intro counter/readable
interval avoids charging these introductions against the existing story ledger.

| Type | en | nl | de | fr | es |
| --- | --- | --- | --- | --- | --- |
| music_announcement | Music announcement | Muziek aankondiging | Musikankündigung | Annonce musicale | Anuncio musical |

Live `music_announcement` schema1 carries original occurrence, recording,
title/artist, album edition and generated/degraded state. Full original text,
Session/Moment identity/time and Persona/Mood/locale use existing
`owner_metadata_narration_v1`, archive guard and normal retention/privacy/deletion.
History-disabled live publication cannot claim durable retention. Old current-only
`track` receipts are not relabelled.

Original `session_media_reference` retains recording/album edition and private
source binding, not CDN URL or pixel permission. Existing authenticated live and
retained media preparation rechecks source/edition. Missing art uses a placeholder;
never borrow the current recording's cover. Text is independent of image retrieval.

## Independent speech and client handoff

Automatic speech needs the original new publication/start window, selected output
and device autoplay/permission settings. No settings mutation, backlog or extra
processor/local/cloud rights. Only this typed accepted family permits speech
prepare3 `intent:manual`, `target:local` under `announcement_output:text_only`.
Other families keep existing policy. Live/retained descriptors add
`moment_type:music_announcement`; replay uses the actual retained original after
the automatic deadline/Session end. History clients use original `entry_id`.
No generation, publication, count or music effect on replay. Additive
`session_speech.music_announcement` capability names this narrow exception;
it grants no caller text/URI/provider override.

Apple renders exact type, localized category, original text/cover placeholder and
existing Luister control. Core source does not install Apple binaries or grant
new APNs/Watch haptic permission.

## Shared Play Now dependency and acceptance

Owner comments6656089289,6656188640,6656257988 separately request shared Play Now
for introductions, playback-observed items and Ask DJ: track continuity best effort,
collection replacement, honest localized copy. Last comment supersedes the former
absolute preservation requirement. Never advertise the old guarantee flag as new
best-effort support. This separate effect-owner change requires actual provider
qualification; typed text/media/speech does not itself qualify playback.

Fixtures cover twenty starts, duplicate attempts, separate quotas, recent frames,
private prefetch, reorder/source withdrawal, degradation, original braces in titles,
text-only/manual separation and original text/edition after SQLite reopen/Session
end. Actual isolated HA HTTP/SQLite and current-source regression receipts remain
necessary. Real model variety, provider queue behavior, audible timing, installed
native rendering and APNs remain separate gates. Normal protected Source, exact
owner authorization and separate Finalization apply.

## Source validation readback

Current producer receipt:
`examples/client_contracts/music_announcement_v1/actual-ha-wire.json`, made by
`scripts/verification/verify_music_announcement_http.py` in offline real HA.
Its twenty fixture starts pass ordinary paired Session creation, original
source/archive admission, real realization/review orchestration, HTTP projection,
SQLite history and explicit local replay at text-only after Session end. Model
response wires are declared fixtures; real model/Spotify/audio effects are zero.

25 isolated actual-HA groups qualify the unchanged final product source. All307
product files are pinned; historical receipts are preserved. 4573 repository
tests pass with11 existing skips;172 verification-framework tests, Ruff, DAG
validation and Bandit medium/high checks pass. This is source validation only;
shared Play Now, real generated variety/audible timing, independent review,
protected delivery, native adoption and installed acceptance remain separate.
