# Profile Spotify reconnect repair — 2026-11-06

Decision: PASS for isolated source qualification; protected GitHub and owner gates pending.
Branch: `codex/profile-spotify-reconnect-20261106`.
Base: `b5f06bb6ec29b7d2a5f2ca464550b269def8976d`.
Pull request and exact candidate SHA: recorded at the protected PR freeze; base SHA above is not the candidate authorization.

## Reproduced defects and scope

Before repair, the causal shared-client test could not find the reconnect
option; selecting the existing Spotify backend returned a form error rather
than reusing the Profile connection. The requester's lack of local credentials
was incorrectly interpreted as a missing Profile connection.

Scope evidence added by #1487 updates `observed_at` on token refresh. The entry
reload signature included that receipt, causing refresh -> metadata update ->
reload -> refresh cycles. Ordinary shared-client requests then failed with
profile_connection_unavailable despite correct persisted Profile references.
The fix excludes observation metadata, not meaningful configuration identity.

The callback used the global runtime for ordinary reauthorization and even
initial setup. It now persists to the exact bound existing owner, or to the
original initial flow only. Options completion selects the options manager.
No duplicate credential owner or linked-client credential copy is introduced.

The separately reproduced read-only Discovery command tested the canonical
ProfileBackendView as though it were the registered raw runtime. It now checks
the original registered caller while retaining the view's original provider
and full runtime scope. A changed pairing remains rejected, without a write.

## Evidence and verification

The original failed causal tests and all earlier diagnostics remain private in
`/Volumes/Shared Data/tmp/pcvantol/core-profile-spotify-reconnect-20261106`.
Qualified host verify exited0 with manifest/bootstrap desired-state MATCH.
The prior #1490 Finalization main run42277371292 passed; its clean identical
merged worktree was archived into a verified full-history bundle and removed.
No other worktree, WIP or recovery snapshot was removed.

New unit checks exercise same-backend reuse, five supported client families,
exact owner targeting, no credential copying, changed account/client/owner,
ambiguous owner, binding generation, disabled requester and metadata-only
versus real client-ID configuration updates.

The isolated HA harness `verify_profile_spotify_reconnect_http.py` exercises the
actual options preparation, HTTP callback, ConfigEntry persistence and disk
Store. Token exchange, reload and options-flow completion are explicit
fixtures. Ten cases pass, including success, duplicate, Profile/account change,
owner unloaded/disabled, requester replacement, dead owner-reference recovery,
metadata persistence with no reload and initial-flow isolation. It uses no
network, model, real grant, playback or installed HA mutation.
The paired Discovery harness separately qualifies the canonical view path and
stale-pairing rejection against synthetic provider wires.

Maintained protocol reruns, current receipt binding, full tests, static checks
and protected GitHub qualification are required before merge. Exact current
Owner Authorization, separate Finalization, composed #1439 qualification,
HA-dev install and independent runtime readback remain separate gates.

## Installed and product acceptance boundary

HA-dev retains restored debug `1e990d979d55b5e54f58f3e90f9a65ec03c92516`,
qualified main `dacf9cd01a8fbc17827438f228d95657fe62de93` plus original #1439.
Three ordinary backend reads succeeded after source-only recovery; credentials
and Profile storage were not rolled back. Do not claim new main is installed
until qualified repair deployment and exact installed hash readback occur.
No audible/native Spotify, physical Watch or APNs outcome is established here.

The Apple lane's exact HAEVN request (`Heb je iets van de artiest haevn`) is a
separate read-only discovery regression awaiting current response correlation.
No fabricated five-playlist/five-album response or provider acceptance is
included in this repair. Help EN/NL publication, other three pending textual
locales, all five-language UI data, Golden998 cases and execute:false remain.

## Final local qualification

All34 maintained actual-HA groups passed with frozen308 product-file hashes
before and after their execution. Current receipt bindings are regenerated from
those actual reruns, not from hash-only relabelling. The new reconnect wire proof
also binds both added harnesses; historical original receipts remain unchanged.
The canonical repository runner used by `.github/workflows/validate.yaml`
(`tools/run_parallel_unittest.py --jobs 4`) reconciled all4700 discovered/started
IDs, all four worker exit codes0, with only the11 existing skips. The exploratory
single-process discovery retained two order-sensitive artist-draft failures;
those same three artist tests pass alone, and the canonical complete process
shards pass without selection, changed assertions or added skips. Original
single-process failure logs remain available for later fixture hygiene work.
178 focused source/receipt/flow/Golden tests and8 lifecycle/roadmap checks pass.
Ruff and diff validation pass. Bandit medium/high scan reports no findings.
Golden catalogue changes are limited to three refreshed producer receipt hashes;
all998 case definitions, model policy, locale scope and execute:false are intact.
Verification-framework results are recorded separately at freeze.

Created: Profile reconnect contract, this report, two isolated HA harnesses,
causal unit checks and exact-source reconnect qualification fixture/test.
Updated: options/callback owner routing, receipt-only reload identity,
canonical-view read guard, five-language option errors, original orphan-contract
navigation and current actual-HA receipts/Golden receipt hashes/rolling records.
Remaining: exact current Owner Authorization and protected merge, separate
Finalization, qualified main+#1439 debug composition, authorized HA-dev install
and exact runtime readback. No new live OAuth or playback has been performed.
