// Bildschirmbilder der Reiseseite für die Infoseite (#436), aufgerufen von engine/info/erzeugen.py.
// Aufruf: node aufnehmen.mjs <playwright-modul> <basis-url> <ausgabe-ordner> <bilder-json>
// bilder-json: [{name, reise, hash, ziel?}], je Bild eine Seite der gebauten Beispielreise (<basis-url>/<reise>/#<hash>), mit ziel
// (CSS-Selektor) an diese Stelle gerollt. Handy-Ansicht
// 390 × 700 CSS-Pixel, doppelte Dichte, als PNG; Netz der Karte und api/… sind gesperrt, die Uhr steht fest (nichts hängt vom Tag
// der Aufnahme ab). Meldet als JSON je Bild den Text der Ansicht (#main) und alle Skriptfehler.
const [, , modul, basis, aus, bilderJson] = process.argv;
const pw = await import(modul);
const b = await pw.chromium.launch();
const ctx = await b.newContext({viewport: {width: 390, height: 700}, deviceScaleFactor: 2, serviceWorkers: "block"});
await ctx.route("**/api/**", r => r.abort());
await ctx.route(u => !u.href.startsWith(basis), r => r.abort());
const p = await ctx.newPage();
const fehler = [], texte = {};
p.on("pageerror", e => fehler.push(String(e)));
await p.clock.setFixedTime(new Date("2026-11-09T10:00:00"));
for (const bild of JSON.parse(bilderJson)) {
  await p.goto(`${basis}/${bild.reise}/${bild.hash ? "#" + bild.hash : ""}`);
  await p.waitForSelector("#titel:not(:empty)");
  await p.waitForTimeout(800);
  if (bild.ziel) {   // eine Stelle ohne eigenes Sprungziel (etwa die Karte des Tags): an den oberen Rand rollen
    await p.$eval(bild.ziel, e => { e.scrollIntoView({block: "start"}); window.scrollBy(0, -16); });
    await p.waitForTimeout(500);
  }
  texte[bild.name] = await p.$eval("#main", m => m.innerText);
  await p.screenshot({path: `${aus}/${bild.name}.png`});
}
await b.close();
console.log(JSON.stringify({fehler, texte}));
