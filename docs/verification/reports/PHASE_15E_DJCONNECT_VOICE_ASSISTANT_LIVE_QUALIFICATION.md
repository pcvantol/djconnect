# Phase 15E DJConnect Voice Assistant Live Qualification

Status: `VOICE_ASSISTANT_LIVE_QUALIFICATION_BLOCKED`

Date: 2026-07-12

Branch: `main`

Repository SHA: `af8228bc7c933df61cab47d4105002839ba65fb3`

Verification Runtime: `1.1.0`

## Executive Summary

Phase 15E attempted to qualify the DJConnect Voice Assistant Verification
Adapter against a live Home Assistant Assist / DJConnect Conversation Agent
runtime.

Qualification decision:

```text
VOICE_ASSISTANT_LIVE_QUALIFICATION_BLOCKED
```

The phase did not reach live Voice Assistant mutation. The Verification
Execution Environment failed closed because the local Home Assistant lab was
not proven safe for the current repository SHA. A stale Docker Home Assistant
container from earlier lab work was still bound to port `18123`, and Docker
runtime discovery reported that the running lab source SHA did not match the
current repository SHA.

## Scope

Executed:

- clean-session bootstrap and Phase 15E prompt review;
- Voice Endpoint smoke planning for `VOICE-001`;
- focused Voice Assistant adapter and planning regression tests;
- live execution attempt through the Scenario Engine and `voice_endpoint`
  adapter path;
- evidence collection for the fail-closed live gate;
- completion protocol review.

Out of scope and not executed:

- Phase 16 Cross-Platform Qualification;
- new Voice Assistant, Ask DJ, Assist, STT or TTS product behavior;
- ESP32, Apple, Raspberry Pi or Windows adapter changes;
- Software Assurance implementation;
- Platform Baseline certification.

## Verification

Focused adapter and planner regression tests:

```bash
python -m pytest tests/verification/test_voice_assistant_adapter.py tests/verification/test_planning_engine.py -q
```

Result:

```text
16 passed in 7.03s
```

Voice Endpoint smoke planning:

```bash
python -m tools.verification.cli plan --scenario-id VOICE-001 --strategy smoke --policy smoke --format json
```

Result:

```text
adapter: voice_endpoint
platform: Voice Endpoint
scenario: VOICE-001
selected lab profile: ha-assist
external resource: voice_endpoint.runtime
required secret: ha.access_token
```

Live execution attempt:

```bash
python -m tools.verification.cli --voice-assistant-adapter execute --scenario-id VOICE-001
```

Result:

```text
execute: 1 of 1 tests executed, status FAIL (1 FAIL), total 0.00s
```

The failure happened at mandatory environment gates before live runtime
mutation.

## Evidence

Primary evidence:

- live gate evidence:
  `artifacts/verification/evidence/djv-20260712T154526Z-1d6103fdd3/`;
- clean `ha-assist` lab follow-up evidence:
  `artifacts/verification/evidence/djv-20260712T155121Z-61f8232037/`;
- run summary:
  `artifacts/verification/evidence/djv-20260712T154526Z-1d6103fdd3/summary.json`;
- qualification metadata:
  `artifacts/verification/evidence/djv-20260712T154526Z-1d6103fdd3/qualification.json`;
- environment snapshot:
  `artifacts/verification/evidence/djv-20260712T154526Z-1d6103fdd3/environment.json`;
- execution plan:
  `artifacts/verification/evidence/djv-20260712T154526Z-1d6103fdd3/execution-plan.json`.

Important recorded gate state:

```text
host_preflight: FAIL
ha_docker_discovery: FAIL
github_ci_status: WARNING
scenario_execution_started: false
```

The running Docker Home Assistant lab reported:

```text
container: djconnect-verification-ha
port: 18123
lab profile: ha-profile
lab source SHA: 57bd7d45dc006f0b4411fc2a443c2e9123321061
current repository SHA: af8228bc7c933df61cab47d4105002839ba65fb3
source_matches_sha: false
safe_for_verification: false
```

No Voice Assistant target JSON was present in the environment when checked:

```bash
env | rg '^DJCONNECT_VERIFICATION_(VOICE_ASSISTANT|HA|LAB|EVIDENCE|PARALLEL)'
```

Result:

```text
no matching environment variables
```

Follow-up clean-lab remediation was executed after operator direction that
Voice Assistant live qualification must always start from a clean HA lab:

```bash
python -m tools.verification.cli lab ha destroy --allow-destructive
DJCONNECT_VERIFICATION_LAB_PROFILE=ha-assist python -m tools.verification.cli lab ha fresh
rm -f artifacts/verification/lab/home_assistant/.secrets/ha_lab_auth.json
DJCONNECT_VERIFICATION_LAB_PROFILE=ha-assist python -m tools.verification.cli lab ha bootstrap-auth
DJCONNECT_VERIFICATION_LAB_PROFILE=ha-assist python -m tools.verification.cli lab ha doctor
```

Result:

```text
LOCAL_VERIFICATION_LAB_QUALIFIED
profile: ha-assist
source_sha: af8228bc7c933df61cab47d4105002839ba65fb3
safe_for_verification: true
source_matches_sha: true
github_ci_status: CI_PASS
```

The follow-up Voice Endpoint smoke run against the clean qualified lab still
failed because no Voice Assistant target was configured:

```text
run: artifacts/verification/evidence/djv-20260712T155121Z-61f8232037/
scenario: VOICE-001
state: FAIL
error: VoiceAssistantTargetUnavailable
failed primitives: validate_target_identity, collect_assist_metadata, probe_voice_endpoint
```

During an additional sidecar check, the initial `ha-assist` Piper container was
found exited because `docker/verification/compose.piper.yaml` did not provide
Piper's required `--voice` argument. The verification compose fragment was
updated to provide a default voice:

```text
DJCONNECT_VERIFICATION_PIPER_VOICE default: en_US-lessac-medium
```

After another clean rebuild, Home Assistant, Whisper and Piper were all
running. The HA lab then passed source, safety, REST and token checks, but the
Home Assistant websocket probe timed out. This means the environment improved
from stale-lab failure to a narrower lab readiness blocker:

```text
containers: homeassistant running, whisper running, piper running
rest: PASS
token: PASS
safe_for_verification: true
websocket: FAIL timed out
```

## Investigation

Classification:

```text
execution environment issue / live lab readiness
```

Owner:

```text
Verification Execution Environment / local Home Assistant Assist lab
```

Reason:

- the initial Docker Home Assistant lab was stale for the active repository
  SHA;
- port `18123` was initially occupied by the existing Docker Home Assistant
  listener;
- the initial discovered lab profile was `ha-profile`, while `VOICE-001`
  planning requires `ha-assist`;
- `DJCONNECT_VERIFICATION_VOICE_ASSISTANT_TARGET_JSON` was not configured;
- `DJCONNECT_VERIFICATION_VOICE_ASSISTANT_ALLOW_LIVE=true` was not configured;
- exact-SHA GitHub CI was still running during the initial attempt.

Follow-up status:

- the stale HA lab was destroyed;
- a clean `ha-assist` lab was started and qualified;
- lab-only credentials were regenerated after removing the stale generated lab
  auth file;
- exact-SHA GitHub CI later returned `CI_PASS`;
- a Piper startup defect in the `ha-assist` compose fragment was found and
  remediated;
- after the Piper fix, the clean lab rebuilt with all three containers running
  but HA websocket qualification timed out;
- after HA websocket qualification is stable, the remaining blocker is Voice
  Assistant target/live opt-in configuration.

The adapter and planner remained healthy. The blocking condition occurred
before adapter mutation, preserving the fail-closed live verification contract.

## Repository Intelligence Review

Knowledge captured for future sessions:

- Phase 15E requires a current `ha-assist` lab, not the stale `ha-profile` lab
  left from earlier phases.
- Operator direction after this attempt: Voice Assistant live qualification
  should always spin up a clean HA lab environment instead of reusing previous
  lab state.
- A configured Voice Assistant live target and explicit live opt-in are
  mandatory before live mutation.
- The active remediation should start by recreating or qualifying the HA Assist
  lab from clean state for the current repository SHA, then configure the Voice
  Assistant target and rerun `VOICE-001`.

This knowledge is now recorded in this report and the generated Phase 15E-R
prompt.

## Architecture Impact Assessment

No architecture changed.

The frozen verification architecture held: the Execution Environment owned lab
readiness, the Planning Engine selected the Voice Endpoint smoke path, and the
thin adapter did not redefine scenario expectations.

## Technical Design Assessment

No technical design changes were made.

The observed failure is an execution environment readiness blocker, not a
Voice Assistant product or adapter design change.

## Verification Assessment

Phase 15E did not qualify live Voice Assistant behavior.

The verification platform produced useful fail-closed evidence and identified
the exact remediation scope. No scenario expectations were changed.

## Known Blockers

- Keep Voice Assistant live qualification on a clean `ha-assist` lab for SHA
- `af8228bc7c933df61cab47d4105002839ba65fb3`.
- Re-run HA lab doctor after the Piper compose fix until the websocket probe
  passes, then capture the qualified clean-lab evidence.
- Configure `DJCONNECT_VERIFICATION_VOICE_ASSISTANT_TARGET_JSON`.
- Configure `DJCONNECT_VERIFICATION_VOICE_ASSISTANT_ALLOW_LIVE=true`.

## Qualification Decision

Phase 15E returns:

```text
VOICE_ASSISTANT_LIVE_QUALIFICATION_BLOCKED
```

Do not begin Phase 16.

Next engineering action:

```text
Phase 15E-R DJConnect Voice Assistant Live Qualification Remediation
```
