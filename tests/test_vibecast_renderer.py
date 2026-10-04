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
        self.assertNotIn("/api/djconnect/v1/vibecast", result.text)
        self.assertIn("/session/broadcast/handoff/claim", result.text)
        self.assertIn("/session/broadcast/handoff/collect", result.text)
        self.assertNotIn("sessionStorage", result.text)

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

    def test_browser_claim_joins_existing_broadcast_without_token_in_url_or_storage(self) -> None:
        node = shutil.which("node")
        if node is None:
            self.skipTest("Node.js is required to execute the VibeCast handoff test")
        script = textwrap.dedent(f"""
            import assert from "node:assert/strict"; import fs from "node:fs"; import vm from "node:vm";
            const page = fs.readFileSync({json.dumps(str(PAGE))}, "utf8");
            const scripts = [...page.matchAll(/<script>([\\s\\S]*?)<\\/script>/g)].map(match => match[1]);
            assert.equal(scripts.length, 2);
            const make = () => ({{textContent:"",hidden:false,src:"",alt:"",max:0,value:0,append(...children){{this.children=children;}}}});
            const elements = new Map(); for(const id of ["state","artwork","mood","title","artist","moment","progress","album","time","handoff"]) elements.set(id,make());
            const listeners = new Map(), timers = [], calls = [], sockets = [];
            class WS {{ constructor(url) {{ this.url=url; sockets.push(this); }} close() {{}} }}
            class Event {{ constructor(type, options) {{ this.type=type; this.detail=options.detail; }} }}
            const window = {{location:{{protocol:"https:",host:"receiver.test",search:""}},
                addEventListener:(type,callback)=>listeners.set(type,callback),
                dispatchEvent:event=>listeners.get(event.type)(event),
                setTimeout:callback=>{{timers.push(callback);return timers.length;}},
                fetch:async(path,options)=>{{ calls.push({{path,options}}); const result=calls.length===1
                    ? {{claim_id:"claim-id",claim_secret:"private-secret",code:"123456"}}
                    : {{state:"approved",session_id:"session-1",broadcast_token:"runtime-token"}};
                    return {{ok:true,json:async()=>result}}; }} }};
            const context={{URLSearchParams,JSON,Math,Number,Array,Object,String,encodeURIComponent,navigator:{{language:"de-DE"}},
                document:{{body:{{classList:{{toggle:()=>{{}}}}}},documentElement:{{style:{{setProperty:()=>{{}}}}}},
                    getElementById:id=>elements.get(id),createElement:()=>make()}},window,WebSocket:WS,CustomEvent:Event}};
            vm.runInNewContext(scripts[0],context); vm.runInNewContext(scripts[1],context);
            for(let i=0;i<12;i++) await Promise.resolve();
            assert.equal(elements.get("handoff").children[1].textContent,"123456");
            assert.match(elements.get("handoff").children[0].textContent,/Gib diesen Code/);
            assert.equal(context.document.documentElement.lang,"de");
            assert.equal(elements.get("title").textContent,"Warten auf eine Session");
            assert.equal(calls[0].path,"/api/djconnect/v1/session/broadcast/handoff/claim");
            assert.equal(calls[1].path,"/api/djconnect/v1/session/broadcast/handoff/collect");
            assert.equal(JSON.parse(calls[1].options.body).claim_secret,"private-secret");
            assert.equal(sockets[0].url,"wss://receiver.test/api/djconnect/v1/session/broadcast/ws/session-1?broadcast_token=runtime-token");
            assert.equal(window.location.search,""); assert.equal(elements.get("handoff").hidden,true);
            assert.equal(page.includes("localStorage"),false); assert.equal(page.includes("sessionStorage"),false);
        """)
        completed = subprocess.run([node, "--input-type=module", "--eval", script], check=False, capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
