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
  --dry-run             Print changes without executing them.
  --help                Show this help.

No GitHub registration token is passed on the command line. After `gh auth
login`, the script obtains one short-lived token per repository through the
authenticated GitHub API and gives it directly to the runner configurator.

Signing material must be supplied from a local secure backup. It is never
downloaded from GitHub, written to this repository or emitted to a log.
EOF
}

log() { printf '\n==> %s\n' "$*"; }
warn() { printf 'WARN: %s\n' "$*" >&2; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

run() {
  if [[ "$DRY_RUN" == '1' ]]; then
    printf 'DRY:'
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
    printf 'DRY: (cd %q &&' "$directory"
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
  run gh auth login --hostname github.com --git-protocol https --web
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
  run docker login
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
  if [[ -n "$NGROK_DOMAIN" ]]; then
    run_in_dir "$central_repository" bash tools/dev_onboarding_macos.sh --all --yes --warm-sudo --ngrok-domain "$NGROK_DOMAIN"
  else
    run_in_dir "$central_repository" bash tools/dev_onboarding_macos.sh --all --yes --warm-sudo
  fi
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
  run sudo ./svc.sh install "$(id -un)"
  run sudo ./svc.sh start
}

install_maintenance() {
  local app_root="$GITHUB_ROOT/djconnect-app"
  [[ -f "$app_root/scripts/runner/install_macos_ci_tooling_maintenance.sh" ]] || die 'The macOS maintenance installer is unavailable after repository preparation.'
  log 'Installing and verifying daily macOS runner tooling maintenance.'
  run_in_dir "$app_root" bash scripts/runner/install_macos_ci_tooling_maintenance.sh --run-now
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
    --dry-run) DRY_RUN=1; shift ;;
    --help|-h) usage; exit 0 ;;
    *) die "Unknown option: $1" ;;
  esac
done

ensure_macos_arm64
ensure_tooling
ensure_xcode
ensure_parallels
ensure_github_auth
prepare_repositories
bootstrap_developer_workstation
ensure_docker_hub_auth

for profile in apple private-network esp32 pi; do
  if profile_enabled "$profile"; then
    install_runner_profile "$profile"
  fi
done

install_maintenance
configure_signing_keychain
report_signing_recovery
