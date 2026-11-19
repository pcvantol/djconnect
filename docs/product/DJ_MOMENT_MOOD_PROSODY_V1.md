# DJMoment Mood prosody v1

Status: local implementation and qualification in progress; no installed or audible acceptance.

The confirmed Mood at publication controls the spoken delivery of every non-Silence
DJMoment. Chill is relaxed and unhurried, Groove warm and rhythmically conversational,
Energy lively and assertive, Party celebratory with animated emphasis. These are vocal
directions, not new words, volume changes, playback-speed effects or different voices.
Persona and the selected provider voice remain independent. Published text is spoken
literally, without adding names, laughter, sound effects or new facts.

The immutable accepted Moment supplies Mood, including after history reload. Unknown
historical Mood remains unknown. Changing Session Mood affects subsequent Moments;
replaying an old bubble preserves its accepted Mood. Silence never invokes TTS.

Use only the selected HA Assist TTS entity. A provider adapter must qualify its actual
per-request expression interface. The verified HA 2026.10 OpenAI TTS implementation
passes its per-request `prompt` option to speech instructions; DJConnect can append
bounded Core vocal instructions while preserving the configured provider prompt. It
does not call OpenAI directly or modify the HA subentry. Providers without a qualified
interface continue literal TTS and report unavailable Mood prosody. Do not infer
expressivity from voice names, gender or provider speed controls.

Descriptors expose requested Mood and effective expression capability. Their expression
revision participates in the private audio cache key. Provider reconfiguration still
invalidates in-flight and cached delivery through the existing authority fence.
Native local synthesis needs its own consumer qualification; Core capability does not
prove Apple playback or audible acceptance. No automatic provider substitution.

Qualification requires same text, voice and language across all four Moods, literal-text
and cache/failure tests, real configured-provider audio, and listening comparison for
recognizably calmer Chill versus more energetic Party. Metadata, distinct bytes and
shorter duration alone are insufficient. Preserve five-language delivery, all spoken
Moment families, settings races, history reload and Silence regressions.

## Golden release binding

The existing `askdj-contextual-release-gate.yml` invokes the existing release
matrix runner. Its `mood_prosody` profile is mandatory: four Moods × five languages
through the real HA provider, plus one paired bubble preparation and repeated
private audio read (21 bounded paid syntheses). The test model is the already
qualified `gpt-4o-mini-tts`; this is a speech model, independent of the dialogue
model. No provider calls occur in the deterministic owning test fixtures.

The executable `moment_mood_prosody` family binds literal text/voice/settings,
accepted-Mood identity, cache reuse, provider changes and every spoken type
boundary including Silence exclusion. Same-Mood speech remains on the shared
TTS route. Full semantic generation of all seven Moment families is a separate
existing proactive Golden responsibility, not established by changing a type in
a boundary fixture.

The release validator requires current source hashes before/after, actual paired
start/prepare/repeat/end receipts, identical valid private audio reads, complete
unique Mood/language cells, common text/voice within each language, and matching
bounded audio files. Missing credentials, cells, files, failed synthesis or stale
source proof fail closed. A technical PASS explicitly leaves audible, native and
installed acceptance open; bytes/hashes are integrity evidence, not a listening
verdict. The pinned paired harness asserts no-store on actual audio responses.
