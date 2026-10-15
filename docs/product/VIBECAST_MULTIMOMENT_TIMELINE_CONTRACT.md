# VibeCast same-track Moment timeline — delivered Core source slice

## Owner-authorized current-slice extension

The [VibeCast owner refinements contract](VIBECAST_OWNER_REFINEMENTS_CONTRACT.md)
records the new bounded qualified-fact producer/display path, responsive UI,
read-only next-queue item and separate opt-in receiver end authority.
[PR #1120](https://github.com/pcvantol/djconnect/pull/1120) delivered the
protected source; the physical Pi run observed two factual types on one real
Spotify track and normal physical end. Automatic per-Moment capture and
full-rate motion remain partial. The completed baseline below stays historical
and its evidence is not retroactively upgraded. Older source qualification
flags and generic Broadcast permissions remain unchanged.

**Assignment:** `DJC-CORE-VIBECAST-MULTIMOMENT-TIMELINE-V1-20261006`  
**Owner:** DJC-CORE  
**State:** [source PR #1118](https://github.com/pcvantol/djconnect/pull/1118) protected merged as `f15fb861e223a209341592666dc2092bad4b4a2e`; [software/browser acceptance](https://github.com/pcvantol/djconnect/issues/1101#issuecomment-6012947392) passed. Physical 10-inch Pi and fresh installed/live qualification were not run for this slice.

## Outcome and ownership

One sufficiently long, actively observed playback item may receive a second
substantively different DJMoment during the same active Session. The Runtime
uses the existing Planner, Knowledge Engine, Moment Engine, Session Flow,
Presentation Composer and Broadcast. VibeCast only presents approved, current,
unexpired Moments. Its cards do not create Session history or trigger audio.

## Bounded current-track opportunity

- The existing Spotify Direct observer supplies fresh, normalized playback
  position, duration, state and item identity. Its existing Track Insight
  provider supplies one safe current-track context. The Runtime retains only a
  small allowlist of that context until the observed item changes or ends.
- The Planner considers one later opportunity after a real, non-Silence first
  Moment. The item must be at least three minutes long, playing, and have at
  least 45 seconds left. The Broadcast-only contribution waits for observed
  playback distance of 15–60 seconds according to the first card's approved
  read duration, leaving a short valid overlap for a calm handoff. Genre
  context receives at least 45 seconds of approved display life. The existing
  spoken-Moment spacing and audio policy are unchanged. The opportunity never
  fires from a local progress estimate or future queue guess.
- The Planner may select one *different* existing factual angle whose safe
  primary evidence is actually present. Track Context requires the existing
  analysis text; Genre requires the existing Track Insight genre evidence.
  Artist/Album credits remain behind their Phase A source gates. A missing
  second angle produces no card. At most two factual Moments are published for
  one observed item by this slice; no deferred backlog is accumulated.
- The Knowledge Engine reassembles only the selected allowed context. The
  Moment Engine freezes a new identity and distinct content. Performance
  Memory, primary-evidence checks and an angle/subject key prevent repetition.
  The Flow is append-only and Broadcast uses its existing event vocabulary.

## Validity and cancellation

Selection and publication require the same Session and hashed observed item.
An internal generation invalidates in-flight work on track change, pause,
seek, changed playback source, idle/stopped state, Runtime end and unload.
Publication rechecks these conditions, observation freshness and remaining
read time after Knowledge returns. Resume never drains missed opportunities;
one fresh observed position can approve at most one available angle. A
backend without reliable state/position/duration keeps the prior one-Moment
behavior. No Playback Instance Identity or Stage 2 claim follows from this
binding.

## Renderer contract

The existing renderer-safe `moment_id`, `type`, `created_at`,
`playback_item_id`, `presentation_intent.maximum_duration_seconds` and
current playback projection establish card identity, order and expiry.
VibeCast keeps a maximum of two visible cards and a bounded deduplication
window. Snapshot/reconnect loads only currently valid cards without replaying
entrance animations. Broadcast event sequence and per-field ordering reject
duplicates while allowing a Moment after a later presentation event. Events
may animate a new approved card once. Progress
updates do not reset its read period. Current-track change and Session end
remove cards locally; committed Moments and Flow remain immutable. Missing or
unknown optional fields preserve safe old-client behavior. Type labels and
other new copy use the Session language across en/nl/de/fr/es.

## Evidence gates

Source tests must show one real Session and observed track producing two
different existing Moment types through Flow/Broadcast, plus negative cases
for insufficient context/time, pause/resume, seek, track change, late work,
reconnect and end. Browser acceptance must inspect a real 1200×1920 render
sequence, card transitions, readable long copy, stable Now Playing and reduced
motion. Software/simulator and physical 10-inch Pi evidence are separate.
