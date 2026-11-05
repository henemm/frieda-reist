// Reihenfolge der Zeitleiste eines Tags prüfen (#287), aufgerufen von test_seite.py.
// Aufruf: node seiten_wegverlauf.mjs <playwright-modul> <basis-url> <datum>
// Meldet die Zeilen der Zeitleiste von Tag 2 in der Reihenfolge der Seite: [Art der Zeile, Text].
const [, , modul, basis] = process.argv;
const pw = await import(modul);
const b = await pw[process.env.RH_BROWSER || "chromium"].launch();
const ctx = await b.newContext({viewport: {width: 390, height: 900}, serviceWorkers: "block"});
await ctx.route("**/api/**", r => r.abort());
const p = await ctx.newPage();
const fehler = [];
p.on("pageerror", e => fehler.push(String(e)));
await p.goto(basis + "#T-02");
await p.waitForSelector(".tagseite .wv");
const verlauf = await p.evaluate(() => [...document.querySelectorAll(".tagseite .wv > div")].map(x => [x.className.replace(/\s+/g, " ").trim(), x.textContent.replace(/\s+/g, " ").trim().slice(0, 160)]));
await b.close();
console.log(JSON.stringify({verlauf, fehler}));
