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
        self.assertIn('data-testid="playback"', result.text)
        self.assertIn('data-testid="moment"', result.text)
        self.assertIn('data-testid="flow"', result.text)

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
            for (const id of ["title", "connection-state", "message", "session-label", "session", "playback-label", "playback", "moment-label", "moment", "flow-label", "flow"]) elements.set(id, {{ textContent: "" }});
            const timers = [];
            const sockets = [];
            class FakeWebSocket {{
              constructor(url) {{ this.url = url; sockets.push(this); }}
              close() {{ if (this.onclose) this.onclose(); }}
            }}
            const context = {{
              URLSearchParams, JSON, Set, Map, Array, Object, Math, encodeURIComponent,
              navigator: {{ language: "en-US" }},
              document: {{ documentElement: {{}}, title: "", getElementById: id => elements.get(id) }},
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
              playback: {{ current_track: {{ title: "Track One" }} }},
              session_flow: {{ items: [{{ flow_id: "flow-1" }}] }},
              dj_moments: [{{ moment_id: "moment-1", title: "First moment" }}],
              planner: {{ hidden: true }},
            }} }}) }});
            assert.match(elements.get("session").textContent, /session-1/);
            assert.match(elements.get("playback").textContent, /Track One/);
            assert.match(elements.get("moment").textContent, /First moment/);
            assert.match(elements.get("flow").textContent, /flow-1/);
            const flowUpdate = {{ event_type: "session_flow_updated", payload: {{ session_flow: {{ items: [{{ flow_id: "flow-2" }}] }} }} }};
            const momentUpdate = {{ event_type: "dj_moment_published", payload: {{ dj_moment: {{ moment_id: "moment-2", title: "Second moment" }} }} }};
            sockets[0].onmessage({{ data: JSON.stringify({{ type: "event", data: flowUpdate }}) }});
            sockets[0].onmessage({{ data: JSON.stringify({{ type: "event", data: momentUpdate }}) }});
            assert.match(elements.get("flow").textContent, /flow-2/);
            assert.match(elements.get("moment").textContent, /Second moment/);
            sockets[0].onclose();
            assert.equal(timers.length, 1);
            timers.shift()();
            assert.equal(sockets.length, 2);
            sockets[1].onmessage({{ data: JSON.stringify({{ type: "snapshot", snapshot: {{ session: {{ session_id: "session-1", runtime_state: "active" }}, playback: {{ current_track: {{ title: "Restored" }} }}, session_flow: {{ items: [] }}, dj_moments: [] }} }}) }});
            assert.match(elements.get("playback").textContent, /Restored/);
            const endedEvent = {{ event_type: "runtime_ended", payload: {{ session: {{ runtime_state: "ended" }} }} }};
            sockets[1].onmessage({{ data: JSON.stringify({{ type: "event", data: endedEvent }}) }});
            assert.equal(elements.get("session").textContent, "—");
            assert.equal(elements.get("message").textContent, "Session ended");
            sockets[1].onclose();
            assert.equal(timers.length, 0);
            assert.equal(page.includes("localStorage"), false);
            assert.equal(page.includes("fetch("), false);
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
