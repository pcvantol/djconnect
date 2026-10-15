// Software-only browser consumer of real Core Runtime snapshots.
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {chromium} from 'playwright';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const output=path.join(root,'artifacts/verification/contextual-fact-planning');
fs.mkdirSync(output,{recursive:true});
const input=path.join(output,'runtime-before-after.json');
execFileSync('python3',[path.join(root,'scripts/verification/capture_contextual_fact_planning.py'),input]);
const evidence=JSON.parse(fs.readFileSync(input));
const html=fs.readFileSync(path.join(root,'custom_components/djconnect/vibecast.html'));
const server=http.createServer((req,res)=>{res.setHeader('Cache-Control','no-store');res.setHeader('Content-Type','text/html');res.end(html);});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
const receipts=[];
try {
  assert.notEqual(evidence.before.manual.receipts[0].content,evidence.before.reversed.receipts[0].content);
  assert.equal(evidence.after.manual.receipts[0].content,evidence.after.reversed.receipts[0].content);
  assert.deepEqual(evidence.after.manual.receipts.map(x=>x.type),['track','album','artist']);
  assert.deepEqual(evidence.after.discover.receipts.map(x=>x.type),['artist','album','track']);
  assert.equal(evidence.before.short_fit.receipts.length,0);
  assert.equal(evidence.after.short_fit.receipts.length,1);
  assert.equal(evidence.after.calm.receipts[1].position_ms,50000);
  for(const [profile,width,height] of [['portrait',1200,1920],['landscape',1920,1200]]) {
    for(const name of ['manual','discover','calm','short_fit']) {
      const context=await browser.newContext({viewport:{width,height},deviceScaleFactor:1});
      await context.addInitScript(()=>{
        const RealDate=Date;window.__now=RealDate.now();window.Date=class extends RealDate{static now(){return window.__now;}};
        window.WebSocket=class{constructor(){window.__ws=this;queueMicrotask(()=>this.onopen?.());}close(){}};
        window.__deliver=frame=>window.__ws.onmessage({data:JSON.stringify(frame)});
      });
      const page=await context.newPage();const errors=[];
      page.on('pageerror',e=>errors.push(String(e)));
      const response=await page.goto(`http://127.0.0.1:${server.address().port}/?session_id=software&broadcast_token=software-only`);
      assert.equal(response.headers()['cache-control'],'no-store');
      const scenario=evidence.after[name];
      await page.evaluate(id=>window.dispatchEvent(new CustomEvent('djconnect-handoff',{detail:{session_id:id,broadcast_token:'software-only'}})),scenario.after.session.session_id);
      for(let index=0;index<scenario.snapshots.length;index++) {
        const snapshot=scenario.snapshots[index];const moment=snapshot.dj_moments.at(-1);
        await page.evaluate(snapshot=>{window.__now=Date.parse(snapshot.dj_moments.at(-1).created_at)+100;window.__deliver({type:'snapshot',snapshot});},snapshot);
        await page.waitForTimeout(1750);
        assert.equal(await page.locator('#moment').textContent(),moment.summary);
        assert.equal(await page.locator('#moment-source').textContent(),moment.source_attribution.provider);
        assert.equal(await page.locator('#moment-source').getAttribute('href'),moment.source_attribution.url);
        const box=await page.locator('#moment-card').boundingBox();
        assert.ok(box.x>=0&&box.y>=0&&box.x+box.width<=width+1&&box.y+box.height<=height+1);
        const filename=`${profile}-${name}-${index+1}-${moment.type}.png`;
        await page.screenshot({path:path.join(output,filename)});
        receipts.push({filename,scenario:name,type:moment.type,reason:scenario.receipts[index].reason,source:moment.source_attribution.provider});
      }
      assert.deepEqual(errors,[]);await context.close();
    }
  }
  fs.writeFileSync(path.join(output,'acceptance.json'),JSON.stringify({simulator:true,base:evidence.base,candidate_files:evidence.candidate_files,receipts,checks:{order_independent:true,context_changes_real_sequence:true,short_fit:true,bounded_calm_spacing:true,portrait_landscape:true,unchanged_attribution:true,no_store:true}},null,2));
  console.log(`Contextual fact planning browser acceptance PASS: ${output}`);
} finally {await browser.close();await new Promise(resolve=>server.close(resolve));}
