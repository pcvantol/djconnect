# Least-privilege and local credential-expiry audits.
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
