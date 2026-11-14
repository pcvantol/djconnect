# Pi 4.0.3-rc.1 deployment handoff

The [publication evidence](PI_4_0_3_RC1_PUBLICATION_EVIDENCE.json) records
the published producer for the successor two-instance deployment contract.
It is a publication record. It contains no operational approval or dispatch
parameters. The existing RC6 and RC7 contracts and receipts remain historical.

## Published release

- Pi source repository ID `1267248532`, protected publication commit
  `5404184eb795c5eb16ef5565482c2313fca54082`.
- [Official publication run](https://github.com/pcvantol/djconnect-pi/actions/runs/43647710722)
  and [post-merge source qualification](https://github.com/pcvantol/djconnect-pi/actions/runs/43647584550).
- [Distribution release](https://github.com/djconnect-music-dj/djconnect-pi-releases/releases/tag/v4.0.3-rc.1)
  ID `445631616` in repository ID `1267500969`. It is a prerelease. The
  stable updater still resolves to release `440379959` (4.0.2).
- Both profile archives match the published SHA-256 and contain that exact
  source commit and their respective device profiles. Both contain the same
  wheel, with 107 files under `djconnect_pi/`. This is a packaged file count.
  Compare the eventual installed files with the verified wheel paths and bytes.

## Matching consumer

The successor request and operational manifest must select this exact
publication and the unchanged
[`PI_WALL_DEVICE_INVENTORY_V1.json`](PI_WALL_DEVICE_INVENTORY_V1.json).
Join the release and asset IDs, profile, SHA-256, publication workflow run,
consumer commit and qualification evidence. Revalidate the remote publication
before use because the GitHub release is mutable. Resolve GitHub repositories
by their numeric IDs so a rename cannot substitute another repository. Use the
original publication namespace as historical provenance. A successful
publication-access check is separate from provenance of a release.

Carry forward the [RC7 guard and restore behavior](PI_TWO_HOST_DEPLOYMENT_CONTRACT_V3.md):
durable per-instance claim before any effect, actual PID1 guards on the four
competing services, control of their four timers, drain before stopping the
client, and independent native smoke before restoring only the original
scheduling state. Unknown results retain the owned hold. The hold-only helper
does not provide install or restore qualification. Qualify the matching
consumer in isolated Linux with the successor package, including interpreter
Python 3.14.10 with GIL enabled, PySide6 6.12.0 and loaded Qt 6.12.0 readback.
An expected runtime version or a wheel inventory cannot attest an installed
process or replace the separate instance receipts.

## Execution route

The [private runner rehearsal](https://github.com/djconnect-music-dj/djconnect-pi-operations/actions/runs/43646621320)
proved macOS ARM64 and Python 3.14 on the Mac mini. The demo job has no
deployment credentials. Before connecting a runner to a device, verify the
exact reviewed workflow commit and allowed caller on the private route and
independently qualify each configured instance through a read-only readiness
run. The reviewed workflow identity must be enforced before credentials are
made available. The private repository's current plan does not offer branch
protection, so a private branch name alone cannot provide this identity.
