// Reiseüberblick (gewählter Plan, 28.10.2026), aufgerufen von test_reiseueberblick.py.
// Aufruf: node seiten_reise.mjs <playwright-modul> <basis-url> <datum JJJJ-MM-TT>
// Meldet je Breite: Reiter, Planname auf der Seite, Kopf mit Zähler, An- und Abreise, Kennzahlen mit Kosten, Mitreisende,
// Stand der Vorbereitung, feste Termine, Tage als Zeilen mit Nacht und Stand, Reihenfolge, Überstand, Ziel eines Plans (P-…) und eines Tages, Skriptfehler.
const [, , modul, basis, datum] = process.argv;
const pw = await import(modul);
const b = await pw[process.env.RH_BROWSER || "chromium"].launch();
const fehler = [], aus = {};
for (const breite of [390, 1300]) {
  const ctx = await b.newContext({viewport: {width: breite, height: 900}, serviceWorkers: "block"});
  await ctx.route("**/api/**", r => r.abort());
  const p = await ctx.newPage();
  p.on("pageerror", e => fehler.push(`${breite}: ${e}`));
  await p.clock.setFixedTime(new Date(`${datum}T10:00:00`));
  await p.goto(basis);
  await p.waitForSelector(".tagzeilen");
  const lesen = () => p.evaluate(() => {
    const t = s => [...document.querySelectorAll(s)].map(x => x.textContent.trim());
    return {
      reiter: t("#nav a"), aktiv: (document.querySelector("#nav a.on") || {}).textContent,
      planname: /\bPlan [A-Z]\b/.test(document.querySelector("#main").textContent),
      steckbriefe: document.querySelectorAll("#main .steckbrief, #main .umschalter").length,
      kopf: t(".reisekopf > *"),
      kennzahlen: t("#main > .kz .kzn"),
      stand: [...document.querySelectorAll(".stand .standzeile")].map(z => [z.children[0].textContent, z.children[1].textContent, z.getAttribute("href")]),
      tage: [...document.querySelectorAll("#main > .tagzeilen > .tagzeile")].map(z => [z.getAttribute("href"), z.querySelector(".tz-titel").textContent,
        (z.querySelector(".tz-nacht .chip") || {}).textContent || null]),
      breit: document.documentElement.scrollWidth > innerWidth + 1,
      anab: [...document.querySelectorAll(".anab")].map(x => [x.querySelector(".etikett").textContent, x.getAttribute("href"), [...x.querySelectorAll("li")].map(l => l.textContent)]),
      reihenfolge: [...document.querySelectorAll("#main > *")].map(x => x.matches(".anab") ? x.querySelector(".etikett").textContent.split(" ")[0]
        : x.matches(".kartenbox") ? "Karte" : x.matches(".tagzeilen") ? "Tage" : null).filter(Boolean),
      kosten: (document.querySelector("#main > .kz > div:last-child .kzw") || {}).textContent,
      kostenHinweis: (document.querySelector("#main > .kz + .meldung") || {}).textContent || "",
      mitreisende: (document.querySelector(".mitreisende") || {}).textContent || null,
      termine: t(".termine .tz-titel"),
    };
  });
  const a = aus[breite] = await lesen();
  await p.evaluate(() => { location.hash = "P-A"; });
  await p.waitForTimeout(200);
  a.planZiel = await p.evaluate(() => !!document.querySelector(".tagzeilen") && !document.querySelector(".steckbrief"));
  await p.evaluate(() => { location.hash = ""; });
  await p.waitForSelector(".tagzeilen");
  await p.locator("#main > .tagzeilen .tz-titel").first().click();
  await p.waitForTimeout(200);
  a.nachKlick = await p.evaluate(() => location.hash);
  await ctx.close();
}
await b.close();
console.log(JSON.stringify({aus, fehler}));
