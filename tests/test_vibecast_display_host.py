"""Causal browser-host races; deterministic JS time, not HA acceptance."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest


class DisplayHostRaceTests(unittest.TestCase):
    def test_display_reissues_code_only_after_current_grant_ends(self):
        node = shutil.which("node")
        if node is None:
            self.skipTest("Node.js required")
        source = Path(__file__).resolve().parents[1] / "custom_components/djconnect/vibecast_renderer/display-host.js"
        script = r'''
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
const source=fs.readFileSync(SOURCE_PATH,"utf8");
for(const scenario of ["late-pending","late-admitted","revoked","disconnected","expired","renew-denied"]){
  let time=0, resolveCollect, claims=0, socket, serial=0, clears=0;
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
    crypto:{getRandomValues:bytes=>bytes.fill(claims+1)},btoa:value=>Buffer.from(value,"binary").toString("base64"),
    AbortController,Event,CustomEvent:class{},WebSocket:class{
      constructor(){socket=this}
      close(){}
    },
    setTimeout:(fn,delay)=>{timers.set(++serial,{fn,delay});return serial},clearTimeout:id=>timers.delete(id),
    document:{getElementById:()=>panel,createElement:element,querySelector:()=>header,addEventListener(){}},
    window:{addEventListener(){},dispatchEvent(event){if(event.type==="djconnect-display-clear")clears++}},
    fetch:async (path,options)=>{
      if(path.endsWith("/claim")){
        assert.equal(options.headers.Authorization,undefined);
        assert.equal(JSON.parse(options.body).browser_nonce,Buffer.alloc(32,claims+1).toString("base64url"));
        return response({contract_version:1,code:++claims===1?"123456":"654321",expires_in:120,
        issuer_epoch:"epoch",claim_id:"claim",claim_secret:"secret",browser_generation:"generation"});}
      if(path.endsWith("/renew"))return {ok:false,status:401,text:async()=>JSON.stringify({error:"display_grant_invalid"})};
      return new Promise(resolve=>{resolveCollect=resolve});
    }};
  vm.runInNewContext(source,context);
  await new Promise(setImmediate);
  assert.equal(panel.children.some(child=>child.tag==="strong"),true);
  assert.equal(header.children.length,0);
  if(!scenario.startsWith("late-")){
    resolveCollect(response({state:"admitted",grant_token:"djcd_"+"A".repeat(43),lease_expires_in:60,
      capabilities:{owner_controls:false,session_end:false}}));
    await new Promise(setImmediate);
    const previousClears=clears;
    if(scenario==="disconnected"){
      socket.onclose({code:1006});
      assert.equal(claims,1);
      [...timers.values()].find(timer=>timer.delay===1500).fn();
    }
    const previousSocket=socket, previousClose=socket.onclose;
    if(scenario==="revoked" || scenario==="disconnected")previousClose({code:1008});
    if(scenario==="expired"){
      time=60000;
      [...timers.values()].find(timer=>timer.delay===1000).fn();
    }
    if(scenario==="renew-denied"){
      time=20000;
      [...timers.values()].find(timer=>timer.delay===20000).fn();
    }
    await new Promise(setImmediate);
    assert.ok(clears>previousClears);
    assert.equal(socket,previousSocket);
    assert.equal(claims,2);
    assert.equal(panel.children.find(child=>child.tag==="strong").textContent,"654321");
    assert.equal(panel.children.some(child=>child.tag==="button"),false);
    previousClose({code:1008});
    assert.equal(claims,2);
    continue;
  }
  time=120001;
  resolveCollect(response({state:scenario.slice(5),grant_token:"djcd_"+"A".repeat(43),lease_expires_in:60}));
  await new Promise(setImmediate);
  assert.match(panel.children[0].textContent,/access has expired/);
  assert.equal(panel.children.some(child=>child.tag==="strong"),false);
  const retry=panel.children.find(child=>child.tag==="button");
  assert.equal(retry.textContent,"Request a new code");
  assert.equal(socket,undefined);
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
