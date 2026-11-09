// Exercise the shared renderer in WebKit with a closed display transport fixture.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const {webkit} = require(process.env.DJC_PLAYWRIGHT);
const root = path.resolve(__dirname, "../..");
const html = fs.readFileSync(path.join(root,"custom_components/djconnect/vibecast_display.html"),"utf8");
const origin = "https://ha.example.test";
const cover = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAIAAAD8GO2jAAAANUlEQVR4nO3QsQ0AMAzDsLT//9yeoCkbeYAN6LzZdZf3x0GSKEmUJEoSJYmSREmiJFGSaMoHo8QBPwYSAhsAAAAASUVORK5CYII=", "base64");
const grant = "djcd_" + "A".repeat(43);
const binding = {issuer_epoch:"epoch",display_id:"display",share_id:"share",share_generation:1,session_id:"session"};

async function main() {
  const browser = await webkit.launch({timeout:12000});
  try {
    const page = await browser.newPage({viewport:{width:1280,height:720},reducedMotion:"reduce"});
    page.setDefaultTimeout(5000);
    let socket;
    await page.route(origin+"/**",route=>{
      const endpoint = new URL(route.request().url()).pathname.split("/").pop();
      if(endpoint==="display") return route.fulfill({body:html,contentType:"text/html"});
      if(endpoint==="claim") return route.fulfill({json:{success:true,contract_version:1,code:"123456",
        expires_in:120,issuer_epoch:"epoch",claim_id:"claim",claim_secret:"secret",browser_generation:"generation"}});
      if(endpoint==="artwork") {
        assert.equal(route.request().headers().authorization,"Bearer "+grant);
        assert.equal(route.request().postDataJSON().reference,"a".repeat(64));
        return route.fulfill({body:cover,contentType:"image/png",
          headers:{"Content-Length":String(cover.length)}});
      }
      assert.equal(endpoint,"collect");
      return route.fulfill({json:{success:true,state:"admitted",...binding,grant_token:grant,lease_expires_in:60,
        capabilities:{owner_controls:false,session_end:false}}});
    });
    await page.routeWebSocket("wss://ha.example.test/api/djconnect/v1/display/live",ws=>{
      socket=ws;
      ws.onMessage(data=>assert.equal(JSON.parse(data).grant_token,grant));
    });
    const music = [
      "Listen for the bass line in the second verse. It leaves space for the lead guitar.",
      "The opening riff comes back in the outro, this time with the rhythm section stripped back.",
      "That soft keyboard chord under the chorus gives the vocal room to carry.",
      "The mix puts the drums up front, with the backing vocals just behind them."
    ];
    const cards=Array.from({length:11},(_,index)=>({
      moment_id:"published-"+index,type:"album",
      content:index===10 ? music[0].repeat(15) : music[index%music.length],
      display_expires_at:new Date(Date.now()+40000).toISOString()
    }));
    function snapshot(count) {
      socket.send(JSON.stringify({type:"snapshot",contract_version:1,connection_generation:1,snapshot:{
        ...binding,contract_version:1,session:{session_id:"session",runtime_state:"active",locale:"en"},
        playback:{state:"playing",item_id:"current",title:"Current recording",artist:"Artist",album:"Album"},
        artwork:{item_id:"current",reference:"a".repeat(64),
          expires_at:cards[0].display_expires_at},
        shared_flow:cards.slice(0,count),dj_moments:[{content:"Legacy card must stay out of the Flow"}]}}));
    }
    await page.goto(origin+"/djconnect/vibecast/display");
    await page.waitForFunction(()=>document.querySelector("#handoff")?.textContent.includes("Reconnecting") ||
      document.querySelector("#handoff")?.textContent.includes("Connecting")).catch(()=>{});
    for(let i=0;!socket && i<50;i++) await new Promise(resolve=>setTimeout(resolve,50));
    assert.ok(socket);
    snapshot(8);
    const viewport=page.locator("#flow-viewport"), rows=page.locator(".flow-card");
    const atEdge=()=>viewport.evaluate(e=>e.scrollHeight-e.clientHeight-e.scrollTop<=4);
    await rows.nth(7).waitFor();
    const albumCover=page.locator("#artwork");
    await page.waitForFunction(()=>document.querySelector("#artwork").naturalWidth>0);
    const coverUrl=await albumCover.getAttribute("src");
    assert.match(coverUrl,/^blob:/);
    assert.equal(await rows.count(),8);
    assert.equal(await atEdge(),true);
    assert.equal(await viewport.getAttribute("tabindex"),"0");
    const top=await page.locator("#title").boundingBox();
    const styles=await rows.evaluateAll(items=>items.slice(-4).map(row=>{
      const style=getComputedStyle(row);
      return {font:parseFloat(style.fontSize),radius:style.borderTopLeftRadius,border:style.borderTopColor};
    }));
    assert.deepEqual(styles.map(item=>item.radius),["18px","18px","18px","32px"]);
    assert.ok(styles.every((item,index)=>index===0 || styles[index-1].font<item.font));
    assert.match(styles[3].border,/255, 255, 255, 0.32/);
    await viewport.focus();
    await page.keyboard.press("ArrowUp");
    await page.waitForFunction(()=>!document.querySelector("#flow-live").hidden);
    await page.keyboard.press("Home");
    await page.waitForFunction(()=>document.querySelector("#flow-viewport").scrollTop===0);
    const live=page.getByRole("button",{name:"Back to live"});
    await live.waitFor();
    assert.equal(await atEdge(),false);
    snapshot(9);
    await rows.nth(8).waitFor({state:"attached"});
    assert.equal(await atEdge(),false);
    assert.equal(await viewport.evaluate(e=>e.scrollTop),0);
    assert.equal((await page.locator("#title").boundingBox()).y,top.y);
    assert.equal(await albumCover.getAttribute("src"),coverUrl);
    await live.click();
    assert.equal(await atEdge(),true);
    snapshot(10);
    await rows.nth(9).waitFor();
    assert.equal(await atEdge(),true);
    assert.equal(await page.getByText("Legacy card must stay out of the Flow").count(),0);
    await viewport.hover();
    await page.mouse.wheel(0,-220);
    await live.waitFor();
    assert.equal(await atEdge(),false);
    await viewport.focus();
    await page.keyboard.press("End");
    await live.waitFor({state:"hidden"});
    assert.equal(await atEdge(),true);
    if(process.env.DJC_FLOW_SCREENSHOT) await page.screenshot({path:process.env.DJC_FLOW_SCREENSHOT});
    snapshot(11);
    await rows.nth(10).waitFor();
    const newestTop=(await rows.nth(10).boundingBox()).y;
    const paneTop=(await viewport.boundingBox()).y;
    assert.ok(newestTop>=paneTop && newestTop<paneTop+12);
    socket.close({code:1008});
    await viewport.waitFor({state:"hidden"});
    assert.equal(await rows.count(),0);
    await albumCover.waitFor({state:"hidden"});
    assert.equal(await albumCover.getAttribute("src"),null);
    console.log("WebKit: Flow cards, fixed track bar, keyboard and wheel reading, live return, album cover and withdrawal PASS");
  } finally {
    await browser.close();
  }
}
main().catch(error=>{console.error(error);process.exitCode=1;});
