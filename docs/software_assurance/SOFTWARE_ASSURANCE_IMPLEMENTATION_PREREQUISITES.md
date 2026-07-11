# Software Assurance Implementation Prerequisites

Status: canonical prerequisites  
Scope owner: `pcvantol/djconnect`

Software Assurance implementation may begin only after:

- Home Assistant qualified;
- Apple qualified;
- Raspberry Pi qualified;
- ESP32 qualified;
- Voice Endpoint qualified;
- Windows qualified;
- cross-platform qualification completed;
- Verification Runtime released as stable;
- Platform Baseline v1.0 certified.

The mandatory platform prerequisite is:

```text
PLATFORM_BASELINE_V1_CERTIFIED
```

These prerequisites are mandatory and must not be weakened by repository-local
prompts, workflow edits or partial implementation milestones.

When all prerequisites are satisfied, the first implementation prompt should
start only through the registered implementation sequence in
`SOFTWARE_ASSURANCE_IMPLEMENTATION.md`.
