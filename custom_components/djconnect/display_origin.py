"""Closed HTTPS external-origin policy for B; never authenticates rendezvous A."""
from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlsplit

ENTRY_PATH = '/djconnect/vibecast/display'
LABEL = re.compile(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\Z')
RESERVED = {'local', 'localhost', 'internal', 'invalid', 'test', 'example', 'lan', 'home', 'onion', 'arpa'}


def canonical_origin(value: object) -> str | None:
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
            or labels[-1] in RESERVED or any(x.startswith('xn--') for x in labels)
            or not re.fullmatch(r'[a-z]{2,63}', labels[-1])):
        return None
    canonical = 'https://' + host
    return canonical if parsed.netloc == host else None


def lexical_route_allowed(value: object, selected_origin: object) -> bool:
    """Lexical comparison only; selected_origin must be separately authenticated."""
    selected = canonical_origin(selected_origin)
    if selected is None or selected_origin != selected:
        return False
    origin = canonical_origin(value)
    return origin == selected and value == selected + ENTRY_PATH



def configured_origin(value: object) -> str | None:
    """Normalize only explicit standard port/root slash from trusted HA config."""
    if not isinstance(value, str):
        return None
    raw = value.removesuffix("/")
    if raw.endswith(":443"):
        raw = raw[:-4]
    origin = canonical_origin(raw)
    return origin if origin == raw else None


def selected_ha_origin(hass) -> str | None:
    """Read supported HA configuration synchronously; never request Host/forwarded."""
    from homeassistant.helpers.network import NoURLAvailableError, get_url
    try:
        value = get_url(hass, prefer_external=True, prefer_cloud=True,
                        allow_internal=False, allow_external=True, allow_cloud=True,
                        allow_ip=False, require_ssl=True, require_standard_port=True)
    except NoURLAvailableError:
        return None
    return configured_origin(value)
