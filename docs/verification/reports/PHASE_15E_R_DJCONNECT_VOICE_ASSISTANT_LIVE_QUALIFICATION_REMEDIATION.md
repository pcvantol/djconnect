# Phase 15E-R DJConnect Voice Assistant Live Qualification Remediation

Status: `VOICE_ASSISTANT_LIVE_QUALIFIED`

Date: 2026-07-12

Branch: `main`

Repository SHA: `af8228bc7c933df61cab47d4105002839ba65fb3`

Verification Runtime: `1.1.0`

## Executive Summary

Phase 15E-R remediated the Voice Assistant live qualification blockers from
Phase 15E and qualified the DJConnect Voice Assistant verification path against
a clean Home Assistant Assist lab.

Qualification decision:

```text
VOICE_ASSISTANT_LIVE_QUALIFIED
```

## Scope

Executed:

- discarded the stale Home Assistant verification lab;
- started a clean `ha-assist` lab for the current repository SHA;
- regenerated lab-only Home Assistant auth credentials;
- fixed the Piper sidecar startup configuration used by the `ha-assist` lab;
- verified Home Assistant, Whisper and Piper containers were running;
- qualified the clean Home Assistant lab through REST and websocket gates;
- configured an explicit Voice Assistant live target for the local DJConnect
  Conversation Agent;
- executed `VOICE-001` through the Scenario Engine and `voice_endpoint`
  adapter;
- collected sanitized evidence and run metadata.

Out of scope and not executed:

- Phase 16 Cross-Platform Qualification;
- new Voice Assistant, Ask DJ, Assist, STT or TTS product behavior;
- ESP32, Apple, Raspberry Pi or Windows adapter changes;
- Software Assurance implementation;
- Platform Baseline certification.

## Implementation

The `ha-assist` lab includes the Piper sidecar and advertises `tts.piper`.
During remediation, the Piper container was found exiting because the Compose
fragment did not provide Piper's required `--voice` argument.

Updated:

- `docker/verification/compose.piper.yaml`;
- `verification/lab/services/piper.yaml`.

The verification Compose fragment now supplies a default lab voice:

```text
DJCONNECT_VERIFICATION_PIPER_VOICE=en_US-lessac-medium
```

## Verification

Focused adapter and planner regression tests:

```bash
python -m pytest tests/verification/test_voice_assistant_adapter.py tests/verification/test_planning_engine.py -q
```

Result:

```text
16 passed
```

Clean lab lifecycle:

```bash
DJCONNECT_VERIFICATION_LAB_PROFILE=ha-assist python -m tools.verification.cli lab ha destroy --allow-destructive
rm -f artifacts/verification/lab/home_assistant/.secrets/ha_lab_auth.json
DJCONNECT_VERIFICATION_LAB_PROFILE=ha-assist python -m tools.verification.cli lab ha fresh
DJCONNECT_VERIFICATION_LAB_PROFILE=ha-assist python -m tools.verification.cli lab ha bootstrap-auth
DJCONNECT_VERIFICATION_LAB_PROFILE=ha-assist python -m tools.verification.cli lab ha doctor
```

Result:

```text
LOCAL_VERIFICATION_LAB_QUALIFIED
```

Sidecar status:

```text
djconnect-verification-ha        Up
djconnect-verification-whisper   Up
djconnect-verification-piper     Up
```

Live Voice Endpoint execution:

```bash
DJCONNECT_VERIFICATION_LAB_PROFILE=ha-assist \
DJCONNECT_VERIFICATION_VOICE_ASSISTANT_ALLOW_LIVE=true \
DJCONNECT_VERIFICATION_VOICE_ASSISTANT_TARGET_JSON='{"target_id":"ha-assist-local-conversation-agent","runtime":"live","ha_url":"http://127.0.0.1:18123","endpoint_id":"conversation.djconnect_verification_lab_dj","metadata":{"lab_profile":"ha-assist","conversation_agent":"DJConnect DJ","source":"local_verification_lab"}}' \
python -m tools.verification.cli --voice-assistant-adapter execute --scenario-id VOICE-001
```

Result:

```text
execute: 1 of 1 tests executed, status PASS (1 PASS)
```

Repository hygiene:

```bash
git diff --check
```

Result:

```text
passed
```

## Evidence

Primary passing evidence:

- `artifacts/verification/evidence/djv-20260712T155553Z-fbdeaf590f/`;
- summary:
  `artifacts/verification/evidence/djv-20260712T155553Z-fbdeaf590f/summary.json`;
- qualification metadata:
  `artifacts/verification/evidence/djv-20260712T155553Z-fbdeaf590f/qualification.json`;
- environment snapshot:
  `artifacts/verification/evidence/djv-20260712T155553Z-fbdeaf590f/environment.json`;
- execution plan:
  `artifacts/verification/evidence/djv-20260712T155553Z-fbdeaf590f/execution-plan.json`.

Important recorded state:

```text
scenario: VOICE-001
adapter: voice_endpoint
result_state: PASS
target_configured: true
target_id: ha-assist-local-conversation-agent
github_ci_status: CI_PASS
ha_docker_discovery: PASS
```

## Investigation

Phase 15E blockers and disposition:

| Blocker | Classification | Disposition |
| --- | --- | --- |
| Stale HA lab on old SHA | Execution environment issue | Remediated by destroying and recreating clean `ha-assist` lab |
| Missing live target config | Operator configuration issue | Remediated with explicit `DJCONNECT_VERIFICATION_VOICE_ASSISTANT_TARGET_JSON` |
| Missing live opt-in | Operator configuration issue | Remediated with `DJCONNECT_VERIFICATION_VOICE_ASSISTANT_ALLOW_LIVE=true` |
| Piper sidecar exited | Verification environment defect | Remediated by adding default Piper voice configuration |
| Early websocket timeout | Startup readiness timing | Passed after lab settled |

No product implementation defect was found.

## Repository Intelligence Review

Knowledge captured:

- Voice Assistant live qualification must always start from a clean
  `ha-assist` lab.
- The lab-only auth file under
  `artifacts/verification/lab/home_assistant/.secrets/ha_lab_auth.json` must be
  removed when a truly clean HA lab is required.
- `ha-assist` requires the Piper sidecar to start with an explicit voice.
- The local DJConnect Conversation Agent target can be represented with
  `endpoint_id` `conversation.djconnect_verification_lab_dj`.

## Architecture Impact Assessment

No architecture changed.

The existing Verification Execution Environment, Planning Engine and thin
Voice Endpoint adapter boundaries held.

## Technical Design Assessment

No product technical design changed.

The only implementation change was verification lab Compose metadata for the
Piper sidecar.

## Verification Assessment

Phase 15E-R qualifies live Voice Assistant runtime smoke coverage for the
current verification roadmap.

The passing scenario is intentionally narrow: it proves the live Voice Endpoint
adapter path, clean HA Assist lab readiness, target configuration and runtime
primitive execution. Broader cross-platform behavior remains Phase 16 scope.

## Known Blockers

None blocking Phase 16.

## Qualification Decision

Phase 15E-R returns:

```text
VOICE_ASSISTANT_LIVE_QUALIFIED
```

Next engineering action:

```text
Phase 16 Cross-Platform Qualification
```

Do not execute Phase 16 automatically.
