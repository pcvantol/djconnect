# DJConnect Platform Baseline v1.0 Gap Analysis

Status: active certification follow-up  
Date: 2026-07-11  
Certification decision: `PLATFORM_BASELINE_V1_NOT_CERTIFIED`

## Summary

The platform is close in foundation maturity but not close enough in
qualification maturity.

The largest gap is not architecture. The largest gap is evidence: primary
adapter qualification and cross-platform qualification are incomplete.

## Blocking Gaps

| Gap | Evidence | Impact | Recommended action |
| --- | --- | --- | --- |
| Apple latest runtime qualification is blocked. | `PHASE_10E_R2_APPLE_LATEST_RUNTIME_QUALIFICATION.md`; VPB-031, VPB-036, VPB-037, VPB-038. | Blocks Apple scenario coverage and Phase 10E retry. | Resolve Apple client fix, stable target JSON, isolated DerivedData, signing expectations and UI healthcheck. |
| Apple scenario coverage is not qualified. | `PROMPT_INDEX.md` marks Phase 10E retry blocked. | Blocks cross-platform qualification and later adapters. | Rerun Phase 10E-R2 until `APPLE_LATEST_RUNTIME_QUALIFIED`, then complete Phase 10E coverage. |
| Pi, ESP32, Voice and Windows adapters are future work. | `PROMPT_INDEX.md` Phase 11+ Additional Platform Adapters is future. | Baseline requires primary adapters qualified. | Generate and execute adapter qualification phases after Apple coverage. |
| Cross-platform qualification is incomplete. | No completed cross-platform qualification report exists after all adapters. | Prevents business-first transition. | Run shared contract and interoperability qualification after primary adapters pass. |
| Verification Runtime release operations are not fully operationalized. | VPB-033, VPB-034, VPB-035. | Does not block framework code, but leaves runtime maturity as warning. | Complete Docker Hub secret provisioning, optional repository naming cleanup and self-hosted runner epic. |

## Non-Blocking Warnings

| Warning | Evidence | Recommended action |
| --- | --- | --- |
| Home Assistant backend qualified with transient lab warnings. | Phase 9E-R affected-scenario rerun passed after websocket timeouts. | Keep lab stability watch item VPB-025. |
| Automated Investigator classified one earlier wrapper failure as `unknown`. | Phase 9V rerun report; VPB-020. | Improve classification for missing runtime token cases. |
| Platform Health is architecture-ready, not implementation-ready. | `SOFTWARE_ASSURANCE_PLATFORM_HEALTH.md`. | Implement after baseline prerequisites allow Software Assurance implementation. |

## Required Path To Certification

1. Resolve VPB-031, VPB-036, VPB-037 and VPB-038.
2. Rerun Phase 10E-R2 and obtain `APPLE_LATEST_RUNTIME_QUALIFIED`.
3. Complete Phase 10E Apple scenario coverage.
4. Qualify Pi, ESP32, Voice and Windows primary adapters.
5. Run cross-platform qualification over shared contracts and interoperability.
6. Stabilize Verification Runtime release operations enough to remove warning.
7. Re-run Platform Baseline v1.0 certification.

## Out Of Scope

The following are not required to remove the current certification blockers:

- Software Assurance implementation;
- new product functionality;
- new foundational architecture;
- business feature epics such as Discover, Party Intelligence or Cloud;
- replacing the Verification Platform.
