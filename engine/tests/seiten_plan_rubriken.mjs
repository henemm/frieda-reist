// Leere Rubriken „Tagesplan“ und „Unterkünfte“ unter Wissen (frieda-reist#276), aufgerufen von test_plan_rubriken_276.py.
// Aufruf: node seiten_plan_rubriken.mjs <playwright-modul> <basis-url> <id> [<id> …]
// Meldet die Zeilen unter „Über diesen Plan“ im Reiter Wissen und für jede ID, wo ihr Aufruf landet.
const [, , modul, basis, ...ids] = process.argv;
const pw = await import(modul);
const b = await pw[process.env.RH_BROWSER || "chromium"].launch();
const ctx = await b.newContext({viewport: {width: 390, height: 844}, serviceWorkers: "block"});
await ctx.route("**/api/**", r => r.abort());
const p = await ctx.newPage();
const fehler = [];
p.on("pageerror", e => fehler.push(String(e)));
await p.goto(basis + "#wissen");
await p.waitForSelector("#titel:not(:empty)");
await p.waitForTimeout(300);
const zeilen = await p.evaluate(() => {
  const h = document.querySelector("#main #ueber-plan");
  const l = h && h.nextElementSibling && h.nextElementSibling.matches(".wliste") ? h.nextElementSibling
    : h && h.nextElementSibling && h.nextElementSibling.nextElementSibling;
  return l && l.matches(".wliste") ? [...l.querySelectorAll("a.wzeile")].map(a => a.getAttribute("href").slice(1)) : [];
});
const ziele = {};
for (const id of ids) {
  await p.evaluate(h => { location.hash = h; }, id);
  await p.waitForTimeout(300);
  ziele[id] = await p.evaluate(() => ({
    reiter: (document.querySelector("#nav a.on") || {getAttribute: () => "#"}).getAttribute("href").slice(1),
    achse: !!document.querySelector("#main .tagzeilen"),
    leer: (document.querySelector("#main").innerText || "").trim().length < 40,
  }));
}
await b.close();
console.log(JSON.stringify({fehler, zeilen, ziele}));
