"""Platform-independent environment snapshot collection."""

from __future__ import annotations

import hashlib
import json
import locale
import platform
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from tools.verification.models import EnvironmentSnapshot, HarnessConfig
from tools.verification.environment.toolchain import ToolchainInspector


class EnvironmentSnapshotter:
    def collect(self, config: HarnessConfig) -> EnvironmentSnapshot:
        dependency_versions = _dependency_versions(config.root)
        fingerprint_payload = {
            "scenario_paths": [str(path) for path in config.scenario_paths],
            "ci": config.ci,
            "test_mode": config.test_mode,
            "overrides": sorted(config.overrides),
        }
        fingerprint = hashlib.sha256(
            json.dumps(fingerprint_payload, sort_keys=True).encode("utf-8")
        ).hexdigest()
        toolchain = _toolchain()
        capabilities = {
            name: info.state.value
            for name, info in ToolchainInspector().discover().items()
        }
        return EnvironmentSnapshot(
            timestamp=datetime.now(timezone.utc).isoformat(),
            host=platform.node(),
            os=f"{platform.system()} {platform.release()}",
            architecture=platform.machine(),
            toolchain=toolchain,
            locale=locale.getlocale()[0] or "",
            timezone=time.tzname[0] if time.tzname else "",
            git_sha=_git(config.root, "rev-parse", "HEAD"),
            git_branch=_git(config.root, "rev-parse", "--abbrev-ref", "HEAD"),
            dependency_versions=dependency_versions,
            configuration_fingerprint=fingerprint,
            capabilities=capabilities,
        )


def _toolchain() -> dict[str, str]:
    tools: dict[str, str] = {"python": platform.python_version()}
    for command in ("git", "pytest", "node", "npm", "xcodebuild", "swift", "dotnet", "pio", "docker", "prlctl"):
        resolved = shutil.which(command)
        if resolved:
            tools[command] = resolved
    return tools


def _dependency_versions(root: Path) -> dict[str, str]:
    versions: dict[str, str] = {}
    manifest = root / "custom_components/djconnect/manifest.json"
    if manifest.exists():
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return versions
        for key, value in data.items():
            if key in {"version", "requirements", "dependencies"}:
                versions[key] = json.dumps(value, sort_keys=True) if not isinstance(value, str) else value
    return versions


def _git(root: Path, *args: str) -> str | None:
    try:
        return subprocess.check_output(("git", *args), cwd=root, text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return None
