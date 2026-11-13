// Packliste im Browser (ADR-0010, #370), aufgerufen von test_packliste.py mit laufendem Rückmeldedienst.
// Aufruf: node seiten_packliste.mjs <playwright-modul> <basis-url> <dienst-url> <name>
// Die Seite spricht api/… an; die Anfragen gehen an den echten Dienst (<dienst-url>/<reise>/…), solange „netz“ an ist.
// Mit RH_BILDER=<ordner> entstehen Bilder (Handy und Rechner). Meldet je Schritt, was die Seite zeigt, und Skriptfehler.
import {bild} from "./bild.mjs";

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
  // #431: Summe aufgeteilt nach dem ersten Auswahl-Merkmal, Hinweis auf die für die Reise ausgeblendete Kategorie
  aufteilen: await p.$eval("#plAufteilen", s => s.value),
  teile: await p.$$eval(".pack-aufteilung > div", a => a.map(d => d.children[0].textContent + " " + d.children[1].textContent)),
  hinweis: await texte(p, ".pack-hinweis"),
};
// Sortieren (#431): auf, ab, nach Neuladen gemerkt, dritter Tipp zurück; gilt für alle Tabellen
const kopfGewicht = '.pack-tabelle:first-of-type [data-pl-sort="gewicht"]';
const sortStand = async () => ({sort: await p.$eval(kopfGewicht, k => k.closest("th").getAttribute("aria-sort")),
  zeilen: await texte(p, ".pack-tabelle:first-of-type tbody th[scope=row]")});
const titelVon = z => z.map(t => t.split("G-")[0].trim());
await p.click(kopfGewicht);
const auf = await sortStand();
await p.click(kopfGewicht);
const ab = await sortStand();
await p.reload();
await p.waitForSelector(".pack-tabelle");
const gemerktSort = await sortStand();
await p.click(kopfGewicht);
const zurueck = await sortStand();
aus.sortieren = {auf: {...auf, zeilen: titelVon(auf.zeilen)}, ab: {...ab, zeilen: titelVon(ab.zeilen)}, gemerkt: gemerktSort.sort,
  zurueck: {...zurueck, zeilen: titelVon(zurueck.zeilen)}};
// nicht aufteilen
await p.selectOption("#plAufteilen", "");
await warte(p, () => !document.querySelector(".pack-aufteilung"));
aus.nichtAufteilen = await p.locator(".pack-aufteilung").count();
await p.selectOption("#plAufteilen", "getragen");
await warte(p, () => document.querySelector(".pack-aufteilung"));
// Ansicht Packen
await p.click('[data-pl-ansicht="packen"]');
await p.waitForSelector(".pack-zeile");
aus.packen = {
  gruppen: await texte(p, ".pack-gruppe > summary > h3"),
  fortschritt: await texte(p, ".pack-kopf ~ p.meldung"),
  haekchenFuerKarl: await p.locator(".pack-zeile [data-pack]").count(),
  ohneHakenIda: await p.locator("#G-07 [data-pack]").count(),      // das Erste-Hilfe-Set packt Ida
  // #431: nur meins (Vorgabe), kompakte Zeile ohne „packt“, Etikett der angebotenen Auswahl, Hinweis auf Sachen anderer
  wer: await p.$$eval(".pack-wer button", a => a.map(b => b.textContent + "=" + b.getAttribute("aria-pressed"))),
  idaDa: await p.locator("#G-07").count(),
  packt: await p.locator(".pack-zeile", {hasText: /packt/}).count(),
  griffbereit: await zeile(p, "Trinkflasche").locator(".chip", {hasText: "griffbereit"}).count(),
  wert: await texte(p, "#G-01 .pack-wert"),
  hinweis: await texte(p, ".pack-hinweis"),
  kamera: await p.locator("#G-11").count(),
  fuerMich: await p.$$eval(".pack-kats button", a => a.map(b => b.textContent + "=" + b.getAttribute("aria-pressed"))),
};
// Notiz erst nach Antippen
const notizKnopf = "#G-05 button.pack-auf";
aus.notiz = {vorher: await p.$eval(notizKnopf, k => k.getAttribute("aria-expanded")), sichtbarVorher: await p.isVisible("#G-05-mehr"),
  hinweis: (await texte(p, `${notizKnopf} .pack-mehr-hinweis`))[0]};
await p.click(notizKnopf);
aus.notiz.nachher = await p.$eval(notizKnopf, k => k.getAttribute("aria-expanded"));
aus.notiz.text = (await texte(p, "#G-05-mehr"))[0];
await p.click(notizKnopf);
// Alle: die Sachen der anderen mit ihrem Namen, ohne Haken; zurück auf nur meins
await p.click('[data-pl-wer="alle"]');
await p.waitForSelector("#G-07");
aus.alle = {etikett: await texte(p, "#G-07 .pack-person"), haken: await p.locator("#G-07 [data-pack]").count(), hinweis: await p.locator(".pack-hinweis").count()};
await p.click('[data-pl-wer="meins"]');
await warte(p, () => !document.querySelector("#G-07"));
// Kategorie für mich abwählen: fehlt beim Packen, Fortschritt zählt, was gezeigt wird; nach Neuladen gemerkt; wieder anwählen
await p.click('[data-pl-aus="apotheke"]');
await warte(p, () => !document.querySelector("#G-08"));
await p.reload();
await p.waitForSelector(".pack-zeile");
aus.ohneApotheke = {g08: await p.locator("#G-08").count(), fortschritt: await texte(p, ".pack-kopf ~ p.meldung"),
  knopf: await p.$eval('[data-pl-aus="apotheke"]', b => b.getAttribute("aria-pressed"))};
await p.click('[data-pl-aus="apotheke"]');
await p.waitForSelector("#G-08");
if (process.env.RH_BILDER) await bild(p, {path: `${process.env.RH_BILDER}/packliste-390.png`, fullPage: true});
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
// Der Haken ist sofort zu sehen, die Zeile bleibt aber erst stehen und rutscht nach der Pause (#503)
const sofort = await texte(p, ".pack-gruppe:first-of-type .pack-titel");
await gespeichert;
await warte(p, () => [...document.querySelectorAll(".pack-gruppe:first-of-type .pack-titel")].pop()?.textContent.startsWith("Regenjacke"));
await p.waitForTimeout(400);
aus.haken = {sofort, gepackt: await texte(p, ".pack-zeile.gepackt .pack-titel"), checked: await haken(p, "Regenjacke").getAttribute("aria-checked"),
  vorher, nachher: await texte(p, ".pack-gruppe:first-of-type .pack-titel"), zuckt: await p.evaluate(() => window.__zuckt),
  fokus: await p.evaluate(() => document.activeElement?.dataset?.pack || "")};
await p.reload();
await p.waitForSelector(".pack-zeile");
aus.nachNeuladen = await texte(p, ".pack-zeile.gepackt .pack-titel");
aus.fortschritt = await texte(p, ".pack-kopf ~ p.meldung");
// Gruppieren nach Getragen: in der Reihenfolge der Werte der Auswahl, mit Summen je Gruppe; die Zeile nennt den Wert nicht noch einmal
await p.selectOption("#plGruppe", "getragen");
await warte(p, () => document.querySelector(".pack-gruppe[data-gruppe='Rucksack']"));
aus.raum = {gruppen: await texte(p, ".pack-gruppe > summary > h3"), summen: await texte(p, ".pack-gruppe > summary > .pack-summe"),
  mitWert: await p.locator(".pack-gruppe .pack-zeile", {hasText: "Tagesrucksack"}).count()};
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
// Einklappen (#511): eine Gruppe, in der alles Eigene gepackt ist, klappt zu; der Knopf klappt alle auf oder zu; die Wahl bleibt
const koerper = ".pack-gruppe[data-gruppe='am Körper']";
const vorFertig = await p.$eval(koerper, d => d.open);
await haken(p, "Wanderschuhe").click();
await warte(p, s => !document.querySelector(s).open, koerper);
// Der Knopf entsteht leer, seinen Text setzt die Seite einen Takt später (#550): darauf warten, bei Zeitablauf trotzdem lesen
await warte(p, () => document.querySelector(".pack-alle")?.textContent.trim()).catch(() => {});
const knopf0 = (await texte(p, ".pack-alle"))[0];
await p.click(".pack-alle");
const alleOffen = await p.$$eval("details.pack-klapper", ds => ds.every(d => d.open));
await p.click(".pack-alle");
const alleZu = await p.$$eval("details.pack-klapper", ds => ds.every(d => !d.open));
const gemerkt = await p.evaluate(r => localStorage.getItem(`rh-${r}-pl-offen`), reise);
await p.reload();
await p.waitForSelector("details.pack-klapper");
await warte(p, () => document.querySelector(".pack-alle")?.textContent.trim()).catch(() => {});
aus.klappen = {gemerkt, nach: await p.$$eval("details.pack-klapper", ds => ds.map(d => d.dataset.klapper + "=" + d.open)), vorFertig, knopf0, alleOffen, alleZu, nachNeuladen: await p.$$eval("details.pack-klapper", ds => ds.length > 1 && ds.every(d => !d.open)),
  kopf: (await texte(p, `${koerper} > summary`))[0], knopf: (await texte(p, ".pack-alle"))[0]};
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
if (process.env.RH_BILDER) await bild(w, {path: `${process.env.RH_BILDER}/packliste-1200.png`, fullPage: true});
aus.breit = await w.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1);
await b.close();
console.log(JSON.stringify({...aus, fehler}));
