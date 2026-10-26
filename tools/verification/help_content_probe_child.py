"""Bounded diagnostic adapter around the unchanged real HA/profile execution."""

from __future__ import annotations

import asyncio
import importlib.util
import os
from pathlib import Path
import signal
import sys
import time

from tools.verification.help100_child import checkpoint, classify
from tools.verification.help_content_probe import CONTENT_PROFILE_ID, DiagnosticProgress, mode_policy


def remaining(wall, mono):
    value = min(wall - time.time(), mono - time.monotonic())
    if not 0 < value <= 1770:
        raise TimeoutError
    return value


async def execute():
    mode = os.environ["DJC_CONTENT_MODE"]
    selected, _, _ = mode_policy(mode)
    wall, mono = (
        float(os.environ["DJC_CONTENT_WALL_END"]),
        float(os.environ["DJC_CONTENT_MONO_END"]),
    )
    seconds = remaining(wall, mono)
    if os.environ.get("DJC_CATALOGUE_CASES", "") != ",".join(selected):
        raise ValueError("diagnostic_selection_changed")
    checkpoint("IMPORT")
    spec = importlib.util.spec_from_file_location(
        "original_help_content_main",
        "/candidate/scripts/verification/verify_ask_dj_contextual_dialogue_http.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if selected:
        # The original main explicitly skips its full100 progress constructor
        # for selected cases. Supply the same observer API, with the closed selected-mode
        # pre-I/O budget. No case, response, model or source predicate is replaced.
        module.catalogue_progress = DiagnosticProgress(
            Path("/lab/diagnostic-progress.json"), content_digest=os.environ["DJC_CONTENT_DIGEST"],
            mode=mode,
        )
    checkpoint("MAIN")
    task = asyncio.current_task()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, task.cancel)
    import httpx

    original_send, closed = httpx.AsyncClient.send, False

    async def bounded_send(client, request, *args, **kwargs):
        if closed:
            raise TimeoutError
        async with asyncio.timeout(remaining(wall, mono)):
            return await original_send(client, request, *args, **kwargs)

    httpx.AsyncClient.send = bounded_send

    async def watch():
        while True:
            try:
                await asyncio.sleep(min(0.1, remaining(wall, mono)))
            except TimeoutError:
                task.cancel()
                return

    watcher = asyncio.create_task(watch())
    try:
        async with asyncio.timeout(seconds):
            await module.main(qualification_profile=CONTENT_PROFILE_ID)
    except BaseException as exc:
        progress = getattr(module, "catalogue_progress", None)
        if progress is not None:
            progress.failure_without_masking_primary(
                cancelled=isinstance(exc, asyncio.CancelledError)
            )
        raise
    finally:
        # Keep the transport closed through HA teardown and late cancelled tasks.
        closed = True
        watcher.cancel()
        await asyncio.gather(watcher, return_exceptions=True)


def main():
    code, error = 1, "UNKNOWN"
    try:
        asyncio.run(execute())
        code, error = 0, "NONE"
    except (ImportError, ModuleNotFoundError):
        error = "IMPORT_FAILED"
    except (ValueError, KeyError, TypeError):
        error = "INPUT_OR_SETUP_INVALID"
    except (TimeoutError, asyncio.CancelledError):
        error = "TIMEOUT_OR_CANCELLED"
    except BaseException as exc:
        error = classify(exc)
    try:
        checkpoint("TERMINAL", error)
    except BaseException:
        code = 1
    return code


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    raise SystemExit(main())
