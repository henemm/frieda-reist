// Art-Übersicht (ADR-0007, Schritt e, frieda-reist#286), aufgerufen von test_art_uebersicht.py.
// Aufruf: node seiten_art_uebersicht.mjs <playwright-modul> <basis-url> <abschnitt> <art>
// Meldet am Rechner (1300 px) und am Telefon (390 px), was die Übersicht der Art zeigt: Zeilen, Links, ob Tabelle oder Karten sichtbar
// sind, ob ein Ding vollständig dort steht, und die Reihenfolge nach einem Klick auf einen Spaltenkopf.
const [, , modul, basis, abschnitt, art] = process.argv;
const pw = await import(modul);
const b = await pw[process.env.RH_BROWSER || "chromium"].launch();
const fehler = [], out = {};
const messen = async (breite, grob) => {
  const ctx = await b.newContext({viewport: {width: breite, height: 900}, serviceWorkers: "block", hasTouch: grob, isMobile: grob});
  await ctx.route("**/api/**", r => r.abort());
  const p = await ctx.newPage();
  p.on("pageerror", e => fehler.push(String(e)));
  await p.goto(basis + "#" + abschnitt);
  await p.waitForSelector(".art-tabelle");
  const sichtbar = sel => p.evaluate(sel => { const e = document.querySelector(sel); return !!e && e.getBoundingClientRect().width > 0 && getComputedStyle(e).display !== "none"; }, sel);
  const r = {
    tabellen: await p.locator(`.art-tabelle[data-art="${art}"]`).count(),
    zeilen: await p.locator(`.art-tabelle[data-art="${art}"] tbody tr`).count(),
    karten: await p.locator(`.art-tabelle[data-art="${art}"] .wm-karte`).count(),
    links: await p.evaluate(a => [...document.querySelectorAll(`.art-tabelle[data-art="${a}"] tbody th a`)].map(x => x.getAttribute("href")), art),
    tabelleSichtbar: await sichtbar(`.art-tabelle[data-art="${art}"] .wm-tabelle`),
    kartenSichtbar: await sichtbar(`.art-tabelle[data-art="${art}"] .wm-karten`),
    // kein Ding steht vollständig in der Übersicht: keine Kennung als Sprungziel, keine Karte des Dings
    vollstaendig: await p.evaluate(() => document.querySelectorAll(".art-uebersicht [data-ziel], .art-uebersicht .karte[id]").length),
    text: await p.evaluate(a => document.querySelector(`.art-tabelle[data-art="${a}"]`).innerText, art),
  };
  if (!grob) {
    const namen = () => p.evaluate(a => [...document.querySelectorAll(`.art-tabelle[data-art="${a}"] tbody th a`)].map(x => x.textContent), art);
    r.vorher = await namen();
    const knopf = p.locator(`.art-tabelle[data-art="${art}"] thead button`).nth(1);
    if (await knopf.count()) { await knopf.click(); r.nach_sortierung = await namen(); r.aria = await p.evaluate(a => document.querySelector(`.art-tabelle[data-art="${a}"] thead th[aria-sort]`)?.textContent || null, art); }
    // ein Link führt zur Heimat
    const erster = p.locator(`.art-tabelle[data-art="${art}"] tbody th a`).first();
    if (await erster.count()) { await erster.click(); r.nach_klick = await p.evaluate(() => location.hash); }
  }
  await ctx.close();
  return r;
};
out.rechner = await messen(1300, false);
out.telefon = await messen(390, true);
await b.close();
console.log(JSON.stringify({fehler, ...out}));
