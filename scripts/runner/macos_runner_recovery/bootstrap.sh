#!/usr/bin/env bash
# DJConnect macOS runner-host recovery package. Modules share one Bash process
# and its deliberately explicit recovery state; this file owns load order.

readonly RECOVERY_PACKAGE_DIRECTORY="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "$RECOVERY_PACKAGE_DIRECTORY/config.sh"
source "$RECOVERY_PACKAGE_DIRECTORY/core.sh"
source "$RECOVERY_PACKAGE_DIRECTORY/workflow.sh"
source "$RECOVERY_PACKAGE_DIRECTORY/security.sh"
source "$RECOVERY_PACKAGE_DIRECTORY/operations.sh"
source "$RECOVERY_PACKAGE_DIRECTORY/runners.sh"
source "$RECOVERY_PACKAGE_DIRECTORY/apple.sh"
source "$RECOVERY_PACKAGE_DIRECTORY/main.sh"
