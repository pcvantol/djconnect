"""Codex execution evidence helpers, isolated from lifecycle coordination."""
from __future__ import annotations

import os
from pathlib import Path
import tempfile

from .agent_state import redact_diagnostic


def project_codex_activity(event: object) -> str | None:
    """Map one JSONL event to an approved, prompt-free activity label."""
    if not isinstance(event, dict) or event.get("type") not in {"item.started", "item.updated"}:
        return None
    item = event.get("item")
    if not isinstance(item, dict):
        return None
    return {
        "reasoning": "Codex plant de volgende stap",
        "command_execution": "Codex voert een opdracht uit",
        "file_change": "Codex bewerkt bestanden",
        "web_search": "Codex onderzoekt referentiemateriaal",
        "mcp_tool_call": "Codex gebruikt een ontwikkeltool",
        "agent_message": "Codex formuleert het resultaat",
    }.get(item.get("type"))


def redacted_cli_tail(value: str, prompt: str, *, limit: int = 1_200) -> str:
    without_prompt = value.replace(prompt, "[PROMPT_OMITTED]") if prompt else value
    return redact_diagnostic("\n".join(without_prompt.splitlines()[-60:]), limit=limit) or "(empty)"


def format_cli_failure(exit_code: int, stderr: str, stdout: str, prompt: str = "") -> str:
    return "\n".join((f"Codex CLI exit code: {exit_code}", f"stderr tail: {redacted_cli_tail(stderr, prompt)}", f"stdout tail: {redacted_cli_tail(stdout, prompt)}"))


def write_redacted_codex_cli_log(root: Path, run_id: str, detail: str) -> Path:
    directory = root / ".engineering" / "logs" / "codex"
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = directory / f"{run_id}.log"
    descriptor, temporary = tempfile.mkstemp(prefix=f".{run_id}.", suffix=".tmp", dir=directory)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write("# Redacted Codex CLI diagnostic\n\n" + redact_diagnostic(detail, limit=3_000) + "\n")
            handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return path
