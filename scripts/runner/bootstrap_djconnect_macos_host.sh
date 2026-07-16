#!/usr/bin/env bash
# Version: 2.0.4
set -euo pipefail

readonly SCRIPT_DIRECTORY="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIRECTORY/macos_host_bootstrap/bootstrap.sh"

djconnect_macos_host_bootstrap_main "$@"
