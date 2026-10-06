// Real Chromium acceptance of renderer-safe events captured from the Core Runtime.
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {chromium} from 'playwright';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '../..');
const input = process.argv[2] || path.join(root, 'artifacts/verification/vibecast-multimoment/simulator-broadcast.json');
const output = process.argv[3] || path.join(root, 'artifacts/verification/vibecast-multimoment/browser');
execFileSync('python3',[path.join(root,'scripts/verification/capture_vibecast_multimoment.py'),input],{cwd:root});
const capture = JSON.parse(fs.readFileSync(input, 'utf8'));
assert.equal(capture.moment_receipts.length, 2);
assert.equal(new Set(capture.moment_receipts.map(m => m.type)).size, 2);
assert.equal(Date.parse(capture.moment_receipts[1].created_at)-Date.parse(capture.moment_receipts[0].created_at),30000);
fs.mkdirSync(output, {recursive:true});
const pageHtml = fs.readFileSync(path.join(root, 'custom_components/djconnect/vibecast.html'));
const cover = `<svg xmlns="http://www.w3.org/2000/svg" width="700" height="700" viewBox="0 0 700 700"><defs><linearGradient id="g" x2="1" y2="1"><stop stop-color="#44356f"/><stop offset=".6" stop-color="#9769a6"/><stop offset="1" stop-color="#edb684"/></linearGradient></defs><rect width="700" height="700" fill="url(#g)"/><circle cx="360" cy="340" r="210" fill="none" stroke="#fff8" stroke-width="3"/><circle cx="360" cy="340" r="110" fill="#17162288"/><circle cx="360" cy="340" r="12" fill="#f8f6ff"/></svg>`;
const server = http.createServer((req,res) => {
  res.setHeader('Cache-Control','no-store');
  if (req.url.startsWith('/api/djconnect/v1/image_proxy/test-cover')) {
    res.setHeader('Content-Type','image/svg+xml'); res.end(cover);
  } else { res.setHeader('Content-Type','text/html; charset=utf-8'); res.end(pageHtml); }
});
await new Promise(resolve => server.listen(0,'127.0.0.1',resolve));
const port = server.address().port;
const browser = await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
const context = await browser.newContext({viewport:{width:1200,height:1920},deviceScaleFactor:1,recordVideo:{dir:output,size:{width:1200,height:1920}}});
const firstTime = Date.parse(capture.moment_receipts[0].created_at);
const secondTime = Date.parse(capture.moment_receipts[1].created_at);
assert.ok(secondTime < firstTime + capture.before.dj_moments.at(-1).presentation_intent.maximum_duration_seconds*1000);
const installClock = (startingAt) => {
  window.__now = startingAt;
  const RealDate = Date;
  window.Date = class extends RealDate {static now() {return window.__now;}};
  window.__advanceClock = ms => {window.__now += ms;};
};
await context.addInitScript(installClock,firstTime);
await context.addInitScript(() => {
  window.__sockets = [];
  window.WebSocket = class {
    constructor(url) { this.url=url; window.__sockets.push(this); queueMicrotask(() => this.onopen?.()); }
    close() { this.onclose?.(); }
  };
  window.__deliver = (frame, index=window.__sockets.length-1) => window.__sockets[index].onmessage({data:JSON.stringify(frame)});
});
const page = await context.newPage();
let animationStarts = 0;
try {
  const sessionId = capture.before.session.session_id;
  await page.goto(`http://127.0.0.1:${port}/?session_id=${encodeURIComponent(sessionId)}&broadcast_token=simulator-token`);
  await page.evaluate(snapshot => window.__deliver({type:'snapshot',session_id:snapshot.session.session_id,snapshot}),capture.before);
  await page.locator('#moment').waitFor({state:'visible'});
  assert.equal(await page.locator('html').getAttribute('lang'),'nl');
  assert.equal(await page.locator('#moment-type').textContent(),'Genre');
  assert.equal(await page.locator('#title').textContent(),'Current');
  const artwork = await page.locator('#artwork').getAttribute('src');
  await page.locator('#moment-card').evaluate(el => el.addEventListener('animationstart', () => window.__animationStarts = (window.__animationStarts || 0) + 1));
  await page.screenshot({path:path.join(output,'01-first.png')});

  for (const event of capture.events) {
    if (event.event_type === 'dj_moment_published') break;
    const position = event.payload?.playback?.position_ms;
    if (position === 15000 || position === 30000) await page.evaluate(ms => window.__advanceClock(ms),15000);
    await page.evaluate(value => window.__deliver({type:'event',data:value}),event);
  }
  assert.equal(await page.locator('#progress').evaluate(el => el.value),30000);
  assert.equal(await page.locator('#moment-type').textContent(),'Genre');
  assert.equal(await page.locator('#artwork').getAttribute('src'),artwork);
  assert.equal(await page.evaluate(() => window.__animationStarts || 0),0);
  await page.screenshot({path:path.join(output,'02-progress.png')});

  const published = capture.events.find(event => event.event_type === 'dj_moment_published');
  const presentation = capture.events.find(event => event.event_type === 'presentation_published');
  assert.ok(published);
  assert.ok(presentation?.delivery_sequence > published.delivery_sequence);
  assert.ok(published.delivery_sequence > capture.before.broadcast.snapshot_watermark);
  await page.evaluate(value => window.__deliver({type:'event',data:value}),presentation);
  await page.evaluate(value => window.__deliver({type:'event',data:value}),published);
  await page.waitForTimeout(90);
  const during = await page.locator('#moment-card').evaluate(el => ({animation:getComputedStyle(el).animationName,opacity:getComputedStyle(el).opacity}));
  assert.equal(during.animation,'card-in');
  assert.equal(await page.locator('#moment-history').evaluate(el => getComputedStyle(el).animationName),'card-old');
  await page.screenshot({path:path.join(output,'03-entering.png')});
  await page.waitForTimeout(800);
  assert.equal(await page.locator('#moment-type').textContent(),'Nummer');
  assert.match(await page.locator('#moment-history').textContent(),/Genre/);
  assert.equal(await page.locator('#title').textContent(),'Current');
  assert.equal(await page.locator('#artwork').getAttribute('src'),artwork);
  assert.ok((await page.locator('#moment-detail').textContent()).length > 300);
  assert.equal(await page.locator('.moment-card:not([hidden])').count(),2);
  await page.screenshot({path:path.join(output,'04-settled.png')});
  animationStarts = await page.evaluate(() => window.__animationStarts || 0);
  assert.equal(animationStarts,1);
  await page.evaluate(value => window.__deliver({type:'event',data:value}),published);
  assert.equal(await page.evaluate(() => window.__animationStarts || 0),1);
  const oldPlayback = capture.events.find(event => event.event_type === 'playback_changed');
  await page.evaluate(value => window.__deliver({type:'event',data:value}),oldPlayback);
  assert.equal(await page.locator('#progress').evaluate(el => el.value),30000);
  assert.equal(await page.locator('#moment-type').textContent(),'Nummer');
  await page.waitForTimeout(5700);
  const scrollTop = await page.locator('#moment-detail').evaluate(el => el.scrollTop);
  assert.ok(scrollTop > 0,`long card did not scroll: ${scrollTop}`);
  await page.screenshot({path:path.join(output,'05-scrolled.png')});

  const firstSocket = await page.evaluate(() => { const ws=window.__sockets[0]; ws.onclose(); return window.__sockets.length; });
  assert.equal(firstSocket,1);
  await page.waitForTimeout(1150);
  assert.equal(await page.evaluate(() => window.__sockets.length),2);
  await page.evaluate(snapshot => window.__deliver({type:'snapshot',session_id:snapshot.session.session_id,snapshot}),capture.before);
  assert.equal(await page.locator('#moment-type').textContent(),'Nummer');
  await page.evaluate(snapshot => window.__deliver({type:'snapshot',session_id:snapshot.session.session_id,snapshot}),capture.after);
  assert.equal(await page.evaluate(() => window.__animationStarts || 0),1);
  assert.equal(await page.locator('#moment-type').textContent(),'Nummer');
  const expired = structuredClone(capture.after);
  for (const item of expired.dj_moments) item.created_at = '2000-01-01T00:00:00Z';
  await page.evaluate(snapshot => window.__deliver({type:'snapshot',session_id:snapshot.session.session_id,snapshot}),expired);
  assert.equal(await page.locator('#moment-card').isVisible(),false);
  await page.screenshot({path:path.join(output,'06-expired.png')});
  const changed = structuredClone(oldPlayback);
  changed.delivery_sequence = capture.after.broadcast.snapshot_watermark + 1;
  changed.payload.playback = {...changed.payload.playback,item_id:'next-track',title:'Next track',position_ms:0};
  await page.evaluate(value => window.__deliver({type:'event',data:value}),changed);
  await page.evaluate(value => window.__deliver({type:'event',data:value}),published);
  assert.equal(await page.locator('#title').textContent(),'Next track');
  assert.equal(await page.locator('#moment-card').isVisible(),false);
  await page.evaluate(value => window.__deliver({type:'event',data:value}),{event_type:'runtime_ended',delivery_sequence:changed.delivery_sequence+1,payload:{}});
  assert.equal(await page.locator('#title').textContent(),'Wachten op een sessie');

  const landscape = await browser.newContext({viewport:{width:1920,height:1200},deviceScaleFactor:1});
  await landscape.addInitScript(installClock,secondTime);
  await landscape.addInitScript(() => {window.WebSocket=class {constructor(){window.__ws=this;queueMicrotask(()=>this.onopen?.())}close(){}};window.__deliver=f=>window.__ws.onmessage({data:JSON.stringify(f)});});
  const landPage = await landscape.newPage();
  await landPage.goto(`http://127.0.0.1:${port}/?session_id=${encodeURIComponent(sessionId)}&broadcast_token=simulator-token`);
  await landPage.evaluate(snapshot => window.__deliver({type:'snapshot',session_id:snapshot.session.session_id,snapshot}),capture.after);
  assert.equal(await landPage.locator('#moment-type').textContent(),'Nummer');
  const overflow = await landPage.evaluate(() => document.documentElement.scrollWidth > innerWidth || document.documentElement.scrollHeight > innerHeight);
  assert.equal(overflow,false);
  await landPage.screenshot({path:path.join(output,'07-landscape.png')});
  await landscape.close();

  const reduced = await browser.newContext({viewport:{width:1200,height:1920},reducedMotion:'reduce'});
  await reduced.addInitScript(installClock,secondTime);
  await reduced.addInitScript(() => {window.WebSocket=class {constructor(){window.__ws=this;queueMicrotask(()=>this.onopen?.())}close(){}};window.__deliver=f=>window.__ws.onmessage({data:JSON.stringify(f)});});
  const reducedPage = await reduced.newPage();
  await reducedPage.goto(`http://127.0.0.1:${port}/?session_id=${encodeURIComponent(sessionId)}&broadcast_token=simulator-token`);
  await reducedPage.evaluate(snapshot => window.__deliver({type:'snapshot',session_id:snapshot.session.session_id,snapshot}),capture.before);
  await reducedPage.evaluate(value => window.__deliver({type:'event',data:value}),published);
  assert.equal(await reducedPage.locator('#moment-card').evaluate(el => getComputedStyle(el).animationName),'none');
  assert.equal(await reducedPage.locator('#moment-history').evaluate(el => getComputedStyle(el).animationName),'none');
  await reduced.close();

  fs.writeFileSync(path.join(output,'acceptance.json'),JSON.stringify({
    viewport:'1200x1920',landscape:'1920x1200',source:capture.source,simulator:true,
    moment_receipts:capture.moment_receipts,types:capture.moment_receipts.map(m=>m.type),
    broadcast_events:capture.events.map(e=>e.event_type),
    checks:{first:true,progress_stable:true,enter_animation:true,previous_exit_animation:true,previous_card:true,long_copy_scroll:true,duplicate_ignored:true,out_of_order_ignored:true,reconnect_no_replay:true,expired_hidden:true,track_change_clears:true,landscape_no_overflow:true,reduced_motion:true},
    animationStarts,scrollTop
  },null,2)+'\n');
  console.log(`Visual acceptance PASS: ${output}`);
} finally {
  await page.close(); await context.close(); await browser.close();
  await new Promise(resolve => server.close(resolve));
}
