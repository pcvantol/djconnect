// Actual generated HTML; synthetic readonly WS only. Missing API is a runtime fixture.
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const {chromium,webkit}=require(process.env.DJC_PLAYWRIGHT || 'playwright');
const input=path.resolve(process.argv[2]),output=path.resolve(process.argv[3]);
const html=fs.readFileSync(input),sha=b=>createHash('sha256').update(b).digest('hex');
fs.mkdirSync(output,{recursive:true});
const server=http.createServer((req,res)=>{res.setHeader('Content-Type','text/html');res.end(html);});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const origin='http://127.0.0.1:'+server.address().port;
const results=[];
try {
 for(const [engine,type] of [['chromium',chromium],['webkit',webkit]]) {
  const opts={headless:true};
  if(engine==='chromium' && fs.existsSync('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')) opts.executablePath='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
  let browser;
  try {browser=await type.launch(opts);} catch(error) {
   results.push({engine,status:'NOT_RUN',reason:error.message});continue;
  }
  try { for(const legacy of [false,true]) {
   const context=await browser.newContext({viewport:{width:1280,height:800},reducedMotion:'reduce'});
   await context.route('**/*',route=>new URL(route.request().url()).origin===origin ? route.continue() : route.abort());
   await context.addInitScript(legacy=>{
    if(legacy)Element.prototype.replaceChildren=undefined;
    window.__sockets=[];
    window.WebSocket=class {constructor(){window.__sockets.push(this);queueMicrotask(()=>this.onopen && this.onopen());}close(){this.closed=true;if(this.onclose)this.onclose();}};
   },legacy);
   const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
   const row={engine,replaceChildren:legacy?'absent':'native',errors,status:'FAIL'};
   try {
    await page.goto(origin+'/?session_id=fixture-session&broadcast_token=fixture-readonly-token');
    const deliver=async item=>page.evaluate(item=>{
     const citations=[{provider:'Wikipedia',title:'Fixture public reference',language:'nl',license:'CC-BY-SA-4.0',url:'https://nl.wikipedia.org/wiki/Music',revision_url:'https://nl.wikipedia.org/w/index.php?oldid=111'}];
     const moment={moment_id:'fixture-'+item,playback_item_id:item,type:'track',summary:'A source-bound fixture story.',sources:citations};
     window.__sockets[0].onmessage({data:JSON.stringify({type:'snapshot',snapshot:{session:{session_id:'fixture-session',locale:'nl'},playback:{item_id:item,title:'Fixture music',artist:'Fixture artist'},dj_moments:[moment]}})});
    },item);
    await deliver('first-item');
    await page.waitForFunction(()=>document.querySelector('#moment-research-sources').children.length===1,{},{timeout:2000});
    assert.equal(await page.locator('#moment-research-sources a').count(),1);
    await deliver('second-item');
    assert.equal(await page.locator('#moment-research-sources a').count(),1,'previous links must be removed');
    await page.screenshot({path:path.join(output,engine+'-'+(legacy?'legacy':'native')+'-live.png')});
    for(let i=0;i<2;i++)await page.evaluate(()=>window.dispatchEvent(new Event('djconnect-host-stop')));
    assert.equal(await page.locator('#moment-research-sources a').count(),0);
    assert.equal(await page.locator('#moment').textContent(),'');
    assert.equal(await page.locator('#moment-research-sources').evaluate(e=>e.hidden),true);
    assert.equal(await page.evaluate(()=>window.__sockets.every(s=>s.closed)),true);
    assert.deepEqual(errors,[]);
    row.status='PASS';
   } catch(error) {row.failure=error.message;}
   results.push(row);await context.close();
  }} finally {await browser.close();}
 }
} finally {await new Promise(resolve=>server.close(resolve));}
const receipt={scope:'REAL_CHROMIUM_WEBKIT_GENERATED_HTML_SYNTHETIC_WS_NO_NATIVE_OR_INSTALLED_CLAIM',html_sha256:sha(html),results,status:results.length===4 && results.every(r=>r.status==='PASS')?'PASS':'FAIL'};
fs.writeFileSync(path.join(output,'receipt.json'),JSON.stringify(receipt,null,2)+'\n');
console.log(JSON.stringify({status:receipt.status,results:results.map(({engine,replaceChildren,status})=>({engine,replaceChildren,status}))}));
if(receipt.status!=='PASS')process.exitCode=1;
