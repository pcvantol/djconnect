# Version: 1.0.0
# CLI parsing and top-level recovery orchestration.
djconnect_macos_runner_recovery_main() {
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
}
