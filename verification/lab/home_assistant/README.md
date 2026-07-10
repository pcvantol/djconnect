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
python3 -m tools.verification.cli lab ha bootstrap-auth
python3 -m tools.verification.cli lab ha doctor
python3 -m tools.verification.cli lab ha stop
```

Destructive cleanup requires explicit opt-in:

```bash
python3 -m tools.verification.cli lab ha destroy --allow-destructive
```

## Lab Authentication

The lab supports two token sources:

- `DJCONNECT_VERIFICATION_HA_TOKEN` from the local environment;
- generated lab-only Home Assistant credentials under the ignored lab root.

For a fresh dedicated lab, run:

```bash
python3 -m tools.verification.cli lab ha bootstrap-auth
```

This creates a verification-only Home Assistant user through the Home
Assistant onboarding API and stores the generated password only under:

```text
artifacts/verification/lab/home_assistant/.secrets/
```

The CLI requests a fresh Home Assistant access token from those credentials
when `lab ha doctor` runs. Tokens are never committed and are redacted from
reports and evidence.

## Safety

The lab must prove:

- `djconnect.verification=true` label;
- source mount from this repository;
- dedicated config/log/storage paths;
- no production Home Assistant volumes;
- exact repository SHA/fingerprint evidence;
- HA tokens loaded from the environment or generated lab-only credentials;
- GitHub credentials loaded from the environment only.
