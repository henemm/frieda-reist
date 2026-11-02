// Eine Seitenordnung für alle Reisen (frieda-reist#214), aufgerufen von test_eine_seitenordnung.py.
// Aufruf: node seiten_eine_seitenordnung.mjs <playwright-modul> <basis-url> <json: {tage, voll, wahlen, extra}>
// extra: weitere Sprungziele (z. B. ein Plan P-A), gemessen wie die Dinge
// Misst die Startseite, jeden Reiter und jede Tagesseite: wie oft jedes Ding vollständig steht (an einer Angabe, die nur seine
// volle Form trägt), Vergleiche je Wahlstelle, doppelte IDs, Marken „offen“. Dazu die Zeitachse der Startseite, „Zu tun“ und
// wohin der Link zu einem Ding führt. Wartet nur auf den Titel, nie auf Elemente der neuen Ordnung (fehlt eines, steht null da).
const [, , modul, basis, auftragText] = process.argv;
const auftrag = JSON.parse(auftragText);
const pw = await import(modul);
const b = await pw[process.env.RH_BROWSER || "chromium"].launch();
const ctx = await b.newContext({viewport: {width: 1300, height: 900}, serviceWorkers: "block"});
await ctx.route("**/api/**", r => r.abort());
const p = await ctx.newPage();
const fehler = [];
p.on("pageerror", e => fehler.push(String(e)));
await p.clock.setFixedTime(new Date("2026-11-02T10:00:00"));   // vor der Reise (Planung)
await p.goto(basis);
await p.waitForSelector("#titel:not(:empty)");
await p.waitForTimeout(300);

const messen = (auftrag) => {
  const main = document.querySelector("#main");
  // Textknoten im Hauptbereich, die genau die Angabe sind (je volle Form genau einer; ein Verlauf, der sie nennt, zählt nicht)
  const zaehle = text => {
    let n = 0;
    const w = document.createTreeWalker(main, NodeFilter.SHOW_TEXT);
    while (w.nextNode()) if (w.currentNode.nodeValue.trim() === text) n++;
    return n;
  };
  const voll = Object.fromEntries(Object.entries(auftrag.voll).map(([id, text]) => [id, zaehle(text)]));
  const vergleiche = {};
  for (const x of main.querySelectorAll(".wm[data-vgl]")) {
    const v = x.getAttribute("data-vgl").split(/[~@]/)[0];
    vergleiche[v] = (vergleiche[v] || 0) + 1;
  }
  const ids = {};
  for (const x of document.querySelectorAll("[id]")) ids[x.id] = (ids[x.id] || 0) + 1;
  const doppelt = Object.fromEntries(Object.entries(ids).filter(([, n]) => n > 1));
  return {hash: location.hash, voll, vergleiche, ids, doppelt,
          wahlen: main.querySelectorAll(".ding.wahl, .wm-knopf, .tz-marken .chip.offen").length,   // Wahl, Einstieg, Marke
          tagseite: !!main.querySelector(".tagseite"),
          kopf: main.querySelector(".tagseite") ? (main.querySelector("h2.tagkopf .tagdatum") || {}).textContent || null : null,   // Kopf der Tagesseite
          etappe: main.querySelector("[id='E-01']") ? {karte: !!main.querySelector(".maplibregl-map, canvas, svg.karte"),
            weiter: (main.querySelector("a.weiter") || {}).textContent || null} : null,
          reiter: (document.querySelector("#nav a.on") || {getAttribute: () => "#"}).getAttribute("href").slice(1)};
};
const gehe = async hash => {
  await p.evaluate(h => { location.hash = h; }, hash);
  await p.waitForTimeout(250);
};

// Startseite (ohne Sprungziel)
const reiter = await p.evaluate(() => [...document.querySelectorAll("#nav a")].map(a => a.getAttribute("href").slice(1)));
const startMessung = await p.evaluate(messen, auftrag);
const start = await p.evaluate(() => {
  const achse = document.querySelector("#main .tagzeilen.achse");
  const zeilen = [...document.querySelectorAll("#main .tagzeile")];
  return {
    achse: !!achse,
    zeilen: zeilen.map(z => z.getAttribute("data-tag")),
    zeilenNr: zeilen.map(z => (z.querySelector(".tz-datum b") || {}).textContent || null),
    zeilenLinks: zeilen.map(z => [z, ...z.querySelectorAll("a")].filter(a => a.tagName === "A").map(a => a.getAttribute("href"))),
    spalten: new Set(zeilen.map(z => Math.round(z.getBoundingClientRect().left))).size,
    tageskaesten: document.querySelectorAll("#main .karte[id^='T-']").length,
  };
});
const ansichten = [{schluessel: "start", ...startMessung}];
const startReiter = startMessung.reiter;
for (const r of reiter) {
  if (r === startReiter) continue;   // der Startreiter ist die Startseite
  await gehe(r);
  ansichten.push({schluessel: "#" + r, ...(await p.evaluate(messen, auftrag))});
}
const tagesseiten = {};
for (const t of auftrag.tage) {
  await gehe(t);
  const m = await p.evaluate(messen, auftrag);
  tagesseiten[t] = m;
  // Ohne Tagesseite führt #T-… in einen Tageskasten einer anderen Ansicht: die zählt dann nicht doppelt
  ansichten.push({schluessel: m.tagseite ? "#" + t : "#" + m.reiter, ...m});
}
// „Zu tun“
let zuTun = null;
if (reiter.includes("offen")) {
  await gehe("offen");
  zuTun = await p.evaluate(() => ({zuBuchen: !!document.querySelector("#main #zu-buchen"),
                                   zuEntscheiden: !!document.querySelector("#main #zu-entscheiden")}));
}
// Der Link zu einem Ding: wo landet er, steht das Ding dort vollständig?
const sprung = {};
for (const id of [...Object.keys(auftrag.voll), "O-03", ...(auftrag.extra || [])]) {
  await gehe(id);
  sprung[id] = await p.evaluate(([id, text]) => {
    const main = document.querySelector("#main");
    const am = [...main.querySelectorAll("section.am-element")];
    return {hash: location.hash, tagseite: !!main.querySelector(".tagseite"), ziel: !!main.querySelector(`[id='${id}']`),
            reiter: (document.querySelector("#nav a.on") || {getAttribute: () => "#"}).getAttribute("href").slice(1),
            voll: text ? main.textContent.includes(text) : null,
            wahlLinks: am.flatMap(s => [...s.querySelectorAll("a[href^='#V-']")].map(a => a.getAttribute("href"))
              .concat([...s.querySelectorAll("[id^='V-']")].map(x => "#" + x.id)))};
  }, [id, auftrag.voll[id] || null]);
}
await b.close();
console.log(JSON.stringify({fehler, reiter, start, ansichten, tagesseiten, zuTun, sprung}));
