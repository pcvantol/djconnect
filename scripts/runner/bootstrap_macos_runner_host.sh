#!/usr/bin/env bash
set -euo pipefail

readonly SCRIPT_DIRECTORY="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIRECTORY/macos_runner_recovery/bootstrap.sh"

djconnect_macos_runner_recovery_main "$@"
