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
  --dry-run             Print changes without executing them.
  --help                Show this help.

No GitHub registration token is passed on the command line. After `gh auth
login`, the script obtains one short-lived token per repository through the
authenticated GitHub API and gives it directly to the runner configurator.

The Apple Developer signing certificate, private key and provisioning profiles
are intentionally not restored by this script. Import them locally after the
host bootstrap; they must never be copied into GitHub secrets or this repo.
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
  if xcodebuild -version >/dev/null 2>&1; then
    log "Using $(xcodebuild -version | tr '\n' ' ' | sed 's/ $//')."
    return
  fi

  if xcode-select -p >/dev/null 2>&1; then
    die 'Xcode Command Line Tools are present, but full Xcode is required for Apple builds. Install the approved Xcode line, select it with xcode-select, then rerun.'
  fi

  log 'Requesting Apple Command Line Tools installation.'
  run xcode-select --install || true
  die 'Finish the Apple Command Line Tools and full Xcode installation, accept its license, select it with xcode-select, then rerun this script.'
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
  run brew install git gh jq node python@3.12 xcodegen swiftlint xcbeautify create-dmg mas
  if [[ "$SKIP_CODEX" == '0' ]]; then
    run npm install -g @openai/codex
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

report_signing_recovery() {
  cat <<'EOF'

Apple signing recovery remains intentionally manual:
  1. Install/select the latest qualified Xcode line and accept its license.
  2. Import the Apple Development/Developer ID certificate and private key into
     this runner user's login keychain.
  3. Restore the required provisioning profiles locally.
  4. Run the Apple runner-qualification workflow before private distribution.

No certificate, private key, provisioning profile or Apple account credential
is fetched, logged or stored by this bootstrap.
EOF
}

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --profiles) PROFILE_SELECTION="${2:?--profiles requires a value}"; shift 2 ;;
    --github-root) GITHUB_ROOT="${2:?--github-root requires a value}"; shift 2 ;;
    --runner-root) RUNNER_ROOT="${2:?--runner-root requires a value}"; shift 2 ;;
    --skip-codex) SKIP_CODEX=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    --help|-h) usage; exit 0 ;;
    *) die "Unknown option: $1" ;;
  esac
done

ensure_macos_arm64
ensure_xcode
ensure_tooling
ensure_github_auth
prepare_repositories

for profile in apple private-network esp32 pi; do
  if profile_enabled "$profile"; then
    install_runner_profile "$profile"
  fi
done

install_maintenance
report_signing_recovery
