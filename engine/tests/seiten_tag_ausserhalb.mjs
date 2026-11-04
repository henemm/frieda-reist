// Tag außerhalb der Zeitachse und Heimat einer Wahlstelle über an: (frieda-reist#247), aufgerufen von test_tag_ausserhalb_247.py.
// Aufruf: node seiten_tag_ausserhalb.mjs <playwright-modul> <basis-url> <tag> <wahlstelle>
// Meldet für den Tag die Blätterlinks (Text, Ziel) und für jedes Ziel die Nummer im Kopf seiner Tagesseite; für die Wahlstelle,
// auf welcher Tagesseite ihr Aufruf landet und ob sie dort steht.
const [, , modul, basis, tag, wahl, plan] = process.argv;
const pw = await import(modul);
const b = await pw[process.env.RH_BROWSER || "chromium"].launch();
const ctx = await b.newContext({viewport: {width: 1300, height: 900}, serviceWorkers: "block"});
await ctx.route("**/api/**", r => r.abort());
const p = await ctx.newPage();
const fehler = [];
p.on("pageerror", e => fehler.push(String(e)));
const gehe = async h => { await p.goto("about:blank"); await p.goto(basis + "#" + h); await p.waitForSelector("#titel:not(:empty)"); await p.waitForTimeout(300); };
if (plan) await gehe(plan);   // zuletzt geöffneter Plan: in ihm zählt der Tag außerhalb der Zeitachse
await p.evaluate(h => { location.hash = h; }, tag);
await p.waitForTimeout(300);
const links = await p.evaluate(() => [...document.querySelectorAll("#main .blaettern a")].map(a => ({text: a.textContent.trim(), ziel: a.getAttribute("href").slice(1)})));
for (const l of links) { await gehe(l.ziel); l.kopf = await p.evaluate(() => (document.querySelector("#main h2.tagkopf") || {}).textContent || ""); }
await gehe(wahl);
const heimat = await p.evaluate(w => ({tagseite: !!document.querySelector(".tagseite"), tag: (document.querySelector("#main h2.tagkopf") || {}).id || null,
  da: !!document.getElementById(w)}), wahl);
await b.close();
console.log(JSON.stringify({fehler, links, heimat}));
