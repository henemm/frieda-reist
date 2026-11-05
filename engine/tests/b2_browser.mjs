// B2 auf Wissen, Orte und Vergleich (#58), aufgerufen von test_seite.py mit der Beispielreise (Plan A fest).
// Aufruf: node b2_browser.mjs <playwright-modul> <basis-url> <datum>
// Meldet je Breite (Handy 390, Tablet 820, Rechner 1300): Weitere Wege (Tabelle oder Einträge, keine Kacheln, kein
// Überlauf), Ortsseite (Ebenen ohne Kasten, Lesespalte) und Vergleich V-03 (kein i, Herkunft je Möglichkeit, Tabelle nur
// am Rechner).
const [, , modul, basis, datum] = process.argv;
const pw = await import(modul);
const b = await pw[process.env.RH_BROWSER || "chromium"].launch();
const fehler = [], aus = {};
for (const [breite, hoehe] of [[390, 844], [820, 1180], [1300, 900]]) {
  const ctx = await b.newContext({viewport: {width: breite, height: hoehe}, serviceWorkers: "block"});
  await ctx.route("**/api/**", r => r.abort());
  const p = await ctx.newPage();
  p.on("pageerror", e => fehler.push(String(e)));
  await p.clock.setFixedTime(new Date(datum + "T10:00:00"));
  const auf = async h => { await p.goto(basis + "#" + h); await p.waitForSelector("#titel:not(:empty)"); await p.waitForTimeout(300); };
  const sicht = "(e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; })";
  await auf("wissen");
  const wege = await p.evaluate(sicht => { const sichtbar = eval(sicht), w = document.querySelector("#main .wege");
    if (!w) return null;
    return {zeilen: w.querySelectorAll("tbody tr").length, kopf: sichtbar(w.querySelector("thead")), kacheln: w.querySelectorAll(".kz").length,
      // die Seite scrollt nicht seitwärts, und am Rechner scrollt die Tabelle nicht in sich (am Handy ist die Hülle offen)
      ueberlauf: document.documentElement.scrollWidth > innerWidth || (getComputedStyle(w).overflowX !== "visible" && w.scrollWidth > w.clientWidth + 1),
      seite: [document.documentElement.scrollWidth, innerWidth, getComputedStyle(w).overflowX, w.scrollWidth, w.clientWidth],
      zahlen: [...w.querySelectorAll("tbody tr:first-child td:not(.leer)")].map(td => td.textContent),
      links: [...w.querySelectorAll("tbody th a[href^='#E-']")].length, kartenMitKacheln: document.querySelectorAll("#main a.karte .kz").length}; }, sicht);
  await auf("O-01");
  const ort = await p.evaluate(sicht => { const sichtbar = eval(sicht), s = document.querySelector("#main .lese-spalte");
    return {spalte: !!s, abschnitte: s ? s.querySelectorAll(".lese-abschnitt").length : 0, kaesten: document.querySelectorAll("#main details.block").length,
      breite: s ? Math.round(s.getBoundingClientRect().width) : 0, allesSichtbar: s ? [...s.querySelectorAll(".lese-abschnitt")].every(sichtbar) : false}; }, sicht);
  await auf("V-03");
  if (!await p.locator('#main [data-vgl^="V-03"]:not([hidden])').count()) { const k = p.locator('#main [data-vgl-auf^="V-03"]:visible'); if (await k.count()) { await k.first().click(); await p.waitForTimeout(300); } }
  // Der Vergleich richtet sich nach der Breite seines Behälters, nicht des Fensters (#332, Schritt D; Entscheidung des Product Owners
  // 5.11.2026, Option B): V-03 steht auf der Tagesseite in einer Spalte unter 960 px, also zeigt er auch am Rechner Karten, dazu mit
  // Maus den Umschalter „Tabelle“. Für die Bedienung der Tabelle (sortieren, aufklappen) wird in der Spalte umgeschaltet.
  let inSpalte = null;
  if (breite === 1300) {
    inSpalte = await p.evaluate(() => { const box = document.querySelector('#main [data-vgl^="V-03"]:not([hidden])');
      if (!box) return null;
      const t = box.querySelector(".wm-tabelle"), u = box.querySelector(".wm-ansicht");
      return {breite: Math.round(box.getBoundingClientRect().width), tabelle: !!t && getComputedStyle(t).display !== "none", karten: box.querySelectorAll(".wm-karte").length,
        umschalter: !!u && getComputedStyle(u).display !== "none"}; });
    const tab = p.locator('#main [data-vgl^="V-03"]:not([hidden]) [data-vgl-ansicht$="|tabelle"]:visible');
    if (await tab.count()) { await tab.first().click(); await p.waitForTimeout(400); }
  }
  const vergleich = await p.evaluate(sicht => { const sichtbar = eval(sicht), box = document.querySelector('#main [data-vgl^="V-03"]:not([hidden])');
    if (!box) return null;
    const tab = box.querySelector(".wm-tabelle"), karten = [...box.querySelectorAll(".wm-karte")];
    const werte = vglTeile(box.dataset.vgl);
    return {id: box.dataset.vgl, tabelle: tab ? sichtbar(tab) : false, karten: karten.filter(sichtbar).length,
      iImVergleich: box.querySelectorAll(":is(.wm-karte, tr.wm-zeile) :is(.mk-i, [data-mk-i], [data-mk-h])").length,
      // #342: die Herkunft steht nie als eigene Zeile oder offen im Vergleich; Karte: zugeklappt hinter „Herkunft“, Tabelle: in den Einzelheiten
      herkunftKarten: karten.filter(k => k.querySelector("details.wm-herkunft:not([open]) .herkunft")).length, herkunftZeilen: box.querySelectorAll("tr.wm-herkunft").length,
      herkunftOffenZugeklappt: [...box.querySelectorAll(".wm-tab .herkunft")].length,
      // #343: das Hero-Merkmal ist keine Spalte, sondern steht in jeder Möglichkeit ganz oben über alle Spalten (Tabelle: Zeile unter der Möglichkeit, Karte: unter dem Namen)
      heroZeilen: [...box.querySelectorAll("tr.wm-hero")].map(r => [r.querySelector("td").colSpan, r.previousElementSibling.classList.contains("wm-zeile"),
        r.querySelector(".hero-name").textContent, r.querySelector(".hero-text").textContent.length > 10, r.querySelectorAll("td").length]),
      heroSpalte: [...box.querySelectorAll(".wm-tab thead th")].some(t => /Einschätzung/.test(t.textContent)),
      spaltenZahl: box.querySelectorAll(".wm-tab thead th").length,
      heroKarten: karten.filter(k => k.querySelector(".hero .hero-text")).length,
      heroKartenOben: karten.every(k => !k.querySelector(".hero") || k.querySelector(".hero").previousElementSibling.classList.contains("chips") || k.querySelector(".hero").previousElementSibling.classList.contains("k")),
      herkunftText: (box.querySelector(".wm-karte details.wm-herkunft .herkunft") || {}).textContent || "",
      ueberlauf: document.documentElement.scrollWidth > innerWidth}; }, sicht);
  if (vergleich) vergleich.inSpalte = inSpalte;
  if (breite === 1300 && vergleich) {
    const box = `#main [data-vgl="${vergleich.id}"]`;
    // Aufgeklappte Einzelheiten gehören zum Vergleich: auch dort kein i (#58)
    await p.locator(`${box} tr.wm-zeile`).first().click({position: {x: 12, y: 12}}); await p.waitForTimeout(200);
    vergleich.aufgeklappt = await p.evaluate(box => ({mehr: document.querySelectorAll(`${box} tr.wm-mehr`).length,
      // die Herkunft aller Quellen der Möglichkeit steht jetzt in ihren aufgeklappten Einzelheiten (#342)
      herkunft: (() => { const z = document.querySelector(`${box} tr.wm-zeile.auf`), h = document.querySelector(`${box} tr.wm-mehr .herkunft`);
        const o = vglTeile(document.querySelector(box).dataset.vgl).w.optionen.find(x => z && z.dataset.vglZeile.endsWith("|" + x.id));
        const q = Object.values((o && o.merkmale) || {}).flatMap(v => [v, ...(v.je_datum || [])]).map(v => v.quelle).filter(Boolean);
        return !!h && h.textContent.startsWith("Quellen: ") && q.every(x => h.textContent.includes(x)); })(),
      iImKasten: document.querySelectorAll(`${box} :is(.wm-tabelle, .wm-karten) :is(.mk-i, [data-mk-i], [data-mk-h])`).length}), box);
    // Knöpfe im Kasten nach Art (für die Abnahme-Seite)
    vergleich.knopfArten = await p.evaluate(box => { const n = {};
      for (const x of document.querySelectorAll(`${box} :is(button, summary, a.zid, .zid)`)) { const r = x.getBoundingClientRect();
        if (r.width && r.height) { const k = x.className || x.tagName; n[k] = (n[k] || 0) + 1; } } return n; }, box);
  }
  aus[breite] = {wege, ort, vergleich};
  await ctx.close();
}
await b.close();
console.log(JSON.stringify({fehler, ...aus}));
