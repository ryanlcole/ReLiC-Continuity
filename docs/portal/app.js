"use strict";

/*
 * ReLiC IS browser portal: local demonstration only.
 * No third-party calls, credential enrollment, microphone/camera capture,
 * browser permission prompts on entry, or authoritative ReLiC history writes.
 * Rion binary is an ordinary JS representation adapter, NOT RuneCore runtime.
 */
(() => {
  const $ = (id) => document.getElementById(id);
  const STORAGE_KEY = "relic-is-bios-preferences-v1";
  const canStore = () => {
    try {
      const k = "__relic_storage_test__";
      localStorage.setItem(k, "1");
      localStorage.removeItem(k);
      return true;
    } catch (_) { return false; }
  };
  const featureDefs = [
    ["audio", "Audio output", () => "Audio" in window || "AudioContext" in window],
    ["microphone", "Microphone", () => !!navigator.mediaDevices?.getUserMedia, "microphone"],
    ["video", "Video playback", () => !!document.createElement("video").canPlayType],
    ["camera", "Camera capture", () => !!navigator.mediaDevices?.getUserMedia, "camera"],
    ["parallax", "Motion / parallax", () => "DeviceOrientationEvent" in window],
    ["popups", "Pop-up windows", () => typeof window.open === "function"],
    ["cookies", "Site cookies", () => navigator.cookieEnabled === true],
    ["localStorage", "Local storage APIs", () => canStore()],
    ["notifications", "Notifications", () => "Notification" in window, "notifications"],
    ["location", "Geolocation", () => "geolocation" in navigator, "geolocation"],
    ["clipboard", "Clipboard access", () => !!navigator.clipboard],
    ["fullscreen", "Fullscreen request", () => !!(document.documentElement.requestFullscreen || document.documentElement.webkitRequestFullscreen)],
    ["bluetooth", "Bluetooth", () => "bluetooth" in navigator],
    ["usb", "USB devices", () => "usb" in navigator],
    ["serial", "Serial devices", () => "serial" in navigator],
    ["midi", "MIDI devices", () => !!navigator.requestMIDIAccess],
    ["vibration", "Vibration", () => !!navigator.vibrate],
    ["wakeLock", "Screen wake lock", () => "wakeLock" in navigator],
    ["webgl", "WebGL graphics", () => "WebGLRenderingContext" in window],
    ["wasm", "WebAssembly", () => "WebAssembly" in window],
    ["offline", "Service workers", () => "serviceWorker" in navigator],
    ["share", "Native share sheet", () => !!navigator.share],
    ["speech", "Speech recognition", () => !!(window.SpeechRecognition || window.webkitSpeechRecognition)]
  ];
  const defaults = () => Object.fromEntries(featureDefs.map((f) => [f[0], false]));
  function load() {
    try {
      const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
      const state = defaults();
      for (const key of Object.keys(state)) state[key] = parsed[key] === true;
      return state;
    } catch (_) { return defaults(); }
  }
  let saved = load();
  let choices = { ...saved };
  const supported = Object.fromEntries(featureDefs.map(([id, , test]) => {
    try { return [id, !!test()]; } catch (_) { return [id, false]; }
  }));
  const permissionStates = {};
  function notice(message) { $("feedback").textContent = message; }
  function makeFact(key, value) {
    const box = document.createElement("div");
    box.className = "fact";
    const dt = document.createElement("dt");
    dt.textContent = key;
    const dd = document.createElement("dd");
    dd.textContent = String(value);
    box.append(dt, dd);
    return box;
  }
  function knownFacts() {
    const tz = (() => { try { return Intl.DateTimeFormat().resolvedOptions().timeZone || "unknown"; } catch (_) { return "unknown"; } })();
    const facts = [
      ["Secure context", window.isSecureContext ? "yes" : "no"],
      ["Page origin", location.protocol === "file:" ? "local file" : location.origin],
      ["Viewport", innerWidth + " × " + innerHeight],
      ["Screen", screen.width + " × " + screen.height],
      ["Pixel ratio", devicePixelRatio || "unknown"],
      ["Language", navigator.language || "unknown"],
      ["Time zone", tz],
      ["Logical CPU hint", navigator.hardwareConcurrency || "unknown"],
      ["Device RAM hint", navigator.deviceMemory ? navigator.deviceMemory + " GB (rounded)" : "unknown"],
      ["Touch points", Number.isInteger(navigator.maxTouchPoints) ? navigator.maxTouchPoints : "unknown"],
      ["OS identity", "not verified by browser"],
      ["Browser session", document.visibilityState || "unknown"]
    ];
    $("known").replaceChildren(...facts.map(([k, v]) => makeFact(k, v)));
  }
  function renderCapabilities() {
    const nodes = featureDefs.map(([id, label]) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "cap";
      btn.setAttribute("role", "switch");
      btn.setAttribute("aria-label", "Permit future site use of " + label);
      const enabled = supported[id] && choices[id];
      btn.setAttribute("aria-checked", String(!!enabled));
      btn.disabled = !supported[id];
      const textWrap = document.createElement("span");
      const title = document.createElement("span");
      title.className = "cap-title";
      title.textContent = label;
      const state = document.createElement("span");
      state.className = "cap-state";
      if (!supported[id]) state.textContent = "Unavailable in this browser";
      else if (permissionStates[id] === "denied") state.textContent = "Browser denied · " + (enabled ? "selected" : "off");
      else if (permissionStates[id] === "granted") state.textContent = "Browser permission granted · " + (enabled ? "selected" : "off");
      else state.textContent = enabled ? "Selected · request later" : "Off · available";
      textWrap.append(title, state);
      const pill = document.createElement("span");
      pill.className = "pill";
      pill.setAttribute("aria-hidden", "true");
      pill.append(document.createElement("i"));
      btn.append(textWrap, pill);
      btn.addEventListener("click", () => {
        choices[id] = !choices[id];
        renderCapabilities();
        notice("Unsaved choice. No OS permission has been changed.");
      });
      return btn;
    });
    $("capabilities").replaceChildren(...nodes);
  }
  async function refreshPermissionHints() {
    if (!navigator.permissions?.query) return;
    const names = featureDefs.filter((f) => f[3] && supported[f[0]]);
    await Promise.all(names.map(async ([id, , , permission]) => {
      try { permissionStates[id] = (await navigator.permissions.query({ name: permission })).state; }
      catch (_) { permissionStates[id] = "unknown"; }
    }));
    renderCapabilities();
  }
  let fpsText = "unknown";
  function sampleFrames() {
    if (!window.requestAnimationFrame) return;
    let frames = 0, start = 0;
    function tick(t) {
      if (!start) start = t;
      frames++;
      if (t - start < 700) return requestAnimationFrame(tick);
      const fps = (frames - 1) * 1000 / Math.max(1, t - start);
      fpsText = fps >= 1 && fps <= 300 ? "~" + fps.toFixed(0) + " fps" : "unknown";
      renderMetrics();
    }
    requestAnimationFrame(tick);
  }
  let probe = "not run";
  function renderMetrics() {
    const net = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
    const nav = performance?.getEntriesByType?.("navigation")?.[0];
    const info = [
      ["Online hint", navigator.onLine ? "online" : "offline"],
      ["Network type", net?.effectiveType || "unknown"],
      ["Downlink estimate", net?.downlink ? net.downlink + " Mbps" : "unknown"],
      ["RTT estimate", Number.isFinite(net?.rtt) ? net.rtt + " ms" : "unknown"],
      ["Data saver", net?.saveData === undefined ? "unknown" : (net.saveData ? "on" : "off")],
      ["Page load", Number.isFinite(nav?.duration) ? Math.round(nav.duration) + " ms" : "unknown"],
      ["Frame sample", fpsText],
      ["Same-origin probe", probe],
      ["HTTPS / context", isSecureContext ? "secure" : "not secure"]
    ];
    const nodes = info.map(([title, value]) => {
      const card = document.createElement("div");
      card.className = "metric";
      const v = document.createElement("div");
      v.className = "value";
      v.textContent = value;
      const n = document.createElement("div");
      n.className = "name";
      n.textContent = title;
      card.append(v, n);
      return card;
    });
    $("metrics").replaceChildren(...nodes);
  }
  async function runProbe() {
    const button = $("probe");
    if (location.protocol === "file:") {
      $("probe-note").textContent = "A local file has no HTTP origin to measure.";
      return;
    }
    button.disabled = true;
    const ms = [];
    for (let i = 0; i < 3; i++) {
      try {
        const start = performance.now();
        const r = await fetch(location.origin + location.pathname, { method: "HEAD", cache: "no-store", credentials: "omit", mode: "same-origin" });
        if (r.ok) ms.push(Math.round(performance.now() - start));
      } catch (_) { /* Unknown, not stable. */ }
    }
    probe = ms.length + "/3";
    $("probe-note").textContent = ms.length
      ? "This page's origin answered " + ms.length + "/3 samples. Mean request duration: " + Math.round(ms.reduce((a, b) => a + b, 0) / ms.length) + " ms. This does not measure internet-wide stability."
      : "All three same-origin requests failed. Cause unknown.";
    renderMetrics();
    button.disabled = false;
  }
  function saveChoices() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(choices));
      saved = { ...choices };
      notice("Saved browser preferences on this device. No account or identity data stored.");
      return true;
    } catch (_) {
      saved = { ...choices };
      notice("Local storage unavailable. Choices are retained only while this page stays open.");
      return false;
    }
  }
  function fullscreen() {
    const root = document.documentElement;
    const request = root.requestFullscreen || root.webkitRequestFullscreen;
    if (!request) { notice("Fullscreen API unavailable here. On desktop use F11; on iPhone use Safari's available display options."); return; }
    try {
      const result = request.call(root);
      if (result?.catch) result.catch(() => notice("Browser blocked fullscreen. Try F11 on desktop or browser display controls."));
    } catch (_) { notice("Browser blocked fullscreen."); }
  }
  const encoder = new TextEncoder();
  let transitionId = null;
  function hideAll() { ["bios", "decode", "presence"].forEach((id) => $(id).classList.add("hidden")); }
  function enterDecode() {
    hideAll();
    $("decode").classList.remove("hidden");
    const lanes = featureDefs.map(([id]) => ({
      key: id,
      known: supported[id] ? 1 : 0,
      sign: 0,
      selected: supported[id] && choices[id] ? 1 : 0
    }));
    const packet = { protocol: "RION-DEMO-v1", source: "browser-observation", verified: false, lanes };
    const rions = window.ReLiCRionAdapter;
    const stateBits = rions ? rions.pack(lanes) : "UNKNOWN — Rion adapter unavailable";
    const byteArray = encoder.encode(JSON.stringify(packet));
    const bits = Array.from(byteArray.slice(0, 88), (n) => n.toString(2).padStart(8, "0")).join(" ");
    $("bits").textContent = "RION LANES [KNOWN SIGN VALUE]\n" + stateBits +
      "\n\nUTF-8 TRANSPORT BYTES [PROVENANCE + LANES]\n" + bits +
      (byteArray.length > 88 ? "\n… " + byteArray.length + " bytes total" : "");
    transitionId = setTimeout(enterPresence, matchMedia("(prefers-reduced-motion: reduce)").matches ? 250 : 2200);
  }
  function enterPresence() {
    if (transitionId) clearTimeout(transitionId);
    transitionId = null;
    hideAll();
    $("presence").classList.remove("hidden");
    $("say").focus({ preventScroll: true });
    if (!$("messages").childElementCount) {
      post("system", "Welcome. I am a local ReLiC interface demonstrator, not yet a connected service.");
      post("system", "Presence enrollment begins with your consent. I can gather an alias and a device label in temporary session memory; neither proves identity. Type BEGIN to proceed or CANCEL to return to BIOS.");
    }
  }
  const profile = { alias: null, device: null, factor: null };
  let phase = 0;
  function post(kind, message) {
    const div = document.createElement("div");
    div.className = "message " + kind;
    div.textContent = message;
    $("messages").append(div);
    $("messages").scrollTop = $("messages").scrollHeight;
  }
  function resetProfile() {
    profile.alias = profile.device = profile.factor = null;
    phase = 0;
    $("auth-state").textContent = "PRESENCE · UNVERIFIED";
    $("messages").replaceChildren();
  }
  function goBack() {
    resetProfile();
    hideAll();
    $("bios").classList.remove("hidden");
    knownFacts();
    renderMetrics();
  }
  function handleMessage(raw) {
    const text = raw.trim();
    if (!text) return;
    post("user", text);
    const lower = text.toLowerCase();
    if (lower === "cancel" || lower === "exit") { goBack(); notice("Presence draft discarded from session memory."); return; }
    if (phase === 0) {
      if (lower !== "begin") { post("system", "No details gathered. Type BEGIN to consent, or CANCEL."); return; }
      phase = 1;
      post("system", "What display alias should I use for this session? Please do not enter your legal name, password or sensitive identity information.");
      return;
    }
    if (phase === 1) {
      if (text.length > 60) { post("system", "Please use 60 characters or fewer."); return; }
      profile.alias = text;
      phase = 2;
      post("system", "What friendly label would you give this device? For example, Phone or Desktop. Do not use a serial number.");
      return;
    }
    if (phase === 2) {
      if (text.length > 60) { post("system", "Please use 60 characters or fewer."); return; }
      profile.device = text;
      phase = 3;
      post("system", "Which future presence factor do you prefer: PASSKEY, SECURITY KEY, or MANUAL APPROVAL? This is a preference, not authentication.");
      return;
    }
    if (phase === 3) {
      if (!["passkey", "security key", "manual approval"].includes(lower)) {
        post("system", "Please enter PASSKEY, SECURITY KEY, or MANUAL APPROVAL.");
        return;
      }
      profile.factor = lower;
      phase = 4;
      $("auth-state").textContent = "DRAFT ONLY · NOT VERIFIED";
      post("system", "Session draft created: alias “" + profile.alias + "”, device “" + profile.device + "”, preferred factor “" + profile.factor + "”. Nothing was sent or saved. No person, device or job role has been verified.");
      post("system", "A trusted local verifier, challenge/response protocol, access policy and audit trail must be built before enrollment. Type STATUS or INFRASTRUCTURE.");
      return;
    }
    if (lower === "status") {
      post("system", "Browser shell: local only. Presence: unverified session draft. RuneCore: not connected. ReLiC ledger: not connected. Existing M1 localhost pilot: separate and unchanged.");
    } else if (lower === "infrastructure") {
      post("system", "Next approved engineering path: local verifier → consented passkey/security-key challenge → authenticated principal and role policy → auditable access to local-first tasks. No construction or authorization happened from this text command.");
    } else if (lower === "help") {
      post("system", "Recognized commands: STATUS, INFRASTRUCTURE, CANCEL. Unknown commands execute nothing.");
    } else {
      post("system", "Unknown command. No action executed. Type HELP.");
    }
  }
  $("talk").addEventListener("submit", (e) => {
    e.preventDefault();
    const value = $("say").value;
    $("say").value = "";
    handleMessage(value);
    $("say").focus();
  });
  $("fullscreen").addEventListener("click", fullscreen);
  $("save").addEventListener("click", saveChoices);
  $("continue").addEventListener("click", () => { saveChoices(); enterDecode(); });
  $("cancel").addEventListener("click", () => {
    choices = { ...saved };
    renderCapabilities();
    notice("Unsaved selections canceled; last saved choices restored.");
  });
  $("exit").addEventListener("click", () => {
    resetProfile();
    notice("Session draft cleared. You may close this browser tab; websites generally cannot close tabs they did not open.");
    window.close();
  });
  $("skip").addEventListener("click", enterPresence);
  $("return").addEventListener("click", goBack);
  $("probe").addEventListener("click", runProbe);
  addEventListener("resize", knownFacts);
  addEventListener("online", renderMetrics);
  addEventListener("offline", renderMetrics);
  document.addEventListener("visibilitychange", () => { knownFacts(); renderMetrics(); });
  const network = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
  network?.addEventListener?.("change", renderMetrics);
  knownFacts();
  renderCapabilities();
  renderMetrics();
  refreshPermissionHints();
  sampleFrames();
})();
