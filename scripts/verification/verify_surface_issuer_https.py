"""Actual aiohttp HTTPS adapter in an isolated container, synthetic TLS/DNS only.

A temporary test CA/key exists solely in container RAM tmpfs and is destroyed
with this fixture. Resolver and trust root are explicit test boundaries; the
product's exact HTTPS adapter, headers, decompression flag and body reader run
unaltered. No operator, enrollment, external network or provider is involved.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import socket
import ssl
import sys
import tempfile
import time
import types
from unittest.mock import patch

ROOT = Path(os.environ.get('DJC_SOURCE_ROOT', Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(ROOT))
for name, directory in (('custom_components', ROOT/'custom_components'),
        ('custom_components.djconnect', ROOT/'custom_components/djconnect')):
    package = types.ModuleType(name)
    package.__path__ = [str(directory)]
    sys.modules[name] = package

from cryptography import x509  # noqa: E402
from cryptography.hazmat.primitives import hashes, serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric import ec  # noqa: E402
from cryptography.x509.oid import NameOID  # noqa: E402
import aiohttp  # noqa: E402
from aiohttp import web  # noqa: E402
from aiohttp.abc import AbstractResolver  # noqa: E402
from verify_surface_issuer_lifecycle import SyntheticPreEnrolledOwner  # noqa: E402
from custom_components.djconnect.surface_issuer_transport import IssuerHTTPS  # noqa: E402
from custom_components.djconnect.surface_issuer_wire import PREFIX, signing_bytes  # noqa: E402
from custom_components.djconnect.surface_push_contract import SurfacePushError  # noqa: E402


async def main():
    lab = Path(os.environ['DJC_LAB_ROOT'])
    host = 'synthetic.example.invalid'
    seen, cases, mode = [], [], ['ordinary']
    async def handler(request):
        assert request.method == 'POST' and request.path == PREFIX+'status'
        assert 'Authorization' not in request.headers and 'Cookie' not in request.headers
        assert request.headers['Accept-Encoding'] == 'identity'
        assert set(await request.json()) == {'payload', 'signature'}
        seen.append(mode[0])
        if mode[0] == 'gzip':
            return web.Response(body=gzip.compress(b'{"ok":true}'),
                headers={'Content-Type': 'application/json', 'Content-Encoding': 'gzip'})
        if mode[0] == 'wrong_media':
            return web.Response(body=b'{"ok":true}', content_type='text/html')
        if mode[0] == 'duplicate_media':
            response = web.Response(body=b'{"ok":true}', content_type='application/json')
            response.headers.add('Content-Type', 'text/html')
            return response
        if mode[0] == 'too_large':
            return web.Response(body=b' '*8193, content_type='application/json')
        if mode[0] == 'duplicate_json':
            return web.Response(body=b'{"ok":true,"ok":false}', content_type='application/json')
        if mode[0] == 'invalid_utf8':
            return web.Response(body=b'{"x":"\xff"}', content_type='application/json')
        if mode[0] == 'redirect':
            return web.Response(status=307, headers={'Location': 'https://unrelated.invalid/'})
        return web.Response(body=b'{"ok":true}',
            headers={'Content-Type': 'application/json; charset=UTF-8', 'Content-Encoding': 'identity'})
    owner = SyntheticPreEnrolledOwner()
    capture = owner.original
    e = capture.expected
    payload = {'contract_version': 1, 'purpose': 'surface_push', 'action': 'status',
        'operation_id': e.operation_id, 'delegation_id': e.delegation_id,
        'delegation_revision': 1, 'key_thumbprint': e.key_thumbprint}
    signature = await owner.sign(capture, PREFIX+'status', signing_bytes(PREFIX+'status', payload), action='status')
    app = web.Application()
    app.router.add_post(PREFIX+'status', handler)
    with tempfile.TemporaryDirectory(dir=lab) as temporary:
        directory = Path(temporary)
        tls_key = ec.generate_private_key(ec.SECP256R1())
        subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, host)])
        now = datetime.now(timezone.utc)
        cert = (x509.CertificateBuilder().subject_name(subject).issuer_name(subject)
            .public_key(tls_key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now-timedelta(minutes=1)).not_valid_after(now+timedelta(hours=1))
            .add_extension(x509.SubjectAlternativeName([x509.DNSName(host)]), critical=False)
            .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
            .sign(tls_key, hashes.SHA256()))
        cert_path, key_path = directory/'synthetic.pem', directory/'synthetic-key.pem'
        cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        key_path.write_bytes(tls_key.private_bytes(serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        key_path.chmod(0o600)
        server_tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        server_tls.load_cert_chain(cert_path, key_path)
        trust = ssl.create_default_context(cafile=str(cert_path))
        assert trust.check_hostname and trust.verify_mode == ssl.CERT_REQUIRED
        runner = web.AppRunner(app, access_log=None)
        await runner.setup()
        site = web.TCPSite(runner, '127.0.0.1', 0, ssl_context=server_tls)
        await site.start()
        port = site._server.sockets[0].getsockname()[1]
        class FixtureResolver(AbstractResolver):
            def __init__(self, *args, **kwargs):
                pass
            async def resolve(self, hostname, port_number=0, family=socket.AF_INET):
                assert hostname == host
                return [{'hostname': hostname, 'host': '127.0.0.1', 'port': port,
                    'family': socket.AF_INET, 'proto': 0, 'flags': 0}]
            async def close(self):
                pass
        guards = [0]
        def guard():
            guards[0] += 1  # No real live-owner admission claimed by this fixture.
        try:
            # DNS and TLS trust are synthetic. Certificate verification and the
            # exact product transport remain enabled, not replaced by a fake session.
            with patch.object(aiohttp.connector, 'DefaultResolver', FixtureResolver), \
                    patch.object(aiohttp.connector, '_SSL_CONTEXT_VERIFIED', trust):
                for kind in ('ordinary', 'gzip', 'wrong_media', 'duplicate_media', 'too_large',
                        'duplicate_json', 'invalid_utf8', 'redirect'):
                    mode[0] = kind
                    before = len(seen)
                    try:
                        reply = await IssuerHTTPS().post_once(capture, 'status',
                            {'payload': payload, 'signature': signature}, guard=guard,
                            deadline=time.monotonic()+10)
                    except SurfacePushError:
                        assert kind != 'ordinary', 'ordinary JSON positive control rejected'
                        cases.append({'case': kind, 'result': 'REJECTED'})
                    else:
                        assert kind == 'ordinary' and reply.status == 200 and reply.body == {'ok': True}
                        cases.append({'case': kind, 'result': 'ACCEPTED'})
                    assert len(seen) == before+1, 'request replayed or never reached synthetic HTTPS'
        finally:
            await runner.cleanup()
            owner.key, tls_key = None, None
    record = {'scope': 'ACTUAL_AIOHTTP_PRODUCT_HTTPS_ADAPTER_SYNTHETIC_DNS_TLS_TRUST_ONLY',
        'aiohttp_version': aiohttp.__version__, 'cases': cases, 'loopback_https_requests': len(seen),
        'external_network_calls': 0, 'operator_enrollments': 0, 'native_provider_calls': 0,
        'test_tls_key_ram_tmpfs_only_removed': True, 'real_or_host_private_keys': 0,
        'guards_executed': guards[0], 'production_tls_or_dns_claim': False,
        'source_hashes': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (ROOT/'custom_components/djconnect').rglob('*')
            if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}}
    (lab/'issuer-https-receipt.json').write_text(json.dumps(record, indent=2)+'\n')
    print(json.dumps({k: v for k, v in record.items() if k != 'source_hashes'}))


if __name__ == '__main__':
    asyncio.run(main())
