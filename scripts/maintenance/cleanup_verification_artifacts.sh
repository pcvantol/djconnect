#!/usr/bin/env bash
set -euo pipefail

mode=check
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/.."
[[ "${1:-}" == "--execute" ]] && mode=execute
[[ "${1:-}" == "--execute" || "${1:-}" == "--check" || -z "${1:-}" ]] || { echo "Usage: $0 [--check|--execute]" >&2; exit 2; }
found=0
for repo in "$root"/*; do
  [[ -d "$repo/.git" && -d "$repo/artifacts/verification" ]] || continue
  while IFS= read -r -d '' rel; do
    found=1
    if [[ "$mode" == execute ]]; then rm -f -- "$repo/$rel"; fi
  done < <(cd "$repo" && find artifacts/verification -type f -mtime +14 -print0 | git check-ignore -z --stdin)
  [[ "$mode" == execute ]] && find "$repo/artifacts/verification" -depth -type d -empty -delete
done
[[ "$mode" == execute || "$found" == 0 ]]
