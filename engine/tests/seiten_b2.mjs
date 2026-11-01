// B2 auf Reise, Ort, Wissen und Vergleich (frieda-reist#58), aufgerufen von test_b2_ansichten.py.
// Aufruf: node seiten_b2.mjs <playwright-modul> <basis-url>
// <basis>/fest/ ist die Beispielreise mit Plan A, <basis>/offen/ dieselbe mit offener Nacht in Hohnstein.
// Meldet je Ansicht und Breite: Kästen, Überstand und was die Entscheidungen vom 1.11.2026 verlangen.
const [, , modul, basis] = process.argv;
const pw = await import(modul);
const b = await pw[process.env.RH_BROWSER || "chromium"].launch();
const fehler = [], aus = {};
// Kasten: Rahmen oder Schatten, Radius ab 6 px, höher als 60 px (dasselbe Maß wie beim Befund)
const kaesten = wurzel => [wurzel, ...wurzel.querySelectorAll("*")].filter(e => {
  const r = e.getBoundingClientRect(), s = getComputedStyle(e);
  return r.height > 60 && r.width > 0 && s.visibility !== "hidden" && (parseFloat(s.borderTopWidth) > 0 || s.boxShadow !== "none")
    && parseFloat(s.borderTopLeftRadius) >= 6 && !e.closest(".kartenbox, .leaflet-container");
}).map(e => e.className || e.tagName);
for (const breite of [390, 820, 1300]) {
  const ctx = await b.newContext({viewport: {width: breite, height: 900}, serviceWorkers: "block"});
  await ctx.route("**/api/**", r => r.abort());
  const p = await ctx.newPage();
  p.on("pageerror", e => fehler.push(`${breite}: ${e}`));
  const geh = async (pfad) => { await p.goto(basis + pfad); await p.waitForSelector("#main *"); await p.waitForTimeout(150); };
  const a = aus[breite] = {};
  const ueber = () => p.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1);
  // Reise: An- und Abreise als Zeile, kein Kasten
  await geh("fest/#reise");
  a.reise = await p.evaluate(`({anab: [...document.querySelectorAll(".anab")].map(x => x.classList.contains("karte")),
    kaesten: (${kaesten})(document.querySelector("#main")).filter(k => /anab/.test(k)).length})`);
  // Ortsseite: Abschnitte als Lesetext, offen, ohne Rahmen; die Sprechblase steht im Kopf jedes Abschnitts
  await geh("fest/#O-01");
  a.ort = await p.evaluate(`({bloecke: document.querySelectorAll("#main details.block").length,
    lesen: [...document.querySelectorAll("#main .lese-abschnitt")].map(x => [x.querySelector("h4").textContent, !!x.querySelector(".lese-kopf .zid-box")]),
    kaesten: (${kaesten})(document.querySelector("#main")).length})`);
  a.ort.ueber = await ueber();
  // Wissen: Weitere Wege als Listenzeilen, ohne Kacheln
  await geh("fest/#wissen");
  // Weitere Wege in der Wegtabelle (#58): am Rechner Tabelle, sonst je Weg ein Eintrag mit Zahlenzeile
  a.wissen = await p.evaluate(`({wege: [...document.querySelectorAll("#main .wege tbody tr")]
      .map(x => [x.querySelector("a").getAttribute("href"), x.textContent.replace(/\\s+/g, " ")]),
    kopf: (e => !!e && getComputedStyle(e).display !== "none")(document.querySelector("#main .wege thead")),
    kacheln: document.querySelectorAll("#main .kz").length, bloecke: document.querySelectorAll("#main details.block").length,
    kaesten: (${kaesten})(document.querySelector("#main")).length})`);
  // Vergleich (offene Nacht in Hohnstein): ohne Rahmen um die Wahlstelle, Herkunft hinter dem Wert,
  // Tabelle nur am Rechner, Frage mit Namen
  await geh("offen/#T-02");
  const nacht = "#main .ebene-nacht";
  a.vergleich = await p.evaluate(`(() => { const n = document.querySelector("${nacht}"), m = n.querySelector(".wahl-modul"), s = getComputedStyle(m);
    const sicht = e => !!e && e.getClientRects().length > 0 && getComputedStyle(e).display !== "none";
    return {rahmen: parseFloat(s.borderTopWidth) > 0 || s.boxShadow !== "none", i: n.querySelectorAll(".mk-i").length, werte: [...n.querySelectorAll(":is(.wm-tabelle, .wm-karten) [data-mk-i]")].filter(sicht).length, herkunft: [...n.querySelectorAll(".herkunft")].filter(sicht).length,
      tabelle: sicht(n.querySelector(".wm-tabelle")), karten: sicht(n.querySelector(".wm-karten")), umschalter: sicht(n.querySelector(".wm-ansicht")),
      einzeln: sicht(n.querySelector("details.wm-einzeln")), kennung: /\\bF-\\d/.test(n.textContent), frage: (n.querySelector('a[href="#F-02"]') || {}).textContent || null,
      kaesten: (${kaesten})(n).filter(k => !/wm-karte|wm-einzeln/.test(k))}; })()`);
  a.vergleich.ueber = await ueber();
  // Herkunft am Wert außerhalb des Vergleichs (gewählte Unterkunft): Tippen öffnet das Fenster und hält es offen;
  // am Rechner reicht Darüberfahren
  await geh("fest/#T-02");
  const wert = p.locator(`${nacht} button.mk-w:visible`).first();
  await wert.scrollIntoViewIfNeeded();
  if (breite >= 1100) { await wert.hover(); a.vergleich.hover = await wert.evaluate(x => !x.nextElementSibling.hidden); await p.mouse.move(1, 1); }
  await wert.click();
  a.vergleich.tippen = await wert.evaluate(x => [x.getAttribute("aria-expanded"), !x.nextElementSibling.hidden, x.nextElementSibling.textContent]);
  a.vergleich.tippenText = await wert.evaluate(x => x.textContent);
  await ctx.close();
}
await b.close();
console.log(JSON.stringify({fehler, aus}));
