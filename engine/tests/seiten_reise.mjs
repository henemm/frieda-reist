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
      tage: [...document.querySelectorAll(".reise-tage .tagzeile")].map(z => [z.getAttribute("href"), z.querySelector(".tz-name").textContent,
        (z.querySelector(".tz-nacht .chip") || {}).textContent || null]),
      // genau ein Link je Tag: die Zeile selbst, darin weder Links noch Knöpfe noch Kennungen
      inZeile: document.querySelectorAll(".reise-tage .tagzeile :is(a, button, .zid)").length,
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
  // Karte der Reise: Leaflet hat ihren Kasten vermessen und zeichnet die Wege in der Fläche, nicht in einen Punkt
  // (Fehler 29.10.2026: Kasten beim Zeichnen noch nicht im Dokument, Größe 0)
  // Auf einem ausgelasteten Rechner braucht das Vermessen länger als eine feste Frist: warten, bis Leaflet den Kasten kennt
  await p.waitForFunction(() => { const box = document.querySelector(".reise-karte .kartenbox");
    return !box || (KARTE && box.clientWidth > 0 && KARTE.getSize().x === box.clientWidth); }, null, {timeout: 5000}).catch(() => {});
  await p.waitForTimeout(300);
  a.karte = await p.evaluate(() => { const box = document.querySelector(".reise-karte .kartenbox");
    if (!box) return null;
    const w = [...box.querySelectorAll(".leaflet-overlay-pane path")].map(x => x.getBoundingClientRect());
    return {breite: KARTE.getSize().x, kasten: box.clientWidth, wege: Math.max(0, ...w.map(r => r.right)) - Math.min(...w.map(r => r.left))}; });
  await p.evaluate(() => { location.hash = "P-A"; });
  await p.waitForTimeout(200);
  a.planZiel = await p.evaluate(() => !!document.querySelector(".tagzeilen") && !document.querySelector(".steckbrief"));
  await p.evaluate(() => { location.hash = ""; });
  await p.waitForSelector(".tagzeilen");
  await p.locator(".reise-tage .tz-titel").first().click();
  await p.waitForTimeout(200);
  a.nachKlick = await p.evaluate(() => location.hash);
  // Zurück an dieselbe Zeile: Tag 3 öffnen, „← Reise“ führt zur Zeile von Tag 3 mit Fokus, sichtbar
  await p.evaluate(() => { location.hash = ""; });
  await p.waitForSelector(".tagzeilen");
  await p.locator('.reise-tage .tagzeile[data-tag="T-03"]').click();
  await p.waitForSelector(".tagseite");
  await p.locator("a.zurueck").click();
  await p.waitForSelector(".tagzeilen");
  a.zurueck = await p.evaluate(() => { const e = document.activeElement, r = e.getBoundingClientRect();
    return {tag: e.dataset.tag || null, sichtbar: r.top >= 0 && r.bottom <= innerHeight, oben: scrollY}; });
  // Heimat der Unterkunft: der Abschnitt „Nacht“ ihres Tags; Zu tun mit „Zu buchen“ je Nacht
  await p.evaluate(() => { location.hash = "U-02"; });
  await p.waitForSelector(".tagseite");
  a.unterkunft = await p.evaluate(() => ({inNacht: !!document.querySelector(".ebene-nacht #U-02"), reiter: document.querySelector("#nav a.on").textContent,
    // Webseite aus dem Kontakt nach außen, kein Link der Nacht auf sich selbst (29.10.2026)
    web: (document.querySelector('.ebene-nacht a.web-link[target="_blank"]:not(.karten-links a)') || {}).href || null,
    selbst: document.querySelectorAll('.ebene-nacht a[href="#U-02"]').length,
    // Lage (ADR-0004): Punkt aus plan/punkte.yaml, Link zu Google Maps; Apple Karten nur auf Apple-Geräten
    karte: [...document.querySelectorAll('.ebene-nacht .lage a')].map(a => a.href)}));
  await p.evaluate(() => { location.hash = "offen"; });
  await p.waitForSelector("#zu-buchen");
  a.buchen = await p.evaluate(() => [...document.querySelectorAll("#zu-buchen .wzeile")].map(z => [z.getAttribute("href"), z.querySelector(".chip").textContent]));
  await p.evaluate(() => { location.hash = "wissen"; });
  await p.waitForSelector("#ueber-plan");
  a.ueberPlan = await p.evaluate(() => document.querySelectorAll("#ueber-plan ~ .wliste .typ-plan").length);
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
