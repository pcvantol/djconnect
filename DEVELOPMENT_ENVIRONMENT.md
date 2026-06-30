# DJConnect Development Environment

This document describes the local development setup for the DJConnect Home
Assistant custom integration.

## Repository

Work from the repository root:

```bash
cd ~/Documents/GitHub/djconnect
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

For a fresh Windows 11 developer machine, use the PowerShell onboarding helper
from the repository root:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\tools\dev_onboarding_windows.ps1
```

It offers Windows-native steps for preflight checks, winget-based tooling,
GitHub/Python/Node/.NET setup, Codex CLI installation through npm, DJConnect repo checkout, Home Assistant
integration tests, .NET MAUI workloads for the Windows client, local
integration sync, optional HACS setup, host-service checks for the macOS Docker
Home Assistant/Music Assistant/Wyoming stack, an optional persistent ngrok
tunnel via Windows Task Scheduler and CI smoke pushes.

Windows 11 ARM in Parallels on Apple Silicon should not run Docker Desktop
inside the VM. Run the Docker stack on the macOS host with the macOS onboarding
script, then connect from Windows through the Parallels shared-network host
address. The Windows helper defaults to:

```text
HA_HOST_URL=http://10.211.55.2:8123
MA_HOST_URL=http://10.211.55.2:8095
```

Override those with `-HaHostUrl`, `-MaHostUrl`, `HA_HOST_URL` or
`MA_HOST_URL` when your Parallels network uses a different host address.

The Windows helper clones repositories to a Windows-local checkout root by
default:

```text
C:\Users\<user>\LocalDocuments\GitHub
```

Avoid `C:\Users\<user>\Documents\GitHub` in Parallels VMs when Documents is
shared with macOS; Git for Windows can then hit shared-folder ownership and file
locking issues.

Useful Windows dry-run and planning commands:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\tools\dev_onboarding_windows.ps1 -Core -Plan
pwsh -NoProfile -ExecutionPolicy Bypass -File .\tools\dev_onboarding_windows.ps1 -Steps 8,9,11 -DryRun -Yes
pwsh -NoProfile -ExecutionPolicy Bypass -File .\tools\dev_onboarding_windows.ps1 -Steps 12 -NgrokDomain your-domain.ngrok-free.app -DryRun -Yes
```

The Windows helper is intentionally current-user only: do not run it from an
Administrator terminal. Its tooling step is idempotent around `winget` packages
that are already installed, installs Codex with `npm install -g @openai/codex`,
sets the current-user PowerShell execution policy to `RemoteSigned` so npm
`.ps1` shims such as `codex.ps1` can launch, and refreshes PATH inside the same
PowerShell session. When the onboarding script itself is launched with
`-ExecutionPolicy Bypass`, PowerShell may report that this process still uses
the process-level policy; open a new normal PowerShell terminal before launching
`codex`. If a locked-down shell still blocks the shim, run `codex.cmd` from the
same terminal. Python commands run with `PYTHONUTF8=1`, `PYTHONIOENCODING=utf-8`
and `python -X utf8` so tests that read UTF-8 documentation do not fail under
Windows code pages such as `cp1252`; the helper prefers the `py -3.11` launcher
or a real Python install and avoids the Microsoft Store `python.exe` alias.
When a Windows client checkout contains `global.json`, step `6` installs that
exact .NET SDK version into
`C:\Users\<user>\.dotnet` before running MAUI workload restore from the solution
directory.

The macOS helper offers numbered steps for preflight checks, Homebrew/tooling,
Docker Desktop, Home Assistant, HACS, Codex CLI, repo validation and syncing
this integration into the local Home Assistant config. Step `27` can start a
local Music Assistant server container for Music Assistant backend testing;
provider and player setup still happens in the Music Assistant and Home
Assistant UIs. Step `0` validates machine, hardware, filesystem and network
requirements. VM creation is intentionally outside the onboarding helper; create
any macOS or Windows VM manually with your preferred virtualization tool, then
run the platform-specific onboarding helper inside that environment. The script
also includes optional cross-repo setup steps derived from the other DJConnect
development docs: XcodeGen for the Apple app, PlatformIO for ESP32 firmware,
npm/Playwright/Wrangler for the website/API, Python/PySide dev dependencies for
the Raspberry Pi client and .NET MAUI workloads for the Windows/Mac Catalyst
client.

For a supervised full bootstrap run, use this sequence:

```bash
./tools/dev_onboarding_macos.sh --steps 0,3,4,5,6,7,8,9,10,11,12,21 --plan
./tools/dev_onboarding_macos.sh --steps 0
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

The script adds any missing `homeassistant`, `whisper`, `piper` and
`music-assistant` services to the local Home Assistant Docker Compose file, then
runs:

```bash
docker compose -f "$HOME/docker/homeassistant/docker-compose.yml" up -d homeassistant whisper piper music-assistant
```

Whisper uses `rhasspy/wyoming-whisper` with `--model tiny-int8 --language nl` on
port `10300`. Piper uses `rhasspy/wyoming-piper` with
`--voice nl_NL-mls-medium` on port `10200`. Music Assistant uses the Docker
image `ghcr.io/music-assistant/server:latest`, stores data under
`$HOME/docker/music-assistant-server/data` by default and serves its UI
on:

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

If your compose file is not next to the Home Assistant `config` directory, pass
it explicitly:

```bash
./tools/dev_onboarding_macos.sh --steps 27 --ha-compose-file /path/to/docker-compose.yml
```

To expose the local Home Assistant dev instance for iPhone, Spotify OAuth and
remote-client testing without Nabu Casa, create a free ngrok account, reserve a
static ngrok domain if you want the URL to survive reboot, then run:

```bash
export NGROK_AUTHTOKEN="<token from ngrok>"
./tools/dev_onboarding_macos.sh --steps 28 --ngrok-domain your-domain.ngrok-free.app
```

Step `28` installs ngrok with Homebrew, stores the auth token in ngrok's own
config, creates a macOS LaunchAgent under the current user's
`~/Library/LaunchAgents`, starts it with `RunAtLoad`/`KeepAlive`, and updates
`$HOME/docker/homeassistant/config/configuration.yaml` with:

```yaml
homeassistant:
  external_url: "https://your-domain.ngrok-free.app"
  internal_url: "https://your-domain.ngrok-free.app"

http:
  use_x_forwarded_for: true
  trusted_proxies:
    - 127.0.0.1
    - ::1
    - 172.16.0.0/12
    - 192.168.65.0/24
```

If you run without `--ngrok-domain`, ngrok still starts, but the free ephemeral
Forwarding URL can change. The script prints the current URL when available and
reminds you where to configure it manually in Home Assistant if automatic config
is not possible.

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
$HOME/docker/homeassistant/config
```

The installed custom integration path is:

```text
$HOME/docker/homeassistant/config/custom_components/djconnect
```

The default local stack is managed through Docker Compose at:

```text
$HOME/docker/homeassistant/docker-compose.yml
```

## Install The Current Working Tree Into Home Assistant

From this repository root, sync the current integration into the Docker Home
Assistant config:

```bash
rsync -a --delete --delete-excluded \
  --exclude __pycache__ \
  --exclude '*.pyc' \
  custom_components/djconnect/ \
  "$HOME/docker/homeassistant/config/custom_components/djconnect/"
```

Confirm the installed manifest:

```bash
python3 -m json.tool "$HOME/docker/homeassistant/config/custom_components/djconnect/manifest.json"
```

Then restart Home Assistant Core through Docker Compose:

```bash
docker compose -f "$HOME/docker/homeassistant/docker-compose.yml" up -d homeassistant
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
