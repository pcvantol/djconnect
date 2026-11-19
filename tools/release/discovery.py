"""Repository Ownership discovery for the Platform Release Orchestrator."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


class DiscoveryError(ValueError):
    """Raised when canonical Repository Ownership cannot be interpreted."""


@dataclass(frozen=True)
class RepositoryNode:
    """A repository record discovered from an ownership document."""

    name: str
    role: str
    mandatory: bool
    ownership_summary: str


_HEADING = re.compile(r"^##\s+`(?P<name>[^`]+)`\s*$", re.MULTILINE)


def discover_repositories(ownership_path: Path, role_overrides: dict[str, str] | None = None) -> list[RepositoryNode]:
    """Discover repository nodes without embedding a platform repository list.

    Role inference deliberately uses ownership language, not repository names.
    A future ownership document may declare an explicit role using
    ``Release role: <role>``; until then distribution-only ownership is the
    only intrinsic role that can be inferred safely. Callers may supply a
    release-plan role override as an immutable planning input.
    """

    text = ownership_path.read_text(encoding="utf-8")
    matches = list(_HEADING.finditer(text))
    if not matches:
        raise DiscoveryError(f"no repository ownership records found in {ownership_path}")
    overrides = role_overrides or {}
    nodes: list[RepositoryNode] = []
    for index, match in enumerate(matches):
        body_end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[match.end() : body_end].strip()
        name = match.group("name")
        explicit = re.search(r"^Release role:\s*`?(active_source|release_source|distribution|optional|future)`?\s*$", body, re.MULTILINE)
        role = overrides.get(name) or (explicit.group(1) if explicit else _infer_role(body))
        if role not in {"active_source", "release_source", "distribution", "optional", "future"}:
            raise DiscoveryError(f"unsupported release role {role!r} for {name}")
        mandatory = role not in {"optional", "future"}
        nodes.append(RepositoryNode(name=name, role=role, mandatory=mandatory, ownership_summary=_summary(body)))
    return nodes


def _infer_role(body: str) -> str:
    normalized = " ".join(body.lower().split())
    if "release distribution artifacts only" in normalized:
        return "distribution"
    if "future repository" in normalized or "future release path" in normalized:
        return "future"
    return "active_source"


def _summary(body: str) -> str:
    first_line = next((line.strip() for line in body.splitlines() if line.strip()), "")
    return first_line[:240]
