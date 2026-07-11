"""Thin Home Assistant runtime adapter for verification execution."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import platform
import socket
import ssl
import struct
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from tools.verification.adapters import VerificationAdapter
from tools.verification.evidence import LogManager
from tools.verification.models import ArtifactMetadata, EnvironmentSnapshot, EvidenceItem, PrimitiveAction, PrimitiveResult, ResourceState

APPROVED_STORAGE_KEYS = {
    "djconnect_profile_platform",
    "djconnect_music_dna",
    "djconnect_ask_dj_history",
}

FIXTURE_PREFIXES = (
    "verification-profile-",
    "verification-device-",
    "verification-area-",
    "verification-backend-",
    "verification-household-",
)


class HomeAssistantAdapterError(RuntimeError):
    """Base adapter-level error."""


class ConnectionFailed(HomeAssistantAdapterError):
    """The Home Assistant runtime could not be reached."""


class AuthenticationFailed(HomeAssistantAdapterError):
    """The Home Assistant runtime rejected authentication."""


class CapabilityUnavailable(HomeAssistantAdapterError):
    """The requested primitive is not available in this environment."""


class FixtureFailed(HomeAssistantAdapterError):
    """A fixture operation was rejected or failed."""


@dataclass(frozen=True)
class HomeAssistantAdapterConfig:
    base_url: str = "http://localhost:8123"
    token: str = ""
    storage_dir: Path | None = None
    log_path: Path | None = None
    timeout_seconds: float = 10.0
    allow_destructive: bool = False
    fixture_namespace: str = "verification"

    @classmethod
    def from_environment(cls, root: Path | None = None) -> "HomeAssistantAdapterConfig":
        storage_dir = os.getenv("DJCONNECT_VERIFICATION_HA_STORAGE_DIR")
        log_path = os.getenv("DJCONNECT_VERIFICATION_HA_LOG_PATH")
        return cls(
            base_url=os.getenv("DJCONNECT_VERIFICATION_HA_URL", "http://localhost:8123").rstrip("/"),
            token=os.getenv("DJCONNECT_VERIFICATION_HA_TOKEN", ""),
            storage_dir=_resolve_optional(root, storage_dir),
            log_path=_resolve_optional(root, log_path),
            timeout_seconds=float(os.getenv("DJCONNECT_VERIFICATION_HA_TIMEOUT", "10")),
            allow_destructive=_truthy(os.getenv("DJCONNECT_VERIFICATION_ALLOW_DESTRUCTIVE")),
            fixture_namespace=os.getenv("DJCONNECT_VERIFICATION_FIXTURE_NAMESPACE", "verification"),
        )


@dataclass(frozen=True)
class HTTPResult:
    status: int
    headers: dict[str, str]
    body: Any
    duration_seconds: float
    url: str
    method: str


@dataclass
class HomeAssistantFixtureStore:
    namespace: str = "verification"
    fixtures: dict[str, dict[str, Any]] = field(default_factory=dict)

    def create(self, kind: str, name: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        fixture_id = f"{self.namespace}-{kind}-{name}"
        if not fixture_id.startswith(FIXTURE_PREFIXES):
            raise FixtureFailed(f"fixture id is outside verification namespace: {fixture_id}")
        fixture = {"id": fixture_id, "kind": kind, "name": name, "payload": payload or {}}
        self.fixtures[fixture_id] = fixture
        return fixture

    def remove(self, fixture_id: str) -> dict[str, Any]:
        if not fixture_id.startswith(FIXTURE_PREFIXES):
            raise FixtureFailed(f"refusing to remove non-verification fixture: {fixture_id}")
        existed = fixture_id in self.fixtures
        self.fixtures.pop(fixture_id, None)
        return {"id": fixture_id, "removed": existed}


class HomeAssistantVerificationAdapter(VerificationAdapter):
    """Execute runtime primitives against Home Assistant without assertions."""

    name = "home_assistant"

    def __init__(
        self,
        config: HomeAssistantAdapterConfig | None = None,
        *,
        transport: Any | None = None,
        fixture_store: HomeAssistantFixtureStore | None = None,
    ) -> None:
        self.config = config or HomeAssistantAdapterConfig.from_environment()
        self.transport = transport or UrllibHomeAssistantTransport(self.config)
        self.fixtures = fixture_store or HomeAssistantFixtureStore(self.config.fixture_namespace)
        self._logs: list[dict[str, Any]] = []
        self._connected = False

    def initialize(self) -> None:
        self._connected = True
        self._record("initialize", "local", True, {})

    def shutdown(self) -> None:
        self._connected = False
        self._record("shutdown", "local", True, {})

    def health(self) -> dict[str, Any]:
        result = self.execute_rest("GET", "/api/")
        return {
            "ok": result.ok,
            "status": result.data.get("status"),
            "base_url": self.config.base_url,
            "authenticated": bool(self.config.token),
        }

    def version(self) -> PrimitiveResult:
        return self.execute_rest("GET", "/api/config")

    def capabilities(self) -> PrimitiveResult:
        return self.execute_websocket({"id": 1, "type": "djconnect/capabilities"})

    def prepare_environment(self) -> None:
        self._record("prepare_environment", "local", True, {"source": "execution_environment"})

    def launch(self, target: str | None = None) -> PrimitiveResult:
        return PrimitiveResult("launch", True, {"target": target or "home_assistant"})

    def stop(self) -> PrimitiveResult:
        return self.call_service("homeassistant", "stop", {})

    def restart(self) -> PrimitiveResult:
        return self.restart_runtime()

    def restart_runtime(self) -> PrimitiveResult:
        return self.call_service("homeassistant", "restart", {})

    def reload_djconnect(self) -> PrimitiveResult:
        return self.call_service("homeassistant", "reload_config_entry", {"domain": "djconnect"})

    def click(self, target: str, **kwargs: Any) -> PrimitiveResult:
        return PrimitiveResult("click", False, {"target": target, "error": "CapabilityUnavailable"}, message="Home Assistant adapter has no UI click primitive")

    def type(self, text: str, **kwargs: Any) -> PrimitiveResult:
        return PrimitiveResult("type", False, {"error": "CapabilityUnavailable"}, message="Home Assistant adapter has no UI type primitive")

    def execute_service(self, name: str, payload: dict[str, Any] | None = None) -> PrimitiveResult:
        domain, _, service = name.partition(".")
        if not domain or not service:
            return PrimitiveResult("call_service", False, {"error": "ServiceError", "service": name})
        return self.call_service(domain, service, payload or {})

    def call_service(self, domain: str, service: str, payload: dict[str, Any] | None = None) -> PrimitiveResult:
        path = f"/api/services/{domain}/{service}"
        return self.execute_rest("POST", path, payload or {})

    def execute_rest(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> PrimitiveResult:
        started = time.perf_counter()
        try:
            response = self.transport.request(method, path, payload, headers)
            ok = 200 <= response.status < 400
            data = {
                "status": response.status,
                "headers": _redact(response.headers),
                "body": _redact(response.body),
                "duration_seconds": response.duration_seconds,
                "method": response.method,
                "path": path,
            }
            self._record("http_request", "rest", ok, data, started=started)
            return PrimitiveResult("http_request", ok, data)
        except AuthenticationFailed as exc:
            return self._error_result("http_request", "AuthenticationFailed", exc, started)
        except TimeoutError as exc:
            return self._error_result("http_request", "Timeout", exc, started)
        except Exception as exc:
            return self._error_result("http_request", "ConnectionFailed", exc, started)

    def execute_websocket(self, message: dict[str, Any]) -> PrimitiveResult:
        started = time.perf_counter()
        try:
            response = self.transport.websocket(message)
            self._record("websocket_request", "websocket", True, response, started=started)
            return PrimitiveResult("websocket_request", True, _redact(response))
        except CapabilityUnavailable as exc:
            return self._error_result("websocket_request", "CapabilityUnavailable", exc, started)
        except Exception as exc:
            return self._error_result("websocket_request", "WebSocketError", exc, started)

    def wait_for_event(self, event_type: str, timeout_seconds: float | None = None) -> PrimitiveResult:
        return PrimitiveResult(
            "wait_for_event",
            False,
            {"event_type": event_type, "timeout_seconds": timeout_seconds, "error": "CapabilityUnavailable"},
            message="event waiting requires live websocket subscription support",
        )

    def get_state(self, entity_id: str) -> PrimitiveResult:
        return self.execute_rest("GET", f"/api/states/{entity_id}")

    def list_entities(self) -> PrimitiveResult:
        return self.execute_rest("GET", "/api/states")

    def list_devices(self) -> PrimitiveResult:
        return self.execute_rest("GET", "/api/config/device_registry/list")

    def get_device(self, device_id: str) -> PrimitiveResult:
        result = self.list_devices()
        devices = result.data.get("body") if isinstance(result.data, dict) else None
        if isinstance(devices, list):
            result_data = {"device": next((item for item in devices if item.get("id") == device_id), None)}
            return PrimitiveResult("get_device", True, _redact(result_data))
        return PrimitiveResult("get_device", False, {"error": "RegistryUnavailable", "device_id": device_id})

    def list_areas(self) -> PrimitiveResult:
        return self.execute_rest("GET", "/api/config/area_registry/list")

    def get_area(self, area_id: str) -> PrimitiveResult:
        result = self.list_areas()
        areas = result.data.get("body") if isinstance(result.data, dict) else None
        if isinstance(areas, list):
            result_data = {"area": next((item for item in areas if item.get("id") == area_id), None)}
            return PrimitiveResult("get_area", True, _redact(result_data))
        return PrimitiveResult("get_area", False, {"error": "RegistryUnavailable", "area_id": area_id})

    def snapshot_storage(self, key: str = "djconnect_profile_platform") -> PrimitiveResult:
        if key not in APPROVED_STORAGE_KEYS:
            return PrimitiveResult("snapshot_storage", False, {"error": "StorageUnavailable", "key": key})
        if self.config.storage_dir is None:
            return PrimitiveResult("snapshot_storage", False, {"error": "StorageUnavailable", "key": key})
        path = self.config.storage_dir / key
        if not path.exists():
            return PrimitiveResult("snapshot_storage", True, {"key": key, "exists": False, "data": None})
        data = json.loads(path.read_text(encoding="utf-8"))
        return PrimitiveResult("snapshot_storage", True, {"key": key, "exists": True, "data": _redact(data)})

    def compare_storage(self, before: dict[str, Any], after: dict[str, Any]) -> PrimitiveResult:
        return PrimitiveResult(
            "compare_storage",
            True,
            {
                "before_keys": sorted(before.keys()),
                "after_keys": sorted(after.keys()),
                "changed": before != after,
            },
        )

    def create_fixture(self, kind: str, name: str, payload: dict[str, Any] | None = None) -> PrimitiveResult:
        try:
            return PrimitiveResult("create_fixture", True, {"fixture": _redact(self.fixtures.create(kind, name, payload))})
        except FixtureFailed as exc:
            return PrimitiveResult("create_fixture", False, {"error": "FixtureFailed", "message": str(exc)})

    def remove_fixture(self, fixture_id: str) -> PrimitiveResult:
        try:
            return PrimitiveResult("remove_fixture", True, self.fixtures.remove(fixture_id))
        except FixtureFailed as exc:
            return PrimitiveResult("remove_fixture", False, {"error": "FixtureFailed", "message": str(exc)})

    def execute_action(self, action: PrimitiveAction) -> PrimitiveResult:
        name = action.name.lower().replace(" ", "_")
        parameters = action.parameters
        if name in {"collect_environment", "collect_runtime_metadata"}:
            return PrimitiveResult(name, True, _redact(self.collect_environment()))
        if name in {"health", "connect"}:
            return PrimitiveResult(name, True, self.health())
        if name == "capabilities":
            return self.capabilities()
        if name == "snapshot_storage":
            return self.snapshot_storage(str(parameters.get("key") or "djconnect_profile_platform"))
        if name == "create_fixture":
            return self.create_fixture(str(parameters.get("kind") or "profile"), str(parameters.get("name") or "default"), parameters)
        if name == "remove_fixture":
            return self.remove_fixture(str(parameters.get("fixture_id") or ""))
        if name == "collect_logs":
            return PrimitiveResult("collect_logs", True, {"logs": list(self.collect_logs())})
        if name == "http_request":
            return self.execute_rest(
                str(parameters.get("method") or "GET"),
                str(parameters.get("path") or "/api/"),
                parameters.get("payload") if isinstance(parameters.get("payload"), dict) else None,
            )
        return PrimitiveResult(name, False, {"error": "CapabilityUnavailable", "action": action.name})

    def cleanup(self) -> None:
        for fixture_id in list(self.fixtures.fixtures):
            self.fixtures.remove(fixture_id)
        self._record("cleanup", "local", True, {"fixtures_remaining": 0})

    def collect_logs(self) -> tuple:
        log_entries = list(self._logs)
        if self.config.log_path and self.config.log_path.exists():
            tail = self.config.log_path.read_text(encoding="utf-8", errors="replace")[-8000:]
            log_entries.append({"source": "home_assistant_log", "text": LogManager().redact(tail)})
        return tuple(_redact(log_entries))

    def collect_artifacts(self) -> tuple:
        return ()

    def capture_screenshot(self, name: str | None = None) -> PrimitiveResult:
        return PrimitiveResult("capture_screenshot", False, {"error": "CapabilityUnavailable", "name": name})

    def capture_serial(self) -> tuple:
        return ()

    def collect_environment(self) -> dict[str, Any]:
        return {
            "adapter": self.name,
            "base_url": self.config.base_url,
            "host": platform.node(),
            "os": platform.platform(),
            "architecture": platform.machine(),
            "python": platform.python_version(),
            "storage_dir": str(self.config.storage_dir) if self.config.storage_dir else None,
            "capabilities": {
                "rest": True,
                "websocket": hasattr(self.transport, "websocket"),
                "storage_snapshot": self.config.storage_dir is not None,
                "fixtures": True,
                "logs": True,
            },
        }

    def collect_artifact_metadata(self) -> tuple[ArtifactMetadata, ...]:
        return ()

    def reset(self) -> None:
        self.cleanup()
        self._logs.clear()

    def _error_result(self, action: str, code: str, exc: Exception, started: float) -> PrimitiveResult:
        data = {"error": code, "message": LogManager().redact(str(exc)), "duration_seconds": time.perf_counter() - started}
        self._record(action, "adapter", False, data, started=started)
        return PrimitiveResult(action, False, data, message=code)

    def _record(
        self,
        operation: str,
        transport: str,
        ok: bool,
        data: dict[str, Any],
        *,
        started: float | None = None,
    ) -> None:
        self._logs.append(
            {
                "timestamp": time.time(),
                "operation": operation,
                "transport": transport,
                "ok": ok,
                "duration_seconds": (time.perf_counter() - started) if started else 0.0,
                "data": _redact(data),
            }
        )


class UrllibHomeAssistantTransport:
    def __init__(self, config: HomeAssistantAdapterConfig) -> None:
        self.config = config

    def request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> HTTPResult:
        url = self.config.base_url + (path if path.startswith("/") else f"/{path}")
        request_headers = {"Content-Type": "application/json", **(headers or {})}
        if self.config.token:
            request_headers["Authorization"] = f"Bearer {self.config.token}"
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(url, data=data, headers=request_headers, method=method.upper())
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                body = _decode_body(response.read())
                return HTTPResult(
                    status=int(response.status),
                    headers=dict(response.headers.items()),
                    body=body,
                    duration_seconds=time.perf_counter() - started,
                    url=url,
                    method=method.upper(),
                )
        except urllib.error.HTTPError as exc:
            if exc.code in {401, 403}:
                raise AuthenticationFailed(str(exc)) from exc
            return HTTPResult(
                status=int(exc.code),
                headers=dict(exc.headers.items()),
                body=_decode_body(exc.read()),
                duration_seconds=time.perf_counter() - started,
                url=url,
                method=method.upper(),
            )
        except TimeoutError:
            raise
        except OSError as exc:
            raise ConnectionFailed(str(exc)) from exc

    def websocket(self, message: dict[str, Any]) -> dict[str, Any]:
        if not self.config.token:
            raise AuthenticationFailed("missing Home Assistant token")
        with _WebSocketConnection(self.config.base_url, self.config.timeout_seconds) as ws:
            auth_required = ws.receive_json()
            if auth_required.get("type") != "auth_required":
                raise ConnectionFailed(f"unexpected websocket greeting: {auth_required.get('type')}")
            ws.send_json({"type": "auth", "access_token": self.config.token})
            auth = ws.receive_json()
            if auth.get("type") != "auth_ok":
                raise AuthenticationFailed(str(auth.get("message") or auth.get("type") or "auth failed"))
            ws.send_json(message)
            response = ws.receive_json()
            if response.get("type") == "result" and response.get("success") is False:
                error = response.get("error") or {}
                raise CapabilityUnavailable(str(error.get("code") or error.get("message") or "websocket command failed"))
            return response


class _WebSocketConnection:
    def __init__(self, base_url: str, timeout_seconds: float) -> None:
        parsed = urlsplit(base_url)
        self.secure = parsed.scheme == "https"
        self.host = parsed.hostname or "localhost"
        self.port = parsed.port or (443 if self.secure else 80)
        self.path = "/api/websocket"
        self.timeout_seconds = timeout_seconds
        self.sock: socket.socket | ssl.SSLSocket | None = None

    def __enter__(self) -> "_WebSocketConnection":
        raw = socket.create_connection((self.host, self.port), timeout=self.timeout_seconds)
        raw.settimeout(self.timeout_seconds)
        self.sock = ssl.create_default_context().wrap_socket(raw, server_hostname=self.host) if self.secure else raw
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        request = (
            f"GET {self.path} HTTP/1.1\r\n"
            f"Host: {self.host}:{self.port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        )
        self.sock.sendall(request.encode("ascii"))
        response = self._read_http_response()
        if " 101 " not in response.split("\r\n", 1)[0]:
            raise ConnectionFailed(response.split("\r\n", 1)[0])
        accept = base64.b64encode(hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("ascii")).digest()).decode("ascii")
        if f"sec-websocket-accept: {accept.lower()}" not in response.lower():
            raise ConnectionFailed("websocket accept header mismatch")
        return self

    def __exit__(self, *_args: object) -> None:
        if self.sock is not None:
            try:
                self.sock.close()
            finally:
                self.sock = None

    def send_json(self, payload: dict[str, Any]) -> None:
        self._send_text(json.dumps(payload, separators=(",", ":")))

    def receive_json(self) -> dict[str, Any]:
        text = self._receive_text()
        data = json.loads(text)
        return data if isinstance(data, dict) else {"value": data}

    def _read_http_response(self) -> str:
        assert self.sock is not None
        data = b""
        while b"\r\n\r\n" not in data:
            chunk = self.sock.recv(4096)
            if not chunk:
                break
            data += chunk
        return data.decode("iso-8859-1", errors="replace")

    def _send_text(self, text: str) -> None:
        assert self.sock is not None
        payload = text.encode("utf-8")
        mask = os.urandom(4)
        header = bytearray([0x81])
        length = len(payload)
        if length < 126:
            header.append(0x80 | length)
        elif length < 65536:
            header.extend((0x80 | 126, *struct.pack("!H", length)))
        else:
            header.extend((0x80 | 127, *struct.pack("!Q", length)))
        masked = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        self.sock.sendall(bytes(header) + mask + masked)

    def _receive_text(self) -> str:
        assert self.sock is not None
        chunks: list[bytes] = []
        while True:
            first = self._recv_exact(2)
            opcode = first[0] & 0x0F
            masked = bool(first[1] & 0x80)
            length = first[1] & 0x7F
            if length == 126:
                length = struct.unpack("!H", self._recv_exact(2))[0]
            elif length == 127:
                length = struct.unpack("!Q", self._recv_exact(8))[0]
            mask = self._recv_exact(4) if masked else b""
            payload = self._recv_exact(length) if length else b""
            if masked:
                payload = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
            if opcode == 0x8:
                raise ConnectionFailed("websocket closed")
            if opcode in {0x1, 0x0}:
                chunks.append(payload)
                if first[0] & 0x80:
                    return b"".join(chunks).decode("utf-8")

    def _recv_exact(self, size: int) -> bytes:
        assert self.sock is not None
        data = b""
        while len(data) < size:
            chunk = self.sock.recv(size - len(data))
            if not chunk:
                raise ConnectionFailed("websocket connection closed")
            data += chunk
        return data


def _decode_body(body: bytes) -> Any:
    if not body:
        return None
    text = body.decode("utf-8", errors="replace")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            normalized = str(key).lower()
            if any(token in normalized for token in ("token", "password", "secret", "proof", "authorization", "prompt", "history", "memory", "raw_audio")):
                result[key] = "<redacted>"
            else:
                result[key] = _redact(item)
        return result
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact(item) for item in value)
    if isinstance(value, str):
        return LogManager().redact(value)
    return value


def _resolve_optional(root: Path | None, value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    return path if path.is_absolute() or root is None else root / path


def _truthy(value: Any) -> bool:
    return str(value).lower() in {"1", "true", "yes", "on"}
