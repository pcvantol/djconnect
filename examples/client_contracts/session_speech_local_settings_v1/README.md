# Settings-aware local speech grant: bounded Core handoff

Normative: `docs/product/SESSION_ON_DEVICE_SPEECH_SETTINGS_V1.md`.
The adjacent fixture contains actual owner-route responses from
`tests/test_local_settings_speech.py`: synthetic owner, agent/source boundaries
and no native renderer. It is not installed, real-provider or audible evidence.
No headers/tokens, host identities, live Profiles or real Session content occur.

Use the existing paired prepare3 request shape with `processor:local_on_device`,
original reference, `intent` and `target:local`. No text, voice, gender, rate or
pitch request fields. Activated Settings require3;1/2 cannot bypass migration.
Discovery `prepare_contracts.3.processors` includes local_on_device and its
`local_on_device` metadata declares device-local voice configuration. The
Profile's HA voice fields retain their original meaning for the HA leg.

A successful response has exact admitted segments/revisions/attribution and
original expiry, current opaque Settings revision, `processor:local_on_device`,
`audio_state:renderer_pending`, `effective_voice:null`. It has no HA audio asset
or voice override. Native voice/locale availability still needs real OS
qualification. Do not speak arbitrary visible bubble text as a substitute.

For automatic local delivery require the original publication eligibility,
confirmed client_device/both output and the separate local autoplay preference.
Prepare is not a publication: its existing autoplay_eligible remains false.
Manual local replay follows the existing output matrix including ha_speaker;
text_only denies all synthesis/output/preview. A successful prepare is neither
ready native audio nor proof of audibility.

Both output keeps Core's independently authorized HA-speaker leg. Native local
synthesis and HA local-audio playback are mutually exclusive choices for the
same contribution. Local prepare cannot dispatch the HA speaker. The existing
speaker operation accepts only ha_configured, with its original journal fences.

Cancel/discard buffered speech on Settings/Session/source/revision/authority
change, expiry, withdrawal or renderer lifecycle cancellation. Re-prepare on a
new deliberate replay; never renew an old grant via read/reconnect. The fixture
covers the24-case output/intent/target matrix, unavailable HA voice, exact live
and retained sources, unknown provenance, expired/withdrawn sources and Settings
change during prepare. Other lifecycle/transport guards execute in owning tests.

A local source/fixture manifest freezes exact bytes after source qualification.
Its digest is a local contract pin, not a protected Git release or installed
producer pin. Existing broader narrative-quality and release gates stay open.
