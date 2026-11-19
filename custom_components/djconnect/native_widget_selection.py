"""Bind a WidgetKit first key to the durable owner of the original pair."""

from dataclasses import dataclass, field
import hmac
import json
from pathlib import Path
import re

from .surface_push_contract import require


def _matches_storage(path, key, version, expected):
    try:
        with Path(path).open("rb") as stream:
            saved = json.load(stream)
        return (saved["key"] == key and saved["version"] == version
                and saved["data"] == expected)
    except (OSError, KeyError, ValueError, TypeError):
        return False


@dataclass(frozen=True, repr=False)
class WidgetEnrollmentAuthority:
    snapshot: object
    bindings: dict
    public_key_spki: bytes
    sign: object = field(repr=False)

    def current(self):
        return self.snapshot.current()


class WidgetEnrollmentSelection:
    """Use explicitly selected Core key custody and a separate binding key."""

    def __init__(self, binding_key, signing_key):
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

        require(type(binding_key) is bytes and len(binding_key) == 32
                and isinstance(signing_key, ec.EllipticCurvePrivateKey)
                and isinstance(signing_key.curve, ec.SECP256R1),
                "native_widget_key_unavailable", 503)
        self._binding_key = binding_key
        self._signing_key = signing_key
        self._spki = signing_key.public_key().public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo)

    def _sign(self, message):
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature

        r, s = decode_dss_signature(self._signing_key.sign(message, ec.ECDSA(hashes.SHA256())))
        return r.to_bytes(32, "big") + s.to_bytes(32, "big")

    async def capture(self, pair, *, channel):
        from .domain.storage import STORE_KEY, STORE_VERSION, household_to_storage
        from .profile_observation import capture_source_committed
        from .profile_privacy import resolve_profile_privacy_policy

        require(channel == "widgetkit" and pair.current(), "native_pair_changed", 403)
        snapshot = capture_source_committed(pair.hass)
        require(snapshot is not None, "native_widget_owner_unavailable", 503)
        device_id, client_type = pair.coordinates[:2]
        device = snapshot.household.devices.get(device_id)
        require(device is not None and device.client_type == client_type
                and str(device.pairing_state) == "paired"
                and re.fullmatch(r"[0-9a-f]{32}", device.binding_generation or ""),
                "native_widget_owner_unavailable", 403)
        profile = snapshot.household.profiles.get(device.linked_profile_id)
        require(profile is not None and str(profile.state) == "active"
                and str(profile.privacy_mode) == "normal"
                and resolve_profile_privacy_policy(profile, {}).allow_personal_read,
                "native_widget_owner_unavailable", 403)
        saved = await pair.hass.async_add_executor_job(
            _matches_storage, snapshot.original.store.path, STORE_KEY, STORE_VERSION,
            household_to_storage(snapshot.household))
        require(saved and snapshot.current() and pair.current(), "native_widget_owner_unavailable", 503)
        acknowledgement = pair.acknowledgement
        common = (acknowledgement.instance_id, acknowledgement.auth_generation)
        preimages = {
            "pairing_generation": ("djc-native-pair-generation/1", *common),
            "pair_binding": ("djc-native-pair-binding/1", *common, pair.registration.binding),
            "owner_binding": ("djc-native-owner-binding/1", *common, profile.profile_id, device.binding_generation),
            "device_binding": ("djc-native-device-binding/1", *common, device_id, client_type),
        }
        bindings = {field: hmac.digest(self._binding_key, json.dumps(values, ensure_ascii=True, separators=(",", ":")).encode("ascii"), "sha256").hex()
                    for field, values in preimages.items()}
        return WidgetEnrollmentAuthority(snapshot, bindings, self._spki, self._sign)
