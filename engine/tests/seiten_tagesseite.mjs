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
      // Aufenthalte ohne Nacht in der Zeitleiste des Tags (Paket O-5): Name und Buchungsstand
      aufenthalte: [...document.querySelectorAll(".tagseite .wv-aufenthalt")].map(x => [x.querySelector(".titelzeile span").textContent, (x.querySelector(".chip") || {}).textContent || ""]),
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
      // Nacht: über die volle Breite nur bei offener Wahl, sonst an ihrem Platz in der Lesespalte
      nacht: {voll: !!document.querySelector(".tagseite > .nacht-voll"), inLesen: !!document.querySelector(".tag-lesen > .ebene-nacht"),
        // Platz (Product Owner 31.10.2026): nach dem Hintergrund, vor den Quellen; oben in Pixeln
        oben: oben(".ebene-nacht"), hintergrund: oben(".ebene-hintergrund"), quellen: oben(".ebene-quellen"),
        // Stand-Leiter: nicht gebucht sind die Einzelheiten der Unterkunft offen
        einzelheiten: [...document.querySelectorAll(".ebene-nacht .karte > details.einzelheiten")].map(d => d.open)},
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
  // Stand-Leiter, gebucht (Tag 1, Hotel am Elbufer mit Buchung B-01, Beispielwerte): kompakt, Einzelheiten zu, ein Stand
  await p.evaluate(() => { location.hash = "#T-01"; });
  await p.waitForSelector(".ebene-nacht #U-01");
  a.gebucht = await p.evaluate(() => {
    const k = document.querySelector(".ebene-nacht #U-01"), b = k.querySelector("[id='B-01']");
    const zeilen = x => [...x.querySelectorAll(":scope > .z")].map(z => z.textContent);
    return {karte: [...k.querySelectorAll(":scope > details.einzelheiten")].map(d => d.open),
      buchung: [...b.querySelectorAll(":scope > details.einzelheiten")].map(d => d.open),
      oben: zeilen(b).map(t => t.split(":")[0]), storno: zeilen(b).find(t => t.startsWith("Storno")) || null,
      ab: zeilen(b).find(t => t.startsWith("Ab:")) || null,
      // Charakter (nach_buchung) sichtbar vor der Buchung, die übrigen Merkmale „Aus der Planung“ (zu)
      sichtbar: [...k.querySelectorAll(":scope > dl.mliste dt")].map(x => x.textContent),
      planung: [...k.querySelectorAll(":scope > details.einzelheiten > summary")].map(x => x.textContent),
      inPlanung: [...k.querySelectorAll(":scope > details.einzelheiten dl.mliste dt")].map(x => x.textContent),
      reihenfolge: [...k.children].map(x => x.matches("dl.mliste") ? "sichtbar" : x.matches(".buchung") ? "buchung"
        : x.matches("details.einzelheiten") ? "planung" : null).filter(Boolean),
      // Stand-Chips an der Karte (ohne Frage und Kalender)
      chipsKarte: [...k.querySelectorAll(":scope > .chips .chip")].filter(c => ["gebucht", "angefragt", "nicht gebucht"].includes(c.textContent)).length,
      tageskasten: [...document.querySelectorAll(".tag-oben .ding.nacht .chip, .tag-oben .ding.nacht .wm-knopf")].map(x => x.textContent)};
  });
  // Kosten: gebucht zählt der Preis der Buchung, nicht das Angebot (Testwert: B-01 kostet 100 €, U-01 bietet 120 €)
  a.kosten = await p.evaluate(() => { const alt = R.buchungen["B-01"].preis; R.buchungen["B-01"].preis = "100 € (Testwert)";
    const k = reiseKosten(PLAN_FEST).text; R.buchungen["B-01"].preis = alt; return [k, reiseKosten(PLAN_FEST).text]; });
  // Belege (31.10.2026): eine Zeile wie im Postfach, sichtbar ohne Aufklappen; keine Knöpfe ohne Konto (Beleg erfunden)
  await p.evaluate(() => { BL = [{id: "x1", buchung: "B-01", name: "Bestätigung Hotel.pdf", groesse: 2048, wer: "Ida",
    hochgeladen: "2026-10-29T10:00:00", sichtbar: "alle"}]; route(true); });
  await p.waitForSelector(".ebene-nacht #U-01 .beleg");
  a.beleg = await p.evaluate(() => { const z = document.querySelector("[id='B-01'] .beleg");
    return {zugeklappt: !!z.closest("details:not([open])"), art: z.querySelector(".beleg-art").textContent,
      name: z.querySelector("a").textContent, knoepfe: document.querySelectorAll("[id='B-01'] .belege button").length}; });
  await ctx.close();
}
await b.close();
console.log(JSON.stringify({fehler, aus}));
