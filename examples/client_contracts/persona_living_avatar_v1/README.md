# Existing Core signals for Living Persona Avatar v1

`existing-signals.json` is a deterministic semantic derivative from actual
Runtime/Broadcast projections. Inputs are synthetic. It deliberately removes
private/random identities and wall timestamps; it is **not** a replacement raw
HTTP schema, a UI reducer, actual sound or installed/native qualification.

Six actual Core states cover empty active, music_only, intentional Silence,
confirmed Mood revision, confirmed Persona revision and end. Source SHA256 pins
identify the exact producer modules. `tools/verification/persona_avatar_signals.py`
rebuilds the derivative; `tests/test_persona_avatar_signals.py` compares it and
checks the80Persona/Mood/language cells, no side effects on reads and replacement
Session fencing. Two owning Ask DJ regressions cover explicit text and cancellation
in music_only without proactive publication or budget reset. An additional
actual Runtime announcement probe checks typed public provenance, original native
authority, expiry and rejection when only public-looking metadata remains.
These tests never implement Apple glyph selection or demonstrate audible output.

Touch reactions are NOT_IMPLEMENTED/NOT_ADVERTISED. Existing speech/Ask DJ
support never grants reaction or remote-speaker permission. No new wire fields,
capability, Moment, renderer state or native source are introduced by this fixture.
Original fixtures elsewhere are unchanged. See
[the canonical contract](../../../docs/product/DJ_PERSONA_LIVING_AVATAR_V1.md).
