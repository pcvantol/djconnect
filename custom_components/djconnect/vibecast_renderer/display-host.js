/* B host only. One maintained renderer; no credentials in URLs or persistence. */
(()=>{
  "use strict";
  const language=(navigator.language || "en").slice(0,2);
  const words={
    en:{approve:"Enter these six digits in your paired DJConnect app. Approve this read-only screen.",waiting:"Waiting for approval",retry:"Request a new code",expired:"This screen’s access has expired. Approve it again in DJConnect.",unavailable:"Cannot reach DJConnect. Check the external HTTPS address and connection.",denied:"Screen access was withdrawn or the session ended.",reconnect:"Reconnecting…",close:"Close this screen",capacity:"Too many screens or requests. Try again shortly."},
    nl:{approve:"Voer deze zes cijfers in je gekoppelde DJConnect-app in. Geef dit scherm alleen-lezen toegang.",waiting:"Wachten op goedkeuring",retry:"Nieuwe code aanvragen",expired:"De toegang van dit scherm is verlopen. Keur het opnieuw goed in DJConnect.",unavailable:"DJConnect is niet bereikbaar. Controleer het externe HTTPS-adres en de verbinding.",denied:"De schermtoegang is ingetrokken of de sessie is beëindigd.",reconnect:"Opnieuw verbinden…",close:"Dit scherm sluiten",capacity:"Te veel schermen of verzoeken. Probeer het zo opnieuw."},
    de:{approve:"Gib diese sechs Ziffern in deiner gekoppelten DJConnect-App ein. Erlaube diesem Bildschirm nur Lesezugriff.",waiting:"Warten auf Genehmigung",retry:"Neuen Code anfordern",expired:"Der Zugriff dieses Bildschirms ist abgelaufen. Genehmige ihn erneut in DJConnect.",unavailable:"DJConnect ist nicht erreichbar. Prüfe die externe HTTPS-Adresse und die Verbindung.",denied:"Der Bildschirmzugriff wurde entzogen oder die Session beendet.",reconnect:"Verbindung wird wiederhergestellt…",close:"Diesen Bildschirm schließen",capacity:"Zu viele Bildschirme oder Anfragen. Versuche es gleich erneut."},
    fr:{approve:"Saisissez ces six chiffres dans votre app DJConnect associée. Autorisez cet écran en lecture seule.",waiting:"En attente d’autorisation",retry:"Demander un nouveau code",expired:"L’accès de cet écran a expiré. Autorisez-le à nouveau dans DJConnect.",unavailable:"DJConnect est inaccessible. Vérifiez l’adresse HTTPS externe et la connexion.",denied:"L’accès de l’écran a été retiré ou la session est terminée.",reconnect:"Reconnexion…",close:"Fermer cet écran",capacity:"Trop d’écrans ou de demandes. Réessayez dans un instant."},
    es:{approve:"Introduce estos seis dígitos en tu app DJConnect vinculada. Autoriza esta pantalla en modo de solo lectura.",waiting:"Esperando autorización",retry:"Solicitar un código nuevo",expired:"El acceso de esta pantalla ha caducado. Autorízala de nuevo en DJConnect.",unavailable:"No se puede acceder a DJConnect. Comprueba la dirección HTTPS externa y la conexión.",denied:"Se ha retirado el acceso de la pantalla o ha terminado la sesión.",reconnect:"Reconectando…",close:"Cerrar esta pantalla",capacity:"Demasiadas pantallas o solicitudes. Vuelve a intentarlo en un momento."}
  };
  const outcomes={
    en:{closed:"This screen is closed. Closing it does not end the DJ session.",newcode:"Access could not be confirmed. Request a new code and approve this screen again.",configuration:"Check the external HTTPS address in Home Assistant and reopen this screen from your paired DJConnect app."},
    nl:{closed:"Dit scherm is gesloten. De DJ-sessie wordt hierdoor niet beëindigd.",newcode:"De toegang kon niet worden bevestigd. Vraag een nieuwe code aan en keur dit scherm opnieuw goed.",configuration:"Controleer het externe HTTPS-adres in Home Assistant en open dit scherm opnieuw vanuit je gekoppelde DJConnect-app."},
    de:{closed:"Dieser Bildschirm ist geschlossen. Dadurch wird die DJ-Session nicht beendet.",newcode:"Der Zugriff konnte nicht bestätigt werden. Fordere einen neuen Code an und genehmige den Bildschirm erneut.",configuration:"Prüfe die externe HTTPS-Adresse in Home Assistant und öffne den Bildschirm erneut über deine gekoppelte DJConnect-App."},
    fr:{closed:"Cet écran est fermé. Sa fermeture ne met pas fin à la session DJ.",newcode:"L’accès n’a pas pu être confirmé. Demandez un nouveau code et autorisez à nouveau cet écran.",configuration:"Vérifiez l’adresse HTTPS externe dans Home Assistant et rouvrez cet écran depuis votre app DJConnect associée."},
    es:{closed:"Esta pantalla está cerrada. Cerrarla no termina la sesión DJ.",newcode:"No se ha podido confirmar el acceso. Solicita un código nuevo y vuelve a autorizar esta pantalla.",configuration:"Comprueba la dirección HTTPS externa en Home Assistant y vuelve a abrir esta pantalla desde tu app DJConnect vinculada."}
  };
  const text={...(words[language] || words.en),...(outcomes[language] || outcomes.en)}, panel=document.getElementById("handoff");
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
  function later(fn,delay){const timer=setTimeout(()=>{timers.delete(timer);fn();},delay);timers.add(timer);return timer;}
  function clearContent(){window.dispatchEvent(new Event("djconnect-display-clear"));}
  function show(message,code="",retry=false){
    panel.textContent=""; const caption=document.createElement("span");caption.textContent=message;panel.append(caption);
    if(code){const value=document.createElement("strong");value.textContent=code;value.setAttribute("aria-label",code.split("").join(" "));panel.append(value);}
    if(retry){const button=document.createElement("button");button.textContent=text.retry;button.onclick=begin;panel.append(button);}
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
    later(()=>{if(g!==generation || !grant)return;if(expired())terminal(text.expired);else watchLease(g);},Math.max(1,Math.min(1000,lease-now())));
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
        // The renderer receives only the Core's explicit shared allowlist.
        window.dispatchEvent(new CustomEvent("djconnect-display-snapshot",{detail:snapshot}));panel.hidden=true;
      }catch(_){terminal(text.denied);}
    };
    current.onclose=event=>{
      if(g!==generation || socket!==current)return;socket=null;clearContent();
      if(expired())return terminal(text.expired);
      if(event.code===1008)return terminal(text.denied);
      show(text.reconnect);later(()=>connect(g),1500);
    };
    current.onerror=()=>{if(current===socket)current.close();};
  }
  async function collect(g){
    if(g!==generation || !claim)return;
    if(now()>=claimDeadline)return terminal(text.expired);
    try{
      const {value,started}=await post("collect",claim);
      if(g!==generation || !claim)return;
      if(now()>=claimDeadline)return terminal(text.expired);
      if(value.state==="pending"){later(()=>collect(g),1000);return;}
      if(value.state!=="admitted" || typeof value.grant_token!=="string" || !/^djcd_[A-Za-z0-9_-]{43}$/.test(value.grant_token)
          || !(value.lease_expires_in>0 && value.lease_expires_in<=60) || !value.capabilities || value.capabilities.owner_controls!==false
          || value.capabilities.session_end!==false)throw new Error("contract");
      grant=value;claim=null;lease=started+value.lease_expires_in*1000;sequence=0;connectionGeneration=0;
      if(expired())return terminal(text.expired);
      show(text.reconnect);watchLease(g);connect(g);later(()=>renew(g,1),20000);
    }catch(error){if(g===generation)terminal(failureText(error,true));}
  }
  async function begin(){
    stopped=false;cancelWork();claim=null;grant=null;const g=generation;
    if(location.protocol!=="https:" || location.search || location.hash || !crypto.getRandomValues)return show(text.unavailable,"",true);
    show(text.waiting);
    try{
      const browser_nonce=nonce(),{value,started}=await post("claim",{browser_nonce});
      if(g!==generation || stopped)return;
      if(value.contract_version!==1 || !/^[0-9]{6}$/.test(value.code) || !(value.expires_in>0 && value.expires_in<=120))throw new Error("contract");
      claim={issuer_epoch:value.issuer_epoch,claim_id:value.claim_id,claim_secret:value.claim_secret,
        browser_generation:value.browser_generation,browser_nonce};claimDeadline=started+value.expires_in*1000;
      show(text.approve,value.code);collect(g);
    }catch(error){if(g===generation)show(failureText(error),"",true);}
  }
  function stop(){stopped=true;cancelWork();claim=null;grant=null;lease=0;panel.hidden=true;panel.textContent="";}
  const closeButton=document.createElement("button");closeButton.textContent=text.close;
  closeButton.onclick=()=>{
    const oldGrant=grant,oldClaim=claim;stop();
    if(oldGrant)post("leave",{issuer_epoch:oldGrant.issuer_epoch,display_id:oldGrant.display_id},oldGrant.grant_token).catch(()=>{});
    else if(oldClaim)post("cancel",oldClaim).catch(()=>{});
    show(text.closed,"",true);
  };
  document.querySelector("header").append(closeButton);
  window.addEventListener("beforeunload",stop);
  window.addEventListener("djconnect-host-stop",stop);
  window.addEventListener("offline",()=>{if(grant){clearContent();show(text.reconnect);requests.forEach(c=>c.abort());if(socket)socket.close();}});
  window.addEventListener("online",()=>{if(grant && !expired() && !socket)connect(generation);});
  window.addEventListener("pageshow",()=>{if(grant){clearContent();if(expired())terminal(text.expired);else if(socket)socket.close();else connect(generation);}});
  document.addEventListener("visibilitychange",()=>{if(document.hidden){clearContent();if(socket)socket.close();}else if(grant){if(expired())terminal(text.expired);else if(!socket)connect(generation);}});
  begin();
})();
