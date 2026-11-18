"""Canonical Platform Release version utilities."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re


class VersionError(ValueError):
    """Raised when a platform or repository version is malformed."""


@dataclass(frozen=True, order=True)
class PlatformVersion:
    """A platform compatibility train represented as Major.Minor."""

    major: int
    minor: int

    _PATTERN = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)$")

    @classmethod
    def parse(cls, value: str) -> "PlatformVersion":
        match = cls._PATTERN.fullmatch(value.strip())
        if not match:
            raise VersionError("platform version must be Major.Minor")
        return cls(major=int(match.group(1)), minor=int(match.group(2)))

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}"


@dataclass(frozen=True, order=True)
class RepositoryVersion:
    """A repository delivery version represented as Major.Minor.Patch."""

    major: int
    minor: int
    patch: int

    _PATTERN = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")

    @classmethod
    def parse(cls, value: str) -> "RepositoryVersion":
        match = cls._PATTERN.fullmatch(value.strip())
        if not match:
            raise VersionError("repository version must be Major.Minor.Patch")
        return cls(major=int(match.group(1)), minor=int(match.group(2)), patch=int(match.group(3)))

    @property
    def platform_version(self) -> PlatformVersion:
        return PlatformVersion(major=self.major, minor=self.minor)

    def compatible_with(self, platform_version: PlatformVersion) -> bool:
        return self.platform_version == platform_version

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


def read_repository_version(repository_root: Path) -> RepositoryVersion:
    """Read a local version from common repository metadata without mutation.

    The caller chooses the repository root. This utility never maps a platform
    repository name to a path and therefore cannot embed repository membership.
    """

    candidates = (
        repository_root / "manifest.json",
        repository_root / "package.json",
        repository_root / "pyproject.toml",
        repository_root / "VERSION",
    )
    for candidate in candidates:
        if not candidate.is_file():
            continue
        value = _read_version_value(candidate)
        if value:
            return RepositoryVersion.parse(value)
    raise VersionError(f"no readable repository version found under {repository_root}")


def _read_version_value(path: Path) -> str | None:
    if path.name in {"manifest.json", "package.json"}:
        data = json.loads(path.read_text(encoding="utf-8"))
        value = data.get("version")
        return value if isinstance(value, str) else None
    text = path.read_text(encoding="utf-8").strip()
    if path.name == "pyproject.toml":
        match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']\s*$', text, re.MULTILINE)
        return match.group(1) if match else None
    return text.splitlines()[0] if text else None
