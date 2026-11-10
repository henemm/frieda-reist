// Packliste im Browser (ADR-0010, #370), aufgerufen von test_packliste.py mit laufendem Rückmeldedienst.
// Aufruf: node seiten_packliste.mjs <playwright-modul> <basis-url> <dienst-url> <name>
// Die Seite spricht api/… an; die Anfragen gehen an den echten Dienst (<dienst-url>/<reise>/…), solange „netz“ an ist.
// Mit RH_BILDER=<ordner> entstehen Bilder (Handy und Rechner). Meldet je Schritt, was die Seite zeigt, und Skriptfehler.
const [, , modul, basis, dienst, name] = process.argv;
const pw = await import(modul);
const b = await pw[process.env.RH_BROWSER || "chromium"].launch();
const fehler = [], aus = {};
let netz = true;
const reise = new URL(basis).pathname.split("/").filter(Boolean).pop();

async function seite(breite, hash) {
  const ctx = await b.newContext({viewport: {width: breite, height: 900}, serviceWorkers: "block"});
  await ctx.route("**/api/**", async r => {
    if (!netz) return r.abort();
    const pfad = new URL(r.request().url()).pathname.split("/api/")[1];
    // Wer spricht: der Name aus dem Speicher des Browsers, beglaubigt wie vom Konnektor (Dienst-Geheimnis aus der Umgebung);
    // ohne Anmeldung nimmt der Dienst seit #421 keinen eingetippten Namen mehr an
    const kopf = {...await r.request().allHeaders(), "x-frieda-dienst": process.env.FR_TEST_DIENST || ""};
    r.fulfill({response: await r.fetch({url: `${dienst}/${reise}/${pfad}`, headers: kopf})});
  });
  await ctx.addInitScript(n => localStorage.setItem("rh-name", n), name);
  const p = await ctx.newPage();
  p.on("pageerror", e => fehler.push(`${breite}: ${e}`));
  p.on("dialog", d => d.accept());
  await p.goto(basis + hash);
  return p;
}
const texte = (p, sel) => p.$$eval(sel, a => a.map(x => x.textContent.replace(/\s+/g, " ").trim()));
const zeile = (p, titel) => p.locator(".pack-zeile", {hasText: titel});
const haken = (p, titel) => zeile(p, titel).locator("[data-pack]");
const ausgang = p => p.evaluate(r => JSON.parse(localStorage.getItem(`rh-${r}-packstand-ausgang`) || "[]").length, reise);
const warte = (p, f, ...a) => p.waitForFunction(f, ...a, {timeout: 5000});

const p = await seite(390, "#packliste");
await p.waitForSelector(".pack-tabelle");
// Ansicht Planen: je Kategorie eine Tabelle mit den Merkmalen als Spalten, Summen unten, Summe der ganzen Liste oben
aus.planen = {
  reiter: await p.$eval("#nav a.on", a => a.getAttribute("href")),
  kategorien: await texte(p, ".pack-tabelle h3"),
  gesamt: await texte(p, ".pack-summe.gesamt"),
  spalten: await texte(p, ".pack-tabelle:first-of-type thead th"),
  summen: await p.$$eval(".pack-tabelle tfoot tr", a => a.map(x => [...x.cells].map(c => c.textContent.trim()).filter(Boolean).join(" "))),
  weggelassen: await texte(p, ".pack-weg summary"),
  breit: await p.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1),
};
// Ansicht Packen
await p.click('[data-pl-ansicht="packen"]');
await p.waitForSelector(".pack-zeile");
aus.packen = {
  gruppen: await texte(p, ".pack-gruppe > h3"),
  fortschritt: await texte(p, ".pack-kopf ~ p.meldung"),
  haekchenFuerKarl: await p.locator(".pack-zeile [data-pack]").count(),
  ohneHakenIda: await p.locator("#G-07 [data-pack]").count(),      // das Erste-Hilfe-Set packt Ida
};
if (process.env.RH_BILDER) await p.screenshot({path: `${process.env.RH_BILDER}/packliste-390.png`, fullPage: true});
// Abhaken geht sofort, bleibt beim Dienst und überlebt das Neuladen. Die Seite zeigt den Haken vor der Antwort des
// Dienstes; neu geladen wird erst, wenn das Speichern beantwortet ist, sonst gewinnt das Neuladen den Wettlauf (#413).
// Mit Netz zuckt nichts: kein Hinweis „ohne Netz“ und kein „wird nachgereicht“, auch nicht kurz während des Sendens (#501)
await p.evaluate(() => { window.__zuckt = 0; new MutationObserver(() => {
  if (document.querySelector(".pack-zeile .chip.offen") || [...document.querySelectorAll("p.meldung")].some(x => /Ohne Netz/.test(x.textContent))) window.__zuckt++;
}).observe(document.body, {childList: true, subtree: true}); });
const vorher = await texte(p, ".pack-gruppe:first-of-type .pack-titel");
const gespeichert = p.waitForResponse(r => r.url().includes("api/packstand") && r.request().method() === "PATCH");
await haken(p, "Regenjacke").click();
await warte(p, () => document.querySelector(".pack-zeile.gepackt"));
await gespeichert;
await p.waitForTimeout(300);
aus.haken = {gepackt: await texte(p, ".pack-zeile.gepackt .pack-titel"), checked: await haken(p, "Regenjacke").getAttribute("aria-checked"),
  vorher, nachher: await texte(p, ".pack-gruppe:first-of-type .pack-titel"), zuckt: await p.evaluate(() => window.__zuckt),
  fokus: await p.evaluate(() => document.activeElement?.dataset?.pack || "")};
await p.reload();
await p.waitForSelector(".pack-zeile");
aus.nachNeuladen = await texte(p, ".pack-zeile.gepackt .pack-titel");
aus.fortschritt = await texte(p, ".pack-kopf ~ p.meldung");
// Gruppieren nach Raum: in der Reihenfolge der Werte der Auswahl, mit Summen je Gruppe
await p.selectOption("#plGruppe", "raum");
await warte(p, () => document.querySelector(".pack-gruppe[data-gruppe='Rucksack']"));
aus.raum = {gruppen: await texte(p, ".pack-gruppe > h3"), summen: await texte(p, ".pack-gruppe > .pack-summe"),
  mitRaum: await p.locator(".pack-gruppe .pack-unter", {hasText: "Raum"}).count()};
// Ohne Netz abhaken und zurücknehmen: wird gemerkt und beim nächsten Kontakt nachgereicht
netz = false;
await haken(p, "Wanderstöcke").click();
await haken(p, "Regenjacke").click();                              // eigener Haken vom Dienst: auch ohne Netz zurücknehmen
await warte(p, () => !document.querySelector(".pack-zeile.gepackt .pack-titel")?.textContent.includes("Regenjacke"));
await warte(p, () => document.querySelectorAll(".pack-zeile .chip.offen").length === 2);
aus.offline = {ausgang: await ausgang(p), gepackt: await texte(p, ".pack-zeile.gepackt .pack-titel"),
  nachreichen: await texte(p, ".pack-zeile .chip.offen")};
netz = true;
await p.evaluate(() => dispatchEvent(new Event("online")));
await warte(p, r => localStorage.getItem(`rh-${r}-packstand-ausgang`) === "[]", reise);
await p.waitForTimeout(300);
aus.nachgereicht = {ausgang: await ausgang(p), gepackt: await texte(p, ".pack-zeile.gepackt .pack-titel")};
// Mitnehmen: eine Zeile am Ding, an dem der Gegenstand hängt; sie führt zur Packliste
const t = await seite(390, "#T-02");
await t.waitForSelector(".mitnehmen");
aus.mitnehmen = {text: await texte(t, ".mitnehmen"), href: await t.$eval(".mitnehmen", a => a.getAttribute("href"))};
await t.click(".mitnehmen");
await t.waitForSelector(".pack-tabelle, .pack-zeile");
aus.mitnehmen.danach = await t.$eval("#nav a.on", a => a.getAttribute("href"));
// Ein Gegenstand ist über seine Kennung erreichbar
const g = await seite(390, "#G-05");
await g.waitForSelector("#G-05");
aus.kennung = {reiter: await g.$eval("#nav a.on", a => a.getAttribute("href")), da: await g.locator("#G-05").count()};
// Breite Ansicht
const w = await seite(1200, "#packliste");
await w.waitForSelector(".pack-tabelle");
if (process.env.RH_BILDER) await w.screenshot({path: `${process.env.RH_BILDER}/packliste-1200.png`, fullPage: true});
aus.breit = await w.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1);
await b.close();
console.log(JSON.stringify({...aus, fehler}));
