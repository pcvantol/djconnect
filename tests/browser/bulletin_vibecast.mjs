// Generated local HTML + original isolated-HA TLS wire. Browser WS/clock are declared fixtures.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const {chromium,webkit}=require(process.env.DJC_PLAYWRIGHT || 'playwright');
const html=fs.readFileSync(process.argv[2]);
const original=fs.readFileSync(process.argv[3]);
const sample=JSON.parse(original).extension.sample;
const out=path.resolve(process.argv[4]);fs.mkdirSync(out,{recursive:true});
const sha=data=>createHash('sha256').update(data).digest('hex');
const server=http.createServer((req,res)=>{res.setHeader('Content-Type','text/html');res.end(html);});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const origin='http://127.0.0.1:'+server.address().port;
const results=[];
try {
 for(const [engine,type] of [['chromium',chromium],['webkit',webkit]]){
  const opts={headless:true};
  if(engine==='chromium' && fs.existsSync('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'))opts.executablePath='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
  const browser=await type.launch(opts);
  try {for(const [locale,width,height] of [['en',1280,720],['nl',720,1280],['de',1280,720],['fr',720,1280],['es',1280,720]]){
   const context=await browser.newContext({viewport:{width,height},reducedMotion:'reduce'});
   await context.route('**/*',route=>new URL(route.request().url()).origin===origin ? route.continue() : route.abort());
   const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
   await page.clock.install({time:new Date(Date.parse(sample.moment.created_at)+100)});
   await page.addInitScript(()=>{
    window.__sockets=[];
    window.WebSocket=class{constructor(){window.__sockets.push(this);queueMicrotask(()=>this.onopen && this.onopen());}close(){this.closed=true;}};
   });
   await page.goto(origin+'/?session_id='+encodeURIComponent(sample.moment.session_id)+'&broadcast_token=synthetic-readonly');
   const send=async frame=>page.evaluate(frame=>window.__sockets[0].onmessage({data:JSON.stringify(frame)}),frame);
   const initial=structuredClone(sample.initial_shared_snapshot);initial.session.locale=locale;
   await send({type:'snapshot',snapshot:initial});
   assert.equal(await page.locator('#moment-detail').textContent(),'');
   await send(sample.shared_event);
   await page.waitForFunction(text=>document.querySelector('#moment-detail').textContent===text,sample.moment.content,{timeout:3000});
   assert.equal(await page.locator('#moment-research-sources a').count(),2);
   assert.deepEqual(await page.locator('#moment-research-sources a').evaluateAll(links=>links.map(l=>l.href)),sample.moment.sources.map(s=>s.url));
   assert.equal(await page.locator('html').getAttribute('lang'),locale);
   assert.equal(await page.locator('#end-session').isVisible(),false);
   const reconnect=structuredClone(sample.shared_snapshot);reconnect.session.locale=locale;
   await send({type:'snapshot',snapshot:reconnect});
   assert.equal(await page.locator('#moment-detail').textContent(),sample.moment.content);
   await page.screenshot({path:path.join(out,engine+'-'+locale+'-bulletin.png')});
   const box=await page.locator('#moment-card').boundingBox();
   assert(box && box.width>100 && box.x>=-1 && box.y>=-1 && box.x+box.width<=width+1 && box.y+box.height<=height+1);
   for(const link of await page.locator('#moment-research-sources a').all()){const r=await link.boundingBox();assert(r && r.y>=box.y && r.y+r.height<=box.y+box.height+1,'both source credits must remain inside the card');}
   const noticeReadable=await page.locator('#moment-detail').evaluate(element=>{
    element.scrollTop=element.scrollHeight;
    const range=document.createRange();range.selectNodeContents(element);
    range.setStart(element.firstChild,Math.max(0,element.firstChild.length-80));
    const tail=range.getBoundingClientRect(),area=element.getBoundingClientRect();
    return area.height>0 && tail.top>=area.top-1 && tail.bottom<=area.bottom+1;
   });
   assert(noticeReadable,'complete final source/adaptation notice must be reachable without truncation');
   await page.screenshot({path:path.join(out,engine+'-'+locale+'-notice.png')});
   await page.clock.fastForward(91000);
   assert.equal(await page.locator('#moment-detail').textContent(),'');
   await send({type:'snapshot',snapshot:reconnect});
   assert.equal(await page.locator('#moment-detail').textContent(),'','reconnect must not revive original expired text');
   assert.deepEqual(errors,[]);
   results.push({engine,locale,width,height,event:'PASS',reconnect:'PASS',expiry:'PASS',complete_notice_readable:'PASS',console_errors:0});
   await context.close();
  }} finally {await browser.close();}
 }
} finally {await new Promise(resolve=>server.close(resolve));}
const receipt={scope:'ACTUAL_CHROMIUM_WEBKIT_ORIGINAL_ISOLATED_HA_WIRE_BROWSER_WS_AND_CLOCK_FIXTURES_NO_INSTALLED_DEVICE_OR_AUDIO_CLAIM',
 html_sha256:sha(html),original_ha_receipt_sha256:sha(original),results,status:results.length===10?'PASS':'FAIL'};
fs.writeFileSync(path.join(out,'receipt.json'),JSON.stringify(receipt,null,2)+'\n');
console.log(JSON.stringify(receipt));
