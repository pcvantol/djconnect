# Spotify volume action-error repair — 2026-11-06

Decision: PASS for source/offline protocol verification; NOT QUALIFIED for live
provider, installed iPhone or audible acceptance. Branch:
`codex/spotify-volume-action-error-20261106`. Base main:
`b9cc7a50d81e3845e1d8cf37ca8cbd43e24781d2`. Documentation-first commit:
`73c1cd40` (full identity is in enclosing Git). Exact implementation commit and
reviewable PR are the enclosing immutable Git/GitHub identities; merge is pending.

## Cause and behavior

The old source replaces Spotify supports_volume:false with not is_restricted,
so an unrestricted output incorrectly appears volume-capable. A set_volume
failure writes global backend_available:false and last_error. volume_delta runs
outside that error wrapper, so a refusal can escape; a returned success:false
can also be overwritten with success:true. Original failing offline results
remain external in core-volume-action-error-20261106/before-fix.log. The first
probe's imported-test discovery issue is retained separately; correcting that
fixture import did not change product expectations or turn the original red
regressions green.

The repair preserves exact provider true/false, with null for missing/invalid
capability and no name/type heuristic. Only a403 with the specific provider
volume-refusal reason becomes MusicBackendCapabilityError supports_volume.
Other403 / 503/timeouts remain command failures, not permanent capability claims.
Both paired commands use the additive action-scoped contract in
SPOTIFY_VOLUME_ACTION_ERRORS_V1.md. No command failure writes global health,
last_error, DJ text, voice, cached playback or Session state. Generic failures
omit backend_available instead of pretending to know health. Independent status
errors keep their existing global error behavior. A failed delta status cannot
fall back to cached volume and dispatch a write. No extra request or retry.

## Verification and evidence

The host verification exited 0 with onboarding 4.5.6 and MATCH. Nine behavioral
unit regressions pass, plus one actual-receipt binding test. The broader pinned
HA no-network test run passes 257 tests before adding that final receipt assertion;
47 current receipt/consumer/volume checks pass locally. Ruff, projection and diff
checks are required before push and exact-head GitHub CI remains separate.

The new actual isolated HA verifier uses ordinary pairing, registered loopback
HTTP routes, the real ConfigEntry/Profile/provider fences and SQLite. It performs
49 requests including 18 volume/capability cases in EN/NL; only provider responses
and the synthetic token are replaced. One PUT per intentional synthetic volume
case, no retry, no response DJ/audio/playback leakage and unchanged active Session,
DJ text and health are asserted. All 29 current isolated HA protocol suites pass
on unchanged product hashes with network disabled. Their 28 maintained current
receipts are rebound only from actual reruns; historical originals and all
failures remain. All 308 product files are pinned. The native consumer inventory
changes only the affected receipt digests, with no policy/locale/question change;
its synthetic examples still grant no live authority.

Golden relationship: the new provider-free unit module is automatically included
in normal PR discovery. The actual HA source verifier is an explicit local proof;
no paid model/native job or additional per-PR workflow is added. No provider/model
calls, OAuth repair, live volume change, HA-dev install or native installation
occurs in this preparation increment. All five product localizations remain.
Apple separately reports its ten old/new command-form regressions green; those
are Apple evidence, not Core or physical/native acceptance.

## Remaining gates

Exact-head review/CI and any required Owner Authorization precede merge. The
prior #1480 approval does not authorize this new product SHA. Separate mandatory
Finalization follows a protected merge. The owner's after-each-PR HA-dev debug
update remains applicable after merge, preserving #1439 and independently reading
runtime. That future composition must retain the Watch-specific http.py changes
while adopting this volume helper. Original #1439 signer/restore/physical/APNs and
Golden native fixture/operator/provider gates remain OPEN.

Recommended next prompt: review this concrete source PR and its current checks;
authorize its exact SHA if required, then merge/finalize and install the new main
debug on HA-dev. Real iPhone volume refusal/audio acceptance remains separate.
