// Actual isolated HA/Broadcast to both unchanged shared renderer builds.
// CAF host adapter is modeled; private owner speech is deliberately absent.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import https from 'node:https';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const {chromium}=require(process.env.DJC_PLAYWRIGHT);
const lab=process.env.DJC_LAB_ROOT;
const ready=JSON.parse(fs.readFileSync(lab+'/browser-ready.json'));
const sdk=`let ready=false,listener;const caf={addEventListener:(type,cb)=>{if(type==='ready')listener=cb},isSystemReady:()=>ready,addCustomMessageListener:(ns,cb)=>{window.__receive=cb},sendCustomMessage:()=>{},start:()=>{ready=true;listener()}};window.cast={framework:{CastReceiverContext:{getInstance:()=>caf},system:{EventType:{READY:'ready',SENDER_DISCONNECTED:'disconnected'},MessageType:{JSON:'JSON'}}}};`;
const handoff={kind:'vibecast_handoff',version:1,ha_url:'https://localhost:18235',
 session_id:ready.session_id,broadcast_token:ready.broadcast_token};
const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
 headless:true,args:['--ignore-certificate-errors-spki-list='+process.env.DJC_LAB_SPKI]});
const opened=[];
fs.mkdirSync(lab+'/browser',{recursive:true});
try {
 await Promise.all(['local','cast'].flatMap(host=>[
  ['portrait',1200,1920],['landscape',1920,1200]].map(async([orientation,width,height])=>{
   const context=await browser.newContext({viewport:{width,height},locale:'en'});
   const page=await context.newPage(),frames=[],errors=[],privateRequests=[];
   opened.push({context,page,host,orientation,frames,errors,privateRequests});
   page.on('pageerror',error=>errors.push(error.message));
   page.on('request',request=>{if(request.url().includes('/speech/'))privateRequests.push(request.url());});
   page.on('websocket',socket=>socket.on('framereceived',frame=>frames.push(JSON.parse(frame.payload.toString()))));
   await page.route('https://www.gstatic.com/**',route=>route.fulfill({contentType:'application/javascript',body:sdk}));
   await page.goto(host==='local'?'https://localhost:18235/djconnect/vibecast?session_id='+
    encodeURIComponent(ready.session_id)+'&broadcast_token='+encodeURIComponent(ready.broadcast_token):'https://localhost:18236/');
   if(host==='cast')await page.evaluate(h=>window.__receive({data:h,senderId:'own-software-test'}),handoff);
   await page.waitForFunction(content=>!document.querySelector('#moment-card').hidden&&
    document.querySelector('#moment-detail').textContent===content,ready.moment.content);
   assert.equal(await page.locator('#title').textContent(),ready.playback.title);
   assert.equal(await page.locator('#moment-source').getAttribute('href'),ready.moment.source_attribution.url);
   assert.equal(await page.locator('#spotify-source').isVisible(),true);
   const bounds=await page.locator('#moment-card').boundingBox();
   assert.ok(bounds.x>=0&&bounds.y>=0&&bounds.x+bounds.width<=width+1&&bounds.y+bounds.height<=height+1);
   const detail=await page.locator('#moment-detail').evaluate(e=>({font:parseFloat(getComputedStyle(e).fontSize),
    width:e.clientWidth,scrollWidth:e.scrollWidth,height:e.clientHeight,scrollHeight:e.scrollHeight}));
   assert.ok(detail.font>=20&&detail.scrollWidth<=detail.width+1&&detail.scrollHeight<=detail.height+1,JSON.stringify(detail));
   await page.screenshot({path:lab+'/browser/'+host+'-'+orientation+'.png'});
   await context.setOffline(true); await page.waitForTimeout(800); await context.setOffline(false);
   await page.waitForTimeout(1400);
   assert.equal(await page.locator('#moment-detail').textContent(),ready.moment.content);
   await page.waitForFunction(()=>document.querySelector('#moment-card').hidden,null,{timeout:40000});
   await page.reload();
   if(host==='cast')await page.evaluate(h=>window.__receive({data:h,senderId:'own-software-test'}),handoff);
   await page.waitForTimeout(900);
   assert.equal(await page.locator('#moment-card').isVisible(),false);
   assert.equal(await page.locator('#title').textContent(),ready.playback.title);
  })));
 const ended=await new Promise((resolve,reject)=>{
  const req=https.request('https://localhost:18235/__speech_lab/end',{
   method:'POST',ca:fs.readFileSync(lab+'/ca.pem')},res=>{
   res.resume();res.on('end',()=>res.statusCode===200?resolve(true):reject(new Error('end '+res.statusCode)));
  });req.on('error',reject);req.end();
 });
 assert.ok(ended);
 await Promise.all(opened.map(async({page,frames,errors,privateRequests})=>{
  await page.waitForTimeout(1200);
  assert.equal(await page.locator('#moment-card').isVisible(),false);
  assert.ok(frames.some(f=>f.type==='event'&&f.data?.event_type==='runtime_ended'));
  for(const frame of frames)assert.ok(!JSON.stringify(frame).includes('session_speech'));
  assert.deepEqual(privateRequests,[]);assert.deepEqual(errors,[]);
 }));
 const receipts=opened.map(({host,orientation,frames})=>({host,orientation,actual_HA_Broadcast:true,
  frames:frames.length,currentTrack:true,exactText:true,sourceLink:true,spotifyMark:true,readability:true,
  reconnect:true,originalExpiry:true,noResurrection:true,sessionEnd:true,privateSpeechAbsent:true,
  CAF:host==='cast'?'MODELED_ONLY':'NOT_APPLICABLE'}));
 fs.writeFileSync(lab+'/browser-done.json',JSON.stringify({result:'PASS',receipts,
  qualification:'CORE_BROADCAST_BROWSER_COMPATIBILITY',native:'NOT_RUN',audible:'NOT_RUN',installed:'NOT_RUN',hardware:'NOT_RUN'},null,2)+'\n');
 console.log(JSON.stringify({result:'PASS',paths:receipts.length}));
}catch(error){
 const diagnostics=await Promise.all(opened.map(async({page,host,orientation,frames,errors})=>({host,orientation,
  frameTypes:frames.map(f=>[f.type,f.data?.event_type]),errors,
  state:await page.locator('#state').textContent().catch(()=>null),
  title:await page.locator('#title').textContent().catch(()=>null)})));
 fs.writeFileSync(lab+'/browser/diagnostics.json',JSON.stringify(diagnostics,null,2)+'\n');
 fs.writeFileSync(lab+'/browser-done.json',JSON.stringify({result:'FAIL',error:String(error)})+'\n');
 throw error;
}finally{
 for(const {context} of opened)await context.close();
 await browser.close();
}
