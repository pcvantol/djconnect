(()=>{
  if (new URLSearchParams(window.location.search).has("session_id") || typeof window.fetch !== "function") return;
  const panel = document.getElementById("handoff");
  const labels = {
  "en": {
    "title": "Show your DJ session here",
    "steps": [
      "Start a DJ session in DJConnect on your iPhone, iPad or Mac.",
      "Choose the VibeCast icon in the DJ-session toolbar.",
      "Enter the code below in the app."
    ],
    "code": "Your code"
  },
  "nl": {
    "title": "Toon je DJ-sessie op dit scherm",
    "steps": [
      "Start een DJ-sessie in DJConnect op je iPhone, iPad of Mac.",
      "Kies het VibeCast-icoon bovenin de DJ-sessie.",
      "Vul de onderstaande code in de app in."
    ],
    "code": "Jouw code"
  },
  "de": {
    "title": "Zeige deine DJ-Session hier",
    "steps": [
      "Starte eine DJ-Session in DJConnect auf deinem iPhone, iPad oder Mac.",
      "Wähle das VibeCast-Symbol in der Symbolleiste der DJ-Session.",
      "Gib den unten stehenden Code in der App ein."
    ],
    "code": "Dein Code"
  },
  "fr": {
    "title": "Affichez votre session DJ ici",
    "steps": [
      "Démarrez une session DJ dans DJConnect sur votre iPhone, iPad ou Mac.",
      "Choisissez l’icône VibeCast dans la barre d’outils de la session DJ.",
      "Saisissez le code ci-dessous dans l’app."
    ],
    "code": "Votre code"
  },
  "es": {
    "title": "Muestra tu sesión de DJ aquí",
    "steps": [
      "Inicia una sesión de DJ en DJConnect en tu iPhone, iPad o Mac.",
      "Elige el icono de VibeCast en la barra de la sesión de DJ.",
      "Introduce el código de abajo en la app."
    ],
    "code": "Tu código"
  }
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
      const caption = document.createElement("h2");
      caption.textContent = label.title;
      const steps = document.createElement("ol");
      label.steps.forEach((value, index) => {
        const step = document.createElement("li");
        if (index === 1) {
          const icon = document.createElement("span");
          icon.className = "handoff-icon";
          icon.setAttribute("aria-hidden", "true");
          icon.innerHTML = '<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 23H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h22a2 2 0 0 1 2 2v9M11 28h9M15 23v5M20 19a11 11 0 0 1 10 10M20 24a6 6 0 0 1 5 5"/><circle cx="20" cy="29" r="1" fill="currentColor" stroke="none"/></svg>';
          step.append(icon);
        }
        const text = document.createElement("span");
        text.textContent = value;
        step.append(text);
        steps.append(step);
      });
      const codeLabel = document.createElement("span");
      codeLabel.className = "code-label";
      codeLabel.textContent = label.code;
      const code = document.createElement("strong");
      code.textContent = claim.code;
      panel.append(caption, steps, codeLabel, code);
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