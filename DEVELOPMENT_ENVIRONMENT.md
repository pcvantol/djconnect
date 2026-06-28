# DJConnect Development Environment

This document describes the local development setup for the DJConnect Home
Assistant custom integration.

## Repository

Work from the repository root:

```bash
cd /Users/pcvantol/Documents/GitHub/djconnect
```

The integration source lives in:

```text
custom_components/djconnect/
```

The lightweight test suite stubs Home Assistant where possible, so most changes
can be validated without a full Home Assistant checkout.

## Python Checks

Run the full lightweight suite before release or non-trivial code changes:

```bash
python3 -m unittest discover -s tests
```

For focused work, run only the touched modules. Examples:

```bash
python3 -m unittest tests.test_config_flow_helpers
python3 -m unittest tests.test_translations
python3 -m unittest tests.test_http_voice_helpers
```

Check JSON and Python syntax when touching translations or multiple modules:

```bash
python3 -m json.tool custom_components/djconnect/strings.json >/tmp/djconnect_strings.json
python3 -m json.tool custom_components/djconnect/translations/en.json >/tmp/djconnect_en.json
python3 -m json.tool custom_components/djconnect/translations/nl.json >/tmp/djconnect_nl.json
python3 -m py_compile custom_components/djconnect/*.py tests/*.py
```

Always run:

```bash
git diff --check
```

## Local Home Assistant Docker Environment

For a fresh macOS developer machine, use the onboarding helper from the
repository root:

```bash
./tools/dev_onboarding_macos.sh
```

It offers numbered steps for preflight checks, Homebrew/tooling, Docker
Desktop, Home Assistant, HACS, Codex CLI, repo validation and syncing this
integration into the local Home Assistant config. Step `27` can start a local
Music Assistant server container for Music Assistant backend testing; provider
and player setup still happens in the Music Assistant and Home Assistant UIs.
Step `0` validates machine,
VM, hardware, filesystem and network requirements. Step `1` can install/open
Parallels Desktop and bootstrap a macOS development VM with minimal input. Step
`2` can bootstrap a Parallels Windows 11 ARM development VM on Apple Silicon,
using the Parallels assistant or an optional local Windows ARM ISO. The script
also includes optional cross-repo setup steps derived from the other
DJConnect development docs: XcodeGen for the Apple app, PlatformIO for ESP32
firmware, npm/Playwright/Wrangler for the website/API, Python/PySide dev
dependencies for the Raspberry Pi client and .NET MAUI workloads for the
Windows/Mac Catalyst client.

To bootstrap only the Parallels macOS VM:

```bash
./tools/dev_onboarding_macos.sh --steps 1 --vm-name "DJConnect macOS Dev"
```

Optionally ask macOS to fetch a specific full installer before Parallels opens:

```bash
./tools/dev_onboarding_macos.sh --steps 1 --macos-version 15.5
```

To bootstrap only the Parallels Windows 11 ARM VM:

```bash
./tools/dev_onboarding_macos.sh --steps 2 --windows-vm-name "DJConnect Windows 11 ARM Dev"
```

For a supervised full bootstrap run, use this sequence:

```bash
./tools/dev_onboarding_macos.sh --steps 0,1,2,3,4,5,6,7,8,9,10,11,12,21 --plan
./tools/dev_onboarding_macos.sh --steps 0
./tools/dev_onboarding_macos.sh --steps 1 --macos-version 15.5 --warm-sudo
./tools/dev_onboarding_macos.sh --steps 2 --windows-vm-name "DJConnect Windows 11 ARM Dev" --warm-sudo
./tools/dev_onboarding_macos.sh --steps 3,4,5,6,7,8,9,10,11,12,21 --warm-sudo --prompt-secrets
./tools/dev_onboarding_macos.sh --steps 13,14,15,16,17,18,19,22 --warm-sudo --prompt-secrets
```

Preflight checks include macOS version, architecture, RAM, CPU cores, free disk
space, writable workspace/config/log paths, local port availability for Home
Assistant and dev servers, outbound HTTPS connectivity to GitHub, Homebrew,
npm, PyPI, GHCR/Docker, Cloudflare and Apple software update, Rosetta status on
Apple Silicon, git identity, Xcode license state and local secret/log ignore
rules.

Step `20` can be run separately to prompt for optional local tokens/API keys and
store them in `.djconnect-onboarding.env` with `0600` permissions. The file is
for local validation only and must not be committed.

The onboarding helper writes a timestamped persistent log by default under
`logs/` with `0600` permissions, while still streaming output to the terminal.
Use `--log-file /path/to/file.log` to choose a path or `--no-log-file` to
disable persistent logging. Secret prompt values are not printed.
Interactive terminal output uses ANSI colors, bold section headers, step
progress counters and a spinner for wait loops. Set `NO_COLOR=1` or pass
`--no-color` for plain output.

Use `--dry-run` to print mutating install/bootstrap commands without executing
them. The helper's CLI contract is covered by:

```bash
python3 -m unittest tests.test_dev_onboarding_script
```

Package manager upgrade checks are explicit. Step `23` reports available
Homebrew, npm, pip, PlatformIO and .NET workload updates without applying them.
Step `24` applies upgrades only when `--apply-upgrades` is present:

```bash
./tools/dev_onboarding_macos.sh --steps 23
./tools/dev_onboarding_macos.sh --steps 24 --apply-upgrades
```

Review lockfiles, manifests and dependency documentation after running step
`24`.

Step `25` runs local E2E release/build smoke checks across the DJConnect repos,
including local tests and `release.sh <version> --dry-run` where available.
If the Music Assistant server container from step `27` exists, step `25` also
performs a lightweight `http://localhost:8095` smoke check. When
`DJCONNECT_HA_WS_URL` and `DJCONNECT_HA_TOKEN` are set, step `25` also performs
an optional Home Assistant websocket capability smoke against
`djconnect/capabilities`; dry-run output redacts the token. Step `26` can
create a dedicated CI smoke-test branch with an empty commit, push it and watch
the GitHub Actions result, but only when `--run-ci-push` is explicitly present:

```bash
./tools/dev_onboarding_macos.sh --steps 25 --e2e-version 3.1.999
./tools/dev_onboarding_macos.sh --steps 26 --run-ci-push --ci-branch codex/onboarding-ci-smoke
```

Use `--dry-run` first to inspect the local release or GitHub CI commands.

To bootstrap the Music Assistant server used by the DJConnect `Music Assistant`
backend option:

```bash
./tools/dev_onboarding_macos.sh --steps 27
```

The server uses the Docker image `ghcr.io/music-assistant/server:latest`, stores
data under `/Users/pcvantol/docker/music-assistant-server/data` by default and
serves its UI on:

```text
http://localhost:8095
```

After the server is running, open Music Assistant, configure at least one music
provider and usable player, then add/configure the Music Assistant integration
inside Home Assistant before testing the DJConnect `Music Assistant` backend.
Override the data path with:

```bash
./tools/dev_onboarding_macos.sh --steps 27 --ma-data-dir /path/to/music-assistant-data
```

For unattended setup of only this Home Assistant integration:

```bash
./tools/dev_onboarding_macos.sh --core --yes
```

For unattended setup with cross-repo tooling:

```bash
./tools/dev_onboarding_macos.sh --all --yes
```

For selected cross-repo setup:

```bash
./tools/dev_onboarding_macos.sh --steps 13,14,15,16,17,18
```

The local Home Assistant development instance runs in Docker and is available at:

```text
http://localhost:8123
```

The local Home Assistant config path is:

```text
/Users/pcvantol/docker/homeassistant/config
```

The installed custom integration path is:

```text
/Users/pcvantol/docker/homeassistant/config/custom_components/djconnect
```

## Install The Current Working Tree Into Home Assistant

From this repository root, sync the current integration into the Docker Home
Assistant config:

```bash
rsync -a --delete --delete-excluded \
  --exclude __pycache__ \
  --exclude '*.pyc' \
  custom_components/djconnect/ \
  /Users/pcvantol/docker/homeassistant/config/custom_components/djconnect/
```

Confirm the installed manifest:

```bash
python3 -m json.tool /Users/pcvantol/docker/homeassistant/config/custom_components/djconnect/manifest.json
```

Then restart Home Assistant Core by restarting the Docker container:

```bash
docker restart homeassistant
docker ps --filter name=homeassistant --format '{{.Names}}\t{{.Status}}\t{{.Ports}}'
```

Home Assistant should come back on `localhost:8123`.

## Manual UI Validation

After restart, validate the flows touched by the change:

- Add Integration: confirm `Assist Conversation Agent` appears first in the setup choice.
- Add Integration: confirm setup method is not repeated on the pairing step.
- Add Integration: confirm client type choices are ordered iOS, macOS, Apple Watch, Linux/Raspberry Pi and ESP32.
- Add Integration/options: confirm firmware channel appears only for ESP32 clients.
- Add Integration: confirm Spotify setup asks for a user-owned Spotify Client ID and shows the exact redirect URI.
- Options flow: confirm it opens without an internal server error.
- Options flow: confirm internal compatibility/OTA/audio TTL defaults are not shown.
- Repairs/options: confirm Spotify reauthorization opens the OAuth flow.
- Developer Tools: test `djconnect.test_parse`, `djconnect.test_command` and `djconnect.test_tts` when relevant.
- Ask DJ: confirm `/ask_dj/message` returns `history_revision`,
  `clear_revision`, `history_limit` and trim metadata when applicable.
- Ask DJ: confirm `Goedemorgen` returns a personalized suggestion with Ja/Nee
  actions, and `ask_dj_followup_response` handles yes, no and expired pending
  state.
- Ask DJ: confirm cross-device history clear/trim behavior on iOS, macOS and
  watchOS when those clients are available.
- Ask DJ: confirm gibberish and sandbox/prompt-injection-like messages return
  the neutral unknown-intent fallback without playback mutation.

For UI or translation work, check both Dutch and English Home Assistant
language settings when practical.

## Docker Helpers

Check the running Home Assistant container:

```bash
docker ps --format '{{.Names}}\t{{.Image}}\t{{.Status}}'
```

Follow logs while testing:

```bash
docker logs -f homeassistant
```

If the integration does not reload as expected, restart the container again and
refresh the browser or app cache.

## Development Hygiene

- Do not commit secrets, tokens, passwords, private URLs or raw diagnostics.
- Keep `README.md`, `CHANGELOG.md`, `AGENTS.md`, `HANDOFF.md`, `TODO.md`,
  `ISSUES.md`, `SYNC_PROMPTS.md`, `PRODUCT_ROADMAP.md`,
  `TECHNICAL_DESIGN_DECISIONS.md`, `VOICE_INTENT_DATA.md`,
  `CHAT_BOOTSTRAP.md`, `CONTRIBUTING.md`, `SECURITY.md`, `info.md` and this
  document current when development workflow, public contracts or setup
  assumptions change.
- DJConnect is developed and maintained with AI-assisted and agentic engineering
  workflows, including Codex. Accepted changes remain maintainer-reviewed.
- Do not include secrets, private data or proprietary third-party material in
  prompts, agent logs, screenshots, issues or test fixtures.
