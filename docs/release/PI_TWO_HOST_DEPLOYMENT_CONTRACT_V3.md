# Pi rc.7 two-host deployment contract V3

Status: versioned producer contract. A conforming schema specimen is not approval,
matching-consumer qualification, installation authority or physical acceptance.
This version selects request V4 and operational manifest V4 explicitly. There is
no rc.6 fallback or auto-detection. All earlier contracts, schemas, manifests and
original receipts retain their own historical scope and bytes.

## Published candidate and two identities

Candidate `30c0f8278619a6a5e0ab24726e4c138d167e22c8`, publication run
`40715314835`, is the existing `4.0.0-rc.7` release. It is distinct from the
later Pi consumer source and its separate documentary Final. Do not silently
substitute newer Pi main runtime files into these published packages.

| Deployment instance | Device profile | Published asset SHA256 |
| --- | --- | --- |
| wall-4inch | pi-zero-2w-arm64 | d738f636d2ccbf35b2d10e705b5bf4091630ad394d25cc1d3755515d453fe55e |
| wall-10inch | pi5-arm64 | dd48d4fd165d8538d10c29c2ebc2168b165520b015015d3d9324ec39a236a0a7 |

The unchanged `PI_WALL_DEVICE_INVENTORY_V1.json` digest is
`530220ee38f6ccbcc824a78331b9dd89f236a5fa6ede12ebf7899dac83ff50c0`.
Its endpoint reference, hostname, architecture, model and host-key pins must
resolve to the selected instance before any effect. A generic target name is
not a physical identity. No guessed address, key, Profile or readiness is valid.
Both assets contain the shared wheel
`4f7ad46ee743232474d28d9b7cff0a7435899dc706601fec6d290ee7e19cb66b`.

## Admission and durable once boundary

The owning Pi implementation must qualify this exact contract under normal
protected Source and separate Final delivery before Core publishes any V4
operative manifest. The manifest binds actual producer Source/Final, three
normative hashes, consumer Source/Final, qualification receipt digests, guard
helper digest, original release bytes and fresh independently checked human
scope. Structural `APPROVED` fields are not authority. Neither synthetic values
nor the existing non-integrated rc.7 runtime probe satisfy these bindings.

For each target independently, join all request fields to exactly one target
and artifact row, inventory, original approved manifest and consumer pins.
Reject unknown properties, wrong versions, swapped profiles, altered hashes,
expired or mismatched authority and any preexisting transaction claim.
Read-only readiness must establish the actual current boot, root-owned release,
configuration identity, all eight loaded units and absence of foreign guards.
An initially absent or unknown unit, masked/held state without separately
reviewed recovery authority, configuration/boot drift or foreign guard rejects
before claim creation, guard writes, unit stops or any other effect.

Before the first effect, reserve an exclusive durable once claim for the exact
instance/manifest/transaction, fsync its content and every newly created parent
entry. Never consume another instance's claim, refund a claim, reset it, replay
an old grant or infer availability from historical claim absence. Readiness
must be revalidated at the effect boundary. Use new rc.7 transaction and smoke
identifiers; rc.6 claims and failed physical recoveries remain untouched.

## Mandatory watchdog and competing-task protection

Guard contract: `pi-rc7-pid1-transaction-guard-v1`.
The complete closed unit inventory is:

| Triggered service | Timer |
| --- | --- |
| djconnect-watchdog.service | djconnect-watchdog.timer |
| djconnect-updater.service | djconnect-updater.timer |
| djconnect-maintenance.service | djconnect-maintenance.timer |
| djconnect-nightly-reboot.service | djconnect-nightly-reboot.timer |

After the durable claim and before stopping the client, the consumer must:

1. Capture each unit's original enabled/disabled, active/inactive and held state,
   unit fragment/drop-ins, boot identity and guard ownership. Preserve original
   disabled/inactive states; an installer enabling timers does not change them.
2. Install transaction-owned, root-owned, content/inode/hash-bound **service**
   ExecCondition guards outside release paths replaced by the installer. A
   timer has no service ExecCondition: fence its actual triggered service and
   control its scheduling separately. Runtime mask, file presence or CLI exit
   success alone is insufficient.
3. Reload PID1, read its actual loaded ExecCondition, fragment and drop-in paths
   and hashes for all four services, and verify the timer-to-service mapping.
   Qualify denied starts from the loaded condition result and process state;
   systemd can return success for an ExecCondition skip. No unguarded reboot,
   update or maintenance effect may occur.
4. Drain all already-running competing service processes/cgroups under the
   durable guards. A new ExecCondition does not stop an existing process.
   Establish that none can reboot or rewrite the release before client stop.
5. Prove in isolated Linux qualification that hostile installer daemon-reload
   and timer re-enable cannot remove or bypass the guards. The published
   installer does both. Re-read the actual loaded guard after installer steps;
   do not introduce an unguarded interval or rely on a later check to undo an
   earlier effect. Fail closed on any guard, inode, boot or ownership change.

Only the owning consumer performs these actions. The Core verifier below is
pure schema/semantic evidence and cannot establish any PID1 behavior.

## Install, native readback and restore

The consumer must preserve each target's complete prior release, configuration
and native runtime independently before replacement. Do not copy authority,
configuration or install results between hosts. No silent install fallback.

Before restoring scheduling, join all 84 installed product files to the
published candidate; inspect the actual installed venv and root-owned base:
Python `3.14.9`, GIL enabled, PySide6 and loaded native Qt `6.12.0`.
A version from the invoking shell is insufficient. Separately authenticate
PID1 MainPID, executable inode, start ticks and unchanged process identity
before/after inspection, plus current release/configuration and boot. Do not
read process environment, command lines, tokens or private session data.
A temporary probe process does not prove the actual running client.

Require stable client/API service state and a separate per-instance readonly
`pi-rc7-instance-native-readback-v1` smoke bound to the exact transaction,
installed release, identity and original deployment receipt. Logs or model
results cannot stand in for the actual device smoke or visible acceptance.

Restore only this transaction's still-owned exact guards, only after same-boot,
full native/readback success and ownership checks. Restore original scheduling
states exactly, including originally disabled/stopped units. If connection is
lost, the device reboots, readiness becomes UNKNOWN, ownership changes or the
result is incomplete, retain the hold and record uncertainty. Never perform
automatic destructive rollback, restore timers, remove a foreign guard, reset
claims or retry. Recovery requires a new concrete review and authority.

Aggregate success requires two original successful instance receipts and two
separate matching smokes. One success plus one failure remains partial. Core
Source qualification, Pi consumer qualification, installed state and physical
user acceptance are separate records.

## Protected handoff and remaining gates

`PI_TWO_HOST_DEPLOYMENT_REQUEST_V4.schema.json` and
`PI_TWO_HOST_OPERATIONAL_MANIFEST_V4.schema.json` are canonical producer formats.
`scripts/verification/verify_pi_two_host_rc7_contract.py` checks schema boundaries
and reference joins without writing an operational manifest or contacting hosts.
The Pi lane must implement/qualify the real guard transaction and wire the
existing non-integrated native probe before requesting an operative binding.

The installation handoff must identify protected producer Source and separate
Final, exact normative hashes, original qualification evidence and these open
consumer/device gates. Only after protected matching-consumer Source/Final and
original isolated PID1 evidence may a fresh human-scoped operative manifest be
reviewed and delivered. No dispatch, device access or installation follows from
this producer-only document.
