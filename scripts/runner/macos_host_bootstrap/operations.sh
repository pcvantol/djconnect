# Version: 1.3.5
# macOS host provisioning, developer-workstation and service operations.
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
  local macos_version macos_major cpu_brand hardware_profile mem_bytes mem_gb cpu_count disk_probe_path disk_kb disk_gb
  [[ "$DESIRED_HOST_PLATFORM" == 'macos' ]] || die "Desired state requires unsupported host platform: $DESIRED_HOST_PLATFORM"
  [[ "$(id -u)" != '0' ]] || die 'Do not run DJConnect recovery as root. Use the dedicated maintainer account so runner services do not inherit root privileges.'
  [[ "$(uname -s)" == 'Darwin' ]] || die 'This development-host bootstrap runs only on macOS.'
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
    # The bootstrap sources its modules and desired-state manifest from this
    # checkout. Switching that checkout to main while a repair is in progress
    # can remove the currently running package before final verification.
    if [[ "$(cd "$directory" && pwd -P)" == "$REPOSITORY_ROOT" ]]; then
      log "Preserving active host-bootstrap checkout $directory; it is not synchronized during this run."
      return
    fi
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

require_canonical_onboarding_4_2_0() {
  local central_repository="$1" manifest actual_version
  manifest="$central_repository/onboarding/manifest.yml"
  [[ "$DESIRED_ONBOARDING_PACKAGE_VERSION" == '4.2.0' ]] || die "The canonical macOS bootstrap requires onboarding 4.2.0; desired state declares $DESIRED_ONBOARDING_PACKAGE_VERSION."
  [[ -f "$manifest" ]] || die "The canonical onboarding manifest is unavailable: $manifest"
  actual_version="$(awk -F': ' '$1 == "package.version" { print $2; exit }' "$manifest")"
  [[ "$actual_version" == '4.2.0' ]] || die "The canonical macOS bootstrap requires onboarding 4.2.0; found ${actual_version:-missing} in $manifest."
}

bootstrap_developer_workstation() {
  if [[ "$SKIP_DEVELOPER_WORKSTATION" == '1' ]]; then
    return
  fi
  local central_repository="$GITHUB_ROOT/djconnect"
  local onboarding="$central_repository/onboarding/dev_onboarding_macos.sh"
  [[ -f "$onboarding" ]] || die "The full developer onboarding script is unavailable at $onboarding."
  require_canonical_onboarding_4_2_0 "$central_repository"
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
  local -a onboarding_args=(onboarding/dev_onboarding_macos.sh --all --yes --warm-sudo --no-log-file)
  if [[ "$DRY_RUN" == '1' ]]; then
    onboarding_args+=(--dry-run)
  fi
  if [[ -n "$NGROK_DOMAIN" ]]; then
    onboarding_args+=(--ngrok-domain "$NGROK_DOMAIN")
  fi
  run_in_dir "$central_repository" bash "${onboarding_args[@]}"
}

repair_engineering_platform() {
  local repository="$GITHUB_ROOT/djconnect" legacy_directory label plist
  [[ -f "$repository/tools/engineering/inbox_watcher.py" ]] || die "Engineering Inbox watcher is missing from $repository."
  [[ -f "$repository/tools/engineering/dashboard.py" ]] || die "Engineering dashboard is missing from $repository."

  log 'Analyzing local Engineering Platform watcher and dashboard health.'
  if ! python3 -m tools.engineering.inbox_watcher doctor --repo "$repository"; then
    warn 'Engineering Inbox doctor reported drift; repairing the canonical watcher service.'
  fi
  if ! python3 -m tools.engineering.dashboard doctor --repo "$repository"; then
    warn 'Engineering dashboard doctor reported drift; repairing the canonical dashboard service.'
  fi

  legacy_directory="$repository/.djconnect/legacy-launchagents"
  for label in com.djconnect.engineering-dashboard-backend com.djconnect.engineering-dashboard-proxy; do
    plist="$HOME/Library/LaunchAgents/$label.plist"
    [[ -f "$plist" ]] || continue
    log "Retiring legacy Engineering dashboard service $label before canonical restart."
    launchctl bootout "gui/$(id -u)" "$plist" >/dev/null 2>&1 || true
    mkdir -p "$legacy_directory"
    mv "$plist" "$legacy_directory/$label.plist"
  done

  log 'Restarting the canonical local Engineering Inbox watcher and dashboard.'
  python3 -m tools.engineering.inbox_watcher install --repo "$repository"
  python3 -m tools.engineering.dashboard install --repo "$repository"
  sleep 2

  python3 -m tools.engineering.inbox_watcher doctor --repo "$repository" || return 1
  python3 -m tools.engineering.dashboard doctor --repo "$repository" || return 1
}

ensure_home_assistant_internal_test_environment() {
  local central_repository="$GITHUB_ROOT/djconnect"
  local onboarding="$central_repository/onboarding/dev_onboarding_macos.sh"
  [[ -f "$onboarding" ]] || die "The Home Assistant internal-test-environment bootstrap is unavailable at $onboarding."
  log "Reconciling the internal Home Assistant Docker test environment ($DESIRED_HA_CONTAINER_NAME at $DESIRED_HA_URL)."
  local -a onboarding_args=(onboarding/dev_onboarding_macos.sh --steps 9 --yes --warm-sudo --no-log-file)
  [[ "$DRY_RUN" == '1' ]] && onboarding_args+=(--dry-run)
  run_in_dir "$central_repository" bash "${onboarding_args[@]}"
  if [[ "$DRY_RUN" == '1' ]]; then
    printf 'DRY: verify Home Assistant container %s is running and %s responds\n' "$DESIRED_HA_CONTAINER_NAME" "$DESIRED_HA_URL"
    return
  fi
  [[ "$(docker inspect --format '{{.State.Running}}' "$DESIRED_HA_CONTAINER_NAME" 2>/dev/null || true)" == 'true' ]] || die "Home Assistant internal-test container is not running: $DESIRED_HA_CONTAINER_NAME"
  curl -fsS --max-time 15 "$DESIRED_HA_URL" >/dev/null || die "Home Assistant internal-test environment is not reachable: $DESIRED_HA_URL"
  ok "Home Assistant internal test environment is ready at $DESIRED_HA_URL."
}

install_maintenance() {
  local app_root="$GITHUB_ROOT/djconnect-app"
  [[ -f "$app_root/scripts/runner/install_macos_ci_tooling_maintenance.sh" ]] || die 'The macOS maintenance installer is unavailable after repository preparation.'
  log 'Installing and verifying daily macOS runner tooling maintenance.'
  run_in_dir "$app_root" bash scripts/runner/install_macos_ci_tooling_maintenance.sh --run-now
}

refresh_host_tooling() {
  log 'Updating all Homebrew-managed DJConnect host tooling.'
  ensure_homebrew
  run brew update
  run brew upgrade
  run brew upgrade --cask
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
    if [[ "$PROFILE_PROVISIONING" == 'external_windows_arm64' ]]; then
      external_runner_profile_registered "$profile" || die "External Windows runner $runner_name is not online with its required labels."
      log "External Windows runner $runner_name is online with its required labels."
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
  log 'Running initial post-bootstrap verification for the complete local development host.'
  local -a verification_args=(onboarding/dev_onboarding_macos.sh --steps 21,22 --yes --no-log-file)
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
      profile_is_local_macos "$profile" || continue
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
