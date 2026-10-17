"""Causal browser-host races; deterministic JS time, not HA acceptance."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest


class DisplayHostRaceTests(unittest.TestCase):
    def test_collect_response_after_original_deadline_clears_code_and_offers_retry(self):
        node = shutil.which("node")
        if node is None:
            self.skipTest("Node.js required")
        source = Path(__file__).resolve().parents[1] / "custom_components/djconnect/vibecast_renderer/display-host.js"
        script = r'''
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
const source=fs.readFileSync(SOURCE_PATH,"utf8");
for(const state of ["pending","admitted"]){
  let time=0, resolveCollect, claims=0, sockets=0, serial=0;
  const timers=new Map();
  function element(tag="span"){
    const value={tag,children:[],hidden:false,append(child){this.children.push(child)},setAttribute(){}};
    Object.defineProperty(value,"textContent",{get(){return this._text || ""},set(text){this._text=text;this.children=[]}});
    return value;
  }
  const panel=element(),header=element();
  const response=value=>({ok:true,status:200,text:async()=>JSON.stringify({success:true,...value})});
  const context={navigator:{language:"en",onLine:true},performance:{now:()=>time},
    location:{protocol:"https:",origin:"https://ha.example.test",search:"",hash:""},
    crypto:{getRandomValues:bytes=>bytes.fill(42)},btoa:value=>Buffer.from(value,"binary").toString("base64"),
    AbortController,Event,CustomEvent:class{},WebSocket:class{constructor(){sockets++}},
    setTimeout:fn=>{timers.set(++serial,fn);return serial},clearTimeout:id=>timers.delete(id),
    document:{getElementById:()=>panel,createElement:element,querySelector:()=>header,addEventListener(){}},
    window:{addEventListener(){},dispatchEvent(){}},
    fetch:async path=>{
      if(path.endsWith("/claim")){claims++;return response({contract_version:1,code:"123456",expires_in:120,
        issuer_epoch:"epoch",claim_id:"claim",claim_secret:"secret",browser_generation:"generation"});}
      return new Promise(resolve=>{resolveCollect=resolve});
    }};
  vm.runInNewContext(source,context);
  await new Promise(setImmediate);
  assert.equal(panel.children.some(child=>child.tag==="strong"),true);
  time=120001;
  resolveCollect(response({state,grant_token:"djcd_"+"A".repeat(43),lease_expires_in:60}));
  await new Promise(setImmediate);
  assert.match(panel.children[0].textContent,/access has expired/);
  assert.equal(panel.children.some(child=>child.tag==="strong"),false);
  const retry=panel.children.find(child=>child.tag==="button");
  assert.equal(retry.textContent,"Request a new code");
  assert.equal(sockets,0);
  await retry.onclick();
  assert.equal(claims,2);
}
'''.replace("SOURCE_PATH", json.dumps(str(source)))
        result = subprocess.run([node, "--input-type=module", "--eval", script], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_all_generated_hosts_preserve_retired_receiver_end_authority(self):
        from scripts.build_vibecast import render
        root=Path(__file__).resolve().parents[1]
        for host in ('local','cast','display'):
            html=render(root,host)
            for retired in ('endGrant','end_grant','/broadcast/control/end','id="end-session"'):
                self.assertNotIn(retired,html,(host,retired))
            if host in ('local','display'):
                name='vibecast.html' if host=='local' else 'vibecast_display.html'
                self.assertEqual((root/'custom_components/djconnect'/name).read_text(),html)
