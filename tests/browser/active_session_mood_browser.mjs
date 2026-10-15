// Actual paired-owner POST -> HA Broadcast -> unchanged shared renderer.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import https from 'node:https';
import {randomBytes} from 'node:crypto';
const {chromium}=await import(process.env.DJC_PLAYWRIGHT || 'playwright');
const lab=process.env.DJC_LAB_ROOT;
const ca=fs.readFileSync(lab+'/ca.pem');
const get=path=>new Promise((resolve,reject)=>https.get('https://localhost:18203/__mood_lab/'+path,{ca},res=>{let body='';res.on('data',s=>body+=s);res.on('end',()=>{try{assert.equal(res.statusCode,200);resolve(JSON.parse(body));}catch(e){reject(e);}});}).on('error',reject));
const sdk=`let ready=false,listener;const caf={addEventListener:(type,cb)=>{if(type==='ready')listener=cb},isSystemReady:()=>ready,addCustomMessageListener:(ns,cb)=>{window.__receive=cb},sendCustomMessage:(ns,id,data)=>{(window.__statuses||(window.__statuses=[])).push({id,data})},start:()=>{ready=true;listener()}};window.cast={framework:{CastReceiverContext:{getInstance:()=>caf},system:{EventType:{READY:'ready',SENDER_DISCONNECTED:'disconnected'},MessageType:{JSON:'JSON'}}}};`;
const browser=await chromium.launch({executablePath:process.env.DJC_CHROMIUM || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true,args:['--ignore-certificate-errors-spki-list='+process.env.DJC_LAB_SPKI]});
const receipts=[];fs.mkdirSync(lab+'/browser',{recursive:true});
try{
 for(const host of ['local','cast'])for(const [orientation,width,height] of [['portrait',1200,1920],['landscape',1920,1200]]){
  const context=await browser.newContext({viewport:{width,height}}),page=await context.newPage(),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.clock.install();
  await page.route('https://www.gstatic.com/**',route=>route.fulfill({contentType:'application/javascript',body:sdk}));
  const handoff=await get('setup');handoff.status_version=1;handoff.handoff_id=randomBytes(16).toString('hex');
  await page.goto(host==='local'?`https://localhost:18203/djconnect/vibecast?session_id=${handoff.session_id}&broadcast_token=${handoff.broadcast_token}`:'https://localhost:18204/');
  if(host==='cast')await page.evaluate(h=>window.__receive({data:h,senderId:'owned-software-sender'}),handoff);
  const first=await get('publish?number=0');
  await page.waitForTimeout(300);await page.clock.runFor(1500);
  await page.waitForFunction(t=>document.querySelector('#moment-detail').textContent===t,first.moment.content);
  assert.equal(first.moment.presentation_intent.source_session_mood,'groove');
  const frozen=JSON.stringify(first.snapshot.dj_moments);
  const changed=await get('mood?value=party');assert.equal(changed.mood_revision,1);await page.waitForTimeout(300);await page.clock.runFor(1000);
  await page.waitForFunction(()=>document.querySelector('#mood').textContent==='party');
  const current=await get('snapshot');assert.equal(JSON.stringify(current.dj_moments),frozen);
  assert.equal(current.session.session_id,handoff.session_id);
  assert.equal(await page.locator('#moment-detail').textContent(),first.moment.content);
  const second=await get('publish?number=1');
  assert.equal(second.moment.presentation_intent.source_session_mood,'party');
  await page.clock.runFor(1000);
  await page.waitForFunction(t=>document.querySelector('#moment-detail').textContent===t,second.moment.content);
  await page.clock.runFor(1500);
  await page.waitForFunction(()=>parseFloat(getComputedStyle(document.querySelector('#moment-card')).opacity)>=0.99);
  assert.equal(await page.locator('#moment-source').getAttribute('href'),second.moment.source_attribution.url);
  assert.equal(await page.locator('#end-session').isVisible(),false);
  assert.equal(await page.evaluate(()=>localStorage.length+sessionStorage.length),0);
  const box=await page.locator('#moment-card').boundingBox();assert.ok(box.width>200&&box.height>60&&box.x>=0&&box.y>=0&&box.x+box.width<=width+1&&box.y+box.height<=height+1);
  await page.screenshot({path:`${lab}/browser/${host}-${orientation}-party.png`});
  await context.setOffline(true);await page.waitForTimeout(1200);await context.setOffline(false);await page.waitForTimeout(2200);
  assert.equal(await page.locator('#mood').textContent(),'party');
  assert.equal(await page.locator('#moment-detail').textContent(),second.moment.content);
  if(host==='cast'){
   await page.waitForFunction(()=>window.__statuses.some(s=>s.data.state==='presenting'));
   assert.ok((await page.evaluate(()=>window.__statuses)).every(s=>!JSON.stringify(s).includes('broadcast_token')));
  }
  await page.clock.fastForward(100000);await page.waitForTimeout(1000);
  assert.equal(await page.locator('#moment-detail').textContent(),'');
  await get('end');await page.waitForFunction(()=>document.querySelector('#title').textContent==='Wachten op een sessie');
  if(host==='cast')assert.equal((await page.evaluate(()=>window.__statuses)).at(-1).data.state,'ended');
  assert.deepEqual(errors,[]);
  await page.screenshot({path:`${lab}/browser/${host}-${orientation}-ended.png`});
  receipts.push({host,orientation,viewport:{width,height},owner_post:true,immutable_cards_preserved:true,future_mood:'party',source_links:true,reconnect:true,expiry:true,end:true,cast_status:host==='cast'?'MODELED_CAF_ONLY':'NOT_APPLICABLE',tls:'Node trusts owned CA; browser permits only owned server SPKI',hardware:'NOT_RUN'});
  await context.close();
 }
 fs.writeFileSync(lab+'/browser-receipt.json',JSON.stringify({receipts,renderer_version:'1.1.0',renderer_source_revision:'ad178c7b88d8f2e502c2930afe95352554838572',native:'NOT_RUN',installed:'NOT_RUN',hardware:'NOT_RUN'},null,2));
 console.log('PASS: four actual owner POST/Broadcast/shared-renderer sequences');
}finally{await browser.close();}
