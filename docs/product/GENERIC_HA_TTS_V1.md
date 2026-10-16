# Generic configured Home Assistant TTS for Session speech

Assignment: `DJC-CORE-GENERIC-HA-TTS-V1-20261016`. Owner explicitly rejects
Piper-only Session speech. This is a corrective increment after completed
Speech PR1177/1186, on main `8757ecd38a5fe31254a36aba5e0cbe5852edfa7e`;
it does not reopen those deliveries or start the queued passive-surface slice.

## Contract before implementation

Use HA's supported `tts.get_engine_instance` and `async_get_tts_audio` contract
for the exact selected Assist pipeline. No provider class allowlist for ordinary
qualified speech: OpenAI, Cloud, Piper and other installed HA TTS providers use
the same adapter. No direct external API, credential copying to clients, added
provider installation, pipeline/default change, provider discovery or fallback.

Use the pipeline's exact supported language and configured voice. If no voice
is configured, use the provider's advertised default; a provider without a voice
inventory may use its own default, explicitly reported as provider-selected.
An explicit unavailable voice or unsupported locale returns unavailable. The
HA voice interface supplies ID/name, not a qualified gender: male/female stays
unavailable unless a future explicit metadata contract qualifies it. Voice names
and Persona are never gender evidence. Read-only voice options do no synthesis.

The loaded entity, provider/configuration revision, exact language and voice
participate in the private resource identity and post-await authority fence.
Changing provider options during synthesis invalidates that result and old
bytes; no stale cached voice may be relabeled. Do not expose config, prompts,
API keys, URLs or credentials in public provider metadata.

Accept bounded WAV or MP3 through the existing private RAM audio owner; preserve
4000-character/2-MiB/20-second/original-expiry limits. Validate actual returned
audio bytes, do not turn provider error pages or MIME-only claims into audio.
No transcoding service, speaker call, playback command or new synthesis retry.
Failure/cancellation/revocation keeps the accepted text usable and publishes no
late resource. Existing deduplication, expiry, Profile ABA and Session-end fences
apply unchanged to every provider.

## Source and processing rights

Provider compatibility and source permission are separate checks. Exact accepted
qualified dialogue (`qualified_dialogue_v1`), normalized CC0 fields and authored
Runtime direction can be read by the owner's explicitly configured HA provider,
including cloud TTS. This owner request authorizes use of that configured route;
it does not grant a new archive, model rewrite, private shared surface or raw
provider payload. Only the exact accepted speech segments are sent.

`spotify_owner_local_read_v1` remains a local-processing grant. It may use the
already qualified actual local installed Wyoming Piper route, but must be denied
before synthesis on a cloud or unclassified configured provider. Do not infer
locality from the `tts` domain, private URL or a provider display name. Unknown
source bases fail closed. This source restriction is not a general Piper-only
provider gate. Original retention, withdrawal, attribution and owner permission
remain authoritative. No caller-supplied source/processor grant is accepted.

## Qualification and delivery

Test different provider classes, no-inventory default, exact voice/language,
unavailable provider, WAV/MP3, malformed audio, configuration changes, concurrency,
withdrawal and retry. Use real isolated HA, normal paired Core preparation and
private audio readback; only external synthesis boundaries may be fixtures.
Qualify the actual existing OpenAI provider with a short authored public test
sentence, without playback or private/catalog text. Keep real-provider proof
separate from mocks and from native audible acceptance.

Update the existing Speech contracts and consumer handoff. Exact source and
separate Finalization publication gates remain applicable. Installed dev/prod
qualification follows protected delivery under the standing owner instruction;
no live source hotpatch, Swift change, HA migration or new passive-surface work.
