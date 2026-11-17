// Kacheln in „Meine Reisen“ (#455, P3), aufgerufen von test_bilder_konto.py.
// Aufruf: node seiten_konto_kacheln.mjs <playwright-modul> <konto.html> <json {bildpfad: datei}>
// Die gebaute Kontoseite wird unter einer erfundenen Adresse ausgeliefert, die Bilder aus den Dateien der gebauten Seiten,
// alles andere abgelehnt. Meldet je Breite (360, 760, 1300): Zahl der Kacheln in der Liste, Spalten (verschiedene linke
// Kanten), Überbreite der Seite, Seitenverhältnis der Bildflächen, und Skriptfehler.
import {readFileSync} from "node:fs";
const [, , modul, html, bilderJson] = process.argv;
const pw = await import(modul);
const bilder = JSON.parse(bilderJson);
const b = await pw[process.env.RH_BROWSER || "chromium"].launch();
const fehler = [], aus = {breiten: {}};
for (const breite of [360, 760, 1300]) {
  const ctx = await b.newContext({viewport: {width: breite, height: 900}, serviceWorkers: "block"});
  await ctx.route("**/*", r => {
    const pfad = new URL(r.request().url()).pathname;
    if (pfad === "/konto") return r.fulfill({status: 200, contentType: "text/html; charset=utf-8", body: readFileSync(html)});
    if (bilder[pfad]) return r.fulfill({status: 200, contentType: pfad.endsWith(".png") ? "image/png" : "image/webp", body: readFileSync(bilder[pfad])});
    return r.abort();
  });
  const p = await ctx.newPage();
  p.on("pageerror", e => fehler.push(String(e)));
  await p.goto("http://frieda.beispiel.invalid/konto");
  await p.waitForTimeout(300);
  aus.breiten[breite] = await p.evaluate(() => {
    const k = [...document.querySelectorAll(".liste .kachel")].filter(e => !e.closest(".archiv"));
    const links = new Set(k.map(e => Math.round(e.getBoundingClientRect().left)));
    const flaechen = k.map(e => e.querySelector(".bild, .flaeche")).filter(Boolean);
    return {kacheln: k.length, spalten: links.size,
            ueberbreite: document.documentElement.scrollWidth > innerWidth,
            verhaeltnis: flaechen.map(f => { const r = f.getBoundingClientRect(); return r.height ? r.width / r.height : 0; })};
  });
  await ctx.close();
}
aus.fehler = fehler;
await b.close();
console.log(JSON.stringify(aus));
