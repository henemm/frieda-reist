// Buchungen mit Zeitraum (#463), aufgerufen von test_buchung_zeitraum.py.
// Aufruf: node seiten_buchung_zeitraum.mjs <playwright-modul> <basis-url>
const [, , modul, basis] = process.argv;
const pw = await import(modul);
const b = await pw[process.env.RH_BROWSER || "chromium"].launch();
const fehler = [], tage = {};
const ctx = await b.newContext({viewport: {width: 1300, height: 900}, serviceWorkers: "block"});
await ctx.route("**/api/**", r => r.abort());
const neu = async () => { const p = await ctx.newPage(); p.on("pageerror", e => fehler.push(String(e))); return p; };
for (const tag of ["T-01", "T-07"]) {
  const p = await neu();
  await p.goto(basis + "#" + tag);
  await p.waitForSelector(".tagseite");
  tage[tag] = await p.evaluate(() => {
    const s = document.querySelector("#main #nacht"), k = s && s.querySelector('.karte[data-ziel="U-01"]');
    const bl = k ? k.querySelector(".buchung") : null;
    const oben = bl ? [...bl.children].filter(x => x.tagName !== "DETAILS").map(x => x.textContent).join(" | ") : "";
    const lage = k && k.querySelector(".lage");
    return {karte: !!k, buchungen: s ? [...s.querySelectorAll(".buchung")].filter(x => !x.closest("details.weg")).map(x => x.id) : [], oben,
      marken: bl ? [...bl.querySelectorAll(".titelzeile .chip")].map(x => x.textContent) : [],
      einzelheiten_zu: !!(bl && bl.querySelector("details.einzelheiten") && !bl.querySelector("details.einzelheiten").open),
      herkunft_adresse: !!(lage && lage.textContent.includes("ⓘ"))};
  });
  await p.close();
}
const p = await neu();
await p.goto(basis + "#B-04");
await p.waitForSelector(".tagseite");
const ziel_b04 = await p.evaluate(() => ({block: !!document.querySelector("#main #nacht #B-04"),
  kopf: (document.querySelector("#main .tagdatum") || {}).textContent || ""}));
await p.goto(basis + "#reise");
await p.waitForTimeout(500);
const zeilen = await p.evaluate(() => Object.fromEntries([...document.querySelectorAll("a.tagzeile")].map(z =>
  [z.dataset.tag, ((z.querySelector(".tz-nacht .chip") || {}).textContent || "")])));
await p.close();
await b.close();
console.log(JSON.stringify({fehler, tage, ziel_b04, zeilen}));
