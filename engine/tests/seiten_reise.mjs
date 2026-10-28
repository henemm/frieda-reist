// Reiseüberblick (gewählter Plan, 28.10.2026), aufgerufen von test_reiseueberblick.py.
// Aufruf: node seiten_reise.mjs <playwright-modul> <basis-url> <datum JJJJ-MM-TT>
// Meldet je Breite: Reiter, Planname auf der Seite, Kopf mit Zähler, An- und Abreise, Kennzahlen mit Kosten, Mitreisende,
// Stand der Vorbereitung, feste Termine, Tage als Zeilen mit Nacht und Stand, Reihenfolge, offene Fragen ohne Kennungen, Überstand, Ziel eines Plans (P-…) und eines Tages, Skriptfehler.
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
      kennzahlen: t(".reise-zahlen .kz .kzn"),
      stand: [...document.querySelectorAll(".stand .standzeile")].map(z => [z.children[0].textContent, z.children[1].textContent, z.getAttribute("href")]),
      tage: [...document.querySelectorAll(".reise-tage .tagzeile")].map(z => [z.getAttribute("href"), z.querySelector(".tz-titel").textContent,
        (z.querySelector(".tz-nacht .chip") || {}).textContent || null]),
      breit: document.documentElement.scrollWidth > innerWidth + 1,
      anab: [...document.querySelectorAll(".anab")].map(x => [x.querySelector(".etikett").textContent, x.getAttribute("href"), [...x.querySelectorAll("li")].map(l => l.textContent)]),
      reihenfolge: [...document.querySelectorAll(".reise > *")].map(x => x.matches(".anab") ? x.querySelector(".etikett").textContent.split(" ")[0]
        : x.matches(".reise-karte") ? "Karte" : x.matches(".reise-tage") ? "Tage" : null).filter(Boolean),
      kosten: (document.querySelector(".reise-zahlen .kz > div:last-child .kzw") || {}).textContent,
      kostenHinweis: (document.querySelector(".reise-zahlen .meldung") || {}).textContent || "",
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
  await p.locator(".reise-tage .tz-titel").first().click();
  await p.waitForTimeout(200);
  a.nachKlick = await p.evaluate(() => location.hash);
  // Lesetext: eine Kennung wird zum Namen mit Link, eine Rückmeldungsnummer entfällt
  await p.evaluate(() => { location.hash = "W-06.kirnitzschtalbahn"; });
  await p.waitForTimeout(200);
  a.lesetext = await p.evaluate(() => { const b = document.getElementById("W-06.kirnitzschtalbahn");
    return {text: b.textContent, link: [...b.querySelectorAll('a[href="#F-03"]')].map(x => x.textContent)}; });
  // Offene Fragen ohne Kennungen im Text, gruppiert nach Stand; die Stellen als Pillen mit Namen
  await p.evaluate(() => { location.hash = "fragen"; });
  await p.waitForSelector("#fragen .frage");
  a.fragen = await p.evaluate(() => ({
    kennungen: (document.querySelector("#fragen").textContent.match(/\b(?:AG-\d+|[TEOUVPFW]-\d+(?:\.[a-z0-9-]+)?)\b/g) || []),
    gruppen: [...document.querySelectorAll("#fragen :is(h3, summary .kap-titel)")].map(x => x.firstChild.textContent),
    pillen: [...document.querySelectorAll("#F-01 .ag-bezug a")].map(x => x.textContent),
  }));
  await ctx.close();
}
await b.close();
console.log(JSON.stringify({aus, fehler}));
