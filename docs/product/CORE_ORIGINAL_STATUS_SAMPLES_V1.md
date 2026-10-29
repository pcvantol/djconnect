# Original status-source samples v1

This internal producer records observed playback DATA for subsequent status-only
widget/Activity work. It supplies no push permission, native lifecycle identity,
registration or provider effect. Existing af201 registration and 090b status
presentation contracts remain unchanged; public positive role admission is closed.

## Original observation and scope

The regular Spotify observer captures the already-loaded owner/source/Session,
original Broadcast, exact settings generations/revisions, storage authority,
observer command revision and runtime/config identity before the provider await.
It seals UTC milliseconds and a monotonic timestamp immediately on return.
Guarded command readback captures before the real player GET and seals immediately
after its return, before favorite/genre/Music DNA enrichment. Private typed dict
metadata carries that original witness to the observer; ordinary JSON responses,
the runtime playback cache and Music DNA receive only the existing dictionary
fields. A plain dictionary cannot synthesize the missing original observation.
The command's own synchronous N-to-N+1 transition preserves the original event,
clock and shared spent/revoked latches. A competing command closes the witness.

Playing/paused/stopped are observed states. Empty idle maps to unknown. No track,
artwork or user-facing text is exported by this journal. The sample UUID and local
ordinal are private source DATA; they cannot stand in for presentation_id,
presentation_generation, sequence, grant_epoch, target_generation or
source_generation from the native delivery contracts.

## Settlement and retirement

Migration 17 adds djconnect_status_samples. Each private SHA256 scope covers the
actual entry/owner/source/Session/settings incarnation. A row stores original
sample UUID, local ordinal, original UTC milliseconds, state and an ended marker.
There is at most one latest row per scope, with a fixed 4,096-scope capacity.
Existing rows can advance within that bound; there is no eviction or replay reset.
Clock regression and exhausted ordinals close writes instead of clamping time.
An ended scope cannot reopen. Restore does not adopt any row as RAM authority.

The existing persistence provider verifies WAL/FULL settlement with authorization
checks before dispatch and before commit. SQL workers receive immutable scalars;
HA/source/currentness checks remain on the HA loop. Cancellation is preserved
after definitive SQL settlement, including lost responses; no uncancel or retry
turns a possible commit into new publication authority.

Weak negative witnesses are installed before awaits. Runtime or observer
retirement revokes pending source witnesses synchronously and drops cached
original source references. Session end captures its original clock before the
manager-lock await and closes late samples even without a visual listener.
A failed end transition or a committed transition with lost acknowledgement
retains an opaque negative fence while releasing source/credential references.
A local ended DATA row does not prove an OS Activity ended.

## Qualification scope

The actual isolated HA harness uses the shipping manager factory, real paired
HTTP/source/settings/observer/Session lifecycle and SQLite. Fifteen causal cases
cover original backend clocks, held locks/enrichment/guards, source/settings
changes, competing commands, plain-dictionary denial, retirement without cached
samples and failed/lost-acknowledgement end transitions. The same harness on
protected parent ffa75 fails because the real accepted observation has no sample.
The original failure and success receipts remain separate and hash-bound in
[the source DATA fixture](../../examples/client_contracts/status_source_samples_v1/actual-ha-source-data.json).
All sixteen preceding isolated HA groups were also rerun on the same 276 product
hashes. External Spotify/CDN replies and the command-turn guard are explicit
fixtures; this proves neither real command effect authorization nor actual
provider/native/installed push behavior. Local SQL tests exercise real SQLite,
restart, cancellation, capacity, conflicts and terminal behavior with synthetic
source witnesses. Whole-source and exact-commit review, normal protected delivery
and separate original Final qualification remain release requirements.

## Remaining integration

A separately accepted actual grant/source/native-target/presentation lifecycle
must supply the native UUIDs and its independent permission/clock/restore proofs.
The API private R2 proposal describes prospective operations and pre-start once
ordering, not existing qualified factories or an actual owner. Local Activity
creation still needs an independently accepted real start intent and right before
any SDK attempt; a complete descriptor/B join follows the genuine activity ID.
No observer sample, ordinary pairing record, runtime boolean or self-reported key
can replace those sources. API deployment, HA installation and physical iPhone
widget/Activity receipt remain distinct acceptance gates.
