#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  ./release.sh <version> [--dry-run]

Examples:
  ./release.sh 3.0.1
  ./release.sh v3.0.1
  ./release.sh 3.0.1 --dry-run

The script stages all changes, commits, tags, pushes main and the tag, and
creates a GitHub release from the matching CHANGELOG.md version section. It
also updates the integration version in the repo before committing. The release
commit can be made from any branch whose HEAD is based on origin/main; the
script pushes the release commit explicitly to origin/main.
EOF
}

if [[ $# -lt 1 || $# -gt 2 ]]; then
  usage
  exit 64
fi

VERSION="${1#v}"
TAG="v${VERSION}"
DRY_RUN=false

if [[ $# -eq 2 ]]; then
  if [[ "$2" != "--dry-run" ]]; then
    usage
    exit 64
  fi
  DRY_RUN=true
fi

if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "Invalid version: $1. Use semantic version format, for example 3.0.1." >&2
  exit 64
fi

if [[ ! -f "CHANGELOG.md" || ! -f "custom_components/djconnect/manifest.json" ]]; then
  echo "Run this script from the djconnect repository root." >&2
  exit 1
fi

if git rev-parse "$TAG" >/dev/null 2>&1; then
  echo "Tag already exists locally: $TAG" >&2
  exit 1
fi

if [[ "$DRY_RUN" == false ]] && git ls-remote --exit-code --tags origin "refs/tags/${TAG}" >/dev/null 2>&1; then
  echo "Tag already exists on origin: $TAG" >&2
  exit 1
fi

run() {
  echo "+ $*"
  if [[ "$DRY_RUN" == false ]]; then
    "$@"
  fi
}

run_always() {
  echo "+ $*"
  "$@"
}

preflight_release_base() {
  if [[ "$DRY_RUN" == true ]]; then
    echo "+ git fetch origin main --tags --dry-run"
    return
  fi
  run_always git fetch origin main --tags
  if ! git rev-parse --verify origin/main >/dev/null 2>&1; then
    echo "origin/main is unavailable after fetch." >&2
    exit 1
  fi
  if ! git merge-base --is-ancestor origin/main HEAD; then
    echo "Current HEAD is not based on origin/main. Rebase or merge origin/main before releasing." >&2
    exit 1
  fi
}

validate_release() {
  run_always python3 -m unittest tests.test_ask_dj_e2e_contract
}

write_release_notes() {
  RELEASE_NOTES_FILE="$(mktemp "${TMPDIR:-/tmp}/djconnect-release-${TAG}.XXXXXX")"
  export RELEASE_NOTES_FILE
  echo "+ extract CHANGELOG.md section for ${VERSION} to ${RELEASE_NOTES_FILE}"
  VERSION="$VERSION" DRY_RUN="$DRY_RUN" RELEASE_NOTES_FILE="$RELEASE_NOTES_FILE" python3 - <<'PY'
import os
import re
from pathlib import Path

version = os.environ["VERSION"]
dry_run = os.environ["DRY_RUN"] == "true"
notes_path = Path(os.environ["RELEASE_NOTES_FILE"])
text = Path("CHANGELOG.md").read_text()
match = re.search(
    rf"^## {re.escape(version)}\n(?P<body>.*?)(?=^## \d+\.\d+\.\d+\n|\Z)",
    text,
    flags=re.MULTILINE | re.DOTALL,
)
if not match:
    if dry_run:
        notes_path.write_text(
            f"Dry-run release notes for {version}; CHANGELOG.md has no generated section yet.\n"
        )
        raise SystemExit(0)
    raise SystemExit(f"Missing CHANGELOG.md section for {version}")
body = match.group("body").strip()
if not body:
    raise SystemExit(f"Empty CHANGELOG.md section for {version}")
notes_path.write_text(body + "\n")
PY
}

bump_versions() {
  echo "+ update repo version to ${VERSION}"
  VERSION="$VERSION" DRY_RUN="$DRY_RUN" python3 - <<'PY'
import json
import os
import re
from pathlib import Path

version = os.environ["VERSION"]
tag = f"v{version}"
dry_run = os.environ["DRY_RUN"] == "true"


def replace_text(path: str, replacements: list[tuple[str, str]]) -> None:
    file_path = Path(path)
    text = file_path.read_text()
    updated = text
    for pattern, replacement in replacements:
        updated = re.sub(pattern, replacement, updated, flags=re.MULTILINE)
    if updated == text:
        print(f"  unchanged {path}")
        return
    print(f"  update {path}")
    if not dry_run:
        file_path.write_text(updated)


manifest_path = Path("custom_components/djconnect/manifest.json")
manifest = json.loads(manifest_path.read_text())
if manifest.get("version") != version:
    print("  update custom_components/djconnect/manifest.json")
    if not dry_run:
        manifest["version"] = version
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
else:
    print("  unchanged custom_components/djconnect/manifest.json")

replace_text(
    "custom_components/djconnect/const.py",
    [(r'^VERSION = "[^"]+"$', f'VERSION = "{version}"')],
)
replace_text(
    "CHANGELOG.md",
    [(r"^## Unreleased$", f"## {version}")],
)
replace_text(
    "README.md",
    [
        (r"^- Home Assistant integration: `[^`]+`$", f"- Home Assistant integration: `{version}`"),
        (r'  "version": "[^"]+",', f'  "version": "{version}",'),
        (r'  "version_tag": "v[^"]+",', f'  "version_tag": "{tag}",'),
        (
            r"releases/download/v[0-9]+\.[0-9]+\.[0-9]+/",
            f"releases/download/{tag}/",
        ),
        (
            r"releases/download/v[0-9]+\.[0-9]+\.[0-9]+/",
            f"releases/download/{tag}/",
        ),
        (
            r"djconnect-lilygo-t-embed-s3-v[0-9]+\.[0-9]+\.[0-9]+\.bin",
            f"djconnect-lilygo-t-embed-s3-{tag}.bin",
        ),
        (
            r"djconnect-lilygo-t-embed-s3-v[0-9]+\.[0-9]+\.[0-9]+\.bin",
            f"djconnect-lilygo-t-embed-s3-{tag}.bin",
        ),
        (
            r"djconnect-esp32-s3-box-3-v[0-9]+\.[0-9]+\.[0-9]+\.bin",
            f"djconnect-esp32-s3-box-3-{tag}.bin",
        ),
        (
            r"djconnect-esp32-s3-box-3-v[0-9]+\.[0-9]+\.[0-9]+\.bin",
            f"djconnect-esp32-s3-box-3-{tag}.bin",
        ),
        (r'  "min_ha_integration": "[^"]+"', f'  "min_ha_integration": "{version}"'),
        (r"\./release\.sh [0-9]+\.[0-9]+\.[0-9]+", f"./release.sh {version}"),
        (r"\./release\.sh [0-9]+\.[0-9]+\.[0-9]+ --dry-run", f"./release.sh {version} --dry-run"),
        (r'git commit -m "Release DJConnect v[^"]+"', f'git commit -m "Release DJConnect {tag}"'),
        (r"git tag v[0-9]+\.[0-9]+\.[0-9]+", f"git tag {tag}"),
        (r"git push origin v[0-9]+\.[0-9]+\.[0-9]+", f"git push origin {tag}"),
        (
            r'gh release create v[0-9]+\.[0-9]+\.[0-9]+ --title "DJConnect v[^"]+" --notes-file CHANGELOG\.md',
            f'gh release create {tag} --title "DJConnect {tag}" --notes-file "$RELEASE_NOTES_FILE"',
        ),
    ],
)
replace_text(
    "examples/firmware_manifest.json",
    [
        (r'  "version": "[^"]+",', f'  "version": "{version}",'),
        (r'  "version_tag": "v[^"]+",', f'  "version_tag": "{tag}",'),
        (r'  "min_ha_integration": "[^"]+",', f'  "min_ha_integration": "{version}",'),
        (
            r"releases/download/v[0-9]+\.[0-9]+\.[0-9]+/",
            f"releases/download/{tag}/",
        ),
        (
            r"releases/download/v[0-9]+\.[0-9]+\.[0-9]+/",
            f"releases/download/{tag}/",
        ),
        (
            r"djconnect-lilygo-t-embed-s3-v[0-9]+\.[0-9]+\.[0-9]+\.bin",
            f"djconnect-lilygo-t-embed-s3-{tag}.bin",
        ),
        (
            r"djconnect-lilygo-t-embed-s3-v[0-9]+\.[0-9]+\.[0-9]+\.bin",
            f"djconnect-lilygo-t-embed-s3-{tag}.bin",
        ),
        (
            r"djconnect-esp32-s3-box-3-v[0-9]+\.[0-9]+\.[0-9]+\.bin",
            f"djconnect-esp32-s3-box-3-{tag}.bin",
        ),
        (
            r"djconnect-esp32-s3-box-3-v[0-9]+\.[0-9]+\.[0-9]+\.bin",
            f"djconnect-esp32-s3-box-3-{tag}.bin",
        ),
    ],
)
replace_text(
    "AGENTS.md",
    [(r"^- Actuele integratieversie: `[^`]+`\.$", f"- Actuele integratieversie: `{version}`.")],
)
replace_text(
    "CHAT_BOOTSTRAP.md",
    [(r"^- Laatste release: `[^`]+`\.$", f"- Laatste release: `{version}`.")],
)
replace_text(
    "HANDOFF.md",
    [
        (
            r"^- Current integration release: `[^`]+`\.$",
            f"- Current integration release: `{version}`.",
        ),
        (
            r"^- Release status: DJConnect `[^`]+` keeps the `3\.2\.x` transport, pairing and$",
            f"- Release status: DJConnect `{version}` keeps the `3.2.x` transport, pairing and",
        ),
        (
            r"^- Current latest baseline is `[^`]+`\.$",
            f"- Current latest baseline is `{version}`.",
        ),
        (
            r"^- For the current `[^`]+` release, no pinned Python package versions were$",
            f"- For the current `{version}` release, no pinned Python package versions were",
        ),
    ],
)
replace_text(
    "SYNC_PROMPTS.md",
    [
        (
            r"aligned after Home Assistant integration release `v[^`]+`\. DJConnect clients on the",
            f"aligned after Home Assistant integration release `{tag}`. DJConnect clients on the",
        ),
    ],
)
PY
}

preflight_release_base
validate_release
bump_versions
write_release_notes
run git add .
run git commit -m "Release DJConnect ${TAG}"
run git tag "$TAG"
run git push origin HEAD:main
run git push origin "$TAG"
run gh release create "$TAG" --title "DJConnect ${TAG}" --notes-file "$RELEASE_NOTES_FILE"

echo "Release ${TAG} complete."
