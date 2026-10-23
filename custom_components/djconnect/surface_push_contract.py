"""Closed native token roles; registration is never content or start authority.

Availability comes from the original Apple SDK26 DocC declarations, not a
claim that a native target, relay, installed build or APNs path is qualified.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import re

from .client_identity import device_id_matches_client_type
from .transport_operations import FUTURE_SKEW_MS, LIFETIME_MS, OperationError, operation_created_ms

VERSION = 1
BASE = "/api/djconnect/v1/push/surface"
ROLES = ("widget", "live_activity_update", "live_activity_start")
PLATFORM_CLIENT = {
    "ios": "ios",
    "ipados": "ios",
    "macos": "macos",
    "maccatalyst": "ios",
    "watchos": "watchos",
    "visionos": "ios",
    "tvos": "ios",
}
FIELDS = frozenset(
    {
        "contract_version",
        "device_id",
        "client_type",
        "operation_id",
        "session_id",
        "platform",
        "os_version",
        "token_role",
        "target",
        "apns_token",
        "apns_environment",
        "expected_registration",
        "consent",
    }
)
CONSENT_FIELDS = frozenset(
    {
        "background_read",
        "os_snapshot_cache",
        "locked_display",
        "external_push_content",
        "allow_remote_start",
    }
)
IDENTIFIER = re.compile(r"[A-Za-z0-9_-]{1,128}\Z")
BUNDLE = re.compile(r"[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+\Z")
TOKEN = re.compile(r"[0-9a-f]{32,4096}\Z")


class SurfacePushError(ValueError):
    """Static codes only; no native token, owner identity, text or URL."""

    def __init__(self, code, status=400):
        super().__init__(code)
        self.code, self.status = code, status


def require(condition, code, status=400):
    if not condition:
        raise SurfacePushError(code, status)


def _version(value):
    require(
        type(value) is str and re.fullmatch(r"[1-9][0-9]?(?:\.[0-9]{1,2}){1,2}", value) is not None,
        "invalid_surface_os_version",
    )
    parts = tuple(int(p) for p in value.split("."))
    return (*parts, *(0 for _ in range(3 - len(parts))))


def native_support(platform, role, version):
    """Native transport availability; mirroring is not token destination parity."""
    if (
        type(platform) is not str
        or type(role) is not str
        or platform not in PLATFORM_CLIENT
        or role not in ROLES
    ):
        return False
    value = _version(version)
    if role == "widget":
        return platform != "tvos" and value >= (26, 0, 0)
    if platform not in {"ios", "ipados"}:
        return False
    return value >= (
        (17, 2, 0)
        if role == "live_activity_start"
        else (17, 0, 0)
        if platform == "ipados"
        else (16, 1, 0)
    )


def platform_matrix():
    return {
        platform: {
            "paired_client_type": client,
            "widget_push_minimum": "26.0" if platform != "tvos" else None,
            "live_activity_update_minimum": ("16.1" if platform == "ios" else "17.0")
            if platform in {"ios", "ipados"}
            else None,
            "live_activity_start_minimum": "17.2" if platform in {"ios", "ipados"} else None,
            "live_activity_presentation": "native"
            if platform in {"ios", "ipados"}
            else "system_mirror_only"
            if platform in {"macos", "watchos"}
            else "unsupported",
            "native_target_qualification": "separate",
        }
        for platform, client in PLATFORM_CLIENT.items()
    }


def capability():
    return {
        "version": VERSION,
        "available": False,
        "reason": "requires_current_operator_enrolled_purpose",
        "context_path": BASE + "/context",
        "background_read_path": BASE + "/read",
        "register_path": BASE + "/register",
        "revoke_path": BASE + "/revoke",
        "status_path": BASE + "/status",
        "authentication": "paired_device_bearer",
        "roles": list(ROLES),
        "platforms": platform_matrix(),
        "ordinary_app_registration": "independent",
        "registration_starts_activity": False,
        "dynamic_island": "live_activity_presentation",
        "background_read": "separately_scoped_original_grant",
        "relay_readiness": "requires_matching_relay_contract",
        "native_acceptance": "separate",
    }


@dataclass(frozen=True)
class RegistrationIntent:
    """Immutable validated input; never print or persist the native token."""

    encoded: str = field(repr=False)
    apns_token: str = field(repr=False)
    fingerprint: str

    def metadata(self):
        return json.loads(self.encoded)

    def relay_registration(self):
        return {**self.metadata(), "apns_token": self.apns_token}


def validate_registration(payload, *, now_ms):
    require(type(payload) is dict and set(payload) == FIELDS, "invalid_surface_registration")
    require(
        type(payload["contract_version"]) is int and payload["contract_version"] == VERSION,
        "unsupported_surface_push_version",
    )
    role, platform = payload["token_role"], payload["platform"]
    require(
        type(role) is str
        and role in ROLES
        and type(platform) is str
        and platform in PLATFORM_CLIENT,
        "unsupported_surface_platform",
    )
    require(
        payload["client_type"] == PLATFORM_CLIENT[platform]
        and type(payload["device_id"]) is str
        and device_id_matches_client_type(payload["device_id"], payload["client_type"]),
        "invalid_surface_identity",
    )
    require(native_support(platform, role, payload["os_version"]), "surface_not_supported", 409)
    require(
        type(payload["session_id"]) is str
        and IDENTIFIER.fullmatch(payload["session_id"]) is not None,
        "invalid_surface_session",
    )
    try:
        created = operation_created_ms(payload["operation_id"])
    except OperationError:
        raise SurfacePushError("invalid_operation_id") from None
    require(type(now_ms) is int and now_ms >= 0, "invalid_surface_clock")
    require(created <= now_ms + FUTURE_SKEW_MS, "operation_clock_unqualified", 409)
    require(now_ms < created + LIFETIME_MS, "operation_expired", 409)
    token = payload["apns_token"]
    require(
        type(token) is str and TOKEN.fullmatch(token) is not None and len(token) % 2 == 0,
        "invalid_surface_push_token",
    )
    require(
        type(payload["apns_environment"]) is str
        and payload["apns_environment"] in {"sandbox", "production"},
        "invalid_surface_push_environment",
    )
    target = payload["target"]
    fields = {"instance_id", "app_bundle_id"} | (
        {"extension_bundle_id", "widget_kind"}
        if role == "widget"
        else {"activity_id", "attributes_type"}
        if role == "live_activity_update"
        else {"attributes_type"}
    )
    require(type(target) is dict and set(target) == fields, "invalid_surface_target")
    for key, value in target.items():
        matcher = BUNDLE if key.endswith("bundle_id") else IDENTIFIER
        require(
            type(value) is str and len(value) <= 200 and matcher.fullmatch(value) is not None,
            "invalid_surface_target",
        )
    expected = payload["expected_registration"]
    require(
        expected is None
        or (
            type(expected) is dict
            and set(expected) == {"registration_id", "generation", "revision"}
            and all(
                type(expected[k]) is str and IDENTIFIER.fullmatch(expected[k]) is not None
                for k in ("registration_id", "generation")
            )
            and type(expected["revision"]) is int
            and expected["revision"] >= 1
        ),
        "invalid_surface_registration_revision",
    )
    consent = payload["consent"]
    require(
        type(consent) is dict
        and set(consent) == CONSENT_FIELDS
        and all(type(v) is bool for v in consent.values()),
        "invalid_surface_consent",
    )
    require(
        consent["os_snapshot_cache"] and (role == "widget" or consent["locked_display"]),
        "surface_consent_required",
        403,
    )
    require(not consent["allow_remote_start"], "remote_start_requires_separate_presentation", 403)
    require(
        role != "widget" or (consent["background_read"] and not consent["external_push_content"]),
        "invalid_widget_delivery_consent",
    )
    metadata = {k: v for k, v in payload.items() if k != "apns_token"}
    encoded = json.dumps(metadata, sort_keys=True, separators=(",", ":"))
    fingerprint = hashlib.sha256((encoded + "\0" + token).encode()).hexdigest()
    return RegistrationIntent(encoded, token, fingerprint)


def widget_notification():
    """A reload signal cannot carry music, private text, credentials or actions."""
    return {"aps": {"content-changed": True}}
