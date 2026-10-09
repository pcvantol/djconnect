(() => {
  const params = new URLSearchParams(window.location.search);
  const staticHost = window.DJC_VIBECAST_MODE === "cast";
  let haOrigin = "", sessionId = staticHost ? null : params.get("session_id"), broadcastToken = staticHost ? null : params.get("broadcast_token"), endGrant=null;
  const endpoint = path => haOrigin + path;
  const asset = value => haOrigin && String(value || "").startsWith("/") ? haOrigin + value : value;
  const read = (value, path) => path.reduce((current,key) => current && current[key],value);
  function togglePlacement(below) { const stage=document.querySelector && document.querySelector(".stage"); if (stage && stage.classList) stage.classList.toggle("bubble-below",below); }
  const e = id => document.getElementById(id), root = document.documentElement;
  const compatibility={en:"This display needs a compatible DJConnect session",nl:"Dit scherm vereist een compatibele DJConnect-sessie",de:"Dieses Display benötigt eine kompatible DJConnect-Session",fr:"Cet écran nécessite une session DJConnect compatible",es:"Esta pantalla necesita una sesión DJConnect compatible"};
  const copy = {
    en:{idle:"Idle",connecting:"Connecting",live:"Live",unavailable:"No active session",waiting:"Waiting for a session",ambient:"Ambient session",types:{track:"Track",artist:"Artist",album:"Album",genre:"Genre",recommendation:"Recommendation",transition:"Transition",session:"Session"}},
    nl:{idle:"Inactief",connecting:"Verbinden",live:"Live",unavailable:"Geen actieve sessie",waiting:"Wachten op een sessie",ambient:"Ambient sessie",types:{track:"Nummer",artist:"Artiest",album:"Album",genre:"Genre",recommendation:"Aanbeveling",transition:"Overgang",session:"Sessie"}},
    de:{idle:"Inaktiv",connecting:"Verbinden",live:"Live",unavailable:"Keine aktive Session",waiting:"Warten auf eine Session",ambient:"Ambient-Session",types:{track:"Titel",artist:"Künstler",album:"Album",genre:"Genre",recommendation:"Empfehlung",transition:"Übergang",session:"Session"}},
    fr:{idle:"Inactif",connecting:"Connexion",live:"En direct",unavailable:"Aucune session active",waiting:"En attente d’une session",ambient:"Session d’ambiance",types:{track:"Titre",artist:"Artiste",album:"Album",genre:"Genre",recommendation:"Suggestion",transition:"Transition",session:"Session"}},
    es:{idle:"Inactivo",connecting:"Conectando",live:"En directo",unavailable:"No hay sesión activa",waiting:"Esperando una sesión",ambient:"Sesión ambiental",types:{track:"Canción",artist:"Artista",album:"Álbum",genre:"Género",recommendation:"Recomendación",transition:"Transición",session:"Sesión"}}
  };
  let language = (navigator.language || "en").slice(0,2), text = copy[language] || copy.en;
  let projection = {}, socket, reconnectTimer, expiryTimer, scrollTimer, exitTimer, attempts = 0, ended = false;
  let placementCount=0, lastPlacedKey="";
  let playbackItem = "", current = null, previous = null, lastShownAt = -Infinity, lastArtwork = "", lastSequence = 0, snapshotSequence = 0, fieldSequences = {};
  const firstSeen = new Map();
  const endLabels={en:["End session","Could not end the session"],nl:["Sessie beëindigen","Sessie beëindigen is niet gelukt"],de:["Session beenden","Session konnte nicht beendet werden"],fr:["Terminer la session","Impossible de terminer la session"],es:["Finalizar sesión","No se pudo finalizar la sesión"]};
  const previousSourceLabels={en:"MusicBrainz · earlier recording",nl:"MusicBrainz · eerdere opname",de:"MusicBrainz · frühere Aufnahme",fr:"MusicBrainz · enregistrement précédent",es:"MusicBrainz · grabación anterior"};
  const nextLabels={en:"Up next",nl:"Hierna",de:"Als Nächstes",fr:"À suivre",es:"A continuación"};
  function updateClock() {
    if (e("clock")) e("clock").textContent = new Date().toLocaleTimeString(root.lang,{hour:"2-digit",minute:"2-digit",hour12:false});
    const expiry=Date.parse(read(projection,["playback","up_next","expires_at"]) || "");
    if (e("up-next") && Number.isFinite(expiry) && Date.now() >= expiry) e("up-next").hidden=true;
  }
  window.setInterval && window.setInterval(updateClock,1000);
  root.lang = copy[language] ? language : "en";
  const playback = () => projection.playback && typeof projection.playback === "object" ? projection.playback : {};
  const theme = mood => ({chill:"#7d8dff",groove:"#c07dff",energy:"#ff806b",party:"#ffce55"}[mood] || "#9f7cff");
  const format = value => Number.isFinite(value) && value >= 0 ? `${Math.floor(value/60000)}:${String(Math.floor(value/1000)%60).padStart(2,"0")}` : "";
  const reduceMotion = () => !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  function clearTimer(name) {
    const timer = name === "expiry" ? expiryTimer : scrollTimer;
    if (timer && window.clearTimeout) window.clearTimeout(timer);
    if (name === "expiry") expiryTimer = undefined; else scrollTimer = undefined;
  }
  function useLanguage() {
    const requested = String(read(projection,["session","locale"]) || "").slice(0,2).toLowerCase();
    const selected = copy[requested] ? requested : (copy[language] ? language : "en");
    text = copy[selected]; root.lang = selected;
  }
  function keyFor(item) {
    return String(item.moment_id || `${item.playback_item_id || ""}|${item.type || ""}|${item.created_at || ""}|${item.summary || item.content || item.title || ""}`);
  }
  function cardFor(item) {
    if (!item || typeof item !== "object" || item.type === "silence") return null;
    const summary = String(item.summary || item.content || item.title || "").slice(0,1200);
    if (!summary) return null;
    const key = keyFor(item), now = Date.now();
    if (!firstSeen.has(key)) {
      firstSeen.set(key, now);
      if (firstSeen.size > 32) firstSeen.delete(firstSeen.keys().next().value);
    }
    const created = Date.parse(item.created_at || ""), stamped = Number.isFinite(created);
    if (stamped && created > now + 10000) return null;
    const rawDuration = Number(read(item,["presentation_intent","maximum_duration_seconds"]));
    const seconds = Number.isFinite(rawDuration) && rawDuration > 0 ? Math.min(90, rawDuration) : 25;
    const expiry = (stamped ? created : firstSeen.get(key)) + seconds*1000;
    return now < expiry ? {key, created:stamped ? created : firstSeen.get(key), expiry, summary,
      detail:String(item.content || "").slice(0,1200), attribution:item.source_attribution, type:item.type || "", itemId:item.playback_item_id || "", stamped} : null;
  }
  function eligibleCards() {
    const p = playback(), items = Array.isArray(projection.dj_moments) ? projection.dj_moments : [];
    const cards = [];
    for (const item of items.slice(-24)) {
      if (!item || (p.item_id ? item.playback_item_id !== p.item_id : !!item.playback_item_id)) continue;
      const card = cardFor(item);
      if (card) cards.push(card);
    }
    cards.sort((a,b) => a.created - b.created);
    return cards;
  }
  function clearCards() {
    clearTimer("expiry"); clearTimer("scroll"); current = null; previous = null;
    const card = e("moment-card"), history = e("moment-history"), detail = e("moment-detail"), kind = e("moment-type");
    if (exitTimer) window.clearTimeout(exitTimer); exitTimer=undefined;
    if (card) { card.hidden = true; card.classList && card.classList.remove("exiting"); }
    if (history) history.hidden = true;
    history && history.classList && history.classList.remove("leaving");
    if (detail) detail.textContent = "";
    if (kind) kind.textContent = "";
    e("moment").textContent = "";
  }
  function scheduleCardExpiry() {
    clearTimer("expiry");
    const now = Date.now();
    const deadlines = [current,previous].filter(card => card && card.expiry > now).map(card => card.expiry);
    if (deadlines.length) expiryTimer = window.setTimeout(
      () => renderCards(false), Math.max(0,Math.min(...deadlines)-Date.now()+25)
    );
  }
  function showPrevious(card, animate=false) {
    const history = e("moment-history");
    if (!history) return;
    if (!card || Date.now() >= card.expiry) { history.hidden = true; history.classList && history.classList.remove("leaving"); return; }
    const label = text.types[card.type] || "";
    history.textContent = label && !card.summary.toLocaleLowerCase().startsWith(label.toLocaleLowerCase())
      ? `${label} · ${card.summary}` : card.summary;
    history.hidden = false;
    if (animate && !reduceMotion()) {
      history.classList && history.classList.remove("leaving");
      void history.offsetWidth;
      history.classList && history.classList.add("leaving");
    }
  }
  function fitBubble() {
    const stage=document.querySelector && document.querySelector(".stage"), now=document.querySelector && document.querySelector(".now-playing"), shell=e("moment-card"), detail=e("moment-detail");
    if (!stage || !now || !shell || shell.hidden) return;
    const region=stage.getBoundingClientRect(), content=now.getBoundingClientRect();
    const portrait=window.innerHeight>=window.innerWidth;
    const available=portrait ? Math.max(0,(stage.classList.contains("bubble-below") ? region.bottom-content.bottom : content.top-region.top)-24) : region.height*.7;
    shell.style.maxHeight=`${available}px`;
    if (detail) {
      detail.style.maxHeight=portrait ? "12vh" : "30vh";
      const overhead=shell.scrollHeight-detail.offsetHeight;
      detail.style.maxHeight=`${Math.max(0,available-overhead)}px`;
    }
  }
  function showCurrent(card, animate, afterExit=false) {
    const shell = e("moment-card"), kind = e("moment-type"), detail = e("moment-detail");
    if (animate && !afterExit && shell && !shell.hidden && lastPlacedKey !== card.key && !reduceMotion()) {
      if (exitTimer) window.clearTimeout(exitTimer);
      shell.classList && shell.classList.remove("fresh"); shell.classList && shell.classList.add("exiting");
      exitTimer=window.setTimeout(()=>{ exitTimer=undefined; if ((current && current.key) === card.key) showCurrent(card,true,true); },800);
      return;
    }
    e("moment").textContent = card.summary;
    const source=card.attribution;
    const safeSource=source && ({Spotify:"https://open.spotify.com/",MusicBrainz:"https://musicbrainz.org/",Wikidata:"https://www.wikidata.org/wiki/"}[source.provider]) && String(source.url || "").startsWith({Spotify:"https://open.spotify.com/",MusicBrainz:"https://musicbrainz.org/",Wikidata:"https://www.wikidata.org/wiki/"}[source.provider]);
    e("moment-source").hidden=!safeSource;
    e("moment-source").textContent=safeSource ? source.provider : "";
    if (safeSource) e("moment-source").href=source.url; else e("moment-source").removeAttribute("href");
    const previousSource=e("moment-source-previous");
    if (previousSource) {
      const safePrevious=safeSource && source.provider === "MusicBrainz" && /^https:\/\/musicbrainz\.org\/recording\/[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$/.test(String(source.url_previous || "")) && source.url_previous !== source.url;
      previousSource.hidden=!safePrevious;
      previousSource.textContent=safePrevious ? (previousSourceLabels[root.lang] || previousSourceLabels.en) : "";
      if (safePrevious) previousSource.href=source.url_previous; else previousSource.removeAttribute("href");
    }
    if (kind) kind.textContent = text.types[card.type] || "";
    if (detail) {
      detail.textContent = card.detail && card.detail !== card.summary ? card.detail : "";
      detail.scrollTop = 0;
      detail.classList && detail.classList.remove("scrolled");
    }
    if (shell) {
      shell.hidden = false;
      if (exitTimer) window.clearTimeout(exitTimer); exitTimer=undefined;
      shell.classList && shell.classList.remove("fresh","exiting");
      if (lastPlacedKey !== card.key) { placementCount++; lastPlacedKey=card.key; }
      togglePlacement(placementCount % 2 === 0);
      if (animate && !reduceMotion()) {
        void shell.offsetWidth;
        shell.classList && shell.classList.add("fresh");
      }
    }
    fitBubble();
    clearTimer("scroll");
    if ((detail && detail.textContent) && !reduceMotion() && detail.scrollHeight > detail.clientHeight) {
      const step = Math.max(24,parseFloat(getComputedStyle(detail).lineHeight) || 28);
      const advance = () => {
        if ((current && current.key) !== card.key) return;
        const limit = detail.scrollHeight-detail.clientHeight;
        if (detail.scrollTop >= limit-1) return;
        detail.classList && detail.classList.add("scrolled");
        detail.scrollTo ? detail.scrollTo({top:Math.min(limit,detail.scrollTop+step),behavior:"smooth"}) : (detail.scrollTop=Math.min(limit,detail.scrollTop+step));
        scrollTimer = window.setTimeout(advance,2600);
      };
      scrollTimer = window.setTimeout(advance,5000);
    }
    scheduleCardExpiry();
  }
  function renderCards(animate) {
    const p = playback(), item = p.item_id || "";
    if (item !== playbackItem) {
      playbackItem = item; lastShownAt = -Infinity; clearCards();
    }
    if (current && Date.now() >= current.expiry) {
      if (!exitTimer && !reduceMotion()) {
        const expiredKey=current.key;
        e("moment-card").classList && e("moment-card").classList.add("exiting");
        exitTimer=window.setTimeout(() => { if ((current && current.key)===expiredKey) clearCards(); exitTimer=undefined; },800);
      } else if (reduceMotion()) clearCards();
    }
    const cards = eligibleCards(), latest = cards[cards.length-1];
    if (!latest) { if (!exitTimer) clearCards(); return; }
    if ((current && current.key) === latest.key) { showPrevious(previous); scheduleCardExpiry(); return; }
    if (latest.created < lastShownAt) return;
    previous = animate && current && current.itemId === latest.itemId ? current : null;
    current = latest; lastShownAt = latest.created;
    showPrevious(previous, animate); showCurrent(latest, animate);
  }
  function render(animate=false) {
    useLanguage(); updateClock();
    e("end-session").hidden=!endGrant || ended;
    e("end-session").setAttribute("aria-label",(endLabels[root.lang] || endLabels.en)[0]);
    e("state").hidden=!!endGrant && !ended;
    const p = playback(), mood = read(projection,["session","selected_mood"]);
    document.body.classList.toggle("idle",!p.title);
    e("mood").textContent = mood || text.ambient;
    e("title").textContent = p.title || text.waiting;
    e("artist").textContent = p.artist || "";
    e("album").textContent = p.album || "";
    const next=p.up_next;
    const safeNext=next && typeof next === "object" && next.title && next.artist && p.item_id && next.current_item_id === p.item_id && Date.parse(next.expires_at || "") > Date.now();
    e("up-next").hidden=!safeNext;
    e("next-label").textContent=nextLabels[root.lang] || nextLabels.en;
    e("next-title").textContent=safeNext ? next.title : "";
    e("next-artist").textContent=safeNext ? next.artist : "";
    e("next-art").hidden=!(safeNext && next.artwork_url);
    if (safeNext && next.artwork_url) e("next-art").src=asset(next.artwork_url);
    else e("next-art").removeAttribute("src");
    const validSpotify=String(p.source_url || "").startsWith("https://open.spotify.com/track/");
    e("spotify-source").hidden=!validSpotify;
    if (validSpotify) e("spotify-source").href=p.source_url; else e("spotify-source").removeAttribute("href");
    const art = asset(p.artwork_url || "");
    e("artwork").hidden = !art;
    if (art !== lastArtwork) { e("artwork").src = art; lastArtwork = art; }
    e("artwork").alt = art ? (p.album || p.title || "") : "";
    root.style.setProperty("--art",art ? `url("${art.split('"').join('%22')}")` : "none");
    if (!art) { root.style.setProperty("--accent",theme(mood)); for (const key of ["--tone1","--tone2","--tone3"]) root.style.removeProperty && root.style.removeProperty(key); }
    const active = Number.isFinite(p.duration_ms) && Number.isFinite(p.position_ms) && p.duration_ms > 0;
    e("progress").hidden = !active;
    if (active) { e("progress").max=p.duration_ms; e("progress").value=p.position_ms; e("time").textContent=`${format(p.position_ms)} / ${format(p.duration_ms)}`; }
    else e("time").textContent="";
    renderCards(animate);
  }
  function apply(snapshot) {
    const watermark = Number(read(snapshot,["broadcast","snapshot_watermark"]));
    if (Number.isFinite(watermark) && watermark < lastSequence) return;
    if (Number.isFinite(watermark)) lastSequence = snapshotSequence = watermark;
    fieldSequences = {};
    projection = snapshot && typeof snapshot === "object" ? snapshot : {};
    render(false);
  }
  function event(frame) {
    const p = (frame && frame.payload);
    if (ended || !p || typeof p !== "object" || (frame.session_id && frame.session_id !== sessionId)) return;
    const sequence = Number(frame.delivery_sequence);
    const ordered = Number.isFinite(sequence) && sequence > 0;
    if (ordered && sequence <= snapshotSequence) return;
    if (ordered) lastSequence = Math.max(lastSequence,sequence);
    if (frame.event_type === "runtime_ended" || frame.event_type === "broadcast_stopped") {
      ended=true; broadcastToken=null; endGrant=null; apply({}); e("state").textContent=text.idle; if (socket) socket.close(); return;
    }
    for (const key of ["session","playback","planner","session_flow","audience","broadcast"])
      if (p[key] && (!ordered || sequence > (fieldSequences[key] || snapshotSequence))) {
        projection[key]=p[key];
        if (ordered) fieldSequences[key]=sequence;
      }
    if (p.dj_moment) {
      const items = Array.isArray(projection.dj_moments) ? projection.dj_moments : [];
      const key = keyFor(p.dj_moment);
      if (!items.some(item => item && keyFor(item) === key)) projection.dj_moments = [...items.slice(-23),p.dj_moment];
      render(true);
    } else render(false);
  }
  window.addEventListener("resize",fitBubble);
  e("artwork").addEventListener("load",()=>{
    fitBubble();
    // Sample colors only; never display cropped/blurred Spotify artwork.
    const image=e("artwork"), identity=lastArtwork;
    if (!identity || !image.naturalWidth) return;
    try {
      const canvas=document.createElement("canvas"); canvas.width=24; canvas.height=24;
      const ctx=canvas.getContext("2d",{willReadFrequently:true}); ctx.drawImage(image,0,0,24,24);
      const pixels=ctx.getImageData(0,0,24,24).data, buckets=new Map();
      for (let i=0;i<pixels.length;i+=4) {
        const channels=[pixels[i],pixels[i+1],pixels[i+2]];
        const key=channels.map(c=>Math.round(c/32)*32).join(",");
        const bucket=buckets.get(key) || {count:0,total:[0,0,0]}; bucket.count++;
        channels.forEach((c,index)=>bucket.total[index]+=c); buckets.set(key,bucket);
      }
      const tones=[...buckets.values()].sort((a,b)=>b.count-a.count).slice(0,3).map(b=>b.total.map(c=>Math.round(c/b.count)));
      if (identity !== lastArtwork) return;
      tones.forEach((rgb,index)=>root.style.setProperty(`--tone${index+1}`,`rgb(${rgb.map(c=>Math.round(c*.5)).join(" ")})`));
      if (tones[0]) root.style.setProperty("--accent",`rgb(${tones[0].map(c=>Math.max(100,c)).join(" ")})`);
    } catch (_) { /* Same-origin proxy unavailable: keep the neutral palette. */ }
  });
  const url = () => `${haOrigin ? haOrigin.replace(/^https:/,"wss:").replace(/^http:/,"ws:") : (window.location.protocol === "https:" ? "wss:" : "ws:")+"//"+window.location.host}/api/djconnect/v1/session/broadcast/ws/${encodeURIComponent(sessionId)}?broadcast_token=${encodeURIComponent(broadcastToken)}`;
  function connect() {
    if (ended) return;
    e("state").textContent=text.connecting;
    const active = new WebSocket(url()); socket=active;
    active.onopen=() => { if (active !== socket) return; attempts=0; e("state").textContent=text.live; };
    active.onmessage=({data}) => {
      if (active !== socket) return;
      try {
        const f=JSON.parse(data);
        if (f.type === "snapshot" && (!f.session_id || f.session_id === sessionId)) {
          if (staticHost && (!f.capabilities || f.capabilities.view_broadcast !== true || f.capabilities.owner_controls !== false || !f.snapshot || !f.snapshot.session || f.snapshot.session.session_id !== sessionId || (f.snapshot.schema_version !== undefined && f.snapshot.schema_version !== 1))) { stopHost(); e("state").textContent=compatibility[root.lang] || compatibility.en; return; }
          apply(f.snapshot);
        }
        else if (f.type === "event") event(f.data);
        else if (f.type === "error") { ended=true; broadcastToken=null; endGrant=null; apply({}); e("state").textContent=text.unavailable; if (socket) socket.close(); }
      } catch (_) { /* Ignore malformed receiver frames. */ }
    };
    active.onclose=() => {
      if (active !== socket || ended || reconnectTimer) return;
      reconnectTimer=window.setTimeout(() => { reconnectTimer=undefined; attempts++; connect(); },Math.min(1000*2**attempts,5000));
    };
    active.onerror=() => active.close();
  }
  e("end-session").addEventListener("click",async()=>{
    if (!endGrant || ended) return;
    e("end-session").disabled=true;
    const requestedSession=sessionId, requestedGrant=endGrant;
    try {
      const response=await window.fetch(endpoint("/api/djconnect/v1/session/broadcast/control/end"),{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({session_id:sessionId,end_grant:endGrant}),cache:"no-store",credentials:"omit"});
      const result=await response.json();
      if (sessionId !== requestedSession || endGrant !== requestedGrant) return;
      if (!response.ok || result.success !== true || result.state !== "ended") throw new Error("end_failed");
      // Server-confirmed end also covers loss of the terminal WebSocket frame.
      event({session_id:sessionId,event_type:"runtime_ended",payload:{}});
    } catch (_) { if (sessionId !== requestedSession || endGrant !== requestedGrant) return; e("state").hidden=false; e("state").textContent=(endLabels[root.lang] || endLabels.en)[1]; }
    finally { if (sessionId === requestedSession) e("end-session").disabled=false; }
  });
  updateClock();
  e("state").textContent=text.idle;
  e("title").textContent=text.waiting;
  e("mood").textContent=text.ambient;
  if (sessionId && broadcastToken) connect(); else e("state").textContent=text.unavailable;
  window.addEventListener("djconnect-handoff",({detail}) => {
    if (!(detail && detail.session_id) || !(detail && detail.broadcast_token)) return;
    stopHost();
    haOrigin=detail.ha_url || ""; sessionId=detail.session_id; broadcastToken=detail.broadcast_token; endGrant=detail.end_grant || null;
    ended=false; projection={}; playbackItem=""; lastShownAt=-Infinity;
    lastSequence=0; snapshotSequence=0; fieldSequences={}; clearCards(); render(false);
    e("handoff").hidden=true; connect();
  });
  function stopHost() {
    ended=true; broadcastToken=null; endGrant=null;
    if (reconnectTimer) window.clearTimeout(reconnectTimer); reconnectTimer=undefined;
    const old=socket; socket=null; if (old) old.close();
    firstSeen.clear(); placementCount=0; lastPlacedKey=""; lastShownAt=-Infinity;
    projection={}; clearCards(); render(false); e("state").textContent=text.idle;
  }
  window.addEventListener("djconnect-host-stop",stopHost);
  window.addEventListener("beforeunload",stopHost);
})()