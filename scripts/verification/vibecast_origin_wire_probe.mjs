// Optional real-browser wire experiment; only temporary own loopback HTTP.
const {chromium, webkit}=await import(process.env.DJC_PLAYWRIGHT_MODULE || '@playwright/test');
import {createServer} from 'node:http';
import {writeFile} from 'node:fs/promises';
import assert from 'node:assert/strict';
const results=[];
for(const [engine,type] of Object.entries({chromium,webkit})) {
  const seen=[]; let origin;
  const server=createServer(async(req,res)=>{
    let bytes=0; for await(const chunk of req){bytes+=chunk.length;assert(bytes<=4096);}
    seen.push({path:req.url,method:req.method,origin_present:!!req.headers.origin,
      origin_matches:req.headers.origin===origin,authorization_present:!!req.headers.authorization});
    if(req.url==='/shell') res.writeHead(200,{'content-type':'text/html'}).end('<!doctype html><title>Synthetic B Origin wire</title>');
    else res.writeHead(200,{'content-type':'application/json','cache-control':'no-store'}).end('{"synthetic":true}');
  });
  server.on('upgrade',(req,socket)=>{
    seen.push({path:req.url,method:req.method,origin_present:!!req.headers.origin,
      origin_matches:req.headers.origin===origin,authorization_present:!!req.headers.authorization});
    // Header mechanics only; no session authentication or live B socket exists.
    socket.end('HTTP/1.1 403 Forbidden\r\nConnection: close\r\nContent-Length: 0\r\n\r\n');
  });
  let browser;
  try {
    await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
    origin='http://127.0.0.1:'+server.address().port;
    browser=await type.launch();
    const context=await browser.newContext();
    try {
      const page=await context.newPage(); await page.goto(origin+'/shell');
      await page.evaluate(async()=>{
        await fetch('/get-snapshot',{headers:{Authorization:'Bearer synthetic-not-a-credential'},credentials:'omit'});
        for(const path of ['/post-snapshot','/post-context']) await fetch(path,{method:'POST',
          headers:{'content-type':'application/json',Authorization:'Bearer synthetic-not-a-credential'},
          credentials:'omit',body:JSON.stringify({contract_version:1,synthetic:true})});
        await new Promise((resolve,reject)=>{
          const timer=setTimeout(()=>reject(Error('Synthetic upgrade did not finish')),3000);
          const ws=new WebSocket(location.origin.replace('http:','ws:')+'/live');
          ws.onerror=()=>{clearTimeout(timer);resolve();};
        });
      });
      const paths=['/shell','/get-snapshot','/post-snapshot','/post-context','/live'];
      for(const path of paths){
        const request=seen.find(x=>x.path===path); assert(request,'Missing measured request '+path);
        const expectedOrigin=path.startsWith('/post-')||path==='/live';
        assert.equal(request.origin_present,expectedOrigin);
        if(expectedOrigin) assert.equal(request.origin_matches,true);
        results.push({engine,...request,pass:true});
      }
    } finally {await context.close();}
  } finally {
    if(browser) await browser.close();
    server.closeAllConnections();
    await new Promise(resolve=>server.close(resolve));
  }
}
const receipt={outcome:'PASS_SYNTHETIC_BROWSER_ORIGIN_HEADER_MECHANICS_ONLY',
  production_requests:false,real_HA_TLS_or_auth:false,websocket_acceptance:false,results};
if(process.argv[2]) await writeFile(process.argv[2],JSON.stringify(receipt,null,2)+'\n');
process.stdout.write(JSON.stringify(receipt,null,2)+'\n');
