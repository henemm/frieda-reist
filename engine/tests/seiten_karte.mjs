// Automatische Karte (Epic #225), aufgerufen von test_karte_seite.py.
// Aufruf: node seiten_karte.mjs <playwright-modul> <basis-url> <offen|fest>
// offen: Reiter, Punkte je Ansicht, Legende, gestrichelte Linien, Aufenthalte ohne Tag. fest: Tageskarten von Tag 1 und 2.
const [, , modul, basis, fall] = process.argv;
const pw = await import(modul);
const b = await pw[process.env.RH_BROWSER || "chromium"].launch();
const fehler = [], aus = {};
const punkte = p => p.evaluate(() => ({
  gefuellt: document.querySelectorAll(".kartenbox:not(.ekarte) .rh-ding:not(.umriss)").length,
  umriss: document.querySelectorAll(".kartenbox:not(.ekarte) .rh-ding.umriss").length}));
for (const breite of [390, 1300]) {
  const ctx = await b.newContext({viewport: {width: breite, height: 900}, serviceWorkers: "block"});
  await ctx.route("**/api/**", r => r.abort());
  const p = await ctx.newPage();
  p.on("pageerror", e => fehler.push(`${breite}: ${e}`));
  await p.goto(basis + "#karte");
  await p.waitForSelector(".kartenbox .leaflet-marker-icon", {state: "attached"});
  const a = aus[breite] = await p.evaluate(() => ({
    reiter: [...document.querySelectorAll("#nav a")].map(x => x.textContent.trim()),
    kartenboxen: document.querySelectorAll("#main .kartenbox:not(.ekarte)").length,
    steckbriefe: document.querySelectorAll("#main .steckbrief").length,
    legende: [...document.querySelectorAll("#main .legende span")].map(x => x.textContent.trim()),
    gestrichelt: [...document.querySelectorAll(".kartenbox path")].filter(x => x.getAttribute("stroke-dasharray") === "7 7").length,
    ansichten: [...document.querySelectorAll(".kartenansichten button")].map(x => x.textContent.trim()),
    // vollständig als Karte (dingKarte), mit Heimat anderswo als Listenzeile (#328)
    ohneTag: [...[...document.querySelectorAll(".ohne-tag .karte > .k")].map(x => x.firstChild.textContent),
              ...[...document.querySelectorAll(".ohne-tag .wzeile .wt")].map(x => x.textContent)].map(x => x.trim()),
    breit: document.documentElement.scrollWidth > innerWidth + 1,
  }));
  a.punkte = {uebersicht: await punkte(p)};
  // Vergrößern (#425): Knopf an der Karte unter Reise, Vollbild per CSS (auch am iPhone), Schließen mit Knopf und Esc
  const gross = () => p.evaluate(() => {
    const s = document.querySelector("#main .reise-karte"), k = s && s.querySelector(".kartenbox");
    return {gross: !!s && s.classList.contains("gross"), hoehe: k ? Math.round(k.getBoundingClientRect().height) : 0, fenster: innerHeight};
  });
  a.klein = await gross();
  await p.click("#main .karte-gross");
  await p.waitForFunction(() => document.querySelector("#main .reise-karte.gross"));
  a.vergroessert = await gross();
  await p.keyboard.press("Escape");
  await p.waitForFunction(() => !document.querySelector("#main .reise-karte.gross"));
  a.zu = await gross();
  await p.click("#main .karte-gross");
  await p.click("#main .karte-gross");
  a.knopfSchliesst = !(await gross()).gross;
  for (const titel of a.ansichten.slice(1)) {
    await p.click(`.kartenansichten button:text-is("${titel}")`);
    await p.waitForSelector(".kartenbox .leaflet-marker-icon", {state: "attached"});
    a.punkte[titel] = await punkte(p);
  }
  if (a.ansichten.length) await p.click('.kartenansichten button:text-is("Übersicht")');
  if (fall === "plaene") {
    // Linien tragen die Klasse rh-plan-<farbe> des Plans (vorlage.html, Karte); die Farben müssen sich unterscheiden
    // Mehrere Pläne stehen nebeneinander auf dem Reiter „Varianten“; der Reiter „Karte“ zeigt nur den Plan der Zeitachse
    await p.goto(basis + "#plaene");
    await p.waitForSelector(".kartenbox path");
    a.auto = await p.evaluate(() => !![...document.querySelectorAll("#main .legende span")].find(x => /schematisch/.test(x.textContent)));
    a.planLegende = await p.evaluate(() => [...document.querySelectorAll("#main .legende span")].map(x => x.textContent.trim()));
    Object.assign(a, await p.evaluate(() => {
      const pfade = [...document.querySelectorAll(".kartenbox path")];
      const klassen = [...new Set(pfade.flatMap(x => [...x.classList]).filter(c => /^rh-plan-/.test(c)))];
      const farben = Object.fromEntries(klassen.map(c => [c, getComputedStyle(pfade.find(x => x.classList.contains(c))).stroke]));
      return {planKlassen: klassen, planFarben: farben};
    }));
  } else if (fall === "offen") {
    await p.goto(basis + "#plan");
    await p.waitForSelector("#main h2");
    a.imTagesplan = (await p.textContent("#main .tagzeilen.achse")).includes("Wochenmarkt");   // Zeitachse der Tage; der Ort ohne Tag steht am Ende der Reise (#425)
  } else {
    for (const tag of ["T-01", "T-02"]) {
      await p.goto(basis + "#" + tag);
      await p.waitForSelector(".tagseite");
      const box = await p.$(".tag-karte .kartenbox");
      if (box) { await box.scrollIntoViewIfNeeded(); await p.waitForSelector(".tag-karte .kartenbox .leaflet-marker-icon", {state: "attached"}); }
      a["tag" + tag.slice(-1)] = await p.evaluate(() => ({
        karten: document.querySelectorAll(".tag-karte .kartenbox").length,
        gefuellt: document.querySelectorAll(".tag-karte .rh-ding:not(.umriss)").length,
        umriss: document.querySelectorAll(".tag-karte .rh-ding.umriss").length,
        schematisch: !!document.querySelector(".tag-karte .lg-sch")}));
    }
  }
  await ctx.close();
}
await b.close();
console.log(JSON.stringify({fehler, aus}));
