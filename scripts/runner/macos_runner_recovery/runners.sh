# Self-hosted runner profile registration and lifecycle operations.
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
