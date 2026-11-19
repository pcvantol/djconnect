"""Dependency manifest and lockfile inspection without upgrades."""

from __future__ import annotations

import json
from pathlib import Path

from tools.verification.models import DependencyInspection, GateResult, GateState


class DependencyInspector:
    MANIFESTS = (
        ("python", "pyproject.toml", ("uv.lock", "requirements.txt", "requirements_test.txt")),
        ("swift", "Package.swift", ("Package.resolved",)),
        ("nuget", "*.csproj", ("packages.lock.json",)),
        ("npm", "package.json", ("package-lock.json", "pnpm-lock.yaml", "yarn.lock")),
        ("platformio", "platformio.ini", ("platformio.lock",)),
        ("esp-idf", "idf_component.yml", ("dependencies.lock",)),
    )

    def inspect(self, root: Path) -> tuple[DependencyInspection, ...]:
        inspections: list[DependencyInspection] = []
        for ecosystem, manifest_pattern, lock_names in self.MANIFESTS:
            for manifest in _find(root, manifest_pattern):
                inspections.append(
                    DependencyInspection(
                        ecosystem=ecosystem,
                        manifest=manifest,
                        lockfile=_first_existing(manifest.parent, lock_names),
                        package_count=_package_count(manifest),
                        security_advisories_checked=False,
                        drift_checked=any((manifest.parent / name).exists() for name in lock_names),
                    )
                )
        return tuple(inspections)

    def validate(self, root: Path) -> list[GateResult]:
        inspections = self.inspect(root)
        missing_locks = [
            str(item.manifest.relative_to(root))
            for item in inspections
            if item.ecosystem in {"swift", "npm", "nuget"} and item.lockfile is None
        ]
        state = GateState.WARNING if missing_locks else GateState.PASS if inspections else GateState.SKIPPED
        return [
            GateResult(
                "dependency_inspection",
                state,
                f"{len(inspections)} dependency manifests inspected",
                {"missing_locks": missing_locks, "ecosystems": sorted({item.ecosystem for item in inspections})},
            )
        ]


def _find(root: Path, pattern: str) -> list[Path]:
    return sorted(path for path in root.rglob(pattern) if ".git" not in path.parts and "artifacts" not in path.parts)


def _first_existing(root: Path, names: tuple[str, ...]) -> Path | None:
    return next((root / name for name in names if (root / name).exists()), None)


def _package_count(manifest: Path) -> int:
    if manifest.name == "package.json":
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return 0
        return sum(len(data.get(key) or {}) for key in ("dependencies", "devDependencies"))
    if manifest.name == "pyproject.toml":
        text = manifest.read_text(encoding="utf-8")
        return text.count("\n    \"") + text.count("\n    '")
    return 0
