/* Real isolated HA B + shared renderer; no A/public-TLS/native/hardware claim. */
import http from "node:http";
import {spawn,execFile} from "node:child_process";
import {promisify} from "node:util";
import {writeFile,mkdir,readFile} from "node:fs/promises";
import {resolve} from "node:path";
import {pathToFileURL} from "node:url";
import {randomBytes,createHash} from "node:crypto";

const playwright=await import(process.env.DJC_PLAYWRIGHT_MODULE || "@playwright/test");
const output=resolve(process.argv[2] || "/tmp/djc-display-browser-results");
await mkdir(output,{recursive:true});
const selected="https://ha.display-lab.djconnect.dev", children=new Set(), sockets=new Set(), browsers=[];
const proxy=http.createServer((_req,res)=>{res.writeHead(403);res.end();});
proxy.on("connect",(req,socket,head)=>{
  if(req.url!=="ha.display-lab.djconnect.dev:443" || children.size>=32){socket.end("HTTP/1.1 403 Forbidden\r\n\r\n");return;}
  sockets.add(socket);
  const child=spawn("docker",["exec","-i","djc-display-b-browser-lab","python","/work/scripts/verification/display_loopback_bridge.py"],{stdio:["pipe","pipe","pipe"]});
  children.add(child);child.stderr.resume();
  socket.write("HTTP/1.1 200 Connection Established\r\n\r\n");
  if(head.length)child.stdin.write(head);
  socket.pipe(child.stdin);child.stdout.pipe(socket);
  child.stdin.on("error",()=>{});child.stdout.on("error",()=>{});
  const close=()=>{sockets.delete(socket);socket.destroy();child.stdin.end();children.delete(child);};
  child.on("error",close);child.on("exit",close);socket.on("error",close);socket.on("close",close);
});
await new Promise(done=>proxy.listen(0,"127.0.0.1",done));
const proxySettings={server:`http://127.0.0.1:${proxy.address().port}`};
let api;
let finishSession=null, ownerDiagnostic=null, ending=false;
let originalMomentDeadline=null;
const results=[], pages=[], violations=[], wire=[];
const intentionalOffline=new Set();
async function fixturePlayback(enabled){
  await promisify(execFile)("docker",["exec","djc-display-b-browser-lab","python","-c",
    "from pathlib import Path; p=Path('/lab/display-playback-ready'); "+(enabled?"p.touch()":"p.unlink(missing_ok=True)")],{timeout:10000});
}
try{
  await fixturePlayback(false);
  // Certificate acceptance is scoped to this synthetic loopback TLS fixture.
  // Every connection is an unchanged TLS stream to the actual own HA server;
  // no response, authority, transaction or projection is mocked by the bridge.
  api=await playwright.request.newContext({baseURL:selected,proxy:proxySettings,ignoreHTTPSErrors:true});
  const identity={device_id:"djconnect-ios-ABCDEF123456",client_type:"ios"};
  let response=await api.post("/api/djconnect/v1/pair",{data:{...identity,pair_code:"123456"}});
  const paired=await response.json();if(response.status()!==200)throw new Error("pairing_failed");
  const headers={Authorization:"Bearer "+paired.device_token};
  async function owner(path,body,expected=200){
    const response=await api.post("/api/djconnect/v1/"+path,{headers,data:{contract_version:1,identity,...body}});
    const value=await response.json();if(response.status()!==expected)throw new Error(`${path}:${response.status()}:${value.error || "failed"}`);
    return value;
  }
  const probeNonce=randomBytes(32).toString("base64url"), probeBegan=performance.now();
  response=await api.post("/api/djconnect/v1/display/claim",{headers:{Origin:selected},data:{contract_version:1,browser_nonce:probeNonce}});
  const probeClaim=await response.json();
  wire.push({scope:"direct_API_control",status:response.status(),elapsed_ms:performance.now()-probeBegan,keys:Object.keys(probeClaim)});
  await api.post("/api/djconnect/v1/display/cancel",{headers:{Origin:selected},data:{contract_version:1,
    issuer_epoch:probeClaim.issuer_epoch,claim_id:probeClaim.claim_id,claim_secret:probeClaim.claim_secret,
    browser_generation:probeClaim.browser_generation,browser_nonce:probeNonce}});
  let share=null;
  for(const [engine,index] of [["chromium",0],["webkit",1]]){
    const browser=await playwright[engine].launch({headless:true,proxy:proxySettings});browsers.push(browser);
    for(const [orientation,viewport] of [["portrait",{width:900,height:1440}]]){
      const context=await browser.newContext({viewport,ignoreHTTPSErrors:true,locale:index?"nl-NL":"en-US"});
      const page=await context.newPage();
      page.on("websocket",ws=>ws.on("framereceived",({payload})=>{
        try{const frame=JSON.parse(String(payload)), snapshot=frame.snapshot;
          if(snapshot?.dj_moments?.length && originalMomentDeadline===null)
            originalMomentDeadline=Math.min(...snapshot.dj_moments.map(m=>Date.parse(m.display_expires_at)));
          if(snapshot)wire.push({engine,scope:"actual_WS",type:frame.type,moments:snapshot.dj_moments?.length,
            watermark:snapshot.broadcast?.snapshot_watermark});}catch(_){}
      }));
      page.on("console",message=>{if(message.type()==="error"){
        // Session end deliberately aborts the dedicated transport immediately.
        // WebKit logs this exact expected close as a console network error.
        // Preserve the observation; never suppress pre-end or other errors.
        const error=message.text();
        if((ending || intentionalOffline.has(engine)) && error===`WebSocket connection to '${selected.replace("https:","wss:")}/api/djconnect/v1/display/live' failed: The network connection was lost.`)
          wire.push({engine,scope:ending?"expected_session_end_transport_abort":"expected_intentional_offline_transport_abort"});
        else violations.push({engine,orientation,error:error.slice(0,300)});
      }});
      page.on("pageerror",error=>violations.push({engine,orientation,error:error.message.slice(0,300)}));
      page.on("requestfailed",request=>violations.push({engine,orientation,error:request.failure().errorText,
        path:new URL(request.url()).pathname}));
      page.on("response",async response=>{
        if(response.url().includes("/api/djconnect/v1/display/")){
          let code="",keys=[],expires=null;try{const body=await response.json();code=body.error || "";keys=Object.keys(body);expires=body.expires_in;}catch(_){code="invalid_json_body";}
          wire.push({engine,orientation,path:new URL(response.url()).pathname,status:response.status(),error:code,keys,expires});
          if(response.status()>=400)violations.push({engine,orientation,status:response.status(),error:code});
        }
      });
      const navigation=await page.goto(selected+"/djconnect/vibecast/display",{waitUntil:"domcontentloaded",timeout:30000});
      if(navigation.status()!==200 || navigation.request().redirectedFrom())throw new Error("entry_not_direct200");
      if(!navigation.headers()["content-security-policy"] || navigation.headers()["cache-control"]!=="no-store")throw new Error("missing_security_headers");
      const served=await navigation.body(), artifact=await readFile(resolve(output,"../display-build/index.html"));
      const manifest=JSON.parse(await readFile(resolve(output,"../display-build/manifest.json"),"utf8"));
      const digest=createHash("sha256").update(served).digest("hex");
      if(!served.equals(artifact) || digest!==manifest.files["index.html"])throw new Error("served_static_artifact_mismatch");
      wire.push({engine,scope:"served_static_build_byte_identity",sha256:digest});
      await page.locator("#handoff strong").waitFor({state:"visible",timeout:30000});
      const code=await page.locator("#handoff strong").innerText();if(!/^[0-9]{6}$/.test(code))throw new Error("not_six_digits");
      if(!(await page.locator("#end-session").isHidden()))throw new Error("owner_end_control_visible");
      pages.push({page,context,engine,orientation,code});
      results.push({engine,orientation,entry:"direct200",approval:"ordinary_paired_owner_B_six_digits",snapshot:"actual_HA_live",owner_end:"hidden"});
    }
  }
  // Prepare the two unauthorised screens before starting playback. Otherwise
  // slow lab bridge/browser startup can exhaust a genuine short publication's
  // original display lifetime before the second viewer is admitted. Never
  // extend those source/publication clocks to make the test pass.
  response=await api.post("/api/djconnect/v1/session/start",{headers,data:{...identity,mood:"groove",locale:"en"}});
  const started=await response.json();if(response.status()!==201)throw new Error("session_start_failed");
  const sessionId=started.session.session_id;
  finishSession=()=>api.post("/api/djconnect/v1/session/end",{headers,data:{...identity,session_id:sessionId}});
  ownerDiagnostic=()=>api.get(`/api/djconnect/v1/session/broadcast/${sessionId}`,{headers});
  for(const item of pages){
    const resolved=await owner("display/owner/resolve",{code:item.code});
    share=await owner("display/owner/approve",{session_id:sessionId,code:item.code,issuer_epoch:resolved.issuer_epoch,
      claim_id:resolved.claim_id,browser_generation:resolved.browser_generation,
      share:share?{mode:"existing",share_id:share.share_id,share_generation:share.share_generation}:{mode:"create",consent:true,lifetime_seconds:300}});
    delete item.code;
  }
  for(const {page} of pages){
    await page.waitForFunction(()=>document.getElementById("handoff").hidden,null,{timeout:20000});
  }
  await fixturePlayback(true);
  for(const {page} of pages){
    await page.waitForFunction(()=>document.getElementById("title").textContent==="Fixture track",null,{timeout:20000});
  }
  // Wait for an ordinary Runtime observation/provider-qualified contribution;
  // no clock rewrite, injected Moment or planner/Flow shortcut is permitted.
  await pages[0].page.locator("#moment-card").waitFor({state:"visible",timeout:55000});
  const exact=await pages[0].page.locator("#moment-detail").innerText();
  if(!exact)throw new Error("missing_real_Moment_content");
  for(const item of pages){
    await item.page.locator("#moment-card").waitFor({state:"visible",timeout:10000});
    const content=await item.page.locator("#moment-detail").innerText();
    if(content!==exact)throw new Error("Moment_changed_between_displays");
    const source=await item.page.locator("#moment-source").getAttribute("href");
    if(!source || !/^https:\/\/(musicbrainz\.org|www\.wikidata\.org|open\.spotify\.com)\//.test(source))throw new Error("missing_source_link");
    const geometry=await item.page.locator("#moment-card").evaluate(element=>{
      const b=element.getBoundingClientRect();return {width:b.width,height:b.height,inViewport:b.x>=0&&b.y>=0&&b.right<=innerWidth&&b.bottom<=innerHeight};});
    if(!geometry.inViewport || geometry.width<200 || geometry.height<50)throw new Error("unreadable_geometry");
    await item.page.screenshot({path:resolve(output,`${item.engine}-${item.orientation}.png`)});
    Object.assign(results.find(r=>r.engine===item.engine&&r.orientation===item.orientation),{moment:"actual_Runtime_Moment_Flow_Broadcast",unchanged_content:true,source_link:source,geometry});
    await item.page.setViewportSize({width:1440,height:900});
    await item.page.waitForTimeout(100);
    const landscape=await item.page.locator("#moment-card").evaluate(element=>{
      const b=element.getBoundingClientRect();return {width:b.width,height:b.height,inViewport:b.x>=0&&b.y>=0&&b.right<=innerWidth&&b.bottom<=innerHeight};});
    if(!landscape.inViewport || (await item.page.locator("#moment-detail").innerText())!==exact)throw new Error("landscape_content_or_geometry");
    await item.page.screenshot({path:resolve(output,`${item.engine}-landscape.png`)});
    results.push({...results.find(r=>r.engine===item.engine&&r.orientation===item.orientation),orientation:"landscape",geometry:landscape});
  }
  // Actual browser network lifecycle, no injected snapshot or clock advance.
  for(const item of pages){
    intentionalOffline.add(item.engine);
    await item.context.setOffline(true);
    await item.page.waitForFunction(()=>document.getElementById("moment-card").hidden,null,{timeout:5000});
    await item.context.setOffline(false);
    await item.page.waitForFunction(()=>document.getElementById("handoff").hidden &&
      document.getElementById("title").textContent==="Fixture track",null,{timeout:20000});
    await item.page.waitForTimeout(500);
    intentionalOffline.delete(item.engine);
  }
  if(!Number.isFinite(originalMomentDeadline))throw new Error("missing_original_Moment_deadline");
  const wait=Math.max(0,originalMomentDeadline-Date.now()+1000);
  if(wait>90000)throw new Error("unbounded_Moment_deadline");
  await new Promise(done=>setTimeout(done,wait));
  for(const {page} of pages){
    await page.waitForFunction(()=>document.getElementById("moment-card").hidden,null,{timeout:5000});
    if((await page.locator("#moment-detail").innerText()).trim())throw new Error("expired_Moment_text_retained");
  }
  ending=true;
  const ended=await finishSession();
  if(ended.status()!==200)throw new Error("ordinary_session_end_failed:"+ended.status());
  for(const item of pages){
    await item.page.waitForFunction(()=>document.getElementById("moment-card").hidden,{timeout:10000});
    if((await item.page.locator("#moment-detail").innerText()).trim())throw new Error("stale_end_content");
  }
  if(violations.length)throw new Error("browser_errors:"+JSON.stringify(violations));
  await writeFile(resolve(output,"results.json"),JSON.stringify({qualification:"REAL_ISOLATED_HA_B_SHARED_RENDERER_LOCAL",results,
    session_end:"all_cards_and_text_cleared",private_storage:"not_used",TLS:"own_fixture_trust_only_not_public_route",A:"unavailable",
    reconnect:"actual_offline_clears_then_fresh_live_snapshot_both_engines",expiry:"original_published_deadline_no_clock_rewrite",
    static_artifact:"exact_bytes_and_manifest_digest_equal_real_browser_served_app_no_receiver_deployment",
    observations:wire,native_installed_physical:"NOT_QUALIFIED"},null,2)+"\n");
  console.log(JSON.stringify({result:"PASS_REAL_HA_LOCAL_BROWSER_MATRIX",cases:results.length}));
}catch(error){
  const last=browsers.flatMap(b=>b.contexts()).flatMap(c=>c.pages()).at(-1);
  let caption="",environment=null;
  if(ownerDiagnostic){try{
    // Existing owner read is diagnostic only. Log counts/qualification, never
    // owner bodies, tokens or text, and do not feed this response to displays.
    const response=await ownerDiagnostic();
    const body=await response.json(), projection=body.snapshot || body;
    wire.push({scope:"owner_diagnostic",status:response.status(),keys:Object.keys(body),
      moment_types:projection.dj_moments?.map(m=>m.type),
      qualification:projection.dj_moments?.map(m=>m.delivery?.qualification)});
  }catch(_){} }
  if(last){try{caption=(await last.locator("#handoff").innerText()).replace(/[0-9]{6}/g,"[code]");
    environment=await last.evaluate(()=>({protocol:location.protocol,search:location.search,hash:location.hash,
      secure:isSecureContext,crypto:!!crypto.getRandomValues,mode:window.DJC_VIBECAST_MODE}));
    await last.screenshot({path:resolve(output,"failure.png")});}catch(_){} }
  await writeFile(resolve(output,"failure.json"),JSON.stringify({error:error.message,violations,wire,caption,environment},null,2)+"\n");
  throw error;
}finally{
  if(finishSession && api)await finishSession().catch(()=>{});
  for(const browser of browsers)await browser.close();
  if(api)await api.dispose();
  for(const socket of sockets)socket.destroy();
  for(const child of children){child.stdin.end();child.kill();}
  await new Promise(done=>proxy.close(done));
}
