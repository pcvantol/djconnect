"""Owned bounded HTTPS adapter to the actual paired HA/Broadcast fixture."""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import json
from pathlib import Path
import ssl
import time

from aiohttp import web


def register(hass, *, output: Path):
    state = {}

    async def end(request):
        if 'ended' not in state:
            state['ended'] = await state['post']('/session/end', {
                **state['identity'], 'session_id': state['session_id']})
        return web.json_response({'success': True})

    hass.http.app.router.add_post('/__speech_lab/end', end)

    @asynccontextmanager
    async def serve(client, identity, post, active, moment):
        state.update(post=post, identity=identity, session_id=active.session_id)
        tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls.load_cert_chain(output/'server.pem', output/'server-key.pem')
        local = web.TCPSite(client.server.runner, '0.0.0.0', 18235, ssl_context=tls)
        await local.start()
        static = web.Application()

        async def index(request):
            return web.Response(text=(output/'build/cast/index.html').read_text(), content_type='text/html',
                headers={'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer'})

        static.router.add_get('/', index)
        runner = web.AppRunner(static)
        await runner.setup()
        await web.TCPSite(runner, '0.0.0.0', 18236, ssl_context=tls).start()
        try:
            (output/'browser-ready.json').write_text(json.dumps({
                'session_id': active.session_id, 'broadcast_token': active.broadcast.broadcast_token,
                'moment': moment.as_dict(), 'playback': active.broadcast.state.playback.as_dict()}))
            started = time.monotonic()
            while not (output/'browser-done.json').exists():
                if time.monotonic()-started > 75:
                    raise TimeoutError('Owned speech browser proof did not finish in75s')
                await asyncio.sleep(.2)
            receipt = json.loads((output/'browser-done.json').read_text())
            assert receipt['result'] == 'PASS', receipt
            assert 'ended' in state
            yield state['ended']
        finally:
            await runner.cleanup()
            await local.stop()
    return serve
