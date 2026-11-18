"""Real HA Store reload/uncertain-save proof using only disposable synthetic data.

Run in the pinned HA image, network disabled, source read-only and an empty lab
mount. This is not the destructive paired producer, native or installed proof.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
from pathlib import Path
import secrets
import sys
from unittest.mock import patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

ROOT = Path(os.environ.get('DJC_SOURCE_ROOT', '/candidate'))
sys.path.insert(0, str(ROOT))
from custom_components.djconnect.ask_dj_history import AskDJHistoryManager, STORE_KEY, STORE_VERSION  # noqa: E402


def hashes():
    paths = [*sorted((ROOT / 'custom_components/djconnect').rglob('*.py')),
             Path(__file__).resolve()]
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


async def main():
    before = hashes()
    output = Path(os.environ.get('DJC_LAB_ROOT', '/lab'))
    config = output / ('synthetic-store-' + secrets.token_hex(6))
    config.mkdir(parents=True, exist_ok=False)
    hass = HomeAssistant(str(config))
    manager = AskDJHistoryManager(hass)
    cases = []

    async def append(identifier, session):
        return await manager.async_append_exchange('profile:synthetic',
            {'client_message_id': identifier, 'text': 'Synthetic question'},
            {'success': True, 'text': 'Synthetic answer'},
            session_turn={'turn_id': identifier, 'context': {'session_id': session}})

    await append('old', 'old')
    await append('live', 'live')
    revision = manager.scope_revision('profile:synthetic')
    assert await manager.async_forget_archived_sessions('synthetic', frozenset({'old'})) == 2
    # A distinct HA Store instance reads the actual serialized JSON, not manager RAM.
    restored = AskDJHistoryManager(store=Store(hass, STORE_VERSION, STORE_KEY))
    view = await restored.async_history('profile:synthetic')
    assert {m['client_message_id'] for m in view['messages']} == {'live'}
    assert view['clear_revision'] == 1
    assert restored.scope_revision('profile:synthetic') == revision
    cases.append('actual_store_reload_targeted_erasure_and_live_privacy')

    manager.register_session_request('profile:synthetic', 'pending')
    assert await manager.async_forget_archived_sessions('synthetic', frozenset({'absent'})) == 0
    manager.unregister_session_request('profile:synthetic', 'pending')
    restored = AskDJHistoryManager(store=Store(hass, STORE_VERSION, STORE_KEY))
    assert await restored.async_session_request_cleared('profile:synthetic', 'pending')
    cases.append('actual_store_zero_body_pending_retry_tombstone')

    await append('second-archive', 'second-archive')
    actual_save = manager._store.async_save
    async def lost_ack(data):
        await actual_save(data)
        raise OSError('synthetic acknowledgement loss AFTER actual Store save')
    with patch.object(manager._store, 'async_save', lost_ack):
        try:
            await manager.async_forget_archived_sessions('synthetic', frozenset({'second-archive'}))
        except OSError:
            pass
        else:
            raise AssertionError('expected acknowledgement uncertainty')
    try:
        await manager.async_history('profile:synthetic')
    except RuntimeError as exc:
        assert str(exc) == 'history_delete_outcome_unknown'
    else:
        raise AssertionError('stale RAM must be inaccessible after uncertain Store write')
    assert await manager.async_forget_archived_sessions('synthetic', frozenset({'second-archive'})) == 0
    restored = AskDJHistoryManager(store=Store(hass, STORE_VERSION, STORE_KEY))
    view = await restored.async_history('profile:synthetic')
    assert {m['client_message_id'] for m in view['messages']} == {'live'}
    assert view['clear_revision'] == 2
    cases.append('actual_store_save_then_lost_ack_reload_recovery')

    privacy = restored.scope_revision('profile:synthetic')
    await restored.async_clear('profile:synthetic')
    final = AskDJHistoryManager(store=Store(hass, STORE_VERSION, STORE_KEY))
    view = await final.async_history('profile:synthetic')
    assert view['messages'] == []
    assert final.scope_revision('profile:synthetic') != privacy
    cases.append('actual_store_normal_clear_still_withdraws_after_targeted_erasure')
    assert hashes() == before, 'source changed during qualification'
    receipt = {'status': 'PASS', 'cases': cases, 'source_files_sha256': before,
               'qualification': 'actual HA Store save/reload; synthetic records and acknowledgement-loss injection',
               'paired_delete_producer': 'NOT_IMPLEMENTED', 'installed': 'NOT_RUN',
               'native': 'NOT_RUN', 'audible': 'NOT_RUN', 'paid_attempts': 0}
    (output / 'store-readback.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'status': 'PASS', 'cases': len(cases), 'paid_attempts': 0}))


if __name__ == '__main__':
    asyncio.run(main())
