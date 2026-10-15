// Software browser acceptance; mocked source replies/time, never physical/live evidence.
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {chromium} from 'playwright';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const output=path.join(root,'artifacts/verification/vibecast-multimoment/owner-refinements-facts-browser');
fs.mkdirSync(output,{recursive:true});
const input=path.join(output,'runtime.json');
execFileSync('python3',[path.join(root,'scripts/verification/capture_vibecast_owner_refinements.py'),input]);
const evidence=JSON.parse(fs.readFileSync(input));
const html=fs.readFileSync(path.join(root,'custom_components/djconnect/vibecast.html'));
const cover='<svg xmlns="http://www.w3.org/2000/svg" width="600" height="600"><rect width="600" height="600" fill="#1a9785"/><circle cx="300" cy="300" r="180" fill="#e7b04e"/></svg>';
let endRequests=0;
const server=http.createServer((req,res)=>{
  res.setHeader('Cache-Control','no-store');
  if(req.url.startsWith('/api/djconnect/v1/image_proxy/')) {res.setHeader('Content-Type','image/svg+xml');res.end(cover);return;}
  if(req.url.endsWith('/control/end')) {
    let body='';req.on('data',d=>body+=d);req.on('end',()=>{
      const data=JSON.parse(body);assert.equal(data.end_grant,'software-end-grant');assert.equal(data.session_id,evidence.before.session.session_id);
      endRequests++;res.setHeader('Content-Type','application/json');res.statusCode=endRequests===1?503:200;
      res.end(JSON.stringify(endRequests===1?{success:false}:{success:true,state:'ended'}));
    });return;
  }
  res.setHeader('Content-Type','text/html');res.end(html);
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
const receipts=[];
try {
 for(const [name,width,height] of [['portrait',1200,1920],['landscape',1920,1200]]) {
  const context=await browser.newContext({viewport:{width,height},deviceScaleFactor:1,recordVideo:{dir:output,size:{width,height}}});
  await context.addInitScript(()=>{
    const RealDate=Date;window.__now=RealDate.now();window.Date=class extends RealDate {static now(){return window.__now;}};
    window.WebSocket=class {constructor(){window.__ws=this;queueMicrotask(()=>this.onopen?.())}close(){}};
    window.__deliver=frame=>window.__ws.onmessage({data:JSON.stringify(frame)});
  });
  const page=await context.newPage();
  const errors=[];page.on('pageerror',error=>errors.push(String(error)));
  await page.goto(`http://127.0.0.1:${server.address().port}/?session_id=software&broadcast_token=software-only`);
  await page.evaluate(id=>window.dispatchEvent(new CustomEvent('djconnect-handoff',{detail:{session_id:id,broadcast_token:'software-only',end_grant:'software-end-grant'}})),evidence.before.session.session_id);
  const before=structuredClone(evidence.before);
  before.playback.artwork_url='/api/djconnect/v1/image_proxy/test-cover';
  before.playback.up_next={current_item_id:before.playback.item_id,title:'Next test recording',artist:'Next test artist',artwork_url:'/api/djconnect/v1/image_proxy/next-cover',expires_at:'2099-01-01T00:00:00Z'};
  await page.evaluate(snapshot=>{window.__now=Date.parse(snapshot.dj_moments[0].created_at)+100;window.__deliver({type:'snapshot',snapshot});},before);
  const moments=[before.dj_moments[0],...evidence.events.filter(e=>e.event_type==='dj_moment_published').map(e=>e.payload.dj_moment)];
  let eventIndex=0;
  for(let i=0;i<moments.length;i++) {
    const moment=moments[i];
    if(i) {
      const frame=evidence.events.find(e=>e.event_type==='dj_moment_published'&&e.payload.dj_moment.moment_id===moment.moment_id);
      const stop=evidence.events.indexOf(frame);
      while(eventIndex<=stop) {
        const next=structuredClone(evidence.events[eventIndex++]);
        if(next.payload.playback) {
          next.payload.playback.artwork_url=before.playback.artwork_url;
          next.payload.playback.up_next=before.playback.up_next;
        }
        await page.evaluate(frame=>{
          const timestamp=frame.payload.dj_moment?.created_at || frame.payload.playback?.updated_at;
          if(timestamp) window.__now=Date.parse(timestamp)+100;
          window.__deliver({type:'event',data:frame});
        },next);
      }
      await page.waitForTimeout(80);
      assert.equal(await page.locator('#moment-card').evaluate(el=>getComputedStyle(el).animationName),'card-out');
      await page.waitForTimeout(1620);
    }
    assert.equal(await page.locator('#moment').textContent(),moment.summary);
    assert.equal(await page.locator('#moment-source').textContent(),moment.source_attribution.provider);
    assert.equal(await page.locator('#spotify-source').isVisible(),true);
    assert.equal(await page.locator('#up-next').isVisible(),true);
    assert.equal(await page.locator('#end-session').isVisible(),true);
    const boxes=await page.evaluate(()=>Object.fromEntries(['artwork','title','artist','album','moment-card','up-next','progress'].map(id=>{const r=document.getElementById(id).getBoundingClientRect();return [id,{x:r.x,y:r.y,w:r.width,h:r.height}]})));
    const intersects=(a,b)=>a.x<b.x+b.w&&a.x+a.w>b.x&&a.y<b.y+b.h&&a.y+a.h>b.y;
    for(const id of ['artwork','title','artist','album','up-next','progress']) assert.equal(intersects(boxes['moment-card'],boxes[id]),false,`${name} card overlaps ${id}`);
    for(const b of Object.values(boxes)) assert.ok(b.x>=0&&b.y>=0&&b.x+b.w<=width+1&&b.y+b.h<=height+1,`${name} clipping`);
    const filename=`${name}-${i+1}-${moment.type}.png`;
    await page.screenshot({path:path.join(output,filename)});
    receipts.push({filename,viewport:{width,height},type:moment.type,summary:moment.summary,source:moment.source_attribution.provider,simulator:true});
  }
  if(name==='portrait') {
    const playback=structuredClone(evidence.after.playback);
    playback.artwork_url=before.playback.artwork_url;
    playback.up_next={...before.playback.up_next,expires_at:new Date(Date.parse(moments.at(-1).created_at)+2000).toISOString()};
    await page.evaluate(frame=>window.__deliver({type:'event',data:frame}),{event_type:'playback_changed',delivery_sequence:evidence.after.broadcast.snapshot_watermark+1,payload:{playback}});
    assert.equal(await page.locator('#up-next').isVisible(),true);
    await page.evaluate(()=>{window.__now+=2100;});
    await page.waitForTimeout(1100); // No Broadcast event: the ordinary clock tick must hide expired queue data.
    assert.equal(await page.locator('#up-next').isVisible(),false);
    await page.locator('#end-session').click();await page.waitForTimeout(100);
    assert.match(await page.locator('#state').textContent(),/niet gelukt/);
    assert.equal(await page.locator('#title').textContent(),'Test recording');
    await page.locator('#end-session').click();await page.waitForTimeout(100);
    assert.equal(await page.locator('#title').textContent(),'Wachten op een sessie');
    assert.equal(await page.locator('#up-next').isVisible(),false);
    await page.screenshot({path:path.join(output,'portrait-server-confirmed-idle.png')});
  }
  assert.deepEqual(errors,[]);
  await page.close();await context.close();
 }
 fs.writeFileSync(path.join(output,'acceptance.json'),JSON.stringify({simulator:true,source:evidence.source,receipts,checks:{four_independent_facts:true,portrait_landscape_no_overlap:true,source_attribution:true,up_next:true,end_error_no_false_idle:true,server_confirmed_end:true,quiet_queue_expiry:true,same_title_fade_out:true}},null,2));
 console.log(`Owner-refinements software browser acceptance PASS: ${output}`);
} finally {await browser.close();await new Promise(resolve=>server.close(resolve));}
