// Klappen starten zu, ein Pfeil für die ganze Seite (#632), aufgerufen von test_klappen_zugeklappt.py.
// Aufruf: node klappen_browser.mjs <playwright-modul> <basis-url>
// Lädt jede Ansicht frisch (ohne gemerkte Zustände, ohne Sprungziel) und meldet die offenen Klappen außerhalb des Kerns,
// die Richtung des Pfeils an Kapiteln und übrigen Klappen (zu und offen), den Zustand der Einzelheiten, der Abschnitte eines
// Wissenstextes, der „Anderen erwogenen Pläne“ und des Wunschformulars sowie die Sprünge in zugeklappte Klappen.
const [, , modul, basis] = process.argv;
const pw = await import(modul);
const b = await pw[process.env.RH_BROWSER || "chromium"].launch();
const fehler = [];
const ctx = await b.newContext({viewport: {width: 1200, height: 900}, serviceWorkers: "block"});
await ctx.route("**/api/**", r => r.abort());   // ohne Rückmeldedienst: keine Wünsche, keine Rückmeldungen
const p = await ctx.newPage();
await p.clock.setFixedTime(new Date("2026-10-27T10:00:00"));
p.on("pageerror", e => fehler.push(`${p.url()}: ${e}`));

// Jede Ansicht frisch laden: about:blank dazwischen, damit nichts aus der vorigen Ansicht bleibt (Seite neu, Speicher leer)
const laden = async h => {
  await p.goto("about:blank");
  await p.goto(basis + (h ? "#" + h : ""));
  await p.waitForSelector("#titel:not(:empty)");
  await p.evaluate(() => { localStorage.clear(); sessionStorage.clear(); });
  await p.goto("about:blank");
  await p.goto(basis + (h ? "#" + h : ""));
  await p.waitForSelector("#titel:not(:empty)");
  await p.waitForTimeout(150);
};

await laden("");
// Ansichten, keine Sprungziele: Reiter, Tage und Abschnitte (ein Block oder ein Ding wäre ein Sprung, der Klappen öffnet)
const ansichten = await p.evaluate(() => {
  const r = new Set(["", "plan", "plaene", "zu-tun", "wissen", "wuensche", "packliste", "etappen"]);
  for (const a of abschnitte) r.add(a.id);
  if (R) { R.tage.forEach(t => r.add(t.id)); Object.keys(R.weitere_tage).forEach(t => r.add(t)); }
  return [...r];
});

// Kern (Product Owner 23.11.2026): das gemerkte Tageskapitel, die Packliste (#511), das Wunschformular mit Entwurf.
// Ohne gemerkten Zustand ist kein Tageskapitel gemerkt; ohne Eingabe gibt es keinen Entwurf.
const regelwidrig = {}, zaehler = {einzelheiten: 0, bloecke: 0, weg: 0, wu_neu: 0};
for (const h of ansichten) {
  await laden(h);
  const r = await p.evaluate(() => {
    const kern = d => d.matches(".pack-klapper");
    const name = d => d.tagName.toLowerCase() + "." + [...d.classList].join(".") + (d.id ? "#" + d.id : "") + " „" +
      ((d.querySelector(":scope > summary") || {}).textContent || "").trim().slice(0, 40) + "“";
    const alle = [...document.querySelectorAll("#main details")];
    return {offen: alle.filter(d => d.open && !kern(d)).map(name),
      einzelheiten: alle.filter(d => d.matches(".einzelheiten")).length, bloecke: alle.filter(d => d.matches(".block")).length,
      weg: alle.filter(d => d.matches(".weg")).length, wu_neu: alle.filter(d => d.matches(".wu-neu")).length};
  });
  if (r.offen.length) regelwidrig[h || "(Start)"] = r.offen;
  for (const k of Object.keys(zaehler)) zaehler[k] += r[k];
}

// Andere erwogene Pläne (AC-5): auch zu, wenn der gezeigte Plan nicht der feste ist
await laden("plaene");
const erwogen = await p.evaluate(() => {
  if (!R || R.plaene.length < 2) return null;
  const fest = R.plaene.find(planFest), anderer = R.plaene.find(x => x !== fest);
  // Die Ansicht der Pläne gibt es nur, solange kein Plan fest ist; gezeichnet wird sie hier direkt, je gezeigtem Plan
  const lesen = id => { const m = document.createElement("div"); VARIANTE = id; ansichtVarianten(m);
    return [...m.querySelectorAll("details.weg")].map(d => d.open); };
  return {mitFest: fest ? lesen(fest.id) : [false], mitAnderem: lesen(anderer.id), alle: lesen("")};
});

// Packliste (AC-8): unverändert wie #511, jede Klappe steht auf ihrer Vorgabe (ohne gemerkte Abweichung)
const packliste = {};
for (const ansicht of ["planen", "packen"]) {
  await laden("packliste");
  packliste[ansicht] = await p.evaluate(async ansicht => {
    const knopf = [...document.querySelectorAll("#main [data-pl-ansicht], #main button")].find(k => (k.dataset.plAnsicht || "") === ansicht);
    if (knopf) { knopf.click(); await new Promise(r => setTimeout(r, 100)); }
    const ds = [...document.querySelectorAll("#main details.pack-klapper")];
    return {n: ds.length, abweichend: ds.filter(d => String(d.open) !== d.dataset.vorgabe).map(d => d.dataset.klapper)};
  }, ansicht);
}

// Pfeil (AC-2): Richtung in Grad (0 = rechts, 90 = unten) aus dem gezeichneten Pfeil und seiner Drehung. Der Pfeil der Kapitel
// ist ein Winkel aus rechtem und unterem Rand (zeigt ungedreht nach rechts unten, 45°); Picos Pfeil ist ein Bild, das ungedreht
// nach unten zeigt (90°).
const richtungJe = async sel => p.evaluate(sel => {
  const d = document.querySelector(sel);
  if (!d) return null;
  // ohne Übergang: sonst zeigt der berechnete Stil direkt nach dem Umschalten noch den alten Winkel
  document.head.append(Object.assign(document.createElement("style"), {textContent: "*,*::after,*::before{transition:none!important}"}));
  const lesen = () => {
    const s = getComputedStyle(d.querySelector(":scope > summary"), "::after");
    const t = s.transform && s.transform !== "none" ? new DOMMatrixReadOnly(s.transform) : new DOMMatrixReadOnly();
    const dreh = Math.atan2(t.b, t.a) * 180 / Math.PI;
    // Ein Randwinkel geht vor: die Kapitel erben Picos Bild, zeichnen aber mit dem Rand
    const winkel = parseFloat(s.borderRightWidth) > 0 && parseFloat(s.borderBottomWidth) > 0 ? 45
      : s.backgroundImage && s.backgroundImage !== "none" ? 90 : null;
    return winkel === null ? null : Math.round(((winkel + dreh) % 360 + 360) % 360);
  };
  const war = d.open;
  d.open = false; const zu = lesen();
  d.open = true; const offen = lesen();
  d.open = war;
  return {zu, offen};
}, sel);
const pfeil = {};
for (const h of ansichten) {
  if (pfeil.kapitel && pfeil.pico) break;
  await laden(h);
  if (!pfeil.kapitel) pfeil.kapitel = await richtungJe("#main details.kapitel");
  if (!pfeil.pico) pfeil.pico = await richtungJe("#main details:not(.kapitel):not(.pack-klapper)");
}

// Einzelheiten (AC-3): an jedem Tag zu, ob gebucht oder nicht; Name, Stand und Buchen-Handlung stehen außerhalb sichtbar
const einzelheiten = [];
for (const h of ansichten.filter(x => /^T-/.test(x))) {
  await laden(h);
  einzelheiten.push(...await p.evaluate(h => [...document.querySelectorAll("#main details.einzelheiten")].map(d => {
    // nächster Behälter: die Zeile (.z, etwa eine Strecke im Wegverlauf des Tageskastens), die Buchung oder die Karte
    const karte = d.closest(".z, .karte, .buchung") || d.parentElement;
    const aussen = [...karte.children].filter(x => x !== d && !x.contains(d)).map(x => x.textContent).join(" ").trim();
    return {tag: h, offen: d.open, buchung: !!d.closest(".buchung"), aussen: aussen.length > 0};
  }), h));
}

// Wunschformular (AC-6): ohne Wunsch und ohne Entwurf zu; mit angefangenem Entwurf offen, auch nach neuem Zeichnen
const wunsch = {};
await laden("wuensche");
wunsch.da = await p.evaluate(() => !!document.querySelector("#main details.wu-neu"));
if (wunsch.da) {
  wunsch.ohne = await p.evaluate(() => document.querySelector("#main details.wu-neu").open);
  await p.evaluate(() => { document.querySelector("#main details.wu-neu").open = true; });
  await p.fill("#wuText", "Einmal am See frühstücken (Beispielwert)");
  await p.evaluate(() => { location.hash = "wissen"; });
  await p.waitForTimeout(100);
  await p.evaluate(() => { location.hash = "wuensche"; });
  await p.waitForTimeout(100);
  wunsch.mit = await p.evaluate(() => (document.querySelector("#main details.wu-neu") || {}).open);
}

// Sprünge (AC-7): Ein Sprung auf einen Eintrag in zugeklappten Klappen öffnet alle umgebenden und zeigt das Ziel
const sprung = {};
const umgebung = () => {
  const ziel = document.getElementById(window.__ziel);
  if (!ziel) return null;
  const zu = [];
  for (let x = ziel.parentElement; x; x = x.parentElement) if (x.tagName === "DETAILS" && !x.open) zu.push(x.className);
  const sichtbar = ziel.checkVisibility ? ziel.checkVisibility() : !!ziel.getClientRects().length;
  return {zu, sichtbar};
};
// a) Hash auf einen Eintrag in den Einzelheiten eines Tags (Kennung zur Probe gesetzt, die Seite springt wie bei jedem Ziel)
for (const h of ansichten.filter(x => /^T-/.test(x))) {
  await laden(h);
  const ok = await p.evaluate(() => {
    const d = document.querySelector("#main details.einzelheiten");
    const x = d && d.querySelector(":scope > :not(summary)");
    if (!x) return false;
    d.open = false; x.id = "probe-632"; window.__ziel = "probe-632"; zumZiel("probe-632");
    return true;
  });
  if (ok) { sprung.einzelheiten = await p.evaluate(umgebung); break; }
}
// b) Hash auf einen Abschnitt eines Wissenstextes (Block): die Seite lädt mit dem Ziel in der Adresse
const blockId = await p.evaluate(() => { for (const a of abschnitte) if (a.typ !== "ort" && a.bloecke.length > 1) return a.bloecke[1].id; return null; });
if (blockId) {
  await laden(blockId);
  sprung.hash = await p.evaluate(id => { window.__ziel = id; const d = document.getElementById(id); return d ? {offen: d.tagName !== "DETAILS" || d.open} : null; }, blockId);
  if (sprung.hash) sprung.hash = {...sprung.hash, ...await p.evaluate(umgebung)};
}
// c) „zu buchen“: der Link zur Liste der Buchungen öffnet sie
await laden("zu-buchen");
sprung.zu_buchen = await p.evaluate(() => { const d = document.getElementById("zu-buchen"); return d ? {da: true, offen: d.tagName !== "DETAILS" || d.open} : {da: false}; });
// d) Suche: ein Treffer auf einen Block führt hin und öffnet ihn
if (blockId) {
  await laden("");
  const titel = await p.evaluate(id => { for (const a of abschnitte) for (const x of a.bloecke) if (x.id === id) return x.titel; return ""; }, blockId);
  const wort = (titel.match(/[A-Za-zÄÖÜäöüß]{5,}/) || [""])[0];
  if (wort) {
    await p.click("#suchKnopf");
    await p.fill("#suche", wort);
    await p.waitForTimeout(400);
    const link = p.locator(`#main a[href="#${blockId}"]`).first();
    if (await link.count()) {
      await link.click();
      await p.waitForTimeout(300);
      sprung.suche = await p.evaluate(id => { window.__ziel = id; const d = document.getElementById(id); return d ? {offen: d.tagName !== "DETAILS" || d.open} : null; }, blockId);
      if (sprung.suche) sprung.suche = {...sprung.suche, ...await p.evaluate(umgebung)};
    }
  }
}

await b.close();
console.log(JSON.stringify({fehler, ansichten, regelwidrig, zaehler, pfeil, einzelheiten, wunsch, sprung, packliste, erwogen}));
