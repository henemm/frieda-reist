// Rundgang durch alle Ansichten einer gebauten Reise (Designsystem, frieda-reist#18), aufgerufen von test_seite.py.
// Aufruf: node seiten_browser.mjs <playwright-modul> <basis-url> [dom-datei]
// Öffnet jede Route (Reiter, Tage, Wahlstellen, Optionen, Unterkünfte, Pläne, Abschnitte, Fragen, Bausteinseite) bei 390
// und 1200 px und meldet Skriptfehler, leere Ansichten und Ansichten, die auf dem Handy seitlich überstehen. Mit dom-datei
// wird zusätzlich das HTML jeder Ansicht gespeichert, ohne Karteninhalt (der lädt zeitversetzt): So lässt sich vor und
// nach einem Umbau prüfen, ob die Seite gleich bleibt. Mit RH_BILDER=<ordner> entstehen Bilder der Bausteinseite
// (Handy und Rechner, hell und dunkel) zur Durchsicht.
import fs from "node:fs";
import {bild} from "./bild.mjs";

const [, , modul, basis, domDatei] = process.argv;
const pw = await import(modul);
const b = await pw[process.env.RH_BROWSER || "chromium"].launch();
const fehler = [], leer = [], breit = [], dom = {}, vergleich = {}, bilder = [], bilderFehlen = [], ohneArt = [], schrift = {};
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
    const r = new Set(["", "plan", "varianten", "plaene", "zu-tun", "wissen", "etappen", "wuensche", "orte", "praxis", "quellen", "fragen", "aufgaben", "rueckmeldungen", "bausteine"]);
    for (const a of abschnitte) { r.add(a.id); for (const x of a.bloecke) r.add(x.id); }
    if (R) {
      R.tage.forEach(t => r.add(t.id)); Object.keys(R.weitere_tage).forEach(t => r.add(t)); Object.keys(R.unterkuenfte).forEach(u => r.add(u));
      R.wahlstellen.forEach(v => { r.add(v.id); v.optionen.forEach(o => r.add(o.id)); }); R.plaene.forEach(x => r.add(x.id));
      Object.keys(R.buchungen || {}).forEach(b => r.add(b));
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
    // Schriftleiter: jeder sichtbare Text hat eine der fünf Stufen (Größe geteilt durch die Wurzel); Ausnahmen sind Karte,
    // Leiste, Ziffer der Tagesnummer und Hochzahlen
    for (const [v, wo] of Object.entries(await p.evaluate(() => {
      const w = parseFloat(getComputedStyle(document.documentElement).fontSize), stufen = ["--t-titel", "--t-untertitel", "--t-text", "--t-klein", "--t-etikett"]
        .map(t => parseFloat(getComputedStyle(document.documentElement).getPropertyValue(t))), aus = {};
      for (const e of document.querySelectorAll("body *")) {
        if (e.closest(".leaflet-container, svg, nav, #suchKnopf, .tagnr, sup, script, style")) continue;
        if (![...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())) continue;
        const r = e.getBoundingClientRect(); if (!r.width || !r.height) continue;
        const v = parseFloat(getComputedStyle(e).fontSize) / w;
        if (!stufen.some(s => Math.abs(s - v) < 0.002)) aus[v.toFixed(4)] = e.tagName.toLowerCase() + "." + [...e.classList].join(".");
      }
      return aus; }))) schrift[v] = `${breite}#${h} ${wo}`;
  }
  // Ontologie: jede Kennung der Reise gehört einer Art mit Bausteinen an
  if (breite === 390) ohneArt.push(...await p.evaluate(() => {
    const ids = [...abschnitte.flatMap(a => [a.id, ...a.bloecke.map(x => x.id)]), ...D.fragen.zeilen.map(z => z.id),
      ...(R ? [...R.tage.map(t => t.id), ...Object.keys(R.weitere_tage), ...Object.keys(R.unterkuenfte), ...Object.keys(R.strecken), ...Object.keys(R.orte),
        ...R.wahlstellen.flatMap(v => [v.id, ...v.optionen.map(o => o.id)]), ...R.plaene.map(x => x.id),
        ...Object.keys(R.aufenthalte || {}), ...Object.keys(R.buchungen || {})] : []), ...PL_JE.keys()];   // auch Gegenstände (#543)
    const formen = new Set(GRUNDFORMEN.map(o => o[0]));
    return ids.filter(i => !formen.has(grundformVon(i)));
  }));
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
    // Handy: Karten (höchstens 2); Rechner: Tabelle mit je Möglichkeit einer Zeile, alle gültigen (29.10.2026)
    const spalten = await box.locator(breite < 700 ? ".wm-karte" : "tbody tr.wm-zeile").count();
    let sortiert = null, aufgeklappt = null, falscheSpalten = null, einzelheiten = null;
    if (breite >= 700) {
      // Spalten nur für Merkmale der Stufe pflicht oder empfohlen (angeboten steht in den Einzelheiten, aus nirgends)
      falscheSpalten = await p.evaluate(id => { const w = vglTeile(id).w;
        const nicht = new Set(w.kriterien.filter(k => !["pflicht", "empfohlen"].includes(stufeVon(k))).map(k => k.name));
        const pe = w.kriterien.some(k => ["pflicht", "empfohlen"].includes(stufeVon(k)) && w.optionen.some(o => o.merkmale[k.id]));
        return pe ? [...document.querySelectorAll(`#main [data-vgl="${CSS.escape(id)}"] thead th`)].map(th => th.textContent.trim()).filter(t => nicht.has(t)) : []; }, id);
      await box.locator("[data-vgl-sort]").first().click();
      sortiert = await p.locator(`#main [data-vgl="${id}"] th[aria-sort]`).count();
      // erst in Sicht holen und die Lage messen: sonst zählt das Scrollen des Klicks als Springen (wackelte unter Last in CI)
      const zeile = p.locator(`#main [data-vgl="${id}"] tr.wm-zeile`).first();
      await zeile.scrollIntoViewIfNeeded();
      await p.evaluate(() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))));
      const yVor = (await zeile.boundingBox()).y;
      await zeile.click({position: {x: 12, y: 12}});
      aufgeklappt = await p.locator(`#main [data-vgl="${id}"] tr.wm-mehr`).count();
      // Aufklappen lässt die Zeile stehen, wo sie war; die Einzelheiten wiederholen weder Name noch Zustand, kein Fehlertext,
      // keine internen Nummern; der Wert ist aufrecht und zeigt seine Herkunft beim Darüberfahren (kein „i“ mehr, #58)
      einzelheiten = await p.evaluate(id => { const m = document.querySelector(`#main [data-vgl="${CSS.escape(id)}"] tr.wm-mehr`), t = m.textContent;
        const i = document.querySelector("#main .mk-w");
        return {doppelt: m.querySelectorAll(".option, .chip, .k").length, fehlertext: /\[object |undefined|NaN/.test(t), nummern: /\b[AR]-\d{8}/.test(t),
          kursiv: i ? getComputedStyle(i).fontStyle : "normal", iKnoepfe: document.querySelectorAll("#main .mk-i").length, ohneNummern: ohneNummern("Auftrag A-20261029-065303-b061 aus der Claude-App") + "|" + ohneNummern("zu teuer – Auftrag A-20261029-065303-b061 aus der Claude-App")}; }, id);
      einzelheiten.springt = Math.abs((await zeile.boundingBox()).y - yVor) > 1;
      const i = p.locator(`#main [data-vgl="${id}"] .mk-w`).first();
      if (await i.count()) { await i.scrollIntoViewIfNeeded(); await p.waitForTimeout(100); await i.hover();
        einzelheiten.herkunft = await i.evaluate(x => !x.nextElementSibling.hidden && x.nextElementSibling.textContent.length > 0); await p.mouse.move(1, 1); }
    }
    await p.locator(`#main [data-vgl="${id}"] [data-vgl-nur]`).first().check();
    vergleich[breite] = {route: h, sichtbar, spalten, sortiert, aufgeklappt, falscheSpalten, einzelheiten, offen: await p.locator(`[data-vgl-auf="${id}"]`).first().getAttribute("aria-expanded")};
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
    // Chromium nimmt nichts über 32767 Pixel auf (die Bausteinseite wächst mit jedem Baustein): dann die ersten 32000
    const hoehe = await p.evaluate(() => document.documentElement.scrollHeight);
    // Mit Wiederholung (#537); scheitert das Bild endgültig, nennt die Ausgabe die Datei in bilderFehlen (Warnung, nicht rot)
    if (await bild(p, hoehe > 32000 ? {path: datei, fullPage: true, clip: {x: 0, y: 0, width: breite, height: 32000}} : {path: datei, fullPage: true})) bilder.push(datei);
    else bilderFehlen.push(datei.split("/").pop());
  }
  await ctx.close();
}
// Höhe als App vom Home-Bildschirm: iOS vergisst nach der Tastatur die volle Höhe. Nachgestellt durch ein kleineres
// Fenster; gemessen wird der untere Rand der Leiste (soll: ganz unten, außer mit Tastatur, und nur als App).
const leiste = {};
for (const app of [true, false]) {
  const ctx = await b.newContext({viewport: {width: 390, height: 800}, serviceWorkers: "block"});
  await ctx.route("**/api/**", r => r.abort());
  if (app) await ctx.addInitScript(() => {
    const mm = window.matchMedia.bind(window);
    window.matchMedia = q => /display-mode:\s*standalone/.test(q) ? {matches: true, media: q, addEventListener() {}, removeEventListener() {}} : mm(q);
  });
  const p = await ctx.newPage();
  p.on("pageerror", e => fehler.push(`Leiste app=${app}: ${e}`));
  await p.goto(basis);
  await p.waitForSelector("#titel:not(:empty)");
  // Gemessen wird erst, wenn die Lage ruhig ist: das Fenster hat die neue Höhe und der untere Rand der Leiste steht
  // drei Bilder lang still. Unter Last verarbeitet WebKit die Größenänderung sonst erst nach der Messung (#159).
  const unten = () => p.evaluate(() => new Promise(fertig => {
    const rand = () => Math.round(document.querySelector(".leiste").getBoundingClientRect().bottom);
    let vor = rand(), still = 0;
    const ende = setTimeout(() => fertig(rand()), 3000);
    const bild = () => {
      const jetzt = rand();
      still = jetzt === vor ? still + 1 : 0;
      vor = jetzt;
      if (still >= 3) { clearTimeout(ende); fertig(jetzt); } else requestAnimationFrame(bild);
    };
    requestAnimationFrame(bild);
  }));
  const hoehe = async h => {
    await p.setViewportSize({width: 390, height: h});
    await p.waitForFunction(h => window.innerHeight === h, h);
  };
  const m = {start: await unten()};
  await hoehe(500);
  m.klein = await unten();
  await p.evaluate(() => document.querySelector("#suchKnopf").click());
  m.tippt = await unten();
  await p.evaluate(() => document.activeElement && document.activeElement.blur());
  await p.waitForTimeout(500);   // die Vorlage misst nach dem Verlassen eines Felds nach 50 und 400 ms
  m.zu = await unten();
  await hoehe(800);
  m.voll = await unten();
  // Wackelkontakt (Foto 7.11.2026): innerHeight meldet kurz zu wenig, obwohl das Fenster und die Leiste stimmen; die Leiste
  // darf dann nicht aus dem Bild rücken. Nachgestellt, indem nur innerHeight lügt (das Fenster bleibt 800 hoch).
  await p.evaluate(() => { Object.defineProperty(window, "innerHeight", {get: () => 740, configurable: true}); dispatchEvent(new Event("resize")); });
  await p.waitForTimeout(100);
  m.luege = await unten();
  await p.evaluate(() => { delete window.innerHeight; dispatchEvent(new Event("resize")); });
  leiste[app ? "app" : "browser"] = m;
  await ctx.close();
}
// Behälter (#332, Schritt D): kein seitlicher Überstand bei allen sechs Breiten (der Rundgang oben deckt 390 und 1200 ab), und die
// schmale Spalte am Rechner: bei 1300 px Fenster richten sich Vergleich und Kennzahlen nach ihrem Behälter, hier künstlich 340 px breit
const behaelter = {ueberstand: [], spalte: {}};
for (const breite of [320, 700, 900, 1100, 1300]) {
  const ctx = await b.newContext({viewport: {width: breite, height: 900}, serviceWorkers: "block"});
  await ctx.route("**/api/**", r => r.abort());
  const p = await ctx.newPage();
  await p.clock.setFixedTime(new Date("2026-10-27T10:00:00"));
  p.on("pageerror", e => fehler.push(`${breite} Behälter: ${e}`));
  await p.goto(basis);
  await p.waitForSelector("#titel:not(:empty)");
  await p.waitForTimeout(300);
  const routen = await p.evaluate(() => ["", "plan", "etappen", "varianten", "zu-tun", "wuensche", ...(R ? [...R.tage.map(t => t.id), ...R.wahlstellen.map(v => v.id)] : [])]);
  let offen = null;
  for (const h of routen) {
    await p.evaluate(h => { location.hash = h; }, h);
    await p.waitForTimeout(15);
    const knopf = p.locator('#main [data-vgl-auf][aria-expanded="false"]:visible').first();
    if (await knopf.count() && !offen) { offen = await knopf.getAttribute("data-vgl-auf"); await knopf.click(); await p.waitForTimeout(100); }
    if (await p.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1)) behaelter.ueberstand.push(`${breite}#${h}`);
  }
  if (breite === 1300 && offen) {
    const m = await p.evaluate(async id => {
      const box = document.querySelector(`#main [data-vgl="${CSS.escape(id)}"]`), host = document.createElement("div");
      host.id = "schmaleSpalte"; host.style.width = "340px";
      box.parentElement.insertBefore(host, box); host.append(document.querySelector(`[data-vgl-auf="${CSS.escape(id)}"]`) || "", box);
      await new Promise(r => setTimeout(r, 300));
      const w = document.querySelector(`[data-vgl="${CSS.escape(id)}"]`), an = x => { const e = w.querySelector(x); return e ? getComputedStyle(e).display : null; };
      return {karten: w.querySelectorAll(".wm-karte").length, tabelle: an(".wm-tabelle"), umschalter: an(".wm-ansicht"), ueberstand: host.scrollWidth > host.clientWidth + 1, breite: Math.round(host.getBoundingClientRect().width)};
    }, offen);
    behaelter.spalte.vergleich = m;
    for (const h of routen) {
      await p.evaluate(h => { location.hash = h; }, h);
      await p.waitForTimeout(15);
      const k = await p.evaluate(() => { const e = document.querySelector("#main .kz-huelle"); if (!e) return null; const kz = e.querySelector(".kz"), vor = getComputedStyle(kz).gridTemplateColumns.split(" ").length;
        e.style.width = "340px"; return {breiteVor: Math.round(e.parentElement.getBoundingClientRect().width), spaltenVor: vor, spaltenNach: getComputedStyle(kz).gridTemplateColumns.split(" ").length, kacheln: kz.children.length}; });
      if (k) { behaelter.spalte.kennzahlen = k; break; }
    }
  }
  await ctx.close();
}
await b.close();
if (domDatei) fs.writeFileSync(domDatei, JSON.stringify(dom));
console.log(JSON.stringify({routen: Object.keys(dom).length, leer, breit, fehler, vergleich, bilder, bilderFehlen, leiste, ohneArt, schrift, behaelter}));
