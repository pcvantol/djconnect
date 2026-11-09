# Finalize WidgetKit machine access for HA-dev

#### Repository Status

Core #1528 merged as `f2f9c2937b981597592ad4e7fafa6c6f8d76f6cc`
from `f2c843b8314eaa4dd5f2befcc97b1c579257d90f`. Trusted Delivery
qualification passed in run 42405654864. All validation and coverage jobs
passed on Core main in run 42405997137.

#### Management Summary

Core startup can load an operator-mounted, owner-only credential for the
dedicated WidgetKit HA-dev Access origin. The credential expires at its
original deadline and is retired when the service shuts down. Issuance
still requires a separately enrolled owner and the original paired request.

The full source suite accounted for 4,760 tests with 11 skips. In isolated
Home Assistant 2026.10.0, all 44 scenarios passed and the startup probe
loaded and retired a synthetic credential. The HA-dev debug archive from
the merge contains 309 verified files. An independent reconstruction matched every file. The original #1439
patch changes four of those files. The running HA-dev instance was kept on its existing
build during an active session. A separate Docker container start probe
timed out on the first attempt and exited zero on a bounded retry.
The running HA instance remained available.

#### Roadmap Position

Generation 2 Product Development / Phase 1 Platform Qualification.
Native push remains under the existing v4 and signed preference contracts.

#### Rolling Horizon (Execution Horizon — Next 5 Planned)

Derived afresh from docs/roadmap/v1/djconnect-platform-v1.json and CATALOGUE.md;
producer edges SETTINGS-4/6/8/10/12 retain the same prerequisites. These entries
do not issue prompts or grant execution/native dispatch authority.

1. **SETTINGS::APPLE::EDITOR — One Jouw DJ editor and shared Session quick controls**: Planned / NOT_ISSUED; direct prerequisite SETTINGS::CORE::PRODUCER Completed. Execution Rationale: canonical settings follow-through order; exact consumer acceptance and a separate issued prompt still gate execution.

2. **SETTINGS::PI::ADOPTION — Pi allowed shared Session settings and legacy disposition**: Planned / NOT_ISSUED; direct prerequisite SETTINGS::CORE::PRODUCER Completed. Execution Rationale: canonical settings follow-through order; exact consumer acceptance and a separate issued prompt still gate execution.

3. **SETTINGS::ESP32::ADOPTION — ESP32 Assist/voice/settings compatibility and legacy disposition**: Planned / NOT_ISSUED; direct prerequisite SETTINGS::CORE::PRODUCER Completed. Execution Rationale: canonical settings follow-through order; exact consumer acceptance and a separate issued prompt still gate execution.

4. **SETTINGS::VIBECAST::COMPAT — Shared renderer allowed Session fields without Profile preferences**: Planned / NOT_ISSUED; direct prerequisite SETTINGS::CORE::PRODUCER Completed. Execution Rationale: canonical settings follow-through order; exact consumer acceptance and a separate issued prompt still gate execution.

5. **SETTINGS::WEBSITE::COPY — Six-parameter scope/help and obsolete settings copy audit**: Planned / NOT_ISSUED; direct prerequisite SETTINGS::CORE::PRODUCER Completed. Execution Rationale: canonical settings follow-through order; exact consumer acceptance and a separate issued prompt still gate execution.

#### Blocked Items

The live WidgetKit pilot needs an Access credential placed directly into
HA-dev custody and the exact operator-signed enrollment. API #228 merged
as `2274d2875c2ea5c324427c8014ade0c05b0fbead`. The isolated Worker stays
closed while the live prerequisites are pending. Provider acceptance and
physical display on Mac, iPad and iPhone remain unverified. Live Activity
and Watch Moment have separate delivery and device checks. #1439 remains
pending the independently authorized signed Watch preference chain.

#### Repository State

`MERGED_UNRECONCILED` until this Final merges and its main checks pass.

#### Workspace State

`NOT_READY` until the local cleanup record is complete. The source patch,
archive receipts and existing rollback copies are retained.

<!-- widget-access-1528-finalization-end -->
