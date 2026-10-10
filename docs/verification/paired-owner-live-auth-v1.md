# Paired owner live auth v1 qualification

Assignment: `DJC-CORE-PAIRED-LIVE-AUTH-V1-20261010`.
Actual base: `ffaa4df0ea1a184669622a6c98d9f0f5aae7a4f2`.
Sole Core branch: `codex/paired-live-auth-v1`.

The before-proof used real HA 2026.10 pairing, ConfigEntries and Store.
Pairing minted and persisted the existing device token; the Apple-expected
`POST /api/djconnect/v1/websocket/session` returned 404 and native HA websocket
rejected the device token as HA authentication. No HA user credential was
issued or used to replace ordinary pairing.

The correction is the thin, versioned paired owner transport described in
[the producer contract](../product/PAIRED_OWNER_LIVE_CONTRACT_V1.md). It calls
existing owner Broadcast subscribe/recover handlers. There is no new Runtime,
Broadcast Engine, backend, admin token issuer or client intelligence.

## Evidence

Committed sanitized before/after receipts and content pins are in
`examples/client_contracts/paired_owner_live_v1/`. The acceptance receipt has
SHA256 `ef5ca18183e3742b4e15b4375b2525ce3028a447c6c75238fc36204b8c342137`.
All 131 recorded integration source hashes matched the frozen candidate.

The own lab used the already available HA image, network none, no published
ports, one CPU and 768 MiB memory. It used fresh synthetic configured slots,
Profiles and music, real HA AuthManager/HTTP router/ConfigEntries/Store and
actual DJConnect pairing/Profile Store/persistence/Session/Broadcast handlers.
No Apple or HA-dev configuration, identity, credentials or lab was reused.

57 sanitized transport receipts passed: actual pairing/token persistence,
capability discovery, paired auth, owner snapshot, Runtime playback update,
cursor recovery, wrong/missing token or identity/version, forged Profile,
other Session, invalid cursor, prohibited HA action, URL query rejection,
auth timeout, Profile switch and rotation withdrawal, stale reconnect and
Runtime end. The unshortened 300-second lease really elapsed and returned
`auth_expired`, preserving the active Session. Separate fault injection wrapped
the real resolver and stalled pending setup with a short test-only deadline;
auth was not replaced. Rotation during awaited resolution was rejected, and
cancellation removed the pending subscription.

Local checks: 1,684 unittest tests passed (seven existing skips), 172
verification tests passed, Ruff passed, required medium-severity Bandit passed
and the committed AI-development projection validated. Default Bandit retained
21 existing Low findings; no Medium/High or new paired adapter finding.

Independent read-only review found and fixed stale authority across awaits,
hard-deadline enforcement, cancellation cleanup during both snapshot and cursor
setup, exact integer protocol versions and strict known-device binding. The
reviewer verified all ten early handoff files against the immutable archive,
reported no unresolved findings and independently passed 14 focused tests.
The archive pin is `648496f3c218305323c752a632a086cfad97fb15f8f0c9d9126ae92fc319f58b`.

## Contract preservation and delivery boundary

Existing Apple HTTP conversation/voice/history/search, native HA fast-path,
Cast status v1, Pi app and player contracts are preserved. This adapter has no
chat/archive endpoint or playback command. It conveys the same active Session
Broadcast and native Moment projection through the existing handlers.
Golden product scenarios relate indirectly: transport access does not change
planning, knowledge eligibility, Moment selection or playback; existing product
regressions plus actual owner Session/Broadcast delivery test the affected
boundary without claiming fresh provider or hardware qualification.

There are no new user-facing strings or dependencies. The five-language product
resources remain unchanged. Runtime/dependency upgrades were deliberately
excluded from this minimal auth correction; normal CI dependency audit remains
available. No release version, workflow, runner or service policy was changed.

This record qualifies producer software and isolated ordinary paired transport.
It does not claim installed HA, physical Apple, TLS deployment, Cast/LG or
hardware acceptance. Apple owns the explicit route/auth consumer change and
native acceptance. Installation requires the target-specific grant. The early
contract and exact receipts were transferred to Apple #87 comments
6095514984 and 6095547325. Protected delivery and the separate Finalization
reconcile the exact source/main/package records; source merge alone does not
close installed or native acceptance.
