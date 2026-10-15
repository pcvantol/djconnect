// Actual HA HTTP/WebSocket -> shared renderer; CAF message delivery alone is modelled.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import https from 'node:https';
import {randomBytes} from 'node:crypto';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const {chromium}=require(process.env.DJC_PLAYWRIGHT || '/node_modules/playwright');
const out=process.env.DJC_LAB_ROOT || '/lab';
const haPort=process.env.DJC_HA_PORT || '18193',castPort=process.env.DJC_CAST_PORT || '18194';
const ca=fs.readFileSync(out+'/ca.pem');
const request=(path,origin)=>new Promise((resolve,reject)=>{
 https.get('https://localhost:'+haPort+path,{ca,headers:origin?{Origin:origin}:{}},res=>{let data='';res.on('data',s=>data+=s);res.on('end',()=>resolve({status:res.statusCode,headers:res.headers,body:JSON.parse(data)}));}).on('error',reject);
});
const sdk=`let ready=false,listener;const caf={addEventListener:(type,cb)=>{if(type==='ready')listener=cb},isSystemReady:()=>ready,addCustomMessageListener:(ns,cb)=>{window.__castNamespace=ns;window.__receive=cb},sendCustomMessage:(ns,id,data)=>{(window.__castStatuses||(window.__castStatuses=[])).push({id,data})},start:options=>{window.__castOptions=options;ready=true;listener();window.__castStarted=true}};window.cast={framework:{CastReceiverContext:{getInstance:()=>caf},system:{EventType:{READY:'ready',SENDER_DISCONNECTED:'disconnected'},MessageType:{JSON:'JSON'}}}};`;
const browser=await chromium.launch({executablePath:process.env.DJC_CHROMIUM || '/usr/bin/chromium',headless:true,args:['--no-sandbox']});
const receipts=[];fs.mkdirSync(out+'/browser',{recursive:true});
try{
 for(const host of ['before','local','cast'])for(const locale of (host==='before'?['nl']:['en','nl','de','fr','es'])){
  const width=host!=='cast'?1200:1920,height=host!=='cast'?1920:1080;
  const context=await browser.newContext({viewport:{width,height},locale,recordVideo:locale==='nl'?{dir:out+'/browser',size:{width,height}}:undefined});
  const page=await context.newPage();if(locale==='nl' && host!=='before')await page.clock.install();const errors=[];page.on('pageerror',e=>errors.push(e.message));
  let sdkLoads=0;
  await page.route('https://www.gstatic.com/**',route=>{sdkLoads++;return route.fulfill({contentType:'application/javascript',body:sdk});});
  const handoff=(await request('/__lab/setup?lang='+locale)).body;
  if(host==='cast'){handoff.status_version=1;handoff.handoff_id=randomBytes(16).toString('hex');}
  await page.goto(host==='before'?'https://localhost:'+haPort+'/__lab/before':host==='local'?'https://localhost:'+haPort+'/djconnect/vibecast':'https://localhost:'+castPort+'/');
  if(host!=='cast'){
   await page.locator('#handoff strong').waitFor();const code=await page.locator('#handoff strong').textContent();assert.equal((await request('/__lab/approve?code='+code)).body.success,true);
  }else{
   assert.equal(await page.evaluate(()=>window.__castNamespace),'urn:x-cast:com.djconnect.vibecast.v1');
   await page.evaluate(h=>window.__receive({data:h,senderId:"software-sender"}),handoff);
  }
  const first=(await request('/__lab/publish?number=0')).body;
  assert.ok(first.moment);
  await page.waitForFunction(t=>document.querySelector('#moment').textContent===t,first.moment.summary);
  await page.screenshot({path:`${out}/browser/${host}-${locale}-ordinary.png`});
  const second=(await request('/__lab/publish?number=1')).body;
  assert.match(second.moment.content,/Recording 0/);
  await page.waitForFunction(t=>document.querySelector('#moment').textContent===t,second.moment.summary);
  assert.equal(await page.locator('html').getAttribute('lang'),locale);
  assert.equal(await page.locator('#title').textContent(),'Recording 1');
  assert.equal(await page.locator('#moment-source').getAttribute('href'),second.moment.source_attribution.url);
  assert.equal(await page.locator('#moment-source-previous').getAttribute('href'),second.moment.source_attribution.url_previous);
  assert.equal(await page.locator('#end-session').isVisible(),false);
  await page.waitForFunction(()=>document.querySelector('#artwork').naturalWidth>0);
  assert.equal(sdkLoads,host!=='cast'?0:1);
  assert.equal(await page.evaluate(()=>localStorage.length+sessionStorage.length),0);
  await page.waitForTimeout(900);
  const box=await page.locator('#moment-card').boundingBox();assert.ok(box.width>200 && box.height>60 && box.x>=0 && box.y>=0 && box.x+box.width<=width+1 && box.y+box.height<=height+1);
  await page.screenshot({path:`${out}/browser/${host}-${locale}-shared.png`});
  if(host!=='before') {
   const later=(await request('/__lab/action?name=later')).body;
   assert.ok(later.moment,'Real same-track later opportunity missing');
   await page.waitForFunction(t=>document.querySelector('#moment').textContent===t,later.moment.summary);
   assert.equal(await page.locator('#title').textContent(),'Recording 1');
   await page.screenshot({path:`${out}/browser/${host}-${locale}-later.png`});
   second.latest=later.moment;
  }
  // Real transport reconnect (no frames supplied by the browser test).
  await context.setOffline(true);await page.waitForTimeout(1200);await context.setOffline(false);
  await page.waitForTimeout(1800);
  assert.equal(await page.locator('#moment').textContent(),(second.latest || second.moment).summary);
  assert.equal(await page.locator('#moment-detail').textContent(),(second.latest || second.moment).content);
  if(host==='cast'){
   await page.waitForFunction(()=>window.__castStatuses.some(s=>s.data.state==='presenting'));
   assert.ok((await page.evaluate(()=>window.__castStatuses)).every(s=>s.id==='software-sender' && !JSON.stringify(s).includes('broadcast_token')));
   handoff.handoff_id=randomBytes(16).toString('hex');
   // A renewed valid handoff resets transport/sequence; an old sender cannot uplift control.
   await page.evaluate(h=>window.__receive({senderId:"software-sender",data:{...h,end_grant:'invented-owner-authority'}}),handoff);
   await page.waitForFunction(t=>document.querySelector('#moment').textContent===t,(second.latest || second.moment).summary);
   assert.equal(await page.locator('#end-session').isVisible(),false);
  }
  if(locale==='nl' && host!=='before') {
   if(host==='cast') {
    await page.evaluate(h=>window.__receive({senderId:"software-sender",data:{...h,version:2}}),handoff);
    assert.equal(await page.locator('#moment').textContent(),'');
    await page.evaluate(h=>window.__receive({senderId:"software-sender",data:{...h,ha_url:'http://localhost:18193'}}),handoff);
    assert.equal(await page.locator('#moment').textContent(),'');
    handoff.handoff_id=randomBytes(16).toString('hex');
    await page.evaluate(h=>window.__receive({data:h,senderId:"software-sender"}),handoff);
    await page.waitForFunction(t=>document.querySelector('#moment').textContent===t,(second.latest || second.moment).summary);
   }
   await page.clock.fastForward(100000);
   await page.waitForTimeout(1000);
   assert.equal(await page.locator('#moment').textContent(),'');
   if(host==='cast') {handoff.handoff_id=randomBytes(16).toString('hex'); await page.evaluate(h=>window.__receive({data:h,senderId:"software-sender"}),handoff);}
   await page.waitForTimeout(1500);
   assert.equal(await page.locator('#moment').textContent(),'');
  }
  await request('/__lab/action?name=end');
  await page.waitForFunction(()=>document.querySelector('#moment').textContent==='');
  assert.equal(await page.locator('#title').textContent(),({en:'Waiting for a session',nl:'Wachten op een sessie',de:'Warten auf eine Session',fr:'En attente d’une session',es:'Esperando una sesión'})[locale]);
  assert.equal(await page.locator('#artwork').isVisible(),false);
  await page.screenshot({path:`${out}/browser/${host}-${locale}-ended.png`});
  if(host==='cast'){assert.equal((await page.evaluate(()=>window.__castStatuses)).at(-1).data.state,'ended');fs.writeFileSync(`${out}/browser/${host}-${locale}-status.json`,JSON.stringify(await page.evaluate(()=>window.__castStatuses),null,2));}
  assert.deepEqual(errors,[]);
  receipts.push({host,locale,viewport:{width,height},first:first.moment,second:second.moment,later:second.latest,snapshot_watermark:second.snapshot.broadcast.snapshot_watermark,tls:'trusted isolated CA; no ignoreHTTPSErrors',real_transport:'HA HTTP claim / actual Core Broadcast WebSocket',cast_messages:host==='cast'?'MODELED_CAF_ONLY':'NOT_APPLICABLE',sdkLoads,lifecycle:'reconnect, renewed handoff, Runtime-end PASS'});
  await context.close();
 }
 fs.writeFileSync(out+'/browser-scenarios-receipt.json',JSON.stringify({receipts,hardware:'NOT_TESTED'},null,2));
 // Actual delayed collect response must not revive a stopped host.
 const stoppedContext=await browser.newContext({viewport:{width:1200,height:1920}});
 const stoppedPage=await stoppedContext.newPage();let release,entered;
 const held=new Promise(resolve=>release=resolve), waiting=new Promise(resolve=>entered=resolve);let sockets=0;
 stoppedPage.on('websocket',()=>sockets++);
 await request('/__lab/setup?lang=nl');
 await stoppedPage.route('**/handoff/collect',async route=>{entered();await held;const response=await route.fetch();await route.fulfill({response});});
 await stoppedPage.goto('https://localhost:'+haPort+'/djconnect/vibecast');await waiting;
 const code=await stoppedPage.locator('#handoff strong').textContent();await request('/__lab/approve?code='+code);
 await stoppedPage.evaluate(()=>window.dispatchEvent(new CustomEvent('djconnect-host-stop')));release();
 await stoppedPage.waitForTimeout(1800);assert.equal(sockets,0);assert.equal(await stoppedPage.locator('#moment').textContent(),'');
 await stoppedContext.close();
 const denied=await request('/api/djconnect/v1/session/broadcast/ws/any?broadcast_token=synthetic','https://unapproved.test');
 assert.equal(denied.status,403);assert.equal(denied.headers['cache-control'],'no-store');
 assert.equal(denied.body.error,'receiver_origin_not_allowed');
 fs.writeFileSync(out+'/browser-receipt.json',JSON.stringify({receipts,origin_denial:denied,hardware:'NOT_TESTED'},null,2));
 console.log('PASS: eleven actual TLS/Core-Broadcast browser sequences, five languages, two hosts');
}finally{await browser.close();}
