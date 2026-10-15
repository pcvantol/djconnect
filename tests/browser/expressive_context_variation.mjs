// Real HA HTTP/WebSocket -> pinned shared renderer. CAF delivery alone is modeled.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import https from 'node:https';
import {randomBytes,createHash} from 'node:crypto';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const {chromium}=require(process.env.DJC_PLAYWRIGHT || 'playwright');
const out=process.env.DJC_LAB_ROOT || '/lab', haPort=process.env.DJC_HA_PORT || '18197',castPort=process.env.DJC_CAST_PORT || '18198';
const ca=fs.readFileSync(out+'/ca.pem');
const request=path=>new Promise((resolve,reject)=>{
 https.get('https://localhost:'+haPort+path,{ca},res=>{let data='';res.on('data',s=>data+=s);res.on('end',()=>{try{assert.equal(res.statusCode,200);resolve(JSON.parse(data));}catch(e){reject(e);}});}).on('error',reject);
});
const sdk=`let ready=false,listener;const caf={addEventListener:(type,cb)=>{if(type==='ready')listener=cb},isSystemReady:()=>ready,addCustomMessageListener:(ns,cb)=>{window.__receive=cb},sendCustomMessage:(ns,id,data)=>{(window.__castStatuses||(window.__castStatuses=[])).push({id,data})},start:()=>{ready=true;listener()}};window.cast={framework:{CastReceiverContext:{getInstance:()=>caf},system:{EventType:{READY:'ready',SENDER_DISCONNECTED:'disconnected'},MessageType:{JSON:'JSON'}}}};`;
const launch={executablePath:process.env.DJC_CHROMIUM || '/usr/bin/chromium',headless:true,chromiumSandbox:!!process.env.DJC_CHROME_PROFILE};
// The native fallback uses a separate test profile with one locally trusted CA.
// New incognito contexts inherit its normal certificate verification; no TLS
// errors are ignored and no system/browser-user trust store is changed.
const persistent=process.env.DJC_CHROME_PROFILE?await chromium.launchPersistentContext(process.env.DJC_CHROME_PROFILE,launch):null;
const browser=persistent?persistent.browser():await chromium.launch({...launch,args:['--no-sandbox']});
fs.mkdirSync(out+'/context-browser',{recursive:true});
const receipts=[];
try{
for(const host of ['local','cast']) for(const [orientation,width,height] of [['portrait',1200,1920],['landscape',1920,1200]]){
 for(const family of ['birth','formation','description','edition','genre']) for(const locale of ['en','nl','de','fr','es']) for(const persona of ['home_dj','radio_dj','club_dj','festival_dj']){
  const context=await browser.newContext({viewport:{width,height},locale});
  const page=await context.newPage(), errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.clock.install();
  await page.route('https://www.gstatic.com/**',route=>route.fulfill({contentType:'application/javascript',body:sdk}));
  const handoff=await request(`/__lab/setup?lang=${locale}&persona=${persona}&family=${family}`);
  if(host==='cast'){handoff.status_version=1;handoff.handoff_id=randomBytes(16).toString('hex');}
  // Exercise the real claim/approval flow on representative cases. The matrix
  // otherwise uses the renderer's existing scoped read-only grant URL, so it
  // does not exhaust one fixture owner's ten-approval/minute security limit.
  const claimFlow=host==='local'&&locale==='nl'&&persona==='home_dj';
  const localPath='/djconnect/vibecast'+(claimFlow?'':`?session_id=${encodeURIComponent(handoff.session_id)}&broadcast_token=${encodeURIComponent(handoff.broadcast_token)}`);
  await page.goto('https://localhost:'+(host==='cast'?castPort+'/':haPort+localPath));
  if(host==='cast') await page.evaluate(h=>window.__receive({data:h,senderId:'software-sender'}),handoff);
  else if(claimFlow){
   await page.locator('#handoff strong').waitFor();const code=await page.locator('#handoff strong').textContent();
   assert.equal((await request('/__lab/approve?code='+code)).success,true);await page.clock.runFor(1200);
  }
  const series=[], rendered=[];
  for(let number=0;number<12;number++){
   const item=await request('/__lab/publish?number='+number);series.push(item);
   assert.deepEqual(item.owner_snapshot.dj_moments,item.snapshot.dj_moments);
   const m=item.moment;if(!m)continue;
   if(!['artist','album','genre'].includes(m.type))continue;
   await page.clock.runFor(900);
   await page.waitForFunction(text=>document.querySelector('#moment-detail').textContent===text,m.content);
   await page.waitForFunction(text=>{const e=document.querySelector('#moment-card');return !e.hidden&&parseFloat(getComputedStyle(e).opacity)>=0.99&&document.querySelector('#moment-detail').textContent===text;},m.content);
   assert.equal(await page.locator('#moment').textContent(),m.summary);
   assert.equal(await page.locator('html').getAttribute('lang'),locale);
   assert.equal(await page.locator('#title').textContent(),item.snapshot.playback.title);
   if(m.source_attribution?.url)assert.equal(await page.locator('#moment-source').getAttribute('href'),m.source_attribution.url);
   assert.equal(await page.locator('#end-session').isVisible(),false);
   const box=await page.locator('#moment-card').boundingBox();
   assert.ok(box.width>200&&box.height>60&&box.x>=0&&box.y>=0&&box.x+box.width<=width+1&&box.y+box.height<=height+1);
   const detail=await page.locator('#moment-detail').evaluate(e=>({height:e.clientHeight,scroll:e.scrollHeight,width:e.clientWidth,scrollWidth:e.scrollWidth,font:parseFloat(getComputedStyle(e).fontSize)}));
   assert.ok(detail.font>=20&&detail.scrollWidth<=detail.width+1&&detail.scroll<=detail.height+1,JSON.stringify(detail));
   rendered.push(m);
   if(locale==='nl')await page.screenshot({path:`${out}/context-browser/${host}-${orientation}-${family}-${persona}-${rendered.length}.png`});
   if(rendered.length===2)break;
  }
  assert.equal(rendered.length,2,{host,orientation,family,locale,persona});
  if(locale==='nl'&&persona==='home_dj'){
   await context.setOffline(true);await page.clock.runFor(1200);await context.setOffline(false);await page.clock.runFor(1800);
   assert.equal(await page.locator('#moment-detail').textContent(),rendered.at(-1).content);
  }
  if(host==='cast')assert.ok((await page.evaluate(()=>window.__castStatuses)).every(s=>s.id==='software-sender'&&!JSON.stringify(s).includes('broadcast_token')));
  assert.equal(await page.evaluate(()=>localStorage.length+sessionStorage.length),0);
  await request('/__lab/action?name=end');await page.clock.runFor(900);
  await page.waitForFunction(()=>document.querySelector('#moment-card').hidden);
  assert.deepEqual(errors,[]);
  receipts.push({host,orientation,family,locale,persona,series,rendered,tls:'trusted isolated CA; no TLS bypass',transport:'real Core scoped read-only Broadcast grant/HA WebSocket',claimFlow,CAF:host==='cast'?'MODELED_ONLY':'NOT_APPLICABLE'});
  await context.close();
 }
 console.log(`Completed ${host}/${orientation}: ${receipts.length} cases`);
}
const manifest=fs.readFileSync(out+'/build/manifest.json');
fs.writeFileSync(out+'/context-browser/browser-acceptance.json',JSON.stringify({software_only:true,renderer_manifest_sha256:createHash('sha256').update(manifest).digest('hex'),build:JSON.parse(manifest),receipts,checks:{cases:receipts.length,forms:receipts.reduce((n,r)=>n+r.rendered.length,0),owner_shared_equal:true,source_links:true,readability:true,portrait_landscape:true,end:true,reconnect:true,private_storage_empty:true}},null,2));
}finally{if(persistent)await persistent.close();else await browser.close();}
