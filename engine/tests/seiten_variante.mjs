// Seite einer abgewandelten Beispielreise prüfen (Verhalten je Status und Bausteine, Paket B), aufgerufen von test_seite.py.
// Aufruf: node seiten_variante.mjs <playwright-modul> <basis-url> <datum JJJJ-MM-TT>
// Meldet: Reiter der Leiste, aktiver Reiter beim Start, Überschrift des Heute-Blocks, Zahl der Rückmeldeknöpfe an IDs,
// Skriptfehler.
const [, , modul, basis, datum] = process.argv;
const pw = await import(modul);
const b = await pw[process.env.RH_BROWSER || "chromium"].launch();
const ctx = await b.newContext({viewport: {width: 390, height: 900}, serviceWorkers: "block"});
await ctx.route("**/api/**", r => r.abort());
const p = await ctx.newPage();
const fehler = [];
p.on("pageerror", e => fehler.push(String(e)));
await p.clock.setFixedTime(new Date(`${datum}T10:00:00`));
await p.goto(basis);
await p.waitForSelector("#titel:not(:empty)");
await p.waitForTimeout(300);
const start = await p.evaluate(() => ({
  reiter: [...document.querySelectorAll("#nav a")].map(a => a.getAttribute("href").slice(1)),
  aktiv: (document.querySelector("#nav a.on") || {getAttribute: () => "#"}).getAttribute("href").slice(1),
  heute: (document.querySelector("section.heute h2") || {}).textContent || null,
}));
// Rückmeldeknöpfe an IDs im Plan (ohne Baustein „rueckmeldungen“ und „aufgaben“ nur Text)
await p.evaluate(() => { location.hash = "plan"; });
await p.waitForTimeout(200);
start.knoepfe = await p.evaluate(() => document.querySelectorAll("#main button.zid").length);
start.kennungen = await p.evaluate(() => document.querySelectorAll("#main .zid").length);
await b.close();
console.log(JSON.stringify({...start, fehler}));
