# For-you original output readback repair — 2026-11-06

The native Apple lane reported one genre→speaker selection after which the old
track remained paused and no selected mix start was confirmed. Read-only Core
correlation found the output adapter call at13:46:21 and no following play_uris.
The original HTTP error response was not retained. Its precise cause remains
unproven; this repair does not retroactively claim native/provider acceptance.

A causal isolated HA probe establishes a narrower bug: the normal output adapter
has already confirmed the exact speaker through its fresh player readback, but
an independent devices inventory still reports it inactive. Original source
returns409 first_play_output_changed before starting the selected mix. A paused
old track alone passes. Original failing probe output remains separately retained
under `for-you-speaker-investigation-20261106` and `before-fix-valid`; source and
external response fixtures are distinguished, with zero real provider/model calls.

The repair consumes only the private normal adapter's matching dispatched receipt,
strict true readback_confirmed, selected_output_id and playback.device.id. If that
receipt is absent or disagrees, the original guarded fresh-inventory check remains.
The original first-play admission, exact context/Session/lease, frozen media and
single durable effect owner are unchanged. No transfer retry, start retry, fallback
speaker, new preference authority or Profile write is introduced. A paused track
confirms only the selected speaker, never that the mix has started.

Qualification on product commit05d36ca3:28 isolated actual HA protocols PASS with
unchanged product hashes; six new EN/NL output cases PASS through actual paired
HTTP/Store/normal adapters with only Spotify responses synthetic. Positive paths
perform one output transfer and one exact-mix start; duplicate choice returns the
same result without another effect. Negative readback paths return409, perform
no mix start and do not transfer again.420 related tests are accounted: the first
band-story source-pin failure is preserved and its13-test module passes after the
actual receipts are rebound.28 focused evidence/Golden/lifecycle checks pass.
Ruff and the PR diff whitespace check pass. All308 product files are pinned;
25 current projections and the existing eight Mood/continuation cases are rebound
from actual reruns while historical originals stay unchanged. The new six-case
fixture is `examples/client_contracts/session_for_you_v1/actual-ha-output-readback-20261106.json`.

The cost-free EN/NL functional Golden job now schedules the new output harness.
All five product localization families and the original paid release gates remain.
Source, exact-head CI, protected merge/Finalization, HA-dev installation/readback,
real native/provider/audible acceptance and APNs are separate. No new installation
or native retry was performed during qualification. #1439 remains independent.
