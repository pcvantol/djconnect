/* B host only. One maintained renderer; no credentials in URLs or persistence. */
(()=>{
  "use strict";
  const language=(navigator.language || "en").slice(0,2);
  const words={
    en:{approve:"Choose ‘Share VibeCast Screen’ in the app and enter the code below.",retry:"Try again",expired:"This screen’s access has expired. Approve it again in DJConnect.",unavailable:"Cannot reach DJConnect. Check the external HTTPS address and connection.",denied:"Screen access was withdrawn or the session ended.",reconnect:"Reconnecting…",capacity:"Too many screens or requests. Try again shortly."},
    nl:{approve:"Kies 'VibeCast scherm delen' in de app.\nVul onderstaande code in.",retry:"Opnieuw proberen",expired:"De toegang van dit scherm is verlopen. Keur het opnieuw goed in DJConnect.",unavailable:"DJConnect is niet bereikbaar. Controleer het externe HTTPS-adres en de verbinding.",denied:"De schermtoegang is ingetrokken of de sessie is beëindigd.",reconnect:"Opnieuw verbinden…",capacity:"Te veel schermen of verzoeken. Probeer het zo opnieuw."},
    de:{approve:"Wähle in der App „VibeCast-Bildschirm teilen“ und gib den unten stehenden Code ein.",retry:"Erneut versuchen",expired:"Der Zugriff dieses Bildschirms ist abgelaufen. Genehmige ihn erneut in DJConnect.",unavailable:"DJConnect ist nicht erreichbar. Prüfe die externe HTTPS-Adresse und die Verbindung.",denied:"Der Bildschirmzugriff wurde entzogen oder die Session beendet.",reconnect:"Verbindung wird wiederhergestellt…",capacity:"Zu viele Bildschirme oder Anfragen. Versuche es gleich erneut."},
    fr:{approve:"Choisis « Partager l’écran VibeCast » dans l’app et saisis le code ci-dessous.",retry:"Réessayer",expired:"L’accès de cet écran a expiré. Autorisez-le à nouveau dans DJConnect.",unavailable:"DJConnect est inaccessible. Vérifiez l’adresse HTTPS externe et la connexion.",denied:"L’accès de l’écran a été retiré ou la session est terminée.",reconnect:"Reconnexion…",capacity:"Trop d’écrans ou de demandes. Réessayez dans un instant."},
    es:{approve:"Elige «Compartir pantalla VibeCast» en la app e introduce el código que aparece abajo.",retry:"Volver a intentar",expired:"El acceso de esta pantalla ha caducado. Autorízala de nuevo en DJConnect.",unavailable:"No se puede acceder a DJConnect. Comprueba la dirección HTTPS externa y la conexión.",denied:"Se ha retirado el acceso de la pantalla o ha terminado la sesión.",reconnect:"Reconectando…",capacity:"Demasiadas pantallas o solicitudes. Vuelve a intentarlo en un momento."}
  };
  const outcomes={
    en:{newcode:"Access could not be confirmed. Request a new code and approve this screen again.",configuration:"Check the external HTTPS address in Home Assistant and reopen this screen from your paired DJConnect app."},
    nl:{newcode:"De toegang kon niet worden bevestigd. Vraag een nieuwe code aan en keur dit scherm opnieuw goed.",configuration:"Controleer het externe HTTPS-adres in Home Assistant en open dit scherm opnieuw vanuit je gekoppelde DJConnect-app."},
    de:{newcode:"Der Zugriff konnte nicht bestätigt werden. Fordere einen neuen Code an und genehmige den Bildschirm erneut.",configuration:"Prüfe die externe HTTPS-Adresse in Home Assistant und öffne den Bildschirm erneut über deine gekoppelte DJConnect-App."},
    fr:{newcode:"L’accès n’a pas pu être confirmé. Demandez un nouveau code et autorisez à nouveau cet écran.",configuration:"Vérifiez l’adresse HTTPS externe dans Home Assistant et rouvrez cet écran depuis votre app DJConnect associée."},
    es:{newcode:"No se ha podido confirmar el acceso. Solicita un código nuevo y vuelve a autorizar esta pantalla.",configuration:"Comprueba la dirección HTTPS externa en Home Assistant y vuelve a abrir esta pantalla desde tu app DJConnect vinculada."}
  };
  const copyLabels={
    en:["Copy pairing code","Code copied","Could not copy code"],
    nl:["Koppelcode kopiëren","Code gekopieerd","Kopiëren is niet gelukt"],
    de:["Kopplungscode kopieren","Code kopiert","Code konnte nicht kopiert werden"],
    fr:["Copier le code d’association","Code copié","Impossible de copier le code"],
    es:["Copiar el código de vinculación","Código copiado","No se pudo copiar el código"]
  };
  const panel=document.getElementById("handoff");
  let sessionLocale="", text;
  function selectLocale(locale){
    const selected=typeof locale==="string" && /^(en|nl|de|fr|es)$/.test(locale) ? locale : "";
    const labels=selected || language;
    text={...(words[labels] || words.en),...(outcomes[labels] || outcomes.en)};
    if(selected===sessionLocale)return;
    sessionLocale=selected;
    window.dispatchEvent(new CustomEvent("djconnect-display-locale",{detail:selected}));
  }
  selectLocale("");
  function failureText(error,collecting=false){
    if(error.status===429)return text.capacity;
    if(error.code==="display_external_url_unavailable" || error.code==="display_tls_required" || error.code==="display_origin_denied")return text.configuration;
    if(error.status===410 || error.code==="display_lease_expired")return text.expired;
    if(collecting && (error.status===404 || !error.status))return text.newcode;
    if([401,403,404,409].includes(error.status))return text.denied;
    return text.unavailable;
  }
  let generation=0, claim=null, grant=null, socket=null, stopped=false, sequence=0;
  let lease=0, claimDeadline=0, renewalBusy=false, connectionGeneration=0;
  const timers=new Set(), requests=new Set();
  const now=()=>performance.now();
  const nonce=()=>{
    const bytes=new Uint8Array(32); crypto.getRandomValues(bytes);
    return btoa(String.fromCharCode(...bytes)).replace(/\+/g,"-").replace(/\//g,"_").replace(/=+$/,"");
  };
  function claimRequestId(){
    try{
      const state=window.history.state;
      const previous=state?.vibeCastClaimRequestId;
      if(typeof previous==="string" && /^[A-Za-z0-9_-]{43}$/.test(previous))return previous;
      const id=nonce();
      window.history.replaceState({...state,vibeCastClaimRequestId:id},"");
      return id;
    }catch(_){return null;}
  }
  function later(fn,delay){const timer=setTimeout(()=>{timers.delete(timer);fn();},delay);timers.add(timer);return timer;}
  function clearContent(){clearArtwork();window.dispatchEvent(new Event("djconnect-display-clear"));}
  const artwork=new Map();
  let wantedArtwork=new Map(), artworkBusy=false;
  function publishArtwork(){
    window.dispatchEvent(new CustomEvent("djconnect-display-artwork",{
      detail:[...artwork.values()].filter(cover=>cover.url)}));
  }
  function removeArtwork(reference){
    const cover=artwork.get(reference);
    if(!cover)return;
    artwork.delete(reference);
    cover.controller.abort();clearTimeout(cover.timer);
    if(cover.url)URL.revokeObjectURL(cover.url);
  }
  function clearArtwork(){
    wantedArtwork.clear();
    for(const reference of artwork.keys())removeArtwork(reference);
    publishArtwork();
  }
  function updateArtwork(snapshot){
    const wanted=new Map();
    function add(cover,itemId,deadline=Infinity){
      const until=Math.min(Date.parse(cover?.expires_at),deadline);
      if(!cover || !itemId || cover.item_id!==itemId ||
         !/^[a-f0-9]{64}$/.test(cover.reference) || !(until>Date.now()))return;
      const existing=wanted.get(cover.reference);
      if(!existing || existing.until<until)wanted.set(cover.reference,{...cover,until});
    }
    add(snapshot.artwork,snapshot.playback?.item_id);
    if(Array.isArray(snapshot.shared_flow)){
      for(const item of snapshot.shared_flow.slice(-12).reverse()){
        if(item)add(item.artwork,item.playback_item_id,Date.parse(item.flow_expires_at));
      }
    }
    wantedArtwork=wanted;
    let changed=false;
    for(const [reference,cover] of artwork){
      if(!wanted.has(reference) || wanted.get(reference).until!==cover.until){
        removeArtwork(reference);
        changed=true;
      }
    }
    if(changed)publishArtwork();
    void fetchArtwork();
  }
  async function fetchArtwork(){
    if(artworkBusy)return;
    artworkBusy=true;
    try{
      const attempted=new Set();
      let desired=wantedArtwork;
      while(!expired()){
        if(desired!==wantedArtwork){desired=wantedArtwork;attempted.clear();}
        const cover=[...desired.values()].find(value=>
          !attempted.has(value.reference) && !artwork.has(value.reference) && value.until>Date.now());
        if(!cover)break;
        attempted.add(cover.reference);
        const controller=new AbortController();
        const pending={...cover,controller,url:null};
        artwork.set(cover.reference,pending);
        pending.timer=setTimeout(()=>{
          if(artwork.get(cover.reference)!==pending)return;
          removeArtwork(cover.reference);
          publishArtwork();
        },cover.until-Date.now());
        const timeout=setTimeout(()=>controller.abort(),10000);
        try{
          const response=await fetch("/api/djconnect/v1/display/artwork",{method:"POST",credentials:"omit",cache:"no-store",redirect:"error",
            headers:{"Content-Type":"application/json",Authorization:"Bearer "+grant.grant_token},
            body:JSON.stringify({contract_version:1,...binding(),reference:cover.reference}),signal:controller.signal});
          const size=Number(response.headers.get("Content-Length")),mime=response.headers.get("Content-Type");
          if(!response.ok || !(size>0 && size<=256000) || !["image/jpeg","image/png"].includes(mime))throw new Error("artwork");
          const blob=await response.blob();
          if(artwork.get(cover.reference)!==pending || expired() || cover.until<=Date.now())continue;
          if(blob.size!==size)throw new Error("artwork");
          pending.url=URL.createObjectURL(blob);
          publishArtwork();
        }catch(_){
          if(artwork.get(cover.reference)===pending)removeArtwork(cover.reference);
        }finally{clearTimeout(timeout);}
      }
    }finally{artworkBusy=false;}
  }
  function show(message,code="",retry=false){
    const pending=code===null;
    panel.textContent="";
    const caption=document.createElement("span");
    caption.textContent=message;
    if(pending)caption.className="handoff-placeholder";
    panel.append(caption);
    if(code || pending){
      const block=document.createElement("div");
      block.className=pending?"handoff-code handoff-placeholder":"handoff-code";
      const value=document.createElement("strong");
      value.textContent=code ?? "\u00a0";
      if(code)value.setAttribute("aria-label",code.split("").join(" "));
      block.append(value);
      if(code && navigator.clipboard?.writeText){
        const [copy,copied,failed]=copyLabels[sessionLocale || language] || copyLabels.en;
        const button=document.createElement("button");
        button.type="button";
        button.className="handoff-copy";
        button.title=copy;
        button.setAttribute("aria-label",copy);
        button.innerHTML='<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M9 6H7a2 2 0 0 0-2 2v11a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-2M9 4h6v4H9z"/><path class="copy-check" d="m9 14 2 2 4-4"/></svg>';
        button.onclick=async()=>{
          if(!claim || now()>=claimDeadline)return;
          try{
            await navigator.clipboard.writeText(code);
            button.classList.add("copied");
            button.title=copied;
          }catch(_){button.title=failed;}
          button.setAttribute("aria-label",button.title);
        };
        block.append(button);
      }
      panel.append(block);
    }
    if(retry){
      const button=document.createElement("button");
      button.type="button";button.className="handoff-retry";button.textContent=text.retry;
      button.onclick=()=>begin();panel.append(button);
    }
    panel.hidden=false;
  }
  function cancelWork(){
    generation++; timers.forEach(clearTimeout);timers.clear();requests.forEach(c=>c.abort());requests.clear();
    if(socket){const old=socket;socket=null;old.onclose=null;old.close();}
    renewalBusy=false;clearContent();
  }
  function terminal(message){cancelWork();claim=null;grant=null;lease=0;show(message,"",true);}
  async function post(action,body,bearer=""){
    const controller=new AbortController(), started=now();requests.add(controller);
    // Bounds the whole browser DNS/TLS/request path, distinct from HA's fixed
    // five-second send budget. Original authority deadlines never move for it.
    const timeout=setTimeout(()=>controller.abort(),15000);
    try{
      const response=await fetch("/api/djconnect/v1/display/"+action,{method:"POST",credentials:"omit",cache:"no-store",redirect:"error",
        headers:{"Content-Type":"application/json",...(bearer?{Authorization:"Bearer "+bearer}:{})},
        body:JSON.stringify({contract_version:1,...body}),signal:controller.signal});
      const bytes=await response.text();if(bytes.length>131072)throw new Error("oversized");
      const value=JSON.parse(bytes);
      if(!response.ok || value.success!==true){const failure=new Error("display_unavailable");failure.status=response.status;failure.code=value.error;throw failure;}
      return {value,started};
    }finally{clearTimeout(timeout);requests.delete(controller);}
  }
  function binding(){return {issuer_epoch:grant.issuer_epoch,display_id:grant.display_id};}
  function expired(){return !grant || now()>=lease;}
  function watchLease(g){
    later(()=>{if(g!==generation || !grant)return;if(expired())void begin();else watchLease(g);},Math.max(1,Math.min(1000,lease-now())));
  }
  async function renew(g,renewSequence){
    if(g!==generation || expired() || renewalBusy)return;
    if(navigator.onLine===false){later(()=>renew(g,renewSequence),2000);return;}
    renewalBusy=true;
    try{
      const {value,started}=await post("renew",{...binding(),renew_sequence:renewSequence},grant.grant_token);
      if(g!==generation || expired() || navigator.onLine===false)return;
      if(value.lease_revision!==renewSequence || !(value.lease_expires_in>0 && value.lease_expires_in<=60))return terminal(text.denied);
      sequence=renewSequence;lease=started+value.lease_expires_in*1000;
      later(()=>renew(g,sequence+1),20000);
    }catch(error){
      if(g!==generation)return;
      if(error.code==="display_grant_invalid" || error.code==="display_lease_expired")return begin();
      if([401,403,404,409,410].includes(error.status))return terminal(failureText(error));
      clearContent();show(text.reconnect);later(()=>renew(g,renewSequence),2000);
    }finally{if(g===generation)renewalBusy=false;}
  }
  function connect(g){
    if(g!==generation || expired() || document.hidden || navigator.onLine===false)return;
    const current=new WebSocket(location.origin.replace(/^https:/,"wss:")+"/api/djconnect/v1/display/live");socket=current;
    current.onopen=()=>{
      if(g!==generation || expired()){current.close();return;}
      current.send(JSON.stringify({type:"authenticate",contract_version:1,...binding(),grant_token:grant.grant_token,connection_nonce:nonce()}));
    };
    current.onmessage=({data})=>{
      if(g!==generation || current!==socket || expired() || document.hidden || navigator.onLine===false)return;
      try{
        if(typeof data!=="string" || data.length>131072)throw new Error("frame");
        const frame=JSON.parse(data), snapshot=frame.snapshot;
        if(frame.type!=="snapshot" || frame.contract_version!==1 || !snapshot || snapshot.issuer_epoch!==grant.issuer_epoch
            || snapshot.display_id!==grant.display_id || snapshot.share_id!==grant.share_id || snapshot.share_generation!==grant.share_generation
            || snapshot.session_id!==grant.session_id || !Number.isSafeInteger(frame.connection_generation)
            || frame.connection_generation<connectionGeneration)throw new Error("binding");
        connectionGeneration=frame.connection_generation;
        if(snapshot.session && snapshot.session.session_id===grant.session_id
            && snapshot.session.runtime_state==="active")selectLocale(snapshot.session.locale);
        // The renderer receives only the Core's explicit shared allowlist.
        window.dispatchEvent(new CustomEvent("djconnect-display-snapshot",{detail:snapshot}));
        void updateArtwork(snapshot);panel.hidden=true;
      }catch(_){terminal(text.denied);}
    };
    current.onclose=event=>{
      if(g!==generation || socket!==current)return;socket=null;
      if(expired() || event.code===1008)return begin();
      clearContent();
      show(text.reconnect);later(()=>connect(g),1500);
    };
    current.onerror=()=>{if(current===socket)current.close();};
  }
  async function collect(g){
    if(g!==generation || !claim)return;
    if(now()>=claimDeadline)return begin();
    try{
      const {value,started}=await post("collect",claim);
      if(g!==generation || !claim)return;
      if(now()>=claimDeadline)return begin();
      if(value.state==="pending"){later(()=>collect(g),1000);return;}
      if(value.state!=="admitted" || typeof value.grant_token!=="string" || !/^djcd_[A-Za-z0-9_-]{43}$/.test(value.grant_token)
          || !(value.lease_expires_in>0 && value.lease_expires_in<=60) || !value.capabilities || value.capabilities.owner_controls!==false
          || value.capabilities.session_end!==false)throw new Error("contract");
      grant=value;claim=null;lease=started+value.lease_expires_in*1000;sequence=0;connectionGeneration=0;
      if(expired())return terminal(text.expired);
      selectLocale(value.session_locale);
      show(text.reconnect);watchLease(g);connect(g);later(()=>renew(g,1),20000);
    }catch(error){
      if(g!==generation)return;
      if(now()>=claimDeadline)return begin();
      terminal(failureText(error,true));
    }
  }
  async function begin(allowCapacityRetry=true){
    stopped=false;selectLocale("");cancelWork();claim=null;grant=null;lease=0;const g=generation;
    if(location.protocol!=="https:" || location.search || location.hash || !crypto.getRandomValues)return show(text.unavailable,"",true);
    show(text.approve,null);
    try{
      const requestId=claimRequestId(), browser_nonce=nonce();
      const {value,started}=await post("claim",requestId ? {browser_nonce,request_id:requestId} : {browser_nonce});
      if(g!==generation || stopped)return;
      if(value.contract_version!==1 || !/^[0-9]{6}$/.test(value.code) || !(value.expires_in>0 && value.expires_in<=120))throw new Error("contract");
      claim={issuer_epoch:value.issuer_epoch,claim_id:value.claim_id,claim_secret:value.claim_secret,
        browser_generation:value.browser_generation,browser_nonce};claimDeadline=started+value.expires_in*1000;
      show(text.approve,value.code);
      later(()=>{if(g===generation && claim)void begin();},Math.max(0,claimDeadline-now()));
      void collect(g);
    }catch(error){
      if(g!==generation)return;
      if(allowCapacityRetry && error.code==="display_capacity"){
        later(()=>begin(false),800);
      }else show(failureText(error),"",true);
    }
  }
  function stop(){stopped=true;selectLocale("");cancelWork();claim=null;grant=null;lease=0;panel.hidden=true;panel.textContent="";}
  window.addEventListener("pagehide",stop);
  window.addEventListener("djconnect-host-stop",stop);
  window.addEventListener("offline",()=>{if(grant){clearContent();show(text.reconnect);requests.forEach(c=>c.abort());if(socket)socket.close();}});
  window.addEventListener("online",()=>{if(grant && !expired() && !socket)connect(generation);});
  window.addEventListener("pageshow",event=>{if(event.persisted && stopped)return begin();if(grant){clearContent();if(expired())void begin();else if(socket)socket.close();else connect(generation);}});
  document.addEventListener("visibilitychange",()=>{if(document.hidden){clearContent();if(socket)socket.close();}else if(grant){if(expired())void begin();else if(!socket)connect(generation);}});
  begin();
})();
