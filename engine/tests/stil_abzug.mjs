// Abzug der berechneten Stile aller Elemente auf allen Routen einer gebauten Reise (Werkzeug, kein Test).
// Für Umbauten der Stile ohne sichtbare Änderung (z. B. Regeln umordnen): vor und nach dem Umbau abziehen, dann vergleichen.
//   node stil_abzug.mjs <playwright-modul> <basis-url> <datei.json>     Abzug (390 und 1200 px, hell und dunkel)
//   node stil_abzug.mjs vergleich <vorher.json> <nachher.json>           Abweichungen je Route (erste je Route)
// Je Element: Tag, Klassen, Lage und Größe, rund 50 berechnete Eigenschaften, ::before und ::after.
import fs from "node:fs";

const [, , a1, a2, a3] = process.argv;
if (a1 === "vergleich") {
  const v = JSON.parse(fs.readFileSync(a2)), n = JSON.parse(fs.readFileSync(a3));
  let abweichend = 0;
  for (const [k, liste] of Object.entries(v)) {
    const neu = n[k];
    if (!neu) { console.log("fehlt:", k); abweichend++; continue; }
    const i = liste.findIndex((x, j) => x !== neu[j]);
    if (i < 0 && liste.length === neu.length) continue;
    abweichend++;
    console.log(k, i < 0 ? `Anzahl ${liste.length} → ${neu.length}` : `\n  vorher  ${liste[i]}\n  nachher ${neu[i]}`);
  }
  console.log(`${abweichend} von ${Object.keys(v).length} Routen weichen ab.`);
  process.exit(abweichend ? 1 : 0);
}
const pw = await import(a1);
const b = await pw[process.env.RH_BROWSER || "chromium"].launch();
const P = ["color", "background-color", "background-image", "border-top-width", "border-top-style", "border-top-color", "border-right-width",
  "border-bottom-width", "border-bottom-style", "border-bottom-color", "border-left-width", "border-left-color", "border-top-left-radius",
  "font-family", "font-size", "font-weight", "font-style", "letter-spacing", "text-transform", "line-height", "margin-top", "margin-right",
  "margin-bottom", "margin-left", "padding-top", "padding-right", "padding-bottom", "padding-left", "display", "gap", "grid-template-columns",
  "opacity", "box-shadow", "text-decoration-line", "text-decoration-color", "position", "flex-direction", "align-items", "justify-content",
  "white-space", "max-width", "min-height", "order", "outline-style", "fill", "stroke", "visibility", "overflow-x", "text-align"];
const erg = {};
for (const [breite, schema] of [[390, "light"], [1200, "light"], [390, "dark"], [1200, "dark"]]) {
  const ctx = await b.newContext({viewport: {width: breite, height: 900}, serviceWorkers: "block", colorScheme: schema});
  await ctx.route("**/api/**", r => r.abort());
  const p = await ctx.newPage();
  await p.clock.setFixedTime(new Date("2026-10-27T10:00:00"));
  await p.goto(a2);
  await p.waitForSelector("#titel:not(:empty)");
  await p.waitForTimeout(300);
  const routen = await p.evaluate(() => {
    const r = new Set(["", "plan", "varianten", "offen", "wissen", "etappen", "wuensche", "orte", "praxis", "quellen", "bausteine"]);
    for (const a of abschnitte) { r.add(a.id); for (const x of a.bloecke) r.add(x.id); }
    if (R) { R.tage.forEach(t => r.add(t.id)); Object.keys(R.weitere_tage).forEach(t => r.add(t)); Object.keys(R.unterkuenfte).forEach(u => r.add(u));
      R.wahlstellen.forEach(v => { r.add(v.id); v.optionen.forEach(o => r.add(o.id)); }); R.plaene.forEach(x => r.add(x.id)); }
    return [...r];
  });
  for (const h of routen) {
    await p.evaluate(h => { location.hash = h; window.scrollTo(0, 0); }, h);
    await p.waitForTimeout(20);
    erg[`${breite}-${schema}#${h}`] = await p.evaluate(async P => {
      document.querySelectorAll("#main details").forEach(d => { d.open = true; });   // auch Inhalte in Aufgeklapptem
      // Bilder laden lassen, sonst hängt die Höhe davon ab, ob ein Bild schon da ist
      const bilder = [...document.querySelectorAll("#main img")];
      bilder.forEach(i => { i.loading = "eager"; });
      await Promise.all(bilder.map(i => i.decode().catch(() => {})));
      return [document.body, ...document.body.querySelectorAll("*:not(svg *):not(.kartenbox *)")].map(e => {
        const c = getComputedStyle(e), r = e.getBoundingClientRect(), w = P.map(k => c.getPropertyValue(k));
        for (const ps of ["::before", "::after"]) { const q = getComputedStyle(e, ps); if (q.content !== "none") w.push(ps + q.content + q.backgroundColor + q.borderTopColor + q.color + q.width); }
        return `${e.tagName}.${typeof e.className === "string" ? e.className : ""}|${[r.x, r.y, r.width, r.height].map(Math.round)}|${w.join(";")}`;
      });
    }, P);
  }
  await ctx.close();
}
await b.close();
fs.writeFileSync(a3, JSON.stringify(erg));
console.log(`${Object.keys(erg).length} Abzüge geschrieben.`);
