"""Evaluation-only supervisor; exact existing paid main owns all case semantics."""
from __future__ import annotations

import asyncio
import importlib.util
import json
import os
from pathlib import Path
import signal
import sys
import time


def checkpoint(stage, error="NONE"):
    """Exclusive durable prefix; never serialize exception text or credentials."""
    path = Path('/lab') / ('child-' + stage + '.json')
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump({'schema': 1, 'stage': stage, 'error': error,
                   'qualification': 'NOT_QUALIFIED'}, stream)
        stream.flush()
        os.fsync(stream.fileno())
    fd = os.open('/lab', os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def remaining(wall_end, mono_end):
    seconds = min(wall_end - time.time(), mono_end - time.monotonic())
    if not 0 < seconds <= 1770:
        raise TimeoutError
    return seconds


def classify(error):
    """Fixed enums only; never emit provider bodies/messages or arbitrary names."""
    known = {'AuthenticationError': 'MODEL_AUTHENTICATION_FAILED',
        'PermissionDeniedError': 'MODEL_PERMISSION_DENIED',
        'RateLimitError': 'MODEL_RATE_LIMIT', 'APITimeoutError': 'MODEL_TIMEOUT',
        'APIConnectionError': 'MODEL_CONNECTION_FAILED', 'APIStatusError': 'MODEL_HTTP_FAILED'}
    current, seen = error, set()
    for _ in range(8):
        if current is None or id(current) in seen:
            break
        seen.add(id(current))
        if type(current).__module__.split('.')[0] == 'openai':
            for kind in type(current).__mro__:
                if kind.__name__ in known:
                    return known[kind.__name__]
        current = current.__cause__ or current.__context__
    return 'ASSERTION_FAILED' if isinstance(error, AssertionError) else 'ACTUAL_TEST_FAILED'


async def execute():
    checkpoint('IMPORT')
    spec = importlib.util.spec_from_file_location('owned_help100_actual_main',
        '/candidate/scripts/verification/verify_ask_dj_contextual_dialogue_http.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    checkpoint('MAIN')
    # Deadlines were captured before reservation/container creation by the parent.
    # timeout cancels the same task, including every SDK await, without retries.
    wall_end = float(os.environ['DJC_HELP100_WALL_END'])
    mono_end = float(os.environ['DJC_HELP100_MONO_END'])
    seconds = remaining(wall_end, mono_end)
    if not 0 < seconds <= 1770:
        raise TimeoutError
    task = asyncio.current_task()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, task.cancel)
    # Only add an original-deadline fence around the real transport. No fixture
    # response, retry, credential, model setting or case assertion is replaced.
    import httpx
    original_send = httpx.AsyncClient.send
    closed = False
    async def bounded_send(client, request, *args, **kwargs):
        if closed:
            raise TimeoutError
        async with asyncio.timeout(remaining(wall_end, mono_end)):
            return await original_send(client, request, *args, **kwargs)
    httpx.AsyncClient.send = bounded_send
    async def watch():
        while True:
            try:
                await asyncio.sleep(min(0.1, remaining(wall_end, mono_end)))
            except TimeoutError:
                task.cancel()
                return
    watcher = asyncio.create_task(watch())
    try:
        async with asyncio.timeout(seconds):
            await module.main()
    except BaseException as exc:
        progress = getattr(module, 'catalogue_progress', None)
        if progress is not None:
            progress.failure_without_masking_primary(cancelled=isinstance(exc, asyncio.CancelledError))
        raise
    finally:
        # Keep the safety fence closed through asyncio.run's cancellation of
        # remaining HA tasks. Restoring unguarded send here would open a window
        # for a late task after the supervised main has already returned.
        closed = True
        watcher.cancel()
        await asyncio.gather(watcher, return_exceptions=True)


def main():
    code, error = 1, 'UNKNOWN'
    try:
        asyncio.run(execute())
        code, error = 0, 'NONE'
    except (ImportError, ModuleNotFoundError):
        error = 'IMPORT_FAILED'
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        error = 'INPUT_OR_SETUP_INVALID'
    except PermissionError:
        error = 'PERMISSION_DENIED'
    except (TimeoutError, asyncio.CancelledError):
        error = 'TIMEOUT_OR_CANCELLED'
    except OSError:
        error = 'IO_FAILED'
    except BaseException as exc:
        error = classify(exc)
    # Reporting failures cannot turn failure into success or mask its exit status.
    try:
        checkpoint('TERMINAL', error)
    except BaseException:
        code = 1
    return code


if __name__ == '__main__':
    sys.dont_write_bytecode = True
    raise SystemExit(main())
