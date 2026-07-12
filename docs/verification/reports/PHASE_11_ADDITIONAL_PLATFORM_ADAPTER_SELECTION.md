# Phase 11 Additional Platform Adapter Selection

Status: RASPBERRY_PI_ADAPTER_SELECTED
Date: 2026-07-12

## Executive Summary

Phase 11 selected the Raspberry Pi Verification Adapter as the next platform
adapter phase.

Phase 10E-R3 and the Phase 10E retry qualified the first Apple executable
scenario set with non-blocking warnings. The remaining Apple warnings are
deferred scope and do not block selecting the next adapter.

Current decision:

```text
RASPBERRY_PI_ADAPTER_SELECTED
```

No Raspberry Pi adapter implementation started in Phase 11.

## Scope

Phase 11 evaluated the next adapter target from currently deferred platform
runtimes:

- Windows;
- Raspberry Pi;
- ESP32;
- Voice Endpoint;
- Website;
- Release.

The evaluation used the canonical Phase 11 criteria:

- scenario coverage need;
- available local tooling;
- runtime readiness;
- adapter boundary clarity;
- evidence value for Platform Baseline v1.0.

## Inputs

Canonical inputs reviewed:

- `BOOTSTRAP_CODEX_SESSION.md`
- `BOOTSTRAP_CODEX_VERIFICATION.md`
- `PROMPT_INDEX.md`
- `docs/meta/PHASE_COMPLETION_PROTOCOL.md`
- `docs/verification/00_VERIFICATION_VISION.md`
- `docs/verification/01_VERIFICATION_ARCHITECTURE.md`
- `docs/verification/02_SCENARIO_SCHEMA.md`
- `docs/verification/03_SCENARIO_CATALOG.md`
- `docs/verification/08C_VERIFICATION_PLANNING_ENGINE.md`
- `docs/verification/reports/PHASE_10E_APPLE_SCENARIO_COVERAGE.md`
- `docs/verification/reports/VERIFICATION_PLATFORM_BACKLOG.md`
- canonical scenarios under `verification/scenarios/`

## Candidate Assessment

| Candidate | Scenario coverage signal | Runtime readiness | Adapter boundary clarity | Baseline evidence value | Selection |
| --- | --- | --- | --- | --- | --- |
| Raspberry Pi | 28 scenarios reference Raspberry Pi or `pi.runtime`, including shared-room profile, Ask DJ shared context, capabilities, localization and Track Insight surfaces. | Good candidate for a thin first adapter using SSH/process/log/screenshot-style evidence, with hardware optional for the first implementation gate if a prepared target is not configured. | Clear: execute ambient client/runtime primitives only; backend behavior remains owned by Home Assistant scenarios. | High: proves the shared-room and ambient client platform model that Apple does not cover. | Selected |
| Windows | 86 scenarios reference Windows, but broad Windows coverage requires a Windows ARM64 VM/runtime strategy and native client artifact readiness. | Higher operator and VM dependency than Raspberry Pi for first post-Apple adapter. | Clear, but larger setup surface. | High, deferred until Windows runtime prerequisites are explicit. | Deferred |
| ESP32 | 37 scenarios reference ESP32, including hardware, BLE, OTA, mDNS, PTT and serial behavior. | Requires real hardware, serial/WiFi/BLE/OTA readiness and stricter destructive-operation controls. | Clear but hardware-heavy. | Very high, deferred until hardware lab gates are defined. | Deferred |
| Voice Endpoint | 18 scenarios reference Voice Endpoint runtime. | Depends on HA Assist/STT/TTS pipeline readiness and voice endpoint mapping configuration. | Clear, but many assertions remain backend/Assist-coupled. | Medium-high, best after another client adapter proves non-Apple shared runtime flow. | Deferred |
| Release | 18 release/localization scenarios reference release artifacts. | Strong static candidate, but release artifact inventory and release-v1.0 readiness remain broader prerequisites. | Clear static adapter boundary. | High near baseline certification, less valuable than Pi for current runtime coverage. | Deferred |
| Website | 10 localization scenarios reference website runtime. | Likely tractable, but product website source is a sibling repository and the coverage is narrower. | Clear static/browser boundary. | Medium; useful after runtime adapter breadth improves. | Deferred |

## Selection Rationale

Raspberry Pi is the best next adapter because it adds the first non-Apple rich
client runtime path while staying within a thin adapter boundary. It directly
targets ambient/shared-room behavior that is important to Platform Baseline
v1.0 and not proven by Apple simulator coverage.

The first Raspberry Pi adapter phase should focus on runtime qualification and
evidence primitives before broad product assertions:

- prepared target metadata;
- SSH or local-process reachability;
- client artifact or source checkout identity;
- runtime launch/stop;
- sanitized log collection;
- screenshot or UI evidence where available;
- privacy-safe environment snapshot.

The adapter must not own backend expectations, profile resolution rules, Ask DJ
semantics or Music DNA behavior. Those remain scenario and Home Assistant
backend responsibilities.

## Blocking Prerequisites

The Raspberry Pi implementation phase must fail closed before live mutation
unless it has explicit prepared runtime configuration. Required inputs should
include:

- `djconnect-pi` source checkout or packaged artifact path;
- prepared Raspberry Pi target JSON or local process target;
- SSH host/user/port configuration for live Pi execution, if using hardware;
- approved evidence directory outside production user data;
- log collection path or command;
- screenshot/UI evidence command when available;
- explicit non-production fixture state;
- no secrets printed in configuration, logs or evidence.

Physical Raspberry Pi execution should be opt-in. A mock/unit adapter path may
qualify adapter primitives before live hardware is available, but live runtime
proof must remain an explicit gate in the implementation phase.

## Repository Updates

Phase 11 generated the next implementation prompt:

```text
prompts/verification/PHASE_12_RASPBERRY_PI_VERIFICATION_ADAPTER.md
```

Phase 11 updated:

- `PROMPT_INDEX.md`
- `docs/verification/reports/VERIFICATION_PLATFORM_BACKLOG.md`
- `docs/verification/reports/VERIFICATION_PLATFORM_SCORECARD.md`

## Verification

Phase 11 is a selection and prompt-generation phase. Verification consisted of
repository validation after documentation and prompt updates.

```bash
/private/tmp/djconnect-phase9e-venv/bin/python -m tools.verification.cli validate
/private/tmp/djconnect-phase9e-venv/bin/python -m tools.verification.cli plan --strategy smoke --policy smoke --format json
/private/tmp/djconnect-phase9e-venv/bin/python -m pytest tests/verification
git diff --check
```

Results:

- Scenario validation passed: `validated 232 scenarios`.
- Smoke planning passed: 45 cases, including 1 Apple case and 44 Home
  Assistant cases, with `calls_adapters: false`.
- Verification tests passed: `125 passed`.
- `git diff --check` passed.

The host `python3` environment lacked `yaml`, so validation was rerun with the
existing verification virtual environment used by prior qualification phases.

## Known Issues

- Raspberry Pi live hardware availability is not proven in Phase 11.
- The first implementation phase must add the actual adapter, tests and
  scenario execution path; Phase 11 intentionally does not.
- Some existing Pi-relevant scenario YAML still lists Apple/Windows runtime
  requirements despite Pi wording. The Raspberry Pi implementation phase should
  add a Pi-specific runtime smoke scenario rather than rewriting shared
  scenario expectations merely to make planning green.

## Readiness

Phase 11 is complete when this report, the generated prompt, backlog, scorecard
and prompt index are current and repository validation passes.

## Next Phase

Execute only when explicitly prompted:

```text
Phase 12 - Raspberry Pi Verification Adapter
```

Do not begin Phase 12 automatically.
