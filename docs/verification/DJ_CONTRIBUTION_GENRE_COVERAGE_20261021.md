# Current-track genre coverage after declined catalogue stories

## Problem and demonstrated cause

Peter reported very few automatic DJ contributions in an active Presenter
Session. Owning Apple checks found the same scarcity in producer history and no
client decoding/filter loss. Those historical counts alone do not establish
continuous playing time or why each individual opportunity was declined.

A reproducible Core starvation case exists independently of those counts:

1. The current observer finds catalogue album information and returns only its
   qualified fact pool, without obtaining the ordinary current genre evidence.
2. Required album research is rejected. Core correctly declines the technical
   catalogue-date fallback and consumes that attempted fact key.
3. Further observations of the same accepted recording enter the exclusive
   qualified-facts branch. Its nonempty but exhausted pool has no eligible fact;
   separately available genre context is never offered to the Planner.

An offline reproduction on protected source51d9fdf5 exercised the production
Runtime with a synthetic current recording, Presenter,300seconds duration and six
fresh playing observations at0/15/30/45/60/75seconds. One explicit synthetic album
rejection produced zero contributions. No network/provider/model call occurred.
Supplying an independently qualified genre fact to that same existing Runtime
produced exactly one genre contribution, without retrying the rejected album or
publishing a raw-credit/date fallback. This demonstrates the bounded defect; it
is not retrospective proof of every sparse live recording.

## Bounded correction

Two product files change: `spotify_backend.py` and `playback_observation.py`.
Runtime, Planner, Presence policies, expression, research admission and persistence
contracts remain unchanged.

The existing per-track observer may add at most one separately qualified
artist-genre fact beside catalogue/CC0 facts when the existing pool has room below
six. It reads exact captured current-track metadata and exactly one valid Spotify
artist ID. The backend reuses its existing artist-ID cache and error backoff,
with a three-second bound. No repeated current-playback request, TrackInsight
request, model call, Music DNA write, new observer or per-screen-read lookup is
introduced. Cache reads preserve the original genre-source expiry.

Captured observer identity, command revision, owner/source/entry authority,
Profile storage identity and authority revision are rechecked around the await.
Current Session, exact recording/output and playing state must still match.
Runtime/account/credential scope changes discard the added evidence. Cancellation
propagates; unavailable evidence never authorizes another provider/model fallback.
The existing `observed_genre_facts` validator admits only eligible typed evidence.

The ordinary Planner can then choose that distinct fact after declining the album
story. Used fact keys remain consumed. Presence limits, readable duration,
remaining playback, freshness, pause/seek/source withdrawal and publication fences
remain in force. A rejected story still consumes no successful-publication debit.
Artist genre is contextual metadata, not a measured property of the recording;
no energy, BPM, danceability, instrumentation or other audio measure is invented.
Existing five-language/persona realization is reused without new UI strings.

## Qualification and deliberate limits

The owning regressions exercise the actual observer, backend cache, Runtime,
Flow/Broadcast and SQLite causal publication boundary with synthetic inputs:

- A declined album plus independently valid genre yields one genre contribution,
  one artist-ID request and no duplicate or repeated research on further polls.
- A command, authority revision or current track changed during lookup discards
  the result. A full six-fact pool makes no additional request; insufficient remaining playback stays silent.
- Paused/ambiguous/mismatched metadata is refused before lookup. Cache reuse
  preserves original expiry; expired, missing or another artist's metadata cannot
  become a fact. Account/credential changes, timeout and cancellation fail closed.
- A live publication does not create archive authority. Without archive admission,
  actual SQLite reopen retains only its unavailable causal receipt, not prose or
  an executable speech grant.

Targeted validation:124 tests PASS4.574s. Full2994 tests PASS124.490s, seven
existing skips. The new combined observer fixture initially used stale module
references under whole-suite loader isolation; it now patches the actual owning
module/class. No product policy was changed for that harness correction. Changed
Ruff and diff checks pass. Existing client fixtures and
wire/schema versions are unchanged; no Apple/Pi/API/receiver source is modified.

Missing genres, multiple credited artists or a full pool remain outside the added
coverage. This correction does not guarantee a contribution every fixed number
of seconds or weaken factual quality to increase counts. Actual live cadence,
model-written literary quality, native/audio and end-user acceptance require
separate evidence. Validation uses synthetic data and zero paid model attempts.

The source still requires independent exact review, normal protected merge and
actual canonical qualification, a distinct documentary Finalization, then a
controlled HA-dev install with retained rollback and actual runtime/HTTP readback.
The sole Core writer retains Peter's fixed19:10:02UTC deadline. His separate
queue-backed human Forecast, current TrackInsight binding, captured artwork,
Music DNA artwork and historical playback requests remain tracked separately.
