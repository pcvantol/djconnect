# Finalize the retained latest contribution for large widgets

#### Repository Status

Source #1486 merged as `82d2d4eb692bc427c8d85d4cf646bacd557feb0c` from head
`f095847bad3b183bd65ca6c566ba0d9ceee521bb`. Independent main validation 42355939874
passed, including post-merge coverage. This separate Final changes five
documentation files.

#### Management Summary

The HA-dev debug build `d2e4099db344f0f38d482d20c72ce2c182a1d84a` includes the
original #1439 overlay. The independent reconstruction matched all 308 product
files, and 43 isolated HA checks plus 14 original Watch tests passed. The runtime
installation matches all 308 files. Configuration validation passed, paired session
and capabilities reads returned HTTP 200, database quick check returned ok, and
Profile defaults matched across the restart.

Runtime advertises projection v4 and separate retained-authorize and retained-read
routes. Both the existing widget registration and the explicit retained v4 grant
are required. Runtime reports that live push requires an enrolled operator purpose.

#### Roadmap Position

Generation 2 Product Development / Phase 1 Platform Qualification unchanged.
The retained-latest contract governs the WidgetKit background read.

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

Apple native consent, cold background read and physical widget display require
their own acceptance. Provider dispatch and the signed Watch preference chain
remain open.

#### Deferred Items

Golden remains execute:false. Existing WIP is preserved.

#### Repository State

Repository State: `MERGED_UNRECONCILED` until this separate Final merges and its
independent main checks pass.

#### Workspace State

Workspace State: `NOT_READY` until this Final is reconciled. See the
[qualification](docs/verification/PASSIVE_RETAINED_LATEST_20261106.md).

<!-- retained-widget-1486-finalization-end -->
