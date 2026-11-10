// Buchung mit Angaben je Ding (#473, #475), aufgerufen von test_buchung_zeitraum.py.
// Aufruf: node seiten_buchung_je_ding.mjs <playwright-modul> <basis-url>
const [, , modul, basis] = process.argv;
const pw = await import(modul);
const b = await pw[process.env.RH_BROWSER || "chromium"].launch();
const fehler = [], tage = {};
const ctx = await b.newContext({viewport: {width: 1300, height: 900}, serviceWorkers: "block"});
await ctx.route("**/api/**", r => r.abort());
for (const tag of ["T-01", "T-03"]) {
  const p = await ctx.newPage();
  p.on("pageerror", e => fehler.push(String(e)));
  await p.goto(basis + "#" + tag);
  await p.waitForSelector(".tagseite");
  tage[tag] = await p.evaluate(() => {
    const bl = document.querySelector('#main .buchung[data-ziel="B-01"]');
    const z = bl && bl.closest(".z.ziel");
    return {block: !!bl, text: bl ? [...bl.children].filter(x => x.tagName !== "DETAILS").map(x => x.textContent).join(" | ") : "",
      kopf: z ? (z.querySelector(":scope > .z.klein") || {}).textContent || "" : ""};
  });
  await p.close();
}
await b.close();
console.log(JSON.stringify({fehler, tage}));
