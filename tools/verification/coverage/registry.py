"""Coverage parser plugin registry."""

from __future__ import annotations

from pathlib import Path

from tools.verification.coverage.models import CoverageParseResult
from tools.verification.coverage.parsers import AppleXccovParser, CoberturaParser, CoverageParser, LCOVParser


class CoverageParserRegistry:
    def __init__(self) -> None:
        self._parsers: dict[str, CoverageParser] = {}

    def register(self, parser: CoverageParser) -> None:
        self._parsers[parser.format_id] = parser

    def available_formats(self) -> tuple[str, ...]:
        return tuple(sorted(self._parsers))

    def parse(
        self,
        path: Path,
        *,
        coverage_format: str,
        repository: str,
        commit_sha: str,
        scope: str,
    ) -> CoverageParseResult:
        parser = self._parsers.get(coverage_format)
        if parser is None:
            return CoverageParseResult(False, error="unsupported_format", diagnostics={"format": coverage_format})
        return parser.parse(path, repository=repository, commit_sha=commit_sha, scope=scope)


def default_registry() -> CoverageParserRegistry:
    registry = CoverageParserRegistry()
    registry.register(CoberturaParser())
    registry.register(LCOVParser())
    registry.register(AppleXccovParser())
    return registry
