#!/usr/bin/env bash
# Version: 1.1.0
# DJConnect macOS development-host bootstrap package. Modules share one Bash process
# and its deliberately explicit recovery state; this file owns load order.

readonly HOST_BOOTSTRAP_PACKAGE_DIRECTORY="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "$HOST_BOOTSTRAP_PACKAGE_DIRECTORY/config.sh"
source "$HOST_BOOTSTRAP_PACKAGE_DIRECTORY/core.sh"
source "$HOST_BOOTSTRAP_PACKAGE_DIRECTORY/workflow.sh"
source "$HOST_BOOTSTRAP_PACKAGE_DIRECTORY/security.sh"
source "$HOST_BOOTSTRAP_PACKAGE_DIRECTORY/operations.sh"
source "$HOST_BOOTSTRAP_PACKAGE_DIRECTORY/runners.sh"
source "$HOST_BOOTSTRAP_PACKAGE_DIRECTORY/apple.sh"
source "$HOST_BOOTSTRAP_PACKAGE_DIRECTORY/main.sh"

verify_recovery_package_manifest
