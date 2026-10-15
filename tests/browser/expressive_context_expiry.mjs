// Supplement the complete matrix with actual renderer expiry and reconnect.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import https from 'node:https';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const {chromium}=require(process.env.DJC_PLAYWRIGHT || 'playwright');
const root=process.env.DJC_LAB_ROOT,ha=process.env.DJC_HA_PORT || '18197',cast=process.env.DJC_CAST_PORT || '18198';
const ca=fs.readFileSync(root+'/ca.pem');
const request=path=>new Promise((resolve,reject)=>https.get('https://localhost:'+ha+path,{ca},r=>{let data='';r.on('data',s=>data+=s);r.on('end',()=>{try{assert.equal(r.statusCode,200);resolve(JSON.parse(data));}catch(e){reject(e);}});}).on('error',reject));
const sdk=`let cb;const caf={addEventListener:(t,f)=>{if(t==='ready')cb=f},isSystemReady:()=>true,addCustomMessageListener:(n,f)=>{window.__receive=f},sendCustomMessage:()=>{},start:()=>cb()};window.cast={framework:{CastReceiverContext:{getInstance:()=>caf},system:{EventType:{READY:'ready',SENDER_DISCONNECTED:'disconnected'},MessageType:{JSON:'JSON'}}}};`;
const profile=await chromium.launchPersistentContext(process.env.DJC_CHROME_PROFILE,{executablePath:process.env.DJC_CHROMIUM,headless:true,chromiumSandbox:true});
const results=[];
try{
 for(const host of ['local','cast'])for(const [orientation,width,height] of [['portrait',1200,1920],['landscape',1920,1200]]){
  const context=await profile.browser().newContext({viewport:{width,height}}),page=await context.newPage();
  page.setDefaultTimeout(15000);
  await page.clock.install();await page.route('https://www.gstatic.com/**',r=>r.fulfill({contentType:'application/javascript',body:sdk}));
  const handoff=await request('/__lab/setup?lang=nl&persona=home_dj&family=edition');
  await page.goto(host==='local'?`https://localhost:${ha}/djconnect/vibecast?session_id=${handoff.session_id}&broadcast_token=${handoff.broadcast_token}`:`https://localhost:${cast}/`);
  if(host==='cast')await page.evaluate(h=>window.__receive({data:{...h,status_version:1,handoff_id:'00000000000000000000000000000001'},senderId:'software-expiry'}),handoff);
  const item=await request('/__lab/publish?number=0');assert.ok(item.moment);
  await page.clock.runFor(1200);await page.waitForFunction(text=>document.querySelector('#moment-detail').textContent===text,item.moment.content);
  assert.equal(await page.locator('#moment-card').isVisible(),true);
  await page.clock.fastForward(95000);await page.clock.runFor(1200);
  assert.equal(await page.locator('#moment-card').isVisible(),false);
  await context.setOffline(true);await page.clock.runFor(1200);await context.setOffline(false);await page.clock.runFor(2200);
  assert.equal(await page.locator('#moment-card').isVisible(),false);
  assert.equal(await page.locator('#title').textContent(),item.snapshot.playback.title);
  await request('/__lab/action?name=end');await page.clock.runFor(1200);
  assert.equal(await page.locator('#moment-card').isVisible(),false);
  results.push({host,orientation,expired:true,reconnect_does_not_resurrect:true,end:true,software_only:true,CAF:host==='cast'?'MODELED_ONLY':'NOT_APPLICABLE'});
  await context.close();console.log(`Expiry/reconnect/end PASS ${host}/${orientation}`);
 }
 fs.writeFileSync(root+'/context-browser/expiry-acceptance.json',JSON.stringify({results,tls:'normal verification with isolated profile CA; no bypass'},null,2));
}finally{await profile.close();}
