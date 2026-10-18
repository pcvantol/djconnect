# Configured Preview: source and installed development readback

This reconciles the already delivered Speech/Settings producer. It does not
complete the Preview function, select another assignment or dispatch a consumer
writer. A protected merge is source incorporation; each functional requirement
still needs its applicable installed, native, provider and listening evidence.

## Exact producer and installed scope

[Source PR #1197](https://github.com/pcvantol/djconnect/pull/1197), exact candidate
`a5840acdffa99a8c1180d90b714c3c0fb9d983c2`, merged as
`c98cbf3e3114afb8b8212e18224a337b12af3e27`. Complete candidate/merge trees are
equal. Separate [Finalization #1204](https://github.com/pcvantol/djconnect/pull/1204)
merged as `e71daff1e36c7e0284ffa1f42b1a1ada47b50aa1`.

That exact main is installed on HA-dev as an authorized **development build**:
202 integration files, zero hash mismatches, actual HA configuration check,
database integrity and public capability readback passed. Installed
`voice_preview.py` is also byte-identical to subsequent protected main
`3f88898a4f74e84c76abe68476f0a598821d0583`; its passive v2 delta is separate and
is not installed by this Preview readback. HA-prod was not changed by these
development updates. No official release or end-user audible result follows.

The [public-only installed discovery fixture](../../examples/client_contracts/voice_preview_v1/installed-discovery-20261018.json)
records the artifact/module hashes and the actual descriptor:

- `session_speech.voice_preview.available:true`, `version:1`;
- existing `POST /api/djconnect/v1/transport/operation`, operation `speech/preview`;
- confirmed Settings3, processor `ha_configured`, no Session required;
- five language families, original maximum120second lease, private/no-store;
- no caller text, provider, voice, gender or target override, no history entry;
- duplicate intent returns its original receipt without a second synthesis or dispatch.

The old instruction that this producer is merely local and absent from HA-dev
is superseded. Existing consumers may integrate this exact development contract
behind actual versioned discovery and confirmed settings. Missing discovery,
unknown version, unconfirmed/migration-ambiguous settings or a runtime failure
must remain unavailable. This does not assert that any native Preview/Stop UI is
already implemented, installed or audible.

## Current owner fixtures

Eighteen Preview-owner tests passed in the pinned HA image, with network disabled
and zero model calls. They execute the actual paired authority, Settings3,
operation journal, private audio and shared speaker-delivery owners; their HA
object, external TTS and speaker I/O are fixtures. This is **not** a connected
ordinary-HA HTTP test or actual configured-provider synthesis.

The [current thirty-five operation outcomes](../../examples/client_contracts/voice_preview_v1/operation-fixtures-20261018.json)
were exported from those tests on protected main `3f88898a…`.
SHA256: `f0551274a3a6a76302d4657def850bc3958f2dffda611a74db5a51a24a101d15`.
The older fixture remains unchanged as its historical checkpoint. Every UUID,
epoch, Profile, Session, provider and audio reference in the owner fixture is
synthetic and grants no live access.

The request uses the existing version1 operation envelope, a fresh UUIDv7 and
current server operation epoch. Its entire operation payload is
`{"contract_version":1,"language":"nl"}`. Use the confirmed Profile/active
Session output and HA-selected provider/voice/gender. A locale mismatch never
silently changes the HA pipeline. Read the original operation receipt after
lost delivery; never turn a reconnect into a fresh playback intent.

| Fixture outcome | Meaning for the existing client |
| --- | --- |
|200 available, local ready | Authorized private audio exists; local playback is still required. |
|200 speaker queued | HA accepted a speaker dispatch; audibility is unproven. |
|400 `invalid_request` | Reject unsupported fields, versions or malformed intent. |
|409 `settings_migration_choice_required` / `announcement_text_only` | Review confirmed settings; no fallback synthesis or target. |
|409 `no_matching_locale` / `tts_provider_unavailable` / `speech_configuration_changed` | Show functional HA TTS configuration guidance and retain normal Session text. |
|409 `voice_preview_withdrawn` / `speech_preparation_failed` / `speech_retry_backoff` | Stop stale playback, preserve the original operation outcome and allow a deliberate later action only when admitted. |
|503 `speaker_delivery_unknown` | Delivery may have happened; no false success or automatic redispatch. |

Five neutral texts, all configured outputs, text-only zero effects, no-Session
and active-Session isolation, duplicate/cancellation, provider/settings/target
races, partial/unknown delivery, byte fencing, original expiry and backoff are
covered by those owning tests. Neutral Preview intentionally does not add
Persona/Mood prosody; narrated DJMoments have their own quality/audio gates.

## Functional acceptance remains open

The next proofs must connect the real configured HA provider and effective
voice/gender/output to one deliberate Preview, the actual native Preview/Stop
controls, invalidation during runtime and physical listening on each selected
target. Fixture bytes, a discovery descriptor, a source merge, a queued speaker
call or an installed application alone cannot close that requirement.

The existing twelve Core findings and nineteen actual-quality Golden gates stay
OPEN. Single/bulk archive erasure, original history404, richer Persona/Mood
narration, quiet transport and joint client acceptance are independent; this
readback does not complete them.
