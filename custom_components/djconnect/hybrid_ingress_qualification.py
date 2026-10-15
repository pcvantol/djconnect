"""Bounded read-only operator ingress qualification; never minted by a request."""

import hashlib
import json
import os
from pathlib import Path
import stat
import time
from ipaddress import ip_address, ip_network

from .hybrid_local_policy import canonical_origin, direct_local_allowed

FILENAME = "djconnect_direct_local_ingress.json"
_LIMIT = 8192
_FIELDS = {"version", "ha_install_id", "internal_origin", "interface_digest", "allowed_peers", "excluded_peers", "source_preserved", "proxies_excluded", "qualified_at", "expires_at", "evidence_sha256"}


def interface_digest(adapters):
    rows = sorted(
        ({"name": row.get("name"), "index": row.get("index"), "ipv4": sorted(row.get("ipv4", []), key=lambda x: str(x.get("address"))), "ipv6": sorted(row.get("ipv6", []), key=lambda x: str(x.get("address")))} for row in adapters if row.get("enabled")),
        key=lambda x: str(x["name"]),
    )
    return hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("duplicate qualification key")
        result[key] = value
    return result


def _signature(value):
    return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns


def qualification_current_now(config_dir, qualification, *, now=None):
    """Final metadata/clock fence: no file body read and no event-loop yield."""
    now = time.time() if now is None else now
    if now >= qualification["expires_at"]:
        return False
    try:
        current = os.stat(Path(config_dir) / FILENAME, follow_symlinks=False)
    except OSError:
        return False
    return _signature(current) == qualification["stamp"]


def read_qualification(config_dir):
    """Read one regular, operator-owned immutable snapshot without following links."""
    fd = None
    try:
        path = Path(config_dir) / FILENAME
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > _LIMIT or before.st_uid not in {0, os.geteuid()} or before.st_mode & 0o022:
            return None
        raw = os.read(fd, _LIMIT + 1)
        after = os.fstat(fd)
        current = os.stat(path, follow_symlinks=False)
        if len(raw) > _LIMIT or _signature(before) != _signature(after) or _signature(after) != _signature(current):
            return None
        def reject_constant(_value):
            raise ValueError("non-finite qualification value")

        record = json.loads(raw, object_pairs_hook=_pairs, parse_constant=reject_constant)
        if not isinstance(record, dict):
            return None
        return record, hashlib.sha256(raw).hexdigest(), _signature(before)
    except (OSError, ValueError, UnicodeError):
        return None
    finally:
        if fd is not None:
            os.close(fd)


def qualify(snapshot, peername, adapters, internal_url, host, headers, install_ids, *, now=None):
    if snapshot is None:
        return None
    record, fingerprint, stamp = snapshot
    now = time.time() if now is None else now
    try:
        if set(record) != _FIELDS or type(record["version"]) is not int or record["version"] != 1:
            return None
        if record["source_preserved"] is not True or record["proxies_excluded"] is not True:
            return None
        if not isinstance(record["ha_install_id"], str) or record["ha_install_id"] not in install_ids:
            return None
        if record["internal_origin"] != internal_url or canonical_origin(record["internal_origin"]) is None:
            return None
        if record["interface_digest"] != interface_digest(adapters):
            return None
        for key in ("evidence_sha256", "interface_digest"):
            value = record[key]
            if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
                return None
        start, end = record["qualified_at"], record["expires_at"]
        if type(start) is not int or type(end) is not int or not start <= now < end or not 0 < end - start <= 86400:
            return None
        peer = ip_address(str(peername[0]).split("%", 1)[0])
        if peer.version == 6 and peer.ipv4_mapped:
            peer = peer.ipv4_mapped
        if not isinstance(record["allowed_peers"], list) or not 1 <= len(record["allowed_peers"]) <= 64:
            return None
        if not isinstance(record["excluded_peers"], list) or not 1 <= len(record["excluded_peers"]) <= 64:
            return None
        for field in ("allowed_peers", "excluded_peers"):
            values = record[field]
            if any(not isinstance(value, str) or "%" in value for value in values) or len(set(values)) != len(values):
                return None
        allowed = [ip_network(value, strict=True) for value in record["allowed_peers"]]
        excluded = [ip_address(value) for value in record["excluded_peers"]]
        if any(net.prefixlen != net.max_prefixlen for net in allowed):
            return None
        if peer in excluded or not any(peer in net for net in allowed if peer.version == net.version):
            return None
        if not direct_local_allowed(peername, adapters, internal_url, host, headers):
            return None
    except (ValueError, TypeError, KeyError, IndexError):
        return None
    return {"fingerprint": fingerprint, "ha_install_id": record["ha_install_id"], "expires_at": end, "stamp": stamp}
