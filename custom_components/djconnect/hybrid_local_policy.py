"""Pure, fail-closed direct-local ingress predicates; never infer trust from headers."""

from ipaddress import ip_address, ip_network
from urllib.parse import urlsplit

_PRIVATE = tuple(ip_network(value) for value in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "fc00::/7", "fe80::/10"))
_PROXY_HEADERS = {"forwarded", "via", "x-real-ip", "cf-connecting-ip", "true-client-ip", "x-original-forwarded-for"}


def transport_security_policy():
    return {
        "policy_version": 1,
        "external": "authenticated_tls",
        "local_plaintext": "qualified_direct_only",
        "peer_policy": "enabled_interface_subnet_or_loopback",
        "internal_origin_required": True,
        "forwarded_plaintext": "forbidden",
    }


def canonical_origin(value):
    """Return a strict HTTP origin tuple, or None for anything beyond an origin."""
    if not isinstance(value, str) or not value or any(c.isspace() for c in value):
        return None
    try:
        parsed = urlsplit(value)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
            or "?" in value
            or "#" in value
            or value.endswith(":")
        ):
            return None
        return parsed.scheme, parsed.hostname.lower(), parsed.port if parsed.port is not None else (443 if parsed.scheme == "https" else 80)
    except ValueError:
        return None


def same_origin(origins, scheme, host):
    if not origins:
        return True
    # Browser Origin is serialized without a trailing slash or other URL syntax.
    if len(origins) != 1 or origins[0].endswith("/"):
        return False
    expected = canonical_origin(scheme + "://" + host)
    return expected is not None and canonical_origin(origins[0]) == expected


def direct_peer_allowed(peername, adapters):
    if not isinstance(peername, (tuple, list)) or len(peername) < 2:
        return False
    try:
        peer = ip_address(str(peername[0]).split("%", 1)[0])
        if peer.version == 6 and peer.ipv4_mapped:
            peer = peer.ipv4_mapped
        if peer.is_loopback:
            return True
        if not any(peer in subnet for subnet in _PRIVATE if subnet.version == peer.version):
            return False
        for adapter in adapters:
            if not adapter.get("enabled"):
                continue
            if peer.version == 6 and peer.is_link_local:
                if len(peername) < 4 or not peername[3] or peername[3] != adapter.get("index"):
                    continue
            for address in adapter.get("ipv4" if peer.version == 4 else "ipv6", []):
                try:
                    subnet = ip_network(f"{address['address']}/{address['network_prefix']}", strict=False)
                except (KeyError, ValueError, TypeError):
                    continue
                if subnet.prefixlen and subnet.version == peer.version and peer in subnet:
                    return True
    except (ValueError, TypeError):
        return False
    return False


def direct_local_allowed(peername, adapters, internal_url, host, header_names):
    headers = {str(key).lower() for key in header_names}
    if headers & _PROXY_HEADERS or any(key.startswith("x-forwarded-") for key in headers):
        return False
    expected = canonical_origin(internal_url)
    return (
        expected is not None
        and expected[0] == "http"
        and expected == canonical_origin("http://" + host)
        and direct_peer_allowed(peername, adapters)
    )
