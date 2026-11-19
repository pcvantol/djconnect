// Optional synthetic experiment only; never contacts HA or production.
const {chromium, webkit}=await import(process.env.DJC_PLAYWRIGHT_MODULE || '@playwright/test');
import {createServer} from 'node:http';
import {writeFile} from 'node:fs/promises';
import assert from 'node:assert/strict';
const servers=[], results=[];
let ha, outside, outsideRequests=0;
async function serve(handler) {
  const server=createServer(handler);
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  servers.push(server); return 'http://127.0.0.1:'+server.address().port;
}
try {
  outside=await serve((req,res)=>{outsideRequests++;res.end('synthetic outside');});
  ha=await serve((req,res)=>{
    if(req.url==='/redirect-cross') return res.writeHead(302,{location:outside+'/blocked'}).end();
    if(req.url==='/redirect-same') return res.writeHead(302,{location:ha+'/unexpected'}).end();
    let body=`<script>parent.postMessage({ready:true,path:location.pathname},'*')</script>`;
    if(req.url==='/meta-cross') body=`<meta http-equiv="refresh" content="0;url=${outside}/blocked">`;
    if(req.url==='/script-cross') body=`<script>location.replace('${outside}/blocked')</script>`;
    if(req.url==='/top-cross') body=`<script>try{top.location='${outside}/blocked'}catch(e){parent.postMessage({topDenied:true},'*')}</script>`;
    res.writeHead(200,{'content-type':'text/html'}).end(body);
  });
  const start=await serve((req,res)=>{
    res.writeHead(200,{'content-type':'text/html',
      'content-security-policy':`default-src 'none'; script-src 'nonce-probe'; frame-src ${ha}${req.url}; base-uri 'none'; form-action 'none'`});
    res.end(`<script nonce="probe">window.events=[];addEventListener('message',e=>{if(e.origin===${JSON.stringify(ha)})events.push(e.data)});addEventListener('securitypolicyviolation',e=>events.push({blocked:true,directive:e.effectiveDirective}));function begin(path){let f=document.createElement('iframe');f.sandbox='allow-scripts allow-same-origin';f.src=${JSON.stringify(ha)}+path;document.body.append(f)}</script><body></body>`);
  });
  for(const [engine,type] of Object.entries({chromium,webkit})){
    const browser=await type.launch();
    try {
      for(const path of ['/direct','/redirect-cross','/redirect-same','/meta-cross','/script-cross','/top-cross']){
        outsideRequests=0;
        const context=await browser.newContext();
        try {
          const page=await context.newPage(); await page.goto(start+path);
          await page.evaluate(path=>begin(path),path);
          await page.waitForFunction(()=>events.length>0,{},{timeout:5000});
          const events=await page.evaluate(()=>window.events);
          assert.equal(outsideRequests,0,'CSP/sandbox must block foreign requests');
          if(path==='/direct') assert(events.some(e=>e.ready&&e.path==='/direct'));
          else if(path==='/redirect-same') assert(events.some(e=>e.ready&&e.path==='/unexpected'));
          else if(path==='/top-cross') {assert(events.some(e=>e.topDenied));assert.equal(page.url(),start+path);}
          else assert(events.some(e=>e.blocked&&e.directive==='frame-src'));
          results.push({engine,case:path,events,foreign_requests:outsideRequests,pass:true});
        } finally {await context.close();}
      }
    } finally {await browser.close();}
  }
  const receipt={outcome:'PASS_SYNTHETIC_LOOPBACK_FRAME_MECHANICS_ONLY',production_requests:false,real_HA_TLS_DNS:false,
    framing_product_selected:false,proves_no_redirects:false,results};
  if(process.argv[2]) await writeFile(process.argv[2],JSON.stringify(receipt,null,2)+'\n');
  process.stdout.write(JSON.stringify(receipt,null,2)+'\n');
} finally {await Promise.all(servers.map(s=>new Promise(resolve=>s.close(resolve))));}
