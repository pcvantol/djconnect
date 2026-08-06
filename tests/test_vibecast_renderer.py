from __future__ import annotations

import asyncio
import json
from pathlib import Path
import shutil
import subprocess
import textwrap
import unittest

from tests.test_http_voice_helpers import install_http_stubs


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "custom_components" / "djconnect" / "vibecast.html"


class VibeCastRendererTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        install_http_stubs()
        from custom_components.djconnect import http

        cls.http = http

    def test_renderer_page_is_ephemeral_and_ambient(self) -> None:
        result = asyncio.run(self.http.DJConnectVibeCastRendererView().get(object()))
        self.assertEqual(result.status, 200)
        self.assertEqual(result.headers["Cache-Control"], "no-store")
        self.assertIn('data-testid="connection-state"', result.text)
        self.assertIn("@media (orientation:landscape)", result.text)
        self.assertIn("min-height:100dvh", result.text)
        self.assertNotIn("localStorage", result.text)
        self.assertNotIn("fetch(", result.text)

    def test_renderer_uses_only_existing_receiver_transport(self) -> None:
        page = PAGE.read_text(encoding="utf-8")
        self.assertIn("broadcast_token", page)
        self.assertIn("/api/djconnect/v1/session/broadcast/ws/", page)
        self.assertNotIn("/api/djconnect/v1/vibecast", page)

    def test_renderer_applies_snapshot_and_runtime_end_without_persistence(self) -> None:
        node = shutil.which("node")
        if node is None:
            self.skipTest("Node.js is required to execute the VibeCast renderer test")
        script = textwrap.dedent(f"""
            import assert from "node:assert/strict"; import fs from "node:fs"; import vm from "node:vm";
            const page = fs.readFileSync({json.dumps(str(PAGE))}, "utf8"); const script = page.match(/<script>([\\s\\S]*?)<\\/script>/)[1];
            const make = () => ({{textContent:"",hidden:false,src:"",alt:"",max:0,value:0}}), elements = new Map();
            for (const id of ["state","artwork","mood","title","artist","moment","progress","album","time"]) elements.set(id, make());
            const styles = new Map(), sockets = []; class WS {{ constructor(url) {{ this.url=url; sockets.push(this); }} close() {{ if(this.onclose) this.onclose(); }} }}
            const context = {{ URLSearchParams,JSON,Math,Number,Array,Object,String,encodeURIComponent,navigator:{{language:"nl-NL"}},document:{{body:{{classList:{{toggle:()=>{{}}}}}},documentElement:{{style:{{setProperty:(k,v)=>styles.set(k,v)}}}},getElementById:id=>elements.get(id)}},window:{{location:{{protocol:"https:",host:"receiver.test",search:"?session_id=session-1&broadcast_token=token-1"}},setTimeout:()=>1,addEventListener:()=>{{}}}},WebSocket:WS }};
            vm.runInNewContext(script, context); assert.equal(sockets[0].url,"wss://receiver.test/api/djconnect/v1/session/broadcast/ws/session-1?broadcast_token=token-1"); sockets[0].onopen();
            sockets[0].onmessage({{data:JSON.stringify({{type:"snapshot",snapshot:{{session:{{selected_mood:"energy"}},playback:{{title:"Track One",artist:"Artist One",album:"Album One",artwork_url:"/cover",duration_ms:180000,position_ms:61000}},dj_moments:[{{title:"Artist Story",summary:"A bright story."}}]}}}})}});
            assert.equal(elements.get("state").textContent,"Live"); assert.equal(elements.get("title").textContent,"Track One"); assert.equal(elements.get("moment").textContent,"A bright story."); assert.equal(elements.get("progress").value,61000); assert.equal(styles.get("--accent"),"#ff806b");
            sockets[0].onmessage({{data:JSON.stringify({{type:"event",data:{{event_type:"runtime_ended",payload:{{}}}}}})}}); assert.equal(elements.get("state").textContent,"Inactief"); assert.equal(elements.get("title").textContent,"Wachten op een sessie"); assert.equal(page.includes("localStorage"),false);
        """)
        completed = subprocess.run([node, "--input-type=module", "--eval", script], check=False, capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
