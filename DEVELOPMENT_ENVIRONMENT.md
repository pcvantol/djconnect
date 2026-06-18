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
  `ISSUES.md`, `SYNC_PROMPTS.md`, `CHAT_BOOTSTRAP.md`, `CONTRIBUTING.md` and
  this document current when development workflow or setup assumptions change.
- DJConnect is developed and maintained with AI-assisted and agentic engineering
  workflows, including Codex. Accepted changes remain maintainer-reviewed.
- Do not include secrets, private data or proprietary third-party material in
  prompts, agent logs, screenshots, issues or test fixtures.
