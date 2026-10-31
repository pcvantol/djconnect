"""Actual HA-admin preparation, not installation custody or an effect grant.

Only a normal HA bearer session can prepare this selected loaded entry context.
The RAM receipt cannot generate/sign, enroll a principal or authorize a device.
An entry's existing ha_install_id remains metadata, not a new trust root.
"""
from __future__ import annotations

import asyncio
from fractions import Fraction
import json
import math
import re
import secrets
import time
import uuid
import weakref

from aiohttp import web
from homeassistant.components.http import HomeAssistantView

KEY = "installation_management_preparations"
PATH = "/api/djconnect/v1/installation/{entry_id}/management/prepare"
MAX_BODY = 4096
MAX_PENDING = 16
MAX_OPERATIONS = 64
AGE_SECONDS = 120
SAFE = 9007199254740991
HEADERS = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer",
           "X-Content-Type-Options": "nosniff"}


class ManagementError(ValueError):
    def __init__(self, code="management_preparation_unavailable", status=503):
        super().__init__(code)
        self.code, self.status = code, status


def _require(ok, code="management_preparation_unavailable", status=503):
    if not ok:
        raise ManagementError(code, status)


def _auth(hass, request):
    from homeassistant.auth import AuthManager, models
    from homeassistant.components.http.const import (
        KEY_AUTHENTICATED, KEY_HASS_REFRESH_TOKEN_ID, KEY_HASS_USER,
    )

    values = request.headers.getall("Authorization", [])
    _require(len(values) == 1 and type(values[0]) is str
        and len(values[0]) <= 4096 and re.fullmatch(
            r"Bearer [A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", values[0]),
        "management_authentication_required", 401)
    manager = hass.auth
    _require(isinstance(manager, AuthManager), "management_authentication_required", 401)
    token = values[0][7:]
    original = manager.async_validate_access_token(token)  # Synchronous HA callback.
    _require(original is not None and request.get(KEY_AUTHENTICATED) is True
        and request.get(KEY_HASS_USER) is original.user
        and request.get(KEY_HASS_REFRESH_TOKEN_ID) == original.id,
        "management_authentication_required", 401)
    user = original.user
    # Deliberate normal-session-only policy. A normal token is NOT proof of
    # recent human presence, MFA, physical acceptance or a browser identity.
    _require(original.token_type == models.TOKEN_TYPE_NORMAL
        and user.is_active and user.is_admin and not user.system_generated,
        "management_admin_required", 403)
    return manager, original, user, token


def _configuration(entry):
    return {**entry.data, **entry.options}


def _user_state(user):
    return (user.is_owner, user.is_active, user.system_generated, user.local_only,
            tuple((id(group), group.id) for group in user.groups))


def _samples():
    """Production local clocks; private deterministic seam for isolated tests."""
    return time.time(), time.monotonic()


def retire_runtime_preparations(runtime):
    """Negative-only hook, called before existing runtime authority changes."""
    scopes = getattr(runtime, "_installation_management_scopes", None)
    if type(scopes) is weakref.WeakSet:
        for scope in tuple(scopes):
            if type(scope) is _Scope:
                scope.retire()


class _Scope:
    """Server-owned original management context; never a custody owner port."""

    def __init__(self, hass, request, entry_id):
        from . import DJConnectRuntime
        from .client_retirement import is_retired_entry

        self._retired = False
        self._cleanup_incomplete = False
        self._unsubscribers = []
        self._timer = None
        self._registry = None
        self._runtime_scopes = None
        self._handle = self._operation = None
        self._preparing = True
        self._task = asyncio.current_task()
        self._wall, self._mono = _samples()  # Before ANY await.
        _require(all(type(v) in (int, float) and math.isfinite(v)
                     for v in (self._wall, self._mono)) and self._wall > 0 and self._mono >= 0)
        self._last_wall, self._last_mono = self._wall, self._mono
        self.expires_ms = math.floor(Fraction(self._wall) * 1000) + AGE_SECONDS * 1000
        _require(0 < self.expires_ms <= SAFE)
        self.hass = hass
        self.manager, self.refresh, self.user, self._token = _auth(hass, request)
        self._user_state = _user_state(self.user)
        _require(type(entry_id) is str and re.fullmatch(r"[A-Za-z0-9_-]{1,128}", entry_id),
                 "invalid_request", 400)
        self.entry = hass.config_entries.async_get_entry(entry_id)
        _require(self.entry is not None and self.entry.domain == "djconnect"
            and self.entry.disabled_by is None and self.entry.state.value == "loaded"
            and not is_retired_entry(self.entry), "management_entry_unavailable", 409)
        self.runtime = hass.data.get("djconnect", {}).get(entry_id)
        _require(isinstance(self.runtime, DJConnectRuntime) and self.runtime.entry is self.entry,
                 "management_entry_unavailable", 409)
        self.data, self.options = self.entry.data, self.entry.options
        self._installation_metadata = _configuration(self.entry).get("ha_install_id")
        _require(type(self._installation_metadata) is str and re.fullmatch(
            r"[A-Za-z0-9_-]{1,160}", self._installation_metadata),
            "management_entry_unavailable", 409)
        try:
            scopes = getattr(self.runtime, "_installation_management_scopes", None)
            if scopes is None:
                scopes = weakref.WeakSet()
                self.runtime._installation_management_scopes = scopes
            _require(type(scopes) is weakref.WeakSet)
            self._runtime_scopes = scopes
            scopes.add(self)  # Pending AND prepared contexts, before first await.
            self._subscribe()
            self.require_current()
        except BaseException:
            self.retire()
            raise

    def _subscribe(self):
        from homeassistant.auth import EVENT_USER_REMOVED, EVENT_USER_UPDATED
        from homeassistant.core import callback

        user_id = self.user.id

        @callback
        def changed(event):
            if event.data.get("user_id") == user_id:
                self.retire()  # Irreversible negative fence, including update ABA.

        @callback
        def revoked():
            # HA already popped this token's callback set and is iterating it.
            # Calling its unsubscribe here would mutate that same live set.
            # Discard our cleanup reference, then fence the scope synchronously.
            if revoke_unsubscribe in self._unsubscribers:
                self._unsubscribers.remove(revoke_unsubscribe)
            self.retire()

        revoke_unsubscribe = self.manager.async_register_revoke_token_callback(
            self.refresh.id, revoked)
        self._unsubscribers.append(revoke_unsubscribe)
        self._unsubscribers.append(self.hass.bus.async_listen(EVENT_USER_UPDATED, changed))
        self._unsubscribers.append(self.hass.bus.async_listen(EVENT_USER_REMOVED, changed))
        self._timer = self.hass.loop.call_later(AGE_SECONDS, self.retire)

    def require_current(self, request=None):
        from .client_retirement import is_retired_entry

        try:
            _require(not self._retired)
            task = asyncio.current_task()
            if task is not None and task.cancelling():
                raise asyncio.CancelledError
            _require(task is not None and (not self._preparing or task is self._task))
            _require(not self.hass.is_stopping and self.hass.auth is self.manager
                and self.manager.async_get_refresh_token(self.refresh.id) is self.refresh
                and self.manager.async_validate_access_token(self._token) is self.refresh
                and self.refresh.user is self.user and self.user.is_active
                and self.user.is_admin and not self.user.system_generated
                and _user_state(self.user) == self._user_state)
            _require(self.hass.config_entries.async_get_entry(self.entry.entry_id) is self.entry
                and self.entry.disabled_by is None and self.entry.state.value == "loaded"
                and not is_retired_entry(self.entry)
                and self.hass.data.get("djconnect", {}).get(self.entry.entry_id) is self.runtime
                and self.runtime.entry is self.entry and self.entry.data is self.data
                and self.entry.options is self.options
                and getattr(self.runtime, "_installation_management_scopes", None) is self._runtime_scopes
                and self in self._runtime_scopes
                and _configuration(self.entry).get("ha_install_id") == self._installation_metadata)
            if request is not None:
                manager, refresh, user, _ = _auth(self.hass, request)
                _require(manager is self.manager and refresh is self.refresh and user is self.user)
            wall, mono = _samples()
            _require(all(type(v) in (int, float) and math.isfinite(v) for v in (wall, mono))
                and wall >= self._last_wall and mono >= self._last_mono
                and Fraction(wall) * 1000 < self.expires_ms
                and Fraction(mono) - Fraction(self._mono) < AGE_SECONDS)
            self._last_wall, self._last_mono = wall, mono
        except asyncio.CancelledError:
            self.retire()
            raise
        except Exception:
            self.retire()
            raise ManagementError("management_preparation_closed", 410) from None

    def retire(self):
        if self._retired:
            return
        self._retired = True  # BEFORE callbacks/unsubscription or other work.
        if self._runtime_scopes is not None:
            self._runtime_scopes.discard(self)
        if self._timer is not None:
            self._timer.cancel()
        for unsubscribe in self._unsubscribers:
            try:
                unsubscribe()
            except Exception:
                # A cleanup failure cannot stop this or a sibling's negative
                # retirement. The original context remains irreversibly closed.
                self._cleanup_incomplete = True
        self._unsubscribers.clear()
        if self._registry is not None:
            self._registry._pending.discard(self)
            if self._operation is not None:
                self._registry._operations[self._operation] = None  # Spent RAM marker.
            if self._handle is not None:
                self._registry._handles.pop(self._handle, None)
        self._token = ""
        self.user = self.refresh = self.manager = None
        self.entry = self.runtime = self.data = self.options = self._task = None
        self._runtime_scopes = None

    def prepared(self):
        self.require_current()
        original_task, weak = self._task, weakref.ref(self)

        def completed(task):
            scope = weak()
            if scope is not None and (task.cancelled() or task.cancelling()):
                scope.retire()

        original_task.add_done_callback(completed)
        self._preparing = False
        self._task = None


class ManagementPreparations:
    """Bounded RAM preparation, explicitly NOT SQL once/effect acknowledgement."""

    def __init__(self, hass):
        from homeassistant.const import EVENT_HOMEASSISTANT_STOP
        from homeassistant.core import callback

        self.hass, self.closed = hass, False
        self._pending, self._operations, self._handles = set(), {}, {}

        @callback
        def stop(_event):
            self.closed = True
            for scope in tuple(self._pending | set(self._handles.values())):
                scope.retire()

        self._unsubscribe = hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, stop)

    def pending(self, scope):
        _require(not self.closed and len(self._pending) < MAX_PENDING,
                 "management_preparation_capacity", 429)
        scope.require_current()
        scope._registry = self
        self._pending.add(scope)

    def claim(self, scope, operation):
        _require(not self.closed and scope in self._pending)
        scope.require_current()
        _require(operation not in self._operations, "management_operation_exists", 409)
        _require(len(self._operations) < MAX_OPERATIONS, "management_preparation_capacity", 429)
        scope._operation = operation
        self._operations[operation] = scope  # Reserve BEFORE publishing any handle.
        scope._handle = "djcmgmt_" + secrets.token_urlsafe(32)
        self._handles[scope._handle] = scope

    def validate_preparation(self, handle, request):
        """Same fresh HA auth AND original context. Does not authorize an effect."""
        _require(not self.closed and type(handle) is str)
        scope = self._handles.get(handle)
        _require(scope is not None and not scope._preparing)
        scope.require_current(request)
        # Return None, never the context/token or a callable effect capability.


def parse(raw):
    def pairs(items):
        out = {}
        for key, value in items:
            _require(key not in out, "invalid_request", 400)
            out[key] = value
        return out

    def constant(_value):
        raise ManagementError("invalid_request", 400)

    try:
        value = json.loads(raw.decode("utf-8", errors="strict"),
                           object_pairs_hook=pairs, parse_constant=constant)
        _require(type(value) is dict and set(value) == {
            "contract_version", "operation_id", "action", "policy_id", "acknowledgement"},
            "invalid_request", 400)
        _require(type(value["contract_version"]) is int and value["contract_version"] == 1
            and value["action"] == "prepare_custody"
            and value["policy_id"] == "software_p256_ha_file_v1"
            and value["acknowledgement"] == "preparation_only_no_key_effect",
            "invalid_request", 400)
        operation = value["operation_id"]
        _require(type(operation) is str and str(uuid.UUID(operation)) == operation
            and uuid.UUID(operation).version == 4, "invalid_request", 400)
        return operation
    except (ValueError, UnicodeError, TypeError, RecursionError, AttributeError):
        raise ManagementError("invalid_request", 400) from None


class InstallationManagementPrepareView(HomeAssistantView):
    url = PATH
    name = "api:djconnect:installation:management:prepare"
    requires_auth = True

    def __init__(self, hass):
        self.hass = hass

    @staticmethod
    def response(value, status=200):
        return web.Response(text=json.dumps(value, allow_nan=False), status=status,
                            content_type="application/json", headers=HEADERS)

    async def post(self, request, entry_id):
        scope = registry = None
        committed = False
        try:
            _require(not request.query_string and request.content_type == "application/json"
                and (request.charset or "utf-8").lower() in {"utf-8", "utf8"}
                and request.headers.get("Content-Encoding", "identity").lower() == "identity",
                "invalid_request", 400)
            _require(request.content_length is None or request.content_length <= MAX_BODY,
                     "request_too_large", 413)
            scope = _Scope(self.hass, request, entry_id)  # Original context BEFORE await.
            domain = self.hass.data["djconnect"]
            if KEY not in domain:
                domain[KEY] = ManagementPreparations(self.hass)
            registry = domain[KEY]
            _require(type(registry) is ManagementPreparations and registry.hass is self.hass)
            registry.pending(scope)
            raw = bytearray()
            async with asyncio.timeout(5):
                while True:
                    chunk = await request.content.read(min(1024, MAX_BODY + 1 - len(raw)))
                    scope.require_current()
                    if not chunk:
                        break
                    raw.extend(chunk)
                    _require(len(raw) <= MAX_BODY, "request_too_large", 413)
            operation = parse(bytes(raw))
            registry.claim(scope, operation)
            response = self.response({"success": True, "contract_version": 1,
                "state": "prepared", "classification": "HA_ADMIN_PREPARATION_ONLY",
                "operation_id": operation, "handle": scope._handle,
                "expires_at_ms": scope.expires_ms, "execution_available": False})
            scope.prepared()  # Final synchronous check AFTER response serialization.
            committed = True
            return response
        except asyncio.CancelledError:
            raise
        except TimeoutError:
            return self.response({"success": False, "error": "management_request_timeout"}, 408)
        except ManagementError as exc:
            return self.response({"success": False, "error": exc.code}, exc.status)
        finally:
            if registry is not None and scope is not None:
                registry._pending.discard(scope)
            if scope is not None and not committed:
                scope.retire()
