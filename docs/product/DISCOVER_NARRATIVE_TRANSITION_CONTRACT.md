# Bounded Discover narrative: Genre → Track

`DJC-CORE-DISCOVER-NARRATIVE-TRANSITION-V1-20261004` selects exactly one
additional typed relation: `discover_same_artist_genre`, from an existing
**Genre** Moment to an existing **Track** Moment. It does not complete all of
DI-3.2, ME-4.1 or ME-3.4.

## Producer and proof

Spotify's existing `/me/player` normalizer supplies the current track URI,
title, artist name and artist IDs. The existing status path enriches playback
with artist genres from `/artists?ids=…`. Genre evidence is qualified only
when the returned artist object has the exact requested artist ID. Track
Insight receives this status through `run_music_command("status")`; its
separate name-based artist-profile lookup and generated `analysis.genre` do
not prove this relation. A private Session evidence projection is selected
from the same status read as Track Insight, never from its cache or public
response. It cannot enter public Track Insight, Moment copy, Broadcast or
persistent storage. Its URI must match the already accepted Playback
Observation URI, rejecting a stale second status read.

One committed Genre Moment opens a line on observed Spotify track A only if
its title equals a genre in that status, exactly one artist ID is present, and
status title/artist match Track Insight's projected track. The immediately
next accepted distinct Track Started event B may deepen it only if B creates
a committed Track Moment, has the same unique artist ID and genre in verified
status, has a different URI and bounded title, and its own status/Insight URI
and labels agree. This proves only that two observed tracks by one identified
artist were encountered while artist metadata carried the same genre label.
It does not prove a track genre, credit, influence, history or future choice.

## Lifecycle and placement

The Runtime-owned Planner stores at most one pending line: source Moment ID,
bounded source title/artist/genre, opaque URI and artist ID, Mood, Persona,
Direction and the immediate-next-event marker. No scheduler, second history
store or cross-Session memory is added. A duplicate URI does not consume the
opportunity. Any missing, ambiguous, stale, conflicting or unrelated context,
Silence, Mood/Persona/Direction change or Flow invalidation abandons the line.
It cannot reconnect later. A completed or abandoned line does not reopen in
that Runtime. Session end disposes it.

The Planner approves only after both Moments are committed to the same Flow in
order, the source remains in bounded Performance Memory, and the existing
four-Moment Transition spacing permits it. The Moment Engine validates exact
Genre → Track types and IDs, then creates one immutable Transition at `NEXT`
after the Track Moment. Session Flow/Broadcast publish it. The current
Exploring Recommendation Transition retains its own behavior; Manual and
Continue do not gain this relation or change their contracts.

Five localized variants use only the observed artist, prior and current
titles and shared artist-genre context. They describe a second listen to the
same artist in that context, with no raw URI/ID/provider payload, profile
information or unsupported factual claim. Abandonment is silent.

Runtime tests first fail on the baseline for a valid multi-event sequence;
negative, deduplication, invalidation, lifecycle, spacing and existing
Transition regressions are required. A producer test exercises the actual
Spotify normalizer, ID-checked genre enrichment, Track Insight status and
Session provider, with mocked HTTP replies rather than fixture-only fields.
Source acceptance is separate from installed/live and physical Pi acceptance.
