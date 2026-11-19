// Actual isolated paired HA -> read-only Broadcast -> unchanged shared renderer.
// Only the external CAF host adapter is modeled. No native/hardware claim.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const {chromium}=require(process.env.DJC_PLAYWRIGHT);
const lab=process.env.DJC_LAB_ROOT;
const ready=JSON.parse(fs.readFileSync(lab+'/browser-ready.json'));
const sdk=`let ready=false,listener;const caf={addEventListener:(type,cb)=>{if(type==='ready')listener=cb},isSystemReady:()=>ready,addCustomMessageListener:(ns,cb)=>{window.__receive=cb},sendCustomMessage:()=>{},start:()=>{ready=true;listener()}};window.cast={framework:{CastReceiverContext:{getInstance:()=>caf},system:{EventType:{READY:'ready',SENDER_DISCONNECTED:'disconnected'},MessageType:{JSON:'JSON'}}}};`;
const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
 headless:true,args:['--ignore-certificate-errors-spki-list='+process.env.DJC_LAB_SPKI]});
fs.mkdirSync(lab+'/browser',{recursive:true});
const handoff={kind:'vibecast_handoff',version:1,ha_url:'https://localhost:18233',
 session_id:ready.session_id,broadcast_token:ready.broadcast_token};
const opened=[];
try {
 await Promise.all(['local','cast'].flatMap(host=>[
  ['portrait',1200,1920],['landscape',1920,1200]].map(async([orientation,width,height])=>{
   const context=await browser.newContext({viewport:{width,height},locale:'nl'});
   const page=await context.newPage(),frames=[],errors=[],privateRequests=[];
   opened.push({context,page,host,orientation,frames,errors,privateRequests});
   page.on('pageerror',error=>errors.push(error.message));
   page.on('request',request=>{if(request.url().includes('/session/media/image/'))privateRequests.push(request.url());});
   page.on('websocket',socket=>socket.on('framereceived',frame=>{
    const value=JSON.parse(frame.payload.toString());
    frames.push(value);
   }));
   await page.route('https://www.gstatic.com/**',route=>route.fulfill({contentType:'application/javascript',body:sdk}));
   await page.goto(host==='local'?'https://localhost:18233/djconnect/vibecast?session_id='+
    encodeURIComponent(ready.session_id)+'&broadcast_token='+encodeURIComponent(ready.broadcast_token):'https://localhost:18234/');
   if(host==='cast')await page.evaluate(h=>window.__receive({data:h,senderId:'own-software-test'}),handoff);
   await page.waitForFunction(title=>document.querySelector('#title').textContent===title,ready.snapshot.playback.title);
   await page.waitForFunction(()=>!document.querySelector('#moment-card').hidden);
   await page.waitForFunction(()=>{const art=document.querySelector('#artwork');return !art.hidden&&art.complete&&art.naturalWidth>0;});
   const content=await page.locator('#moment-detail').textContent();
   const source=await page.locator('#moment-source').getAttribute('href');
   const original=ready.snapshot.dj_moments.find(moment=>moment.content===content);
   assert.ok(original,'Unchanged actual published content');
   assert.equal(source,original.source_attribution.url);
   const box=await page.locator('#moment-card').boundingBox();
   assert.ok(box.x>=0&&box.y>=0&&box.x+box.width<=width+1&&box.y+box.height<=height+1);
   const font=await page.locator('#moment-detail').evaluate(element=>parseFloat(getComputedStyle(element).fontSize));
   assert.ok(font>=20);
   await page.screenshot({path:lab+'/browser/'+host+'-'+orientation+'.png'});
   await context.setOffline(true);
   await page.waitForTimeout(1100);
   await context.setOffline(false);
   await page.waitForTimeout(2200);
   assert.equal(await page.locator('#title').textContent(),ready.snapshot.playback.title);
   assert.deepEqual(privateRequests,[]);
  })));
 fs.writeFileSync(lab+'/browser-continue','Browser four-path initial/readability/reconnect checks complete\n');
 await Promise.all(opened.map(async({page})=>{
  await page.waitForFunction(()=>document.querySelector('#moment-card').hidden,null,{timeout:25000});
  await page.waitForFunction(()=>document.querySelector('#title').textContent==='Wachten op een sessie',null,{timeout:25000});
 }));
 const receipts=opened.map(({host,orientation,frames,errors,privateRequests})=>{
  assert.deepEqual(errors,[]);
  assert.deepEqual(privateRequests,[]);
  assert.ok(frames.some(frame=>frame.type==='snapshot'));
  assert.ok(frames.some(frame=>frame.type==='event'));
  for(const frame of frames){
   assert.ok(!JSON.stringify(frame).includes('session_media'));
   assert.ok(!JSON.stringify(frame).includes('/session/media/image/'));
  }
  return {host,orientation,actual_HA_Broadcast:true,frames:frames.length,
   currentTrack:true,unchangedMoment:true,sourceLinks:true,existingCoverPixels:true,readability:true,reconnect:true,
   terminalClear:true,privateSessionMediaAbsent:true,CAF:host==='cast'?'MODELED_ONLY':'NOT_APPLICABLE'};
 });
 fs.writeFileSync(lab+'/browser/receipt.json',JSON.stringify({qualification:'CORE_BROADCAST_BROWSER_COMPATIBILITY',
  receipts,native:'NOT_RUN',installed:'NOT_RUN',hardware:'NOT_RUN'},null,2)+'\n');
 console.log(JSON.stringify({result:'PASS',paths:receipts.length}));
} finally {
 for(const {context} of opened)await context.close();
 await browser.close();
}
