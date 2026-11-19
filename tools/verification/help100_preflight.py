"""Cost-free same-main setup; network-none and synthetic stdin only."""
import asyncio
import importlib.metadata
import importlib.util
import io
import json
import os
from pathlib import Path
import sys


def main():
    spec = importlib.util.spec_from_file_location('help100_setup_only',
        '/candidate/scripts/verification/verify_ask_dj_contextual_dialogue_http.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    import httpx
    clients = []
    original = module.AsyncOpenAI
    def constructor(*args, **kwargs):
        client = original(*args, **kwargs)
        assert client.max_retries == 0 and client.timeout == 25
        assert client._client.follow_redirects is False
        clients.append(client)
        return client
    module.AsyncOpenAI = constructor
    async def deny(client, request, *args, **kwargs):
        assert request.method == 'POST' and request.url.host == 'api.openai.com'
        assert request.url.path in {'/v1/responses', '/v1/chat/completions'}
        from scripts.verification.catalogue_progress import validate_progress
        from scripts.verification.askdj_example_catalogue_golden import cases, chain_cases, manifest_digest
        progress = json.loads(Path('/lab/catalogue-progress.json').read_text())
        assert validate_progress(progress, case_ids=[x['id'] for x in cases() + chain_cases()],
            manifest=manifest_digest())
        assert progress['sdk_attempts_reserved'] == 1 and progress['completed_cases'] == []
        assert len(clients) == 1
        value = {'schema': 1, 'status': 'PASS_SETUP_ONLY_NOT_QUALIFIED',
            'actual_HA_setup': 'FIRST_MODEL_REQUEST_FENCED', 'uid': os.getuid(),
            'request_dispatches': 0, 'test_credential': 'SYNTHETIC_ONLY',
            'openai_version': importlib.metadata.version('openai'),
            'httpx_version': importlib.metadata.version('httpx')}
        fd = os.open('/lab/setup-preflight.json', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as stream:
            json.dump(value, stream)
            stream.flush()
            os.fsync(stream.fileno())
        fd = os.open('/lab', os.O_RDONLY)
        os.fsync(fd)
        os.close(fd)
        # This disposable setup process must not swallow the pre-network fence
        # in an HA handler and continue with fabricated answers or more calls.
        os._exit(0)
    httpx.AsyncClient.send = deny
    sys.stdin = io.StringIO(json.dumps({'api_key': 'SYNTHETIC-NEVER-AUTHORIZED-SETUP-ONLY',
        'model': 'gpt-6-luna', 'max_tokens': 3000}))
    asyncio.run(module.main())
    raise RuntimeError('setup_returned_without_first_dispatch_fence')


if __name__ == '__main__':
    try:
        main()
    except BaseException:
        # Private log only. No credential, response body or exception text.
        print('HELP100_SETUP=FAIL_CLOSED', file=sys.stderr)
        raise SystemExit(1) from None
