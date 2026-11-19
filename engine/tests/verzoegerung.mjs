// Künstliche Verzögerung für Browsertests (frieda-reist#599): stellt eine stark belastete Maschine nach, ohne Last zu
// erzeugen. Wird statt des Playwright-Moduls an ein Messskript übergeben und reicht das echte Modul weiter; jede neue
// Browser-Umgebung bekommt vor dem Laden ein Skript, das die Seite verlangsamt. Nur für Tests, ändert keine Hilfsdatei.
// RH_PLAYWRIGHT_ECHT: Pfad des echten Playwright-Moduls.
// RH_VERZOEGERN: JSON mit Millisekunden, jedes Feld optional:
//   resizeobserver  Rückrufe jedes ResizeObserver kommen so viel später
//   zeitgeber       setTimeout der Seite läuft so viel später
//   resize          resize-Hörer an window und visualViewport laufen so viel später
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
  if (v.resize) {
    const anmelden = EventTarget.prototype.addEventListener;
    EventTarget.prototype.addEventListener = function (typ, hoerer, opt) {
      if (typ === "resize" && hoerer && (this === window || this === window.visualViewport)) {
        const f = typeof hoerer === "function" ? hoerer : e => hoerer.handleEvent(e);
        const ziel = this;
        return anmelden.call(this, typ, e => { spaeter(() => f.call(ziel, e), v.resize); }, opt);
      }
      return anmelden.call(this, typ, hoerer, opt);
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
