"""Additive producer metadata; discovery never grants transport authority."""

import json

from .hybrid_local_policy import transport_security_policy

FRAME_LIMIT = 65_536


def bounded_frame(item):
    """Bound server frames without inventing or truncating private projections."""
    encoded = json.dumps(item, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    if len(encoded.encode()) <= FRAME_LIMIT:
        return encoded
    receipt = (item.get("result") or {}).get("operation_receipt")
    minimal = {k: item[k] for k in ("id", "connection_id", "type")}
    if receipt is not None:
        minimal.update(
            success=receipt["phase"] == "confirmed",
            status=item["status"],
            result={
                "operation_receipt": {**receipt, "result_available": False},
                "result_available": False,
            },
        )
    else:
        minimal.update(success=False, status=413, error={"code": "projection_too_large"})
    return json.dumps(minimal, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def hybrid_transport_capability():
    return {
        "available": True,
        "version": 1,
        "requires_authenticated_tls": True,
        "transport_security": transport_security_policy(),
        "client_types": ["ios", "macos", "watchos"],
        "audience": "paired_owner_actions",
        "path": "/api/djconnect/v1/actions/paired",
        "auth": "paired_device_first_frame",
        "ha_credentials_issued": False,
        "commands": ["djconnect/read", "djconnect/operation/execute", "djconnect/operation/status",
                     "djconnect/profile/settings/update", "djconnect/profile/settings/subscribe"],
        "context_path": "/api/djconnect/v1/transport/context",
        "operation_path": "/api/djconnect/v1/transport/operation",
        "status_path": "/api/djconnect/v1/transport/operation/status",
        "recovery_path": "/api/djconnect/v1/session/broadcast/recovery",
        "lease_seconds": 300,
        "auth_timeout_seconds": 5,
        "revocation_check_seconds": 1,
        "heartbeat_seconds": 15,
        "frame_bytes": FRAME_LIMIT,
        "pending_limit": 8,
        "outgoing_queue_limit": 64,
        "connection_request_limit": 256,
        "connection_limit": 16,
        "paired_device_connection_limit": 2,
        "operation_identity": "uuidv7",
        "operation_lifetime_ms": 300000,
        "after_send_retry": "reconcile_original_operation_only",
        "cross_origin_redirects": "forbidden",
        "browser_origin": "same_https_origin_only",
        "native_adoption": "separate_consumer_qualification",
    }
