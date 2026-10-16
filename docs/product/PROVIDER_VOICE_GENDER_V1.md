# Provider-qualified Session voice and gender

Assignment: `DJC-CORE-PROVIDER-VOICE-GENDER-V1-20261016`.
Direct owner follow-up after completed generic TTS PR1187/1188.
Base: `f04fc578d11252f48324a22cb6f71039bdcc59d5`.
Same Core writer; queued passive projection is not started.

## Contract before implementation

Keep the generic configured HA provider and existing private owner routes.
Concrete `voice_id` and `voice_preference: default|female|male` remain optional
Session/device preferences. Never modify a pipeline, Profile, Persona, Mood,
another device, or accepted text. Menu reads do not synthesize or fetch providers.

Qualified gender comes only from explicit metadata for an advertised current
voice. Never infer from voice names, language, pitch, Persona or provider name.
The generic HA Voice object currently supplies ID/name only. A future explicit
`gender` value on that object may qualify female/male when advertised by the
actual provider. Unknown values remain null.

Nabu Casa Cloud has an explicit language/Gender-to-voice mapping in its installed
HA dependency (`hass_nabucasa.voice.MAP_VOICE`). For the actual HA
`CloudTTSEntity`/`CloudProvider`, intersect that mapping with the current exact
language and bounded advertised voice inventory. This is a metadata adapter,
not a provider allowlist for synthesis. Do not add a copied catalogue, external
lookup or classify unmapped voices. Missing/changed metadata fails closed.
Do not send the deprecated Cloud gender parameter: resolve qualified gender
to the supported concrete voice ID, avoiding the HA deprecated-gender Repair.

With both `voice_id` and non-default gender, the exact voice must carry that
gender. Reject a mismatch; do not silently ignore either preference. Without an
explicit voice ID, retain a qualified configured voice of the requested gender,
otherwise select a deterministic qualified ID in that gender. Advertise these
default gender targets in voice-options so clients can show the effective choice.
No matching metadata gives `voice_gender_unavailable`; a stale/mismatched concrete
selection gives `no_matching_voice`, with existing five-language functional help.

## Dynamic invalidation and consumer contract

Recompute inventory and gender targets on every voice-options/prepare/audio
admission. Include the bounded inventory metadata in provider configuration
identity; changes during synthesis or before byte delivery invalidate old audio.
Voice-options revision is equality-only and changes with provider/language,
availability, inventory or gender metadata. No new monitor, event bus or polling
service. Provider change becomes visible on the next existing authorized read;
no claim of unsolicited immediate push to an unopened Apple menu.

Apple rereads on menu open, foreground/reconnect, selected pipeline/provider
invalidation and before prepare. Show only advertised gender values and voices;
do not reconstruct gender locally. Preserve draft/text/controls and offer explicit
provider-default reset when a stored choice is withdrawn. No silent reset/retry.
Use existing localized option labels and functional notices in all five languages.
Native UI and audible acceptance remain Apple-owned, separate from Core tests.

## Verification and delivery boundaries

Test positive Cloud metadata, generic explicit metadata, no-metadata providers,
all five language families, exact locale/voice intersection, gender/voice conflict,
provider swap, metadata withdrawal during synthesis and byte read, unchanged HA
configuration and zero synthesis on reads. Exercise ordinary pairing and actual
HA Cloud entity inventory in an isolated HA process; external waveform boundary
may be a fixture. No dev/prod provider switch or new Cloud subscription.

Retain source-processing grants, expiry, owner/Profile fences and bounded RAM
audio. Existing source and separate Finalization candidate-specific publication
gates apply. Standing qualified dev/prod installation follows protected delivery;
no source hotpatch, Swift/receiver write or passive-surface implementation.
