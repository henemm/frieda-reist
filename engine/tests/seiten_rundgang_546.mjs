// Zwei sichtbare Änderungen aus dem Rundgang vom 12.11.2026 (frieda-reist#546), aufgerufen von test_rundgang_546.py.
// Aufruf: node seiten_rundgang_546.mjs <playwright-modul> <basis-url> <etappe mit Kartenpunkten, die an keinem Tag des Plans steht>
// tage: je Tagesseite am Rechner (1300 px, Maus) die Lage von Tageskasten, rechter Spalte und einer Wahl oder Nacht über die volle
// Breite; punkte: die Zeilen „Punkte am Weg“ auf der Seite der Etappe am Handy und ob ein Link auf einen Punkt bei seiner Zeile landet.
const [, , modul, basis, etappe] = process.argv;
const pw = await import(modul);
const b = await pw[process.env.RH_BROWSER || "chromium"].launch();
const fehler = [];
const seite = async breite => {
  const ctx = await b.newContext({viewport: {width: breite, height: 900}, serviceWorkers: "block"});
  await ctx.route("**/api/**", r => r.abort());
  const p = await ctx.newPage();
  await p.clock.setFixedTime(new Date("2026-10-27T10:00:00"));
  p.on("pageerror", e => fehler.push(String(e)));
  await p.goto(basis);
  await p.waitForSelector("#titel:not(:empty)");
  await p.waitForTimeout(300);
  return p;
};
const gehe = async (p, h) => { await p.evaluate(h => { location.hash = h; }, h); await p.waitForTimeout(150); };
let p = await seite(1300);
const tage = [];
for (const t of await p.evaluate(() => R ? [...R.tage.map(t => t.id), ...Object.keys(R.weitere_tage)] : [])) {
  await gehe(p, t);
  tage.push(await p.evaluate(t => {
    const r = s => { const e = document.querySelector(".tagseite > " + s); if (!e) return null; const q = e.getBoundingClientRect();
      return q.width ? {l: Math.round(q.left), o: Math.round(q.top + scrollY), r: Math.round(q.right), u: Math.round(q.bottom + scrollY)} : null; };
    return {tag: t, karte: document.querySelectorAll(".tag-oben > *").length > 1, oben: r(".tag-oben"), spalte: r(".tag-spalte"), voll: r(".nacht-voll, .wahl-voll"),
      breite: Math.round(document.querySelector(".tagseite").getBoundingClientRect().width)};
  }, t));
}
await p.context().close();
let punkte = null;
if (etappe) {
  p = await seite(390);
  await gehe(p, etappe);
  punkte = await p.evaluate(() => ({titel: [...document.querySelectorAll(".am-element h3")].map(h => h.textContent),
    zeilen: [...document.querySelectorAll(".am-element a.wzeile[data-punkt]")].map(a => ({id: a.id, name: a.querySelector(".wt").textContent, unter: (a.querySelector(".wu") || {}).textContent || ""})),
    karten: document.querySelectorAll(".am-element .karte").length}));
  if (punkte.zeilen.length) {
    const ziel = punkte.zeilen[punkte.zeilen.length - 1].id;
    await gehe(p, ziel);
    punkte.sprung = await p.evaluate(z => { const e = document.getElementById(z), q = e && e.getBoundingClientRect(); return !!q && q.top >= 0 && q.bottom <= innerHeight && e.classList.contains("blitz"); }, ziel);
  }
  await p.context().close();
}
await b.close();
console.log(JSON.stringify({fehler, tage, punkte}));
