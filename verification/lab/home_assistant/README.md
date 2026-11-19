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

## Modular Composition

The lab is modular and scenario-driven. Scenarios declare logical requirements
in `requires`; the Planning Engine aggregates those requirements; the
Execution Environment selects the smallest canonical lab profile that satisfies
the local lab capabilities.

Canonical lab assets:

- capability taxonomy: `verification/lab/capabilities.yaml`;
- service definitions: `verification/lab/services/`;
- profile definitions: `verification/lab/profiles/`;
- Compose fragments: `docker/verification/`.

Supported canonical profiles:

- `ha-minimal`;
- `ha-profile`;
- `ha-assist`;
- `ha-music`;
- `ha-full`.

The default profile is `ha-profile`. Override it locally with:

```bash
DJCONNECT_VERIFICATION_LAB_PROFILE=ha-minimal python3 -m tools.verification.cli lab ha start
```

The fallback Home Assistant image is pinned to the current stable lab baseline:

```text
ghcr.io/home-assistant/home-assistant:2026.7.2
```

When the lab lifecycle starts an image through `build`, `start`, `recreate` or
`fresh`, the Execution Environment checks `ghcr.io/home-assistant/home-assistant:stable`,
reads the Home Assistant version label and runs the exact version tag for that
stable release. This keeps normal local lab runs current while preserving
evidence with an explicit image tag.

Override it locally with `DJCONNECT_VERIFICATION_HA_IMAGE` only when a phase
explicitly asks to qualify a different Home Assistant version. Set
`DJCONNECT_VERIFICATION_HA_AUTO_UPDATE=0` to use the fallback image without
checking the latest stable tag.

## Commands

Use the Verification CLI:

```bash
python3 -m tools.verification.cli lab ha build
python3 -m tools.verification.cli lab ha start
python3 -m tools.verification.cli lab ha bootstrap-auth
python3 -m tools.verification.cli lab ha doctor
python3 -m tools.verification.cli lab ha stop
```

The CLI resolves the selected profile into a deterministic Compose fragment
list. It does not generate unique topologies per scenario.

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
