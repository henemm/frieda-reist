// Signal „Live-Daten geladen“ (#568), aufgerufen von test_wartepunkt_geladen.py.
// Aufruf: node seiten_geladen.mjs <playwright-modul> <basis-url> <anker>
// Bricht api/** ab (alle Lader scheitern), zählt jedes replaceChildren() an #main und hält fest, wie viele davon nach dem Signal
// html[data-geladen] kamen; bleibt .ekarte nach dem Signal dasselbe Element?
const [, , modul, basis, anker] = process.argv;
const pw = await import(modul);
const b = await pw[process.env.RH_BROWSER || "chromium"].launch();
const fehler = [];
const ctx = await b.newContext({viewport: {width: 390, height: 900}, serviceWorkers: "block"});
await ctx.route("**/api/**", r => r.abort());
await ctx.addInitScript(() => {
  window.__aufbau = {gesamt: 0, nachSignal: 0};
  const orig = Element.prototype.replaceChildren;
  Element.prototype.replaceChildren = function (...a) {
    if (this.id === "main") {
      window.__aufbau.gesamt++;
      if (document.documentElement.hasAttribute("data-geladen")) window.__aufbau.nachSignal++;
    }
    return orig.apply(this, a);
  };
});
const p = await ctx.newPage();
p.on("pageerror", e => fehler.push(String(e)));
await p.goto(basis + (anker ? "#" + anker : ""));
let geladen = true;
await p.waitForSelector("html[data-geladen]", {state: "attached", timeout: 15000}).catch(() => { geladen = false; });
const hatKarte = geladen && await p.evaluate(() => { const k = document.querySelector(".ekarte"); if (k) k.__sonde = 1; return !!k; });
await p.waitForTimeout(1500);   // Zeit für ein (unerwünschtes) weiteres Neuzeichnen
const aus = await p.evaluate(() => ({...window.__aufbau, signal: document.documentElement.dataset.geladen || null,
  karteGleich: (() => { const k = document.querySelector(".ekarte"); return k ? k.__sonde === 1 : null; })()}));
aus.geladen = geladen;
aus.hatKarte = hatKarte;
await ctx.close();
await b.close();
console.log(JSON.stringify({fehler, aus}));
