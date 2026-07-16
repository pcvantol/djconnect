#!/usr/bin/env bash
# Compatibility wrapper. The canonical onboarding package is ../onboarding.
set -euo pipefail

readonly REPOSITORY_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec "$REPOSITORY_ROOT/onboarding/dev_onboarding_macos.sh" "$@"
