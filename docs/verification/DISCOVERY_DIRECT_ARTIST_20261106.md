# Discovery direct artist playback qualification — 2026-11-06

## Scope and owner choice

The owner explicitly chose direct artist playback without a This Is promise.
Base main: 48434a60ccef649725a4bc8898f4aa3210570e6a, after source1491 and
Finalization1492. This isolated increment preserves HAEVN source WIP and the
original #1439 development overlay. Current host verification exited0/MATCH;
no machine repair or cleanup was performed.

## Actual provider observation (read-only)

At 2026-11-06T20:23:12Z, the existing paired MacBook/DEFAULT connection returned
valid artist identities for London Grammar, Snow Patrol and Son Mieux. Their
bounded This Is searches returned6,6,5 candidates and no qualified Spotify-owned
exact-title candidate. There were zero playback writes and no new dispatch
capability. Absence in search is not proof of playlist nonexistence or the
app's dashboard quota mode. No credentials, full search results or raw history
are included. Spotify documents artists as valid playback contexts at
https://developer.spotify.com/documentation/web-api/reference/start-a-users-playback.

## Causal and disposable paired HA proof

The new original-card/empty-editorial-search scenario failed against the old
product with music_discovery_this_is_not_found before the product change.
The original log is retained outside the repository. The repaired product uses
one exact artist identity GET, the currently observed unrestricted output, one
context PUT and separate readback. It never calls editorial search/items.
An extra caller-supplied artist URI cannot change the cached selection.

The existing14-case real paired HA transport proof now reflects the explicitly
revised product requirement; no dispatch, denial or lifecycle assertions were
removed. Wrong artist identity, denied identity, failed write, missing output,
expired/future cache, duplicate/concurrent card, pairing replacement during
artist/token waits and real aiohttp disconnect-without-replay all pass.
Read-only official playlist diagnosis and denial evidence remain independently
covered, without becoming a fallback or replay capability.

All34 existing isolated actual HA protocol groups were rerun against the same
frozen308 product files. Every group passed and the product hashes before/after
are identical. Current wrapper receipts and native Golden catalogue source pins
were rebound only from these actual reruns; historical originals remain intact.
Large fixture diffs contain fresh synthetic identities/times and evidence pins,
not extra product capability. Provider/model/installed effects in these labs:0.
Pinned HA2026.10.0 / Python3.14.6 / aiohttp3.14.4 image:
sha256:1b64d38f38d922bf9d59336451fd6453e1d614f934456af4ee3d2a51061be3a4.

## Local validation

42 focused tests pass, including the three reported artists, wrong provider
id/URI/type/name, no external effect scope and withdrawal during artist lookup.
172 verification-framework tests,8 lifecycle/roadmap checks, Ruff, Bandit at
medium/high severity and diff validation pass. All4704 canonical process-sharded
tests reconcile and pass with11 existing skips, zero failures/errors and no new
skips. Exact worker/discovery reports are retained in full-unit.
Golden998 scenario definitions, model policy, all five UI languages, EN/NL
selection, Help28/42 textual boundary and execute:false are unchanged.
This is producer regression evidence below the existing Discover Golden cases;
no paid model or native qualification claim is introduced.

## Delivery boundary

Source qualification, exact-head Owner Authorization, protected PR merge,
independent main checks, separate Finalization, #1439-preserving HA-dev install,
live Spotify context readback, native queue refresh and audible acceptance are
separate gates. No merge, install or live playback is claimed in this record.
The context acknowledgement does not prove manual Spotify queue entries were
erased. No automatic transfer, append, token rotation, broader scopes or retry.

## External evidence identifiers

Evidence root: /Volumes/Shared Data/tmp/pcvantol/core-discovery-direct-artist-20261106.

- Original failure log SHA256: `7e6422efc203603e9a935bde8b336c5c1059cb7adeda70c619e1fa5300918fce`.

- Actual Discovery raw receipt SHA256: `72e24ee222a4e8fea7973a4b2f33d9dd5218c379e40667a356a41b1a8f17e063`.

- All34 result manifest SHA256: `d1f822f25ad6f7367d8767fc66e14e2b3edf94ef977cf9fbc55aedacc8e67347`.
