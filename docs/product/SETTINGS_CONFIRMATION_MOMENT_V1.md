# Accepted settings confirmation Moment v1

A successful, actual user change to Mood, DJ Persona or DJ Presence receives
one short narrative acknowledgement in the newly accepted style. A combined
save receives one contribution confirming all changed axes. The existing
Profile settings v3 acceptance owns this behaviour; automatic Planner Mood
changes do not generate acknowledgements.

Core renders the closed accepted enum values in `en`, `nl`, `de`, `fr` or `es`.
The four Personas retain distinct introductions and the accepted Mood controls
the description and presentation intent. This is a truthful settings response,
not a music fact or a claim to have changed playback. There is no model,
research, Spotify, queue or device request to produce the acknowledgement.

## Acceptance and original identity

The existing SQLite transaction accepts settings, operation receipt and,
when Session history is enabled, one owner-only entry and semantic acceptance
event together. The receipt adds `settings_confirmation` only when a supported
axis actually changed. It contains schema version 1, opaque confirmation ID,
changed fields, accepted Mood/Persona/Presence, locale, original acceptance time,
original Session/generation/revision (or empty/null without a Session), defaults
revision, original Moment ID (or null), title and text.

A no-op, rejected save, stale revision or automatic Mood change has no new
confirmation. Operation replay/readback preserves the original receipt; it does
not apply old settings or generate another semantic event. A bounded pending
RAM publication can recover after a postcommit display/composition failure,
using the original Moment ID and original display clock. Recovery is refused
after expiry, Session end, newer settings or generation change. Reads cannot
reconstruct old publications from durable receipts or renew a lease.

Without an active Session the response confirms the Profile change. It does
not create a Session or a fictitious Session Moment. The client renders that
operation acknowledgement once and does not also manufacture a live Moment.

## Live/native and speech

An active Session publishes an owner-only `session` Moment with
`session_direction` intent and `source_references: ["accepted_settings"]`.
Its internal typed acceptance proof is distinct from Session opening,
proactive direction and researched music facts. The public Moment adds a
`settings_confirmation` identity projection (schema_version, confirmation_id,
changed_fields, accepted_at). Use the existing `native_delivery` admission,
original display deadline and `session_speech` descriptor. No artist art,
playback action, source citation or client-generated text is implied.

An explicit change to Music-only receives this one acknowledgement, then
proactive contributions remain suppressed. Confirmation does not debit or
reset the proactive presence ledger. It may display while music is paused or
absent. Speech respects the accepted announcement output, including text-only,
and the existing paired authorization and local/HA processor selection. A
superseded acknowledgement cannot autoplay again after A→B→A changes.

History-off stores no new history entry or semantic history event; only the
existing bounded operation receipt retains its closed accepted values and
confirmation. With history on, `runtime_accepted_settings_v1` is a separate
owner history/speech basis; history v1 requires the normal v2 upgrade for this
new basis. Retained rows are historical, never renewed current contributions.

The qualified legacy explicit-setting route uses the same authored confirmation
and owner Session history transaction without inventing Profile defaults or
migrating unknown choices. It preserves existing CAS and v3 upgrade guards.
An unknown legacy Mood requires normal settings selection, not an invented Mood.

## Client adoption and delivery status

Feature detect `settings_confirmation_moment` / version 1 and the additive
`settings_confirmation_contract` on settings responses. Deduplicate the original
confirmation/Moment identity across accepted response, readback, snapshot and
reconnect. Render the accepted settings response or its live Moment once;
never read the acknowledgement as a new change on each settings GET. Ordinary
paired transport/privacy and the original server expiry remain authoritative.
The old automatic Mood→mix-question feedback trigger is withdrawn; explicit
Ask DJ music/mix requests retain their existing proposal/action workflow.

This change belongs to draft Core PR1290. Apple adoption, actual native display,
audible output and user acceptance are separate. No merge or install is
permitted until Peter explicitly asks to merge the combined PR.
