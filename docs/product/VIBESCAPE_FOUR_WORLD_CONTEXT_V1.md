# VibeScape four-world confirmed context and Visual Director settings fence v1

This is the bounded Core increment under Core1271/1101 and Apple177. Apple owns all native geometry, animation, one local Dynamics control and applied-scene acknowledgement. Core reuses the existing confirmed Session and visual-only producer; no second persona setting, Session, endpoint, renderer or push dependency is introduced.

## Reusable confirmed producer

On the existing authenticated active Session GET, the response paths are `session.session_id`, `session.owner_profile_id`, `session.runtime_state`, `session.dj_persona`, `session.persona_revision`, `session.selected_mood`, `session.mood_revision`. The same axes except owner are mirrored in `session.broadcast.session`. A standalone Broadcast payload starts at `session`; it does not transmit `owner_profile_id`. Bind ownership through the existing authenticated original Profile/Session admission. Local owner checks are not additional wire fields.

Existing capabilities/versions `active_session_persona:1` and `active_session_mood:1` suffice for confirmed family and atmosphere. Consume actual accepted settings and existing revision floors, never a button label, old Profile default or artwork. Failed or pending saves preserve the old confirmed value. Equal-conflicting/stale snapshots are unavailable. Do not fabricate Home for missing authority.

| Confirmed persona | Native family, Apple-owned |
|---|---|
| home_dj | Existing liquid glass world |
| radio_dj | Kinetic metal atelier |
| club_dj | Dark light architecture |
| festival_dj | Cosmic particle/filament sculpture |

Mood changes atmosphere inside that family. Actual accepted playback occurrence changes composition. Dynamics remains a relative local choice across the uninterrupted visit; it is neither measured music intensity nor a Core setting.

## Compatible visual-only guard

The existing `/vibescape/context`, `/interpret`, `/revoke` request/response schemas stay version1 and byte-preserved. No persona/revision/owner fields are added to those closed DTOs. Feature-detect the additive boolean `capabilities.vibescape_visual_settings_fence` and `contract_versions.vibescape_visual_settings_fence:1` before relying on this strengthened server guarantee.

The actual Stage1 observer admission now captures exact confirmed persona, persona revision, Mood and Mood revision from the current authorized Runtime. Runtime and its original Broadcast must agree with strict field types and bounded nonnegative integer revisions. Before/after provider awaits and throughout the original observation/lease, a mismatching value/revision or exception irreversibly withdraws that captured guard. Normal accepted A→B→A increments revisions and cannot revive an old lease. A seen equal-revision conflict is terminal. No claim is made to detect an entirely unobserved corruption that restores every value and revision.

Original owner/Profile/source/Session/visit authority remains separate from these changing settings axes. A valid new Stage1 sample can produce a fresh context under the new confirmed settings. It does not renew the visit's original30-minute deadline,32 attempts or four-active-lease limit. Older leases retain their own captured guard even when the current Observation object receives a newer sample. No raw playback tuple or private source identity is added to the wire.

The existing visual context supplies `observed_occurrence_id`, original lease/issued/expiry and only qualified `music_context.recording`/`symbolic_session_mood`. Empty genres and null audio_features explicitly mean absent information. Occurrences represent accepted track/output/seek transitions; ordinary polling/progress is not a new occurrence, and unobserved replay is not proven. No numeric Track Insight, new provider or model request is needed.

## Same effective Dynamics and original client ticket

Apple's current prepared consumer sends the one visible `visit.dynamics` as both `active_scene.motion` and `dynamics_bias`. Its apply reducer routes a returned motion patch into that same control and excludes it from geometry-motion multiplication. The bounded legacy v1 shape remains compatible; Core does not invent another slider, persist a bias or claim it can see a gesture never sent to the server.

The existing motion directive accepts ten additional complete phrases: more/less dynamics in EN/NL/DE/FR/ES. They map to the existing bounded faster/calmer patch. Matching is whole-clause after the existing scope parser; adding music/HA/unknown text still rejects the whole request without fallback. Palette/depth-only patches omit motion and preserve other choices. Family-specific unsupported instructions remain an honest422, never a persona/settings change.

The original client ticket must bind confirmed Profile/Session/persona+revision/Mood+revision, visit, playback occurrence, scene revision and original request-start deadline. A manual drag advances the local revision and invalidates pending voice; a character change retires old family-specific undo/pending work. Core echoes base_scene_revision but cannot acknowledge renderer application or unsent local gestures. Reset/undo are client scene operations: restore the CURRENT confirmed family, not a past Session persona. Preserve compatible visit-wide colour/Dynamics only under the owning client rules.

## Privacy and acceptance

No visual request starts/stops a Session, changes settings/queue/playback, calls ordinary Ask DJ, creates a DJMoment/Flow/Forecast, or writes Profile/Music DNA/history/SQLite. Deliberate normal settings operations retain their own existing storage and confirmation behavior; they are outside the read-only visual measurement. No transcript/scene/seed/undo/slider state is durably stored, and no sensitive voice body is logged.

The qualification fixture supplies48 Core context states (four confirmed personas × four Moods × three LOCAL Dynamics positions), original wire echoes and causal negative controls. This supports Apple's48-state suite; it does not qualify native animation, low/mid/high visual quality,20-track variation, actual microphone/apply ACK, GPU/thermal performance, installations or human acceptance. Native renderer work can proceed on the existing confirmed Session route independently of this bounded Visual Director guard.

Normal independent whole/exact review, CI, protected delivery and original source evidence remain required. Per the explicit owner instruction, upcoming Core functional changes, documentation and closing reconciliation are bundled in one PR; no extra per-fix PR is introduced. No deployment or new paid qualification is authorized here.
