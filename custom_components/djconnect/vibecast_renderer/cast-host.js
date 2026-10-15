/* CAF supplies temporary authority and directed status; Core owns content. */
(() => {
  const namespace="urn:x-cast:com.djconnect.vibecast.v1";
  const errors={en:"Cannot connect this display. Check the secure Home Assistant connection and session version.",nl:"Dit scherm kan niet verbinden. Controleer de beveiligde Home Assistant-verbinding en sessieversie.",de:"Dieses Display kann keine Verbindung herstellen. Prüfe die sichere Home-Assistant-Verbindung und Session-Version.",fr:"Connexion impossible. Vérifiez la connexion sécurisée à Home Assistant et la version de session.",es:"No se puede conectar esta pantalla. Comprueba la conexión segura a Home Assistant y la versión de sesión."};
  if (!window.cast || !window.cast.framework) return;
  const context=window.cast.framework.CastReceiverContext.getInstance();
  const system=window.cast.framework.system;
  let active=null, generation=0, deadline, heartbeat, listening=false;
  const retired=new Set();
  function cancelTimers() {
    if (deadline) window.clearTimeout(deadline); deadline=null;
    if (heartbeat) window.clearTimeout(heartbeat); heartbeat=null;
  }
  function status(state,reason,presentation) {
    if (!active || !active.status || !context.isSystemReady()) return;
    if (state===active.last && presentation===active.presentation && state!=="presenting") return;
    active.last=state; active.presentation=presentation;
    const data={kind:"vibecast_status",version:1,handoff_id:active.id,session_id:active.session,sequence:++active.sequence,state,lease_ms:15000};
    if (reason) data.reason=reason;
    if (presentation) data.presentation=presentation;
    try { context.sendCustomMessage(namespace,active.sender,data); } catch (_) { /* Sender must expire missing status, never assume success. */ }
  }
  function stop(state,reason) {
    status(state || "stopped",reason);
    cancelTimers();
    if (active && active.id) { retired.add(active.id); if (retired.size>32) retired.delete(retired.values().next().value); }
    active=null;
    window.dispatchEvent(new CustomEvent("djconnect-host-stop"));
  }
  function awaitSnapshot() {
    if (!active || !active.status) return;
    if (deadline) window.clearTimeout(deadline);
    const current=active;
    deadline=window.setTimeout(()=>{deadline=null;if(active===current)stop("error","snapshot_timeout");},15000);
  }
  function keepAlive() {
    if (!active || !active.status) return;
    if (heartbeat) window.clearTimeout(heartbeat);
    const current=active;
    heartbeat=window.setTimeout(()=>{heartbeat=null;if(active!==current || !active || active.last!=="presenting")return;status("presenting",null,active.presentation);keepAlive();},5000);
  }
  function receive(message) {
    try {
      const value=typeof message.data === "string" ? JSON.parse(message.data) : message.data;
      if (value && value.kind==="vibecast_stop") {
        if (active && active.status && value.version===1 && message.senderId===active.sender && value.handoff_id===active.id && value.session_id===active.session) stop("stopped","host_stop");
        return;
      }
      if (!value || value.kind !== "vibecast_handoff" || value.version !== 1 || typeof value.session_id !== "string" || !value.session_id || value.session_id.length > 128 || typeof value.broadcast_token !== "string" || value.broadcast_token.length < 24 || value.broadcast_token.length > 256) throw new Error("invalid_handoff");
      const ha=new URL(value.ha_url);
      if (ha.protocol !== "https:" || ha.username || ha.password || ha.pathname !== "/" || ha.search || ha.hash) throw new Error("invalid_handoff");
      const wantsStatus=value.status_version!==undefined || value.handoff_id!==undefined;
      if (wantsStatus && (value.status_version!==1 || typeof value.handoff_id!=="string" || !/^[a-f0-9]{32}$/.test(value.handoff_id) || typeof message.senderId!=="string" || !message.senderId || message.senderId.length>128)) throw new Error("invalid_handoff");
      if (wantsStatus && (retired.has(value.handoff_id) || (active && active.id===value.handoff_id))) return;
      if (active) stop("stopped","superseded");
      active={sender:message.senderId,session:value.session_id,id:value.handoff_id,status:wantsStatus,generation:++generation,sequence:0};
      status("receiver_ready"); awaitSnapshot();
      // No sender end-grant or other owner authority crosses this boundary.
      window.dispatchEvent(new CustomEvent("djconnect-handoff", {detail:{ha_url:ha.origin,session_id:value.session_id,broadcast_token:value.broadcast_token,status_generation:generation}}));
    } catch (_) {
      // An unrelated sender's malformed message cannot tear down the active view.
      if (active && message.senderId!==active.sender) return;
      stop("error","invalid_handoff");
      document.getElementById("state").textContent=errors[document.documentElement.lang] || errors.en;
    }
  }
  window.addEventListener("djconnect-renderer-status",({detail})=>{
    if (!active || !detail || detail.generation!==active.generation || detail.session_id!==active.session) return;
    if (detail.state==="connecting" || detail.state==="recovering") {
      if (heartbeat) window.clearTimeout(heartbeat); heartbeat=null;
      status(detail.state); if (!deadline) awaitSnapshot();
    } else if (detail.state==="snapshot_accepted") status("snapshot_accepted");
    else if (detail.state==="presenting") {
      if (deadline) window.clearTimeout(deadline); deadline=null;
      const presentation=detail.presentation==="moment" ? "moment" : "silence";
      if (active.last!=="presenting" || active.presentation!==presentation) status("presenting",null,presentation);
      // Rendering frequent updates must not indefinitely postpone the lease heartbeat.
      if (!heartbeat) keepAlive();
    } else if (detail.state==="error" || detail.state==="ended" || detail.state==="stopped") stop(detail.state,detail.reason);
  });
  function ready() {
    if (listening || !context.isSystemReady()) return;
    context.addCustomMessageListener(namespace,receive); listening=true;
  }
  context.addEventListener(system.EventType.READY,ready);
  context.addEventListener(system.EventType.SENDER_DISCONNECTED,event=>{if(active && event.senderId===active.sender)stop("stopped","sender_disconnected");});
  const namespaces={}; namespaces[namespace]=system.MessageType.JSON;
  context.start({disableIdleTimeout:false,customNamespaces:namespaces});
  ready();
  window.addEventListener("beforeunload",()=>stop("stopped","host_stop"));
})();
