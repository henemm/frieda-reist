// Aufenthalte ohne Nacht als Möglichkeiten einer Wahlstelle (#353), aufgerufen von test_option_aufenthalte.py.
// Aufruf: node seiten_option_aufenthalt.mjs <playwright-modul> <basis-url>
// Meldet den Text der Wahlstelle V-90 am Tag 3 (mit geöffnetem Vergleich), die Zeilen der Zeitleiste und Fehler der Seite.
const [, , modul, basis] = process.argv;
const pw = await import(modul);
const b = await pw[process.env.RH_BROWSER || "chromium"].launch();
const ctx = await b.newContext({viewport: {width: 1280, height: 900}, serviceWorkers: "block"});
await ctx.route("**/api/**", r => r.abort());
const p = await ctx.newPage();
const fehler = [];
p.on("pageerror", e => fehler.push(String(e)));
await p.goto(basis + "#T-03");
await p.waitForSelector(".tagseite");
const knopf = p.locator('[data-ziel="V-90"] button, [data-ziel="V-90"] summary').first();
if (await knopf.count()) await knopf.click().catch(() => {});
// Die Wahlstelle samt ihrem Vergleich (Tabelle oder Karten stehen in .wm, auch wenn sie nicht im Kasten der Wahlstelle liegen)
const wahl = await p.evaluate(() => { const k = document.querySelector('[data-ziel="V-90"]'); if (!k) return null;
  const teile = [k, ...document.querySelectorAll(".tagseite .wm")];
  return teile.map(x => x.textContent.replace(/\s+/g, " ").trim()).join(" || "); });
const verlauf = await p.evaluate(() => [...document.querySelectorAll(".tagseite .wv > div")].map(x => x.textContent.replace(/\s+/g, " ").trim().slice(0, 120)));
await b.close();
console.log(JSON.stringify({wahl, verlauf, fehler}));
