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
  const vergleich = await p.evaluate(sicht => { const sichtbar = eval(sicht), box = document.querySelector('#main [data-vgl^="V-03"]:not([hidden])');
    if (!box) return null;
    const tab = box.querySelector(".wm-tabelle"), karten = [...box.querySelectorAll(".wm-karte")];
    const werte = vglTeile(box.dataset.vgl);
    // jede Quelle eines gezeigten Werts steht in der Herkunftszeile ihrer Möglichkeit
    const quellenDa = werte.w.optionen.filter(o => box.querySelector(`tr.wm-zeile[data-vgl-zeile$="|${o.id}"]`)).every(o => {
      const zeile = box.querySelector(`tr.wm-zeile[data-vgl-zeile$="|${o.id}"]`), hk = zeile.nextElementSibling;
      const q = Object.values(o.merkmale || {}).flatMap(v => [v, ...(v.je_datum || [])]).map(v => v.quelle).filter(Boolean);
      return !q.length || (hk && hk.classList.contains("wm-herkunft") && q.every(x => hk.textContent.includes(x))); });
    return {id: box.dataset.vgl, tabelle: tab ? sichtbar(tab) : false, karten: karten.filter(sichtbar).length,
      iImVergleich: box.querySelectorAll(":is(.wm-karte, tr.wm-zeile) :is(.mk-i, [data-mk-i], [data-mk-h])").length,
      herkunftKarten: karten.filter(k => k.querySelector(".herkunft")).length, herkunftZeilen: box.querySelectorAll("tr.wm-herkunft").length,
      herkunftText: (box.querySelector(".herkunft") || {}).textContent || "", quellenDa,
      herkunftOhneAufklappen: [...box.querySelectorAll("tr.wm-herkunft")].every(r => !r.hasAttribute("data-vgl-zeile")),
      ueberlauf: document.documentElement.scrollWidth > innerWidth}; }, sicht);
  if (breite === 1300 && vergleich && vergleich.herkunftZeilen) {
    // Sortieren nimmt die Herkunftszeile mit: sie steht danach weiter direkt unter ihrer Möglichkeit
    const box = `#main [data-vgl="${vergleich.id}"]`;
    await p.locator(`${box} [data-vgl-sort]`).nth(1).click(); await p.waitForTimeout(200);
    vergleich.nachSortieren = await p.evaluate(box => { const r = [...document.querySelectorAll(`${box} tr.wm-herkunft`)];
      return r.length > 0 && r.every(x => x.previousElementSibling.classList.contains("wm-zeile")); }, box);
    // Aufgeklappte Einzelheiten gehören zum Vergleich: auch dort kein i (#58)
    await p.locator(`${box} tr.wm-zeile`).first().click({position: {x: 12, y: 12}}); await p.waitForTimeout(200);
    vergleich.aufgeklappt = await p.evaluate(box => ({mehr: document.querySelectorAll(`${box} tr.wm-mehr`).length,
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
