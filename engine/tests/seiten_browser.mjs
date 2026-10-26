// Rundgang durch alle Ansichten einer gebauten Reise (Designsystem, frieda-reist#18), aufgerufen von test_seite.py.
// Aufruf: node seiten_browser.mjs <playwright-modul> <basis-url> [dom-datei]
// Öffnet jede Route (Reiter, Tage, Wahlstellen, Optionen, Unterkünfte, Pläne, Abschnitte, Fragen, Bausteinseite) bei 390
// und 1200 px und meldet Skriptfehler, leere Ansichten und Ansichten, die auf dem Handy seitlich überstehen. Mit dom-datei
// wird zusätzlich das HTML jeder Ansicht gespeichert, ohne Karteninhalt (der lädt zeitversetzt): So lässt sich vor und
// nach einem Umbau prüfen, ob die Seite gleich bleibt. Mit RH_BILDER=<ordner> entstehen Bilder der Bausteinseite
// (Handy und Rechner, hell und dunkel) zur Durchsicht.
import fs from "node:fs";

const [, , modul, basis, domDatei] = process.argv;
const pw = await import(modul);
const b = await pw[process.env.RH_BROWSER || "chromium"].launch();
const fehler = [], leer = [], breit = [], dom = {}, vergleich = {}, bilder = [];
for (const breite of [390, 1200]) {
  const ctx = await b.newContext({viewport: {width: breite, height: 900}, serviceWorkers: "block"});
  await ctx.route("**/api/**", r => r.abort());   // ohne Rückmeldedienst: Seite muss trotzdem vollständig sein
  const p = await ctx.newPage();
  await p.clock.setFixedTime(new Date("2026-10-27T10:00:00"));
  p.on("pageerror", e => fehler.push(`${breite} ${p.url()}: ${e}`));
  await p.goto(basis);
  await p.waitForSelector("#titel:not(:empty)");
  await p.waitForTimeout(300);
  const routen = await p.evaluate(() => {
    const r = new Set(["", "plan", "varianten", "offen", "wissen", "etappen", "wuensche", "orte", "praxis", "quellen", "fragen", "aufgaben", "rueckmeldungen", "bausteine"]);
    for (const a of abschnitte) { r.add(a.id); for (const x of a.bloecke) r.add(x.id); }
    if (R) {
      R.tage.forEach(t => r.add(t.id)); Object.keys(R.weitere_tage).forEach(t => r.add(t)); Object.keys(R.unterkuenfte).forEach(u => r.add(u));
      R.wahlstellen.forEach(v => { r.add(v.id); v.optionen.forEach(o => r.add(o.id)); }); R.plaene.forEach(x => r.add(x.id));
    }
    D.fragen.zeilen.forEach(z => r.add(z.id));
    return [...r];
  });
  for (const h of routen) {
    await p.evaluate(h => { location.hash = h; }, h);
    await p.waitForTimeout(15);
    const html = await p.evaluate(() => {
      const c = document.querySelector("#main").cloneNode(true);
      c.querySelectorAll(".regionen").forEach(x => x.querySelectorAll("[aria-pressed]").forEach(k => k.removeAttribute("aria-pressed")));
      c.querySelectorAll(".kartenbox").forEach(x => x.replaceWith(Object.assign(document.createElement("div"), {className: "kartenbox"})));
      c.querySelectorAll(".blitz").forEach(x => x.classList.remove("blitz"));
      return c.childElementCount ? c.outerHTML : "";
    });
    if (!html) leer.push(`${breite}#${h}`);
    if (breite < 700 && await p.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1)) breit.push(h);
    dom[`${breite}#${h}`] = html;
  }
  // Wahl-Modul bedienen: erste Stelle mit „Alternativen vergleichen“ öffnen, „nur Unterschiede“ umschalten
  for (const h of routen) {
    await p.evaluate(h => { location.hash = h; }, h);
    await p.waitForTimeout(15);
    const knopf = p.locator('#main [data-vgl-auf][aria-expanded="false"]:visible').first();
    if (!await knopf.count()) continue;
    const id = await knopf.getAttribute("data-vgl-auf");
    await knopf.click();
    const box = p.locator(`#main [data-vgl="${id}"]`).first();
    const sichtbar = await box.isVisible();
    const spalten = await box.locator(breite < 700 ? ".wm-karte" : "thead th").count();
    await box.locator("[data-vgl-nur]").check();
    vergleich[breite] = {route: h, sichtbar, spalten: breite < 700 ? spalten : spalten - 1, offen: await p.locator(`[data-vgl-auf="${id}"]`).first().getAttribute("aria-expanded")};
    break;
  }
  await ctx.close();
}
// Bausteinseite in hell und dunkel; Bilder nur mit RH_BILDER
for (const [breite, schema] of [[390, "light"], [390, "dark"], [1200, "light"], [1200, "dark"]]) {
  const ctx = await b.newContext({viewport: {width: breite, height: 900}, serviceWorkers: "block", colorScheme: schema});
  await ctx.route("**/api/**", r => r.abort());
  const p = await ctx.newPage();
  await p.clock.setFixedTime(new Date("2026-10-27T10:00:00"));
  p.on("pageerror", e => fehler.push(`${breite} ${schema} #bausteine: ${e}`));
  await p.goto(basis + "#bausteine");
  await p.waitForSelector("#titel:not(:empty)");
  await p.waitForTimeout(300);
  if (process.env.RH_BILDER) {
    const datei = `${process.env.RH_BILDER}/bausteine-${process.env.RH_BROWSER || "chromium"}-${breite}-${schema === "dark" ? "dunkel" : "hell"}.png`;
    await p.addStyleTag({content: ".leiste,body::after{display:none!important}"});
    await p.screenshot({path: datei, fullPage: true});
    bilder.push(datei);
  }
  await ctx.close();
}
await b.close();
if (domDatei) fs.writeFileSync(domDatei, JSON.stringify(dom));
console.log(JSON.stringify({routen: Object.keys(dom).length, leer, breit, fehler, vergleich, bilder}));
