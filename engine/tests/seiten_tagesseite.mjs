// Tagesseite in drei Ansichten (Fluss, Reiter, Magazin), aufgerufen von test_tagesseite.py.
// Aufruf: node seiten_tagesseite.mjs <playwright-modul> <basis-url>
// Meldet je Breite und Ansicht: überstehende Breite, Kennungen, Reiter, Seitenindex, Tiefenlink, Fenster mit Kopieren und Skriptfehler.
const [, , modul, basis] = process.argv;
const pw = await import(modul);
const b = await pw[process.env.RH_BROWSER || "chromium"].launch();
const fehler = [], aus = {};

for (const breite of [390, 1300]) {
  const ctx = await b.newContext({viewport: {width: breite, height: 900}, serviceWorkers: "block"});
  const p = await ctx.newPage();
  p.on("pageerror", e => fehler.push(`${breite}: ${e}`));
  await p.goto(basis + "#T-02");
  await p.waitForSelector(".tagesumschalter");
  aus[breite] = {};
  for (const a of ["fluss", "reiter", "magazin"]) {
    await p.click(`[data-tagesansicht=${a}]`);
    await p.waitForSelector(`.tag-ansicht.tag-${a}`);
    aus[breite][a] = await p.evaluate(() => ({
      breit: document.documentElement.scrollWidth > innerWidth + 1,
      knoepfe: document.querySelectorAll("#main button.zid").length,
      info: document.querySelectorAll(".zid-i, .zid-kennung").length,
      gedrueckt: document.querySelector(".tagesumschalter [aria-pressed=true]").dataset.tagesansicht,
      reiter: document.querySelectorAll(".reiter [role=tab]").length,
      index: !!document.querySelector(".tag-magazin .index") && getComputedStyle(document.querySelector(".tag-magazin .index")).display !== "none",
      indexKlein: !!document.querySelector(".index-m") && getComputedStyle(document.querySelector(".index-m")).display !== "none",
    }));
  }
  // Reiter wechseln: genau ein Abschnitt sichtbar, danach ein anderer
  await p.click("[data-tagesansicht=reiter]");
  const tabs = p.locator(".reiter [role=tab]");
  if (await tabs.count() > 1) {
    await tabs.nth(1).click();
    aus[breite].reiterWechsel = await p.evaluate(() => [...document.querySelectorAll(".reiter .panel")].map(x => !x.hidden));
  }
  // Tiefenlink auf einen Abschnitt in jeder Ansicht sichtbar
  const id = await p.evaluate(() => { const x = document.querySelector(".reiter .panel:last-child"); return x && x.id; });
  aus[breite].tiefenlink = {};
  if (id) for (const a of ["reiter", "magazin", "fluss"]) {
    await p.click(`[data-tagesansicht=${a}]`);
    await p.goto(basis + "#" + id);
    await p.waitForTimeout(500);
    aus[breite].tiefenlink[a] = await p.evaluate(i => { const e = document.getElementById(i); return !!e && e.offsetParent !== null && (e.tagName !== "DETAILS" || e.open); }, id);
    await p.goto(basis + "#T-02");
    await p.waitForSelector(".tagesumschalter");
  }
  // Anmerken öffnet das Fenster mit der Kennung und „Kopieren“
  await p.click("[data-tagesansicht=reiter]");
  await p.locator("#main button.zid").first().click({force: true});
  aus[breite].fenster = await p.evaluate(() => ({offen: document.querySelector("#rm").open, kopieren: !!document.querySelector("#rm [data-kopieren]"), kennung: (document.querySelector("#rm .kennung") || {}).textContent}));
  await ctx.close();
}
await b.close();
console.log(JSON.stringify({fehler, aus}));
