"""One process/event-loop owner for public MusicBrainz request admission.

The service permits at most one request/second per source IP. This coordinates
DJConnect's own consumers; it cannot qualify other processes on the same IP.
"""
import asyncio
from dataclasses import dataclass, field
from weakref import WeakKeyDictionary


@dataclass
class _State:
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    last: float = float('-inf')
    blocked_until: float = 0.0


_states = WeakKeyDictionary()


def _state():
    # A contended asyncio.Lock may retain its loop. Explicitly discard closed
    # loops rather than retaining test/reload loops through a weak-key value.
    for previous in tuple(_states):
        if previous.is_closed():
            del _states[previous]
    loop = asyncio.get_running_loop()
    if loop not in _states:
        _states[loop] = _State()
    return loop, _states[loop]


async def admit(guard=None):
    loop, state = _state()
    async with state.lock:
        if loop.time() < state.blocked_until:
            return False
        await asyncio.sleep(max(0.0, 1.1-(loop.time()-state.last)))
        if guard is not None:
            # Keep the final potentially waiting owner check coordinated. A
            # different consumer cannot dispatch while it is held here.
            await guard()
        if loop.time() < state.blocked_until:
            return False
        state.last = loop.time()
        return True


def defer(retry_after):
    loop, state = _state()
    value = str(retry_after)
    seconds = max(60,min(3600,int(value) if value.isascii() and value.isdigit() and len(value)<8 else 60))
    state.blocked_until = max(state.blocked_until,loop.time()+seconds)
