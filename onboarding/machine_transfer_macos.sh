#!/usr/bin/env bash
# DJConnect macOS machine-transfer utility. Exports only explicitly selected
# DJConnect assets; it never reads the Keychain, browser profiles or CLI stores.
set -euo pipefail

readonly SCRIPT_NAME="$(basename "$0")"
readonly DEFAULT_ROOT="$HOME/Library/Application Support/DJConnect/machine-transfer"
MODE=''
ARCHIVE=''
SIGNING_P12=''
PROFILES_DIR="$HOME/Library/MobileDevice/Provisioning Profiles"
ENV_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/.djconnect-onboarding.env"
INSTALL_SSH=0
SKIP_KEYCHAIN_IMPORT=0
DRY_RUN=0
declare -a SSH_KEYS=() LICENSE_FILES=()

usage() {
  cat <<EOF
Usage: $SCRIPT_NAME --export [options]
       $SCRIPT_NAME --import --archive FILE [options]

Creates or imports an AES-256 encrypted DJConnect machine-transfer archive.
Archives default outside the repository: $DEFAULT_ROOT

Options:
  --export                         Export explicitly selected assets.
  --import                         Import an encrypted archive.
  --archive FILE                   Output archive for export; required for import.
  --signing-p12 FILE               Existing portable Apple signing P12 to include.
  --profiles-dir DIR               Provisioning-profile directory.
  --env-file FILE                  DJConnect onboarding token env file.
  --ssh-key FILE                   Explicit SSH private key to include; repeatable.
  --license-file FILE              Explicit license file to include; repeatable.
  --install-ssh-keys               On import, install included SSH keys into ~/.ssh.
  --skip-keychain-import           Do not import included P12 into login.keychain.
  --dry-run                        Show the plan without reading or writing secrets.
  --help                           Show this help.

The export prints a generated recovery passphrase once. Store it separately
from the archive. No passphrase, token, private key or archive contents are
written to logs. GitHub, Docker and Apple account sessions are intentionally
not exported; authenticate them interactively on the replacement machine.
EOF
}

die() { printf 'ERROR %s\n' "$*" >&2; exit 1; }
note() { printf '%s\n' "$*"; }
require_file() { [[ -f "$1" ]] || die "Required file is unavailable: $1"; }
random_passphrase() {
  local parts=() part
  for _ in 1 2 3 4 5 6; do
    part="$(LC_ALL=C tr -dc 'a-z' </dev/urandom | head -c 6)"
    parts+=("$part")
  done
  (IFS=-; printf '%s' "${parts[*]}")
}
prompt_passphrase() {
  local value confirm
  read -r -s -p 'Machine-transfer recovery passphrase: ' value; printf '\n'
  read -r -s -p 'Confirm recovery passphrase: ' confirm; printf '\n'
  [[ -n "$value" && "$value" == "$confirm" ]] || die 'Passphrases do not match.'
  REPLY="$value"
}
copy_asset() {
  local source="$1" target="$2" label="$3"
  require_file "$source"
  mkdir -p "$(dirname "$target")"
  cp -p "$source" "$target"
  chmod 600 "$target"
  note "Included: $label"
}
encrypt_archive() {
  local input="$1" output="$2" passphrase="$3"
  openssl enc -aes-256-cbc -pbkdf2 -iter 600000 -md sha256 -salt \
    -in "$input" -out "$output" -pass fd:3 3<<<"$passphrase"
}
decrypt_archive() {
  local input="$1" output="$2" passphrase="$3"
  openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 -md sha256 \
    -in "$input" -out "$output" -pass fd:3 3<<<"$passphrase"
}
export_transfer() {
  local staging tarball passphrase index=0 key
  [[ -n "$ARCHIVE" ]] || ARCHIVE="$DEFAULT_ROOT/djconnect-machine-transfer-$(date -u '+%Y%m%dT%H%M%SZ').tar.enc"
  [[ "$ARCHIVE" != *"/"* || "$ARCHIVE" != "$(pwd)"/* ]] || die 'Archive output must be outside the current repository.'
  [[ "$DRY_RUN" == 1 ]] && { note "DRY: create encrypted archive at $ARCHIVE"; return; }
  command -v openssl >/dev/null || die 'openssl is required.'
  umask 077; mkdir -p "$(dirname "$ARCHIVE")"; staging="$(mktemp -d)"; trap 'rm -rf "$staging"' RETURN
  mkdir -p "$staging/assets"
  [[ -n "$SIGNING_P12" ]] && copy_asset "$SIGNING_P12" "$staging/assets/apple-signing.p12" 'Apple signing P12'
  if [[ -d "$PROFILES_DIR" ]]; then
    mkdir -p "$staging/assets/provisioning-profiles"; find "$PROFILES_DIR" -maxdepth 1 -type f -name '*.mobileprovision' -exec cp -p {} "$staging/assets/provisioning-profiles/" \;
  fi
  [[ -f "$ENV_FILE" ]] && copy_asset "$ENV_FILE" "$staging/assets/djconnect-onboarding.env" 'DJConnect token environment'
  for key in "${SSH_KEYS[@]}"; do index=$((index + 1)); copy_asset "$key" "$staging/assets/ssh/key-$index" "explicit SSH key"; done
  index=0; for key in "${LICENSE_FILES[@]}"; do index=$((index + 1)); copy_asset "$key" "$staging/assets/licenses/license-$index" "explicit license file"; done
  find "$staging/assets" -type f | grep -q . || die 'No explicitly selectable assets were found to export.'
  (cd "$staging" && find assets -type f -print0 | sort -z | xargs -0 shasum -a 256 > MANIFEST.sha256 && tar -cf "$staging/transfer.tar" MANIFEST.sha256 assets)
  passphrase="$(random_passphrase)"
  encrypt_archive "$staging/transfer.tar" "$ARCHIVE" "$passphrase"; chmod 600 "$ARCHIVE"
  note "Export complete: $ARCHIVE"
  note "Recovery passphrase (store separately): $passphrase"
  unset passphrase
}
import_transfer() {
  local staging tarball passphrase target_root
  [[ -n "$ARCHIVE" ]] || die '--archive is required for import.'; require_file "$ARCHIVE"
  [[ "$DRY_RUN" == 1 ]] && { note "DRY: decrypt and import $ARCHIVE"; return; }
  command -v openssl >/dev/null || die 'openssl is required.'
  umask 077; staging="$(mktemp -d)"; trap 'rm -rf "$staging"' RETURN
  prompt_passphrase; tarball="$staging/transfer.tar"; decrypt_archive "$ARCHIVE" "$tarball" "$REPLY"; unset REPLY
  tar -xf "$tarball" -C "$staging"; (cd "$staging" && shasum -a 256 -c MANIFEST.sha256)
  target_root="$HOME/Library/Application Support/DJConnect/machine-transfer/imported"; mkdir -p "$target_root"
  [[ -f "$staging/assets/djconnect-onboarding.env" ]] && { cp -p "$staging/assets/djconnect-onboarding.env" "$ENV_FILE"; chmod 600 "$ENV_FILE"; note 'Imported: DJConnect token environment'; }
  if [[ -d "$staging/assets/provisioning-profiles" ]]; then mkdir -p "$PROFILES_DIR"; cp -p "$staging/assets/provisioning-profiles"/*.mobileprovision "$PROFILES_DIR/" 2>/dev/null || true; note 'Imported: provisioning profiles'; fi
  if [[ -f "$staging/assets/apple-signing.p12" ]]; then
    cp -p "$staging/assets/apple-signing.p12" "$target_root/apple-signing.p12"; chmod 600 "$target_root/apple-signing.p12"; note "Imported: portable Apple signing P12 at $target_root/apple-signing.p12"
    if [[ "$SKIP_KEYCHAIN_IMPORT" == 0 ]]; then read -r -s -p 'P12 password for login-keychain import: ' REPLY; printf '\n'; security import "$target_root/apple-signing.p12" -k "$(security login-keychain | tr -d '\"')" -P "$REPLY" -T /usr/bin/codesign -T /usr/bin/xcodebuild; unset REPLY; note 'Imported: Apple signing identity into login keychain'; fi
  fi
  [[ -d "$staging/assets/licenses" ]] && { mkdir -p "$target_root/licenses"; cp -p "$staging/assets/licenses"/* "$target_root/licenses/"; note "Imported: explicit license files at $target_root/licenses"; }
  if [[ -d "$staging/assets/ssh" ]]; then
    if [[ "$INSTALL_SSH" == 1 ]]; then mkdir -p "$HOME/.ssh"; chmod 700 "$HOME/.ssh"; for key in "$staging"/assets/ssh/*; do target="$HOME/.ssh/$(basename "$key")"; [[ ! -e "$target" ]] || die "Refusing to overwrite SSH key: $target"; cp -p "$key" "$target"; chmod 600 "$target"; done; note 'Imported: explicit SSH keys'; else mkdir -p "$target_root/ssh"; cp -p "$staging/assets/ssh"/* "$target_root/ssh/"; note "Staged SSH keys at $target_root/ssh; rerun with --install-ssh-keys to install."; fi
  fi
  note 'Import complete. Reauthenticate GitHub, Docker and Apple accounts interactively on this machine.'
}

while [[ $# -gt 0 ]]; do case "$1" in
  --export|--import) [[ -z "$MODE" ]] || die 'Choose exactly one mode.'; MODE="${1#--}"; shift ;;
  --archive) ARCHIVE="${2:?}"; shift 2 ;; --signing-p12) SIGNING_P12="${2:?}"; shift 2 ;;
  --profiles-dir) PROFILES_DIR="${2:?}"; shift 2 ;; --env-file) ENV_FILE="${2:?}"; shift 2 ;;
  --ssh-key) SSH_KEYS+=("${2:?}"); shift 2 ;; --license-file) LICENSE_FILES+=("${2:?}"); shift 2 ;;
  --install-ssh-keys) INSTALL_SSH=1; shift ;; --skip-keychain-import) SKIP_KEYCHAIN_IMPORT=1; shift ;;
  --dry-run) DRY_RUN=1; shift ;; --help|-h) usage; exit 0 ;; *) die "Unknown option: $1" ;; esac; done
[[ "$(uname -s)" == Darwin ]] || die 'This utility runs only on macOS.'
[[ -n "$MODE" ]] || { usage; exit 1; }
[[ "$MODE" == export ]] && export_transfer || import_transfer
