# Phase 12E-R Raspberry Pi Product Scenario Mapping Remediation

Status: RASPBERRY_PI_PRODUCT_SCENARIO_MAPPING_QUALIFIED
Date: 2026-07-12

## Executive Summary

Phase 12E-R remediated and executed the Phase 12E warning that broad Raspberry
Pi product coverage was not explicitly mapped to the Raspberry Pi adapter.

Current decision:

```text
RASPBERRY_PI_PRODUCT_SCENARIO_MAPPING_QUALIFIED
```

The canonical smoke planner now exposes multiple Pi-adapter executable cases,
including shared-room Profile, Ask DJ shared context, capability discovery and
Track Insight boundary coverage. Scenario expected behavior remains owned by
the Scenario Catalog and Scenario Engine; the Raspberry Pi adapter still owns
only runtime primitives. The selected Phase 12E-R Pi product scenario set
executed through the Scenario Engine and Raspberry Pi adapter with PASS
evidence. A follow-up full Pi smoke execution also passed all 9 Pi adapter
cases now exposed by canonical smoke planning.

## Remediation

Changes:

- Added Pi runtime metadata to `PROFILE-010` and `ASKDJ-010`, which already
  described Pi behavior in their canonical titles and expected behavior.
- Updated the Planning Engine to prefer the Raspberry Pi execution surface when
  a scenario explicitly declares `pi.*` or `raspberry_pi.*` runtime
  capabilities.
- Updated the Scenario Engine so shared HA/Pi product scenarios execute Pi
  runtime primitives when routed through the Raspberry Pi adapter.
- Updated the execution environment so an already-qualified local Home
  Assistant verification lab does not fail startup preflight merely because its
  own host port is listening.
- Added regression tests for shared Pi scenario planning and Scenario Engine
  primitive selection.

No backend expectations, product assertions or adapter-owned behavioral rules
were moved into the Raspberry Pi adapter.

## Planning Evidence

Focused Pi product plan:

```text
scenarios: PROFILE-010, CAPABILITIES-005, ASKDJ-010, TRACKINSIGHT-005
by_platform: Raspberry Pi 4
adapter: raspberry_pi for all 4 cases
required_hardware: pi
```

Full smoke plan after remediation:

```text
by_platform: Apple 1, HA 35, Raspberry Pi 9
case_count: 45
scenario_count: 51
```

The Phase 12E warning stated that canonical smoke planning exposed only
`PI-001` as Pi-adapter executable. That is no longer true.

## Scenario Execution

Focused remediation execution:

```text
PROFILE-010
CAPABILITIES-005
ASKDJ-010
TRACKINSIGHT-005
```

Result:

```text
PASS
```

Run:

```text
djv-20260712T093801Z-b5be5b3197
```

Summary:

- scenarios executed: 4
- pass: 4
- fail: 0
- warning: 0
- skipped: 0
- total execution time: 19.85 seconds

Evidence directory:

```text
artifacts/verification/evidence/djv-20260712T093801Z-b5be5b3197/
```

Full Pi smoke execution:

```text
ASKDJ-010
CAPABILITIES-001
CAPABILITIES-002
CAPABILITIES-003
CAPABILITIES-004
CAPABILITIES-005
CAPABILITIES-006
CAPABILITIES-007
CAPABILITIES-008
```

Result:

```text
PASS
```

Run:

```text
djv-20260712T094155Z-cf11275694
```

Summary:

- scenarios executed: 9
- pass: 9
- fail: 0
- warning: 0
- skipped: 0
- total execution time: 46.78 seconds

Evidence directory:

```text
artifacts/verification/evidence/djv-20260712T094155Z-cf11275694/
```

Environment gates:

- exact-SHA CI passed for SHA `1dd8385b1c0425ff9b1794ddb811d9e40560fe6a`;
- local HA lab was recreated for the current branch/SHA and qualified;
- existing qualified HA lab runtime was accepted without requiring the lab port
  to be free;
- Raspberry Pi runtime target `rbpi-djconnect.local` executed via SSH.

## Verification

Commands:

```bash
python -m unittest tests.verification.test_planning_engine tests.verification.test_raspberry_pi_adapter
python -m tools.verification.cli validate --scenario-id CAPABILITIES-005 --scenario-id PROFILE-010 --scenario-id ASKDJ-010 --scenario-id TRACKINSIGHT-005
python -m tools.verification.cli plan --scenario-id CAPABILITIES-005 --scenario-id PROFILE-010 --scenario-id ASKDJ-010 --scenario-id TRACKINSIGHT-005 --strategy smoke --policy smoke --format json
python -m tools.verification.cli plan --strategy smoke --policy smoke --format json
python -m tools.verification.cli lab ha recreate --allow-destructive
python -m tools.verification.cli lab ha doctor
DJCONNECT_VERIFICATION_PI_TARGET_JSON='...' DJCONNECT_VERIFICATION_PI_ALLOW_SSH=1 DJCONNECT_VERIFICATION_PI_EVIDENCE_DIR=/private/tmp/djconnect-phase12e-r-pi/evidence python -m tools.verification.cli --raspberry-pi-adapter execute --scenario-id PROFILE-010 --scenario-id CAPABILITIES-005 --scenario-id ASKDJ-010 --scenario-id TRACKINSIGHT-005
DJCONNECT_VERIFICATION_PI_TARGET_JSON='...' DJCONNECT_VERIFICATION_PI_ALLOW_SSH=1 DJCONNECT_VERIFICATION_PI_EVIDENCE_DIR=/private/tmp/djconnect-phase12e-full-pi/evidence python -m tools.verification.cli --raspberry-pi-adapter execute --scenario-id CAPABILITIES-001 --scenario-id CAPABILITIES-002 --scenario-id CAPABILITIES-003 --scenario-id CAPABILITIES-004 --scenario-id CAPABILITIES-005 --scenario-id CAPABILITIES-006 --scenario-id CAPABILITIES-007 --scenario-id CAPABILITIES-008 --scenario-id ASKDJ-010
```

Results:

```text
15 unit tests passed.
validated 4 scenarios.
focused plan selected 4 Raspberry Pi adapter cases.
full smoke plan selected 9 Raspberry Pi adapter cases.
local HA lab qualified for the current branch/SHA.
4 Phase 12E-R Pi product scenarios passed through the Raspberry Pi adapter.
9 full Pi smoke scenarios passed through the Raspberry Pi adapter.
```

The first two execution attempts failed closed before scenario execution:

- sandboxed execution could not prove GitHub CLI, Docker or host preflight;
- escalated execution initially found a stale Phase 9L HA lab container from a
  different source SHA;
- after recreating the lab, the preflight still blocked because the qualified
  lab's own host port was listening.

The execution environment was corrected to accept an already-qualified HA lab
runtime before applying startup port-free preflight. The rerun then executed all
selected scenarios and passed.

## Qualification Decision

Phase 12E-R returns:

```text
RASPBERRY_PI_PRODUCT_SCENARIO_MAPPING_QUALIFIED
```

The Phase 12E mapping warning is resolved and the first broader Pi product
scenario batch is qualified. The next platform step may select the next
adapter.
