# Platform Release 3.3.0 — HACS Component 3.3.1

**Status:** Prepared for review; publication pending merge and target validation.

## Scope

This is the sole component patch within Platform Release 3.3.0: the Home
Assistant/HACS integration advances to `3.3.1`. It does not publish firmware,
change any other component version, alter the DJConnect client protocol,
introduce endpoints or change public API contracts.

## Included corrections

- Configured DJConnect entries register the existing HTTP views during their
  lifecycle setup, so `/status`, `/command` and `/voice` are available after
  Home Assistant starts.
- The private deployment no longer leaves a hidden `.djconnect-pre-*` backup
  under `custom_components`. Home Assistant discovers that directory as an
  integration and its duplicate manifest can otherwise shadow the active
  `djconnect` package, preventing config-flow registration.

## Validation before publication

- Full local unit suite: 1141 passed, 7 skipped.
- HACS metadata, route-registration and private-relay workflow contracts pass.
- Local Home Assistant lab runs integration version `3.3.1`, emits the
  `DJConnect HTTP endpoints registered` startup marker, and returns `401` JSON
  (rather than `404`) for unauthenticated POSTs to `/status`, `/command` and
  `/voice`.

## Required publication sequence

1. Merge the version-preparation pull request and require successful main CI.
2. Bind the immutable Home Assistant artifact to the HACS 3.3.1 Pi5 operation.
3. Deploy that exact artifact to `home_assistant_pi5` and run the separate
   live smoke.
4. Publish public GitHub release and tag `v3.3.1` from the verified main
   commit. HACS uses the latest public GitHub release tag as its remote
   version.
5. Refresh/redownload in HACS, restart Home Assistant, and confirm the HACS
   update presentation.

## Operational risk

The remaining risk is distribution-cache delay after public release. It does
not affect the verified local lab or the Pi5 deployment; HACS may require a
manual refresh/redownload before displaying the new tag.
