// DOM-Vergleich: node dump.mjs <basis-url> <ausgabe.json> (Playwright: Paket „playwright“ oder PLAYWRIGHT=<Pfad zu index.mjs>); rendert jede Route bei 390 und 1200 px
import fs from "node:fs";
const pw = await import(process.env.PLAYWRIGHT || "playwright");
const [, , basis, aus] = process.argv;
const b = await pw.chromium.launch();
const erg = {}, fehler = [];
for (const w of [390, 1200]) {
  const ctx = await b.newContext({viewport: {width: w, height: 900}, serviceWorkers: "block"});
  await ctx.route("**/api/**", r => r.abort());
  const p = await ctx.newPage();
  await p.clock.setFixedTime(new Date("2026-10-27T10:00:00"));
  p.on("pageerror", e => fehler.push(w + " " + String(e)));
  await p.goto(basis);
  await p.waitForSelector("#titel:not(:empty)");
  await p.waitForTimeout(300);
  const routen = await p.evaluate(() => {
    const r = new Set(["", "plan", "varianten", "offen", "wissen", "etappen", "wuensche", "orte", "praxis", "quellen", "fragen", "aufgaben", "rueckmeldungen"]);
    for (const a of abschnitte) { r.add(a.id); for (const x of a.bloecke) r.add(x.id); }
    if (R) { R.tage.forEach(t => r.add(t.id)); Object.keys(R.weitere_tage).forEach(t => r.add(t)); Object.keys(R.unterkuenfte).forEach(u => r.add(u));
      R.wahlstellen.forEach(v => { r.add(v.id); v.optionen.forEach(o => r.add(o.id)); }); R.plaene.forEach(x => r.add(x.id)); }
    D.fragen.zeilen.forEach(z => r.add(z.id));
    return [...r];
  });
  for (const h of routen) {
    await p.evaluate(h => { location.hash = h; }, h);
    await p.waitForTimeout(15);
    erg[w + "#" + h] = await p.evaluate(() => { const c = document.querySelector("#main").cloneNode(true);
      c.querySelectorAll(".kartenbox, .regionen").forEach(x => x.replaceChildren());
      c.querySelectorAll("*").forEach(x => { x.classList.remove("blitz"); if (x.closest && x.parentElement && x.parentElement.classList.contains("regionen")) x.removeAttribute("aria-pressed"); });
      c.querySelectorAll(".kartenbox").forEach(x => x.replaceWith(Object.assign(document.createElement("div"), {className: "kartenbox"})));
      return c.outerHTML; });
  }
  await ctx.close();
}
await b.close();
fs.writeFileSync(aus, JSON.stringify(erg));
console.log(Object.keys(erg).length, "Routen", fehler.length ? fehler.slice(0, 5) : "ohne Fehler");
