(()=>{
  if (new URLSearchParams(window.location.search).has("session_id") || typeof window.fetch !== "function") return;
  const panel = document.getElementById("handoff");
  const labels = {
    en: "Enter this code in your paired DJConnect app to show this Session",
    nl: "Voer deze code in je gekoppelde DJConnect-app in om de sessie te tonen",
    de: "Gib diesen Code in deiner gekoppelten DJConnect-App ein, um die Session anzuzeigen",
    fr: "Saisissez ce code dans votre app DJConnect associée pour afficher la session",
    es: "Introduce este código en tu app DJConnect vinculada para mostrar la sesión"
  };
  const language = (navigator.language || "en").slice(0, 2);
  const label = labels[language] || labels.en;
  let stopped = false, generation=0, timer;
  function stop() { stopped=true; generation++; panel.hidden=true; panel.textContent=""; if (timer && window.clearTimeout) window.clearTimeout(timer); timer=undefined; }
  function later(callback,delay) { if (!stopped) timer=window.setTimeout(callback,delay); }
  window.addEventListener("beforeunload",stop);
  window.addEventListener("djconnect-host-stop",stop);
  async function post(path, payload) {
    const response = await window.fetch(path, {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload), cache: "no-store", credentials: "omit"
    });
    if (!response.ok) {
      const error = new Error("handoff_unavailable");
      error.status = response.status;
      throw error;
    }
    return response.json();
  }
  async function begin() {
    if (stopped) return;
    const active=generation;
    try {
      const claim = await post("/api/djconnect/v1/session/broadcast/handoff/claim", {});
      if (stopped || active !== generation) return;
      panel.innerHTML = "";
      const caption = document.createElement("span");
      caption.textContent = label;
      const code = document.createElement("strong");
      code.textContent = claim.code;
      panel.append(caption, code);
      panel.hidden = false;
      poll(claim);
    } catch (_) { if (!stopped) later(begin, 5000); }
  }
  async function poll(claim) {
    if (stopped) return;
    const active=generation;
    try {
      const result = await post("/api/djconnect/v1/session/broadcast/handoff/collect", {
        claim_id: claim.claim_id, claim_secret: claim.claim_secret
      });
      if (stopped || active !== generation) return;
      if (result.state === "approved" && result.session_id && result.broadcast_token) {
        panel.hidden = true;
        window.dispatchEvent(new CustomEvent("djconnect-handoff", {detail: result}));
        return;
      }
      later(() => poll(claim), 1000);
    } catch (error) {
      if (!stopped) later(() => {
        if (error.status === 404) begin();
        else poll(claim);
      }, 1000);
    }
  }
  begin();
})()