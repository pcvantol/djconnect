# Silence live delivery v1

Version-bound additive refinement of [Native Moment Delivery](NATIVE_MOMENT_DELIVERY_CONTRACT.md).

## Intentional Silence live signal

An actually committed `DJMoment.type: silence` is delivered through the existing
`dj_moment_published` event and existing Session Flow. It is a semantic
non-interruption decision, not a fact card, speech request, model answer,
provider failure notification or proof of playback. No event is inferred from
missing content, pending generation or disconnected transport. Existing
music-only admission does not manufacture extra Silence publications.

The ordinary immutable session/moment identity deduplicates delivery. Snapshot
and replay preserve the original publication deadline. Native admission adds
`qualification: intentional_silence`, no actions, no current fact-card admission,
and the original finite `display_expires_at`. Additive
`native_delivery.current_silence_moment_id` identifies only the latest applicable
same-playback decision while playing, before expiry and within the active Flow.
A later content Moment, track change, pause, expiry, withdrawal or Session end
clears that current signal. Reconnect cannot renew it or revive earlier cards.

Clients may use that identity to dim contributions or otherwise express quiet
without fabricating a chat bubble. Clients own the visual choice and must keep
content legible and accessible. Older clients may ignore this additive field.
Silence never triggers TTS, counts toward non-Silence history totals, spends a
proactive content budget, archives a source body or exposes private reasoning.
Native UX adoption remains consumer-owned and separately unqualified.
