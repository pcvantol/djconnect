# Local Apple signing-material recovery and keychain access.
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
