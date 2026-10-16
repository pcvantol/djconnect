# Generic configured Home Assistant TTS for Session speech

## Current successor scope — shared five-parameter settings

[Owner decision6214905647](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6214905647) and the [canonical consolidation contract](PROFILE_SESSION_SETTINGS_CONSOLIDATION_V1.md) supersede device-local voice/gender and Session-only default semantics for the selected contract2 successor. Persona, concrete voice, qualified gender, Mood and Presence roam per Profile/Session; each explicit accepted field choice automatically becomes its Profile default and applies now when a Session is active. Automatic Mood/provider fallback/reconnect does not change defaults. No global HA pipeline change or new source/provider rights.

The delivered contract1 behavior and its source/PR evidence below remain historical/frozen; do not silently reinterpret version1 or infer installed/native adoption. The bounded old-consumer migration and removal gate is explicit in the successor. Core implementation is local/unpublished; Apple/other consumer changes remain owning-lane work, no WIP takeover or automatic dispatch.

## Delivered contract1 and historical qualification

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
HA voice interface supplies ID/name, not a qualified gender: male/female requires the explicit metadata qualification in
[Provider voice/gender](PROVIDER_VOICE_GENDER_V1.md). Voice names
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

New accepted assistant history stores the bounded server-established
`speech_processing_basis` alongside the existing message. The retained-entry
projection carries that original provenance; it does not infer cloud permission
from role, text, attribution or archive membership. Legacy absence retains only
the prior qualified local-read possibility, never retroactive cloud permission.
No body backfill, Store-version rewrite or new event/history engine is required.

## Active-session voice menu (owner additions, 2026-10-16)

Apple exposes a localized Voice menu in the active DJ-session. Concrete voice
selection and optional provider-qualified gender are runtime settings scoped to
HA installation + authorized user/Profile + session_id + device/install-ID.
The client owns this short local preference; Core validates every prepare against
the actual current configured provider and language. Do not write shared HA
pipeline options, Profile defaults, Persona or another device's preference.
Discard session-scoped choice at end; no migration from a global app preference.

The private voice-options projection adds bounded `voices` (max64 unique opaque
IDs with safe names and qualified gender or null), `voice_selection` availability
and `preference_context` scope metadata. Prepare optionally accepts `voice_id`
(max128 characters) only for `ha_configured`, drawn from that exact current
inventory. Unknown/removed IDs fail unavailable, without default fallback.
Old clients omitting it retain the configured/default voice. Revalidate after
await and at byte read; selected voice and configuration fence participate in
cache identity. A change applies to next/pending/explicit replay; it never
rewrites accepted text or replays the original Ask DJ/playback operation.

Gender values require explicit provider metadata; the generic HA Voice ID/name
alone is insufficient. [Provider voice/gender](PROVIDER_VOICE_GENDER_V1.md)
qualifies the installed Cloud language/Gender mapping against its current
inventory, plus explicit gender metadata on a provider Voice when present.
Unmapped voices retain null. No catalogue copy, name/pitch inference or direct
provider lookup. Gender resolves to concrete voice IDs; Cloud's deprecated gender
request parameter is omitted. Changes invalidate options revision and old audio.

Menu opening, preference editing and refresh synthesize nothing. Fetch current
options on open/foreground/reconnect and before explicit preparation. Preserve
text/controls, display current effective voice, and show HA TTS recovery help
when provider/settings fail. Native five-language menu, preference isolation and
installed/audible acceptance remain Apple-owned, separate from Core proof.

## Qualification and delivery

### Runtime provider feedback (owner addition, 2026-10-16)

The existing private prepare, voice-options and audio routes expose optional
`provider_status` and `notification` version1, with stable untranslated codes,
severity, retryability, an allowlisted action and safe localized title/message
in en/nl/de/fr/es. Configuration missing, configured provider unavailable,
unsupported voice/language, synthesis failure/timeout and configuration changed
are distinct functional outcomes. Never forward raw provider exceptions,
credentials, URLs, prompts, accepted text or account details as an error.

No provider work in status reads. Configuration readiness is not proof of
successful synthesis: distinguish `not_tested`, `succeeded` and `failed`.
An actual preparation failure/success has short, bounded, private in-memory
status scoped to exact owner, entry and provider configuration; do not persist
it to history/diagnostics or share across Profiles. A changed configuration
does not inherit an old failure or old success. Failure expiry returns unknown,
not a fabricated recovery. Reads do not extend the original observation.

Recheck on every prepare, private byte read, voice-options read and after every
synthesis await. If the authorized reference remains valid but the provider
changes, return functional unavailable/409 feedback and discard old resources;
permission/source withdrawal remains opaque401/403/404 without provider detail.
No polling service, new event bus, push notification or automatic synthesis retry.

Apple should display the returned functional notice inline with Listen/voice
settings, preserve the accepted answer, and offer explicit Retry or Check Assist
pipeline as appropriate. Retry uses the same reference and existing backoff;
it never repeats the original question/playback action. Re-read on foreground,
reconnect, opening voice settings and before preparation. Handle preparation
errors and audio409 during use; do not rely on the pairing-time capability.
Provider metadata/readiness alone must not show a successful speech health check.
Native presentation/localization/adoption remains Apple-owned and unproven until
its own implementation/tests; this Core increment contains no Swift writes.

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
