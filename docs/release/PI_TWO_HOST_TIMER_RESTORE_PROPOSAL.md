# Pi two-host timer restoration proposal

This proposal specifies a shared release boundary for the guarded timer
restoration in the [Pi 4.0.3-rc.1 handoff](PI_4_0_3_RC1_DEPLOYMENT_HANDOFF.md).
The existing RC7 contract and Pi hold-only implementation keep their current
scope. This experiment establishes no deployment, restoration, host readiness
or acceptance authority.

## Commit boundary

Each instance transaction has its own durable claim and root-controlled permit
path. Install all four service guards before stopping competing work. All four
guards consult the same permit from the beginning, including after an
installer daemon reload. A missing, invalid or wrong-boot permit denies
service execution. Guard ownership, exact loaded conditions, timer mappings,
release identity and boot must be checked independently on each instance.

After separate native smoke passes, restore the captured enabled and active
states of the four timers while service execution is still fenced. Verify
those states and the original guard identities again. Do not use
`enable --now` as a substitute for restoring the two states separately.
Only then publish one same-boot permit with a filesystem operation that makes
it visible atomically to the four guards. Sync the file before publication and
the containing directory before reporting success. Do not remove guard files
one at a time to release the services.

Loss of acknowledgment before a visible permit leaves the guards in force.
If an acknowledgment is lost after a visible permit, read back the exact
transaction and loaded PID1 state. No second release or retry follows from an
incomplete client response. Once visible, service execution may occur even
if the caller has not received a reply. A reboot or a missing or mismatched
receipt cannot be interpreted as a successful return to service.

The producer and consumer still need a separate decision for guards left
after a confirmed release, crash or reboot, and for originally active
competing services. Keep the existing hold semantics until those lifecycle
cases and the exact permitted native smoke are qualified. No permit may be
published solely because a timer or installer operation returned success.

## Isolated PID1 result

A fresh Debian ARM64 VM ran four harmless fixture services and their timers.
The services used one boot-ID-checked permit, and each fixture service wrote
an isolated effect marker when admitted.

- PID1 reported a skip and no effect for all four services before release,
  after the staging process exited midway through timer restoration, after
  daemon reload, and with a wrong-boot permit.
- After the permit was atomically published and the publisher exited without
  acknowledgment, exact readback observed the committed boot marker.
- The four fixture timers retained the respective enabled/active,
  enabled/inactive, disabled/active and disabled/inactive states. Explicit
  starts confirmed all four fixture service bodies could run after commit.

Fixture script SHA-256
`cd1d90d122112436067645cc7ed2cb05c6538221f1aa52c0356b8abbb23c22fa`.
Receipt SHA-256
`029bc6e9710172454b93fc77922040ba5d31bfdcd9d8a5d1a76a7b9294077ddc`.

The trial used fixture units and explicit service starts. The matching Pi
consumer still needs qualification with actual Pi service definitions,
timer-triggered starts, interrupted writes and reboot reconciliation,
including proof that the reviewed private workflow cannot access credentials
before its identity is established.
