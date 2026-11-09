"""Select the first-key service only from the HA-dev process configuration."""

import base64
import json
import os
from pathlib import Path
import re
import stat
import time

from .const import DOMAIN
from .native_pair_enrollment import KEY, NativePairEnrollment
from .native_widget_selection import WidgetEnrollmentSelection
from .surface_issuer_transport import FirstKeyHTTPS, WidgetPublisherHTTPS
from .surface_push_contract import SurfacePushError, require

_CONFIG_ENV = "DJCONNECT_HA_DEV_WIDGET_ENROLLMENT_FILE"
_MAX_FILE = 8192
_ACCESS_KEYS = {"origin", "client_id", "client_secret"}


def _unique_fields(items):
    result = dict(items)
    if len(result) != len(items):
        raise ValueError
    return result


def _read_config(path):
    if not Path(path).is_absolute():
        raise ValueError
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
                or stat.S_IMODE(info.st_mode) not in (0o400, 0o600)
                or not 0 < info.st_size <= _MAX_FILE):
            raise ValueError
        raw = stream.read(_MAX_FILE + 1)
    if len(raw) != info.st_size:
        raise ValueError
    return json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_fields)


def _access_callback(config, expires_at_ms, deadline):
    require(type(config) is dict and set(config) == _ACCESS_KEYS
            and all(type(config[key]) is str and re.fullmatch(r"[!-~]{1,256}", config[key])
                    for key in ("client_id", "client_secret")),
            "native_widget_runtime_invalid", 503)
    origin = config["origin"]
    headers = {"CF-Access-Client-Id": config["client_id"], "CF-Access-Client-Secret": config["client_secret"]}

    def selected_headers(request_origin):
        require(request_origin == origin and time.time_ns() // 1_000_000 < expires_at_ms
                and time.monotonic() < deadline, "native_widget_runtime_unavailable", 503)
        return headers.copy()

    return selected_headers


def _service(hass, path):
    from cryptography.exceptions import UnsupportedAlgorithm
    from cryptography.hazmat.primitives.serialization import load_der_private_key

    config = _read_config(path)

    require(type(config) is dict and set(config) == {
        "purpose", "expires_at_ms", "core", "publisher", "binding_key_b64", "signing_key_der_b64",
    } and config["purpose"] == "ha-dev-widget-first-key-v1", "native_widget_runtime_invalid", 503)
    expiry = config["expires_at_ms"]
    now = time.time_ns() // 1_000_000
    require(type(expiry) is int and now < expiry < 2**53, "native_widget_runtime_invalid", 503)
    deadline = time.monotonic() + (expiry - now) / 1000
    core, publisher = config["core"], config["publisher"]
    core_headers = _access_callback(core, expiry, deadline)
    publisher_headers = _access_callback(publisher, expiry, deadline)
    require(core["origin"] != publisher["origin"] and core["client_id"] != publisher["client_id"]
            and core["client_secret"] != publisher["client_secret"],
            "native_widget_runtime_invalid", 503)
    key_bytes = base64.b64decode(config["signing_key_der_b64"], validate=True)
    try:
        signing_key = load_der_private_key(key_bytes, None)
    except UnsupportedAlgorithm:
        raise ValueError("Unsupported WidgetKit signing key") from None
    selection = WidgetEnrollmentSelection(
        base64.b64decode(config["binding_key_b64"], validate=True), signing_key)

    return NativePairEnrollment(
        hass, FirstKeyHTTPS(core["origin"], machine_headers=core_headers), selection,
        publisher=WidgetPublisherHTTPS(publisher["origin"], machine_headers=publisher_headers),
    )


async def select_from_runtime(hass):
    """Leave all native enrollment routes closed if HA-dev has no valid assignment."""
    path = os.environ.get(_CONFIG_ENV)
    domain = hass.data.setdefault(DOMAIN, {})
    if not path or KEY in domain:
        return
    try:
        service = await hass.async_add_executor_job(_service, hass, path)
    except (OSError, ValueError, TypeError, RecursionError, SurfacePushError):
        return
    domain.setdefault(KEY, service)
