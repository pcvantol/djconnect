#!/usr/bin/env bash
set -euo pipefail

# Recovers a DJConnect macOS Actions-runner host after a laptop replacement.
# Authentication is interactive through gh; GitHub registration tokens are
# fetched just-in-time and are never accepted as arguments or written to disk.

readonly ORG='pcvantol'
readonly SCRIPT_VERSION='1.0.0'
readonly SCRIPT_DIRECTORY="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly REPOSITORY_ROOT="$(cd "$SCRIPT_DIRECTORY/../.." && pwd -P)"
readonly REDACTION_RULES="$SCRIPT_DIRECTORY/redact_recovery_output.sed"
DESIRED_STATE_FILE="${DESIRED_STATE_FILE:-$SCRIPT_DIRECTORY/macos_runner_host_desired_state.yml}"
DESIRED_STATE_SCHEMA_VERSION=''
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
DESIRED_REFRESH_CASKS=()
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
  --desired-state FILE  YAML desired-state manifest to reconcile. Default:
                        scripts/runner/macos_runner_host_desired_state.yml
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
  --skip-phases LIST    Comma-separated phase IDs to skip intentionally.
                        See the recovery guide for valid IDs. Skipped phases
                        are recorded and prevent a fully-qualified PASS.
  --force-phases LIST   Comma-separated phase IDs to reconcile again even
                        when their desired state already exists. This is
                        idempotent and does not recreate existing runners.
  --verify              Read the desired state and print a Markdown delta
                        against this machine without recovery mutations.
  --repair              Run one unattended desired-state repair pass after a
                        baseline verify, then run verify again. Never opens a
                        login, GUI, sudo or confirmation prompt; records
                        remaining manual requirements in the final report.
  --resume              Continue a recovery paused for a required macOS reboot.
                        Re-supply any sensitive local signing inputs; they are
                        never stored in the resume checkpoint.
  --resume-state FILE    Owner-only reboot-resume checkpoint path. Default:
                        ~/Library/Application Support/DJConnect/macos-runner-recovery-resume.env
  --version              Show the bootstrap version and exit.
  help                   Show this help and exit.
  --log-level LEVEL      Minimum message level: debug, verbose, info,
                        warning or error. Default: info (or $LOG_LEVEL).
  --list-phases          List phase execution capabilities and exit. Phases
                        marked HEADLESS + PARALLEL SAFE may run concurrently
                        after all listed prerequisites have completed.
  --parallel-jobs COUNT  Maximum concurrent HEADLESS + PARALLEL SAFE phases.
                        Default: half of available CPU cores, minimum one.
                        Cannot exceed available CPU cores. May also be set by
                        DJCONNECT_PARALLEL_JOBS.
  --confirm-memory-override
                        Explicitly approve recovery on a host that meets the
                        hard RAM minimum but is below the recommended RAM.
                        Otherwise an interactive confirmation is required.
  --expiry-warning-days DAYS
                        Warn when a local Apple certificate or provisioning
                        profile expires within this many days. Default: 30
                        (or DJCONNECT_EXPIRY_WARNING_DAYS).
  --no-color            Disable ANSI color output.
  --help                Show this help.

No GitHub registration token is passed on the command line. After `gh auth
login`, the script obtains one short-lived token per repository through the
authenticated GitHub API and gives it directly to the runner configurator.

Signing material must be supplied from a local secure backup. It is never
downloaded from GitHub, written to this repository or emitted to a log.
EOF
}

print_version() {
  printf 'DJConnect macOS Runner Host Recovery Bootstrap %s\n' "$SCRIPT_VERSION"
}

desired_state_value() {
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
      if (key == requested_key) {
        print value
        exit
      }
    }
  ' "$DESIRED_STATE_FILE"
}

require_desired_state_value() {
  local requested_key="$1"
  local value
  value="$(desired_state_value "$requested_key")"
  [[ -n "$value" ]] || die "Desired-state manifest is missing required key: $requested_key"
  printf '%s' "$value"
}

load_desired_state() {
  local profile
  [[ -f "$DESIRED_STATE_FILE" ]] || die "Desired-state manifest is unavailable: $DESIRED_STATE_FILE"
  DESIRED_STATE_SCHEMA_VERSION="$(require_desired_state_value schema_version)"
  [[ "$DESIRED_STATE_SCHEMA_VERSION" == '1' ]] || die "Unsupported desired-state schema version: $DESIRED_STATE_SCHEMA_VERSION"
  DESIRED_HOST_PLATFORM="$(require_desired_state_value host.platform)"
  DESIRED_HOST_ARCHITECTURE="$(require_desired_state_value host.architecture)"
  DESIRED_HOST_APPLE_SILICON="$(require_desired_state_value host.apple_silicon)"
  DESIRED_MINIMUM_MACOS_MAJOR="$(require_desired_state_value host.macos_minimum_major)"
  DESIRED_MINIMUM_RAM_GB="$(require_desired_state_value host.minimum_ram_gb)"
  DESIRED_RECOMMENDED_RAM_GB="$(require_desired_state_value host.recommended_ram_gb)"
  DESIRED_MINIMUM_CPU_CORES="$(require_desired_state_value host.minimum_cpu_cores)"
  DESIRED_MINIMUM_FREE_DISK_GB="$(require_desired_state_value host.minimum_free_disk_gb)"
  DESIRED_RECOMMENDED_FREE_DISK_GB="$(require_desired_state_value host.recommended_free_disk_gb)"
  IFS=',' read -r -a DESIRED_TOOL_FORMULAS <<<"$(require_desired_state_value tooling.formulas)"
  IFS=',' read -r -a DESIRED_REQUIRED_CASKS <<<"$(require_desired_state_value tooling.required_casks)"
  IFS=',' read -r -a DESIRED_OPTIONAL_CASKS <<<"$(require_desired_state_value tooling.optional_casks)"
  IFS=',' read -r -a DESIRED_REFRESH_CASKS <<<"$(require_desired_state_value tooling.refresh_casks)"
  IFS=',' read -r -a DESIRED_PROFILES <<<"$(require_desired_state_value runner.profiles)"
  for profile in "${DESIRED_PROFILES[@]}"; do
    case "$profile" in
      apple|private-network|esp32|pi) ;;
      *) die "Unsupported desired-state runner profile: $profile" ;;
    esac
    require_desired_state_value "profile.$profile.repository" >/dev/null
    require_desired_state_value "profile.$profile.runner_name" >/dev/null
    require_desired_state_value "profile.$profile.labels" >/dev/null
  done
  [[ "$VERIFY_MODE" == '1' ]] || log "Loaded desired-state manifest $DESIRED_STATE_FILE (schema $DESIRED_STATE_SCHEMA_VERSION)."
}

verify_delta_row() {
  local component="$1" desired="$2" actual="$3" state="$4"
  actual="${actual//|/\\|}"
  printf '| %s | %s | %s | %s |\n' "$component" "$desired" "$actual" "$state"
  case "$state" in
    DRIFT) VERIFY_DRIFT_COUNT=$((VERIFY_DRIFT_COUNT + 1)) ;;
    UNVERIFIED) VERIFY_UNVERIFIED_COUNT=$((VERIFY_UNVERIFIED_COUNT + 1)) ;;
  esac
}

run_desired_state_verification() {
  local hardware_profile macos_version macos_major cpu_brand mem_bytes mem_gb cpu_count disk_probe_path disk_kb disk_gb formula cask profile install_dir uid_value
  printf '# DJConnect macOS Runner Host Desired-State Delta\n\n'
  printf '%s\n\n' "Manifest: \`$DESIRED_STATE_FILE\` (schema $DESIRED_STATE_SCHEMA_VERSION)"
  printf '%s\n' '| Component | Desired | Actual | Delta |'
  printf '%s\n' '| --- | --- | --- | --- |'

  macos_version="$(sw_vers -productVersion 2>/dev/null || printf unknown)"
  macos_major="${macos_version%%.*}"
  verify_delta_row 'host.platform' "$DESIRED_HOST_PLATFORM/$DESIRED_HOST_ARCHITECTURE" "$(uname -s)/$(uname -m)" "$([[ "$(uname -s)" == Darwin && "$(uname -m)" == "$DESIRED_HOST_ARCHITECTURE" ]] && printf MATCH || printf DRIFT)"
  verify_delta_row 'host.macos_minimum_major' ">=$DESIRED_MINIMUM_MACOS_MAJOR" "$macos_version" "$([[ "$macos_major" =~ ^[0-9]+$ ]] && (( macos_major >= DESIRED_MINIMUM_MACOS_MAJOR )) && printf MATCH || printf DRIFT)"
  hardware_profile="$(system_profiler SPHardwareDataType 2>/dev/null || true)"
  cpu_brand="$(sysctl -n machdep.cpu.brand_string 2>/dev/null || true)"
  [[ -n "$cpu_brand" ]] || cpu_brand="$(awk -F': ' '/Chip:/{print $2; exit}' <<<"$hardware_profile")"
  verify_delta_row 'host.apple_silicon' "$DESIRED_HOST_APPLE_SILICON" "${cpu_brand:-unknown}" "$([[ "$cpu_brand" == Apple* ]] && printf MATCH || printf DRIFT)"
  mem_bytes="$(sysctl -n hw.memsize 2>/dev/null || echo 0)"
  if [[ "$mem_bytes" =~ ^[0-9]+$ && "$mem_bytes" != 0 ]]; then mem_gb=$((mem_bytes / 1024 / 1024 / 1024)); else mem_gb="$(awk -F': ' '/Memory:/{print $2; exit}' <<<"$hardware_profile" | awk '{print $1}')"; fi
  verify_delta_row 'host.minimum_ram_gb' ">=$DESIRED_MINIMUM_RAM_GB" "${mem_gb:-unknown}GB" "$([[ "$mem_gb" =~ ^[0-9]+$ ]] && (( mem_gb >= DESIRED_MINIMUM_RAM_GB )) && printf MATCH || printf DRIFT)"
  cpu_count="$(sysctl -n hw.ncpu 2>/dev/null || echo 0)"
  if [[ ! "$cpu_count" =~ ^[0-9]+$ || "$cpu_count" == 0 ]]; then cpu_count="$(awk -F': ' '/Total Number of Cores:/{print $2; exit}' <<<"$hardware_profile" | awk '{print $1}')"; fi
  verify_delta_row 'host.minimum_cpu_cores' ">=$DESIRED_MINIMUM_CPU_CORES" "${cpu_count:-unknown}" "$([[ "$cpu_count" =~ ^[0-9]+$ ]] && (( cpu_count >= DESIRED_MINIMUM_CPU_CORES )) && printf MATCH || printf DRIFT)"
  disk_probe_path="$GITHUB_ROOT"; while [[ ! -e "$disk_probe_path" && "$disk_probe_path" != / ]]; do disk_probe_path="$(dirname "$disk_probe_path")"; done
  disk_kb="$(df -Pk "$disk_probe_path" | awk 'NR == 2 {print $4}')"; disk_gb=$((disk_kb / 1024 / 1024))
  if (( disk_gb >= DESIRED_MINIMUM_FREE_DISK_GB )); then
    verify_delta_row 'host.minimum_free_disk_gb' ">=$DESIRED_MINIMUM_FREE_DISK_GB" "${disk_gb}GB at $disk_probe_path" MATCH
  else
    verify_delta_row 'host.minimum_free_disk_gb' ">=$DESIRED_MINIMUM_FREE_DISK_GB" "${disk_gb}GB at $disk_probe_path" DRIFT
  fi

  for formula in "${DESIRED_TOOL_FORMULAS[@]}"; do
    if command -v brew >/dev/null 2>&1 && brew list --versions "$formula" >/dev/null 2>&1; then verify_delta_row "tooling.formula.$formula" installed installed MATCH; else verify_delta_row "tooling.formula.$formula" installed absent DRIFT; fi
  done
  for cask in "${DESIRED_REQUIRED_CASKS[@]}"; do
    if command -v brew >/dev/null 2>&1 && brew list --cask "$cask" >/dev/null 2>&1; then verify_delta_row "tooling.cask.$cask" installed installed MATCH; else verify_delta_row "tooling.cask.$cask" installed absent DRIFT; fi
  done
  for cask in "${DESIRED_OPTIONAL_CASKS[@]}"; do
    if command -v brew >/dev/null 2>&1 && brew list --cask "$cask" >/dev/null 2>&1; then verify_delta_row "tooling.optional_cask.$cask" installed installed MATCH; else verify_delta_row "tooling.optional_cask.$cask" optional absent OPTIONAL; fi
  done
  for profile in "${DESIRED_PROFILES[@]}"; do
    profile_enabled "$profile" || continue
    profile_values "$profile"; install_dir="$RUNNER_ROOT/$PROFILE_RUNNER_NAME"
    if [[ -f "$install_dir/.runner" ]]; then verify_delta_row "runner.$profile" "$PROFILE_REPOSITORY ($PROFILE_LABELS)" registered MATCH; else verify_delta_row "runner.$profile" "$PROFILE_REPOSITORY ($PROFILE_LABELS)" absent DRIFT; fi
  done
  uid_value="$(id -u)"
  if launchctl print "gui/$uid_value/com.djconnect.ci-tooling-maintenance" >/dev/null 2>&1; then verify_delta_row 'maintenance.launch_agent' loaded loaded MATCH; else verify_delta_row 'maintenance.launch_agent' loaded absent DRIFT; fi
  printf '\n## Verdict\n\n'
  if (( VERIFY_DRIFT_COUNT == 0 && VERIFY_UNVERIFIED_COUNT == 0 )); then printf '%s\n' '**MATCH** — this machine matches the required desired state.'; return 0; fi
  printf '%s\n' "**DRIFT DETECTED** — $VERIFY_DRIFT_COUNT required difference(s), $VERIFY_UNVERIFIED_COUNT unverified item(s)."
  return 1
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
log_level_rank() {
  case "$1" in
    debug) printf '10' ;;
    verbose) printf '20' ;;
    info) printf '30' ;;
    warning) printf '40' ;;
    error) printf '50' ;;
    *) return 1 ;;
  esac
}

validate_log_level() {
  log_level_rank "$LOG_LEVEL" >/dev/null || {
    printf 'ERROR Invalid log level %q. Use debug, verbose, info, warning or error.\n' "$LOG_LEVEL" >&2
    exit 2
  }
}

validate_parallel_jobs() {
  [[ "$PARALLEL_JOBS" =~ ^[0-9]+$ ]] || {
    printf 'ERROR Parallel job count must be a non-negative integer: %q\n' "$PARALLEL_JOBS" >&2
    exit 2
  }
}

validate_expiry_warning_days() {
  [[ "$EXPIRY_WARNING_DAYS" =~ ^[0-9]+$ ]] || {
    printf 'ERROR Expiry warning days must be a non-negative integer: %q\n' "$EXPIRY_WARNING_DAYS" >&2
    exit 2
  }
}

should_log() {
  local message_level="$1"
  (( $(log_level_rank "$message_level") >= $(log_level_rank "$LOG_LEVEL") ))
}

emit_log() {
  local message_level="$1"
  local label="$2"
  local colour="$3"
  shift 3
  should_log "$message_level" || return 0
  if [[ "$message_level" == 'info' ]]; then
    printf '\n'
  fi
  printf '%s %s\n' "$(style "$colour$CLR_BOLD" "$label")" "$*"
}

debug() { emit_log debug 'DEBUG' "$CLR_MAGENTA" "$@"; }
verbose() { emit_log verbose 'VERBOSE' "$CLR_CYAN" "$@"; }
info() { emit_log info 'INFO' "$CLR_CYAN" "$@"; }
progress() { emit_log info 'PROGRESS' "$CLR_GREEN" "$@"; }
log() { info "$@"; }
ok() { emit_log info 'OK' "$CLR_GREEN" "$@"; }
warn() { emit_log warning 'WARNING' "$CLR_YELLOW" "$@"; }
die() { emit_log error 'ERROR' "$CLR_RED" "$@"; exit 1; }

require_external_output_path() {
  local output_kind="$1"
  local output_path="$2"
  [[ "$output_path" == /* ]] || die "$output_kind must use an absolute path outside the repository; relative output paths are refused."
  case "$output_path" in
    "$REPOSITORY_ROOT"|"$REPOSITORY_ROOT"/*)
      die "$output_kind must be outside the repository; recovery output is never written into Git working tree $REPOSITORY_ROOT."
      ;;
  esac
}

start_logging() {
  if [[ "$LOG_FILE" == 'none' ]]; then
    return
  fi
  if [[ -z "$LOG_FILE" ]]; then
    LOG_FILE="$HOME/Library/Logs/DJConnect/macos-runner-recovery-$(date -u '+%Y%m%dT%H%M%SZ').log"
  fi
  require_external_output_path 'Recovery transcript log' "$LOG_FILE"
  if [[ "$DRY_RUN" == '1' ]]; then
    printf 'DRY: capture complete non-sensitive recovery output in %s\n' "$LOG_FILE"
    return
  fi
  umask 077
  mkdir -p "$(dirname "$LOG_FILE")"
  touch "$LOG_FILE"
  chmod 600 "$LOG_FILE"
  [[ -f "$REDACTION_RULES" ]] || die "Recovery transcript redaction rules are unavailable: $REDACTION_RULES"
  LOG_CAPTURE_DIRECTORY="$(mktemp -d "${TMPDIR:-/tmp}/djconnect-recovery-log.XXXXXX")"
  LOG_CAPTURE_PIPE="$LOG_CAPTURE_DIRECTORY/output"
  mkfifo "$LOG_CAPTURE_PIPE"
  sed -E -f "$REDACTION_RULES" <"$LOG_CAPTURE_PIPE" | tee -a "$LOG_FILE" &
  LOG_CAPTURE_PID="$!"
  exec >"$LOG_CAPTURE_PIPE" 2>&1
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

phase_section_id() {
  local phase_id="$1"
  case "$phase_id" in
    macos-preflight) printf '%s' 'host-qualification' ;;
    sudo|tooling|xcode|parallels) printf '%s' 'host-provisioning' ;;
    github-auth|permissions-audit|repositories) printf '%s' 'repository-access' ;;
    developer-workstation|docker-auth) printf '%s' 'developer-workstation' ;;
    runner-apple|runner-private-network|runner-esp32|runner-pi) printf '%s' 'runner-provisioning' ;;
    maintenance|tooling-refresh|reboot-check) printf '%s' 'host-maintenance' ;;
    apple-signing|apple-readiness|credential-expiry-audit|apple-github-audit) printf '%s' 'apple-readiness' ;;
    services|initial-verification) printf '%s' 'final-qualification' ;;
    *) die "No installation section is defined for phase: $phase_id" ;;
  esac
}

section_title() {
  case "$1" in
    host-qualification) printf '%s' 'Host qualification' ;;
    host-provisioning) printf '%s' 'Host tooling and platform provisioning' ;;
    repository-access) printf '%s' 'Repository access and synchronization' ;;
    developer-workstation) printf '%s' 'Developer workstation services' ;;
    runner-provisioning) printf '%s' 'GitHub Actions runner provisioning' ;;
    host-maintenance) printf '%s' 'Host maintenance and reboot readiness' ;;
    apple-readiness) printf '%s' 'Apple internal-release readiness' ;;
    final-qualification) printf '%s' 'Final runner and host qualification' ;;
    *) die "Unknown installation section: $1" ;;
  esac
}

section_description() {
  case "$1" in
    host-qualification) printf '%s' 'Validate physical Apple-Silicon host capacity before any mutation.' ;;
    host-provisioning) printf '%s' 'Install or qualify shared macOS tooling and optional platform components.' ;;
    repository-access) printf '%s' 'Authenticate and synchronize the managed DJConnect repositories.' ;;
    developer-workstation) printf '%s' 'Restore local development services and authenticated Docker access.' ;;
    runner-provisioning) printf '%s' 'Register selected self-hosted runners; eligible profiles run CPU-bounded in parallel.' ;;
    host-maintenance) printf '%s' 'Install maintenance, refresh tooling and check for a required reboot.' ;;
    apple-readiness) printf '%s' 'Restore local signing readiness and audit Apple GitHub Environment configuration.' ;;
    final-qualification) printf '%s' 'Validate runner services and execute final post-recovery verification.' ;;
    *) die "Unknown installation section: $1" ;;
  esac
}

begin_report_section() {
  local section_id="$1"
  [[ "$CURRENT_REPORT_SECTION" == "$section_id" ]] && return 0
  CURRENT_REPORT_SECTION="$section_id"
  printf '\n%s %s\n' "$(style "$CLR_CYAN$CLR_BOLD" 'SECTION')" "$(section_title "$section_id")"
  report_append "Section: $(section_title "$section_id")" 'IN PROGRESS' "$(section_description "$section_id")"
}

begin_phase_section() {
  begin_report_section "$(phase_section_id "$1")"
}

all_section_ids() {
  printf '%s\n' host-qualification host-provisioning repository-access developer-workstation runner-provisioning host-maintenance apple-readiness final-qualification
}

section_phase_ids() {
  case "$1" in
    host-qualification) printf '%s\n' macos-preflight ;;
    host-provisioning) printf '%s\n' sudo tooling xcode parallels ;;
    repository-access) printf '%s\n' github-auth permissions-audit repositories ;;
    developer-workstation) printf '%s\n' developer-workstation docker-auth ;;
    runner-provisioning) printf '%s\n' runner-apple runner-private-network runner-esp32 runner-pi ;;
    host-maintenance) printf '%s\n' maintenance tooling-refresh reboot-check ;;
    apple-readiness) printf '%s\n' apple-signing apple-readiness credential-expiry-audit apple-github-audit ;;
    final-qualification) printf '%s\n' services initial-verification ;;
    *) die "Unknown installation section: $1" ;;
  esac
}

phase_is_in_scope() {
  local phase_id="$1"
  case "$phase_id" in
    runner-*) profile_enabled "${phase_id#runner-}" ;;
    *) return 0 ;;
  esac
}

phase_progress_snapshot() {
  local phase_id phase_state total=0 completed=0
  for phase_id in $(all_phase_ids); do
    phase_is_in_scope "$phase_id" || continue
    total=$((total + 1))
    phase_state="$(get_phase_state "$phase_id")"
    case "$phase_state" in
      PASSED|SKIPPED|FAILED|BLOCKED) completed=$((completed + 1)) ;;
    esac
  done
  (( total > 0 )) || total=1
  printf '%s %s %s' "$(( completed * 100 / total ))" "$completed" "$total"
}

emit_phase_progress() {
  local event="$1"
  local percent completed total
  read -r percent completed total <<<"$(phase_progress_snapshot)"
  progress "${percent}% [${completed}/${total} phases] $event"
  report_append 'Progress' "${percent}%" "${completed}/${total} in-scope phases reached a terminal state. $event"
}

emit_repair_progress() {
  local event="$1"
  REPAIR_PROGRESS_COMPLETED=$((REPAIR_PROGRESS_COMPLETED + 1))
  local percent=$(( REPAIR_PROGRESS_COMPLETED * 100 / REPAIR_PROGRESS_TOTAL ))
  progress "${percent}% [${REPAIR_PROGRESS_COMPLETED}/${REPAIR_PROGRESS_TOTAL} repair stages] $event"
  report_append 'Repair progress' "${percent}%" "${REPAIR_PROGRESS_COMPLETED}/${REPAIR_PROGRESS_TOTAL} repair stages completed. $event"
}

append_section_summary() {
  local section_id phase_id phase_state total passed failed skipped pending
  printf '\n## Installation section summary\n\n'
  printf '%s\n' '| Section | Status | Phase evidence |'
  printf '%s\n' '| --- | --- | --- |'
  for section_id in $(all_section_ids); do
    total=0; passed=0; failed=0; skipped=0; pending=0
    for phase_id in $(section_phase_ids "$section_id"); do
      phase_is_in_scope "$phase_id" || continue
      total=$((total + 1))
      phase_state="$(get_phase_state "$phase_id")"
      case "$phase_state" in
        PASSED) passed=$((passed + 1)) ;;
        SKIPPED) skipped=$((skipped + 1)) ;;
        FAILED|BLOCKED) failed=$((failed + 1)) ;;
        *) pending=$((pending + 1)) ;;
      esac
    done
    if [[ "$section_id" == 'repository-access' && "$PERMISSIONS_AUDIT_HAS_WARNINGS" == '1' ]]; then
      printf '| %s | **ATTENTION REQUIRED** | %s passed; least-privilege warnings require review |\n' "$(section_title "$section_id")" "$passed"
    elif [[ "$section_id" == 'apple-readiness' && "$CREDENTIAL_EXPIRY_HAS_WARNINGS" == '1' ]]; then
      printf '| %s | **ATTENTION REQUIRED** | %s passed; certificate or provisioning-profile expiry warnings require renewal |\n' "$(section_title "$section_id")" "$passed"
    elif (( failed > 0 )); then
      printf '| %s | **ATTENTION REQUIRED** | %s passed, %s failed or blocked, %s skipped, %s pending |\n' "$(section_title "$section_id")" "$passed" "$failed" "$skipped" "$pending"
    elif (( skipped > 0 )); then
      printf '| %s | **FOLLOW-UP REQUIRED** | %s passed, %s skipped, %s pending |\n' "$(section_title "$section_id")" "$passed" "$skipped" "$pending"
    elif (( pending > 0 )); then
      printf '| %s | **NOT COMPLETED** | %s passed, %s pending |\n' "$(section_title "$section_id")" "$passed" "$pending"
    else
      printf '| %s | **COMPLETED** | %s/%s phases passed |\n' "$(section_title "$section_id")" "$passed" "$total"
    fi
  done
}

start_report() {
  if [[ "$REPORT_FILE" == 'none' ]]; then
    return
  fi
  if [[ -z "$REPORT_FILE" ]]; then
    REPORT_FILE="$HOME/Library/Logs/DJConnect/macos-runner-recovery-$(date -u '+%Y%m%dT%H%M%SZ').md"
  fi
  require_external_output_path 'Recovery Markdown report' "$REPORT_FILE"
  if [[ "$DRY_RUN" == '1' ]]; then
    printf 'DRY: write final Markdown recovery report to %s\n' "$REPORT_FILE"
    return
  fi
  umask 077
  mkdir -p "$(dirname "$REPORT_FILE")"
  {
    printf '# DJConnect macOS Runner Recovery Report\n\n'
    printf '%s\n' "- Bootstrap version: $SCRIPT_VERSION"
    printf '%s\n' "- Log level: $LOG_LEVEL"
    printf 'Started (UTC): %s\n\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    if [[ "$REPAIR_MODE" == '1' ]]; then
      printf '%s\n' '- Mode: unattended desired-state repair'
    else
      printf '%s\n' '- Mode: recovery execution'
    fi
    printf '%s\n' "- Desired state: $DESIRED_STATE_FILE (schema $DESIRED_STATE_SCHEMA_VERSION)"
    printf '%s\n' "- Selected runner profiles: $PROFILE_SELECTION"
    printf '%s\n\n' "- Transcript log: ${LOG_FILE:-not configured}"
    printf '%s\n' '| Step | Status | Result |'
    printf '%s\n' '| --- | --- | --- |'
  } >"$REPORT_FILE"
  chmod 600 "$REPORT_FILE"
  REPORTING_STARTED=1
}

complete_report() {
  local exit_code="$1" requirement
  [[ "$REPORTING_STARTED" == '1' ]] || return 0
  if [[ -n "$CURRENT_STEP" ]]; then
    report_append "$CURRENT_STEP" 'FAILED' 'Stopped before this step completed; inspect the transcript log for the exact error.'
    CURRENT_STEP=''
  fi
  if [[ "$REPAIR_MODE" == '1' ]]; then
    {
      printf '\n## Unattended repair outcome\n\n'
      printf '%s\n' "- Baseline verify exit code: ${REPAIR_INITIAL_VERIFY_STATUS:-not run}"
      printf '%s\n' "- Post-repair verify exit code: ${REPAIR_FINAL_VERIFY_STATUS:-not run}"
      if (( ${#REPAIR_MANUAL_REQUIREMENTS[@]} == 0 )); then
        printf '%s\n' '- Remaining manual input: none recorded.'
      else
        printf '%s\n' '- Remaining manual input:'
        for requirement in "${REPAIR_MANUAL_REQUIREMENTS[@]}"; do
          printf '%s\n' "  - $requirement"
        done
      fi
      printf '\n## Installation section summary\n\n'
      if (( ${#REPAIR_MANUAL_REQUIREMENTS[@]} == 0 )); then
        printf '%s\n' '- All unattended repair sections completed without a recorded manual boundary; use the post-repair verification result below as the desired-state decision.'
      else
        printf '%s\n' "- **ATTENTION REQUIRED** — ${#REPAIR_MANUAL_REQUIREMENTS[@]} manual requirement(s) remain; the section rows above identify their owning installation area."
      fi
      printf '\n## Desired-state repair verdict\n\n'
      if [[ "$REPAIR_FINAL_VERIFY_STATUS" == '0' ]]; then
        printf '%s\n' '**MATCH** — the post-repair verification confirms that all required desired-state rows match.'
        printf '%s\n' '**REPAIR COMPLETE** — no further desired-state remediation is required.'
      else
        printf '%s\n' '**DRIFT REMAINS** — the post-repair verification found required differences.'
        printf '%s\n' '**MANUAL FOLLOW-UP REQUIRED** — complete the listed actions, then run one new `--repair` pass or use the full interactive recovery flow.'
      fi
      printf '\nCompleted (UTC): %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    } >>"$REPORT_FILE"
    return 0
  fi
  {
    append_section_summary
    printf '\n## Verification-run verdict\n\n'
    printf '%s\n' '- Verification phase: Initial post-recovery verification'
    if [[ "$INITIAL_VERIFICATION_PASSED" == '1' ]]; then
      printf '%s\n' '- Result: **PASSED**'
    elif [[ "$exit_code" != '0' ]]; then
      printf '%s\n' '- Result: **FAILED OR INCOMPLETE**'
    else
      printf '%s\n' '- Result: **NOT RUN**'
    fi
    printf '\n## Final status\n\n'
    if [[ "$exit_code" != '0' ]]; then
      printf '%s\n' '**FAILED** — recovery stopped before completion; inspect the transcript log and the failed step above.'
    elif [[ "$SKIPPED_PHASE_COUNT" != '0' ]]; then
      printf '%s\n' "**COMPLETED WITH SKIPPED PHASES** — $SKIPPED_PHASE_COUNT phase(s) were intentionally skipped and require separate qualification."
    elif [[ "$INITIAL_VERIFICATION_PASSED" != '1' ]]; then
      printf '%s\n' '**INCOMPLETE** — the required initial post-recovery verification did not run.'
    else
      printf '%s\n' '**PASSED** — all requested recovery stages completed successfully.'
    fi
    printf '\n## Conclusion\n\n'
    if [[ "$exit_code" == '0' && "$SKIPPED_PHASE_COUNT" == '0' && "$INITIAL_VERIFICATION_PASSED" == '1' ]]; then
      printf '%s\n' '**HOST QUALIFIED FOR THE REQUESTED DJCONNECT RECOVERY SCOPE.** This conclusion is based on the successful initial post-recovery verification run.'
    elif [[ "$INITIAL_VERIFICATION_PASSED" == '1' ]]; then
      printf '%s\n' '**NOT FULLY QUALIFIED.** The verification run passed, but intentionally skipped phases require separate execution and qualification before the host is treated as release-capable.'
    else
      printf '%s\n' '**NOT QUALIFIED.** No positive release-capability conclusion may be drawn until the initial post-recovery verification run succeeds without unresolved skipped phases.'
    fi
    printf '\nCompleted (UTC): %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  } >>"$REPORT_FILE"
}

record_repair_manual_requirement() {
  local requirement="$1"
  REPAIR_MANUAL_REQUIREMENTS+=("$requirement")
  warn "MANUAL INPUT REQUIRED: $requirement"
  report_append 'Unattended repair' 'MANUAL INPUT REQUIRED' "$requirement"
}

phase_is_skipped() {
  local phase_id="$1"
  [[ -n "$SKIP_PHASES" && ",$SKIP_PHASES," == *",$phase_id,"* ]]
}

phase_is_forced() {
  local phase_id="$1"
  [[ -n "$FORCE_PHASES" && ",$FORCE_PHASES," == *",$phase_id,"* ]]
}

phase_state_variable() {
  local phase_id="$1"
  printf 'PHASE_STATE_%s' "${phase_id//-/_}"
}

set_phase_state() {
  local phase_id="$1"
  local phase_state="$2"
  local variable_name
  variable_name="$(phase_state_variable "$phase_id")"
  printf -v "$variable_name" '%s' "$phase_state"
}

get_phase_state() {
  local phase_id="$1"
  local variable_name
  variable_name="$(phase_state_variable "$phase_id")"
  printf '%s' "${!variable_name:-PENDING}"
}

all_phase_ids() {
  local profile
  printf '%s\n' macos-preflight sudo tooling xcode parallels github-auth permissions-audit repositories developer-workstation docker-auth
  for profile in "${DESIRED_PROFILES[@]}"; do
    printf 'runner-%s\n' "$profile"
  done
  printf '%s\n' maintenance tooling-refresh reboot-check services apple-signing apple-readiness credential-expiry-audit apple-github-audit initial-verification
}

phase_execution_capability() {
  local phase_id="$1"
  case "$phase_id" in
    runner-apple|runner-private-network|runner-esp32|runner-pi|apple-github-audit)
      printf '%s' 'HEADLESS + PARALLEL SAFE'
      ;;
    *)
      printf '%s' 'SERIAL OR OPERATOR-INTERACTIVE'
      ;;
  esac
}

phase_execution_note() {
  local phase_id="$1"
  case "$phase_id" in
    runner-apple|runner-private-network|runner-esp32|runner-pi)
      printf '%s' 'Unattended after prerequisites; each profile uses a separate runner directory and repository registration.'
      ;;
    apple-github-audit)
      printf '%s' 'Read-only GitHub Environment inventory after GitHub CLI authentication.'
      ;;
    *)
      printf '%s' 'Keep in declared order because it establishes host state, has an interactive boundary, or validates shared state.'
      ;;
  esac
}

print_phase_catalog() {
  local phase_id
  printf '%-26s | %-31s | %s\n' 'PHASE ID' 'EXECUTION CAPABILITY' 'NOTES'
  printf '%-26s-+-%-31s-+-%s\n' "$(printf '%*s' 26 '' | tr ' ' '-')" "$(printf '%*s' 31 '' | tr ' ' '-')" "$(printf '%*s' 65 '' | tr ' ' '-')"
  for phase_id in macos-preflight sudo tooling xcode parallels github-auth repositories developer-workstation docker-auth runner-apple runner-private-network runner-esp32 runner-pi maintenance tooling-refresh reboot-check services apple-signing apple-readiness apple-github-audit initial-verification; do
    printf '%-26s | %-31s | %s\n' "$phase_id" "$(phase_execution_capability "$phase_id")" "$(phase_execution_note "$phase_id")"
  done
}

write_resume_checkpoint() {
  local next_phase="$1"
  local phase_id phase_state
  require_external_output_path 'Recovery resume checkpoint' "$RESUME_STATE_FILE"
  umask 077
  mkdir -p "$(dirname "$RESUME_STATE_FILE")"
  {
    printf 'schema_version=1\n'
    printf 'next_phase=%s\n' "$next_phase"
    printf 'desired_state_file=%s\n' "$DESIRED_STATE_FILE"
    printf 'profile_selection=%s\n' "$PROFILE_SELECTION"
    printf 'github_root=%s\n' "$GITHUB_ROOT"
    printf 'runner_root=%s\n' "$RUNNER_ROOT"
    for phase_id in $(all_phase_ids); do
      phase_state="$(get_phase_state "$phase_id")"
      [[ "$phase_state" == 'PASSED' ]] && printf 'phase.%s=%s\n' "$phase_id" "$phase_state"
    done
  } >"$RESUME_STATE_FILE"
  chmod 600 "$RESUME_STATE_FILE"
  log "Recovery paused for reboot. Resume after restart with: $0 --resume"
}

load_resume_checkpoint() {
  local key value phase_id
  [[ -f "$RESUME_STATE_FILE" ]] || die "No reboot-resume checkpoint exists: $RESUME_STATE_FILE"
  [[ "$(stat -f '%Lp' "$RESUME_STATE_FILE")" == '600' ]] || die "Resume checkpoint must have owner-only 0600 permissions: $RESUME_STATE_FILE"
  while IFS='=' read -r key value; do
    case "$key" in
      schema_version) [[ "$value" == '1' ]] || die "Unsupported resume checkpoint schema: $value" ;;
      next_phase) RESUME_NEXT_PHASE="$value" ;;
      desired_state_file) [[ "$value" == "$DESIRED_STATE_FILE" ]] || die 'Resume checkpoint desired-state manifest differs from this invocation.' ;;
      profile_selection) [[ "$value" == "$PROFILE_SELECTION" ]] || die 'Resume checkpoint profile selection differs from this invocation.' ;;
      github_root) [[ "$value" == "$GITHUB_ROOT" ]] || die 'Resume checkpoint GitHub root differs from this invocation.' ;;
      runner_root) [[ "$value" == "$RUNNER_ROOT" ]] || die 'Resume checkpoint runner root differs from this invocation.' ;;
      phase.*) phase_id="${key#phase.}"; [[ "$value" == 'PASSED' ]] || die "Invalid resume phase state for $phase_id"; set_phase_state "$phase_id" PASSED ;;
      '') ;;
      *) die "Unknown resume checkpoint field: $key" ;;
    esac
  done <"$RESUME_STATE_FILE"
  [[ "$RESUME_NEXT_PHASE" == 'reboot-check' ]] || die "Unsupported resume point: ${RESUME_NEXT_PHASE:-missing}"
  log "Loaded reboot-resume checkpoint; continuing with $RESUME_NEXT_PHASE."
}

clear_resume_checkpoint() {
  [[ -f "$RESUME_STATE_FILE" ]] || return 0
  rm -f "$RESUME_STATE_FILE"
}

phase_dependencies() {
  local phase_id="$1"
  case "$phase_id" in
    macos-preflight) ;;
    sudo|tooling) printf '%s' 'macos-preflight' ;;
    xcode) printf '%s' 'tooling' ;;
    parallels) printf '%s' 'tooling' ;;
    github-auth) printf '%s' 'tooling' ;;
    permissions-audit) printf '%s' 'github-auth' ;;
    repositories) printf '%s' 'permissions-audit' ;;
    developer-workstation) printf '%s' 'repositories sudo tooling' ;;
    docker-auth) printf '%s' 'developer-workstation' ;;
    runner-apple) printf '%s' 'repositories github-auth sudo xcode' ;;
    runner-private-network|runner-esp32|runner-pi) printf '%s' 'repositories github-auth sudo' ;;
    maintenance) printf '%s' 'repositories' ;;
    tooling-refresh) printf '%s' 'tooling sudo' ;;
    reboot-check) printf '%s' 'tooling-refresh' ;;
    services)
      printf '%s' 'maintenance'
      local profile
      for profile in "${DESIRED_PROFILES[@]}"; do
        if profile_enabled "$profile"; then
          printf ' runner-%s' "$profile"
        fi
      done
      ;;
    apple-signing) printf '%s' 'xcode' ;;
    apple-readiness) printf '%s' 'repositories github-auth xcode' ;;
    credential-expiry-audit) printf '%s' 'apple-readiness' ;;
    apple-github-audit) printf '%s' 'credential-expiry-audit' ;;
    initial-verification) printf '%s' 'repositories developer-workstation docker-auth services reboot-check' ;;
    *) die "No dependency definition exists for phase: $phase_id" ;;
  esac
}

phase_runtime_conditions() {
  local phase_id="$1"
  if [[ "$DRY_RUN" == '1' ]]; then
    PHASE_PRECHECK_RESULT='Declared dependencies satisfied in the dry-run plan; runtime conditions will be checked during execution.'
    return 0
  fi
  case "$phase_id" in
    macos-preflight) PHASE_PRECHECK_RESULT='Host qualification will verify macOS, Apple Silicon, RAM, cores and free disk space.' ;;
    sudo) dseditgroup -o checkmember -m "$(id -un)" admin | grep -Fq 'yes' || return 1; PHASE_PRECHECK_RESULT='Current user is a local macOS administrator.' ;;
    tooling) command -v curl >/dev/null 2>&1 || return 1; PHASE_PRECHECK_RESULT='curl is available for supported tooling bootstrap.' ;;
    xcode|parallels|tooling-refresh) command -v brew >/dev/null 2>&1 || return 1; PHASE_PRECHECK_RESULT='Homebrew is available.' ;;
    github-auth|permissions-audit|repositories|apple-github-audit) command -v gh >/dev/null 2>&1 || return 1; PHASE_PRECHECK_RESULT='GitHub CLI is available.' ;;
    developer-workstation|initial-verification) [[ -f "$GITHUB_ROOT/djconnect/tools/dev_onboarding_macos.sh" ]] || return 1; PHASE_PRECHECK_RESULT='Central developer-onboarding script is available.' ;;
    docker-auth) command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1 || return 1; PHASE_PRECHECK_RESULT='Docker Desktop daemon is ready.' ;;
    runner-apple|runner-private-network|runner-esp32|runner-pi) command -v gh >/dev/null 2>&1 && sudo -n true >/dev/null 2>&1 || return 1; PHASE_PRECHECK_RESULT='GitHub CLI and non-interactive administrator access are available for runner registration.' ;;
    maintenance) [[ -f "$GITHUB_ROOT/djconnect-app/scripts/runner/install_macos_ci_tooling_maintenance.sh" ]] || return 1; PHASE_PRECHECK_RESULT='macOS maintenance installer is available.' ;;
    reboot-check) command -v softwareupdate >/dev/null 2>&1 || return 1; PHASE_PRECHECK_RESULT='macOS Software Update utility is available.' ;;
    services) PHASE_PRECHECK_RESULT='Runner and LaunchAgent validation will use the completed installation state.' ;;
    apple-signing) command -v security >/dev/null 2>&1 || return 1; PHASE_PRECHECK_RESULT='macOS keychain tooling is available.' ;;
    apple-readiness) command -v xcodebuild >/dev/null 2>&1 || return 1; PHASE_PRECHECK_RESULT='Xcode command-line tooling is available.' ;;
    credential-expiry-audit) command -v security >/dev/null 2>&1 || return 1; PHASE_PRECHECK_RESULT='macOS keychain tooling is available for non-secret expiry checks.' ;;
    *) die "No runtime-condition definition exists for phase: $phase_id" ;;
  esac
}

precheck_phase() {
  local phase_id="$1"
  local dependency dependency_state dependencies
  dependencies="$(phase_dependencies "$phase_id")"
  for dependency in $dependencies; do
    dependency_state="$(get_phase_state "$dependency")"
    if [[ "$dependency_state" != 'PASSED' ]]; then
      PHASE_PRECHECK_RESULT="Dependency $dependency is $dependency_state; PASSED is required."
      return 1
    fi
  done
  if ! phase_runtime_conditions "$phase_id"; then
    PHASE_PRECHECK_RESULT="Runtime conditions are not met for phase $phase_id."
    return 1
  fi
  if [[ -n "$dependencies" ]]; then
    PHASE_PRECHECK_RESULT="Dependencies passed: $dependencies. $PHASE_PRECHECK_RESULT"
  else
    PHASE_PRECHECK_RESULT="No phase dependencies. $PHASE_PRECHECK_RESULT"
  fi
}

validate_skip_phases() {
  local phase_id
  [[ -z "$SKIP_PHASES" ]] && return 0
  IFS=',' read -r -a requested_phase_ids <<<"$SKIP_PHASES"
  for phase_id in "${requested_phase_ids[@]}"; do
    case "$phase_id" in
      sudo|tooling|xcode|parallels|github-auth|permissions-audit|repositories|developer-workstation|docker-auth|runner-apple|runner-private-network|runner-esp32|runner-pi|maintenance|tooling-refresh|reboot-check|services|apple-signing|apple-readiness|credential-expiry-audit|apple-github-audit|initial-verification) ;;
      macos-preflight) die 'macos-preflight is mandatory and cannot be skipped.' ;;
      '') ;;
      *) die "Unknown --skip-phases ID: $phase_id" ;;
    esac
  done
}

validate_force_phases() {
  local phase_id
  [[ -z "$FORCE_PHASES" ]] && return 0
  IFS=',' read -r -a requested_phase_ids <<<"$FORCE_PHASES"
  for phase_id in "${requested_phase_ids[@]}"; do
    case "$phase_id" in
      macos-preflight|sudo|tooling|xcode|parallels|github-auth|permissions-audit|repositories|developer-workstation|docker-auth|runner-apple|runner-private-network|runner-esp32|runner-pi|maintenance|tooling-refresh|reboot-check|services|apple-signing|apple-readiness|credential-expiry-audit|apple-github-audit|initial-verification) ;;
      '') ;;
      *) die "Unknown --force-phases ID: $phase_id" ;;
    esac
    if phase_is_skipped "$phase_id"; then
      die "A phase cannot be both skipped and forced: $phase_id"
    fi
  done
}

skip_phase() {
  local phase_id="$1"
  local step="$2"
  local reason="$3"
  SKIPPED_PHASE_COUNT=$((SKIPPED_PHASE_COUNT + 1))
  set_phase_state "$phase_id" 'SKIPPED'
  report_append "$step" 'SKIPPED' "$reason (phase ID: $phase_id)."
  emit_phase_progress "Skipped: $step."
  warn "$step was skipped: $reason"
  CURRENT_STEP=''
}

run_phase() {
  local phase_id="$1"
  local step="$2"
  shift 2
  local attempt=1
  local phase_status
  begin_phase_section "$phase_id"
  if [[ "$RESUME_MODE" == '1' && "$phase_id" != 'macos-preflight' && "$(get_phase_state "$phase_id")" == 'PASSED' ]]; then
    report_append "$step" 'RESUMED' 'Previously completed before the required reboot; preserved by the owner-only resume checkpoint.'
    emit_phase_progress "Resumed: $step."
    return 0
  fi
  if phase_is_skipped "$phase_id"; then
    skip_phase "$phase_id" "$step" 'Operator requested skip through --skip-phases'
    return 0
  fi
  CURRENT_STEP="$step"
  CURRENT_PHASE_ID="$phase_id"
  emit_phase_progress "Starting: $step."
  report_append "Execution capability: $step" "$(phase_execution_capability "$phase_id")" "$(phase_execution_note "$phase_id")"
  verbose "$step execution capability: $(phase_execution_capability "$phase_id")."
  if ! precheck_phase "$phase_id"; then
    set_phase_state "$phase_id" 'BLOCKED'
    report_append "Precheck: $step" 'FAILED' "$PHASE_PRECHECK_RESULT"
    emit_phase_progress "Blocked: $step."
    die "Precheck failed for $step: $PHASE_PRECHECK_RESULT"
  fi
  report_append "Precheck: $step" 'PASSED' "$PHASE_PRECHECK_RESULT"
  if phase_is_forced "$phase_id"; then
    log "Force reconciliation requested for $step; existing desired state will be verified without destructive recreation."
  fi
  while true; do
    log "$step (attempt $attempt)"
    set +e
    (set -e; "$@")
    phase_status=$?
    set -e
    if [[ "$phase_status" == '75' && "$phase_id" == 'reboot-check' ]]; then
      report_append "$step" 'PAUSED FOR REBOOT' "Required reboot detected; resume state stored at $RESUME_STATE_FILE."
      CURRENT_STEP=''
      exit 75
    fi
    if [[ "$phase_status" == '42' && "$phase_id" == 'permissions-audit' ]]; then
      PERMISSIONS_AUDIT_HAS_WARNINGS=1
      set_phase_state "$phase_id" 'PASSED'
      report_append "$step" "PASSED WITH WARNINGS (attempt $attempt)" 'Completed with one or more least-privilege warnings; review the audit evidence.'
      emit_phase_progress "Completed with warnings: $step."
      warn "$step completed with least-privilege warnings; review before treating the host as appropriately scoped."
      CURRENT_STEP=''
      CURRENT_PHASE_ID=''
      return 0
    fi
    if [[ "$phase_status" == '43' && "$phase_id" == 'credential-expiry-audit' ]]; then
      CREDENTIAL_EXPIRY_HAS_WARNINGS=1
      set_phase_state "$phase_id" 'PASSED'
      report_append "$step" "PASSED WITH WARNINGS (attempt $attempt)" 'Certificate or provisioning-profile expiry requires attention; review the expiry evidence.'
      emit_phase_progress "Completed with expiry warnings: $step."
      warn "$step completed with certificate or provisioning-profile expiry warnings; renew affected credentials before release work."
      CURRENT_STEP=''
      CURRENT_PHASE_ID=''
      return 0
    fi
    if [[ "$phase_status" == '0' ]]; then
      set_phase_state "$phase_id" 'PASSED'
      if [[ "$phase_id" == 'initial-verification' ]]; then
        INITIAL_VERIFICATION_PASSED=1
      fi
      report_append "$step" "PASSED (attempt $attempt)" 'Completed successfully; see the central transcript for detailed command output.'
      emit_phase_progress "Completed: $step."
      ok "$step"
      CURRENT_STEP=''
      CURRENT_PHASE_ID=''
      return 0
    fi

    report_append "$step" "FAILED (attempt $attempt)" "Exited with status $phase_status."
    warn "$step failed with status $phase_status."
    if [[ "$ALLOW_STEP_RETRY" != '1' || "$DRY_RUN" == '1' || ! -r /dev/tty || ! -w /dev/tty ]]; then
    set_phase_state "$phase_id" 'FAILED'
      emit_phase_progress "Failed: $step."
      die "Recovery phase failed: $step"
    fi
    printf 'Retry this phase? [r]etry / [s]kip / [a]bort: ' >/dev/tty
    local response=''
    read -r response </dev/tty
    case "$response" in
      r|R|retry|Retry|RETRY)
        report_append "$step" 'RETRYING' "Operator requested retry after attempt $attempt."
        attempt=$((attempt + 1))
        ;;
      s|S|skip|Skip|SKIP)
        skip_phase "$phase_id" "$step" "Operator skipped failed attempt $attempt"
        return 0
        ;;
      a|abort|'') die "Recovery phase aborted by operator: $step" ;;
      *) warn 'Enter r to retry, s to skip this phase, or a to abort recovery.' ;;
    esac
  done
}

available_cpu_cores() {
  local cpu_count
  cpu_count="$(sysctl -n hw.ncpu 2>/dev/null || getconf _NPROCESSORS_ONLN 2>/dev/null || printf '1')"
  [[ "$cpu_count" =~ ^[0-9]+$ ]] && (( cpu_count > 0 )) || cpu_count=1
  printf '%s' "$cpu_count"
}

parallel_worker_limit() {
  local candidate_count="$1"
  local cpu_count worker_limit
  cpu_count="$(available_cpu_cores)"
  if (( PARALLEL_JOBS == 0 )); then
    worker_limit=$(( cpu_count / 2 ))
    (( worker_limit > 0 )) || worker_limit=1
  else
    worker_limit="$PARALLEL_JOBS"
  fi
  (( worker_limit <= cpu_count )) || die "Parallel job count $worker_limit exceeds the $cpu_count available CPU cores."
  (( worker_limit <= candidate_count )) || worker_limit="$candidate_count"
  printf '%s' "$worker_limit"
}

parallel_phase_worker() {
  local phase_id="$1"
  shift
  trap - EXIT
  CURRENT_PHASE_ID="$phase_id"
  CURRENT_STEP=''
  "$@"
}

prepare_parallel_phase() {
  local phase_id="$1"
  local step="$2"
  CURRENT_PHASE_ID="$phase_id"
  begin_phase_section "$phase_id"
  if ! precheck_phase "$phase_id"; then
    set_phase_state "$phase_id" 'BLOCKED'
    report_append "Precheck: $step" 'FAILED' "$PHASE_PRECHECK_RESULT"
    die "Precheck failed for $step: $PHASE_PRECHECK_RESULT"
  fi
  report_append "Execution capability: $step" "$(phase_execution_capability "$phase_id")" "$(phase_execution_note "$phase_id")"
  report_append "Precheck: $step" 'PASSED' "$PHASE_PRECHECK_RESULT"
  set_phase_state "$phase_id" 'RUNNING'
  emit_phase_progress "Starting parallel phase: $step."
}

complete_parallel_phase() {
  local phase_id="$1"
  local step="$2"
  local status="$3"
  local output_file="$4"
  if [[ -s "$output_file" ]]; then
    cat "$output_file"
  fi
  rm -f "$output_file"
  if [[ "$status" == '0' ]]; then
    set_phase_state "$phase_id" 'PASSED'
    report_append "$step" 'PASSED (parallel)' 'Completed headlessly in a CPU-bounded parallel batch; see the central transcript for detailed command output.'
    emit_phase_progress "Completed parallel phase: $step."
    ok "$step (parallel)"
    return 0
  fi
  set_phase_state "$phase_id" 'FAILED'
  report_append "$step" 'FAILED (parallel)' "Exited with status $status."
  emit_phase_progress "Failed parallel phase: $step."
  warn "$step failed with status $status in the parallel batch."
  return "$status"
}

run_parallel_runner_profiles() {
  local -a profiles=() phase_ids=() steps=() output_files=() pids=()
  local profile phase_id step worker_limit index batch_end pid status failures=0
  for profile in "${DESIRED_PROFILES[@]}"; do
    profile_enabled "$profile" || continue
    phase_id="runner-$profile"
    [[ "$(phase_execution_capability "$phase_id")" == 'HEADLESS + PARALLEL SAFE' ]] || die "Runner phase $phase_id is not declared parallel-safe."
    profiles+=("$profile")
    phase_ids+=("$phase_id")
    steps+=("GitHub Actions runner profile: $profile")
  done
  (( ${#profiles[@]} > 0 )) || return 0
  worker_limit="$(parallel_worker_limit "${#profiles[@]}")"
  log "Scheduling ${#profiles[@]} headless runner profile(s) with a maximum of $worker_limit concurrent job(s) across $(available_cpu_cores) CPU core(s)."
  report_append 'Parallel execution plan' 'CPU-BOUNDED' "${#profiles[@]} runner phase(s); maximum $worker_limit concurrent job(s) across $(available_cpu_cores) CPU core(s)."

  index=0
  while (( index < ${#profiles[@]} )); do
    batch_end=$(( index + worker_limit ))
    (( batch_end <= ${#profiles[@]} )) || batch_end="${#profiles[@]}"
    output_files=()
    pids=()
    while (( index < batch_end )); do
      phase_id="${phase_ids[$index]}"
      step="${steps[$index]}"
      prepare_parallel_phase "$phase_id" "$step"
      output_file="$(mktemp "${TMPDIR:-/tmp}/djconnect-${phase_id}.XXXXXX")"
      parallel_phase_worker "$phase_id" install_runner_profile "${profiles[$index]}" >"$output_file" 2>&1 &
      pids+=("$!")
      output_files+=("$output_file")
      index=$((index + 1))
    done
    local batch_index
    for batch_index in "${!pids[@]}"; do
      pid="${pids[$batch_index]}"
      set +e
      wait "$pid"
      status=$?
      set -e
      if ! complete_parallel_phase "${phase_ids[$((index - ${#pids[@]} + batch_index))]}" "${steps[$((index - ${#pids[@]} + batch_index))]}" "$status" "${output_files[$batch_index]}"; then
        failures=$((failures + 1))
      fi
    done
    (( failures == 0 )) || die "$failures runner profile phase(s) failed in the CPU-bounded parallel batch."
  done
}

run_apple_audit_alongside_services() {
  local audit_output audit_pid audit_status
  if ! profile_enabled apple; then
    run_phase services 'Runner services and launchd validation' verify_launchd_services
    return
  fi
  prepare_parallel_phase apple-github-audit 'GitHub Apple configuration audit'
  audit_output="$(mktemp "${TMPDIR:-/tmp}/djconnect-apple-github-audit.XXXXXX")"
  parallel_phase_worker apple-github-audit audit_apple_github_configuration >"$audit_output" 2>&1 &
  audit_pid="$!"
  run_phase services 'Runner services and launchd validation' verify_launchd_services
  set +e
  wait "$audit_pid"
  audit_status=$?
  set -e
  complete_parallel_phase apple-github-audit 'GitHub Apple configuration audit' "$audit_status" "$audit_output" || die 'GitHub Apple configuration audit failed alongside service validation.'
}

repair_attempt() {
  local step="$1"
  shift
  local status
  log "Unattended repair attempt: $step."
  set +e
  (trap - EXIT; set -e; "$@")
  status=$?
  set -e
  if [[ "$status" == '42' && "$step" == 'least-privilege permissions audit' ]]; then
    PERMISSIONS_AUDIT_HAS_WARNINGS=1
    report_append "Unattended repair: $step" 'COMPLETED WITH WARNINGS' 'Least-privilege warnings were detected; review the audit evidence before treating the host as appropriately scoped.'
    record_repair_manual_requirement 'Least-privilege audit warnings require review and remediation before treating the host as appropriately scoped.'
    return 0
  fi
  if [[ "$status" == '0' ]]; then
    report_append "Unattended repair: $step" 'COMPLETED' 'Completed without interactive input.'
    return 0
  fi
  record_repair_manual_requirement "$step did not complete unattended (exit $status); inspect the transcript and complete the required local or account action."
  return 1
}

repair_required_casks() {
  local cask
  for cask in "${DESIRED_REQUIRED_CASKS[@]}"; do
    if brew list --cask "$cask" >/dev/null 2>&1; then
      continue
    fi
    run brew install --cask "$cask"
  done
}

run_unattended_repair_runners() {
  local -a profiles=() phase_ids=() steps=() output_files=() pids=()
  local profile phase_id step worker_limit index batch_end pid status batch_index failures
  if ! command -v gh >/dev/null 2>&1 || ! gh auth status --hostname github.com >/dev/null 2>&1; then
    record_repair_manual_requirement 'GitHub CLI authentication is required before missing runner registrations can be repaired. Run gh auth login interactively.'
    return 0
  fi
  if ! sudo -n true >/dev/null 2>&1; then
    record_repair_manual_requirement 'A cached non-interactive sudo authorization is required before missing runner services can be installed. Run sudo -v interactively, then rerun --repair.'
    return 0
  fi
  for profile in "${DESIRED_PROFILES[@]}"; do
    profile_enabled "$profile" || continue
    if [[ "$profile" == 'apple' ]] && ! command -v xcodebuild >/dev/null 2>&1; then
      record_repair_manual_requirement 'Full Xcode is required before the Apple runner can be repaired. Install/select the qualified Xcode version, then rerun --repair.'
      continue
    fi
    profile_values "$profile"
    [[ -f "$RUNNER_ROOT/$PROFILE_RUNNER_NAME/.runner" ]] && continue
    profiles+=("$profile")
    phase_ids+=("runner-$profile")
    steps+=("GitHub Actions runner profile: $profile")
  done
  (( ${#profiles[@]} > 0 )) || return 0
  worker_limit="$(parallel_worker_limit "${#profiles[@]}")"
  log "Unattended repair schedules ${#profiles[@]} missing runner profile(s) with $worker_limit CPU-bounded worker(s)."
  report_append 'Unattended repair: runner registrations' 'CPU-BOUNDED' "${#profiles[@]} missing runner profile(s); maximum $worker_limit concurrent job(s)."
  index=0
  while (( index < ${#profiles[@]} )); do
    batch_end=$(( index + worker_limit ))
    (( batch_end <= ${#profiles[@]} )) || batch_end="${#profiles[@]}"
    output_files=()
    pids=()
    while (( index < batch_end )); do
      phase_id="${phase_ids[$index]}"
      output_file="$(mktemp "${TMPDIR:-/tmp}/djconnect-repair-${phase_id}.XXXXXX")"
      parallel_phase_worker "$phase_id" install_runner_profile "${profiles[$index]}" >"$output_file" 2>&1 &
      pids+=("$!")
      output_files+=("$output_file")
      index=$((index + 1))
    done
    failures=0
    for batch_index in "${!pids[@]}"; do
      pid="${pids[$batch_index]}"
      set +e
      wait "$pid"
      status=$?
      set -e
      phase_id="${phase_ids[$((index - ${#pids[@]} + batch_index))]}"
      step="${steps[$((index - ${#pids[@]} + batch_index))]}"
      [[ -s "${output_files[$batch_index]}" ]] && cat "${output_files[$batch_index]}"
      rm -f "${output_files[$batch_index]}"
      if [[ "$status" == '0' ]]; then
        report_append "Unattended repair: $step" 'COMPLETED (parallel)' 'Runner registration completed without interactive input.'
        ok "$step (unattended repair)"
      else
        failures=$((failures + 1))
        record_repair_manual_requirement "$step could not be repaired unattended (exit $status); inspect its transcript output."
      fi
    done
    (( failures == 0 )) || warn "$failures runner registration repair(s) require manual follow-up."
  done
}

run_unattended_repair() {
  local status preflight_ready=1 github_ready=1
  printf '# DJConnect macOS Runner Host Unattended Repair\n\n'
  printf '%s\n\n' '## Baseline desired-state verification'
  set +e
  run_desired_state_verification
  REPAIR_INITIAL_VERIFY_STATUS=$?
  set -e
  report_append 'Desired-state verification before repair' "EXIT $REPAIR_INITIAL_VERIFY_STATUS" 'Baseline captured before one unattended repair pass.'
  emit_repair_progress 'Baseline desired-state verification captured.'

  begin_report_section host-qualification
  if ! repair_attempt 'mandatory host preflight' ensure_macos_arm64; then
    preflight_ready=0
  fi
  emit_repair_progress 'Mandatory host preflight attempted.'
  if (( preflight_ready == 1 )); then
    begin_report_section host-provisioning
    if ! command -v brew >/dev/null 2>&1; then
      record_repair_manual_requirement 'Homebrew is absent. Install it interactively, then rerun --repair; unattended repair will not run the interactive Homebrew installer.'
    else
      repair_attempt 'required Homebrew formulas and Codex CLI' ensure_tooling || true
      repair_attempt 'required Homebrew casks' repair_required_casks || true
    fi
  else
    record_repair_manual_requirement 'No host mutations were attempted because mandatory host preflight did not pass unattended.'
  fi
  emit_repair_progress 'Host tooling remediation attempted or recorded for manual follow-up.'

  begin_report_section repository-access
  if ! command -v gh >/dev/null 2>&1 || ! gh auth status --hostname github.com >/dev/null 2>&1; then
    github_ready=0
    record_repair_manual_requirement 'GitHub CLI login is required for repository and runner repair. Run gh auth login interactively, then rerun --repair.'
  fi
  if (( preflight_ready == 1 && github_ready == 1 )); then
    repair_attempt 'least-privilege permissions audit' audit_least_privilege || true
    repair_attempt 'managed repository synchronization' prepare_repositories || true
    begin_report_section runner-provisioning
    run_unattended_repair_runners
  fi
  emit_repair_progress 'Repository and runner remediation attempted or recorded for manual follow-up.'
  begin_report_section host-maintenance
  if [[ -f "$GITHUB_ROOT/djconnect-app/scripts/runner/install_macos_ci_tooling_maintenance.sh" ]]; then
    repair_attempt 'macOS CI-tooling maintenance LaunchAgent' install_maintenance || true
  else
    record_repair_manual_requirement 'The djconnect-app maintenance installer is unavailable locally; complete GitHub authentication/repository synchronization, then rerun --repair.'
  fi
  emit_repair_progress 'Maintenance remediation attempted or recorded for manual follow-up.'

  begin_report_section final-qualification
  printf '\n## Post-repair desired-state verification\n\n'
  set +e
  run_desired_state_verification
  REPAIR_FINAL_VERIFY_STATUS=$?
  set -e
  report_append 'Desired-state verification after repair' "EXIT $REPAIR_FINAL_VERIFY_STATUS" 'Post-repair verification captured after one unattended repair pass.'
  emit_repair_progress 'Post-repair desired-state verification captured.'
  if [[ "$REPAIR_FINAL_VERIFY_STATUS" == '0' ]]; then
    ok 'Unattended repair completed: desired state now matches.'
  else
    warn 'Unattended repair completed with remaining desired-state drift; review the post-repair delta and recorded manual requirements.'
  fi
  return "$REPAIR_FINAL_VERIFY_STATUS"
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
  if [[ "$exit_code" == '0' && "$RESUME_MODE" == '1' ]]; then
    clear_resume_checkpoint
  fi
  if [[ "$LOGGING_STARTED" == '1' ]]; then
    exec 1>&- 2>&-
    wait "$LOG_CAPTURE_PID" || true
    rm -rf "$LOG_CAPTURE_DIRECTORY"
  fi
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

least_privilege_warning() {
  local message="$1"
  LEAST_PRIVILEGE_WARNING_COUNT=$((LEAST_PRIVILEGE_WARNING_COUNT + 1))
  warn "LEAST-PRIVILEGE WARNING: $message"
  report_append 'Least-privilege audit' 'WARNING' "$message"
}

path_is_group_or_world_writable() {
  local path="$1"
  local mode
  mode="$(stat -f '%Lp' "$path" 2>/dev/null || printf '')"
  [[ "$mode" =~ ^[0-7]{3,4}$ ]] || return 1
  (( (8#$mode & 0022) != 0 ))
}

audit_path_least_privilege() {
  local path="$1"
  local purpose="$2"
  [[ -e "$path" ]] || return 0
  if path_is_group_or_world_writable "$path"; then
    least_privilege_warning "$purpose is group- or world-writable: $path. Restrict it to the owning maintainer before relying on this host."
  fi
}

audit_least_privilege() {
  local auth_status profile permission install_dir owner current_user
  current_user="$(id -un)"
  [[ "$(id -u)" != '0' ]] || die 'Do not run DJConnect recovery as root. Runner services must execute as the dedicated maintainer user.'
  audit_path_least_privilege "$REPOSITORY_ROOT" 'Canonical repository root'
  audit_path_least_privilege "$SCRIPT_DIRECTORY/bootstrap_macos_runner_host.sh" 'Recovery bootstrap script'
  audit_path_least_privilege "$DESIRED_STATE_FILE" 'Desired-state manifest'
  audit_path_least_privilege "$REDACTION_RULES" 'Transcript redaction rules'

  if sudo -n -l 2>/dev/null | grep -Eq 'NOPASSWD:.*\bALL\b|\bALL\b.*NOPASSWD'; then
    least_privilege_warning 'The current account has passwordless sudo for ALL commands. Recovery needs administrator access only while installing or validating runner services; use a narrowly scoped temporary authorization where feasible.'
  fi
  if sudo -n -l 2>/dev/null | grep -Eq '\(ALL(:ALL)?\)[[:space:]]+ALL'; then
    least_privilege_warning 'The current account has unrestricted sudo rules. This is broader than the runner-service setup requirement; review local sudoers policy after bootstrap.'
  fi

  if ! gh auth status --hostname github.com >/dev/null 2>&1; then
    least_privilege_warning 'GitHub CLI is not authenticated, so repository-specific least-privilege access could not be verified.'
    return 42
  fi
  auth_status="$(gh auth status --hostname github.com 2>&1 || true)"
  if grep -Eq '(^|[,[:space:]])(admin:org|delete_repo|admin:public_key|admin:gpg_key)([,[:space:]]|$)' <<<"$auth_status"; then
    least_privilege_warning 'The GitHub CLI token advertises an administrative scope beyond runner registration. Prefer a fine-grained token limited to the selected DJConnect repositories and required Actions administration.'
  fi
  if grep -Eq '(^|[,[:space:]])repo([,[:space:]]|$)' <<<"$auth_status"; then
    least_privilege_warning 'The GitHub CLI token uses the classic repo scope, which grants broad private-repository access. Prefer a fine-grained, repository-limited token where supported.'
  fi
  for profile in "${DESIRED_PROFILES[@]}"; do
    profile_enabled "$profile" || continue
    profile_values "$profile"
    permission="$(gh api "repos/$ORG/$PROFILE_REPOSITORY" --jq '.permissions.admin // false' 2>/dev/null || printf false)"
    if [[ "$permission" == 'true' ]]; then
      report_append 'Least-privilege audit' 'REQUIRED ACCESS VERIFIED' "GitHub administrator access is available for $ORG/$PROFILE_REPOSITORY, required for selected runner administration."
    else
      least_privilege_warning "GitHub administrator access for $ORG/$PROFILE_REPOSITORY could not be verified. Selected runner administration requires repository Actions administration; grant only that repository access."
    fi
    install_dir="$RUNNER_ROOT/$PROFILE_RUNNER_NAME"
    if [[ -e "$install_dir" ]]; then
      owner="$(stat -f '%Su' "$install_dir" 2>/dev/null || printf unknown)"
      [[ "$owner" == "$current_user" ]] || least_privilege_warning "Runner directory $install_dir is owned by $owner, not dedicated maintainer user $current_user."
      audit_path_least_privilege "$install_dir" "Runner directory for $PROFILE_RUNNER_NAME"
    fi
  done
  if (( LEAST_PRIVILEGE_WARNING_COUNT == 0 )); then
    report_append 'Least-privilege audit' 'PASSED' 'Required local and selected GitHub runner permissions were verified without detected broad-write exposure.'
    ok 'Least-privilege audit: required rights verified; no broad local permission exposure detected.'
  else
    warn "Least-privilege audit completed with $LEAST_PRIVILEGE_WARNING_COUNT warning(s)."
    return 42
  fi
}

credential_expiry_warning() {
  local message="$1"
  warn "CREDENTIAL EXPIRY WARNING: $message"
  report_append 'Credential expiry audit' 'ATTENTION REQUIRED' "$message"
}

audit_certificate_expiry() {
  local common_name="$1"
  local temporary_directory certificate_file expiry subject found=0 warning_seconds
  command -v openssl >/dev/null 2>&1 || {
    report_append 'Credential expiry audit' 'UNVERIFIED' "openssl is unavailable; local $common_name certificate expiry could not be checked."
    return 0
  }
  temporary_directory="$(mktemp -d "${TMPDIR:-/tmp}/djconnect-certificate-expiry.XXXXXX")"
  { security find-certificate -a -p -c "$common_name" 2>/dev/null || true; } | awk -v output="$temporary_directory" '
    /BEGIN CERTIFICATE/ { count++; file = output "/certificate-" count ".pem" }
    count > 0 { print > file }
  '
  for certificate_file in "$temporary_directory"/*.pem; do
    [[ -f "$certificate_file" ]] || continue
    found=1
    subject="$(openssl x509 -in "$certificate_file" -noout -subject -nameopt RFC2253 2>/dev/null | sed 's/^subject=//')"
    expiry="$(openssl x509 -in "$certificate_file" -noout -enddate 2>/dev/null | sed 's/^notAfter=//')"
    if ! openssl x509 -in "$certificate_file" -checkend 0 -noout >/dev/null 2>&1; then
      credential_expiry_warning "$common_name certificate is expired (${subject:-identity unavailable}; expired $expiry)."
      CREDENTIAL_EXPIRY_HAS_WARNINGS=1
    elif ! openssl x509 -in "$certificate_file" -checkend "$(( EXPIRY_WARNING_DAYS * 86400 ))" -noout >/dev/null 2>&1; then
      credential_expiry_warning "$common_name certificate expires within $EXPIRY_WARNING_DAYS days (${subject:-identity unavailable}; expires $expiry)."
      CREDENTIAL_EXPIRY_HAS_WARNINGS=1
    else
      report_append 'Credential expiry audit' 'VALID' "$common_name certificate is valid beyond $EXPIRY_WARNING_DAYS days (${subject:-identity unavailable}; expires $expiry)."
    fi
  done
  (( found == 1 )) || report_append 'Credential expiry audit' 'UNVERIFIED' "No local $common_name certificate was found in the current keychain."
  rm -rf "$temporary_directory"
}

audit_provisioning_profile_expiry() {
  local profiles_directory="$HOME/Library/MobileDevice/Provisioning Profiles"
  local profile raw_expiry expiry_epoch now_epoch found=0
  [[ -d "$profiles_directory" ]] || {
    report_append 'Credential expiry audit' 'UNVERIFIED' 'No local provisioning-profile directory is present.'
    return 0
  }
  now_epoch="$(date +%s)"
  while IFS= read -r -d '' profile; do
    found=1
    raw_expiry="$(security cms -D -i "$profile" 2>/dev/null | plutil -extract ExpirationDate raw -o - - 2>/dev/null || true)"
    expiry_epoch="$(date -j -f '%Y-%m-%dT%H:%M:%SZ' "$raw_expiry" +%s 2>/dev/null || date -j -f '%Y-%m-%d %H:%M:%S %z' "$raw_expiry" +%s 2>/dev/null || true)"
    if [[ ! "$expiry_epoch" =~ ^[0-9]+$ ]]; then
      report_append 'Credential expiry audit' 'UNVERIFIED' "Provisioning-profile expiry could not be parsed for $(basename "$profile")."
    elif (( expiry_epoch <= now_epoch )); then
      credential_expiry_warning "Provisioning profile $(basename "$profile") is expired ($raw_expiry)."
      CREDENTIAL_EXPIRY_HAS_WARNINGS=1
    elif (( expiry_epoch - now_epoch <= EXPIRY_WARNING_DAYS * 86400 )); then
      credential_expiry_warning "Provisioning profile $(basename "$profile") expires within $EXPIRY_WARNING_DAYS days ($raw_expiry)."
      CREDENTIAL_EXPIRY_HAS_WARNINGS=1
    else
      report_append 'Credential expiry audit' 'VALID' "Provisioning profile $(basename "$profile") is valid beyond $EXPIRY_WARNING_DAYS days (expires $raw_expiry)."
    fi
  done < <(find "$profiles_directory" -type f -name '*.mobileprovision' -print0)
  (( found == 1 )) || report_append 'Credential expiry audit' 'UNVERIFIED' 'No local provisioning profiles were found.'
}

audit_credential_expiry() {
  CREDENTIAL_EXPIRY_HAS_WARNINGS=0
  report_append 'Credential expiry audit' 'TOKEN EXPIRY UNVERIFIED' 'GitHub, Docker and ngrok clients do not safely disclose local token expiry through this bootstrap; no token values were read.'
  audit_certificate_expiry 'Apple Development'
  audit_certificate_expiry 'Developer ID Application'
  audit_provisioning_profile_expiry
  if [[ "$CREDENTIAL_EXPIRY_HAS_WARNINGS" == '1' ]]; then
    return 43
  fi
  report_append 'Credential expiry audit' 'PASSED' "No discovered local Apple certificate or provisioning profile expires within $EXPIRY_WARNING_DAYS days."
}

confirm_recommended_memory_override() {
  local mem_gb="$1"
  (( mem_gb >= DESIRED_RECOMMENDED_RAM_GB )) && return 0
  warn "${mem_gb}GB RAM meets the hard ${DESIRED_MINIMUM_RAM_GB}GB minimum, but is below the ${DESIRED_RECOMMENDED_RAM_GB}GB recommendation for Docker, Xcode and parallel runners."
  if [[ "$DRY_RUN" == '1' ]]; then
    printf 'DRY: require explicit operator confirmation before continuing below the recommended %sGB RAM\n' "$DESIRED_RECOMMENDED_RAM_GB"
    report_append 'Memory capacity override' 'CONFIRMATION REQUIRED' "${mem_gb}GB is below the recommended ${DESIRED_RECOMMENDED_RAM_GB}GB; dry-run did not request confirmation."
    return 0
  fi
  if [[ "$MEMORY_OVERRIDE_CONFIRMED" == '1' ]]; then
    report_append 'Memory capacity override' 'EXPLICITLY APPROVED' "Operator supplied --confirm-memory-override for ${mem_gb}GB RAM."
    return 0
  fi
  if [[ "$REPAIR_MODE" == '1' ]]; then
    die "MANUAL INPUT REQUIRED: ${mem_gb}GB RAM is below the recommended ${DESIRED_RECOMMENDED_RAM_GB}GB; rerun interactively to confirm or supply --confirm-memory-override."
  fi
  if [[ ! -r /dev/tty || ! -w /dev/tty ]]; then
    die "${mem_gb}GB RAM is below the recommended ${DESIRED_RECOMMENDED_RAM_GB}GB. Run interactively to confirm, or explicitly supply --confirm-memory-override."
  fi
  local response=''
  printf 'Continue recovery with %sGB RAM (below recommended %sGB)? [y/N]: ' "$mem_gb" "$DESIRED_RECOMMENDED_RAM_GB" >/dev/tty
  read -r response </dev/tty
  case "$response" in
    y|Y|yes|YES)
      report_append 'Memory capacity override' 'INTERACTIVELY APPROVED' "Operator approved recovery with ${mem_gb}GB RAM."
      ;;
    *)
      die "Recovery stopped: ${mem_gb}GB RAM is below the recommended ${DESIRED_RECOMMENDED_RAM_GB}GB and was not approved."
      ;;
  esac
}

ensure_macos_arm64() {
  local macos_version macos_major cpu_brand hardware_profile mem_bytes mem_gb cpu_count disk_probe_path disk_kb disk_gb
  [[ "$DESIRED_HOST_PLATFORM" == 'macos' ]] || die "Desired state requires unsupported host platform: $DESIRED_HOST_PLATFORM"
  [[ "$(id -u)" != '0' ]] || die 'Do not run DJConnect recovery as root. Use the dedicated maintainer account so runner services do not inherit root privileges.'
  [[ "$(uname -s)" == 'Darwin' ]] || die 'This recovery bootstrap runs only on macOS.'
  [[ "$(uname -m)" == "$DESIRED_HOST_ARCHITECTURE" ]] || die "DJConnect macOS runners require a $DESIRED_HOST_ARCHITECTURE host."
  cpu_brand="$(sysctl -n machdep.cpu.brand_string 2>/dev/null || true)"
  hardware_profile=''
  if [[ -z "$cpu_brand" ]]; then
    hardware_profile="$(system_profiler SPHardwareDataType 2>/dev/null || true)"
    cpu_brand="$(awk -F': ' '/Chip:/{print $2; exit}' <<<"$hardware_profile")"
  fi
  [[ "$DESIRED_HOST_APPLE_SILICON" == 'required' ]] || die "Desired state requires unsupported Apple-Silicon policy: $DESIRED_HOST_APPLE_SILICON"
  [[ "$cpu_brand" == Apple* ]] || die 'DJConnect development requires a physical Apple-Silicon Mac, not another arm64 runtime.'

  macos_version="$(sw_vers -productVersion 2>/dev/null || true)"
  macos_major="${macos_version%%.*}"
  [[ "$macos_major" =~ ^[0-9]+$ ]] && (( macos_major >= DESIRED_MINIMUM_MACOS_MAJOR )) || die "DJConnect development requires macOS $DESIRED_MINIMUM_MACOS_MAJOR or newer; detected ${macos_version:-unknown}."

  mem_bytes="$(sysctl -n hw.memsize 2>/dev/null || echo 0)"
  if [[ "$mem_bytes" =~ ^[0-9]+$ && "$mem_bytes" != '0' ]]; then
    mem_gb=$((mem_bytes / 1024 / 1024 / 1024))
  else
    [[ -n "$hardware_profile" ]] || hardware_profile="$(system_profiler SPHardwareDataType 2>/dev/null || true)"
    mem_gb="$(awk -F': ' '/Memory:/{print $2; exit}' <<<"$hardware_profile" | awk '{print $1}')"
  fi
  [[ "$mem_gb" =~ ^[0-9]+$ ]] || die 'Could not determine installed memory.'
  (( mem_gb >= DESIRED_MINIMUM_RAM_GB )) || die "DJConnect development requires at least ${DESIRED_MINIMUM_RAM_GB}GB RAM; detected ${mem_gb}GB."

  cpu_count="$(sysctl -n hw.ncpu 2>/dev/null || echo 0)"
  if [[ ! "$cpu_count" =~ ^[0-9]+$ || "$cpu_count" == '0' ]]; then
    [[ -n "$hardware_profile" ]] || hardware_profile="$(system_profiler SPHardwareDataType 2>/dev/null || true)"
    cpu_count="$(awk -F': ' '/Total Number of Cores:/{print $2; exit}' <<<"$hardware_profile" | awk '{print $1}')"
  fi
  [[ "$cpu_count" =~ ^[0-9]+$ ]] || die 'Could not determine available CPU cores.'
  (( cpu_count >= DESIRED_MINIMUM_CPU_CORES )) || die "DJConnect development requires at least $DESIRED_MINIMUM_CPU_CORES CPU cores; detected $cpu_count."

  disk_probe_path="$GITHUB_ROOT"
  while [[ ! -e "$disk_probe_path" && "$disk_probe_path" != '/' ]]; do
    disk_probe_path="$(dirname "$disk_probe_path")"
  done
  disk_kb="$(df -Pk "$disk_probe_path" | awk 'NR == 2 {print $4}')"
  [[ "$disk_kb" =~ ^[0-9]+$ ]] || die "Could not determine free disk space for $GITHUB_ROOT."
  disk_gb=$((disk_kb / 1024 / 1024))
  (( disk_gb >= DESIRED_MINIMUM_FREE_DISK_GB )) || die "DJConnect development requires at least ${DESIRED_MINIMUM_FREE_DISK_GB}GB free at $GITHUB_ROOT; detected ${disk_gb}GB."

  confirm_recommended_memory_override "$mem_gb"
  log "Qualified development host: macOS $macos_version, $cpu_brand, ${mem_gb}GB RAM, $cpu_count cores, ${disk_gb}GB free at $disk_probe_path."
  report_append 'Development host qualification' 'QUALIFIED' "macOS $macos_version; $cpu_brand; ${mem_gb}GB RAM; $cpu_count cores; ${disk_gb}GB free at $disk_probe_path."
  if (( disk_gb < DESIRED_RECOMMENDED_FREE_DISK_GB )); then
    warn "${disk_gb}GB free meets the minimum; ${DESIRED_RECOMMENDED_FREE_DISK_GB}GB+ is recommended for VM, Xcode and Docker workloads."
  fi
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
  run brew install "${DESIRED_TOOL_FORMULAS[@]}"
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
  local profile
  log 'Preparing repositories required by the macOS runner profiles.'
  clone_or_update djconnect
  for profile in "${DESIRED_PROFILES[@]}"; do
    profile_values "$profile"
    [[ "$PROFILE_REPOSITORY" == 'djconnect' ]] || clone_or_update "$PROFILE_REPOSITORY"
  done
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

profile_declared() {
  local profile="$1"
  local declared_profile
  for declared_profile in "${DESIRED_PROFILES[@]}"; do
    if [[ "$declared_profile" == "$profile" ]]; then
      return 0
    fi
  done
  return 1
}

validate_profile_selection() {
  local profile
  [[ "$PROFILE_SELECTION" == 'all' ]] && return 0
  IFS=',' read -r -a selected_profiles <<<"$PROFILE_SELECTION"
  for profile in "${selected_profiles[@]}"; do
    profile_declared "$profile" || die "Selected runner profile is not declared by desired state: $profile"
  done
}

profile_values() {
  local profile="$1"
  profile_declared "$profile" || die "Runner profile $profile is not declared by desired state."
  PROFILE_REPOSITORY="$(require_desired_state_value "profile.$profile.repository")"
  PROFILE_RUNNER_NAME="$(require_desired_state_value "profile.$profile.runner_name")"
  PROFILE_LABELS="$(require_desired_state_value "profile.$profile.labels")"
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
    if phase_is_forced "$CURRENT_PHASE_ID"; then
      log "$PROFILE_RUNNER_NAME already has the desired registration; reconciling its installed service without re-registering it."
      [[ -x "$install_dir/svc.sh" ]] || die "Configured runner $PROFILE_RUNNER_NAME is missing svc.sh."
      run_in_dir "$install_dir" sudo ./svc.sh status
    else
      warn "$PROFILE_RUNNER_NAME is already configured in $install_dir; preserving the existing registration. Use --force-phases $CURRENT_PHASE_ID to reconcile it."
    fi
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
  for formula in "${DESIRED_TOOL_FORMULAS[@]}"; do
    run brew install "$formula"
    run brew upgrade "$formula"
  done
  for cask in "${DESIRED_REFRESH_CASKS[@]}"; do
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
    write_resume_checkpoint reboot-check
    warn 'macOS reports a pending restart/reboot requirement. Restart the MacBook, then run the same recovery command with --resume.'
    return 75
  fi
  log 'macOS Software Update reports no pending restart/reboot requirement.'
}

verify_runner_online() {
  local profile repository runner_name deadline state
  for profile in "${DESIRED_PROFILES[@]}"; do
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
  for profile in "${DESIRED_PROFILES[@]}"; do
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
    --desired-state) DESIRED_STATE_FILE="${2:?--desired-state requires a value}"; shift 2 ;;
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
    --skip-phases) SKIP_PHASES="${2:?--skip-phases requires a value}"; shift 2 ;;
    --force-phases) FORCE_PHASES="${2:?--force-phases requires a value}"; shift 2 ;;
    --verify) VERIFY_MODE=1; shift ;;
    --repair) REPAIR_MODE=1; shift ;;
    --resume) RESUME_MODE=1; shift ;;
    --resume-state) RESUME_STATE_FILE="${2:?--resume-state requires a value}"; shift 2 ;;
    --version) print_version; exit 0 ;;
    --log-level) LOG_LEVEL="${2:?--log-level requires a value}"; validate_log_level; shift 2 ;;
    --list-phases) LIST_PHASES=1; shift ;;
    --parallel-jobs) PARALLEL_JOBS="${2:?--parallel-jobs requires a value}"; validate_parallel_jobs; shift 2 ;;
    --confirm-memory-override) MEMORY_OVERRIDE_CONFIRMED=1; shift ;;
    --expiry-warning-days) EXPIRY_WARNING_DAYS="${2:?--expiry-warning-days requires a value}"; validate_expiry_warning_days; shift 2 ;;
    --no-color) NO_COLOR=1; shift ;;
    --help|-h|help) usage; exit 0 ;;
    *) die "Unknown option: $1" ;;
  esac
done

validate_log_level
validate_parallel_jobs
validate_expiry_warning_days
if [[ "$LIST_PHASES" == '1' ]]; then
  print_phase_catalog
  exit 0
fi
require_external_output_path 'Recovery resume checkpoint' "$RESUME_STATE_FILE"

if [[ "$VERIFY_MODE" == '1' && "$DRY_RUN" == '1' ]]; then
  die '--verify and --dry-run cannot be combined.'
fi
if [[ "$VERIFY_MODE" == '1' && "$RESUME_MODE" == '1' ]]; then
  die '--verify and --resume cannot be combined.'
fi
if [[ "$REPAIR_MODE" == '1' && "$VERIFY_MODE" == '1' ]]; then
  die '--repair and --verify cannot be combined; --repair performs baseline and post-repair verification itself.'
fi
if [[ "$REPAIR_MODE" == '1' && "$RESUME_MODE" == '1' ]]; then
  die '--repair and --resume cannot be combined.'
fi
if [[ "$VERIFY_MODE" == '1' ]]; then
  [[ -n "$LOG_FILE" ]] || LOG_FILE='none'
  [[ -n "$REPORT_FILE" ]] || REPORT_FILE='none'
fi

if [[ -t 1 ]]; then
  ORIGINAL_STDOUT_IS_TTY=1
fi
init_style
start_logging
load_desired_state
if [[ "$RESUME_MODE" == '1' ]]; then
  load_resume_checkpoint
fi
if [[ "$VERIFY_MODE" == '1' ]]; then
  run_desired_state_verification
  exit $?
fi
start_report
trap cleanup EXIT
if [[ "$REPAIR_MODE" == '1' ]]; then
  validate_profile_selection
  run_unattended_repair
  exit $?
fi
validate_profile_selection
validate_skip_phases
validate_force_phases
run_phase macos-preflight 'macOS host preflight' ensure_macos_arm64
run_phase sudo 'Administrator sudo gate' warm_sudo
run_phase tooling 'Host tooling setup' ensure_tooling
run_phase xcode 'Xcode qualification' ensure_xcode
run_phase parallels 'Parallels Desktop availability' ensure_parallels
run_phase github-auth 'GitHub CLI authentication' ensure_github_auth
run_phase permissions-audit 'Least-privilege permissions audit' audit_least_privilege
run_phase repositories 'Repository preparation' prepare_repositories
run_phase developer-workstation 'Developer workstation recovery' bootstrap_developer_workstation
run_phase docker-auth 'Docker Hub authentication' ensure_docker_hub_auth
run_parallel_runner_profiles

run_phase maintenance 'Daily macOS tooling maintenance' install_maintenance
run_phase tooling-refresh 'Tooling currency refresh' refresh_host_tooling
run_phase reboot-check 'Reboot requirement check' check_reboot_required
run_phase apple-signing 'Apple signing recovery' configure_signing_keychain
run_phase apple-readiness 'Apple internal-release readiness' configure_apple_internal_release
run_phase credential-expiry-audit 'Credential and certificate expiry audit' audit_credential_expiry
run_apple_audit_alongside_services
run_phase initial-verification 'Initial post-recovery verification' run_initial_verification
report_signing_recovery
