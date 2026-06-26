#!/usr/bin/env bash
set -euo pipefail

SCRIPT_NAME="$(basename "$0")"
ORIGINAL_ARGS="$*"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GITHUB_ROOT="$(dirname "$REPO_ROOT")"
DEFAULT_HA_CONFIG_DIR="${HOME}/docker/homeassistant/config"
HA_CONFIG_DIR="${HA_CONFIG_DIR:-$DEFAULT_HA_CONFIG_DIR}"
HA_CONTAINER_NAME="${HA_CONTAINER_NAME:-homeassistant}"
HA_IMAGE="${HA_IMAGE:-ghcr.io/home-assistant/home-assistant:stable}"
MA_CONTAINER_NAME="${MA_CONTAINER_NAME:-music-assistant-server}"
MA_IMAGE="${MA_IMAGE:-ghcr.io/music-assistant/server:latest}"
MA_DATA_DIR="${MA_DATA_DIR:-${HOME}/docker/music-assistant-server/data}"
MACOS_VM_NAME="${MACOS_VM_NAME:-DJConnect macOS Dev}"
MACOS_VERSION="${MACOS_VERSION:-}"
WINDOWS_VM_NAME="${WINDOWS_VM_NAME:-DJConnect Windows 11 ARM Dev}"
WINDOWS_ISO_PATH="${WINDOWS_ISO_PATH:-}"
ONBOARDING_ENV_FILE="${ONBOARDING_ENV_FILE:-$REPO_ROOT/.djconnect-onboarding.env}"
LOG_DIR="${LOG_DIR:-$REPO_ROOT/logs}"
LOG_FILE="${LOG_FILE:-}"
ASSUME_YES=0
WARM_SUDO=0
PROMPT_SECRETS=0
PLAN_ONLY=0
APPLY_UPGRADES=0
RUN_CI_PUSH=0
DRY_RUN=0
NO_COLOR_MODE="${NO_COLOR_MODE:-0}"
SELECTED_STEPS=""
SUDO_KEEPALIVE_PID=""
LOGGING_STARTED=0
STEP_TOTAL=0
STEP_INDEX=0
E2E_VERSION="${E2E_VERSION:-3.1.999}"
CI_BRANCH="${CI_BRANCH:-}"
CLR_RESET=""
CLR_BOLD=""
CLR_DIM=""
CLR_BLUE=""
CLR_GREEN=""
CLR_YELLOW=""
CLR_RED=""
CLR_CYAN=""

init_style() {
  if [[ "$NO_COLOR_MODE" == "1" || -n "${NO_COLOR:-}" || ! -t 1 ]]; then
    return
  fi
  CLR_RESET="$(tput sgr0 2>/dev/null || true)"
  CLR_BOLD="$(tput bold 2>/dev/null || true)"
  CLR_DIM="$(tput dim 2>/dev/null || true)"
  CLR_BLUE="$(tput setaf 4 2>/dev/null || true)"
  CLR_GREEN="$(tput setaf 2 2>/dev/null || true)"
  CLR_YELLOW="$(tput setaf 3 2>/dev/null || true)"
  CLR_RED="$(tput setaf 1 2>/dev/null || true)"
  CLR_CYAN="$(tput setaf 6 2>/dev/null || true)"
}

style() {
  local color="$1"
  shift
  printf '%s%s%s' "$color" "$*" "$CLR_RESET"
}

log() {
  printf '\n%s %s %s\n' "$(style "$CLR_DIM" "[$(date '+%Y-%m-%d %H:%M:%S')]")" "$(style "$CLR_BLUE$CLR_BOLD" "==>")" "$*"
}

ok() {
  printf '%s %s\n' "$(style "$CLR_GREEN$CLR_BOLD" "[OK]")" "$*"
}

status_ok() {
  printf '%s %s\n' "$(style "$CLR_GREEN$CLR_BOLD" "OK  ")" "$*"
}

status_miss() {
  printf '%s %s\n' "$(style "$CLR_RED$CLR_BOLD" "MISS")" "$*"
}

quote_cmd() {
  local out=""
  local arg
  local quoted
  for arg in "$@"; do
    printf -v quoted '%q' "$arg"
    out="${out:+$out }$quoted"
  done
  printf '%s' "$out"
}

run() {
  if [[ "$DRY_RUN" == "1" ]]; then
    printf '%s %s\n' "$(style "$CLR_CYAN$CLR_BOLD" "DRY")" "$(quote_cmd "$@")"
    return 0
  fi
  "$@"
}

run_shell() {
  local cmd="$1"
  if [[ "$DRY_RUN" == "1" ]]; then
    printf '%s %s\n' "$(style "$CLR_CYAN$CLR_BOLD" "DRY")" "$cmd"
    return 0
  fi
  /bin/bash -c "$cmd"
}

run_in_dir() {
  local dir="$1"
  shift
  if [[ ! -d "$dir" ]]; then
    warn "Skipping missing directory: $dir"
    return 0
  fi
  if [[ "$DRY_RUN" == "1" ]]; then
    printf '%s cd %s && %s\n' "$(style "$CLR_CYAN$CLR_BOLD" "DRY")" "$(quote_cmd "$dir")" "$(quote_cmd "$@")"
    return 0
  fi
  (cd "$dir" && "$@")
}

warn() {
  printf '%s %s %s\n' "$(style "$CLR_DIM" "[$(date '+%Y-%m-%d %H:%M:%S')]")" "$(style "$CLR_YELLOW$CLR_BOLD" "WARN")" "$*" >&2
}

die() {
  printf '%s %s %s\n' "$(style "$CLR_DIM" "[$(date '+%Y-%m-%d %H:%M:%S')]")" "$(style "$CLR_RED$CLR_BOLD" "ERROR")" "$*" >&2
  exit 1
}

usage() {
  cat <<EOF
Usage: $SCRIPT_NAME [options]

Automates DJConnect developer onboarding on a clean-ish macOS machine.

Options:
  --all                 Run all steps.
  --core                Run the Home Assistant integration core steps, 3-12.
  --steps 1,2,5         Run selected numbered steps.
  --yes                 Use defaults and skip confirmation prompts.
  --ha-config-dir DIR   Home Assistant config directory.
                       Default: $DEFAULT_HA_CONFIG_DIR
  --vm-name NAME        Parallels macOS VM name for step 1.
                       Default: $MACOS_VM_NAME
  --macos-version VER   Optional macOS full installer version to fetch first.
                       Example: 15.5
  --windows-vm-name NAME
                       Parallels Windows 11 ARM VM name for step 2.
                       Default: $WINDOWS_VM_NAME
  --windows-iso PATH    Optional Windows 11 ARM ISO path for step 2.
  --warm-sudo           Ask for sudo once and keep the timestamp fresh.
  --prompt-secrets      Prompt for optional local tokens/API keys before steps.
  --plan                Print selected steps and exit without making changes.
  --dry-run             Print mutating commands instead of executing them.
  --apply-upgrades      Allow step 24 to modify installed packages/tooling.
  --e2e-version VER     Version passed to release dry-run scripts.
                       Default: $E2E_VERSION
  --run-ci-push         Allow step 26 to push a CI smoke-test commit.
  --ci-branch BRANCH    Branch name for step 26.
                       Default: codex/onboarding-ci-smoke-<timestamp>
  --ma-data-dir DIR     Music Assistant server data directory for step 27.
                       Default: $MA_DATA_DIR
  --log-file FILE       Write a persistent run log. Default is timestamped.
  --no-log-file         Disable persistent run logging.
  --no-color            Disable ANSI colors and styled terminal output.
  --env-file FILE       Local onboarding env file for optional tokens.
                       Default: $ONBOARDING_ENV_FILE
  --help                Show this help.

Environment overrides:
  HA_CONFIG_DIR         Same as --ha-config-dir.
  HA_CONTAINER_NAME     Default: homeassistant.
  HA_IMAGE              Default: ghcr.io/home-assistant/home-assistant:stable.
  MA_CONTAINER_NAME     Default: music-assistant-server.
  MA_IMAGE              Default: ghcr.io/music-assistant/server:latest.
  MA_DATA_DIR           Same as --ma-data-dir.
  MACOS_VM_NAME         Same as --vm-name.
  MACOS_VERSION         Same as --macos-version.
  WINDOWS_VM_NAME       Same as --windows-vm-name.
  WINDOWS_ISO_PATH      Same as --windows-iso.
  ONBOARDING_ENV_FILE   Same as --env-file.
  LOG_DIR               Directory for default timestamped logs.
  LOG_FILE              Explicit persistent run log path.
  NO_COLOR              Standard way to disable colored output.
  E2E_VERSION           Same as --e2e-version.
  CI_BRANCH             Same as --ci-branch.
EOF
}

confirm() {
  local prompt="$1"
  if [[ "$ASSUME_YES" == "1" ]]; then
    return 0
  fi
  read -r -p "$prompt [Y/n] " reply
  case "${reply:-Y}" in
    y|Y|yes|YES) return 0 ;;
    *) return 1 ;;
  esac
}

need_macos() {
  [[ "$(uname -s)" == "Darwin" ]] || die "This script is intended for macOS."
}

have() {
  command -v "$1" >/dev/null 2>&1
}

warm_sudo() {
  log "Refreshing sudo credentials."
  sudo -v
  while true; do
    sudo -n true 2>/dev/null || exit
    sleep 60
  done &
  SUDO_KEEPALIVE_PID="$!"
}

cleanup() {
  if [[ -n "$SUDO_KEEPALIVE_PID" ]]; then
    kill "$SUDO_KEEPALIVE_PID" >/dev/null 2>&1 || true
  fi
}

start_logging() {
  if [[ "$PLAN_ONLY" == "1" || "$LOG_FILE" == "none" || "$LOGGING_STARTED" == "1" ]]; then
    return
  fi
  if [[ -z "$LOG_FILE" ]]; then
    mkdir -p "$LOG_DIR"
    LOG_FILE="$LOG_DIR/dev_onboarding_$(date '+%Y%m%d_%H%M%S').log"
  else
    mkdir -p "$(dirname "$LOG_FILE")"
  fi
  touch "$LOG_FILE"
  chmod 600 "$LOG_FILE"
  exec > >(tee -a "$LOG_FILE") 2>&1
  LOGGING_STARTED=1
  log "Persistent log: $LOG_FILE"
  log "Command: $SCRIPT_NAME ${ORIGINAL_ARGS:-}"
}

load_onboarding_env() {
  if [[ -f "$ONBOARDING_ENV_FILE" ]]; then
    # shellcheck disable=SC1090
    . "$ONBOARDING_ENV_FILE"
  fi
}

write_secret_line() {
  local key="$1"
  local value="$2"
  local tmp_file
  mkdir -p "$(dirname "$ONBOARDING_ENV_FILE")"
  touch "$ONBOARDING_ENV_FILE"
  chmod 600 "$ONBOARDING_ENV_FILE"
  tmp_file="${ONBOARDING_ENV_FILE}.tmp.$$"
  if grep -q "^${key}=" "$ONBOARDING_ENV_FILE"; then
    awk -v key="$key" -v value="$value" '
      BEGIN { replacement = key "=" sq(value) }
      function sq(s, out, i, c) {
        out = "'\''"
        for (i = 1; i <= length(s); i++) {
          c = substr(s, i, 1)
          out = out (c == "'\''" ? "'\''\\'\'''\''" : c)
        }
        return out "'\''"
      }
      index($0, key "=") == 1 { print replacement; next }
      { print }
    ' "$ONBOARDING_ENV_FILE" > "$tmp_file"
    mv "$tmp_file" "$ONBOARDING_ENV_FILE"
  else
    printf '%s=%q\n' "$key" "$value" >> "$ONBOARDING_ENV_FILE"
  fi
  chmod 600 "$ONBOARDING_ENV_FILE"
}

prompt_secret() {
  local key="$1"
  local label="$2"
  local current="${!key-}"
  if [[ -n "$current" ]]; then
    log "$key already set in environment."
    return
  fi
  if [[ "$ASSUME_YES" == "1" ]]; then
    warn "$key not set; skipping prompt because --yes is active."
    return
  fi
  read -r -s -p "$label (leave empty to skip): " value
  printf '\n'
  if [[ -n "$value" ]]; then
    export "$key=$value"
    write_secret_line "$key" "$value"
  fi
}

collect_optional_secrets() {
  load_onboarding_env
  log "Collecting optional local tokens/API keys."
  warn "Values are stored only in $ONBOARDING_ENV_FILE with mode 0600 and must not be committed."
  prompt_secret CLOUDFLARE_API_TOKEN "Cloudflare API token for Worker/Pages validation"
  prompt_secret CLOUDFLARE_ACCOUNT_ID "Cloudflare account ID"
  prompt_secret STATS_TOKEN "Website/operator stats token"
  prompt_secret DJCONNECT_RELAY_SECRET_VALUE "DJConnect relay secret value for API provisioning"
  prompt_secret APNS_TOKEN_ENCRYPTION_KEY_VALUE "APNs token encryption key, base64 32 bytes"
  prompt_secret SPOTIFY_CLIENT_ID "Spotify Developer app Client ID for HA OAuth testing"
}

ensure_homebrew() {
  if have brew; then
    log "Homebrew already installed."
    return
  fi
  log "Installing Homebrew."
  run_shell "NONINTERACTIVE=1 /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
  if [[ -x /opt/homebrew/bin/brew ]]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
  elif [[ -x /usr/local/bin/brew ]]; then
    eval "$(/usr/local/bin/brew shellenv)"
  fi
}

preflight_url() {
  local label="$1"
  local url="$2"
  local code
  code="$(curl -L -sS -o /dev/null -w '%{http_code}' --connect-timeout 10 --max-time 25 "$url" 2>/dev/null || true)"
  case "$code" in
    2*|3*|4*)
      status_ok "$(printf 'network %-18s %s (%s)' "$label" "$url" "$code")"
      return 0
      ;;
    *)
      status_miss "$(printf 'network %-18s %s (%s)' "$label" "$url" "${code:-no response}")"
      return 1
      ;;
  esac
}

preflight_writable_path() {
  local label="$1"
  local path="$2"
  local target="$path"
  if [[ ! -e "$target" ]]; then
    target="$(dirname "$path")"
  fi
  if [[ -w "$target" ]]; then
    status_ok "$label writable via $target"
    return 0
  fi
  warn "$label is not writable: $path"
  return 1
}

preflight_port_free() {
  local port="$1"
  local label="$2"
  if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
    warn "Port $port for $label is already in use."
    return 1
  fi
  status_ok "$(printf 'port %-5s free for %s' "$port" "$label")"
  return 0
}

preflight_home_assistant_port() {
  if ! lsof -nP -iTCP:8123 -sTCP:LISTEN >/dev/null 2>&1; then
    status_ok "port 8123  free for Home Assistant"
    return 0
  fi
  if have docker && docker ps --filter "name=$HA_CONTAINER_NAME" --format '{{.Names}}' | grep -qx "$HA_CONTAINER_NAME"; then
    status_ok "port 8123  already used by $HA_CONTAINER_NAME"
    return 0
  fi
  warn "Port 8123 for Home Assistant is already in use by another process."
  return 1
}

preflight_music_assistant_port() {
  if ! lsof -nP -iTCP:8095 -sTCP:LISTEN >/dev/null 2>&1; then
    status_ok "port 8095  free for Music Assistant"
    return 0
  fi
  if have docker && docker ps --filter "name=$MA_CONTAINER_NAME" --format '{{.Names}}' | grep -qx "$MA_CONTAINER_NAME"; then
    status_ok "port 8095  already used by $MA_CONTAINER_NAME"
    return 0
  fi
  warn "Port 8095 for Music Assistant is already in use by another process."
  return 1
}

step_0_preflight() {
  need_macos
  log "Running machine, VM, hardware, filesystem and network preflight."
  local failed=0
  local warned=0
  local macos_version
  local arch
  local mem_bytes
  local mem_gb
  local cpu_count
  local disk_kb
  local disk_gb

  macos_version="$(sw_vers -productVersion 2>/dev/null || true)"
  arch="$(uname -m)"
  log "Host: macOS ${macos_version:-unknown}, arch $arch"
  case "$macos_version" in
    1[4-9].*|2[0-9].*) status_ok "macOS version $macos_version" ;;
    *) warn "macOS $macos_version may be too old. Use macOS 14 or newer for the full DJConnect toolchain."; failed=1 ;;
  esac

  mem_bytes="$(sysctl -n hw.memsize 2>/dev/null || echo 0)"
  mem_gb=$((mem_bytes / 1024 / 1024 / 1024))
  if (( mem_gb < 8 )); then
    warn "Only ${mem_gb}GB RAM detected. Minimum is 8GB; 16GB+ is recommended."
    failed=1
  elif (( mem_gb < 16 )); then
    warn "${mem_gb}GB RAM detected. This can work, but 16GB+ is recommended for Docker + Xcode + Parallels."
    warned=1
  else
    status_ok "RAM ${mem_gb}GB"
  fi

  cpu_count="$(sysctl -n hw.ncpu 2>/dev/null || echo 0)"
  if (( cpu_count < 4 )); then
    warn "Only $cpu_count CPU cores detected. Minimum recommended is 4."
    failed=1
  else
    status_ok "CPU cores $cpu_count"
  fi

  run mkdir -p "$GITHUB_ROOT" "$LOG_DIR" "$(dirname "$HA_CONFIG_DIR")" "$(dirname "$ONBOARDING_ENV_FILE")"
  preflight_writable_path "GitHub root" "$GITHUB_ROOT" || failed=1
  preflight_writable_path "Log dir" "$LOG_DIR" || failed=1
  preflight_writable_path "Home Assistant config parent" "$(dirname "$HA_CONFIG_DIR")" || failed=1
  preflight_writable_path "Env file parent" "$(dirname "$ONBOARDING_ENV_FILE")" || failed=1

  disk_kb="$(df -Pk "$GITHUB_ROOT" | awk 'NR==2 {print $4}')"
  disk_gb=$((disk_kb / 1024 / 1024))
  if (( disk_gb < 80 )); then
    warn "Only ${disk_gb}GB free at $GITHUB_ROOT. Minimum is 80GB; 120GB+ is recommended for VM/Xcode/Docker."
    failed=1
  elif (( disk_gb < 120 )); then
    warn "${disk_gb}GB free at $GITHUB_ROOT. This can work, but 120GB+ is recommended."
    warned=1
  else
    status_ok "disk free ${disk_gb}GB at $GITHUB_ROOT"
  fi

  preflight_home_assistant_port || failed=1
  preflight_music_assistant_port || warned=1
  preflight_port_free 8787 "Cloudflare Worker dev" || failed=1
  preflight_port_free 8080 "static website preview" || warned=1
  preflight_port_free 18080 "DJConnect Pi local API" || warned=1

  preflight_url "GitHub" "https://github.com" || failed=1
  preflight_url "GitHub raw" "https://raw.githubusercontent.com" || failed=1
  preflight_url "Homebrew" "https://formulae.brew.sh" || failed=1
  preflight_url "npm" "https://registry.npmjs.org" || failed=1
  preflight_url "PyPI" "https://pypi.org" || failed=1
  preflight_url "GHCR" "https://ghcr.io/v2/" || failed=1
  preflight_url "Docker Hub" "https://registry-1.docker.io/v2/" || failed=1
  preflight_url "Cloudflare" "https://api.cloudflare.com/client/v4/user/tokens/verify" || failed=1
  preflight_url "Apple updates" "https://swscan.apple.com" || failed=1

  if [[ "$arch" == "arm64" ]]; then
    if pkgutil --pkg-info com.apple.pkg.RosettaUpdateAuto >/dev/null 2>&1; then
      status_ok "Rosetta installed"
    else
      warn "Rosetta is not installed. Some third-party tooling may need it: softwareupdate --install-rosetta --agree-to-license"
      warned=1
    fi
  fi

  if have git; then
    git config --global user.name >/dev/null || { warn "git user.name is not configured."; warned=1; }
    git config --global user.email >/dev/null || { warn "git user.email is not configured."; warned=1; }
  else
    warn "git is not available yet; step 3 installs tooling after Xcode/Homebrew."
    warned=1
  fi

  if have xcodebuild; then
    xcodebuild -license check >/dev/null 2>&1 || { warn "Xcode license is not accepted yet."; warned=1; }
  else
    warn "Full Xcode is not installed yet. Apple app and Mac Catalyst builds need it."
    warned=1
  fi

  if [[ -f "$ONBOARDING_ENV_FILE" ]]; then
    local mode
    mode="$(stat -f '%Lp' "$ONBOARDING_ENV_FILE" 2>/dev/null || stat -c '%a' "$ONBOARDING_ENV_FILE" 2>/dev/null || true)"
    [[ "$mode" == "600" ]] || { warn "$ONBOARDING_ENV_FILE permissions are $mode, expected 600."; failed=1; }
  fi
  grep -q '^\.djconnect-onboarding\.env$' "$REPO_ROOT/.gitignore" || { warn ".djconnect-onboarding.env is not ignored."; failed=1; }
  grep -q '^logs/$' "$REPO_ROOT/.gitignore" || { warn "logs/ is not ignored."; failed=1; }

  if (( failed )); then
    die "Preflight failed. Fix the hard requirement(s) above before running setup."
  fi
  if (( warned )); then
    warn "Preflight completed with warnings. Setup can continue, but read the warnings above."
  else
    log "Preflight completed successfully."
  fi
}

step_0_parallels_macos_vm() {
  need_macos
  ensure_homebrew
  log "Preparing Parallels macOS VM bootstrap."
  if ! have prlctl; then
    log "Installing Parallels Desktop."
    run brew install --cask parallels
  fi
  if [[ -n "$MACOS_VERSION" ]]; then
    log "Fetching macOS full installer $MACOS_VERSION through softwareupdate."
    run softwareupdate --fetch-full-installer --full-installer-version "$MACOS_VERSION" || \
      warn "softwareupdate could not fetch macOS $MACOS_VERSION. Parallels may still download macOS during VM creation."
  fi
  run open -a "Parallels Desktop" || true
  if [[ "$DRY_RUN" == "1" ]]; then
    log "Attempting unattended macOS VM creation: $MACOS_VM_NAME."
    run prlctl create "$MACOS_VM_NAME" --distribution macos
    return
  fi
  if ! have prlctl; then
    warn "prlctl is still not on PATH. Finish Parallels first-run setup, then rerun step 1."
    return
  fi
  if prlctl list --all --output name 2>/dev/null | grep -Fxq "$MACOS_VM_NAME"; then
    log "Parallels VM '$MACOS_VM_NAME' already exists."
    return
  fi
  log "Attempting unattended macOS VM creation: $MACOS_VM_NAME."
  if run prlctl create "$MACOS_VM_NAME" --distribution macos 2>/dev/null; then
    log "Created Parallels macOS VM '$MACOS_VM_NAME'."
  elif run prlctl create "$MACOS_VM_NAME" -o macos 2>/dev/null; then
    log "Created Parallels macOS VM '$MACOS_VM_NAME'."
  else
    warn "Parallels CLI could not create the macOS VM automatically on this host/version."
    warn "The Parallels Installation Assistant is open. Choose 'Install macOS' and name the VM '$MACOS_VM_NAME'."
    warn "After first boot, run this onboarding script inside the VM with --core or selected steps."
  fi
}

step_0b_parallels_windows_vm() {
  need_macos
  ensure_homebrew
  log "Preparing Parallels Windows 11 ARM VM bootstrap."
  if [[ "$(uname -m)" != "arm64" ]]; then
    warn "This step targets Windows 11 ARM on Apple Silicon. Current arch: $(uname -m)."
  fi
  if ! have prlctl; then
    log "Installing Parallels Desktop."
    run brew install --cask parallels
  fi
  run open -a "Parallels Desktop" || true
  if [[ "$DRY_RUN" == "1" ]]; then
    log "Attempting unattended Windows 11 ARM VM creation: $WINDOWS_VM_NAME."
    if [[ -n "$WINDOWS_ISO_PATH" ]]; then
      run prlctl create "$WINDOWS_VM_NAME" --distribution win-11 --device-set cdrom0 --image "$WINDOWS_ISO_PATH"
    else
      run prlctl create "$WINDOWS_VM_NAME" --distribution win-11
    fi
    return
  fi
  if ! have prlctl; then
    warn "prlctl is still not on PATH. Finish Parallels first-run setup, then rerun step 2."
    return
  fi
  if prlctl list --all --output name 2>/dev/null | grep -Fxq "$WINDOWS_VM_NAME"; then
    log "Parallels VM '$WINDOWS_VM_NAME' already exists."
    return
  fi
  log "Attempting unattended Windows 11 ARM VM creation: $WINDOWS_VM_NAME."
  if [[ -n "$WINDOWS_ISO_PATH" ]]; then
    if [[ ! -f "$WINDOWS_ISO_PATH" && "$DRY_RUN" != "1" ]]; then
      die "Windows ISO not found: $WINDOWS_ISO_PATH"
    fi
    run prlctl create "$WINDOWS_VM_NAME" --distribution win-11 --device-set cdrom0 --image "$WINDOWS_ISO_PATH" || \
      warn "Parallels CLI could not create Windows VM from ISO automatically."
    return
  fi
  if run prlctl create "$WINDOWS_VM_NAME" --distribution win-11 2>/dev/null; then
    log "Created Parallels Windows VM '$WINDOWS_VM_NAME'."
  else
    warn "Parallels CLI could not create the Windows VM automatically on this host/version."
    warn "The Parallels Installation Assistant is open. Choose 'Get Windows 11 from Microsoft' or select a Windows 11 ARM ISO, then name the VM '$WINDOWS_VM_NAME'."
  fi
}

wait_for_home_assistant() {
  local url="http://localhost:8123"
  local max="${1:-120}"
  local i=0
  local frames='-\|/'
  local frame=0
  log "Waiting for Home Assistant at $url."
  while (( i < max )); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      if [[ -t 1 && -z "${NO_COLOR:-}" && "$NO_COLOR_MODE" != "1" ]]; then
        printf '\r\033[K'
      fi
      log "Home Assistant is responding at $url."
      return 0
    fi
    if [[ -t 1 && -z "${NO_COLOR:-}" && "$NO_COLOR_MODE" != "1" ]]; then
      printf '\r%s Waiting for Home Assistant... %ss/%ss' "$(style "$CLR_CYAN$CLR_BOLD" "${frames:frame:1}")" "$i" "$max"
      frame=$(((frame + 1) % 4))
    fi
    sleep 2
    i=$((i + 2))
  done
  if [[ -t 1 && -z "${NO_COLOR:-}" && "$NO_COLOR_MODE" != "1" ]]; then
    printf '\r\033[K'
  fi
  warn "Home Assistant did not respond within ${max}s. It may still be starting."
  return 1
}

step_1_xcode_homebrew() {
  need_macos
  log "Checking Xcode Command Line Tools."
  if ! xcode-select -p >/dev/null 2>&1; then
    log "Installing Xcode Command Line Tools. macOS may show one system dialog."
    run xcode-select --install || true
    warn "Finish the Apple installer, then rerun this script."
    return
  fi
  ensure_homebrew
}

step_2_cli_tooling() {
  ensure_homebrew
  log "Installing CLI tooling."
  run brew update
  run brew install git gh jq python@3.12 node rsync coreutils curl wget
}

step_3_docker() {
  ensure_homebrew
  if have docker; then
    log "Docker CLI already available."
  else
    log "Installing Docker Desktop."
    run brew install --cask docker
  fi
  if ! docker info >/dev/null 2>&1; then
    run open -a Docker || true
    warn "Docker Desktop is installed/opened. Finish first-run setup, then rerun step 4 or 8."
  fi
}

step_4_codex() {
  ensure_homebrew
  log "Installing/updating Codex CLI through npm."
  if ! have npm; then
    run brew install node
  fi
  run npm install -g @openai/codex
  if ! have codex; then
    warn "Codex installed, but 'codex' is not on PATH yet. Open a new terminal or check npm global bin."
  fi
}

step_5_clone_or_update_repo() {
  log "Preparing DJConnect repository."
  run mkdir -p "$(dirname "$REPO_ROOT")"
  if [[ -d "$REPO_ROOT/.git" ]]; then
    log "Repository already present at $REPO_ROOT."
    git -C "$REPO_ROOT" status --short
    return
  fi
  run git clone https://github.com/pcvantol/djconnect.git "$REPO_ROOT"
}

step_6_python_validation() {
  log "Running lightweight Python validation."
  cd "$REPO_ROOT"
  python3 -m unittest discover -s tests
  git diff --check
}

step_7_home_assistant_container() {
  step_3_docker
  if [[ "$DRY_RUN" == "1" ]]; then
    log "Dry-run: printing Home Assistant Docker container commands without requiring Docker to be running."
    run mkdir -p "$HA_CONFIG_DIR"
    run docker run -d \
      --name "$HA_CONTAINER_NAME" \
      --privileged \
      --restart unless-stopped \
      -e TZ=Europe/Amsterdam \
      -v "$HA_CONFIG_DIR:/config" \
      -p 8123:8123 \
      "$HA_IMAGE"
    log "Home Assistant will be available at http://localhost:8123 after first startup."
    return
  fi
  docker info >/dev/null 2>&1 || die "Docker is not running. Start Docker Desktop and rerun this step."
  log "Creating Home Assistant config directory at $HA_CONFIG_DIR."
  run mkdir -p "$HA_CONFIG_DIR"
  if docker ps -a --format '{{.Names}}' | grep -qx "$HA_CONTAINER_NAME"; then
    log "Home Assistant container '$HA_CONTAINER_NAME' already exists."
    run docker start "$HA_CONTAINER_NAME" >/dev/null
  else
    log "Starting Home Assistant container '$HA_CONTAINER_NAME'."
    run docker run -d \
      --name "$HA_CONTAINER_NAME" \
      --privileged \
      --restart unless-stopped \
      -e TZ=Europe/Amsterdam \
      -v "$HA_CONFIG_DIR:/config" \
      -p 8123:8123 \
      "$HA_IMAGE" >/dev/null
  fi
  docker ps --filter "name=$HA_CONTAINER_NAME" --format '{{.Names}}\t{{.Status}}\t{{.Ports}}'
  log "Home Assistant will be available at http://localhost:8123 after first startup."
  wait_for_home_assistant 180 || true
}

step_8_install_hacs() {
  step_7_home_assistant_container
  log "Installing HACS into $HA_CONFIG_DIR."
  run mkdir -p "$HA_CONFIG_DIR/custom_components"
  run docker exec "$HA_CONTAINER_NAME" sh -c "cd /config && wget -O - https://get.hacs.xyz | bash -"
  run docker restart "$HA_CONTAINER_NAME" >/dev/null
  log "HACS installed. Complete HACS authorization in Home Assistant UI if prompted."
}

step_9_sync_djconnect_to_ha() {
  log "Syncing DJConnect integration into Home Assistant config."
  run mkdir -p "$HA_CONFIG_DIR/custom_components/djconnect"
  run rsync -a --delete --delete-excluded \
    --exclude __pycache__ \
    --exclude '*.pyc' \
    "$REPO_ROOT/custom_components/djconnect/" \
    "$HA_CONFIG_DIR/custom_components/djconnect/"
  if [[ "$DRY_RUN" == "1" ]]; then
    run docker restart "$HA_CONTAINER_NAME"
    run docker ps --filter "name=$HA_CONTAINER_NAME" --format '{{.Names}}\t{{.Status}}\t{{.Ports}}'
    return
  fi
  python3 -m json.tool "$HA_CONFIG_DIR/custom_components/djconnect/manifest.json" >/dev/null
  if have docker && docker ps -a --format '{{.Names}}' | grep -qx "$HA_CONTAINER_NAME"; then
    run docker restart "$HA_CONTAINER_NAME" >/dev/null
    docker ps --filter "name=$HA_CONTAINER_NAME" --format '{{.Names}}\t{{.Status}}\t{{.Ports}}'
  fi
}

step_10_auth_and_summary() {
  log "Authentication and final checks."
  if have gh; then
    if gh auth status >/dev/null 2>&1; then
      log "GitHub CLI is authenticated."
    elif confirm "Run 'gh auth login' now?"; then
      run gh auth login
    fi
  else
    warn "gh is not installed. Run step 3 first."
  fi
  if have codex; then
    log "Codex CLI found: $(command -v codex)"
  else
    warn "Codex CLI not found. Run step 5 or open a new terminal after npm install."
  fi
  cat <<EOF

DJConnect dev environment summary:
  Repo:              $REPO_ROOT
  HA config:         $HA_CONFIG_DIR
  HA URL:            http://localhost:8123
  HA container:      $HA_CONTAINER_NAME
  Integration path:  $HA_CONFIG_DIR/custom_components/djconnect
  Music Assistant:  http://localhost:8095 after step 27

Next manual UI steps:
  1. Open http://localhost:8123 and finish Home Assistant onboarding.
  2. Add HACS if HA asks for authorization.
  3. Add the DJConnect integration from Settings > Devices & services.
  4. For Music Assistant backend testing, run step 27, open http://localhost:8095,
     add a provider/player in Music Assistant, then add the Music Assistant
     integration in Home Assistant.
EOF
}

step_18_collect_secrets() {
  collect_optional_secrets
}

validate_command() {
  local cmd="$1"
  if have "$cmd"; then
    status_ok "$cmd -> $(command -v "$cmd")"
  else
    status_miss "$cmd"
    return 1
  fi
}

step_19_validate_core_environment() {
  load_onboarding_env
  log "Validating DJConnect core Home Assistant developer environment."
  local failed=0
  for cmd in git gh jq python3 node npm rsync curl wget; do
    validate_command "$cmd" || failed=1
  done
  validate_command brew || failed=1
  validate_command docker || failed=1
  validate_command codex || true
  if have gh; then
    gh auth status >/dev/null 2>&1 || { warn "GitHub CLI is not authenticated."; failed=1; }
  fi
  if have docker && docker info >/dev/null 2>&1; then
    if docker ps -a --format '{{.Names}}' | grep -qx "$HA_CONTAINER_NAME"; then
      docker ps --filter "name=$HA_CONTAINER_NAME" --format '{{.Names}}\t{{.Status}}\t{{.Ports}}'
    else
      warn "Home Assistant container '$HA_CONTAINER_NAME' does not exist."
      [[ "$DRY_RUN" == "1" ]] || failed=1
    fi
  else
    warn "Docker is not running."
    [[ "$DRY_RUN" == "1" ]] || failed=1
  fi
  [[ -d "$HA_CONFIG_DIR" ]] || { warn "Home Assistant config dir missing: $HA_CONFIG_DIR"; [[ "$DRY_RUN" == "1" ]] || failed=1; }
  [[ -f "$HA_CONFIG_DIR/custom_components/djconnect/manifest.json" ]] || {
    warn "DJConnect integration is not synced into Home Assistant config."
    [[ "$DRY_RUN" == "1" ]] || failed=1
  }
  if [[ -f "$HA_CONFIG_DIR/custom_components/djconnect/manifest.json" ]]; then
    python3 -m json.tool "$HA_CONFIG_DIR/custom_components/djconnect/manifest.json" >/dev/null || failed=1
  fi
  [[ -d "$HA_CONFIG_DIR/custom_components/hacs" ]] || warn "HACS custom component directory not found yet; UI authorization may still be pending."
  (cd "$REPO_ROOT" && python3 -m unittest discover -s tests && git diff --check) || failed=1
  if [[ -f "$ONBOARDING_ENV_FILE" ]]; then
    local mode
    mode="$(stat -f '%Lp' "$ONBOARDING_ENV_FILE" 2>/dev/null || stat -c '%a' "$ONBOARDING_ENV_FILE" 2>/dev/null || true)"
    [[ "$mode" == "600" ]] || { warn "$ONBOARDING_ENV_FILE permissions are $mode, expected 600."; failed=1; }
  fi
  if [[ -n "${CLOUDFLARE_API_TOKEN-}" ]]; then
    log "Cloudflare API token is present for later Wrangler operations."
  else
    warn "CLOUDFLARE_API_TOKEN not set; remote Cloudflare validation/deploy will be skipped."
  fi
  if (( failed )); then
    die "Validation found missing or incomplete setup."
  fi
  log "Core validation completed successfully."
}

step_20_validate_complete_environment() {
  step_19_validate_core_environment
  log "Validating cross-repo developer tooling."
  local failed=0
  validate_command xcodegen || failed=1
  validate_command pio || failed=1
  validate_command dotnet || failed=1
  [[ -d "$GITHUB_ROOT/djconnect-app" ]] || { warn "Missing djconnect-app repo."; failed=1; }
  [[ -d "$GITHUB_ROOT/djconnect-esp32" ]] || { warn "Missing djconnect-esp32 repo."; failed=1; }
  [[ -d "$GITHUB_ROOT/djconnect-website" ]] || { warn "Missing djconnect-website repo."; failed=1; }
  [[ -d "$GITHUB_ROOT/djconnect-pi" ]] || { warn "Missing djconnect-pi repo."; failed=1; }
  [[ -d "$GITHUB_ROOT/djconnect-api" ]] || { warn "Missing djconnect-api repo."; failed=1; }
  [[ -d "$GITHUB_ROOT/djconnect-windows" ]] || { warn "Missing djconnect-windows repo."; failed=1; }
  step_17_cross_repo_validation || failed=1
  if (( failed )); then
    die "Complete validation found missing or incomplete setup."
  fi
  log "Complete validation finished successfully."
}

run_if_dir() {
  local dir="$1"
  shift
  if [[ -d "$dir" ]]; then
    (cd "$dir" && "$@")
  else
    warn "Skipping missing directory: $dir"
  fi
}

step_21_check_package_upgrades() {
  log "Checking package manager upgrades without applying them."
  if have brew; then
    run brew update
    brew outdated || true
    brew outdated --cask || true
  else
    warn "Homebrew not installed."
  fi
  if have npm; then
    run_if_dir "$GITHUB_ROOT/djconnect-website" npm outdated || true
    run_if_dir "$GITHUB_ROOT/djconnect-api" npm outdated || true
  else
    warn "npm not installed."
  fi
  if [[ -d "$GITHUB_ROOT/djconnect-pi/.venv" ]]; then
    (
      cd "$GITHUB_ROOT/djconnect-pi"
      . .venv/bin/activate
      python3 -m pip list --outdated || true
    )
  elif have python3; then
    python3 -m pip list --outdated || true
  fi
  if have pio && [[ -d "$GITHUB_ROOT/djconnect-esp32" ]]; then
    (cd "$GITHUB_ROOT/djconnect-esp32" && pio pkg outdated -e t_embed_cc1101 || true)
  fi
  if have dotnet; then
    dotnet workload list || true
  fi
  log "Upgrade check completed. Run step 24 with --apply-upgrades to apply upgrades."
}

step_22_apply_package_upgrades() {
  if [[ "$APPLY_UPGRADES" != "1" ]]; then
    die "Step 24 requires --apply-upgrades."
  fi
  log "Applying package manager upgrades."
  if have brew; then
    run brew update
    run brew upgrade
    run brew upgrade --cask || true
  else
    warn "Homebrew not installed."
  fi
  if have npm; then
    run_in_dir "$GITHUB_ROOT/djconnect-website" npm update
    run_in_dir "$GITHUB_ROOT/djconnect-api" npm update
  fi
  if [[ -d "$GITHUB_ROOT/djconnect-pi/.venv" ]]; then
    (
      cd "$GITHUB_ROOT/djconnect-pi"
      . .venv/bin/activate
      run python3 -m pip install --upgrade pip
      run python3 -m pip install --upgrade -e '.[dev]'
    )
  fi
  if have pio && [[ -d "$GITHUB_ROOT/djconnect-esp32" ]]; then
    run_in_dir "$GITHUB_ROOT/djconnect-esp32" pio pkg update -e t_embed_cc1101
  fi
  if have dotnet; then
    run dotnet workload update || true
  fi
  log "Package upgrades completed. Review changed lockfiles/manifests before committing."
}

release_dry_run_if_present() {
  local dir="$1"
  local version="$2"
  if [[ ! -d "$dir" ]]; then
    warn "Skipping missing repo: $dir"
    return 0
  fi
  if [[ -x "$dir/release.sh" ]]; then
    run_in_dir "$dir" ./release.sh "$version" --dry-run
  elif [[ -f "$dir/release.sh" ]]; then
    run_in_dir "$dir" bash release.sh "$version" --dry-run
  else
    warn "No release.sh found in $dir; skipping release dry-run."
  fi
}

music_assistant_smoke_if_present() {
  if ! have docker || ! docker ps -a --format '{{.Names}}' | grep -qx "$MA_CONTAINER_NAME"; then
    warn "Music Assistant server container '$MA_CONTAINER_NAME' not found; skipping MA smoke check."
    return 0
  fi
  run docker start "$MA_CONTAINER_NAME" >/dev/null
  if [[ "$DRY_RUN" == "1" ]]; then
    run curl -fsS http://localhost:8095
    return 0
  fi
  if curl -fsS --connect-timeout 5 --max-time 20 http://localhost:8095 >/dev/null 2>&1; then
    status_ok "Music Assistant server responds at http://localhost:8095"
  else
    warn "Music Assistant server container exists but did not respond at http://localhost:8095."
  fi
}

step_24_e2e_local_release_smoke() {
  log "Running local E2E release/build smoke checks with version $E2E_VERSION."
  run_in_dir "$REPO_ROOT" python3 -m unittest discover -s tests
  release_dry_run_if_present "$REPO_ROOT" "$E2E_VERSION"
  music_assistant_smoke_if_present

  if [[ -d "$GITHUB_ROOT/djconnect-website" ]]; then
    run_in_dir "$GITHUB_ROOT/djconnect-website" npm test
    release_dry_run_if_present "$GITHUB_ROOT/djconnect-website" "$E2E_VERSION"
  fi
  if [[ -d "$GITHUB_ROOT/djconnect-api" ]]; then
    run_in_dir "$GITHUB_ROOT/djconnect-api" npx tsc --noEmit
    run_in_dir "$GITHUB_ROOT/djconnect-api" npm test
    release_dry_run_if_present "$GITHUB_ROOT/djconnect-api" "$E2E_VERSION"
  fi
  if [[ -d "$GITHUB_ROOT/djconnect-pi" ]]; then
    run_in_dir "$GITHUB_ROOT/djconnect-pi" python3 -m compileall src tests
    release_dry_run_if_present "$GITHUB_ROOT/djconnect-pi" "$E2E_VERSION"
  fi
  if [[ -d "$GITHUB_ROOT/djconnect-esp32" ]]; then
    run_in_dir "$GITHUB_ROOT/djconnect-esp32" bash test/native/test_release.sh
    release_dry_run_if_present "$GITHUB_ROOT/djconnect-esp32" "$E2E_VERSION"
  fi
  if [[ -d "$GITHUB_ROOT/djconnect-app" ]]; then
    run_in_dir "$GITHUB_ROOT/djconnect-app" git diff --check
  fi
  if [[ -d "$GITHUB_ROOT/djconnect-windows" ]] && have dotnet; then
    run_in_dir "$GITHUB_ROOT/djconnect-windows" dotnet format DJConnect.Windows.sln --verify-no-changes --no-restore
  fi
  log "Local E2E release/build smoke checks completed."
}

step_26_music_assistant_server() {
  step_3_docker
  log "Installing/starting Music Assistant server container."
  warn "Music Assistant provider and player setup is still manual in the MA UI and HA UI."
  warn "The Home Assistant Music Assistant integration is part of HA; this step starts the separate MA server for backend testing."
  run mkdir -p "$MA_DATA_DIR"
  if [[ "$DRY_RUN" == "1" ]]; then
    run docker run -d \
      --name "$MA_CONTAINER_NAME" \
      --restart unless-stopped \
      --network host \
      -v "$MA_DATA_DIR:/data" \
      "$MA_IMAGE"
    run curl -fsS http://localhost:8095
    return
  fi
  docker info >/dev/null 2>&1 || die "Docker is not running. Start Docker Desktop and rerun this step."
  if docker ps -a --format '{{.Names}}' | grep -qx "$MA_CONTAINER_NAME"; then
    log "Music Assistant container '$MA_CONTAINER_NAME' already exists."
    run docker start "$MA_CONTAINER_NAME" >/dev/null
  else
    log "Starting Music Assistant container '$MA_CONTAINER_NAME'."
    run docker run -d \
      --name "$MA_CONTAINER_NAME" \
      --restart unless-stopped \
      --network host \
      -v "$MA_DATA_DIR:/data" \
      "$MA_IMAGE" >/dev/null
  fi
  docker ps --filter "name=$MA_CONTAINER_NAME" --format '{{.Names}}\t{{.Status}}\t{{.Ports}}'
  log "Music Assistant should become available at http://localhost:8095."
  log "After it starts, configure providers/players in Music Assistant and add the Music Assistant integration in Home Assistant."
  music_assistant_smoke_if_present
}

step_25_ci_smoke_push() {
  if [[ "$RUN_CI_PUSH" != "1" ]]; then
    die "Step 26 requires --run-ci-push."
  fi
  have gh || die "gh is required for step 26."
  have git || die "git is required for step 26."
  if [[ "$DRY_RUN" != "1" ]]; then
    gh auth status >/dev/null 2>&1 || die "GitHub CLI is not authenticated."
  fi
  local branch="${CI_BRANCH:-codex/onboarding-ci-smoke-$(date '+%Y%m%d-%H%M%S')}"
  log "Creating CI smoke-test branch $branch with an empty commit."
  run_in_dir "$REPO_ROOT" git switch -c "$branch"
  run_in_dir "$REPO_ROOT" git commit --allow-empty -m "CI smoke test for onboarding script"
  run_in_dir "$REPO_ROOT" git push -u origin "$branch"
  log "Waiting for newest GitHub Actions run on $branch."
  if [[ "$DRY_RUN" == "1" ]]; then
    run gh run list --branch "$branch" --limit 5
    run gh run watch --branch "$branch" --exit-status
  else
    sleep 10
    gh run list --branch "$branch" --limit 5
    gh run watch --branch "$branch" --exit-status
  fi
  log "CI smoke-test workflow completed for $branch."
}

clone_or_update() {
  local repo_name="$1"
  local url="$2"
  local dir="$GITHUB_ROOT/$repo_name"
  run mkdir -p "$GITHUB_ROOT"
  if [[ -d "$dir/.git" ]]; then
    log "$repo_name already present at $dir."
    git -C "$dir" status --short
    return
  fi
  log "Cloning $repo_name."
  run git clone "$url" "$dir"
}

step_11_clone_all_repos() {
  log "Cloning/updating sibling DJConnect repositories."
  clone_or_update djconnect-app https://github.com/pcvantol/djconnect-app.git
  clone_or_update djconnect-esp32 https://github.com/pcvantol/djconnect-esp32.git
  clone_or_update djconnect-website https://github.com/pcvantol/djconnect-website.git
  clone_or_update djconnect-pi https://github.com/pcvantol/djconnect-pi.git
  clone_or_update djconnect-api https://github.com/pcvantol/djconnect-api.git
  clone_or_update djconnect-windows https://github.com/pcvantol/djconnect-windows.git
  clone_or_update djconnect-firmware https://github.com/pcvantol/djconnect-firmware.git
}

step_12_apple_app_tooling() {
  ensure_homebrew
  log "Installing Apple app tooling from djconnect-app."
  run brew install xcodegen
  if have xcodebuild; then
    xcodebuild -version
  else
    warn "Full Xcode is not installed. Install it from the App Store or Apple Developer before iOS/macOS builds."
  fi
  if [[ -d "$GITHUB_ROOT/djconnect-app" ]] && have xcodegen; then
    run_in_dir "$GITHUB_ROOT/djconnect-app" xcodegen generate
  fi
}

step_13_firmware_tooling() {
  ensure_homebrew
  log "Installing ESP32 firmware tooling from djconnect-esp32."
  run brew install platformio
  if [[ -d "$GITHUB_ROOT/djconnect-esp32" ]]; then
    run_in_dir "$GITHUB_ROOT/djconnect-esp32" pio pkg install -e t_embed_cc1101
  fi
}

step_14_node_cloudflare_tooling() {
  step_2_cli_tooling
  log "Installing Node/Cloudflare dependencies for website and API repos."
  if [[ -d "$GITHUB_ROOT/djconnect-website" ]]; then
    run_in_dir "$GITHUB_ROOT/djconnect-website" npm install
    if confirm "Install Playwright browser binaries for website smoke tests?"; then
      run_in_dir "$GITHUB_ROOT/djconnect-website" npx playwright install
    fi
  fi
  if [[ -d "$GITHUB_ROOT/djconnect-api" ]]; then
    run_in_dir "$GITHUB_ROOT/djconnect-api" npm install
    run_in_dir "$GITHUB_ROOT/djconnect-api" npx wrangler types
  fi
}

step_15_python_pi_tooling() {
  step_2_cli_tooling
  log "Preparing Raspberry Pi client local Python environment."
  if [[ ! -d "$GITHUB_ROOT/djconnect-pi" ]]; then
    warn "djconnect-pi not found. Run step 13 first."
    return
  fi
  (
    cd "$GITHUB_ROOT/djconnect-pi"
    python3 -m venv .venv
    . .venv/bin/activate
    run python3 -m pip install --upgrade pip
    run python3 -m pip install -e '.[dev]'
  )
}

step_16_dotnet_maui_tooling() {
  ensure_homebrew
  log "Installing .NET SDK and restoring MAUI workloads from djconnect-windows."
  if ! have dotnet; then
    run brew install --cask dotnet-sdk
  fi
  dotnet --info
  if [[ -d "$GITHUB_ROOT/djconnect-windows" ]]; then
    run_in_dir "$GITHUB_ROOT/djconnect-windows" dotnet workload restore
  fi
}

step_17_cross_repo_validation() {
  log "Running lightweight cross-repo validation commands."
  if [[ -d "$GITHUB_ROOT/djconnect-app" ]]; then
    (cd "$GITHUB_ROOT/djconnect-app" && git diff --check)
  fi
  if [[ -d "$GITHUB_ROOT/djconnect-esp32" ]]; then
    (cd "$GITHUB_ROOT/djconnect-esp32" && bash test/native/test_release.sh)
  fi
  if [[ -d "$GITHUB_ROOT/djconnect-website" ]]; then
    (cd "$GITHUB_ROOT/djconnect-website" && npm test)
  fi
  if [[ -d "$GITHUB_ROOT/djconnect-api" ]]; then
    (cd "$GITHUB_ROOT/djconnect-api" && npx tsc --noEmit && npm test)
  fi
  if [[ -d "$GITHUB_ROOT/djconnect-pi" ]]; then
    (
      cd "$GITHUB_ROOT/djconnect-pi"
      if [[ -d .venv ]]; then
        . .venv/bin/activate
      fi
      python3 -m compileall src tests
    )
  fi
  if [[ -d "$GITHUB_ROOT/djconnect-windows" ]] && have dotnet; then
    (cd "$GITHUB_ROOT/djconnect-windows" && dotnet format DJConnect.Windows.sln --verify-no-changes --no-restore)
  fi
}

print_menu() {
  cat <<EOF

$(style "$CLR_CYAN$CLR_BOLD" "DJConnect macOS developer onboarding")

$(style "$CLR_BOLD" "Machine")
  0. Preflight machine, VM, hardware, filesystem and network requirements
  1. Download/bootstrap a Parallels macOS development VM
  2. Download/bootstrap a Parallels Windows 11 ARM development VM

$(style "$CLR_BOLD" "Core Home Assistant")
  3. Xcode Command Line Tools + Homebrew
  4. CLI tooling: git, gh, jq, Python, Node, rsync
  5. Docker Desktop
  6. Codex CLI
  7. Clone/update DJConnect repo
  8. Run repo validation tests
  9. Create/start Home Assistant Docker container
 10. Install HACS into Home Assistant
 11. Sync DJConnect custom integration into Home Assistant
 12. GitHub/Codex auth checks and summary

$(style "$CLR_BOLD" "Cross Repo")
 13. Clone/update sibling DJConnect repositories
 14. Apple app tooling: XcodeGen and project generation
 15. ESP32 firmware tooling: PlatformIO packages
 16. Website/API tooling: npm, Playwright, Wrangler types
 17. Raspberry Pi client tooling: Python venv + dev install
 18. Windows/Mac Catalyst tooling: .NET SDK + MAUI workloads
 19. Lightweight cross-repo validation
 20. Prompt for optional tokens/API keys
 21. Validate core Home Assistant developer environment
 22. Validate complete cross-repo developer environment
 23. Check package manager upgrades
 24. Apply package manager upgrades
 25. Local E2E release/build smoke checks
 26. GitHub CI smoke push and workflow validation
 27. Install/start Music Assistant server for backend testing

$(style "$CLR_BOLD" "Examples")
  ./$SCRIPT_NAME --all --yes
  ./$SCRIPT_NAME --core --yes
  ./$SCRIPT_NAME --steps 0
  ./$SCRIPT_NAME --steps 1 --macos-version 15.5
  ./$SCRIPT_NAME --steps 2 --windows-vm-name "DJConnect Windows 11 ARM Dev"
  ./$SCRIPT_NAME --steps 3,4,5,9,10,11,12,21 --warm-sudo --prompt-secrets
  ./$SCRIPT_NAME --steps 13,14,15,16,17,18
  ./$SCRIPT_NAME --steps 13,14,15,16,17,18,19,22
  ./$SCRIPT_NAME --steps 23
  ./$SCRIPT_NAME --steps 24 --apply-upgrades
  ./$SCRIPT_NAME --steps 25 --e2e-version 3.1.999
  ./$SCRIPT_NAME --steps 26 --run-ci-push
  ./$SCRIPT_NAME --steps 27

EOF
}

run_step() {
  case "$1" in
    0) step_0_preflight ;;
    1) step_0_parallels_macos_vm ;;
    2) step_0b_parallels_windows_vm ;;
    3) step_1_xcode_homebrew ;;
    4) step_2_cli_tooling ;;
    5) step_3_docker ;;
    6) step_4_codex ;;
    7) step_5_clone_or_update_repo ;;
    8) step_6_python_validation ;;
    9) step_7_home_assistant_container ;;
    10) step_8_install_hacs ;;
    11) step_9_sync_djconnect_to_ha ;;
    12) step_10_auth_and_summary ;;
    13) step_11_clone_all_repos ;;
    14) step_12_apple_app_tooling ;;
    15) step_13_firmware_tooling ;;
    16) step_14_node_cloudflare_tooling ;;
    17) step_15_python_pi_tooling ;;
    18) step_16_dotnet_maui_tooling ;;
    19) step_17_cross_repo_validation ;;
    20) step_18_collect_secrets ;;
    21) step_19_validate_core_environment ;;
    22) step_20_validate_complete_environment ;;
    23) step_21_check_package_upgrades ;;
    24) step_22_apply_package_upgrades ;;
    25) step_24_e2e_local_release_smoke ;;
    26) step_25_ci_smoke_push ;;
    27) step_26_music_assistant_server ;;
    *) die "Unknown step: $1" ;;
  esac
}

step_label() {
  case "$1" in
    0) printf 'Preflight machine, VM, hardware, filesystem and network requirements' ;;
    1) printf 'Download/bootstrap a Parallels macOS development VM' ;;
    2) printf 'Download/bootstrap a Parallels Windows 11 ARM development VM' ;;
    3) printf 'Xcode Command Line Tools + Homebrew' ;;
    4) printf 'CLI tooling: git, gh, jq, Python, Node, rsync' ;;
    5) printf 'Docker Desktop' ;;
    6) printf 'Codex CLI' ;;
    7) printf 'Clone/update DJConnect repo' ;;
    8) printf 'Run repo validation tests' ;;
    9) printf 'Create/start Home Assistant Docker container' ;;
    10) printf 'Install HACS into Home Assistant' ;;
    11) printf 'Sync DJConnect custom integration into Home Assistant' ;;
    12) printf 'GitHub/Codex auth checks and summary' ;;
    13) printf 'Clone/update sibling DJConnect repositories' ;;
    14) printf 'Apple app tooling: XcodeGen and project generation' ;;
    15) printf 'ESP32 firmware tooling: PlatformIO packages' ;;
    16) printf 'Website/API tooling: npm, Playwright, Wrangler types' ;;
    17) printf 'Raspberry Pi client tooling: Python venv + dev install' ;;
    18) printf 'Windows/Mac Catalyst tooling: .NET SDK + MAUI workloads' ;;
    19) printf 'Lightweight cross-repo validation' ;;
    20) printf 'Prompt for optional tokens/API keys' ;;
    21) printf 'Validate core Home Assistant developer environment' ;;
    22) printf 'Validate complete cross-repo developer environment' ;;
    23) printf 'Check package manager upgrades' ;;
    24) printf 'Apply package manager upgrades' ;;
    25) printf 'Local E2E release/build smoke checks' ;;
    26) printf 'GitHub CI smoke push and workflow validation' ;;
    27) printf 'Install/start Music Assistant server for backend testing' ;;
    *) printf 'Unknown step' ;;
  esac
}

parse_steps() {
  local raw="$1"
  raw="${raw// /}"
  [[ -n "$raw" ]] || die "No steps selected."
  IFS=',' read -ra parts <<< "$raw"
  STEP_TOTAL="${#parts[@]}"
  STEP_INDEX=0
  for step in "${parts[@]}"; do
    [[ "$step" =~ ^[0-9]+$ ]] || die "Invalid step: $step"
    (( step >= 0 && step <= 27 )) || die "Step out of range: $step"
    if [[ "$PLAN_ONLY" == "1" ]]; then
      printf '%s %2s. %s\n' "$(style "$CLR_CYAN" "PLAN")" "$step" "$(step_label "$step")"
    else
      STEP_INDEX=$((STEP_INDEX + 1))
      log "[$STEP_INDEX/$STEP_TOTAL] Starting step $step: $(step_label "$step")"
      run_step "$step"
      ok "[$STEP_INDEX/$STEP_TOTAL] Finished step $step: $(step_label "$step")"
    fi
  done
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --all)
      SELECTED_STEPS="0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23"
      shift
      ;;
    --core)
      SELECTED_STEPS="3,4,5,6,7,8,9,10,11,12"
      shift
      ;;
    --steps)
      SELECTED_STEPS="${2:-}"
      shift 2
      ;;
    --yes|-y)
      ASSUME_YES=1
      shift
      ;;
    --warm-sudo)
      WARM_SUDO=1
      shift
      ;;
    --prompt-secrets)
      PROMPT_SECRETS=1
      shift
      ;;
    --plan)
      PLAN_ONLY=1
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --apply-upgrades)
      APPLY_UPGRADES=1
      shift
      ;;
    --e2e-version)
      E2E_VERSION="${2:-}"
      shift 2
      ;;
    --run-ci-push)
      RUN_CI_PUSH=1
      shift
      ;;
    --ci-branch)
      CI_BRANCH="${2:-}"
      shift 2
      ;;
    --ha-config-dir)
      HA_CONFIG_DIR="${2:-}"
      shift 2
      ;;
    --vm-name)
      MACOS_VM_NAME="${2:-}"
      shift 2
      ;;
    --macos-version)
      MACOS_VERSION="${2:-}"
      shift 2
      ;;
    --windows-vm-name)
      WINDOWS_VM_NAME="${2:-}"
      shift 2
      ;;
    --windows-iso)
      WINDOWS_ISO_PATH="${2:-}"
      shift 2
      ;;
    --env-file)
      ONBOARDING_ENV_FILE="${2:-}"
      shift 2
      ;;
    --log-file)
      LOG_FILE="${2:-}"
      shift 2
      ;;
    --no-log-file)
      LOG_FILE="none"
      shift
      ;;
    --no-color)
      NO_COLOR_MODE=1
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      die "Unknown option: $1"
      ;;
  esac
done

init_style
trap cleanup EXIT
need_macos
load_onboarding_env
start_logging

if [[ "$WARM_SUDO" == "1" ]]; then
  warm_sudo
fi

if [[ "$PROMPT_SECRETS" == "1" ]]; then
  collect_optional_secrets
fi

if [[ -z "$SELECTED_STEPS" ]]; then
  print_menu
  read -r -p "Choose steps, for example 0, 1, 2,3,4,8,9,10 or 'core'/'all': " SELECTED_STEPS
  if [[ "$(printf '%s' "$SELECTED_STEPS" | tr '[:upper:]' '[:lower:]')" == "all" ]]; then
    SELECTED_STEPS="0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23"
  elif [[ "$(printf '%s' "$SELECTED_STEPS" | tr '[:upper:]' '[:lower:]')" == "core" ]]; then
    SELECTED_STEPS="3,4,5,6,7,8,9,10,11,12"
  fi
fi

parse_steps "$SELECTED_STEPS"
