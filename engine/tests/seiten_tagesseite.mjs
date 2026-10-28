// Tagesseite in Ebenen (B2, frieda-reist#53), aufgerufen von test_tagesseite.py.
// Aufruf: node seiten_tagesseite.mjs <playwright-modul> <basis-url>
// Meldet je Breite: Überstand, Kästen, Reihenfolge der Ebenen, Reiter (Klick und Pfeiltasten), Tiefenlinks, Kennung
// (Sprechblase, Tooltip, Fenster mit Kopieren), Merkmallisten ohne Kennzahlen, gestapelte Tabellen und Skriptfehler.
const [, , modul, basis] = process.argv;
const pw = await import(modul);
const b = await pw[process.env.RH_BROWSER || "chromium"].launch();
const fehler = [], aus = {};
const offen = () => [...document.querySelectorAll(".ebene-unterwegs [role=tabpanel]")].filter(x => !x.hidden).map(x => x.id);
for (const breite of [390, 1300]) {
  const ctx = await b.newContext({viewport: {width: breite, height: 900}, serviceWorkers: "block"});
  await ctx.route("**/api/**", r => r.abort());
  const p = await ctx.newPage();
  p.on("pageerror", e => fehler.push(`${breite}: ${e}`));
  await p.goto(basis + "#T-02");
  await p.waitForSelector(".tagseite");
  // „Weiterlesen“ misst die Höhe des Texts im nächsten Bild: zwei Bilder abwarten
  await p.evaluate(() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))));
  const a = aus[breite] = await p.evaluate(() => {
    const oben = s => { const e = document.querySelector(s); return e ? Math.round(e.getBoundingClientRect().top + scrollY) : null; };
    const links = s => { const e = document.querySelector(s); return e ? Math.round(e.getBoundingClientRect().left) : null; };
    const breit = [...document.querySelectorAll("#main *")].filter(e => e.getBoundingClientRect().right > innerWidth + 1).map(e => e.className || e.tagName);
    return {
      breit: document.documentElement.scrollWidth > innerWidth + 1 ? breit.slice(0, 5) : [],
      // Kästen außerhalb des Abschnitts „Nacht“ (dort stehen Unterkunft und Vergleich, Seitenordnung 28.10.2026)
      kaesten: [...document.querySelectorAll(".tagseite :is(.karte, details.block, .wm-karte)")].filter(x => !x.closest(".ebene-nacht")).length,
      flaeche: !!document.querySelector(".tag-oben > .karte.flaeche"),
      ebenen: ["weg", "unterwegs", "orte", "hintergrund", "quellen"].map(n => [n, oben(".ebene-" + n), links(".ebene-" + n)]),
      reiter: [...document.querySelectorAll(".ebene-unterwegs [role=tab]")].map(x => x.textContent),
      planChips: [...document.querySelectorAll("#main > .chips .chip")].map(x => x.textContent),
      info: document.querySelectorAll(".zid-i, .zid-kennung, .zid-wort").length,
      knoepfe: [...document.querySelectorAll("#main button.zid")].map(x => [x.title, x.getAttribute("aria-label")]),
      merkmale: [...document.querySelectorAll(".ebene-unterwegs dl.textmerkmale dt")].map(x => x.textContent),
      kennungImKopf: [...document.querySelectorAll(".ebene-unterwegs .ebene-kopf [data-rm]")].map(x => x.dataset.rm),
      textInEtappe: document.querySelectorAll(".wv-strecke [data-rm='E-01']").length,
      // Regel 9: unterwegs keine Sprechblase in Vorschauen (Orte des Tages) und an Zugeklapptem (Quellen)
      sichtbarVorschau: [...document.querySelectorAll(".vorschau .zid-box, details:not([open]) > summary .zid-box")].filter(x => getComputedStyle(x).display !== "none").length,
      vorschauen: document.querySelectorAll(".vorschau .zid-box").length,
      zugeklappt: document.querySelectorAll("details:not([open]) > summary .zid-box").length,
      // Hintergrund als Kapitel, alle zu; Unterwegs nachschlagen als getönte Fläche; Der Weg gekürzt mit „Weiterlesen“
      kapitel: [document.querySelectorAll(".ebene-hintergrund details.kapitel").length, document.querySelectorAll(".ebene-hintergrund details.kapitel[open]").length],
      getoent: getComputedStyle(document.querySelector(".ebene-unterwegs")).backgroundColor !== getComputedStyle(document.body).backgroundColor,
      weiterlesen: [...document.querySelectorAll(".ebene-weg .weiterlesen")].filter(x => !x.hidden).length,
    };
  });
  a.offen = await p.evaluate(offen);
  // Reiter: Klick auf den letzten, dann Pfeil nach rechts (zum ersten)
  const tabs = p.locator(".ebene-unterwegs [role=tab]");
  await tabs.last().click();
  a.nachKlick = await p.evaluate(offen);
  a.kennungNachKlick = await p.evaluate(() => [...document.querySelectorAll(".ebene-unterwegs .ebene-kopf [data-rm]")].map(x => x.dataset.rm));
  await tabs.last().press("ArrowRight");
  a.nachPfeil = await p.evaluate(offen);
  // Breite Tabelle (Unterkünfte) am Handy gestapelt, am Rechner Tabelle
  await tabs.last().click();
  a.tabelle = await p.evaluate(() => { const td = document.querySelector(".ebene-unterwegs [role=tabpanel]:not([hidden]) .tabelle.stapel td");
    return td && {display: getComputedStyle(td).display, vor: getComputedStyle(td.parentNode.children[1], "::before").content}; });
  a.breitNachTabelle = await p.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1);
  // Wahl bleibt beim Neuzeichnen
  await p.evaluate(() => route(true));
  a.gemerkt = await p.evaluate(offen);
  // Anmerken öffnet das Fenster mit Kennung und „Kopieren“
  await p.locator(".ebene-weg button.zid").first().click();
  a.fenster = await p.evaluate(() => ({offen: document.querySelector("#rm").open, kennung: (document.querySelector("#rm .kennung") || {}).textContent,
    kopieren: !!document.querySelector("#rm [data-kopieren]")}));
  await p.keyboard.press("Escape");
  // Kapitel: immer nur eines offen; „Weiterlesen“ zeigt den ganzen Weg
  const kap = p.locator(".ebene-hintergrund details.kapitel > summary .kap-titel");
  await kap.nth(0).click(); await p.waitForTimeout(100); await kap.nth(1).click(); await p.waitForTimeout(100);
  a.kapitelOffen = await p.evaluate(() => [...document.querySelectorAll(".ebene-hintergrund details.kapitel[open]")].map(x => x.id));
  await p.locator(".ebene-weg .weiterlesen:not([hidden])").first().click();
  a.nachWeiterlesen = await p.evaluate(() => document.querySelectorAll(".ebene-weg .weg-text.kurz").length);
  // Tiefenlinks: Abschnitt in einem Reiter, in den Quellen (aufgeklappt) und im Hintergrund
  a.tiefe = {};
  for (const id of ["E-01.wegpunkte", "E-01.quellen-und-pruefung", "E-01.tipps"]) {
    await p.evaluate(() => { location.hash = "#plan"; });
    await p.waitForTimeout(50);
    await p.evaluate(h => { location.hash = h; }, id);
    await p.waitForTimeout(150);
    a.tiefe[id] = await p.evaluate(i => { const e = document.getElementById(i);
      return !!e && !!document.querySelector(".tagseite") && e.offsetParent !== null && !e.hidden && (!e.closest("details") || e.closest("details").open); }, id);
  }
  await ctx.close();
}
await b.close();
console.log(JSON.stringify({fehler, aus}));
