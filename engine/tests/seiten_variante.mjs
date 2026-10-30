// Seite einer abgewandelten Beispielreise prüfen (Verhalten je Status und Bausteine, Paket B), aufgerufen von test_seite.py.
// Aufruf: node seiten_variante.mjs <playwright-modul> <basis-url> <datum JJJJ-MM-TT>
// Meldet: Reiter der Leiste, aktiver Reiter beim Start, Überschrift des Heute-Blocks, Zahl der Rückmeldeknöpfe an IDs,
// Buchung B-01, stornierte Buchungen am Ding (#146), Zeile „Alle Möglichkeiten“, Skriptfehler.
const [, , modul, basis, datum] = process.argv;
const pw = await import(modul);
const b = await pw[process.env.RH_BROWSER || "chromium"].launch();
const ctx = await b.newContext({viewport: {width: 390, height: 900}, serviceWorkers: "block"});
await ctx.route("**/api/**", r => r.abort());
const p = await ctx.newPage();
const fehler = [];
p.on("pageerror", e => fehler.push(String(e)));
await p.clock.setFixedTime(new Date(`${datum}T10:00:00`));
await p.goto(basis);
await p.waitForSelector("#titel:not(:empty)");
await p.waitForTimeout(300);
const start = await p.evaluate(() => ({
  reiter: [...document.querySelectorAll("#nav a")].map(a => a.getAttribute("href").slice(1)),
  aktiv: (document.querySelector("#nav a.on") || {getAttribute: () => "#"}).getAttribute("href").slice(1),
  heute: (document.querySelector("section.heute h2") || {}).textContent || null,
}));
// Rückmeldeknöpfe an IDs im Plan (ohne Baustein „rueckmeldungen“ und „aufgaben“ nur Text)
await p.evaluate(() => { location.hash = "plan"; });
await p.waitForTimeout(200);
start.knoepfe = await p.evaluate(() => document.querySelectorAll("#main button.zid").length);
start.kennungen = await p.evaluate(() => document.querySelectorAll("#main .zid").length);
// Sichtbar: im Layout und in keinem zugeklappten details. Chromium und WebKit blenden den Inhalt eines zugeklappten details
// nicht per display:none aus, offsetParent allein bleibt dort gesetzt (wie seiten_tagesseite.mjs).
await p.evaluate(() => { window.sichtbar = e => { if (!e || !e.offsetParent) return false;
  for (let d = e.parentElement && e.parentElement.closest("details"); d; d = d.parentElement && d.parentElement.closest("details"))
    if (!d.open) return false;
  return true; }; });
// Buchung (B-…, #76): ihr Block ist unter #B-01 bei ihrem Ding erreichbar, auch bei einer Reise ohne Tagesseiten (ADR-0003)
await p.evaluate(() => { location.hash = "B-01"; });
await p.waitForTimeout(200);
start.buchung = await p.evaluate(() => {
  const z = document.querySelector("#main #B-01");
  const nummer = [...z.querySelectorAll(".z")].map(x => x.textContent).find(t => t.startsWith("Nummer: "));
  return z ? {sichtbar: window.sichtbar(z), nummer: nummer ? nummer.slice(8) : null,
              reiter: (document.querySelector("#nav a.on") || {getAttribute: () => "#"}).getAttribute("href").slice(1)} : null;
});
// Stornierte Buchungen (#146): am Ding nur ein zugeklappter Block „Storniert (n)“ mit Hinweis zum Zurückholen; die geltende
// Buchung steht voll da. Gemessen je Ding, das eine Buchung zeigt (Tageskasten, Unterkunftskarte: das nächste Element mit id).
const storniert = () => {
  const istStorno = d => ((d.querySelector(":scope > summary") || {}).textContent || "").startsWith("Storniert");
  const blockInfo = d => ({summary: d.querySelector(":scope > summary").textContent, offen: d.open,
    hinweis: [...d.querySelectorAll(".z.klein")].map(x => x.textContent).find(t => t.startsWith("Zurückholen")) || null,
    b03: d.querySelector("[id='B-03']") ? {
      chip: [...d.querySelectorAll("[id='B-03'] .chip")].map(x => x.textContent),
      nummer: [...d.querySelectorAll("[id='B-03'] .z")].map(x => x.textContent).find(t => t.startsWith("Nummer: ")) || null,
      verlauf: (d.querySelector("[id='B-03'] details.verlauf > summary") || {}).textContent || null,
      grund: (d.querySelector("[id='B-03'] details.verlauf") || {}).textContent?.includes("Zimmer doppelt gebucht") || false,
    } : null});
  // je Ding, an dem die Buchung steht: Blöcke „Storniert“ darin, B-03 außerhalb eines Blocks, Hinweis im Text
  const orte = bid => [...document.querySelectorAll(`#main [id='${bid}']`)].map(x => {
    const ding = x.parentElement.closest("[id]") || document.querySelector("#main");
    return {ding: ding.id, sichtbar: window.sichtbar(x), imBlock: !!x.closest("details.weg"),
            bloecke: [...ding.querySelectorAll("details.weg")].filter(istStorno).map(blockInfo),
            b03Draussen: [...ding.querySelectorAll("[id='B-03']")].filter(y => !y.closest("details.weg")).length,
            zurueckholen: ding.textContent.includes("Zurückholen:")};
  });
  const b03 = [...document.querySelectorAll("#main [id='B-03']")];
  return {hash: location.hash, b01: orte("B-01"), b02: orte("B-02"),
          b03: b03.length, b03Sichtbar: b03.some(x => window.sichtbar(x)), b03Draussen: b03.filter(x => !x.closest("details.weg")).length,
          bloecke: [...document.querySelectorAll("#main details.weg")].filter(istStorno).map(blockInfo),
          chipZuB03: document.querySelectorAll("#main a[href='#B-03']").length,
          chipZuB01: [...document.querySelectorAll("#main a[href='#B-01']")].map(a => a.textContent)};
};
await p.evaluate(() => { location.hash = "B-01"; });
await p.waitForTimeout(200);
start.stornoB01 = await p.evaluate(storniert);
// Ein Ding ohne stornierte Buchung (E-20 mit B-02): kein Block, kein Hinweis
await p.evaluate(() => { location.hash = "B-02"; });
await p.waitForTimeout(200);
start.stornoB02 = await p.evaluate(storniert);
// Link auf die stornierte Buchung: der Block öffnet sich, B-03 steht sichtbar bei seinem Ding
await p.evaluate(() => { location.hash = "B-03"; });
await p.waitForTimeout(300);
start.stornoB03 = await p.evaluate(storniert);
// „Alle Möglichkeiten (n)“ zählt nur gültige Optionen; V-03 hat eine gültige und eine verworfene (V-03.b), die Zeile
// steht trotzdem da („Alle Möglichkeiten (1)“), darin „Verworfen (1)“. Abschnitt „Nacht“ einer Tagesseite (nur bei festem Plan).
await p.evaluate(() => { location.hash = "T-02"; });
await p.waitForTimeout(200);
start.moeglichkeiten = await p.evaluate(() => ({
  nacht: !!document.querySelector("#main section.ebene-nacht"),
  zeilen: [...document.querySelectorAll("#main summary")].map(s => s.textContent)
    .filter(t => t.startsWith("Alle Möglichkeiten (") || t.startsWith("Verworfen (")),
}));
// Link auf die verworfene Option: bleibt erreichbar, die Blöcke darum öffnen sich
await p.evaluate(() => { location.hash = "V-03.b"; });
await p.waitForTimeout(300);
start.moeglichkeiten.verworfenSichtbar = await p.evaluate(() => window.sichtbar(document.getElementById("V-03.b")));
await b.close();
console.log(JSON.stringify({...start, fehler}));
