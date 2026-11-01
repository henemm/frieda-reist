// Wertet JavaScript-Ausdrücke in einer gebauten Seite aus (Tests, ADR-0006).
// Aufruf: node ausdruecke_browser.mjs <playwright-modul> <url> <json-liste-von-ausdruecken>
const [, , modul, url, liste] = process.argv;
const pw = await import(modul);
const b = await pw[process.env.RH_BROWSER || "chromium"].launch();
const ctx = await b.newContext({viewport: {width: 1200, height: 900}, serviceWorkers: "block"});
await ctx.route("**/api/**", r => r.abort());
const p = await ctx.newPage();
const fehler = [];
p.on("pageerror", e => fehler.push(String(e)));
await p.goto(url);
await p.waitForSelector("#titel:not(:empty)");
await p.waitForTimeout(300);
const werte = [];
for (const ausdruck of JSON.parse(liste)) werte.push(await p.evaluate(a => (0, eval)(a), ausdruck));
await b.close();
console.log(JSON.stringify({fehler, werte}));
