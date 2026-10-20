"""Private Golden transport observations, never a native fixture-admission API.

No production import, credential read, network creation, semantic judge or
QUALIFIED export. The operator must independently qualify the installed source,
complete provider-client coverage, disposable fixture and actual native run.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import time
import uuid

BINDINGS = ("catalog_sha256", "profile_sha256", "session_sha256",
            "app_executable_sha256", "core_install_receipt_sha256")
_PROCESS = uuid.uuid4().hex
ADMISSION_KEYS = set(BINDINGS) | {"schema_version", "scope", "producer_commit", "run_id",
    "max_model_calls", "attempts_per_turn", "starts_at", "expires_at", "cases"}
ACTIVE = ContextVar("private_native_golden_transport_turn", default=None)


def sha(value):
    return hashlib.sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def digest(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def stamp(value):
    parsed = datetime.fromisoformat(value)
    if parsed.utcoffset() is None:
        raise ValueError("timezone_required")
    return parsed.timestamp()


def validate(admission):
    if (not isinstance(admission, dict) or set(admission) != ADMISSION_KEYS
            or admission.get("schema_version") != 1
            or admission.get("scope") != "PRIVATE_OBSERVER_NOT_FIXTURE_ADMISSION"
            or any(not digest(admission.get(key)) for key in BINDINGS)
            or not re.fullmatch(r"[0-9a-f]{40}", admission.get("producer_commit", ""))
            or str(uuid.UUID(admission["run_id"])) != admission["run_id"]
            or type(admission.get("max_model_calls")) is not int
            or not 1 <= admission["max_model_calls"] <= 40
            or type(admission.get("attempts_per_turn")) is not int
            or not 1 <= admission["attempts_per_turn"] <= 2
            or not 0 < stamp(admission["expires_at"]) - stamp(admission["starts_at"]) <= 600):
        raise ValueError("invalid_observer_binding_or_budget")
    cases = admission.get("cases")
    if (not isinstance(cases, list) or not 1 <= len(cases) <= 40
            or any(not isinstance(c, dict) or set(c) != {"id", "question_sha256", "model_policy"}
                   or not re.fullmatch(r"[A-Za-z0-9_.-]{1,160}", c["id"])
                   or not digest(c["question_sha256"])
                   or c["model_policy"] not in {"zero", "one_or_two"} for c in cases)
            or len({c["id"] for c in cases}) != len(cases)):
        raise ValueError("unhandled_or_invalid_cases")


def validate_rows(data, admission):
    """Closed persisted schemas also prevent echoing injected private fields."""
    turns, attempts = data["turns"], data["attempts"]
    answer_keys = {"server_turn_sha256", "answer_sha256", "session_entry_sha256"}
    clients = {}
    if len(turns) > len(admission["cases"]):
        raise ValueError("invalid_turn_journal")
    for index, turn in enumerate(turns):
        case = admission["cases"][index]
        required = set(case) | {"client_message_sha256", "state"}
        if (not isinstance(turn, dict) or set(turn) not in (required, required | answer_keys)
                or any(turn[k] != case[k] for k in case)
                or not digest(turn["client_message_sha256"])
                or turn["client_message_sha256"] in clients
                or turn["state"] not in {"IN_FLIGHT", "RETURNED_NOT_NATIVE_QUALIFIED"}
                or any(k in turn and not digest(turn[k]) for k in answer_keys)):
            raise ValueError("invalid_turn_journal")
        clients[turn["client_message_sha256"]] = turn
    counts = {}
    for index, row in enumerate(attempts):
        base = {"ordinal", "case_id", "client_message_sha256", "requested_model",
                "attempted", "completed", "reserved_before_io", "state"}
        complete = base | {"model", "input_tokens", "output_tokens", "provider_response_sha256", "provider_receipt_sha256"}
        failed = base | {"failure", "provider_receipt_sha256"}
        if (not isinstance(row, dict) or set(row) not in (base, complete, failed)
                or type(row["ordinal"]) is not int or row["ordinal"] != index + 1
                or row["attempted"] is not True or row["reserved_before_io"] is not True
                or not isinstance(row["requested_model"], str)
                or re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", row["requested_model"]) is None):
            raise ValueError("invalid_attempt_journal")
        turn = clients.get(row["client_message_sha256"])
        if turn is None or row["case_id"] != turn["id"] or turn["model_policy"] == "zero":
            raise ValueError("unbound_attempt_journal")
        counts[turn["id"]] = counts.get(turn["id"], 0) + 1
        if counts[turn["id"]] > admission["attempts_per_turn"]:
            raise ValueError("attempt_journal_over_budget")
        if set(row) == base:
            valid = row["state"] == "RESERVED_OUTCOME_UNCERTAIN" and row["completed"] is False
        else:
            original = {k: v for k, v in row.items() if k != "provider_receipt_sha256"}
            valid = row["provider_receipt_sha256"] == sha(json.dumps({"run_id": admission["run_id"], **original}, sort_keys=True).encode())
            if set(row) == complete:
                valid = (valid and row["state"] == "COMPLETED" and row["completed"] is True
                         and isinstance(row["model"], str)
                         and re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", row["model"]) is not None
                         and type(row["input_tokens"]) is int and row["input_tokens"] >= 0
                         and type(row["output_tokens"]) is int and row["output_tokens"] > 0
                         and digest(row["provider_response_sha256"]))
            else:
                valid = (valid and row["state"] == "FAILED_OR_UNCERTAIN" and row["completed"] is False
                         and row["failure"] in {"http_failure", "cancelled", "incomplete_stream", "transport_or_stream_failure"})
        if not valid:
            raise ValueError("invalid_attempt_terminal_receipt")


class AttemptJournal:
    """Durable pre-I/O reservation shared across processes; no resume/reset switch."""

    def __init__(self, path, admission):
        validate(admission)
        self.path = Path(path)
        self.admission = json.loads(json.dumps(admission))

    @classmethod
    def create(cls, path, admission):
        result = cls(path, admission)
        fd = result._open(os.O_WRONLY | os.O_CREAT | os.O_EXCL)
        with os.fdopen(fd, "w") as stream:
            started = time.monotonic()
            remaining = min(600, stamp(admission["expires_at"]) - time.time())
            if remaining <= 0:
                raise ValueError("observer_window_closed")
            json.dump({"admission": result.admission, "turns": [], "attempts": [],
                       "lifetime": {"process_instance": _PROCESS,
                           "started_monotonic": started,
                           "deadline_monotonic": started + remaining}}, stream)
            stream.flush()
            os.fsync(stream.fileno())
        return result

    def _open(self, flags):
        if any(p.is_symlink() for p in [self.path, *self.path.parents]):
            raise ValueError("symlink_forbidden")
        if self.path.parent.stat().st_mode & 0o077:
            raise ValueError("private_parent_required")
        fd = os.open(self.path, flags | os.O_NOFOLLOW, 0o600)
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_uid != os.getuid():
            os.close(fd)
            raise ValueError("private_owned_regular_journal_required")
        return fd

    @contextmanager
    def _locked(self, *, mutate=False):
        fd = self._open(os.O_RDWR if mutate else os.O_RDONLY)
        with os.fdopen(fd, "r+" if mutate else "r") as stream:
            fcntl.flock(stream, fcntl.LOCK_EX if mutate else fcntl.LOCK_SH)
            data = json.load(stream)
            if (set(data) != {"admission", "turns", "attempts", "lifetime"}
                    or data.get("admission") != self.admission or not isinstance(data.get("turns"), list)
                    or not isinstance(data.get("attempts"), list)
                    or len(data["attempts"]) > self.admission["max_model_calls"]):
                raise ValueError("journal_identity_or_integrity_failure")
            lifetime = data["lifetime"]
            if (not isinstance(lifetime, dict) or set(lifetime) != {
                    "process_instance", "started_monotonic", "deadline_monotonic"}
                    or not isinstance(lifetime["process_instance"], str)
                    or re.fullmatch(r"[0-9a-f]{32}", lifetime["process_instance"]) is None
                    or any(type(lifetime[k]) not in (int, float) or not math.isfinite(lifetime[k])
                           for k in ("started_monotonic", "deadline_monotonic"))
                    or not 0 < lifetime["deadline_monotonic"] - lifetime["started_monotonic"] <= 600):
                raise ValueError("journal_lifetime_invalid")
            validate_rows(data, self.admission)
            yield data
            if mutate:
                validate_rows(data, self.admission)
                stream.seek(0)
                json.dump(data, stream, sort_keys=True)
                stream.truncate()
                stream.flush()
                os.fsync(stream.fileno())

    def _window(self, data):
        now = time.time()
        lifetime = data["lifetime"]
        monotonic = time.monotonic()
        if (not stamp(self.admission["starts_at"]) <= now < stamp(self.admission["expires_at"])
                or lifetime["process_instance"] != _PROCESS
                or not lifetime["started_monotonic"] <= monotonic < lifetime["deadline_monotonic"]):
            raise ValueError("observer_window_or_process_closed")
        return min(stamp(self.admission["expires_at"]) - now,
                   lifetime["deadline_monotonic"] - monotonic)

    def remaining(self):
        with self._locked() as data:
            return self._window(data)

    @contextmanager
    def turn(self, case_id, *, client_message_id, question, profile_id, session_id):
        """Bind at the private server entry, before invoking the ordinary service."""
        if (ACTIVE.get() is not None or not isinstance(client_message_id, str)
                or not 0 < len(client_message_id) <= 128
                or sha(profile_id) != self.admission["profile_sha256"]
                or sha(session_id) != self.admission["session_sha256"]):
            raise ValueError("wrong_or_nested_turn_owner")
        with self._locked(mutate=True) as data:
            self._window(data)
            index = len(data["turns"])
            if index >= len(self.admission["cases"]):
                raise ValueError("case_order_or_replay")
            case = self.admission["cases"][index]
            client = sha(client_message_id)
            if (case["id"] != case_id or sha(question) != case["question_sha256"]
                    or any(t["client_message_sha256"] == client for t in data["turns"])):
                raise ValueError("case_order_question_or_replay")
            row = {**case, "client_message_sha256": client, "state": "IN_FLIGHT"}
            data["turns"].append(row)
        token = ACTIVE.set((self, case_id, client))
        try:
            yield
        finally:
            ACTIVE.reset(token)
            with self._locked(mutate=True) as data:
                data["turns"][index]["state"] = "RETURNED_NOT_NATIVE_QUALIFIED"

    def reserve(self, model):
        binding = ACTIVE.get()
        if binding is None or binding[0] is not self:
            raise ValueError("unattributed_provider_dispatch_refused")
        _, case_id, client = binding
        if not isinstance(model, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", model):
            raise ValueError("invalid_model")
        with self._locked(mutate=True) as data:
            self._window(data)
            turn = next(t for t in data["turns"] if t["id"] == case_id)
            count = sum(a["client_message_sha256"] == client for a in data["attempts"])
            if (turn["model_policy"] == "zero" or turn["state"] != "IN_FLIGHT"
                    or count >= self.admission["attempts_per_turn"]
                    or len(data["attempts"]) >= self.admission["max_model_calls"]):
                raise ValueError("provider_transport_budget_exhausted")
            ordinal = len(data["attempts"]) + 1
            data["attempts"].append({"ordinal": ordinal, "case_id": case_id,
                "client_message_sha256": client, "requested_model": model,
                "attempted": True, "completed": False, "reserved_before_io": True,
                "state": "RESERVED_OUTCOME_UNCERTAIN"})
        return ordinal

    def finish(self, ordinal, *, completed=False, model=None, input_tokens=None,
               output_tokens=None, response_id=None, failure="transport_or_stream_failure"):
        with self._locked(mutate=True) as data:
            row = data["attempts"][ordinal - 1]
            if row["state"] != "RESERVED_OUTCOME_UNCERTAIN":
                raise ValueError("attempt_already_terminal")
            valid = (completed is True and isinstance(model, str)
                     and re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", model)
                     and type(input_tokens) is int and input_tokens >= 0
                     and type(output_tokens) is int and output_tokens > 0
                     and isinstance(response_id, str) and 0 < len(response_id) <= 256)
            row.update(completed=bool(valid), state="COMPLETED" if valid else "FAILED_OR_UNCERTAIN")
            if valid:
                row.update(model=model, input_tokens=input_tokens, output_tokens=output_tokens,
                           provider_response_sha256=sha(response_id))
            else:
                # Fixed token: never exception text, provider response bodies or paths.
                row["failure"] = failure if failure in {"http_failure", "cancelled", "incomplete_stream"} else "transport_or_stream_failure"
            row["provider_receipt_sha256"] = sha(json.dumps({"run_id": self.admission["run_id"], **row}, sort_keys=True).encode())

    def record_result(self, case_id, response, reopened_assistant, session_entry):
        """Join actual server/history/repository reads, never a native report.

        Apple calls its assistant message ID hash ``server_turn_sha256``; it is
        not the distinct conversation.turn_id. Preserve that exact meaning.
        """
        assistant = response.get("assistant_message") or {}
        body = session_entry.get("body") or {}
        if isinstance(body, str):
            body = json.loads(body)
        client = response.get("client_message_id")
        message_id, text = assistant.get("id"), assistant.get("text")
        conversation = response.get("conversation") or {}
        if (response.get("success") is not True
                or not isinstance(client, str) or not isinstance(message_id, str) or not message_id
                or not isinstance(text, str) or not 0 < len(text.encode()) <= 64000
                or sha(response.get("owner_profile_id", "")) != self.admission["profile_sha256"]
                or conversation.get("history_scope") != "profile"
                or sha((conversation.get("context") or {}).get("session_id", "")) != self.admission["session_sha256"]
                or reopened_assistant.get("id") != message_id
                or reopened_assistant.get("client_message_id") != client
                or reopened_assistant.get("text") != text
                or session_entry.get("kind") != "conversation_dj"
                or sha(session_entry.get("session_id", "")) != self.admission["session_sha256"]
                or not isinstance(session_entry.get("entry_id"), str) or not session_entry["entry_id"]
                or body.get("message_id") != message_id
                or not conversation.get("turn_id") or body.get("turn_id") != conversation["turn_id"]):
            raise ValueError("independent_server_history_entry_binding_failed")
        with self._locked(mutate=True) as data:
            row = next(t for t in data["turns"] if t["id"] == case_id)
            if row["client_message_sha256"] != sha(client) or "answer_sha256" in row:
                raise ValueError("wrong_or_reused_answer_binding")
            row.update(server_turn_sha256=sha(message_id), answer_sha256=sha(text),
                       session_entry_sha256=sha(session_entry["entry_id"]))

    def export(self):
        with self._locked() as data:
            snapshot = json.loads(json.dumps(data))
        # A caller cannot turn observations into fixture/source/native admission.
        return {**{key: self.admission[key] for key in ADMISSION_KEYS},
                "deadline_policy": "NON_RENEWABLE_MONOTONIC_RESTART_REFUSES_NEW_IO",
                "export_status": "OBSERVED_NOT_QUALIFIED",
                "provider_coverage": "BOUND_CLIENT_ONLY_NOT_ALL_INSTALLED_PROVIDERS",
                "unattributed_provider_attempts": None,
                "observed_total_provider_attempts": len(snapshot["attempts"]),
                "turns": snapshot["turns"], "provider_attempts": snapshot["attempts"],
                "cases": [{**turn, "provider_attempts": [a for a in snapshot["attempts"]
                    if a["client_message_sha256"] == turn["client_message_sha256"]],
                    "semantic_verdict": "NOT_REVIEWED", "effects_verdict": "NOT_REVIEWED"}
                    for turn in snapshot["turns"]],
                "semantic_verdict": "NOT_REVIEWED", "effects_verdict": "NOT_REVIEWED",
                "native": "NOT_RUN", "installed": "NOT_RUN", "release": "NOT_GRANTED"}


def wrap_responses_transport(inner, journal):
    """Wrap the actual HTTP boundary so SDK retries reserve independently.

    Test-only opt-in. The caller supplies a transport; this creates no client,
    changes no configured SDK retries, and does not install a production hook.
    """
    import asyncio
    import httpx

    class ObservedStream(httpx.AsyncByteStream):
        def __init__(self, stream, ordinal):
            self.stream, self.ordinal = stream, ordinal
            self.buffer = b""
            self.terminal = None
            self.invalid = False
            self.done = False

        async def __aiter__(self):
            try:
                remaining = journal.remaining()
                async with asyncio.timeout(max(0, remaining)):
                    async for chunk in self.stream:
                        self.buffer += chunk
                        if len(self.buffer) > 262144:
                            self.invalid = True
                            raise ValueError("provider_event_bound")
                        while b"\n" in self.buffer:
                            line, self.buffer = self.buffer.split(b"\n", 1)
                            if not line.startswith(b"data:") or line[5:].strip() == b"[DONE]":
                                continue
                            try:
                                event = json.loads(line[5:].strip())
                            except (ValueError, UnicodeError):
                                self.invalid = True
                                continue
                            if isinstance(event, dict) and event.get("type") in {"response.completed", "response.failed", "response.incomplete"}:
                                if self.terminal is not None:
                                    self.invalid = True
                                self.terminal = event
                        yield chunk
            finally:
                await self.aclose()

        async def aclose(self):
            if self.done:
                return
            self.done = True
            event = self.terminal or {}
            response = event.get("response")
            response = response if isinstance(response, dict) else {}
            usage = response.get("usage")
            usage = usage if isinstance(usage, dict) else {}
            try:
                journal.finish(self.ordinal,
                    completed=not self.invalid and event.get("type") == "response.completed",
                    model=response.get("model"), input_tokens=usage.get("input_tokens"),
                    output_tokens=usage.get("output_tokens"), response_id=response.get("id"),
                    failure="incomplete_stream")
            finally:
                await self.stream.aclose()

    class ObservedTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request):
            if (request.method != "POST" or request.url.scheme != "https"
                    or request.url.host != "api.openai.com" or request.url.port not in (None, 443)
                    or request.url.path != "/v1/responses" or request.url.query
                    or request.url.userinfo or request.url.fragment):
                raise ValueError("unadmitted_provider_route")
            raw = request.content
            if len(raw) > 1_000_000:
                raise ValueError("provider_request_bound")
            body = json.loads(raw)
            if not isinstance(body, dict) or body.get("stream") is not True:
                raise ValueError("streaming_responses_required")
            ordinal = journal.reserve(body.get("model"))
            try:
                remaining = journal.remaining()
                async with asyncio.timeout(max(0, remaining)):
                    response = await inner.handle_async_request(request)
            except BaseException:
                journal.finish(ordinal)
                raise
            if response.status_code != 200:
                journal.finish(ordinal, failure="http_failure")
            else:
                response.stream = ObservedStream(response.stream, ordinal)
            return response

        async def aclose(self):
            await inner.aclose()

    return ObservedTransport()
