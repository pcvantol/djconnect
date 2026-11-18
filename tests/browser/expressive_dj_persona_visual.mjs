// Existing VibeCast consuming exact-base and candidate real Runtime snapshots.
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {chromium} from 'playwright';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const output=path.join(root,'artifacts/verification/expressive-dj-persona');
fs.mkdirSync(output,{recursive:true});
const input=path.join(output,'runtime-before-after.json');
execFileSync(path.join(root,'.venv/bin/python'),[path.join(root,'scripts/verification/capture_expressive_dj_persona.py'),input]);
const evidence=JSON.parse(fs.readFileSync(input));
const html=fs.readFileSync(path.join(root,'custom_components/djconnect/vibecast.html'));
const server=http.createServer((req,res)=>{
  res.setHeader('Cache-Control','no-store');
  if(req.url.startsWith('/api/')) {res.setHeader('Content-Type','image/svg+xml');res.end('<svg xmlns="http://www.w3.org/2000/svg" width="600" height="600"><rect width="600" height="600" fill="#63829d"/></svg>');}
  else {res.setHeader('Content-Type','text/html');res.end(html);}
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
const receipts=[];
try {
  for(const [profile,width,height] of [['portrait',1200,1920],['landscape',1920,1200]]) {
    for(const locale of ['en','nl','de','fr','es']) {
      for(const persona of ['home_dj','radio_dj','club_dj','festival_dj']) {
      for(const phase of ['before','after']) {
        const context=await browser.newContext({viewport:{width,height},deviceScaleFactor:1,locale});
        await context.addInitScript(()=>{
          const RealDate=Date;window.__now=RealDate.now();window.Date=class extends RealDate{static now(){return window.__now;}};
          window.WebSocket=class{constructor(){window.__ws=this;queueMicrotask(()=>this.onopen?.());}close(){}};
          window.__deliver=frame=>window.__ws.onmessage({data:JSON.stringify(frame)});
        });
        const page=await context.newPage(), errors=[];
        page.on('pageerror',e=>errors.push(String(e)));
        const response=await page.goto(`http://127.0.0.1:${server.address().port}/?session_id=software&broadcast_token=software-only`);
        assert.equal(response.headers()['cache-control'],'no-store');
        const scenario=evidence[phase][locale][persona];
        await page.evaluate(id=>window.dispatchEvent(new CustomEvent('djconnect-handoff',{detail:{session_id:id,broadcast_token:'software-only'}})),scenario.snapshots[0].session.session_id);
        for(let index=0;index<4;index++) {
          const snapshot=scenario.snapshots[index], moment=snapshot.dj_moments.at(-1);
          assert.equal(moment.type,'track');
          await page.evaluate(snapshot=>{window.__now=Date.parse(snapshot.dj_moments.at(-1).created_at)+100;window.__deliver({type:'snapshot',snapshot});},snapshot);
          await page.waitForTimeout(1000);
          assert.equal(await page.locator('#moment').textContent(),moment.summary);
          assert.equal(await page.locator('#moment-detail').textContent(),moment.content);
          assert.equal(await page.locator('#moment-source').getAttribute('href'),moment.source_attribution.url);
          const previous=page.locator('#moment-source-previous');
          if(index%2===1) {
            assert.ok(moment.content.includes(snapshot.playback.title) && moment.content.includes(scenario.snapshots[index-1].playback.title) && moment.content.includes('Nora Vale'));
            if(phase==='after') assert.ok(snapshot.presentations.every(p=>!p.speech));
            assert.equal(await previous.getAttribute('href'),moment.source_attribution.url_previous);
            assert.ok(await previous.isVisible());
            assert.ok((await previous.textContent()).includes('MusicBrainz'));
          } else {assert.equal(await previous.isVisible(),false);}
          assert.equal(await page.locator('#title').textContent(),snapshot.playback.title);
          assert.equal(await page.locator('#artist').textContent(),snapshot.playback.artist);
          assert.equal(await page.locator('#artwork').getAttribute('src'),snapshot.playback.artwork_url);
          const box=await page.locator('#moment-card').boundingBox();
          assert.ok(box.x>=0&&box.y>=0&&box.x+box.width<=width+1&&box.y+box.height<=height+1);
          const filename=`${profile}-${locale}-${persona}-${phase}-${index+1}.png`;
          await page.screenshot({path:path.join(output,filename)});
          receipts.push({filename,content:moment.content,attribution:moment.source_attribution,current_title:snapshot.playback.title});
          // Reconnect snapshot does not change the visible Moment or source links.
          await page.evaluate(snapshot=>window.__deliver({type:'snapshot',snapshot}),snapshot);
          assert.equal(await page.locator('#moment-detail').textContent(),moment.content);
        }
        // Playback ends: no source-card or old Now Playing remains visible.
        const terminal=structuredClone(scenario.snapshots.at(-1));
        terminal.session.runtime_state='ended';terminal.playback.state='idle';terminal.dj_moments=[];
        await page.evaluate(snapshot=>window.__deliver({type:'snapshot',snapshot}),terminal);
        await page.waitForTimeout(100);
        assert.equal(await page.locator('#moment-card').isVisible(),false);
        assert.deepEqual(errors,[]);await context.close();
      }
    }
  }
  }
  fs.writeFileSync(path.join(output,'browser-acceptance.json'),JSON.stringify({simulator:true,base:evidence.base,candidate_files:evidence.candidate_files,receipts,checks:{four_personas:true,complete_four_moment_sequences:true,five_locales:true,two_sources:true,current_playback:true,reconnect:true,end:true,portrait_landscape:true,no_store:true}},null,2));
  console.log(`Expressive persona browser acceptance PASS: ${output}`);
} finally {await browser.close();await new Promise(resolve=>server.close(resolve));}
