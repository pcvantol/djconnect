"""Terminal-report persistence coordination for the Execution Host."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from .execution_errors import RunnerError


class ReportingCoordinator:
    """Own report delivery and validation; lifecycle remains caller-owned."""

    def deliver(
        self,
        *,
        path: Path,
        body: str,
        validate: Callable[[str], tuple[str, ...]],
        terminal_matches: Callable[[str], bool],
    ) -> Path:
        errors = validate(body)
        if not terminal_matches(body) or errors:
            details = "; ".join(errors) or "terminal state validation failed"
            raise RunnerError(f"Engineering Report consistency validation failed: {details}")
        path.write_text(body, encoding="utf-8")
        return path
