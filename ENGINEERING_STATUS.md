# DJConnect Engineering Status

**Status:** Operational handoff
**Updated:** 2026-07-19

## Current engineering increment

Operational burn-in process establishment is merged. PR
[#200](https://github.com/pcvantol/djconnect/pull/200) merged as
`8c1dcc40f6dd4ace8753bdb904b906ee1a0821ea`; it defines the reusable,
seven-day evidence-only observation procedure for the exact Internal Release
scope. It does not assert that burn-in evidence has been collected or that
Platform Release 3.3 is certified. The current documentation-only increment
establishes the mandatory Release Certification process that follows burn-in.

## Current engineering program

DJConnect Product Development remains the primary program. The P2 Platform
Release Observatory is design complete and retained in the Platform Evolution
implementation backlog. Platform Release 3.3 remains separate temporary
operational work.

## Current repository truth

PR [#162](https://github.com/pcvantol/djconnect/pull/162), Innovation
Engineering Method Evolution, is merged as
`9ff42a572ae35586cf89d2febdcffab6fb835a58`; its remote branch is absent. The
canonical Engineering Method now includes the lightweight Innovation
Engineering mode. This does not change Observatory priority, its read-only
design boundary or the Release 3.3 authorization model.

All nine required target-scoped operations for Internal Release 3.3 have
deployment and separate smoke evidence. The final Home Assistant operation
uses candidate `30978862a2889bbf35925914e9e2fdb1a707f8a6`, immutable artifact
`internal-ha-30978862…tar.gz` and SHA-256
`03231ba00c3e21188e70efa3ec332042a942ba118e9663c424545f62fbe4c224`.
Deployment run [29683604435](https://github.com/pcvantol/djconnect/actions/runs/29683604435)
and smoke run [29683901389](https://github.com/pcvantol/djconnect/actions/runs/29683901389)
succeeded. The smoke proves installed integration version `3.3.0`, an
authenticated Home Assistant WebSocket handshake and bounded Core health.
See `docs/release/PLATFORM_3_3_HOME_ASSISTANT_DEPLOYMENT_COMPLETION.md`.
The failed pull-request-only HACS job was classified as a branch-cleanup race:
it attempted to resolve the deleted review branch after the merge. The
authoritative `main` run passed, so no workflow or integration remediation is
required.

PR [#185](https://github.com/pcvantol/djconnect/pull/185) remediates the
separate active Home Assistant runtime incident: the configured-entry lifecycle
now independently registers the existing HTTP views, and future smoke runs
fail closed if `/status`, `/command` or `/voice` returns `404`. The merged main
validation passed. A new exact artifact binding and target deployment remain a
separate explicitly authorized operational action.

## Known blockers and limitations

- Internal Release target deployment qualification is complete and the
  Operational Burn-in process is established, but burn-in evidence and a
  Release Certification decision remain separate operational actions.
- The proposed Observatory has no implementation. Its future evidence timing
  contract, collector/persistence and dashboard are independent increments.

## Deferred work

- Perform the three separately authorized Observatory delivery increments in
  their documented order when priority and authorization permit.
- Do not execute burn-in, Release Certification or Public Distribution
  automatically; each remains an evidence-backed, separately authorized
  operational action.

## Recommended next prompt

After this process increment, no release operation starts automatically. The
next eligible Release 3.3 action is collection of the declared burn-in evidence
for the exact bound Internal Release scope, followed by a separately authorized
certification decision.
