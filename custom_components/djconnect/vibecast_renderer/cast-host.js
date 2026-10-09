/* CAF only supplies an ephemeral handoff; Core remains the content authority. */
(() => {
  const namespace="urn:x-cast:com.djconnect.vibecast.v1";
  const errors={en:"Cannot connect this display. Check the secure Home Assistant connection and session version.",nl:"Dit scherm kan niet verbinden. Controleer de beveiligde Home Assistant-verbinding en sessieversie.",de:"Dieses Display kann keine Verbindung herstellen. Prüfe die sichere Home-Assistant-Verbindung und Session-Version.",fr:"Connexion impossible. Vérifiez la connexion sécurisée à Home Assistant et la version de session.",es:"No se puede conectar esta pantalla. Comprueba la conexión segura a Home Assistant y la versión de sesión."};
  function stop() { window.dispatchEvent(new CustomEvent("djconnect-host-stop")); }
  function receive(message) {
    try {
      const value=typeof message.data === "string" ? JSON.parse(message.data) : message.data;
      if (!value || value.kind !== "vibecast_handoff" || value.version !== 1 || typeof value.session_id !== "string" || !value.session_id || value.session_id.length > 128 || typeof value.broadcast_token !== "string" || value.broadcast_token.length < 24 || value.broadcast_token.length > 256) throw new Error("invalid_handoff");
      const ha=new URL(value.ha_url);
      if (ha.protocol !== "https:" || ha.username || ha.password || ha.pathname !== "/" || ha.search || ha.hash) throw new Error("secure_origin_required");
      // Owner commands cannot be uplifted by a message from a sender.
      window.dispatchEvent(new CustomEvent("djconnect-handoff", {detail:{ha_url:ha.origin,session_id:value.session_id,broadcast_token:value.broadcast_token}}));
    } catch (_) {
      stop();
      document.getElementById("state").textContent=errors[document.documentElement.lang] || errors.en;
    }
  }
  // Cast adapter is loaded only by the static Cast entry. Ordinary hosts never load CAF.
  if (!window.cast || !window.cast.framework) return;
  const context=window.cast.framework.CastReceiverContext.getInstance();
  context.addCustomMessageListener(namespace,receive);
  context.start({disableIdleTimeout:false});
  window.addEventListener("beforeunload",stop);
})();
