/* Skript von „Mein Konto“ (Issue #21, Entscheidung A vom 2.11.2026). Ohne Skript bleibt die Seite voll benutzbar; es
 * ergänzt nur, was ohne Skript nicht geht:
 *  1. Frieda-App: meldet den Worker /sw.js an (nur Push, kein Offline-Speicher, engine/app/sw.js).
 *  2. Benachrichtigungen je Gerät (Baustein pushSchalter, docs/design.md): Zustand dieses Geräts, Ein- und Ausschalten.
 *     iPhone und iPad bekommen Push nur in der App vom Home-Bildschirm; im Browser zeigt die Karte die Schritte dahin.
 *     Die Frage des Systems kommt nur auf Tippen (iOS lehnt sie sonst ab), requestPermission steht deshalb zuerst.
 *  3. Speichern mit Zustand (Baustein speichernKnopf): Formulare mit data-aenderung lassen den Knopf aus, bis sich ein Feld
 *     geändert hat; Formulare für Handlungen (alle aus, neuer Link, abmelden, löschen) bleiben, wie sie sind.
 * Texte kommen vom Server aus dem Katalog (data-texte), nie aus diesem Skript (ADR-0006). Kein Inline-Skript (CSP).
 */
(function () {
  "use strict";

  // ---------- Speichern mit Zustand ----------
  function stand(form) {
    const teile = [];
    for (const [k, v] of new FormData(form)) teile.push(k + "=" + v);
    return teile.join("&");
  }
  function speichernBeobachten(form) {
    const knopf = form.querySelector("button:not([type=button])");
    if (!knopf) return;
    const anfang = stand(form);      // Stand, wie der Server ihn geliefert hat
    const pruefen = () => { knopf.disabled = stand(form) === anfang; };
    form.addEventListener("input", pruefen);
    form.addEventListener("change", pruefen);
    // Zurück-Taste (bfcache): Der Browser stellt geänderte Felder wieder her, der Knopf muss das wissen
    window.addEventListener("pageshow", e => { if (e.persisted) pruefen(); });
    pruefen();
  }
  document.querySelectorAll("form[data-aenderung]").forEach(speichernBeobachten);

  // ---------- Frieda-App und Benachrichtigungen ----------
  const ort = document.getElementById("push-geraet");
  const SW_DA = "serviceWorker" in navigator;
  if (SW_DA) navigator.serviceWorker.register("/sw.js", {scope: "/"}).catch(() => {});
  if (!ort) return;

  let T = {};
  try { T = JSON.parse(ort.dataset.texte || "{}"); } catch (e) { T = {}; }
  const t = k => T[k] || "";
  const SCHLUESSEL = ort.dataset.schluessel || "";
  const PUSH_DA = SW_DA && "PushManager" in window && "Notification" in window;
  const APPLE_MOBIL = /iPhone|iPad|iPod/.test(navigator.userAgent) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  const ALS_APP = navigator.standalone === true || !!(window.matchMedia && matchMedia("(display-mode: standalone)").matches);

  function el(tag, attr, ...kinder) {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(attr || {})) e.setAttribute(k, v);
    for (const k of kinder) e.append(k);
    return e;
  }
  function zeigen(...kinder) { ort.replaceChildren(...kinder); ort.hidden = !kinder.length; }
  function satz(text, klasse) { return el("p", klasse ? {class: klasse} : {}, text); }

  function geraetKennung() {
    try {
      let g = localStorage.getItem("rh-geraet");
      if (!g) {
        g = Array.from(crypto.getRandomValues(new Uint8Array(12)), b => b.toString(16).padStart(2, "0")).join("");
        localStorage.setItem("rh-geraet", g);
      }
      return g;
    } catch (e) { return ""; }
  }
  function schluesselBytes(b64) {
    const roh = atob(b64.replace(/-/g, "+").replace(/_/g, "/") + "=".repeat((4 - b64.length % 4) % 4));
    return Uint8Array.from(roh, c => c.charCodeAt(0));
  }
  function zeitzone() { try { return Intl.DateTimeFormat().resolvedOptions().timeZone || ""; } catch (e) { return ""; } }

  // Gleiche Herkunft, Formular wie die übrigen Handlungen von „Mein Konto“ (Origin-Prüfung, Sitzung im Cookie)
  async function senden(felder) {
    const r = await fetch("/konto", {method: "POST", credentials: "same-origin",
      headers: {"Content-Type": "application/x-www-form-urlencoded"}, body: new URLSearchParams(felder)});
    if (!r.ok) throw new Error(String(r.status));
  }
  const fertig = was => { location.replace("/konto?push=" + was + "#push"); };

  async function abo() {
    const reg = await navigator.serviceWorker.getRegistration("/");
    return reg ? reg.pushManager.getSubscription() : null;
  }

  async function einschalten() {
    try {
      const erlaubt = await Notification.requestPermission();
      if (erlaubt !== "granted") return darstellen(erlaubt === "denied" ? "" : t("nicht_erlaubt"));
      await navigator.serviceWorker.register("/sw.js", {scope: "/"});
      const reg = await navigator.serviceWorker.ready;
      const a = await reg.pushManager.getSubscription()
        || await reg.pushManager.subscribe({userVisibleOnly: true, applicationServerKey: schluesselBytes(SCHLUESSEL)});
      await senden({aktion: "push_an", abo: JSON.stringify(a.toJSON()), geraet: geraetKennung(), zeitzone: zeitzone()});
      fertig("an");
    } catch (e) { darstellen(t("fehler")); }
  }

  async function ausschalten() {
    try {
      const a = await abo();
      if (a) {
        await senden({aktion: "push_ab", endpoint: a.endpoint});
        await a.unsubscribe();
      }
      fertig("aus");
    } catch (e) { darstellen(t("fehler")); }
  }

  async function darstellen(meldung) {
    const status = meldung ? [satz(meldung, "fehler")] : [];
    if (!PUSH_DA) {
      if (APPLE_MOBIL && !ALS_APP) {
        return zeigen(el("p", {}, el("strong", {}, t("installieren"))),
          el("ol", {class: "schritte"}, el("li", {}, t("schritt1")), el("li", {}, t("schritt2")), el("li", {}, t("schritt3"))));
      }
      return zeigen(satz(t("kein_browser"), "klein"));
    }
    if (!SCHLUESSEL) return zeigen();
    if (Notification.permission === "denied") return zeigen(satz(t("blockiert"), "fehler"));
    const a = Notification.permission === "granted" ? await abo().catch(() => null) : null;
    if (a) {
      // Beim Öffnen meldet sich ein eingeschaltetes Gerät still neu (Zeitzone für die Ruhezeit, erneuertes Abo)
      senden({aktion: "push_an", abo: JSON.stringify(a.toJSON()), geraet: geraetKennung(), zeitzone: zeitzone()}).catch(() => {});
      const aus = el("button", {type: "button", class: "neutral"}, t("ausschalten"));
      aus.addEventListener("click", ausschalten);
      return zeigen(...status, el("p", {class: "aktiv"}, t("an")), aus);
    }
    const an = el("button", {type: "button"}, t("einschalten"));
    an.addEventListener("click", einschalten);
    zeigen(...status, an);
  }

  darstellen("");
})();
