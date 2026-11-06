# Passive Session original progress projection v3

This owner-requested extension reuses PASSIVE_SESSION_PROJECTION_V1.md and its
v2 contribution rights. It adds no producer, provider request, intelligence,
background grant or external relay. Mac widget layout and native shared-cache
writes remain Apple-owned. An empty cache is not permission to copy private
foreground, Track Insight or history snapshots.

## Exact negotiation and content

contract_version remains1. Capability projection_versions includes1,2,3 and the
default remains1. authorize/read must both explicitly select projection_version3
for a v3 grant. Existing v1/v2 resources and closed Direct-rich-v1 codecs remain
unchanged. Projection version is distinct from surface context/register v3.
No read reauthorizes, creates a grant or upgrades an existing grant's version.

V3 retains v2 independent contribution/now_playing/artwork statuses and source
rights. It adds only optional now_playing.progress, a closed object containing:

- schema_version:1;
- position_ms: exact accepted original nonnegative integer, bounded by duration;
- duration_ms: exact accepted positive integer;
- playback_state: original playing or paused, matching the current same subject;
- observed_at: the original accepted observation UTC stamp;
- expires_at: the earlier of that original observation's120-second expiry and
  the outer original snapshot expiry.

Integers exclude bool and must fit the JSON interoperable safe integer range.
No duration/position inference or fallback to current extrapolated Broadcast
state. Unknown/invalid/missing numbers, subject/state mismatch, future or expired
clock evidence omit progress while independently eligible music text/art survives.
The surrounding original now_playing item_id/subject_uri, Session/binding/
generation, sequence/revision and lease remain mandatory client bindings.

Data comes only from the already accepted broadcast.passive_observation object
and its original monotonic/UTC capture. Repeated reads preserve position, observed
stamp and expiry, do not mutate publication/sequence/source state, and cannot
turn internal progress ticks, Mood changes or redraws into fresh observations.
A genuinely new accepted observation may supply a new exact sample; it is not
manufactured by a passive read.

## Native rendering and lifecycle

For playing only, native hosts may render deterministic elapsed visual progress
from the exact sample, bounded by duration and all shorter original field,
snapshot, purpose and shared-cache deadlines. This is presentation, not a new
playback fact or next-track prediction. Pause freezes at its exact accepted sample;
a state mismatch without a new sample stops progress. Track/session/binding/
generation replacement, expiry or clock uncertainty removes old progress. Reads,
App Group writes and WidgetCenter redraws never restart a lifetime on arrival.

Track/artist/album use the original now_playing metadata. Cover uses only the
already prepared independently admitted current-cover bytes; no foreground/private
URL substitution or external fetch. Mood colors use confirmed mood.value/revision.
Contribution keeps its original full qualified text/source attribution and own
expiry; Apple may truncate visible lines per widget size, without rewriting,
summarizing or dropping the original stored text/attribution. Missing contributor
rights, music-only/Silence, private/overlong/expired content remains independently
unavailable. No resurrection of an older/private contribution to fill whitespace.

## Qualification boundary

Fast regressions must cover exact original versus ticked position, playing/pause,
zero/invalid/missing values, seek/new accepted observation, subject/state changes,
dual-clock expiry/rollback, no read renewal/mutation, unchanged v1/v2 wire behavior,
original contributor rights and ordinary paired owner/consent/version fences.
Actual isolated HA/HTTP source proof stays separate from live provider action,
Mac WidgetCenter detection, shared App Group cache, physical/native display and
background/APNs acceptance. This source extension alone cannot fix an unconfigured
native widget or grant authority to another host.
