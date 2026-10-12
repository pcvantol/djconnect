// Forecast additive compatibility through actual HA Broadcast; visible Forecast adoption stays open. CAF API is modeled.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import https from 'node:https';
import {createHash, randomBytes} from 'node:crypto';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const {chromium}=require(process.env.DJC_PLAYWRIGHT);
const lab=process.env.DJC_LAB_ROOT;
const ca=fs.readFileSync(lab+'/ca.pem');
const request=path=>new Promise((resolve,reject)=>{
 https.get('https://localhost:18233'+path,{ca},res=>{
  let data='';res.on('data',x=>data+=x);res.on('end',()=>{
   try{assert.equal(res.statusCode,200,data);resolve(JSON.parse(data));}catch(e){reject(e);}
  });
 }).on('error',reject);
});
const sdk=`let ready=false,listener;const caf={addEventListener:(type,cb)=>{if(type==='ready')listener=cb},isSystemReady:()=>ready,addCustomMessageListener:(ns,cb)=>{window.__receive=cb},sendCustomMessage:(ns,id,data)=>{(window.__statuses||(window.__statuses=[])).push({id,data})},start:()=>{ready=true;listener()}};window.cast={framework:{CastReceiverContext:{getInstance:()=>caf},system:{EventType:{READY:'ready',SENDER_DISCONNECTED:'disconnected'},MessageType:{JSON:'JSON'}}}};`;
const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
 headless:true,args:['--ignore-certificate-errors-spki-list='+process.env.DJC_LAB_SPKI]});
fs.mkdirSync(lab+'/browser',{recursive:true});
const receipts=[];
try {
 for(const host of ['local','cast']) for(const [orientation,width,height] of [
  ['portrait',1200,1920],['landscape',1920,1200]]) {
  const context=await browser.newContext({viewport:{width,height},locale:'nl'});
  const page=await context.newPage(),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.route('https://www.gstatic.com/**',r=>r.fulfill({contentType:'application/javascript',body:sdk}));
  const handoff=await request('/__album_lab/setup');
  if(host==='cast'){handoff.status_version=1;handoff.handoff_id=randomBytes(16).toString('hex');}
  const url=host==='cast'?'https://localhost:18234/':
   'https://localhost:18233/djconnect/vibecast?session_id='+encodeURIComponent(handoff.session_id)+
   '&broadcast_token='+encodeURIComponent(handoff.broadcast_token);
  await page.goto(url);
  if(host==='cast')await page.evaluate(h=>window.__receive({data:h,senderId:'own-software-sender'}),handoff);
  const series=[];
  for(const number of [1,2]){
   const response=await request('/__album_lab/publish?number='+number);
   const forecast=response.snapshot.session_forecast;
   assert.equal(forecast.state,'ready');
   assert.equal(forecast.sections[0].claim_type,'current');
   assert.equal(forecast.imagery.length,1);
   assert.equal(forecast.imagery[0].role,'current');
   assert.ok(!JSON.stringify(forecast).includes('planned_intents'));
   const decoded=await page.evaluate(async url=>{
    const img=new Image();img.src=url;
    await img.decode();const result={width:img.naturalWidth,height:img.naturalHeight};
    img.removeAttribute('src');return result;
   },forecast.imagery[0].url.startsWith('/')?'https://localhost:18233'+forecast.imagery[0].url:forecast.imagery[0].url);
   assert.deepEqual(decoded,{width:1,height:1});
   const m=response.moment;
   assert.equal(m.type,number===1?'album':'track');
   await page.waitForFunction(t=>{
    const e=document.querySelector('#moment-card');
    return !e.hidden&&parseFloat(getComputedStyle(e).opacity)>=.99&&
     document.querySelector('#moment-detail').textContent===t;
   },m.content);
   assert.equal(await page.locator('#title').textContent(),'Observed track '+number);
   assert.equal(await page.locator('#moment-source').getAttribute('href'),m.source_attribution.url);
   assert.equal(await page.locator('#spotify-source').isVisible(),true);
   const bounds=await page.locator('#moment-card').boundingBox();
   assert.ok(bounds.x>=0&&bounds.y>=0&&bounds.x+bounds.width<=width+1&&bounds.y+bounds.height<=height+1);
   const detail=await page.locator('#moment-detail').evaluate(e=>({
    font:parseFloat(getComputedStyle(e).fontSize),width:e.clientWidth,scrollWidth:e.scrollWidth,
    height:e.clientHeight,scrollHeight:e.scrollHeight}));
   assert.ok(detail.font>=20&&detail.scrollWidth<=detail.width+1&&detail.scrollHeight<=detail.height+1,
             JSON.stringify(detail));
   await page.screenshot({path:lab+'/browser/'+host+'-'+orientation+'-'+number+'.png'});
   series.push(response);
  }
  const native=series[1].snapshot.native_delivery.admissions.find(x=>x.moment_id===series[1].moment.moment_id);
  await context.setOffline(true);
  await page.waitForTimeout(1100);
  await context.setOffline(false);
  await page.waitForTimeout(2300);
  assert.equal(await page.locator('#moment-detail').textContent(),series[1].moment.content);
  // Real wall-clock readable lifetime; no synthetic browser/server clock advance.
  const started=Date.now();
  await page.waitForFunction(()=>document.querySelector('#moment-card').hidden,null,{timeout:65000});
  const realExpiryWait=(Date.now()-started)/1000;
  assert.ok(realExpiryWait>=30);
  // Actual reconnect cannot renew original card/source clocks or resurrect old text.
  await page.reload();
  if(host==='cast')await page.evaluate(h=>window.__receive({data:h,senderId:'own-software-sender'}),handoff);
  await page.waitForTimeout(1200);
  assert.equal(await page.locator('#moment-card').isVisible(),false);
  assert.equal(await page.locator('#title').textContent(),'Observed track 2');
  assert.equal(await page.evaluate(()=>localStorage.length+sessionStorage.length),0);
  await request('/__album_lab/end');
  await page.waitForTimeout(900);
  assert.equal(await page.locator('#moment-card').isVisible(),false);
  assert.deepEqual(errors,[]);
  receipts.push({host,orientation,series,native,readability:true,sourceLinks:true,
   spotifyMark:true,currentTrack:true,transition:true,reconnect:true,
   realExpiryWaitSeconds:realExpiryWait,end:true,CAF:host==='cast'?'MODELED_ONLY':'NOT_APPLICABLE',
   tls:'HTTPS CA verified by driver; Chrome restricted to exact owned fixture leaf SPKI'});
  console.log('PASS '+host+'/'+orientation+' real expiry '+realExpiryWait.toFixed(2)+'s');
  await context.close();
 }
 const manifest=fs.readFileSync(lab+'/build/manifest.json');
 fs.writeFileSync(lab+'/browser/receipt.json',JSON.stringify({
  qualification:'FORECAST_ADDITIVE_SHARED_RENDERER_SOFTWARE_PASS',visible_forecast:'NOT_ADOPTED',artist_byte_decoder:'SOFTWARE_FIXTURE_ONLY',build:JSON.parse(manifest),
  manifestSHA256:createHash('sha256').update(manifest).digest('hex'),receipts,
  native:'NOT_RUN',installed:'NOT_RUN',hardware:'NOT_RUN'},null,2)+'\n');
}finally{await browser.close();}
