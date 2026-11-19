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
    const page = await browser.newPage({viewport:{width:1280,height:720},reducedMotion:"reduce",locale:"en-US",timezoneId:"Europe/Amsterdam"});
    page.setDefaultTimeout(5000);
    let socket;
    await page.route(origin+"/**",route=>{
      const endpoint = new URL(route.request().url()).pathname.split("/").pop();
      if(endpoint==="display") return route.fulfill({body:html,contentType:"text/html"});
      if(endpoint==="claim") return route.fulfill({json:{success:true,contract_version:1,code:"123456",
        expires_in:120,issuer_epoch:"epoch",claim_id:"claim",claim_secret:"secret",browser_generation:"generation"}});
      if(endpoint==="artwork") {
        assert.equal(route.request().headers().authorization,"Bearer "+grant);
        assert.ok(["a".repeat(64),"b".repeat(64)].includes(route.request().postDataJSON().reference));
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
      moment_id:"published-"+index,type:index===5 ? "genre" : index===6 ? "music_announcement" : "album",
      playback_item_id:index===6 ? "previous" : "current",
      content:index===10 ? music[0].repeat(15) : music[index%music.length],
      display_expires_at:new Date(Date.now()-1000).toISOString(),
      flow_expires_at:new Date(Date.now()+40000).toISOString()
    }));
    cards[7].created_at="2026-01-01T23:05:00Z";
    const previousTrack="https://open.spotify.com/track/"+"B".repeat(22);
    cards[6].artwork={item_id:"previous",reference:"b".repeat(64),source_url:previousTrack,
      expires_at:cards[6].flow_expires_at};
    function snapshot(count, itemId="current", state="playing", output={output_label:"Living room",volume_percent:37}, spotlight={}) {
      socket.send(JSON.stringify({type:"snapshot",contract_version:1,connection_generation:1,snapshot:{
        ...binding,contract_version:1,session:{session_id:"session",runtime_state:"active",locale:"en"},
        playback:{state,item_id:itemId,title:"Current recording",artist:"Artist",album:"Album",
          duration_ms:240000,position_ms:60000,...output},
        artwork:{item_id:"current",reference:"a".repeat(64),
          expires_at:cards[0].flow_expires_at},
        shared_flow:cards.slice(0,count),dj_moments:[{content:"Legacy card must stay out of the Flow"}],...spotlight}}));
    }
    await page.goto(origin+"/djconnect/vibecast/display");
    await page.waitForFunction(()=>document.querySelector("#handoff")?.textContent.includes("Reconnecting") ||
      document.querySelector("#handoff")?.textContent.includes("Connecting")).catch(()=>{});
    for(let i=0;!socket && i<50;i++) await new Promise(resolve=>setTimeout(resolve,50));
    assert.ok(socket);
    snapshot(8);
    const viewport=page.locator("#flow-viewport"), rows=page.locator("#flow-cards > .flow-card");
    const atEdge=()=>viewport.evaluate(e=>e.scrollTop<=4);
    await rows.nth(7).waitFor();
    const timestamp=rows.first().locator("time");
    assert.equal(await timestamp.getAttribute("datetime"),cards[7].created_at);
    assert.equal(await timestamp.textContent(),"00:05");
    assert.equal(await rows.nth(2).locator("time").count(),0);
    const albumCover=page.locator("#artwork");
    await page.waitForFunction(()=>document.querySelector("#artwork").naturalWidth>0);
    const coverUrl=await albumCover.getAttribute("src");
    assert.match(coverUrl,/^blob:/);
    const contributionCover=rows.first().locator(".flow-artwork");
    await contributionCover.waitFor();
    assert.equal(await contributionCover.getAttribute("src"),coverUrl);
    assert.equal(await rows.nth(2).locator(".flow-artwork").getAttribute("src"),coverUrl);
    const previousCover=rows.nth(1).locator(".flow-artwork");
    await previousCover.waitFor();
    const previousUrl=await previousCover.getAttribute("src");
    assert.match(previousUrl,/^blob:/);
    assert.notEqual(previousUrl,coverUrl);
    assert.equal(await rows.nth(1).locator(".flow-artwork-link").getAttribute("href"),previousTrack);
    assert.equal(await rows.count(),8);
    assert.equal(await atEdge(),true);
    assert.equal(await page.locator(".now-playing").evaluate(node=>getComputedStyle(node).backgroundColor),"rgba(0, 0, 0, 0)");
    assert.equal(await page.locator("#display-speaker-label").textContent(),"Living room");
    assert.equal(await page.locator("#display-volume-label").count(),0);
    assert.equal(await page.locator("#display-output :is(button,input)").count(),0);
    assert.equal(await page.locator("#display-meter progress").count(),1);
    assert.equal(await page.locator("#time").textContent(),"1:00 / 4:00");
    const equalizer=page.locator("#display-equalizer i").first();
    assert.equal(await equalizer.evaluate(node=>getComputedStyle(node).animationName),"none");
    await page.emulateMedia({reducedMotion:"no-preference"});
    assert.equal(await equalizer.evaluate(node=>getComputedStyle(node).animationName),"display-equalize");
    snapshot(8,"current","paused",{volume_percent:0});
    await page.locator("#display-output").waitFor({state:"hidden"});
    assert.equal(await equalizer.evaluate(node=>getComputedStyle(node).animationName),"none");
    await page.emulateMedia({reducedMotion:"reduce"});
    snapshot(8);
    assert.equal(await viewport.getAttribute("tabindex"),"0");
    const top=await page.locator("#title").boundingBox();
    const styles=await rows.evaluateAll(items=>items.slice(0,4).map(row=>{
      const style=getComputedStyle(row);
      return {font:parseFloat(style.fontSize),radius:style.borderTopLeftRadius,border:style.borderTopColor};
    }));
    assert.deepEqual(styles.map(item=>item.radius),["32px","18px","18px","18px"]);
    assert.ok(styles.every((item,index)=>index===0 || styles[index-1].font>item.font));
    assert.match(styles[0].border,/255, 255, 255, 0.32/);
    const coverBounds=await albumCover.boundingBox();
    const viewportBounds=await viewport.boundingBox();
    assert.ok(coverBounds.width>=170 && viewportBounds.height>=180);
    assert.ok((await rows.nth(1).boundingBox()).y < viewportBounds.y+viewportBounds.height);
    await viewport.focus();
    await page.keyboard.press("ArrowDown");
    await page.waitForFunction(()=>!document.querySelector("#flow-live").hidden);
    const readingRow=await viewport.evaluateHandle(e=>[...e.querySelectorAll("#flow-cards > .flow-card")]
      .find(row=>row.getBoundingClientRect().bottom>e.getBoundingClientRect().top));
    const readingTop=await readingRow.evaluate(row=>row.getBoundingClientRect().top);
    const live=page.getByRole("button",{name:"Back to live"});
    await live.waitFor();
    assert.equal(await atEdge(),false);
    await page.emulateMedia({reducedMotion:"no-preference"});
    const spotlight=page.locator("#moment-card");
    const readingScroll=await viewport.evaluate(node=>node.scrollTop);
    const moment={moment_id:"active-spotlight",type:"album",content:"Current DJ spotlight",
      created_at:new Date(Date.now()-10000).toISOString(),display_expires_at:new Date(Date.now()+2200).toISOString(),
      presentation_intent:{maximum_duration_seconds:1}};
    snapshot(8,"current","playing",undefined,{current_moment_id:moment.moment_id,dj_moments:[moment],session_presentation:{mood:"groove"}});
    await spotlight.waitFor();
    const avatar=spotlight.locator("#spotlight-avatar");
    await avatar.waitFor();
    assert.equal(await spotlight.getAttribute("data-mood"),"groove");
    assert.equal(await avatar.locator("stop").first().evaluate(node=>getComputedStyle(node).stopColor),"rgb(6, 199, 173)");
    const wave=avatar.locator(".spotlight-wave rect").first();
    assert.equal(await wave.evaluate(node=>getComputedStyle(node).animationName),"spotlight-pulse");
    await page.emulateMedia({reducedMotion:"reduce"});
    assert.equal(await wave.evaluate(node=>getComputedStyle(node).animationName),"none");
    await page.emulateMedia({reducedMotion:"no-preference"});
    assert.equal(await spotlight.locator("#moment").textContent(),"Current DJ spotlight");
    if(process.env.DJC_SPOTLIGHT_SCREENSHOT) await page.screenshot({path:process.env.DJC_SPOTLIGHT_SCREENSHOT});
    await viewport.waitFor({state:"hidden"});
    const nowPlaying=await page.locator(".now-playing").boundingBox();
    const spotlightGap=(await spotlight.boundingBox()).y-nowPlaying.y-nowPlaying.height;
    assert.ok(spotlightGap>=0 && spotlightGap<30);
    assert.equal((await page.locator("#title").boundingBox()).y,top.y);
    await spotlight.waitFor({state:"hidden"});
    await viewport.waitFor({state:"visible"});
    assert.equal(await viewport.evaluate(node=>getComputedStyle(node).transitionDuration),"0.35s");
    assert.equal(await viewport.evaluate(node=>node.scrollTop),readingScroll);
    const nextMoment={...moment,moment_id:"next-spotlight",display_expires_at:new Date(Date.now()+10000).toISOString()};
    snapshot(8,"current","playing",undefined,{current_moment_id:nextMoment.moment_id,dj_moments:[nextMoment]});
    await spotlight.waitFor();
    snapshot(8,"current","playing",undefined,{current_moment_id:null,dj_moments:[nextMoment]});
    await spotlight.waitFor({state:"hidden"});
    await viewport.waitFor({state:"visible"});
    assert.equal(await viewport.evaluate(node=>node.scrollTop),readingScroll);
    await page.emulateMedia({reducedMotion:"reduce"});
    snapshot(9);
    await rows.nth(8).waitFor({state:"attached"});
    assert.equal(await atEdge(),false);
    assert.ok(Math.abs(await readingRow.evaluate(row=>row.getBoundingClientRect().top)-readingTop)<=2);
    assert.equal((await page.locator("#title").boundingBox()).y,top.y);
    assert.equal(await albumCover.getAttribute("src"),coverUrl);
    await live.click();
    assert.equal(await atEdge(),true);
    snapshot(10);
    await rows.nth(9).waitFor();
    assert.equal(await atEdge(),true);
    assert.equal(await page.getByText("Legacy card must stay out of the Flow").count(),0);
    await viewport.hover();
    await page.mouse.wheel(0,220);
    await live.waitFor();
    assert.equal(await atEdge(),false);
    await viewport.focus();
    await page.keyboard.press("Home");
    await live.waitFor({state:"hidden"});
    assert.equal(await atEdge(),true);
    if(process.env.DJC_FLOW_SCREENSHOT) await page.screenshot({path:process.env.DJC_FLOW_SCREENSHOT});
    snapshot(11);
    await rows.nth(10).waitFor();
    const newestTop=(await rows.first().boundingBox()).y;
    const paneTop=(await viewport.boundingBox()).y;
    assert.ok(newestTop>=paneTop && newestTop<paneTop+12);
    cards[0].flow_expires_at=new Date(Date.now()-1000).toISOString();
    snapshot(11);
    await page.waitForFunction(()=>document.querySelectorAll("#flow-cards > .flow-card").length===10);
    snapshot(11,"next-recording");
    await contributionCover.waitFor({state:"detached"});
    const retainedCover=rows.locator('a[href="'+previousTrack+'"] img');
    assert.equal(await retainedCover.getAttribute("src"),previousUrl);
    assert.equal(await rows.locator(".flow-artwork").count(),1);
    cards[6].flow_expires_at=new Date(Date.now()-1000).toISOString();
    snapshot(11,"next-recording");
    await retainedCover.waitFor({state:"detached"});

    const horizon={valid_until:new Date(Date.now()+10000).toISOString(),
      sections:[{title:"Direction",text:"Keep the musical thread steady."}]};
    const session={session_id:"session",runtime_state:"active",locale:"es"};
    snapshot(11,"next-recording","playing",undefined,{session,horizon});
    const horizonCard=page.locator("#horizon-card");
    await horizonCard.waitFor({state:"visible"});
    assert.equal(await horizonCard.locator("h2").textContent(),"Los próximos minutos");
    assert.equal(await horizonCard.locator("#horizon-sections p").textContent(),horizon.sections[0].text);
    assert.equal(await page.locator("#renderer-build-label").textContent(),"Versión de VibeCast");
    assert.equal(await rows.first().locator(".flow-kind").textContent(),"Álbum");
    assert.equal(await rows.first().locator("p").textContent(),cards[10].content);
    snapshot(11,"next-recording","playing",undefined,{session,
      horizon:{...horizon,valid_until:new Date(Date.now()-1000).toISOString()}});
    await horizonCard.waitFor({state:"hidden"});
    assert.equal(await horizonCard.locator("#horizon-sections").textContent(),"");
    socket.close({code:1008});
    await viewport.waitFor({state:"hidden"});
    assert.equal(await rows.count(),0);
    await albumCover.waitFor({state:"hidden"});
    assert.equal(await albumCover.getAttribute("src"),null);
    console.log("Browser: Flow cards, fixed track bar, scrolling, timed DJ spotlight, silence, matching artwork and withdrawal PASS");
  } finally {
    await browser.close();
  }
}
main().catch(error=>{console.error(error);process.exitCode=1;});
