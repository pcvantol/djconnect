# DJConnect Local Home Assistant Verification Lab

Status: Phase 9L lab definition

This directory contains the repository-native Docker Compose definition for the
dedicated local Home Assistant verification lab.

The lab is intentionally separate from any existing Home Assistant container.
It uses explicit verification labels and a dedicated runtime root under:

```text
artifacts/verification/lab/home_assistant/
```

Runtime state, logs and generated configuration are not committed.

## Commands

Use the Verification CLI:

```bash
python3 -m tools.verification.cli lab ha build
python3 -m tools.verification.cli lab ha start
python3 -m tools.verification.cli lab ha doctor
python3 -m tools.verification.cli lab ha stop
```

Destructive cleanup requires explicit opt-in:

```bash
python3 -m tools.verification.cli lab ha destroy --allow-destructive
```

## Safety

The lab must prove:

- `djconnect.verification=true` label;
- source mount from this repository;
- dedicated config/log/storage paths;
- no production Home Assistant volumes;
- exact repository SHA/fingerprint evidence;
- token and GitHub credentials loaded from the environment only.
