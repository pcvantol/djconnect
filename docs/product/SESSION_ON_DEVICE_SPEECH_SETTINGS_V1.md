# Settings-aware native device speech — 18 October 2026

Status: explicit owner-approved correction within the existing Core Speech and
Settings assignment. Design precedes implementation. Existing sole Core writer;
no native code, new synthesis service or deployment authority is introduced.
Historical prepare1/2 receipts stay immutable. This addendum supersedes the
ha_configured-only restriction of the earlier shared-settings checkpoint.

## Same accepted contribution, independent device presentation

The existing `speech/prepare` owner route accepts `processor:local_on_device`
under prepare2/3 as a source/settings-qualified native presentation attempt.
Activated settings still require target-aware prepare3; prepare1/2 must not
bypass the existing migration review or426 upgrade boundary. Request fields
are unchanged: prepare3 identity, original reference, processor, intent, target.
There is no caller text, voice, gender, rate, pitch, URL or provider override.

The accepted original text/segments, reference, attribution, text/presentation
and Persona revisions, Mood and original deadlines remain unchanged. Source
processor entitlement uses the existing closed literal-speech provenance set;
unknown provenance or a missing advertised processor fails closed without
executable segments. Owner/pairing/Profile, current effective Settings/Session,
source expiry/withdrawal and final transport-delivery fences remain mandatory.
No visible bubble fallback, history promotion or new publication is created.

For local preparation Core neither reads HA voice availability nor synthesizes
HA audio. An unavailable saved HA voice remains saved and does not block native
speech. The response is `audio_state:renderer_pending`, selected
`processor:local_on_device`, `effective_voice:null`, existing Settings revision
and the exact admitted segments. No audio reference/URL, claimed effective OS
voice or configured-HA voice preference is issued. The renderer qualifies the
real OS voice/locale and its own device voice/gender/rate/pitch; those values
stay local and never write Profile defaults or the HA Assist pipeline.

## Output and lifecycle

| Confirmed output | Automatic local prepare | Explicit local replay |
| --- | --- | --- |
| client_device | admitted source only | admitted source only |
| both | admitted source only | admitted source only |
| ha_speaker | denied | admitted source only |
| text_only | denied, zero synthesis/output | denied, zero synthesis/output |

Automatic playback also requires the original new-publication eligibility and
the device's independent autoplay preference (default OFF). Preparation itself
is not a new autoplay event: its existing `autoplay_eligible:false` remains.
Read/open/reconnect or replay of a retained entry does not create automatic
eligibility. A successful grant is not ready native audio or audible success.

A local processor requests only `target:local`; speaker/both-target requests
retain `use_speech_play_operation`. In `both`, Core's existing automatic speaker
leg already targets ha_speaker separately. Explicit HA-speaker replay continues
through the original journal operation. The native coordinator selects exactly
one local processor; it must not also consume an HA client-audio asset for the
same contribution. This correction never invokes a speaker from local prepare.

Stop/discard native pending/buffered speech on expiry, source withdrawal,
owner/Session/Settings revision or binding change, text_only, and renderer
lifecycle cancellation. A subsequent deliberate replay re-prepares its original
reference against current Settings. Core's existing delivery admission guards
also prevent stale granted text from crossing a delayed HTTP/WS response.
Unknown revisions or admission are not permission to speak.

## Preview and qualification boundaries

Device-local static neutral Preview remains the Apple-owned bounded preview,
not a fake DJ contribution or this prepare endpoint. It must obey confirmed
text_only and normal local renderer cancellation. The separate configured-HA
`speech/preview` design is unchanged and not silently implemented here.

Freeze real request/response and allow/deny fixtures for original turn, live
Moment and retained entry, output/intent/target matrix, unavailable HA provider,
unknown provenance, migration/upgrade, exact segments/revisions, expired and
withdrawn sources and delayed Settings/lifecycle changes. Preserve all historical
fixtures. An exact local source manifest/fixture digest can freeze the handoff;
protected source publication, installed, native and audible proof remain separate.
No consumer may infer deployment or quality completion from a local freeze.

## Local source qualification and frozen consumer fixtures

Implemented in the same Core writer. Eleven new owning tests plus the existing
Speech/Settings owners cover the actual source/Settings/persistence boundaries;
the final focused run passes48 tests. The full combined regression passes2484
with seven existing skips. Static checks and medium/high Bandit pass. Independent
technical/privacy review gives scoped GO for this local admission, explicitly
excluding native renderer qualification, installed, audible or narrative quality.

The frozen consumer examples live in
`examples/client_contracts/session_speech_local_settings_v1/prepare-fixtures.json`.
They include24 actual output/intent/target combinations and original live and
retained references. The source grant was also exercised after Settings activation
and with an unavailable HA TTS engine: new Ask DJ response remains deferred,
then native prepare admits its exact original text without an HA voice lookup.
A Settings change while resolving the source and a delayed delivery after any
changed shared setting reject old text. Expired/withdrawn/unknown sources deny.
The speaker operation rejects a local processor before reading a speaker.

Existing expiry safeguards include the source's monotonic deadline; the final
prepare-delivery guard now also checks the published absolute grant expiry.
No expiry or source/Settings revision is renewed by delivery or a read.
Core emits no local audio asset, OS-voice assertion, new Moment or Profile write.

The source/fixture manifest alongside these examples is a local exact-byte
freeze. Its SHA256 is the consumer contract pin for review/integration preparation,
not a Git release or installed producer claim. The combined broader correction
still awaits protected delivery; no production/device install is authorized by
this handoff. Existing narrative actual-model quality is still OPEN/NO_GO.


### Historical freeze versus current corrective branch

The211-file freeze above remains byte-for-byte historical. It identifies the
source privately installed on HA-dev as candidate3a89473e, not the subsequent
producer/Forecast corrections. Reuse its archive only for that exact contract
review; it is not an exact pin for current checkout bytes. Shared speech wire
semantics are unchanged by those later fixes, but a fresh source pin and
qualification must accompany any later combined delivery. Installed/native/
audible and narrative acceptance remain separate.
