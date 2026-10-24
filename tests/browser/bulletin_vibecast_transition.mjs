// Actual shared renderer; synthetic preceding music/withdrawal/short-expiry frames test timer races.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const {chromium,webkit}=require(process.env.DJC_PLAYWRIGHT || 'playwright');
const html=fs.readFileSync(process.argv[2]),raw=fs.readFileSync(process.argv[3]),sample=JSON.parse(raw).extension.sample;
const out=path.resolve(process.argv[4]);fs.mkdirSync(out,{recursive:true});
const server=http.createServer((req,res)=>{res.setHeader('Content-Type','text/html');res.end(html);});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const origin='http://127.0.0.1:'+server.address().port,results=[];
try {
 for(const [engine,type] of [['chromium',chromium],['webkit',webkit]]){
  const opts={headless:true};
  if(engine==='chromium' && fs.existsSync('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'))opts.executablePath='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
  const browser=await type.launch(opts);
  try {for(const race of ['withdraw-during-transition','expiry-during-transition','withdrawn-previous']){
   const context=await browser.newContext({viewport:{width:1280,height:720},reducedMotion:'no-preference'});
   const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
   await context.route('**/*',route=>new URL(route.request().url()).origin===origin ? route.continue() : route.abort());
   const now=Date.parse(sample.moment.created_at)+100;
   await page.clock.install({time:new Date(now)});await page.clock.pauseAt(new Date(now));
   await page.addInitScript(()=>{window.__sockets=[];window.WebSocket=class{constructor(){window.__sockets.push(this)}close(){}};});
   await page.goto(origin+'/?session_id='+encodeURIComponent(sample.moment.session_id)+'&broadcast_token=synthetic-readonly');
   const send=async frame=>page.evaluate(frame=>window.__sockets[0].onmessage({data:JSON.stringify(frame)}),frame);
   const music={moment_id:'synthetic-music',type:'track',summary:'Synthetic preceding music contribution.',
    created_at:new Date(now-1000).toISOString(),playback_item_id:sample.shared_snapshot.playback.item_id};
   const initial=structuredClone(sample.initial_shared_snapshot);initial.dj_moments=[music];
   if(race==='withdrawn-previous')await send({type:'snapshot',snapshot:sample.shared_snapshot});
   else {
    await send({type:'snapshot',snapshot:initial});
    const event=structuredClone(sample.shared_event);
    if(race==='expiry-during-transition')event.data.payload.native_delivery.admissions[0].display_expires_at=new Date(now+100).toISOString();
    await send(event);
   }
   if(race!=='expiry-during-transition'){
    const payload={native_delivery:{schema_version:1,session_id:sample.moment.session_id,admissions:[],active_flow_moment_ids:[],current_moment_id:null}};
    if(race==='withdrawn-previous')payload.dj_moment={...music,moment_id:'synthetic-next',created_at:new Date(now+1).toISOString()};
    await send({type:'event',data:{session_id:sample.moment.session_id,event_type:'session_flow_updated',delivery_sequence:20,payload}});
   }
   await page.clock.runFor(1000);
   const visible=await page.locator('#moment').textContent()+' '+await page.locator('#moment-detail').textContent()+' '+await page.locator('#moment-history').textContent();
   assert(!visible.includes(sample.moment.content),'withdrawn/expired complete bulletin must be absent: '+race);
   assert(!visible.includes('AI-bewerking'),'no retired adaptation text in current or previous card: '+race);
   assert.equal(await page.locator('#moment-research-sources a').count(),0);
   assert.deepEqual(errors,[]);
   await page.screenshot({path:path.join(out,engine+'-'+race+'.png')});
   results.push({engine,race,status:'PASS'});await context.close();
  }} finally {await browser.close();}
 }
} finally {await new Promise(resolve=>server.close(resolve));}
const sha=data=>createHash('sha256').update(data).digest('hex');
const receipt={scope:'ACTUAL_CHROMIUM_WEBKIT_WITH_ACTIVE_TRANSITION_TIMERS_SYNTHETIC_BOUNDARY_FRAMES_NO_DEVICE_PROVIDER',html_sha256:sha(html),original_ha_receipt_sha256:sha(raw),results,status:results.length===6?'PASS':'FAIL'};
fs.writeFileSync(path.join(out,'receipt.json'),JSON.stringify(receipt,null,2)+'\n');console.log(JSON.stringify(receipt));
