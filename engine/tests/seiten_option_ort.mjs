// Orte als Möglichkeiten einer Wahlstelle (#353, Schritt 2), aufgerufen von test_option_orte.py.
// Aufruf: node seiten_option_ort.mjs <playwright-modul> <basis-url>
// Meldet den Text der Wahlstelle V-91 am Tag 3 (mit geöffnetem Vergleich), die Links in den Möglichkeiten (optionBlock) und in den
// aufgeklappten Einzelheiten des Vergleichs (optionEinzelheiten) sowie Fehler der Seite.
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
const knopf = p.locator('[data-ziel="V-91"] button, [data-ziel="V-91"] summary').first();
if (await knopf.count()) await knopf.click().catch(() => {});
const wahl = await p.evaluate(() => { const k = document.querySelector('[data-ziel="V-91"]'); if (!k) return null;
  const teile = [k, ...document.querySelectorAll(".tagseite .wm")];
  return teile.map(x => x.textContent.replace(/\s+/g, " ").trim()).join(" || "); });
// Links in den Möglichkeiten (optionBlock: .option mit der ID der Möglichkeit), auf der Tagesseite und auf der Seite der Wahlstelle
const linksIn = sel => p.evaluate(s => [...document.querySelectorAll(s)].map(a => a.getAttribute("href")).filter(Boolean), sel);
let links_block = await linksIn('[id^="V-91."] a[href^="#O-"], [data-ziel^="V-91."] a[href^="#O-"]');
if (!links_block.length) {
  await p.goto(basis + "#V-91");
  await p.waitForTimeout(300);
  links_block = await linksIn('[id^="V-91."] a[href^="#O-"], [data-ziel^="V-91."] a[href^="#O-"], .option a[href^="#O-"]');
}
// Einzelheiten im Vergleich: jede Zeile aufklappen, dann die Links in .wm-einzelheiten
await p.goto(basis + "#T-03");
await p.waitForSelector(".tagseite");
for (const z of await p.locator(".tagseite .wm tr, .tagseite .wm .wm-zeile").all()) await z.click({timeout: 500}).catch(() => {});
let links_einzelheiten = await linksIn(".wm-einzelheiten a[href^='#O-']");
if (!links_einzelheiten.length) {
  await p.goto(basis + "#V-91");
  await p.waitForTimeout(300);
  for (const z of await p.locator(".wm tr, .wm .wm-zeile").all()) await z.click({timeout: 500}).catch(() => {});
  links_einzelheiten = await linksIn(".wm-einzelheiten a[href^='#O-']");
}
await b.close();
console.log(JSON.stringify({wahl, links_block, links_einzelheiten, fehler}));
