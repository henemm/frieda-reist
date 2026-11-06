// Start jeder Seite (frieda-reist#387), aufgerufen von test_seite_startet.py.
// Aufruf: node seiten_start.mjs <playwright-modul> <basis-url> [alle]
// Lädt die Startseite, liest daraus alle Ziele (Tage, Orte, Aufenthalte, Strecken, Unterkünfte, Wahlstellen, Abschnitte, Reiter)
// und lädt jedes Ziel frisch in eine neue Seite. Meldet jeden Seitenfehler und jedes console.error und je Seite, ob sie Inhalt hat.
const [, , modul, basis] = process.argv;
const pw = await import(modul);
const b = await pw[process.env.RH_BROWSER || "chromium"].launch();
const ctx = await b.newContext({viewport: {width: 1300, height: 900}, serviceWorkers: "block"});
await ctx.route("**/api/**", r => r.abort());
const fehler = [], seiten = {};

async function laden(h) {
  const p = await ctx.newPage();
  p.on("pageerror", e => fehler.push(`#${h}: ${e}`));
  // „Failed to load resource“ kommt von den gesperrten Aufrufen (api, Kartenkacheln im Netz), nicht von der Seite; fehlende
  // Dateien der Seite selbst melden die Antworten unten
  p.on("console", m => { if (m.type() === "error" && !/^Failed to load resource/.test(m.text())) fehler.push(`#${h}: console.error ${m.text()}`); });
  p.on("response", r => { if (r.url().startsWith(basis) && !r.url().includes("/api/") && r.status() >= 400) fehler.push(`#${h}: ${r.status()} ${r.url()}`); });
  await p.goto(basis + (h ? "#" + h : ""));
  await p.waitForTimeout(500);
  const e = await p.evaluate(() => ({
    titel: ((document.querySelector("#main h2") || document.querySelector("#main h1") || {}).textContent || "").trim(),
    inhalt: document.querySelectorAll("#main > *").length,
    ziele: typeof R === "undefined" || !R ? [] : [
      ...Object.keys(R.orte || {}), ...Object.keys(R.aufenthalte || {}), ...Object.keys(R.strecken || {}),
      ...Object.keys(R.unterkuenfte || {}), ...Object.keys(R.buchungen || {}), ...(R.wahlstellen || []).map(w => w.id),
      ...(PLAN_ANSICHT.tage || []).map(t => t.id), ...[...proId.keys()],
    ],
  }));
  await p.close();
  return e;
}

const start = await laden("");
seiten[""] = {titel: start.titel, inhalt: start.inhalt};
const feste = ["plan", "karte", "wissen", "etappen", "zu-tun", "wuensche", "packliste", "plaene", "orte", "praxis", "quellen", "bausteine"];
for (const h of new Set([...feste, ...start.ziele])) {
  const e = await laden(h);
  seiten[h] = {titel: e.titel, inhalt: e.inhalt};
}
await b.close();
console.log(JSON.stringify({fehler, seiten}));
