# Verification Program V1
## Phase 10E-R - Apple Runtime Qualification Remediation

Repository:

`pcvantol/djconnect`

Apple application source repository:

`pcvantol/djconnect-app`

Context:

Phase 10E executed the mandatory Apple Runtime Qualification gate and returned:

```text
APPLE_RUNTIME_QUALIFICATION_BLOCKED
```

Do not begin Phase 11. Do not execute broad Apple scenario batches until this
remediation phase qualifies the Apple runtime path.

---

# Mission

Prepare and prove the local Apple runtime configuration required by Phase 10E:
release-equivalent app artifact, isolated DerivedData, prepared simulator
target JSON, install, launch, screenshot, scoped redacted logs and UI automation
healthcheck.

No new verification architecture subsystem may be introduced.

---

# Required Work

1. Configure a release-equivalent Apple build command through
   `DJCONNECT_VERIFICATION_APPLE_BUILD_COMMAND`.
2. Use an isolated Phase 10E DerivedData path through
   `DJCONNECT_VERIFICATION_APPLE_DERIVED_DATA`.
3. Produce or select a prepared simulator target JSON through
   `DJCONNECT_VERIFICATION_APPLE_TARGET_JSON`.
4. Ensure the target JSON includes `target_id`, `variant`, `runtime`, `udid`,
   `bundle_id` and `app_path`.
5. Install and launch the qualified app artifact on the selected simulator.
6. Capture screenshot evidence.
7. Collect scoped, redacted runtime logs.
8. Configure and execute one XCTest or accessibility-driver healthcheck through
   `DJCONNECT_VERIFICATION_APPLE_UI_DRIVER` and
   `DJCONNECT_VERIFICATION_APPLE_UI_HEALTHCHECK_COMMAND`.
9. Keep physical-device execution skipped unless explicit operator opt-in and
   local configuration are present.
10. Rerun:

```bash
python3 -m tools.verification.cli apple qualify-runtime
```

---

# Acceptance Criteria

Phase 10E-R is complete when:

- the Apple Runtime Qualification gate returns `PASS`;
- evidence includes release-equivalent build metadata, entitlement metadata,
  simulator target metadata, install, launch, screenshot, log collection and UI
  automation healthcheck status;
- live simulator results are reported as passed only when they actually ran;
- physical-device status is either explicitly qualified or explicitly skipped;
- Phase 10E report, scorecard, backlog and prompt index are updated;
- the first Apple scenario set may be selected only after the gate passes.

---

# Stop Condition

After Phase 10E-R, produce the remediation report and stop. Do not begin Phase
11 or broad Apple scenario expansion automatically unless the active prompt is
updated to require it.
