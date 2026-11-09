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
for(const scenario of ["late-pending","late-admitted","revoked","disconnected","expired","renew-denied","reload","cached-page","capacity"]){
  let time=0, resolveCollect, claims=0, socket, serial=0, clears=0;
  const timers=new Map(), handlers=new Map(), clipboard=[];
  const history={state:null,replaceState(state){this.state=state}};
  function element(tag="span"){
    const value={tag,children:[],hidden:false,classList:new Set(),append(child){this.children.push(child)},setAttribute(){}};
    Object.defineProperty(value,"textContent",{get(){return this._text || ""},set(text){this._text=text;this.children=[]}});
    return value;
  }
  const panel=element(),header=element();
  const codeBlock=()=>panel.children.find(child=>child.className==="handoff-code");
  const digits=()=>codeBlock()?.children.find(child=>child.tag==="strong");
  const response=value=>({ok:true,status:200,text:async()=>JSON.stringify({success:true,...value})});
  const context={navigator:{language:"en",onLine:true,clipboard:{writeText:async value=>clipboard.push(value)}},performance:{now:()=>time},
    location:{protocol:"https:",origin:"https://ha.example.test",search:"",hash:""},
    crypto:{getRandomValues:bytes=>bytes.fill(claims+1)},btoa:value=>Buffer.from(value,"binary").toString("base64"),
    AbortController,Event,CustomEvent:class{},WebSocket:class{
      constructor(){socket=this}
      close(){}
    },
    setTimeout:(fn,delay)=>{timers.set(++serial,{fn,delay});return serial},clearTimeout:id=>timers.delete(id),
    document:{getElementById:()=>panel,createElement:element,querySelector:()=>header,addEventListener(){}},
    window:{history,addEventListener(type,handler){handlers.set(type,handler)},dispatchEvent(event){if(event.type==="djconnect-display-clear")clears++}},
    fetch:async (path,options)=>{
      if(path.endsWith("/claim")){
        assert.equal(options.headers.Authorization,undefined);
        const body=JSON.parse(options.body);
        assert.equal(body.browser_nonce,Buffer.alloc(32,claims+1).toString("base64url"));
        assert.equal(body.request_id,Buffer.alloc(32,1).toString("base64url"));
        claims++;
        if(scenario==="capacity" && claims<=2){
          return {ok:false,status:429,text:async()=>JSON.stringify({error:"display_capacity"})};
        }
        const resumed=["reload","cached-page"].includes(scenario) && claims===2;
        return response({contract_version:1,code:claims===1 || resumed?"123456":"654321",expires_in:resumed?75:120,
        issuer_epoch:"epoch",claim_id:"claim",claim_secret:"secret",browser_generation:"generation"});}
      if(path.endsWith("/renew"))return {ok:false,status:401,text:async()=>JSON.stringify({error:"display_grant_invalid"})};
      assert.ok(path.endsWith("/collect"),path);
      return new Promise(resolve=>{resolveCollect=resolve});
    }};
  vm.runInNewContext(source,context);
  assert.equal(panel.hidden,false);
  assert.deepEqual(panel.children.map(child=>child.className),["handoff-placeholder","handoff-code handoff-placeholder"]);
  assert.equal(panel.children[1].children[0].textContent.trim(),"");
  await new Promise(setImmediate);
  if(scenario==="capacity"){
    assert.equal(claims,1);
    const retry=[...timers.entries()].find(([,timer])=>timer.delay===800);
    assert.ok(retry);
    timers.delete(retry[0]);
    retry[1].fn();
    await new Promise(setImmediate);
    assert.equal(claims,2);
    assert.equal([...timers.values()].some(timer=>timer.delay===800),false);
    assert.ok(panel.children.some(child=>child.className==="handoff-retry"));
    continue;
  }
  assert.equal(digits()?.textContent,"123456");
  const copy=codeBlock().children.find(child=>child.className==="handoff-copy");
  await copy.onclick();
  assert.deepEqual(clipboard,["123456"]);
  assert.equal(copy.title,"Code copied");
  assert.equal(header.children.length,0);
  if(scenario==="reload" || scenario==="cached-page"){
    time=45000;
    if(scenario==="cached-page"){
      handlers.get("pagehide")({persisted:true});
      assert.equal(panel.hidden,true);
      assert.deepEqual(Object.keys(history.state),["vibeCastClaimRequestId"]);
      await handlers.get("pageshow")({persisted:true});
    }else{
      timers.clear();
      vm.runInNewContext(source,context);
    }
    await new Promise(setImmediate);
    assert.equal(claims,2);
    assert.equal(digits()?.textContent,"123456");
    const rotation=[...timers.values()].find(timer=>timer.delay===75000);
    assert.ok(rotation);
    time=120000;
    rotation.fn();
    await new Promise(setImmediate);
    assert.equal(claims,3);
    assert.equal(digits()?.textContent,"654321");
    continue;
  }
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
    assert.equal(digits()?.textContent,"654321");
    assert.equal(panel.children.some(child=>child.tag==="button"),false);
    previousClose({code:1008});
    assert.equal(claims,2);
    continue;
  }
  const previousCollect=resolveCollect;
  time=120000;
  await copy.onclick();
  assert.deepEqual(clipboard,["123456"]);
  const rotation=[...timers.values()].find(timer=>timer.delay===120000);
  assert.ok(rotation);
  rotation.fn();
  await new Promise(setImmediate);
  assert.equal(claims,2);
  assert.equal(digits()?.textContent,"654321");
  previousCollect(response({state:scenario.slice(5),grant_token:"djcd_"+"A".repeat(43),lease_expires_in:60,
    capabilities:{owner_controls:false,session_end:false}}));
  await new Promise(setImmediate);
  assert.equal(socket,undefined);
  assert.equal(digits()?.textContent,"654321");
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
