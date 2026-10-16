"""Offline ROUTE-1 review corpus, never live route or installation authority."""
from __future__ import annotations

import ipaddress
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

ENTRY_PATH = '/djconnect/vibecast/display'
LABEL = re.compile(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\Z')
RESERVED = {'local', 'localhost', 'internal', 'invalid', 'test', 'example', 'lan', 'home', 'onion', 'arpa'}


def _origin(value: object) -> str | None:
    if not isinstance(value, str) or not value.isascii() or not 0 < len(value) <= 2048:
        return None
    if any(ord(c) <= 32 or ord(c) == 127 for c in value) or any(c in value for c in '%\\?#@'):
        return None
    try:
        parsed = urlsplit(value)
        host = parsed.hostname
        if (parsed.scheme != 'https' or not host or parsed.port not in (None, 443)
                or parsed.username is not None or parsed.password is not None):
            return None
    except ValueError:
        return None
    try:
        ipaddress.ip_address(host)
        return None
    except ValueError:
        pass
    labels = host.split('.')
    if (len(host) > 253 or len(labels) < 2 or any(not LABEL.fullmatch(x) for x in labels)
            or labels[-1] in RESERVED or not re.fullmatch(r'(?:[a-z]{2,63}|xn--[a-z0-9-]+)', labels[-1])):
        return None
    try:
        # Corpus admission is ASCII-only; never turn received Unicode into a trusted origin.
        if host.encode('ascii').decode('idna').encode('idna').decode('ascii') != host:
            return None
    except UnicodeError:
        return None
    canonical = 'https://' + host
    return canonical if parsed.netloc == host else None


def lexical_route_allowed(value: object, selected_origin: object) -> bool:
    """Lexical comparison only; selected_origin must be separately authenticated."""
    selected = _origin(selected_origin)
    if selected is None or selected_origin != selected:
        return False
    origin = _origin(value)
    return origin == selected and value == selected + ENTRY_PATH


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    corpus = json.loads((root/'examples/client_contracts/vibecast_display_admission_v1/route-cases.json').read_text())
    assert corpus['status'] == 'REVIEW_CANDIDATE_NOT_FROZEN'
    for case in corpus['cases']:
        actual = lexical_route_allowed(case['entry_url'], case['selected_origin'])
        if actual is not case['allowed']:
            raise AssertionError(case['id'])
    print(json.dumps({'lexical_cases': len(corpus['cases']), 'result': 'PASS_LEXICAL_CORPUS_ONLY',
                      'trust_TLS_DNS_redirect_HA_runtime': 'NOT_QUALIFIED'}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
