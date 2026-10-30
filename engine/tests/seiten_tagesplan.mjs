// Tagesseite und Ortsseite bei gewähltem Plan (frieda-reist#144), aufgerufen von test_tagesplan.py.
// Aufruf: node seiten_tagesplan.mjs <playwright-modul> <basis-url>
// Ruft jede Tagesseite des aktuellen Plans direkt auf (frische Seite, kein zuletzt angesehener Plan) und meldet Kopf,
// erwartete Nummer und Datum aus der Übersicht (R.tage), die Blätterlinks und die Ortsseite.
const [, , modul, basis] = process.argv;
const pw = await import(modul);
const b = await pw[process.env.RH_BROWSER || "chromium"].launch();
const fehler = [], tage = [];
const ctx = await b.newContext({viewport: {width: 1300, height: 900}, serviceWorkers: "block"});
await ctx.route("**/api/**", r => r.abort());
const neu = async () => {
  const p = await ctx.newPage();
  p.on("pageerror", e => fehler.push(String(e)));
  return p;
};
let p = await neu();
await p.goto(basis);
await p.waitForSelector("#main *");
const ids = await p.evaluate(() => R.tage.map(t => t.id));
await p.close();
for (const id of ids) {
  p = await neu();
  await p.goto(basis + "#" + id);
  await p.waitForSelector(".tagseite");
  tage.push(await p.evaluate(id => {
    const t = R.tage.find(x => x.id === id);
    return {id, erwartet: `Tag ${t.nr} · ${datumText(t.datum, t.wochentag)}`,
      kopf: (document.querySelector("#main .tagdatum") || {}).textContent || "",
      blaettern: [...document.querySelectorAll(".tagseite .blaettern a")].map(a => [a.getAttribute("href"), a.textContent])};
  }, id));
  await p.close();
}
// Ortsseite: Wo kommt der Ort vor, wohin führt der Zurück-Link
p = await neu();
await p.goto(basis + "#O-01");
await p.waitForSelector("#main h2");
const ort = await p.evaluate(() => ({
  chips: [...document.querySelectorAll("#main .chips .chip")].map(x => x.textContent),
  zurueck: (document.querySelector("#main .zurueck") || {}).getAttribute("href"),
}));
await p.close();
await b.close();
console.log(JSON.stringify({fehler, tage, ort}));
