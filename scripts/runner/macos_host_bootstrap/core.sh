# Version: 1.3.1
# CLI help, desired-state verification and console/report primitives.
usage() {
  cat <<'EOF'
Usage: bootstrap_djconnect_macos_host.sh [options]

Recover a fresh Apple-Silicon MacBook as a DJConnect developer and GitHub
development host. The script installs supported host tooling, clones the
required repositories, authenticates GitHub CLI interactively if necessary,
registers the selected runners as launchd services, and installs the daily
macOS CI-tooling maintenance LaunchAgent.

Options:
  --profiles LIST       Comma-separated: apple,private-network,esp32,pi.
                        Default: all.
  --desired-state FILE  YAML desired-state manifest to reconcile. Default:
                        scripts/runner/macos_development_host_desired_state.yml
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
  --install-parallels   Compatibility option. Parallels Desktop is required by
                        the desired state and is always reconciled; this option
                        does not activate a license or create a Windows VM.
  --skip-developer-workstation
                        Do not run the complete existing macOS developer
                        onboarding. By default the recovery restores the full
                        local DJConnect development workstation as well as the
                        development host.
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
  printf 'DJConnect macOS Development Host Bootstrap %s\n' "$SCRIPT_VERSION"
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

semantic_version_at_least() {
  local actual="$1" minimum="$2" index
  local -a actual_parts minimum_parts
  IFS='.' read -r -a actual_parts <<<"$actual"
  IFS='.' read -r -a minimum_parts <<<"$minimum"
  for index in 0 1 2; do
    (( 10#${actual_parts[$index]:-0} > 10#${minimum_parts[$index]:-0} )) && return 0
    (( 10#${actual_parts[$index]:-0} < 10#${minimum_parts[$index]:-0} )) && return 1
  done
  return 0
}

load_desired_state() {
  local profile
  [[ -f "$DESIRED_STATE_FILE" ]] || die "Desired-state manifest is unavailable: $DESIRED_STATE_FILE"
  DESIRED_STATE_SCHEMA_VERSION="$(require_desired_state_value schema_version)"
  [[ "$DESIRED_STATE_SCHEMA_VERSION" == '1' ]] || die "Unsupported desired-state schema version: $DESIRED_STATE_SCHEMA_VERSION"
  DESIRED_STATE_VERSION="$(require_desired_state_value version)"
  DESIRED_MINIMUM_TOOL_VERSION="$(require_desired_state_value minimum_tool_version)"
  [[ "$DESIRED_STATE_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || die "Invalid desired-state manifest version: $DESIRED_STATE_VERSION"
  [[ "$DESIRED_MINIMUM_TOOL_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || die "Invalid desired-state minimum_tool_version: $DESIRED_MINIMUM_TOOL_VERSION"
  if semantic_version_at_least "$SCRIPT_VERSION" "$DESIRED_MINIMUM_TOOL_VERSION"; then
    MANIFEST_TOOL_COMPATIBILITY_VERDICT='MANIFEST_TOOL_COMPATIBLE'
  else
    MANIFEST_TOOL_COMPATIBILITY_VERDICT='MANIFEST_TOOL_TOO_OLD'
    [[ "$VERIFY_MODE" == '1' ]] || die "Desired-state manifest $DESIRED_STATE_VERSION requires bootstrap >=$DESIRED_MINIMUM_TOOL_VERSION; installed bootstrap is $SCRIPT_VERSION."
  fi
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
  local optional_casks
  optional_casks="$(desired_state_value tooling.optional_casks)"
  if [[ -n "$optional_casks" ]]; then IFS=',' read -r -a DESIRED_OPTIONAL_CASKS <<<"$optional_casks"; else DESIRED_OPTIONAL_CASKS=(); fi
  IFS=',' read -r -a DESIRED_REFRESH_CASKS <<<"$(require_desired_state_value tooling.refresh_casks)"
  DESIRED_HA_SERVICE="$(require_desired_state_value lab.home_assistant.service)"
  DESIRED_HA_CONTAINER_NAME="$(require_desired_state_value lab.home_assistant.container_name)"
  DESIRED_HA_URL="$(require_desired_state_value lab.home_assistant.url)"
  DESIRED_NGROK_CONFIG_RELATIVE_PATH="$(require_desired_state_value network.ngrok.config_relative_path)"
  DESIRED_NGROK_CONFIG_VERSION="$(require_desired_state_value network.ngrok.config_version)"
  DESIRED_NGROK_CONFIG_PERMISSIONS="$(require_desired_state_value network.ngrok.config_permissions)"
  DESIRED_NGROK_AUTHTOKEN="$(require_desired_state_value network.ngrok.authtoken)"
  DESIRED_NGROK_LAUNCH_AGENT_LABEL="$(require_desired_state_value network.ngrok.launch_agent_label)"
  DESIRED_NGROK_TUNNEL_DOMAIN="$(require_desired_state_value network.ngrok.tunnel.domain)"
  DESIRED_NGROK_TUNNEL_TARGET="$(require_desired_state_value network.ngrok.tunnel.target)"
  DESIRED_NGROK_INSPECTOR_URL="$(require_desired_state_value network.ngrok.inspector_url)"
  [[ "$DESIRED_HA_SERVICE" == 'homeassistant' ]] || die "Unsupported Home Assistant lab service: $DESIRED_HA_SERVICE"
  [[ "$DESIRED_HA_CONTAINER_NAME" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]*$ ]] || die "Invalid Home Assistant lab container name: $DESIRED_HA_CONTAINER_NAME"
  [[ "$DESIRED_HA_URL" =~ ^http://localhost:[0-9]+$ ]] || die "Invalid Home Assistant lab URL: $DESIRED_HA_URL"
  [[ "$DESIRED_NGROK_CONFIG_RELATIVE_PATH" =~ ^[A-Za-z0-9_./[:space:]-]+$ && "$DESIRED_NGROK_CONFIG_RELATIVE_PATH" != /* && "$DESIRED_NGROK_CONFIG_RELATIVE_PATH" != *'..'* ]] || die 'Invalid ngrok config relative path.'
  [[ "$DESIRED_NGROK_CONFIG_VERSION" == '3' ]] || die "Unsupported ngrok config version: $DESIRED_NGROK_CONFIG_VERSION"
  [[ "$DESIRED_NGROK_CONFIG_PERMISSIONS" == '600' ]] || die "ngrok config permissions must be 600, got: $DESIRED_NGROK_CONFIG_PERMISSIONS"
  [[ "$DESIRED_NGROK_AUTHTOKEN" == 'required_local_secret' ]] || die 'ngrok authtoken policy must be required_local_secret.'
  [[ "$DESIRED_NGROK_LAUNCH_AGENT_LABEL" =~ ^[A-Za-z0-9_.-]+$ ]] || die 'Invalid ngrok LaunchAgent label.'
  [[ "$DESIRED_NGROK_TUNNEL_DOMAIN" =~ ^[A-Za-z0-9.-]+\.ngrok-free\.dev$ ]] || die 'Invalid ngrok static domain.'
  [[ "$DESIRED_NGROK_TUNNEL_TARGET" =~ ^http://127\.0\.0\.1:[0-9]+$ ]] || die 'ngrok tunnel target must bind to loopback HTTP.'
  [[ "$DESIRED_NGROK_INSPECTOR_URL" =~ ^http://127\.0\.0\.1:[0-9]+$ ]] || die 'ngrok inspector must bind to loopback HTTP.'
  IFS=',' read -r -a DESIRED_PROFILES <<<"$(require_desired_state_value runner.profiles)"
  for profile in "${DESIRED_PROFILES[@]}"; do
    case "$profile" in
      apple|private-network|esp32|pi|windows) ;;
      *) die "Unsupported desired-state runner profile: $profile" ;;
    esac
    require_desired_state_value "profile.$profile.repository" >/dev/null
    require_desired_state_value "profile.$profile.runner_name" >/dev/null
    require_desired_state_value "profile.$profile.labels" >/dev/null
    require_desired_state_value "profile.$profile.provisioning" >/dev/null
  done
  [[ "$VERIFY_MODE" == '1' ]] || log "Loaded desired-state manifest $DESIRED_STATE_FILE (version $DESIRED_STATE_VERSION, schema $DESIRED_STATE_SCHEMA_VERSION); bootstrap $SCRIPT_VERSION requires >=$DESIRED_MINIMUM_TOOL_VERSION: $MANIFEST_TOOL_COMPATIBILITY_VERDICT."
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
  local hardware_profile macos_version macos_major cpu_brand mem_bytes mem_gb cpu_count disk_probe_path disk_kb disk_gb formula cask profile install_dir uid_value ha_running ngrok_config ngrok_permissions ngrok_config_version ngrok_authtoken_status ngrok_authtoken_state ngrok_tunnel
  printf '# DJConnect macOS Development Host Desired-State Delta\n\n'
  printf '%s\n\n' "Manifest: \`$DESIRED_STATE_FILE\` (version $DESIRED_STATE_VERSION, schema $DESIRED_STATE_SCHEMA_VERSION; bootstrap $SCRIPT_VERSION, minimum tool $DESIRED_MINIMUM_TOOL_VERSION, $MANIFEST_TOOL_COMPATIBILITY_VERDICT)"
  printf '%s\n' '| Component | Desired | Actual | Delta |'
  printf '%s\n' '| --- | --- | --- | --- |'

  macos_version="$(sw_vers -productVersion 2>/dev/null || printf unknown)"
  macos_major="${macos_version%%.*}"
  verify_delta_row 'host.platform' "$DESIRED_HOST_PLATFORM/$DESIRED_HOST_ARCHITECTURE" "$(uname -s)/$(uname -m)" "$([[ "$(uname -s)" == Darwin && "$(uname -m)" == "$DESIRED_HOST_ARCHITECTURE" ]] && printf MATCH || printf DRIFT)"
  verify_delta_row 'host.macos_minimum_major' ">=$DESIRED_MINIMUM_MACOS_MAJOR" "$macos_version" "$([[ "$macos_major" =~ ^[0-9]+$ ]] && (( macos_major >= DESIRED_MINIMUM_MACOS_MAJOR )) && printf MATCH || printf DRIFT)"
  verify_delta_row 'manifest.tool_compatibility' ">=$DESIRED_MINIMUM_TOOL_VERSION" "$SCRIPT_VERSION" "$([[ "$MANIFEST_TOOL_COMPATIBILITY_VERDICT" == MANIFEST_TOOL_COMPATIBLE ]] && printf MATCH || printf DRIFT)"
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
  if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
    ha_running="$(docker inspect --format '{{.State.Running}}' "$DESIRED_HA_CONTAINER_NAME" 2>/dev/null || true)"
    verify_delta_row 'lab.home_assistant.container' "$DESIRED_HA_CONTAINER_NAME running" "${ha_running:-absent}" "$([[ "$ha_running" == 'true' ]] && printf MATCH || printf DRIFT)"
  else
    verify_delta_row 'lab.home_assistant.container' "$DESIRED_HA_CONTAINER_NAME running" 'Docker unavailable' UNVERIFIED
  fi
  if curl -fsS --max-time 5 "$DESIRED_HA_URL" >/dev/null 2>&1; then
    verify_delta_row 'lab.home_assistant.url' "$DESIRED_HA_URL reachable" reachable MATCH
  else
    verify_delta_row 'lab.home_assistant.url' "$DESIRED_HA_URL reachable" unavailable DRIFT
  fi
  ngrok_config="$HOME/$DESIRED_NGROK_CONFIG_RELATIVE_PATH"
  if [[ -f "$ngrok_config" ]]; then
    ngrok_permissions="$(stat -f '%Lp' "$ngrok_config" 2>/dev/null || printf unknown)"
    verify_delta_row 'network.ngrok.config_permissions' "$DESIRED_NGROK_CONFIG_PERMISSIONS" "$ngrok_permissions" "$([[ "$ngrok_permissions" == "$DESIRED_NGROK_CONFIG_PERMISSIONS" ]] && printf MATCH || printf DRIFT)"
    ngrok_config_version="$(awk -F: '/^[[:space:]]*version:[[:space:]]*/ {gsub(/[[:space:]\"]/, "", $2); print $2; exit}' "$ngrok_config")"
    verify_delta_row 'network.ngrok.config_version' "$DESIRED_NGROK_CONFIG_VERSION" "${ngrok_config_version:-missing}" "$([[ "$ngrok_config_version" == "$DESIRED_NGROK_CONFIG_VERSION" ]] && printf MATCH || printf DRIFT)"
    if awk -F: '/^[[:space:]]*authtoken:[[:space:]]*[^[:space:]]/ {found=1} END {exit !found}' "$ngrok_config"; then ngrok_authtoken_status='configured (value redacted)'; ngrok_authtoken_state=MATCH; else ngrok_authtoken_status='missing'; ngrok_authtoken_state=DRIFT; fi
    verify_delta_row 'network.ngrok.authtoken' "$DESIRED_NGROK_AUTHTOKEN" "$ngrok_authtoken_status" "$ngrok_authtoken_state"
  else
    verify_delta_row 'network.ngrok.config_permissions' "$DESIRED_NGROK_CONFIG_PERMISSIONS" absent DRIFT
    verify_delta_row 'network.ngrok.config_version' "$DESIRED_NGROK_CONFIG_VERSION" absent DRIFT
    verify_delta_row 'network.ngrok.authtoken' "$DESIRED_NGROK_AUTHTOKEN" absent DRIFT
  fi
  if launchctl print "gui/$(id -u)/$DESIRED_NGROK_LAUNCH_AGENT_LABEL" >/dev/null 2>&1; then verify_delta_row 'network.ngrok.launch_agent' "$DESIRED_NGROK_LAUNCH_AGENT_LABEL loaded" loaded MATCH; else verify_delta_row 'network.ngrok.launch_agent' "$DESIRED_NGROK_LAUNCH_AGENT_LABEL loaded" absent DRIFT; fi
  ngrok_tunnel="$(curl -fsS --max-time 5 "$DESIRED_NGROK_INSPECTOR_URL/api/tunnels" 2>/dev/null | jq -r --arg url "https://$DESIRED_NGROK_TUNNEL_DOMAIN" --arg target "$DESIRED_NGROK_TUNNEL_TARGET" '.tunnels[]? | select(.public_url == $url and .config.addr == $target) | .public_url' 2>/dev/null | head -n 1 || true)"
  if [[ "$ngrok_tunnel" == "https://$DESIRED_NGROK_TUNNEL_DOMAIN" ]]; then verify_delta_row 'network.ngrok.tunnel' "https://$DESIRED_NGROK_TUNNEL_DOMAIN -> $DESIRED_NGROK_TUNNEL_TARGET" "$ngrok_tunnel" MATCH; else verify_delta_row 'network.ngrok.tunnel' "https://$DESIRED_NGROK_TUNNEL_DOMAIN -> $DESIRED_NGROK_TUNNEL_TARGET" unavailable DRIFT; fi
  for profile in "${DESIRED_PROFILES[@]}"; do
    profile_enabled "$profile" || continue
    profile_values "$profile"
    if [[ "$PROFILE_PROVISIONING" == 'external_windows_arm64' ]]; then
      if external_runner_profile_registered "$profile"; then verify_delta_row "runner.$profile" "$PROFILE_REPOSITORY ($PROFILE_LABELS)" registered MATCH; else verify_delta_row "runner.$profile" "$PROFILE_REPOSITORY ($PROFILE_LABELS)" absent DRIFT; fi
    else
      install_dir="$RUNNER_ROOT/$PROFILE_RUNNER_NAME"
      if [[ -f "$install_dir/.runner" ]]; then verify_delta_row "runner.$profile" "$PROFILE_REPOSITORY ($PROFILE_LABELS)" registered MATCH; else verify_delta_row "runner.$profile" "$PROFILE_REPOSITORY ($PROFILE_LABELS)" absent DRIFT; fi
    fi
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
