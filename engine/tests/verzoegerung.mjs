// Künstliche Verzögerung für Browsertests (frieda-reist#599): stellt eine stark belastete Maschine nach, ohne Last zu
// erzeugen. Wird statt des Playwright-Moduls an ein Messskript übergeben und reicht das echte Modul weiter; jede neue
// Browser-Umgebung bekommt vor dem Laden ein Skript, das die Seite verlangsamt. Nur für Tests, ändert keine Hilfsdatei.
// RH_PLAYWRIGHT_ECHT: Pfad des echten Playwright-Moduls.
// RH_VERZOEGERN: JSON mit Millisekunden, jedes Feld optional:
//   resizeobserver  Rückrufe jedes ResizeObserver kommen so viel später
//   zeitgeber       setTimeout der Seite läuft so viel später
//   resize          resize-Hörer an window und visualViewport laufen so viel später
//   hashchange      hashchange-Hörer an window laufen so viel später (#661)
//   hash            hashchange nur beim Wechsel auf diesen Hash verzögern (ohne #)
//   ab              CSS-Selektor: ResizeObserver erst verzögern, die nach einem Klick auf ein solches Element entstehen
const echt = await import(process.env.RH_PLAYWRIGHT_ECHT);
const v = JSON.parse(process.env.RH_VERZOEGERN || "{}");

function verlangsamen(v) {
  const spaeter = window.setTimeout.bind(window);
  if (v.resizeobserver != null && window.ResizeObserver) {
    const Echt = window.ResizeObserver;
    let scharf = !v.ab;
    if (v.ab) document.addEventListener("click", e => { if (e.target.closest && e.target.closest(v.ab)) scharf = true; }, true);
    window.ResizeObserver = class extends Echt {
      constructor(rueckruf) { super(scharf ? (e, o) => spaeter(() => rueckruf(e, o), v.resizeobserver) : rueckruf); }
    };
  }
  if (v.zeitgeber) window.setTimeout = (f, t, ...a) => spaeter(f, (Number(t) || 0) + v.zeitgeber, ...a);
  if (v.resize || v.hashchange) {
    const anmelden = EventTarget.prototype.addEventListener;
    const trifft = e => v.hash == null || decodeURIComponent(new URL(e.newURL).hash.slice(1)) === v.hash;
    EventTarget.prototype.addEventListener = function (typ, hoerer, opt) {
      let warten = null;
      if (v.resize && typ === "resize" && (this === window || this === window.visualViewport)) warten = () => v.resize;
      if (v.hashchange && typ === "hashchange" && this === window) warten = e => (trifft(e) ? v.hashchange : 0);
      if (!warten || !hoerer) return anmelden.call(this, typ, hoerer, opt);
      const f = typeof hoerer === "function" ? hoerer : e => hoerer.handleEvent(e);
      const ziel = this;
      return anmelden.call(this, typ, e => { const ms = warten(e); if (ms) spaeter(() => f.call(ziel, e), ms); else f.call(ziel, e); }, opt);
    };
  }
}

function browserart(art) {
  return {
    async launch(opt) {
      const b = await art.launch(opt);
      const neu = b.newContext.bind(b);
      b.newContext = async o => {
        const ctx = await neu(o);
        await ctx.addInitScript(verlangsamen, v);
        return ctx;
      };
      return b;
    },
  };
}

export const chromium = browserart(echt.chromium);
export const webkit = browserart(echt.webkit);
