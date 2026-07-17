# Version: 1.3.3
# Shared recovery state, constants and desired-state parsing.
# Bootstraps a DJConnect macOS development host after a laptop replacement.
# Authentication is interactive through gh; GitHub registration tokens are
# fetched just-in-time and are never accepted as arguments or written to disk.

readonly ORG='pcvantol'
readonly HOST_BOOTSTRAP_PACKAGE_MANIFEST="$HOST_BOOTSTRAP_PACKAGE_DIRECTORY/manifest.yml"

package_manifest_value() {
  local requested_key="$1"
  awk -v requested_key="$requested_key" '
    /^[[:space:]]*($|#)/ { next }
    {
      separator = index($0, ":")
      if (separator == 0) next
      key = substr($0, 1, separator - 1)
      value = substr($0, separator + 1)
      gsub(/^[[:space:]]+|[[:space:]]+$/, "", key)
      gsub(/^[[:space:]]+|[[:space:]]+$/, "", value)
      if (key == requested_key) { print value; exit }
    }
  ' "$HOST_BOOTSTRAP_PACKAGE_MANIFEST"
}

load_recovery_package_manifest() {
  local version
  [[ -f "$HOST_BOOTSTRAP_PACKAGE_MANIFEST" ]] || {
    printf 'ERROR Host-bootstrap package manifest is missing: %s\n' "$HOST_BOOTSTRAP_PACKAGE_MANIFEST" >&2
    exit 1
  }
  version="$(package_manifest_value 'package.version')"
  [[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || {
    printf 'ERROR Host-bootstrap package manifest has an invalid package version: %s\n' "$version" >&2
    exit 1
  }
  readonly SCRIPT_VERSION="$version"
}

verify_recovery_package_manifest() {
  local component expected_file expected_version expected_sha256 actual_version actual_sha256 aggregate_input aggregate_sha256
  aggregate_input=''
  for component in entry config core workflow security operations runners apple cli bootstrap; do
    expected_file="$(package_manifest_value "component.$component.file")"
    expected_version="$(package_manifest_value "component.$component.version")"
    expected_sha256="$(package_manifest_value "component.$component.sha256")"
    if [[ "$component" == 'entry' ]]; then
      [[ "$expected_file" == '../bootstrap_djconnect_macos_host.sh' ]] || die 'Host-bootstrap package manifest has an invalid entry-point file binding.'
      expected_file="$SCRIPT_DIRECTORY/bootstrap_djconnect_macos_host.sh"
    else
      [[ "$expected_file" =~ ^[A-Za-z0-9_-]+\.sh$ ]] || die "Host-bootstrap package manifest has an invalid file for component $component."
      expected_file="$HOST_BOOTSTRAP_PACKAGE_DIRECTORY/$expected_file"
    fi
    [[ "$expected_version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || die "Host-bootstrap package manifest has an invalid version for component $component."
    [[ "$expected_sha256" =~ ^[0-9a-f]{64}$ ]] || die "Host-bootstrap package manifest has an invalid SHA-256 for component $component."
    actual_version="$(sed -nE 's/^# Version: ([0-9]+\.[0-9]+\.[0-9]+)$/\1/p' "$expected_file" | head -n 1)"
    [[ "$actual_version" == "$expected_version" ]] || die "Host-bootstrap package component $component version mismatch: manifest=$expected_version module=${actual_version:-missing}."
    actual_sha256="$(shasum -a 256 "$expected_file" | awk '{print $1}')"
    [[ "$actual_sha256" == "$expected_sha256" ]] || die "Host-bootstrap package component $component SHA-256 mismatch: manifest=$expected_sha256 module=$actual_sha256."
    aggregate_input+="$component:$actual_sha256"$'\n'
  done
  aggregate_sha256="$(printf '%s' "$aggregate_input" | shasum -a 256 | awk '{print $1}')"
  [[ "$aggregate_sha256" == "$(package_manifest_value 'package.aggregate_sha256')" ]] || die 'Host-bootstrap package aggregate SHA-256 mismatch.'
}

load_recovery_package_manifest
readonly REPOSITORY_ROOT="$(cd "$SCRIPT_DIRECTORY/../.." && pwd -P)"
readonly REDACTION_RULES="$SCRIPT_DIRECTORY/redact_recovery_output.sed"
DESIRED_STATE_FILE="${DESIRED_STATE_FILE:-$SCRIPT_DIRECTORY/macos_development_host_desired_state.yml}"
DESIRED_STATE_SCHEMA_VERSION=''
DESIRED_STATE_VERSION=''
DESIRED_MINIMUM_TOOL_VERSION=''
MANIFEST_TOOL_COMPATIBILITY_VERDICT=''
DESIRED_HOST_PLATFORM=''
DESIRED_HOST_ARCHITECTURE=''
DESIRED_HOST_APPLE_SILICON=''
DESIRED_MINIMUM_MACOS_MAJOR=''
DESIRED_MINIMUM_RAM_GB=''
DESIRED_RECOMMENDED_RAM_GB=''
DESIRED_MINIMUM_CPU_CORES=''
DESIRED_MINIMUM_FREE_DISK_GB=''
DESIRED_RECOMMENDED_FREE_DISK_GB=''
DESIRED_TOOL_FORMULAS=()
DESIRED_REQUIRED_CASKS=()
DESIRED_OPTIONAL_CASKS=()
DESIRED_HA_SERVICE=''
DESIRED_HA_CONTAINER_NAME=''
DESIRED_HA_URL=''
DESIRED_NGROK_CONFIG_RELATIVE_PATH=''
DESIRED_NGROK_CONFIG_VERSION=''
DESIRED_NGROK_CONFIG_PERMISSIONS=''
DESIRED_NGROK_AUTHTOKEN=''
DESIRED_NGROK_LAUNCH_AGENT_LABEL=''
DESIRED_NGROK_TUNNEL_DOMAIN=''
DESIRED_NGROK_TUNNEL_TARGET=''
DESIRED_NGROK_INSPECTOR_URL=''
DESIRED_TAILSCALE_INSTALLATION=''
DESIRED_TAILSCALE_STATE=''
DESIRED_TAILSCALE_MAGIC_DNS=''
DESIRED_TAILSCALE_ACCEPT_ROUTES=''
DESIRED_TAILSCALE_EXIT_NODE=''
DESIRED_TAILSCALE_SSH=''
DESIRED_TAILSCALE_SHIELDS_UP=''
DESIRED_TAILSCALE_AUTO_UPDATE=''
DESIRED_PROFILES=()
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
LOG_CAPTURE_DIRECTORY=''
LOG_CAPTURE_PIPE=''
LOG_CAPTURE_PID=''
ORIGINAL_STDOUT_IS_TTY=0
REPORT_FILE="${REPORT_FILE:-}"
REPORTING_STARTED=0
CURRENT_STEP=''
CURRENT_REPORT_SECTION=''
REPAIR_PROGRESS_COMPLETED=0
readonly REPAIR_PROGRESS_TOTAL=6
ALLOW_STEP_RETRY=1
SKIP_PHASES="${SKIP_PHASES:-}"
SKIPPED_PHASE_COUNT=0
INITIAL_VERIFICATION_PASSED=0
LEAST_PRIVILEGE_WARNING_COUNT=0
PERMISSIONS_AUDIT_HAS_WARNINGS=0
CREDENTIAL_EXPIRY_HAS_WARNINGS=0
EXPIRY_WARNING_DAYS="${DJCONNECT_EXPIRY_WARNING_DAYS:-30}"
PHASE_PRECHECK_RESULT=''
FORCE_PHASES="${FORCE_PHASES:-}"
CURRENT_PHASE_ID=''
VERIFY_MODE=0
VERIFY_DRIFT_COUNT=0
VERIFY_UNVERIFIED_COUNT=0
LOG_LEVEL="${LOG_LEVEL:-info}"
LIST_PHASES=0
PARALLEL_JOBS="${DJCONNECT_PARALLEL_JOBS:-0}"
MEMORY_OVERRIDE_CONFIRMED=0
REPAIR_MODE=0
REPAIR_INITIAL_VERIFY_STATUS=''
REPAIR_FINAL_VERIFY_STATUS=''
REPAIR_MANUAL_REQUIREMENTS=()
RESUME_MODE=0
RESUME_STATE_FILE="${RESUME_STATE_FILE:-$HOME/Library/Application Support/DJConnect/macos-runner-recovery-resume.env}"
RESUME_NEXT_PHASE=''
readonly RESUME_AUTOSTART_LABEL='com.djconnect.macos-runner-recovery-resume'
RESUME_AUTOSTART_PLIST="$HOME/Library/LaunchAgents/$RESUME_AUTOSTART_LABEL.plist"
RESUME_CONTINUATION_COMMAND="$HOME/Library/Application Support/DJConnect/macos-runner-recovery-resume.command"
