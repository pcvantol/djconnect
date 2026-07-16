#!/usr/bin/env bash
set -euo pipefail

# Recovers a DJConnect macOS Actions-runner host after a laptop replacement.
# Authentication is interactive through gh; GitHub registration tokens are
# fetched just-in-time and are never accepted as arguments or written to disk.

readonly ORG='pcvantol'
GITHUB_ROOT="${GITHUB_ROOT:-$HOME/Documents/GitHub}"
RUNNER_ROOT="${RUNNER_ROOT:-$HOME/actions-runners}"
PROFILE_SELECTION='all'
DRY_RUN=0
SKIP_CODEX=0
XCODE_VERSION=''
SIGNING_P12=''
PROVISIONING_PROFILES_DIR=''
CONFIGURE_KEYCHAIN_ACCESS=0
INSTALL_PARALLELS=0
SKIP_DEVELOPER_WORKSTATION=0
NGROK_DOMAIN="${NGROK_DOMAIN:-}"
PROMPT_NGROK_AUTH=0
CONFIGURE_APPLE_INTERNAL_RELEASE=0
APPLE_TEAM_ID="${APPLE_TEAM_ID:-}"
APPLE_DEVELOPMENT_IDENTITY="${APPLE_DEVELOPMENT_IDENTITY:-}"
SUDO_KEEPALIVE_PID=''
CLR_RESET=''
CLR_BOLD=''
CLR_CYAN=''
CLR_GREEN=''
CLR_YELLOW=''
CLR_RED=''
CLR_MAGENTA=''
LOG_FILE="${LOG_FILE:-}"
LOGGING_STARTED=0
ORIGINAL_STDOUT_IS_TTY=0
REPORT_FILE="${REPORT_FILE:-}"
REPORTING_STARTED=0
CURRENT_STEP=''
ALLOW_STEP_RETRY=1

usage() {
  cat <<'EOF'
Usage: bootstrap_macos_runner_host.sh [options]

Recover a fresh Apple-Silicon MacBook as a DJConnect developer and GitHub
Actions runner host. The script installs supported host tooling, clones the
required repositories, authenticates GitHub CLI interactively if necessary,
registers the selected runners as launchd services, and installs the daily
macOS CI-tooling maintenance LaunchAgent.

Options:
  --profiles LIST       Comma-separated: apple,private-network,esp32,pi.
                        Default: all.
  --github-root DIR     Parent directory for DJConnect repositories.
                        Default: ~/Documents/GitHub
  --runner-root DIR     Parent directory for Actions runner installations.
                        Default: ~/actions-runners
  --skip-codex          Do not install/update the Codex CLI.
  --xcode-version VER   Download, install and select this qualified Xcode line
                        through xcodes. Apple Developer authentication may
                        prompt interactively.
  --signing-p12 FILE    Import this locally supplied signing identity into the
                        login keychain. Its password is prompted invisibly.
  --provisioning-profiles-dir DIR
                        Copy local *.mobileprovision files into the current
                        user's provisioning-profile directory.
  --configure-keychain-access
                        Grant the standard Apple build tools unattended access
                        to existing local signing keys. The login-keychain
                        password is prompted invisibly.
  --install-parallels   Check for Parallels Desktop and install it through
                        Homebrew when absent. It does not activate a license or
                        create a Windows VM.
  --skip-developer-workstation
                        Do not run the complete existing macOS developer
                        onboarding. By default the recovery restores the full
                        local DJConnect development workstation as well as the
                        runner host.
  --ngrok-domain DOMAIN Reserved ngrok static domain for the Home Assistant
                        external URL.
  --prompt-ngrok-auth   Prompt invisibly for the ngrok authtoken when it is
                        not already set in NGROK_AUTHTOKEN.
  --configure-apple-internal-release
                        Open Xcode for interactive Apple Developer sign-in,
                        validate local Apple Development identity and iPhone/
                        Watch development profiles, then update the exact
                        MacBook UUID and identity in the GitHub Environment.
  --apple-team-id ID    Apple Developer Team ID for the internal-release
                        readiness check. Defaults to the unique Team ID in
                        the checked-out Apple project.
  --apple-development-identity NAME
                        Exact local Apple Development signing identity. If
                        omitted, the script prompts after listing candidates.
  --dry-run             Print changes without executing them.
  --log-file FILE       Capture all non-sensitive recovery output in this
                        single file. Default:
                        ~/Library/Logs/DJConnect/macos-runner-recovery-<UTC>.log
  --no-log-file         Do not create a recovery log file.
  --report-file FILE    Write the final Markdown recovery report to this file.
                        Default:
                        ~/Library/Logs/DJConnect/macos-runner-recovery-<UTC>.md
  --no-report-file      Do not create the Markdown recovery report.
  --no-step-retry       Abort immediately when a recovery phase fails instead
                        of offering an interactive retry for that same phase.
  --no-color            Disable ANSI color output.
  --help                Show this help.

No GitHub registration token is passed on the command line. After `gh auth
login`, the script obtains one short-lived token per repository through the
authenticated GitHub API and gives it directly to the runner configurator.

Signing material must be supplied from a local secure backup. It is never
downloaded from GitHub, written to this repository or emitted to a log.
EOF
}

init_style() {
  if [[ "$ORIGINAL_STDOUT_IS_TTY" == '1' && -z "${NO_COLOR:-}" ]]; then
    CLR_RESET=$'\033[0m'
    CLR_BOLD=$'\033[1m'
    CLR_CYAN=$'\033[36m'
    CLR_GREEN=$'\033[32m'
    CLR_YELLOW=$'\033[33m'
    CLR_RED=$'\033[31m'
    CLR_MAGENTA=$'\033[35m'
  fi
}

style() { printf '%s%s%s' "$1" "$2" "$CLR_RESET"; }
log() { printf '\n%s %s\n' "$(style "$CLR_CYAN$CLR_BOLD" '==>')" "$*"; }
ok() { printf '%s %s\n' "$(style "$CLR_GREEN$CLR_BOLD" 'OK')" "$*"; }
warn() { printf '%s %s\n' "$(style "$CLR_YELLOW$CLR_BOLD" 'WARN')" "$*" >&2; }
die() { printf '%s %s\n' "$(style "$CLR_RED$CLR_BOLD" 'ERROR')" "$*" >&2; exit 1; }

start_logging() {
  if [[ "$LOG_FILE" == 'none' ]]; then
    return
  fi
  if [[ -z "$LOG_FILE" ]]; then
    LOG_FILE="$HOME/Library/Logs/DJConnect/macos-runner-recovery-$(date -u '+%Y%m%dT%H%M%SZ').log"
  fi
  if [[ "$DRY_RUN" == '1' ]]; then
    printf 'DRY: capture complete non-sensitive recovery output in %s\n' "$LOG_FILE"
    return
  fi
  umask 077
  mkdir -p "$(dirname "$LOG_FILE")"
  touch "$LOG_FILE"
  chmod 600 "$LOG_FILE"
  exec > >(tee -a "$LOG_FILE") 2>&1
  LOGGING_STARTED=1
  log "Capturing complete non-sensitive recovery output in $LOG_FILE."
}

report_append() {
  local step="$1"
  local status="$2"
  local result="$3"
  [[ "$REPORTING_STARTED" == '1' ]] || return 0
  result="${result//|/\\|}"
  printf '| %s | %s | %s |\n' "$step" "$status" "$result" >>"$REPORT_FILE"
}

start_report() {
  if [[ "$REPORT_FILE" == 'none' ]]; then
    return
  fi
  if [[ -z "$REPORT_FILE" ]]; then
    REPORT_FILE="$HOME/Library/Logs/DJConnect/macos-runner-recovery-$(date -u '+%Y%m%dT%H%M%SZ').md"
  fi
  if [[ "$DRY_RUN" == '1' ]]; then
    printf 'DRY: write final Markdown recovery report to %s\n' "$REPORT_FILE"
    return
  fi
  umask 077
  mkdir -p "$(dirname "$REPORT_FILE")"
  {
    printf '# DJConnect macOS Runner Recovery Report\n\n'
    printf 'Started (UTC): %s\n\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    printf '%s\n' '- Mode: recovery execution'
    printf '%s\n' "- Selected runner profiles: $PROFILE_SELECTION"
    printf '%s\n\n' "- Transcript log: ${LOG_FILE:-not configured}"
    printf '%s\n' '| Step | Status | Result |'
    printf '%s\n' '| --- | --- | --- |'
  } >"$REPORT_FILE"
  chmod 600 "$REPORT_FILE"
  REPORTING_STARTED=1
}

complete_report() {
  local exit_code="$1"
  [[ "$REPORTING_STARTED" == '1' ]] || return 0
  if [[ -n "$CURRENT_STEP" ]]; then
    report_append "$CURRENT_STEP" 'FAILED' 'Stopped before this step completed; inspect the transcript log for the exact error.'
    CURRENT_STEP=''
  fi
  {
    printf '\n## Final status\n\n'
    if [[ "$exit_code" == '0' ]]; then
      printf '%s\n' '**PASSED** — all requested recovery stages completed successfully.'
    else
      printf '%s\n' '**FAILED** — recovery stopped before completion; inspect the transcript log and the failed step above.'
    fi
    printf '\nCompleted (UTC): %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  } >>"$REPORT_FILE"
}

run_phase() {
  local step="$1"
  shift
  local attempt=1
  local phase_status
  CURRENT_STEP="$step"
  while true; do
    log "$step (attempt $attempt)"
    set +e
    (set -e; "$@")
    phase_status=$?
    set -e
    if [[ "$phase_status" == '0' ]]; then
      report_append "$step" "PASSED (attempt $attempt)" 'Completed successfully; see the central transcript for detailed command output.'
      ok "$step"
      CURRENT_STEP=''
      return 0
    fi

    report_append "$step" "FAILED (attempt $attempt)" "Exited with status $phase_status."
    warn "$step failed with status $phase_status."
    if [[ "$ALLOW_STEP_RETRY" != '1' || "$DRY_RUN" == '1' || ! -r /dev/tty || ! -w /dev/tty ]]; then
      die "Recovery phase failed: $step"
    fi
    printf 'Retry this phase? [r]etry / [a]bort: ' >/dev/tty
    local response=''
    read -r response </dev/tty
    case "$response" in
      r|R|retry|Retry|RETRY)
        report_append "$step" 'RETRYING' "Operator requested retry after attempt $attempt."
        attempt=$((attempt + 1))
        ;;
      a|abort|'') die "Recovery phase aborted by operator: $step" ;;
      *) warn 'Enter r to retry the same phase or a to abort recovery.' ;;
    esac
  done
}

run_interactive() {
  if [[ "$DRY_RUN" == '1' ]]; then
    run "$@"
    return
  fi
  [[ -r /dev/tty && -w /dev/tty ]] || die 'An interactive terminal is required for this authentication step.'
  "$@" </dev/tty >/dev/tty 2>/dev/tty
}

cleanup() {
  local exit_code=$?
  if [[ -n "$SUDO_KEEPALIVE_PID" ]]; then
    kill "$SUDO_KEEPALIVE_PID" >/dev/null 2>&1 || true
  fi
  complete_report "$exit_code"
  return "$exit_code"
}

warm_sudo() {
  if [[ "$DRY_RUN" == '1' ]]; then
    printf '%s verify administrator membership and refresh sudo credentials\n' "$(style "$CLR_MAGENTA$CLR_BOLD" 'DRY:')"
    return
  fi
  dseditgroup -o checkmember -m "$(id -un)" admin | grep -Fq 'yes' || die 'The recovery user must be a local macOS administrator for runner services and Xcode setup.'
  log 'Verifying administrator access and refreshing sudo credentials.'
  sudo -v
  while true; do
    sudo -n true 2>/dev/null || exit
    sleep 60
  done &
  SUDO_KEEPALIVE_PID="$!"
}

run() {
  if [[ "$DRY_RUN" == '1' ]]; then
    printf '%s' "$(style "$CLR_MAGENTA$CLR_BOLD" 'DRY:')"
    printf ' %q' "$@"
    printf '\n'
    return 0
  fi
  "$@"
}

run_in_dir() {
  local directory="$1"
  shift
  if [[ "$DRY_RUN" == '1' ]]; then
    printf '%s (cd %q &&' "$(style "$CLR_MAGENTA$CLR_BOLD" 'DRY:')" "$directory"
    printf ' %q' "$@"
    printf ')\n'
    return 0
  fi
  (cd "$directory" && "$@")
}

ensure_macos_arm64() {
  [[ "$(uname -s)" == 'Darwin' ]] || die 'This recovery bootstrap runs only on macOS.'
  [[ "$(uname -m)" == 'arm64' ]] || die 'DJConnect macOS runners require an Apple-Silicon (arm64) host.'
}

ensure_xcode() {
  if [[ -n "$XCODE_VERSION" ]]; then
    ensure_homebrew
    run brew install xcodes
    if [[ "$DRY_RUN" == '1' ]]; then
      printf 'DRY: xcodes install %q --select\n' "$XCODE_VERSION"
      return
    fi
    if ! xcodebuild -version 2>/dev/null | head -n 1 | grep -Fq "Xcode $XCODE_VERSION"; then
      log "Installing and selecting qualified Xcode $XCODE_VERSION through xcodes."
      xcodes install "$XCODE_VERSION" --select
    fi
  fi

  xcodebuild -version >/dev/null 2>&1 || die 'Full Xcode is absent. Rerun with --xcode-version <qualified-version>; xcodes will authenticate with Apple interactively and install it.'
  log "Using $(xcodebuild -version | tr '\n' ' ' | sed 's/ $//')."
  [[ "$DRY_RUN" == '1' ]] || sudo xcodebuild -license accept
  [[ "$DRY_RUN" == '1' ]] || sudo xcodebuild -runFirstLaunch
}

ensure_homebrew() {
  if command -v brew >/dev/null 2>&1; then
    return
  fi
  if [[ -x /opt/homebrew/bin/brew ]]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
    return
  fi

  log 'Installing Homebrew for the current user.'
  if [[ "$DRY_RUN" == '1' ]]; then
    printf 'DRY: install Homebrew from https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh\n'
    return
  fi
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  eval "$(/opt/homebrew/bin/brew shellenv)"
}

ensure_tooling() {
  ensure_homebrew
  log 'Installing or updating macOS runner tooling.'
  run brew update
  run brew install git gh jq node python@3.12 xcodegen swiftlint xcbeautify create-dmg mas xcodes
  if [[ "$SKIP_CODEX" == '0' ]]; then
    run npm install -g @openai/codex
  fi
}

ensure_parallels() {
  if [[ "$INSTALL_PARALLELS" == '0' ]]; then
    return
  fi
  if [[ -d '/Applications/Parallels Desktop.app' ]] && command -v prlctl >/dev/null 2>&1; then
    log "Parallels Desktop is available: $(prlctl --version 2>/dev/null || printf 'version unavailable')."
    return
  fi
  ensure_homebrew
  log 'Installing Parallels Desktop through Homebrew.'
  run brew install --cask parallels
  if [[ "$DRY_RUN" == '0' ]]; then
    [[ -d '/Applications/Parallels Desktop.app' ]] || die 'Parallels Desktop installation did not create the expected application bundle.'
    warn 'Open Parallels Desktop once to activate its license. Windows ARM VM recovery and its self-hosted runner remain a separate, explicit operation.'
  fi
}

ensure_github_auth() {
  if gh auth status --hostname github.com >/dev/null 2>&1; then
    return
  fi
  log 'Authenticating GitHub CLI. Sign in with the account that administers the DJConnect repositories.'
  run_interactive gh auth login --hostname github.com --git-protocol https --web
  [[ "$DRY_RUN" == '1' ]] || gh auth status --hostname github.com >/dev/null 2>&1 || die 'GitHub CLI authentication did not complete.'
}

ensure_docker_hub_auth() {
  if [[ "$SKIP_DEVELOPER_WORKSTATION" == '1' ]]; then
    return
  fi
  if [[ "$DRY_RUN" == '1' ]]; then
    run docker login
    return
  fi
  command -v docker >/dev/null 2>&1 || die 'Docker CLI is unavailable after developer workstation recovery.'
  docker info >/dev/null 2>&1 || die 'Docker Desktop is not ready after developer workstation recovery.'
  log 'Authenticating Docker CLI with Docker Hub using its interactive device-login flow.'
  log 'Complete the browser/device-code flow if Docker asks. No Docker credential is passed as an argument or written by this script.'
  run_interactive docker login
}

configure_apple_internal_release() {
  if [[ "$CONFIGURE_APPLE_INTERNAL_RELEASE" == '0' ]]; then
    return
  fi
  local apple_repository="$GITHUB_ROOT/djconnect-app"
  local verifier="${GITHUB_ROOT}/djconnect/scripts/runner/verify_apple_internal_release_readiness.py"
  [[ -d "$apple_repository/DJConnectApp.xcodeproj" ]] || die "Apple project is unavailable at $apple_repository."
  [[ -f "$verifier" ]] || die "Apple internal-release verifier is unavailable at $verifier."

  if [[ -z "$APPLE_TEAM_ID" ]]; then
    APPLE_TEAM_ID="$(sed -nE 's/.*DEVELOPMENT_TEAM = ([A-Z0-9]{10});.*/\1/p' "$apple_repository/DJConnectApp.xcodeproj/project.pbxproj" | sort -u | head -n 1)"
  fi
  [[ "$APPLE_TEAM_ID" =~ ^[A-Z0-9]{10}$ ]] || die 'No Apple Developer Team ID was supplied or discovered from the Apple project.'

  log 'Opening Xcode for Apple Developer account registration and provisioning refresh.'
  run open -a Xcode
  if [[ "$DRY_RUN" == '0' ]]; then
    printf 'In Xcode, sign in with the DJConnect Apple Developer account and refresh/download managed profiles. Press Return when complete. ' >&2
    read -r
  fi

  if [[ -z "$APPLE_DEVELOPMENT_IDENTITY" ]]; then
    local candidates
    candidates="$(security find-identity -v -p codesigning 2>/dev/null | awk -F'"' '/Apple Development:/{print $2}')"
    if [[ "$DRY_RUN" == '1' ]]; then
      APPLE_DEVELOPMENT_IDENTITY="Apple Development: <account> ($APPLE_TEAM_ID)"
    else
      printf 'Available Apple Development identities:\n%s\n' "$candidates" >&2
      read -r -p 'Paste the exact Apple Development identity to use: ' APPLE_DEVELOPMENT_IDENTITY
    fi
  fi
  [[ -n "$APPLE_DEVELOPMENT_IDENTITY" ]] || die 'An Apple Development signing identity is required.'

  run python3 "$verifier" --apple-repo "$apple_repository" --team-id "$APPLE_TEAM_ID" --signing-identity "$APPLE_DEVELOPMENT_IDENTITY"
  local macbook_uuid
  macbook_uuid="$(ioreg -rd1 -c IOPlatformExpertDevice | awk -F'"' '/IOPlatformUUID/{print $4; exit}')"
  [[ "$macbook_uuid" =~ ^[0-9A-Fa-f-]{36}$ ]] || die 'Could not determine this MacBook hardware UUID.'
  if [[ "$DRY_RUN" == '1' ]]; then
    printf 'DRY: update GitHub environment apple-secure-distribution with this MacBook UUID and Apple Development identity\n'
    return
  fi
  printf '%s' "$macbook_uuid" | gh secret set DJCONNECT_APPLE_MACBOOK_HARDWARE_UUID --repo "$ORG/djconnect-app" --env apple-secure-distribution
  printf '%s' "$APPLE_DEVELOPMENT_IDENTITY" | gh secret set DJCONNECT_APPLE_DEVELOPMENT_SIGNING_IDENTITY --repo "$ORG/djconnect-app" --env apple-secure-distribution
  log 'Apple internal-release readiness passed and the new MacBook relay environment binding was updated.'
}

audit_apple_github_configuration() {
  if ! profile_enabled apple; then
    return
  fi
  log 'Auditing Apple Secure Distribution GitHub Environment configuration by name only.'
  run gh secret list --repo "$ORG/djconnect-app" --env apple-secure-distribution
  run gh variable list --repo "$ORG/djconnect-app" --env apple-secure-distribution
  cat <<'EOF'

Apple Secure Distribution recovery inventory:
  DJCONNECT_APPLE_MACBOOK_HARDWARE_UUID
    New Mac-specific value. Updated automatically by
    --configure-apple-internal-release after local readiness passes.
  DJCONNECT_APPLE_DEVELOPMENT_SIGNING_IDENTITY
    Update when the restored/local Apple Development identity name differs.
    Updated automatically by --configure-apple-internal-release.
  DJCONNECT_APPLE_IPHONE_UDID and DJCONNECT_APPLE_WATCH_UDID
    Physical-device values, not Mac-specific. Keep them unchanged unless the
    iPhone or Watch was replaced; then update each in the same Environment.
  Host-local paths
    None are stored as Apple GitHub Environment secrets or variables. Runner,
    keychain, profile and Docker paths are discovered locally by recovery and
    must never be copied into GitHub configuration.
EOF
}

clone_or_update() {
  local repository="$1"
  local directory="$GITHUB_ROOT/$repository"
  run mkdir -p "$GITHUB_ROOT"
  if [[ -d "$directory/.git" ]]; then
    if [[ "$DRY_RUN" == '0' ]] && [[ -n "$(git -C "$directory" status --porcelain)" ]]; then
      warn "$repository has local changes; preserving it without update."
      return
    fi
    run_in_dir "$directory" git fetch origin main
    run_in_dir "$directory" git switch main
    run_in_dir "$directory" git pull --ff-only origin main
    return
  fi
  run gh repo clone "$ORG/$repository" "$directory" -- --branch main
}

prepare_repositories() {
  log 'Preparing repositories required by the macOS runner profiles.'
  clone_or_update djconnect
  clone_or_update djconnect-app
  clone_or_update djconnect-esp32
  clone_or_update djconnect-pi
}

bootstrap_developer_workstation() {
  if [[ "$SKIP_DEVELOPER_WORKSTATION" == '1' ]]; then
    return
  fi
  local central_repository="$GITHUB_ROOT/djconnect"
  local onboarding="$central_repository/tools/dev_onboarding_macos.sh"
  [[ -f "$onboarding" ]] || die "The full developer onboarding script is unavailable at $onboarding."
  if [[ -n "$NGROK_DOMAIN" && -z "${NGROK_AUTHTOKEN:-}" && "$PROMPT_NGROK_AUTH" == '1' ]]; then
    prompt_secret 'ngrok authtoken'
    export NGROK_AUTHTOKEN="$REPLY"
    unset REPLY
  fi
  if [[ -z "$NGROK_DOMAIN" ]]; then
    warn 'No ngrok domain supplied; the developer onboarding will leave the optional persistent tunnel unconfigured.'
  elif [[ -z "${NGROK_AUTHTOKEN:-}" ]]; then
    die 'An ngrok domain requires NGROK_AUTHTOKEN or --prompt-ngrok-auth.'
  fi
  log 'Restoring the complete DJConnect macOS developer workstation.'
  local -a onboarding_args=(tools/dev_onboarding_macos.sh --all --yes --warm-sudo --no-log-file)
  if [[ "$DRY_RUN" == '1' ]]; then
    onboarding_args+=(--dry-run)
  fi
  if [[ -n "$NGROK_DOMAIN" ]]; then
    onboarding_args+=(--ngrok-domain "$NGROK_DOMAIN")
  fi
  run_in_dir "$central_repository" bash "${onboarding_args[@]}"
}

profile_enabled() {
  local profile="$1"
  [[ "$PROFILE_SELECTION" == 'all' ]] && return 0
  [[ ",$PROFILE_SELECTION," == *",$profile,"* ]]
}

profile_values() {
  local profile="$1"
  case "$profile" in
    apple)
      PROFILE_REPOSITORY='djconnect-app'
      PROFILE_RUNNER_NAME='djconnect-apple-macos'
      PROFILE_LABELS='internal-release,qualification,apple'
      ;;
    private-network)
      PROFILE_REPOSITORY='djconnect'
      PROFILE_RUNNER_NAME='djconnect-private-network-relay'
      PROFILE_LABELS='internal-release,private-network-deployment'
      ;;
    esp32)
      PROFILE_REPOSITORY='djconnect-esp32'
      PROFILE_RUNNER_NAME='djconnect-esp32-firmware'
      PROFILE_LABELS='internal-release,qualification,firmware,esp32,private-network-deployment'
      ;;
    pi)
      PROFILE_REPOSITORY='djconnect-pi'
      PROFILE_RUNNER_NAME='djconnect-pi-readiness'
      PROFILE_LABELS='internal-release,private-network-deployment'
      ;;
    *) die "Unknown runner profile: $profile" ;;
  esac
}

runner_release_metadata() {
  local metadata asset_name
  metadata="$(gh api repos/actions/runner/releases/latest)"
  asset_name='actions-runner-osx-arm64-'
  RUNNER_RELEASE_TAG="$(jq -r '.tag_name' <<<"$metadata")"
  asset_name+="${RUNNER_RELEASE_TAG}.tar.gz"
  RUNNER_ARCHIVE_URL="$(jq -r --arg name "$asset_name" '.assets[] | select(.name == $name) | .browser_download_url' <<<"$metadata")"
  RUNNER_ARCHIVE_DIGEST="$(jq -r --arg name "$asset_name" '.assets[] | select(.name == $name) | .digest // empty' <<<"$metadata")"
  [[ -n "$RUNNER_ARCHIVE_URL" && "$RUNNER_ARCHIVE_URL" != 'null' ]] || die "GitHub did not publish $asset_name in the latest actions/runner release."
  [[ "$RUNNER_ARCHIVE_DIGEST" =~ ^sha256:[0-9a-fA-F]{64}$ ]] || die "GitHub did not publish a SHA-256 digest for $asset_name."
}

registration_token() {
  local repository="$1"
  gh api --method POST "repos/$ORG/$repository/actions/runners/registration-token" --jq '.token'
}

install_runner_profile() {
  local profile="$1"
  profile_values "$profile"
  local install_dir="$RUNNER_ROOT/$PROFILE_RUNNER_NAME"
  local token archive_file actual_sha256

  log "Configuring $PROFILE_RUNNER_NAME for $ORG/$PROFILE_REPOSITORY."
  if [[ -e "$install_dir/.runner" ]]; then
    warn "$PROFILE_RUNNER_NAME is already configured in $install_dir; preserving the existing registration."
    return
  fi
  [[ ! -e "$install_dir" ]] || die "$install_dir exists but is not a configured runner. Move it aside or choose a new --runner-root."

  if [[ "$DRY_RUN" == '1' ]]; then
    printf 'DRY: fetch a short-lived registration token for %s/%s\n' "$ORG" "$PROFILE_REPOSITORY"
    printf 'DRY: download the latest actions/runner osx-arm64 release into %s\n' "$install_dir"
    printf 'DRY: configure %s with labels %s and install its launchd service\n' "$PROFILE_RUNNER_NAME" "$PROFILE_LABELS"
    return
  fi

  runner_release_metadata
  token="$(registration_token "$PROFILE_REPOSITORY")"
  run mkdir -p "$install_dir"
  archive_file="$(mktemp -t djconnect-actions-runner)"
  trap 'rm -f "$archive_file"' RETURN
  curl --fail --location --silent --show-error --output "$archive_file" "$RUNNER_ARCHIVE_URL"
  actual_sha256="$(shasum -a 256 "$archive_file" | awk '{print $1}')"
  [[ "sha256:$actual_sha256" == "$RUNNER_ARCHIVE_DIGEST" ]] || die "Actions runner archive SHA-256 does not match GitHub release metadata."
  tar -xzf "$archive_file" -C "$install_dir"
  rm -f "$archive_file"
  trap - RETURN
  run_in_dir "$install_dir" ./config.sh --unattended --replace --url "https://github.com/$ORG/$PROFILE_REPOSITORY" --token "$token" --name "$PROFILE_RUNNER_NAME" --labels "$PROFILE_LABELS" --work _work
  run_in_dir "$install_dir" sudo ./svc.sh install "$(id -un)"
  run_in_dir "$install_dir" sudo ./svc.sh start
}

install_maintenance() {
  local app_root="$GITHUB_ROOT/djconnect-app"
  [[ -f "$app_root/scripts/runner/install_macos_ci_tooling_maintenance.sh" ]] || die 'The macOS maintenance installer is unavailable after repository preparation.'
  log 'Installing and verifying daily macOS runner tooling maintenance.'
  run_in_dir "$app_root" bash scripts/runner/install_macos_ci_tooling_maintenance.sh --run-now
}

refresh_host_tooling() {
  local formula cask
  log 'Updating all Homebrew-managed DJConnect host tooling.'
  ensure_homebrew
  run brew update
  for formula in git gh jq node python@3.12 xcodegen swiftlint xcbeautify create-dmg mas xcodes platformio; do
    run brew install "$formula"
    run brew upgrade "$formula"
  done
  for cask in docker dotnet-sdk parallels; do
    if [[ "$DRY_RUN" == '1' ]]; then
      printf 'DRY: upgrade Homebrew cask %s when already installed\n' "$cask"
    elif brew list --cask "$cask" >/dev/null 2>&1; then
      run brew upgrade --cask "$cask"
    fi
  done
  if [[ "$SKIP_CODEX" == '0' ]]; then
    run npm install -g @openai/codex
  fi
  # Xcode itself is deliberately not upgraded here. The qualified line supplied
  # to --xcode-version remains the release-capable Xcode selection.
  run sudo xcodebuild -runFirstLaunch
}

check_reboot_required() {
  if [[ "$DRY_RUN" == '1' ]]; then
    printf 'DRY: inspect macOS Software Update for pending restart/reboot requirements\n'
    return
  fi
  local updates
  updates="$(softwareupdate --list 2>&1 || true)"
  if [[ -e /var/run/reboot-required ]] || grep -Eqi '\[(restart|reboot)\]|restart required|reboot required' <<<"$updates"; then
    printf '%s\n' "$updates" >&2
    die 'macOS reports a pending restart/reboot requirement. Restart the MacBook, then rerun the recovery bootstrap for final verification.'
  fi
  log 'macOS Software Update reports no pending restart/reboot requirement.'
}

verify_runner_online() {
  local profile repository runner_name deadline state
  for profile in apple private-network esp32 pi; do
    profile_enabled "$profile" || continue
    profile_values "$profile"
    repository="$PROFILE_REPOSITORY"
    runner_name="$PROFILE_RUNNER_NAME"
    if [[ "$DRY_RUN" == '1' ]]; then
      printf 'DRY: wait for GitHub runner %s in %s to report online with its registered labels\n' "$runner_name" "$repository"
      continue
    fi
    deadline=$((SECONDS + 90))
    state=''
    while (( SECONDS < deadline )); do
      state="$(gh api "repos/$ORG/$repository/actions/runners" | jq -r --arg name "$runner_name" '.runners[] | select(.name == $name) | .status' | head -n 1)"
      [[ "$state" == 'online' ]] && break
      sleep 3
    done
    [[ "$state" == 'online' ]] || die "GitHub runner $runner_name did not report online within 90 seconds."
    log "GitHub runner $runner_name is online."
  done
}

run_initial_verification() {
  if [[ "$SKIP_DEVELOPER_WORKSTATION" == '1' ]]; then
    warn 'Skipping developer-workstation verification because --skip-developer-workstation was selected.'
    verify_runner_online
    return
  fi
  local central_repository="$GITHUB_ROOT/djconnect"
  log 'Running initial post-recovery verification for the complete local developer and runner host.'
  local -a verification_args=(tools/dev_onboarding_macos.sh --steps 21,22 --yes --no-log-file)
  if [[ "$DRY_RUN" == '1' ]]; then
    verification_args+=(--dry-run)
  fi
  run_in_dir "$central_repository" bash "${verification_args[@]}"
  verify_launchd_services
  verify_runner_online
  log 'Initial post-recovery verification passed.'
}

verify_launchd_services() {
  local uid_value="$(id -u)"
  local profile install_dir
  for profile in apple private-network esp32 pi; do
    if profile_enabled "$profile"; then
      profile_values "$profile"
      install_dir="$RUNNER_ROOT/$PROFILE_RUNNER_NAME"
      if [[ "$DRY_RUN" == '1' ]]; then
        printf 'DRY: verify system launchd status for %s through svc.sh\n' "$PROFILE_RUNNER_NAME"
      else
        [[ -f "$install_dir/.runner" ]] || die "Runner $PROFILE_RUNNER_NAME is not registered."
        run_in_dir "$install_dir" sudo ./svc.sh status
      fi
    fi
  done
  if [[ "$DRY_RUN" == '1' ]]; then
    printf 'DRY: verify gui/%s/com.djconnect.ci-tooling-maintenance is loaded\n' "$uid_value"
  else
    launchctl print "gui/$uid_value/com.djconnect.ci-tooling-maintenance" >/dev/null || die 'macOS CI-tooling maintenance LaunchAgent is not loaded.'
  fi
  if [[ -n "$NGROK_DOMAIN" ]]; then
    if [[ "$DRY_RUN" == '1' ]]; then
      printf 'DRY: verify gui/%s/dev.djconnect.homeassistant.ngrok is loaded\n' "$uid_value"
    else
      launchctl print "gui/$uid_value/dev.djconnect.homeassistant.ngrok" >/dev/null || die 'Home Assistant ngrok LaunchAgent is not loaded.'
    fi
  fi
}

prompt_secret() {
  local prompt="$1"
  local value
  if [[ "$DRY_RUN" == '1' ]]; then
    printf 'DRY: prompt invisibly for %s\n' "$prompt"
    REPLY='dry-run-secret-placeholder'
    return
  fi
  read -r -s -p "$prompt: " value
  printf '\n' >&2
  REPLY="$value"
}

configure_signing_keychain() {
  local login_keychain keychain_password p12_password profiles_target
  if [[ -z "$SIGNING_P12" && "$CONFIGURE_KEYCHAIN_ACCESS" == '0' && -z "$PROVISIONING_PROFILES_DIR" ]]; then
    return
  fi
  login_keychain="$(security login-keychain | tr -d '\"')"

  if [[ -n "$SIGNING_P12" ]]; then
    [[ -f "$SIGNING_P12" ]] || die "Signing identity does not exist: $SIGNING_P12"
    prompt_secret 'P12 password'
    p12_password="$REPLY"
    if [[ "$DRY_RUN" == '1' ]]; then
      printf 'DRY: security import %q into %q with non-interactive Apple tool ACL\n' "$SIGNING_P12" "$login_keychain"
    else
      security import "$SIGNING_P12" -k "$login_keychain" -P "$p12_password" -T /usr/bin/codesign -T /usr/bin/xcodebuild -T /usr/bin/productbuild -T /usr/bin/security
    fi
    unset p12_password REPLY
    CONFIGURE_KEYCHAIN_ACCESS=1
  fi

  if [[ -n "$PROVISIONING_PROFILES_DIR" ]]; then
    [[ -d "$PROVISIONING_PROFILES_DIR" ]] || die "Provisioning-profile directory does not exist: $PROVISIONING_PROFILES_DIR"
    profiles_target="$HOME/Library/MobileDevice/Provisioning Profiles"
    run mkdir -p "$profiles_target"
    local profile
    local found=0
    while IFS= read -r -d '' profile; do
      found=1
      run cp "$profile" "$profiles_target/"
    done < <(find "$PROVISIONING_PROFILES_DIR" -type f -name '*.mobileprovision' -print0)
    (( found == 1 )) || die "No .mobileprovision files found in $PROVISIONING_PROFILES_DIR"
  fi

  if [[ "$CONFIGURE_KEYCHAIN_ACCESS" == '1' ]]; then
    prompt_secret 'Login keychain password'
    keychain_password="$REPLY"
    if [[ "$DRY_RUN" == '1' ]]; then
      printf 'DRY: security unlock-keychain and set Apple tool partition list on %q\n' "$login_keychain"
    else
      security unlock-keychain -p "$keychain_password" "$login_keychain"
      security set-key-partition-list -S apple-tool:,apple:,codesign:,productbuild:,xcodebuild: -s -k "$keychain_password" "$login_keychain"
      security find-identity -v -p codesigning "$login_keychain"
    fi
    unset keychain_password REPLY
  fi
}

report_signing_recovery() {
  cat <<'EOF'

Apple signing recovery is local-only. When supplied with --signing-p12,
--provisioning-profiles-dir and --configure-keychain-access, this bootstrap
imports local material and grants Apple build tools non-interactive key access.
It never fetches, logs or stores certificates, private keys, profiles or Apple
account credentials. Run Apple runner qualification before private distribution.
EOF
}

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --profiles) PROFILE_SELECTION="${2:?--profiles requires a value}"; shift 2 ;;
    --github-root) GITHUB_ROOT="${2:?--github-root requires a value}"; shift 2 ;;
    --runner-root) RUNNER_ROOT="${2:?--runner-root requires a value}"; shift 2 ;;
    --skip-codex) SKIP_CODEX=1; shift ;;
    --xcode-version) XCODE_VERSION="${2:?--xcode-version requires a value}"; shift 2 ;;
    --signing-p12) SIGNING_P12="${2:?--signing-p12 requires a value}"; shift 2 ;;
    --provisioning-profiles-dir) PROVISIONING_PROFILES_DIR="${2:?--provisioning-profiles-dir requires a value}"; shift 2 ;;
    --configure-keychain-access) CONFIGURE_KEYCHAIN_ACCESS=1; shift ;;
    --install-parallels) INSTALL_PARALLELS=1; shift ;;
    --skip-developer-workstation) SKIP_DEVELOPER_WORKSTATION=1; shift ;;
    --ngrok-domain) NGROK_DOMAIN="${2:?--ngrok-domain requires a value}"; shift 2 ;;
    --prompt-ngrok-auth) PROMPT_NGROK_AUTH=1; shift ;;
    --configure-apple-internal-release) CONFIGURE_APPLE_INTERNAL_RELEASE=1; shift ;;
    --apple-team-id) APPLE_TEAM_ID="${2:?--apple-team-id requires a value}"; shift 2 ;;
    --apple-development-identity) APPLE_DEVELOPMENT_IDENTITY="${2:?--apple-development-identity requires a value}"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    --log-file) LOG_FILE="${2:?--log-file requires a value}"; shift 2 ;;
    --no-log-file) LOG_FILE='none'; shift ;;
    --report-file) REPORT_FILE="${2:?--report-file requires a value}"; shift 2 ;;
    --no-report-file) REPORT_FILE='none'; shift ;;
    --no-step-retry) ALLOW_STEP_RETRY=0; shift ;;
    --no-color) NO_COLOR=1; shift ;;
    --help|-h) usage; exit 0 ;;
    *) die "Unknown option: $1" ;;
  esac
done

if [[ -t 1 ]]; then
  ORIGINAL_STDOUT_IS_TTY=1
fi
init_style
start_logging
start_report
trap cleanup EXIT
run_phase 'macOS host preflight' ensure_macos_arm64
run_phase 'Administrator sudo gate' warm_sudo
run_phase 'Host tooling setup' ensure_tooling
run_phase 'Xcode qualification' ensure_xcode
run_phase 'Parallels Desktop availability' ensure_parallels
run_phase 'GitHub CLI authentication' ensure_github_auth
run_phase 'Repository preparation' prepare_repositories
run_phase 'Developer workstation recovery' bootstrap_developer_workstation
run_phase 'Docker Hub authentication' ensure_docker_hub_auth

for profile in apple private-network esp32 pi; do
  if profile_enabled "$profile"; then
    run_phase "GitHub Actions runner profile: $profile" install_runner_profile "$profile"
  fi
done

run_phase 'Daily macOS tooling maintenance' install_maintenance
run_phase 'Tooling currency refresh' refresh_host_tooling
run_phase 'Reboot requirement check' check_reboot_required
run_phase 'Runner services and launchd validation' verify_launchd_services
run_phase 'Apple signing recovery' configure_signing_keychain
run_phase 'Apple internal-release readiness' configure_apple_internal_release
run_phase 'GitHub Apple configuration audit' audit_apple_github_configuration
run_phase 'Initial post-recovery verification' run_initial_verification
report_signing_recovery
