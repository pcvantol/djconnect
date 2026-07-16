# Version: 1.3.0
# Phase lifecycle, progress reporting, reboot continuation and repair flow.
phase_section_id() {
  local phase_id="$1"
  case "$phase_id" in
    macos-preflight) printf '%s' 'host-qualification' ;;
    sudo|tooling|xcode|parallels) printf '%s' 'host-provisioning' ;;
    github-auth|permissions-audit|repositories) printf '%s' 'repository-access' ;;
    developer-workstation|docker-auth|home-assistant-lab) printf '%s' 'developer-workstation' ;;
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
    host-provisioning) printf '%s' 'Install or qualify required shared macOS tooling and platform components.' ;;
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
    developer-workstation) printf '%s\n' developer-workstation docker-auth home-assistant-lab ;;
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
    printf '%s\n' "- Desired state: $DESIRED_STATE_FILE (version $DESIRED_STATE_VERSION, schema $DESIRED_STATE_SCHEMA_VERSION)"
    printf '%s\n' "- Manifest minimum bootstrap version: $DESIRED_MINIMUM_TOOL_VERSION"
    printf '%s\n' "- Manifest/bootstrap compatibility: $MANIFEST_TOOL_COMPATIBILITY_VERDICT"
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
  printf '%s\n' macos-preflight sudo tooling xcode parallels github-auth permissions-audit repositories developer-workstation docker-auth home-assistant-lab
  for profile in "${DESIRED_PROFILES[@]}"; do
    profile_is_local_macos "$profile" || continue
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
  for phase_id in macos-preflight sudo tooling xcode parallels github-auth repositories developer-workstation docker-auth home-assistant-lab runner-apple runner-private-network runner-esp32 runner-pi maintenance tooling-refresh reboot-check services apple-signing apple-readiness credential-expiry-audit apple-github-audit initial-verification; do
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
  install_resume_terminal_continuation
  log 'Recovery paused for reboot. After the next macOS login, Terminal opens and starts the protected recovery continuation.'
}

xml_escape() {
  local value="$1"
  value="${value//&/&amp;}"
  value="${value//</&lt;}"
  value="${value//>/&gt;}"
  value="${value//\"/&quot;}"
  value="${value//\'/&apos;}"
  printf '%s' "$value"
}

install_resume_terminal_continuation() {
  local -a resume_args
  local plist_command
  resume_args=(
    "$0" --resume --resume-state "$RESUME_STATE_FILE"
    --profiles "$PROFILE_SELECTION"
    --desired-state "$DESIRED_STATE_FILE"
    --github-root "$GITHUB_ROOT"
    --runner-root "$RUNNER_ROOT"
    --log-level "$LOG_LEVEL"
    --parallel-jobs "$PARALLEL_JOBS"
    --expiry-warning-days "$EXPIRY_WARNING_DAYS"
  )
  [[ "$SKIP_CODEX" == '1' ]] && resume_args+=(--skip-codex)
  [[ -n "$XCODE_VERSION" ]] && resume_args+=(--xcode-version "$XCODE_VERSION")
  [[ -n "$SIGNING_P12" ]] && resume_args+=(--signing-p12 "$SIGNING_P12")
  [[ -n "$PROVISIONING_PROFILES_DIR" ]] && resume_args+=(--provisioning-profiles-dir "$PROVISIONING_PROFILES_DIR")
  [[ "$CONFIGURE_KEYCHAIN_ACCESS" == '1' ]] && resume_args+=(--configure-keychain-access)
  [[ "$INSTALL_PARALLELS" == '1' ]] && resume_args+=(--install-parallels)
  [[ "$SKIP_DEVELOPER_WORKSTATION" == '1' ]] && resume_args+=(--skip-developer-workstation)
  [[ -n "$NGROK_DOMAIN" ]] && resume_args+=(--ngrok-domain "$NGROK_DOMAIN")
  [[ "$PROMPT_NGROK_AUTH" == '1' ]] && resume_args+=(--prompt-ngrok-auth)
  [[ "$CONFIGURE_APPLE_INTERNAL_RELEASE" == '1' ]] && resume_args+=(--configure-apple-internal-release)
  [[ -n "$APPLE_TEAM_ID" ]] && resume_args+=(--apple-team-id "$APPLE_TEAM_ID")
  [[ -n "$APPLE_DEVELOPMENT_IDENTITY" ]] && resume_args+=(--apple-development-identity "$APPLE_DEVELOPMENT_IDENTITY")
  [[ "$ALLOW_STEP_RETRY" != '1' ]] && resume_args+=(--no-step-retry)
  [[ -n "$SKIP_PHASES" ]] && resume_args+=(--skip-phases "$SKIP_PHASES")
  [[ -n "$FORCE_PHASES" ]] && resume_args+=(--force-phases "$FORCE_PHASES")
  [[ "$MEMORY_OVERRIDE_CONFIRMED" == '1' ]] && resume_args+=(--confirm-memory-override)
  [[ -n "${NO_COLOR:-}" ]] && resume_args+=(--no-color)
  case "$LOG_FILE" in
    none) resume_args+=(--no-log-file) ;;
    '') ;;
    *) resume_args+=(--log-file "$LOG_FILE") ;;
  esac
  case "$REPORT_FILE" in
    none) resume_args+=(--no-report-file) ;;
    '') ;;
    *) resume_args+=(--report-file "$REPORT_FILE") ;;
  esac

  require_external_output_path 'Recovery Terminal continuation' "$RESUME_CONTINUATION_COMMAND"
  umask 077
  mkdir -p "$(dirname "$RESUME_CONTINUATION_COMMAND")" "$(dirname "$RESUME_AUTOSTART_PLIST")"
  {
    printf '%s\n' '#!/usr/bin/env bash' 'set -uo pipefail'
    printf 'rm -f %q\n' "$RESUME_AUTOSTART_PLIST"
    printf '%s\n' "printf '%s\\n' 'DJConnect recovery continuation started after reboot. Sensitive passwords and token values remain outside the checkpoint.'"
    printf '%q ' "${resume_args[@]}"
    printf '%s\n' '' 'continuation_status=$?' "printf '%s\\n' \"DJConnect recovery continuation finished with status \$continuation_status. Press Return to close this Terminal window.\"" "read -r _" 'exit "$continuation_status"'
  } >"$RESUME_CONTINUATION_COMMAND"
  chmod 700 "$RESUME_CONTINUATION_COMMAND"
  plist_command="$(xml_escape "$RESUME_CONTINUATION_COMMAND")"
  {
    cat <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$RESUME_AUTOSTART_LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/open</string>
    <string>-a</string>
    <string>Terminal</string>
    <string>$plist_command</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>ProcessType</key>
  <string>Interactive</string>
  <key>LimitLoadToSessionType</key>
  <array><string>Aqua</string></array>
</dict>
</plist>
EOF
  } >"$RESUME_AUTOSTART_PLIST"
  chmod 600 "$RESUME_AUTOSTART_PLIST"
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
  rm -f "$RESUME_STATE_FILE" "$RESUME_CONTINUATION_COMMAND" "$RESUME_AUTOSTART_PLIST"
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
    home-assistant-lab) printf '%s' 'developer-workstation docker-auth' ;;
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
          profile_is_local_macos "$profile" || continue
          printf ' runner-%s' "$profile"
        fi
      done
      ;;
    apple-signing) printf '%s' 'xcode' ;;
    apple-readiness) printf '%s' 'repositories github-auth xcode' ;;
    credential-expiry-audit) printf '%s' 'apple-readiness' ;;
    apple-github-audit) printf '%s' 'credential-expiry-audit' ;;
    initial-verification) printf '%s' 'repositories developer-workstation docker-auth home-assistant-lab services reboot-check' ;;
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
    developer-workstation|initial-verification) [[ -f "$GITHUB_ROOT/djconnect/onboarding/dev_onboarding_macos.sh" ]] || return 1; PHASE_PRECHECK_RESULT='Central developer-onboarding package is available.' ;;
    docker-auth) command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1 || return 1; PHASE_PRECHECK_RESULT='Docker Desktop daemon is ready.' ;;
    home-assistant-lab) command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1 || return 1; PHASE_PRECHECK_RESULT='Docker Desktop daemon is ready for the Home Assistant internal test environment.' ;;
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
      sudo|tooling|xcode|parallels|github-auth|permissions-audit|repositories|developer-workstation|docker-auth|home-assistant-lab|runner-apple|runner-private-network|runner-esp32|runner-pi|maintenance|tooling-refresh|reboot-check|services|apple-signing|apple-readiness|credential-expiry-audit|apple-github-audit|initial-verification) ;;
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
      macos-preflight|sudo|tooling|xcode|parallels|github-auth|permissions-audit|repositories|developer-workstation|docker-auth|home-assistant-lab|runner-apple|runner-private-network|runner-esp32|runner-pi|maintenance|tooling-refresh|reboot-check|services|apple-signing|apple-readiness|credential-expiry-audit|apple-github-audit|initial-verification) ;;
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
    profile_is_local_macos "$profile" || continue
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
    profile_is_local_macos "$profile" || continue
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
