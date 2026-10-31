// Rundgang durch alle Ansichten in der Pseudo-Sprache xx (ADR-0006), aufgerufen von test_seite_sprachen.py.
// Aufruf: node sprachen_rundgang.mjs <playwright-modul> <basis-url> <sprache>
// Prüft für jede Ansicht zweierlei:
//  1. umgeschaltet: Wer auf Deutsch startet und auf <sprache> umschaltet, sieht dieselbe Ansicht wie jemand, der in <sprache>
//     startet (sonst blieb ein Text vom Start stehen, etwa eine Konstante, die beim Umschalten nicht neu entsteht);
//  2. ohne Marke: Sichtbare Texte und Beschriftungen, die nicht aus den Daten der Reise stammen, tragen die Marke der Pseudo-Sprache;
//     was ohne Marke bleibt, ist fest im Code (ein vergessener Text).
const [, , modul, basis, sprache] = process.argv;
const pw = await import(modul);
const b = await pw[process.env.RH_BROWSER || "chromium"].launch();
const neu = async (vorher) => {
  const ctx = await b.newContext({viewport: {width: 1200, height: 900}, serviceWorkers: "block"});
  await ctx.route("**/api/**", r => r.abort());
  if (vorher) await ctx.addInitScript(vorher);
  const p = await ctx.newPage();
  await p.clock.setFixedTime(new Date("2026-10-27T10:00:00"));
  const fehler = [];
  p.on("pageerror", e => fehler.push(String(e)));
  await p.goto(basis);
  await p.waitForSelector("#titel:not(:empty)");
  await p.waitForTimeout(300);
  return {p, fehler};
};
const A = await neu();
await A.p.evaluate(sprache => localStorage.setItem(SP + "sprache", JSON.stringify(sprache)), sprache);
await A.p.reload();
await A.p.waitForSelector("#titel:not(:empty)");
await A.p.waitForTimeout(300);
const B = await neu();
await B.p.click(`#sprachen button[data-sprache="${sprache}"]`);
await B.p.waitForTimeout(300);
const routen = await A.p.evaluate(() => {
  const r = new Set(["", "plan", "varianten", "offen", "wissen", "etappen", "wuensche", "orte", "praxis", "quellen", "fragen", "aufgaben", "rueckmeldungen"]);
  for (const a of abschnitte) { r.add(a.id); for (const x of a.bloecke) r.add(x.id); }
  if (R) {
    R.tage.forEach(t => r.add(t.id)); Object.keys(R.weitere_tage).forEach(t => r.add(t)); Object.keys(R.unterkuenfte).forEach(u => r.add(u));
    R.wahlstellen.forEach(v => { r.add(v.id); v.optionen.forEach(o => r.add(o.id)); }); R.plaene.forEach(x => r.add(x.id));
    Object.keys(R.buchungen || {}).forEach(b => r.add(b));
  }
  D.fragen.zeilen.forEach(z => r.add(z.id));
  return [...r];
});
const ansicht = () => document.querySelector("#main").cloneNode(true) && (() => {
  const c = document.querySelector("#main").cloneNode(true);
  c.querySelectorAll(".regionen").forEach(x => x.querySelectorAll("[aria-pressed]").forEach(k => k.removeAttribute("aria-pressed")));
  c.querySelectorAll(".kartenbox").forEach(x => x.replaceWith(Object.assign(document.createElement("div"), {className: "kartenbox"})));
  c.querySelectorAll(".blitz").forEach(x => x.classList.remove("blitz"));
  const rahmen = ["#nav", "header", ".leiste", "#neu", "#offline"].map(s => (document.querySelector(s) || {}).outerHTML || "").join("");
  return c.outerHTML + rahmen;
})();
const ohneMarke = (marke) => {
  const daten = JSON.stringify(D).toLowerCase();
  // Wörter der deutschen Oberfläche: ein Text, der als Ganzes oder in einem Stück so im Katalog steht, ist ein vergessener Text
  const deWerte = new Set(Object.values(TEXTE.de.texte).map(v => v.trim()).filter(v => v.length > 1));
  const aus = new Set();
  const sichtbar = e => !!(e.offsetWidth || e.offsetHeight || e.getClientRects().length);
  const pruefen = (text) => {
    const t = text.replace(/\s+/g, " ").trim();
    if (!t || !/[A-Za-zÄÖÜäöüß]{2,}/.test(t) || t.includes(marke)) return;
    const stuecke = t.split(/ · |: |, |; | \(|\)/).map(x => x.trim()).filter(Boolean);
    const katalogWort = stuecke.some(x => deWerte.has(x));
    const woerter = t.match(/[A-Za-zÄÖÜäöüß]{2,}/g) || [];
    const ausDaten = woerter.every(w => daten.includes(w.toLowerCase()));
    const exakt = daten.includes(JSON.stringify(t.toLowerCase())) || daten.includes(JSON.stringify(t).toLowerCase());   // der Text steht als ganzer Wert in den Daten
    if (!exakt && ((katalogWort && woerter.length <= 3) || !ausDaten) && t !== "Google Maps ↗" && t !== "Apple Karten ↗") aus.add(t);
  };
  for (const w of document.querySelectorAll("#main, header, .leiste, #neu, #offline")) {
    const walker = document.createTreeWalker(w, NodeFilter.SHOW_TEXT);
    for (let n = walker.nextNode(); n; n = walker.nextNode()) {
      const e = n.parentElement;
      if (!e || e.closest("#sprachen") || e.closest("script, style, svg, .kartenbox, .leaflet-container") || !sichtbar(e)) continue;
      pruefen(n.nodeValue);
    }
    for (const e of w.querySelectorAll("[title], [aria-label], [placeholder]")) {
      if (e.closest(".kartenbox, .leaflet-container")) continue;
      for (const a of ["title", "aria-label", "placeholder"]) if (e.hasAttribute(a)) pruefen(e.getAttribute(a));
    }
  }
  return [...aus];
};
const stale = {}, marke = {};
for (const h of routen) {
  for (const x of [A, B]) { await x.p.evaluate(h => { location.hash = h; }, h); }
  await A.p.waitForTimeout(12);
  const [a, bb] = [await A.p.evaluate(ansicht), await B.p.evaluate(ansicht)];
  if (a !== bb) {
    let i = 0;
    while (i < a.length && a[i] === bb[i]) i++;
    stale[h] = [a.slice(Math.max(0, i - 60), i + 80), bb.slice(Math.max(0, i - 60), i + 80)];
  }
  const m = await A.p.evaluate(ohneMarke, `[${sprache} `);
  if (m.length) marke[h] = m;
}
await b.close();
console.log(JSON.stringify({routen: routen.length, stale, marke, fehler: [...A.fehler, ...B.fehler]}));
