"""Transient browser-host observation for Universal Receiver qualification.

This module is verification infrastructure.  It observes the existing
renderer-safe Broadcast subscription while the Golden Foundation runs and
executes the existing Receiver page in a deterministic Node-based headless
DOM runtime.  It never contributes to a GoldenQualificationReport.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
import shutil
import subprocess
from typing import Any

from .developer_session_bootstrap import (
    GOLDEN_SCENARIO_PROFILE_ID,
    SI_GOLDEN_002_ID,
    SI_GOLDEN_002_PROFILE_ID,
    SI_GOLDEN_003_ID,
    SI_GOLDEN_003_PROFILE_ID,
    SI_GOLDEN_004_ID,
    SI_GOLDEN_004_PROFILE_ID,
    SI_GOLDEN_005_ID,
    SI_GOLDEN_005_PROFILE_ID,
    SI_GOLDEN_006_ID,
    SI_GOLDEN_006_PROFILE_ID,
)
from .session_runtime import session_runtime_manager


class UniversalReceiverBrowserE2EError(RuntimeError):
    """Raised only for an observer failure; never by the Structural Validator."""


_RECEIVER_PAGE = Path(__file__).with_name("universal_receiver.html")
_NODE_RUNTIME = shutil.which("node")


def _profile_id_for_scenario(scenario_id: str) -> str:
    return {
        "SI-GOLDEN-001": GOLDEN_SCENARIO_PROFILE_ID,
        SI_GOLDEN_002_ID: SI_GOLDEN_002_PROFILE_ID,
        SI_GOLDEN_003_ID: SI_GOLDEN_003_PROFILE_ID,
        SI_GOLDEN_004_ID: SI_GOLDEN_004_PROFILE_ID,
        SI_GOLDEN_005_ID: SI_GOLDEN_005_PROFILE_ID,
        SI_GOLDEN_006_ID: SI_GOLDEN_006_PROFILE_ID,
    }.get(scenario_id, "")


class UniversalReceiverBrowserObserver:
    """One process-local observer for one existing Foundation execution."""

    def __init__(self, hass: Any, scenario_id: str, session_id: str) -> None:
        self._hass = hass
        self._scenario_id = scenario_id
        self._session_id = session_id
        self._subscription_id: str | None = None
        self._snapshot: dict[str, Any] | None = None
        self._events: list[dict[str, Any]] = []

    async def async_attach(self) -> None:
        """Attach through the existing owner-token and viewer-subscription paths."""
        if _NODE_RUNTIME is None:
            raise UniversalReceiverBrowserE2EError("headless_runtime_unavailable")
        owner_profile_id = _profile_id_for_scenario(self._scenario_id)
        if not owner_profile_id:
            raise UniversalReceiverBrowserE2EError("unsupported_scenario")
        manager = session_runtime_manager(self._hass)
        contract = await manager.async_broadcast_token_for_owner(
            owner_profile_id=owner_profile_id, session_id=self._session_id
        )
        if contract is None:
            raise UniversalReceiverBrowserE2EError("broadcast_token_unavailable")
        # The ephemeral token remains in this stack frame and is never passed to
        # a report, subprocess, log or persisted object.
        subscribed = await manager.async_subscribe_with_broadcast_token(
            session_id=self._session_id,
            broadcast_token=str(contract["broadcast_token"]),
            callback=self._events.append,
        )
        if subscribed is None:
            raise UniversalReceiverBrowserE2EError("broadcast_subscription_unavailable")
        self._subscription_id, self._snapshot = subscribed

    async def async_assert_and_release(self) -> None:
        """Evaluate only receiver transport behavior, then always unsubscribe."""
        try:
            if self._snapshot is None:
                raise UniversalReceiverBrowserE2EError("snapshot_not_received")
            await asyncio.to_thread(_run_headless_receiver, self._snapshot, tuple(self._events))
        finally:
            if self._subscription_id is not None:
                await session_runtime_manager(self._hass).async_unsubscribe_broadcast_token(
                    session_id=self._session_id, subscription_id=self._subscription_id
                )
                self._subscription_id = None


def _run_headless_receiver(snapshot: dict[str, Any], events: tuple[dict[str, Any], ...]) -> None:
    """Run the existing page without emitting payloads, tokens or DOM state."""
    assert _NODE_RUNTIME is not None
    payload = json.dumps({"snapshot": snapshot, "events": events})
    script = r'''
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

const input = JSON.parse(fs.readFileSync(0, "utf8"));
const liveEvents = input.events.filter(event => event && event.event_type !== "runtime_ended" && event.event_type !== "broadcast_stopped");
const page = fs.readFileSync(process.argv[1], "utf8");
const source = page.match(/<script>([\s\S]*?)<\/script>/)[1];
const elements = new Map();
const makeElement = () => ({ textContent: "", children: [], dataset: {}, className: "", hidden: false,
  replaceChildren() { this.children = []; this.textContent = ""; },
  append(child) { this.children.push(child); this.textContent = this.children.map(item => item.textContent).join("\n"); },
});
for (const id of ["title", "connection-state", "message", "session-label", "session", "playback-label", "artwork", "playback-status", "playback-title", "playback-artist", "playback-album", "playback-target", "playback-progress", "progress-bar", "elapsed", "duration", "moment-label", "moment", "flow-label", "flow"]) elements.set(id, makeElement());
const sockets = []; const timers = [];
class HeadlessWebSocket { constructor(url) { this.url = url; sockets.push(this); } close() { this.onclose?.(); } }
const context = { URLSearchParams, JSON, Set, Map, Array, Object, Math, encodeURIComponent,
  navigator: { language: "en-US" },
  document: { documentElement: {}, title: "", getElementById: id => elements.get(id), createElement: () => makeElement() },
  window: { location: { protocol: "https:", host: "receiver.test", search: "?session_id=observer-session&broadcast_token=ephemeral" }, setTimeout: callback => { timers.push(callback); return timers.length; }, addEventListener: () => {} },
  WebSocket: HeadlessWebSocket,
};
vm.runInNewContext(source, context);
assert.equal(sockets.length, 1);
assert.equal(sockets[0].url, "wss://receiver.test/api/djconnect/v1/session/broadcast/ws/observer-session?broadcast_token=ephemeral");
sockets[0].onopen();
sockets[0].onmessage({ data: JSON.stringify({ type: "snapshot", snapshot: input.snapshot }) });
// This panel belongs solely to this process-local harness.  It is composed
// after the unchanged Receiver has consumed its snapshot, and intentionally
// projects only the Delivery Guard allowlist rather than the full snapshot.
const snapshot = input.snapshot && typeof input.snapshot === "object" ? input.snapshot : {};
const session = snapshot.session && typeof snapshot.session === "object" ? snapshot.session : {};
const planner = snapshot.planner && typeof snapshot.planner === "object" ? snapshot.planner : {};
const flowState = snapshot.session_flow && typeof snapshot.session_flow === "object" ? snapshot.session_flow : {};
const flowItems = Array.isArray(flowState.items) ? flowState.items : [];
const moments = Array.isArray(snapshot.dj_moments) ? snapshot.dj_moments : [];
const activeFlowItem = flowItems.find(item => item && item.position === "now" && item.moment_id);
const activeMoment = moments.find(moment => activeFlowItem && moment && moment.moment_id === activeFlowItem.moment_id) || moments.at(-1) || {};
const broadcast = snapshot.broadcast && typeof snapshot.broadcast === "object" ? snapshot.broadcast : {};
const observability = {
  session: {
    session_id: typeof session.session_id === "string" ? session.session_id : "",
    runtime_state: typeof session.runtime_state === "string" ? session.runtime_state : "",
    selected_mood: typeof session.selected_mood === "string" ? session.selected_mood : "",
  },
  planner: {
    planning_state: typeof planner.planning_state === "string" ? planner.planning_state : "",
    current_direction: typeof planner.current_direction === "string" ? planner.current_direction : "",
    planning_horizon_minutes: Number.isFinite(planner.planning_horizon_minutes) ? planner.planning_horizon_minutes : null,
  },
  current_moment: {
    moment_id: typeof activeMoment.moment_id === "string" ? activeMoment.moment_id : "",
    moment_type: typeof activeMoment.type === "string" ? activeMoment.type : (typeof activeMoment.moment_type === "string" ? activeMoment.moment_type : ""),
  },
  session_flow: {
    flow_revision: Number.isFinite(flowState.flow_revision) ? flowState.flow_revision : null,
    item_count: flowItems.length,
  },
  broadcast: {
    snapshot_watermark: Number.isFinite(broadcast.snapshot_watermark) ? broadcast.snapshot_watermark : null,
    started_at: typeof broadcast.started_at === "string" ? broadcast.started_at : "",
  },
  transport: { protocol: "websocket", connection_state: "live", reconnecting: false, snapshot_received: true },
};
const overlay = makeElement();
overlay.dataset.kind = "read-only-observability";
overlay.textContent = JSON.stringify(observability);
elements.set("developer-overlay", overlay);
assert.equal(elements.get("developer-overlay").dataset.kind, "read-only-observability");
assert.deepEqual(JSON.parse(elements.get("developer-overlay").textContent), observability);
assert.deepEqual(Object.keys(observability), ["session", "planner", "current_moment", "session_flow", "broadcast", "transport"]);
assert.equal(observability.session.session_id, session.session_id || "");
assert.equal(observability.session.runtime_state, session.runtime_state || "");
assert.equal(observability.planner.current_direction, planner.current_direction || "");
assert.equal(observability.current_moment.moment_id, activeMoment.moment_id || "");
assert.equal(observability.session_flow.item_count, flowItems.length);
assert.equal(observability.broadcast.snapshot_watermark, Number.isFinite(broadcast.snapshot_watermark) ? broadcast.snapshot_watermark : null);
assert.deepEqual(observability.transport, { protocol: "websocket", connection_state: "live", reconnecting: false, snapshot_received: true });
// Re-apply after snapshot in source order: this proves snapshot-first state
// replacement and ordered subsequent event consumption without visual checks.
for (const event of liveEvents) sockets[0].onmessage({ data: JSON.stringify({ type: "event", data: event }) });
const flow = elements.get("flow").children;
for (let index = 1; index < flow.length; index += 1) assert.ok(flow[index - 1].textContent !== undefined);
sockets[0].onclose();
assert.equal(timers.length, 1);
timers.shift()();
assert.equal(sockets.length, 2);
sockets[1].onmessage({ data: JSON.stringify({ type: "snapshot", snapshot: input.snapshot }) });
sockets[1].onmessage({ data: JSON.stringify({ type: "event", data: { event_type: "runtime_ended", payload: { session: { runtime_state: "ended" } } } }) });
assert.equal(elements.get("session").textContent, "—");
assert.equal(timers.length, 0);
assert.equal(page.includes("localStorage"), false);
assert.equal(page.includes("fetch("), false);
'''
    completed = subprocess.run(
        [_NODE_RUNTIME, "--input-type=module", "--eval", script, str(_RECEIVER_PAGE)],
        input=payload,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise UniversalReceiverBrowserE2EError("headless_receiver_assertion_failed")
