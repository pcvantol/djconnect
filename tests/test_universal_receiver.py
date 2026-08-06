from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import textwrap
import unittest

from tests.test_http_voice_helpers import install_http_stubs


ROOT = Path(__file__).resolve().parents[1]
RECEIVER_PAGE = ROOT / "custom_components" / "djconnect" / "universal_receiver.html"


class UniversalReceiverTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        install_http_stubs()
        from custom_components.djconnect import http

        cls.http = http

    def test_receiver_page_is_a_nocache_presentation_shell(self) -> None:
        response = self.http.DJConnectUniversalReceiverView()
        result = __import__("asyncio").run(response.get(object()))

        self.assertEqual(result.status, 200)
        self.assertEqual(result.content_type, "text/html")
        self.assertEqual(result.headers["Cache-Control"], "no-store")
        self.assertEqual(result.headers["Referrer-Policy"], "no-referrer")
        self.assertIn('data-testid="connection-state"', result.text)
        self.assertIn('data-testid="session"', result.text)
        self.assertIn('data-testid="now-playing"', result.text)
        self.assertIn('data-testid="playback-title"', result.text)
        self.assertIn('data-testid="progress-bar"', result.text)
        self.assertIn('data-testid="moment"', result.text)
        self.assertIn('data-testid="flow"', result.text)

    def test_receiver_page_uses_the_full_portrait_viewport(self) -> None:
        page = RECEIVER_PAGE.read_text(encoding="utf-8")

        self.assertIn("min-height: 100dvh", page)
        self.assertIn("@media (orientation: portrait)", page)

    def test_receiver_uses_only_existing_broadcast_websocket_and_renders_lifecycle(self) -> None:
        node = shutil.which("node")
        if node is None:
            self.skipTest("Node.js is required to execute the browser receiver test")

        script = textwrap.dedent(
            f"""
            import assert from "node:assert/strict";
            import fs from "node:fs";
            import vm from "node:vm";

            const page = fs.readFileSync({json.dumps(str(RECEIVER_PAGE))}, "utf8");
            const script = page.match(/<script>([\\s\\S]*?)<\\/script>/)[1];
            const elements = new Map();
            const makeElement = () => ({{
              textContent: "", children: [], dataset: {{}}, className: "",
              replaceChildren() {{ this.children = []; this.textContent = ""; }},
              append(child) {{ this.children.push(child); this.textContent = this.children.map(entry => entry.textContent).join("\\n"); }},
            }});
            for (const id of ["title", "connection-state", "message", "session-label", "session", "playback-label", "artwork", "playback-status", "playback-title", "playback-artist", "playback-album", "playback-target", "playback-progress", "progress-bar", "elapsed", "duration", "moment-label", "moment", "flow-label", "flow"]) elements.set(id, makeElement());
            const timers = [];
            const sockets = [];
            class FakeWebSocket {{
              constructor(url) {{ this.url = url; sockets.push(this); }}
              close() {{ if (this.onclose) this.onclose(); }}
            }}
            const context = {{
              URLSearchParams, JSON, Set, Map, Array, Object, Math, encodeURIComponent,
              navigator: {{ language: "en-US" }},
              document: {{ documentElement: {{}}, title: "", getElementById: id => elements.get(id), createElement: () => makeElement() }},
              window: {{
                location: {{ protocol: "https:", host: "example.test", search: "?session_id=session-1&broadcast_token=token-1" }},
                setTimeout: callback => {{ timers.push(callback); return timers.length; }},
                addEventListener: () => {{}},
              }},
              WebSocket: FakeWebSocket,
            }};
            vm.runInNewContext(script, context);
            assert.equal(sockets.length, 1);
            assert.equal(sockets[0].url, "wss://example.test/api/djconnect/v1/session/broadcast/ws/session-1?broadcast_token=token-1");
            sockets[0].onopen();
            sockets[0].onmessage({{ data: JSON.stringify({{ type: "snapshot", snapshot: {{
              session: {{ session_id: "session-1", runtime_state: "active" }},
              playback: {{ state: "playing", title: "Track One", artist: "Artist One", album: "Album One", artwork_url: "/api/djconnect/v1/image_proxy/cover-one", target_name: "Living Room", duration_ms: 180000, position_ms: 61000 }},
              session_flow: {{ items: [
                {{ item_id: "completed-1", position: "completed", item_type: "dj_moment", label: "First moment", moment_id: "moment-1", moment_type: "artist_story" }},
                {{ item_id: "now-1", position: "now", item_type: "current_track", label: "Track One" }},
                {{ item_id: "next-1", position: "next", item_type: "dj_moment", label: "Next moment", moment_id: "moment-2", moment_type: "transition" }},
              ] }},
              dj_moments: [{{ moment_id: "moment-1", title: "First moment" }}],
              planner: {{ hidden: true }},
            }} }}) }});
            assert.match(elements.get("session").textContent, /session-1/);
            assert.equal(elements.get("playback-title").textContent, "Track One");
            assert.equal(elements.get("playback-artist").textContent, "Artist One");
            assert.equal(elements.get("playback-album").textContent, "Album One");
            assert.equal(elements.get("playback-status").textContent, "Playing");
            assert.equal(elements.get("artwork").hidden, false);
            assert.equal(elements.get("artwork").src, "/api/djconnect/v1/image_proxy/cover-one");
            assert.equal(elements.get("progress-bar").value, 61000);
            assert.equal(elements.get("progress-bar").max, 180000);
            assert.equal(elements.get("elapsed").textContent, "1:01");
            assert.equal(elements.get("duration").textContent, "3:00");
            assert.match(elements.get("moment").textContent, /First moment/);
            assert.equal(elements.get("flow").textContent, "completed · dj_moment · First moment · artist_story\\nnow · current_track · Track One\\nnext · dj_moment · Next moment · transition");
            const flowUpdate = {{ event_type: "session_flow_updated", payload: {{ session_flow: {{ items: [
              {{ item_id: "now-2", position: "now", item_type: "current_track", label: "Track Two" }},
              {{ item_id: "next-2", position: "next", item_type: "dj_moment", label: "Second moment", moment_id: "moment-2", moment_type: "session_update" }},
              {{ item_id: "later-2", position: "later", item_type: "future_placeholder", label: "Later" }},
            ] }} }} }};
            const momentUpdate = {{ event_type: "dj_moment_published", payload: {{ dj_moment: {{ moment_id: "moment-2", title: "Second moment" }} }} }};
            sockets[0].onmessage({{ data: JSON.stringify({{ type: "event", data: flowUpdate }}) }});
            sockets[0].onmessage({{ data: JSON.stringify({{ type: "event", data: momentUpdate }}) }});
            const liveTimeline = elements.get("flow").textContent;
            assert.ok(liveTimeline.indexOf("Track Two") < liveTimeline.indexOf("Second moment"));
            assert.ok(liveTimeline.indexOf("Second moment") < liveTimeline.indexOf("Later"));
            assert.match(elements.get("moment").textContent, /Second moment/);
            const playbackUpdate = {{ event_type: "playback_progress", payload: {{ playback: {{ state: "paused", title: "Track Two", artist: "Artist Two", album: "Album Two", artwork_url: "/api/djconnect/v1/image_proxy/cover-two", target_name: "Kitchen", duration_ms: 240000, position_ms: 123000 }} }} }};
            sockets[0].onmessage({{ data: JSON.stringify({{ type: "event", data: playbackUpdate }}) }});
            assert.equal(elements.get("playback-title").textContent, "Track Two");
            assert.equal(elements.get("playback-status").textContent, "Paused");
            assert.equal(elements.get("artwork").src, "/api/djconnect/v1/image_proxy/cover-two");
            assert.equal(elements.get("progress-bar").value, 123000);
            assert.equal(elements.get("elapsed").textContent, "2:03");
            sockets[0].onmessage({{ data: JSON.stringify({{ type: "snapshot", snapshot: {{
              session: {{ session_id: "session-1", runtime_state: "active" }},
              session_flow: {{ items: [{{ item_id: "reset-1", position: "now", item_type: "current_track", label: "Reset flow" }}] }},
              dj_moments: [],
            }} }}) }});
            assert.equal(elements.get("flow").textContent, "now · current_track · Reset flow");
            sockets[0].onclose();
            assert.equal(timers.length, 1);
            timers.shift()();
            assert.equal(sockets.length, 2);
            sockets[1].onmessage({{ data: JSON.stringify({{ type: "snapshot", snapshot: {{ session: {{ session_id: "session-1", runtime_state: "active" }}, playback: {{ state: "stopped", title: "Restored", artist: "", album: "", duration_ms: 0 }}, session_flow: {{ items: [{{ item_id: "restored-1", position: "now", item_type: "current_track", label: "Restored flow" }}] }}, dj_moments: [] }} }}) }});
            assert.equal(elements.get("playback-title").textContent, "Restored");
            assert.equal(elements.get("playback-status").textContent, "Stopped");
            assert.equal(elements.get("artwork").hidden, true);
            assert.equal(elements.get("playback-progress").hidden, true);
            assert.equal(elements.get("playback-artist").textContent, "—");
            assert.equal(elements.get("playback-album").textContent, "—");
            assert.equal(elements.get("flow").textContent, "now · current_track · Restored flow");
            const endedEvent = {{ event_type: "runtime_ended", payload: {{ session: {{ runtime_state: "ended" }} }} }};
            sockets[1].onmessage({{ data: JSON.stringify({{ type: "event", data: endedEvent }}) }});
            assert.equal(elements.get("session").textContent, "—");
            assert.equal(elements.get("message").textContent, "Session ended");
            sockets[1].onclose();
            assert.equal(timers.length, 0);
            assert.equal(page.includes("localStorage"), false);
            assert.equal(page.includes("fetch("), false);
            assert.equal(page.includes(".sort("), false);
            assert.equal(page.includes("setInterval("), false);
            """
        )
        completed = subprocess.run(
            [node, "--input-type=module", "--eval", script],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_missing_session_or_token_stays_disconnected(self) -> None:
        page = RECEIVER_PAGE.read_text(encoding="utf-8")
        self.assertIn("if (!sessionId || !broadcastToken)", page)
        self.assertIn("text.missing", page)
        self.assertIn("text.unavailable", page)
