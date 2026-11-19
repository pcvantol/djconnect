# Pi rc.7 two-host producer qualification — 2 November 2026

## Scope and actual publication

Peter requested the prepared rc.7 qualification for both Pi instances, including
watchdog protection, followed by a protected handoff to the owning Pi lane.
The sole Core writer started from clean protected Core
`94ce3026fdfcca0bdfe6b1a3409f6df3921931c0`; native host verification completed
MATCH/exit0/onboarding4.5.6 before implementation. No Pi source was modified and
no remote Pi connection, service stop, claim, install or device effect occurred.

Root freshly downloaded the original provider release metadata, publication-run
metadata and both published rc.7 archives. Publication `40715314835` completed
SUCCESS at candidate `30c0f8278619a6a5e0ab24726e4c138d167e22c8`.
The wall-4inch archive is 3,469,293 bytes and wall-10inch 3,469,205 bytes; their
exact SHA256 values are in the V3 contract and V4 manifest schema.
Bounded in-memory archive inspection rejects duplicate/traversing paths and
non-file/directory members. All 84 packaged runtime files match original Git
blobs; installer, provisioning script and lock match; both contain the exact
shared wheel `4f7ad46ee743232474d28d9b7cff0a7435899dc706601fec6d290ee7e19cb66b`.
This fresh publication join does not repair or upgrade the preserved historical
absence of original CI ZIP/full durable coverage receipts.

## Producer behavior and executed checks

The new V3 contract selects V4 request and manifest explicitly, with two fixed
instance/profile/artifact tuples, unchanged inventory530220, pinned rc.7
publication, distinct producer/consumer Source and Final bindings, qualification
digests, native-runtime requirements and closed watchdog protection policy.
No operational manifest or approved example is committed.

The pure verifier executes **275 PASS** cases, including both targets, reordered
rows, every required field, unknown fields, duplicate/missing targets, swapped
profile/artifact, terminal newline, invalid dates, legacy rejection, external
producer/consumer pins and normative-hash joins. Nested policy mutation cases
reject removing any of the eight unit names or weakening guard/native values.
An explicit strict UTC/date parser is installed in the verifier; format checking
is never assumed from an optional library extra. The first local harness run
exposed the absent optional date checker, failed, and was retained; the checker
was made explicit before the passing runs. No schema was weakened.
Ruff checks of the verifier pass. Qualification uses an already existing isolated
Draft202012 validator environment; no dependency installation or paid call.

These are structural and reference-join checks. They are **not** Linux PID1,
watchdog effect, matching Pi consumer, installed-runtime or physical tests.
All earlier Pi normative files, inventory, historical operative manifests, all
302 HA product files and release inputs remain unchanged.

## Mandatory consumer gate and protected installation handoff

The existing Pi deployment workflow is still rc.6-specific. The independently
prepared native probe is explicitly non-integrated and cannot supply installation
readiness. Pi source may have changed since the published rc.7 runtime; preserve
the actual publication candidate rather than treating current Pi main as that
runtime. The new consumer requires normal own protected Source and separate
Final before a concrete V4 operative binding can be produced.

The owning Pi lane must qualify, in an isolated Linux environment, the real
transaction-owned PID1-loaded service ExecCondition fences for watchdog,
updater, maintenance and nightly reboot, and all four corresponding timers.
Initial absent/unknown/foreign/held state rejects before any effect. Durable
exclusive claim and parent fsync precede guard writes or client stop. Already
running competing services must be drained. Installer reload/re-enable must
never bypass loaded guards; CLI success for a skipped unit is not proof.

Preserve original scheduler states. Unknown result, lost connection, reboot or
changed guard ownership retains the hold; no automatic cleanup, restore, retry
or destructive rollback. Restore only owned guards after same-boot full native
venv plus authenticated MainPID/inode/startticks, all84-file and service stability
readback. Require a separate exact readonly smoke per instance; aggregate
partial remains partial. Root cannot supply these device receipts.

After protected Core Source and separate Final delivery, handoff consists of
their exact commits and qualification receipts plus the three normative hashes.
Pi first returns its matching consumer Source/Final and original guard/native
qualification evidence. Only then may a fresh explicitly human-scoped operative
V4 manifest and installation transaction be independently reviewed. This is a
producer handoff for the requested installation, not a claim that both physical
Pi devices have already been qualified or installed.
