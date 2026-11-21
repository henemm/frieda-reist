// Eigene Fotos (#582, Spec docs/specs/oberflaeche/bilder-582-eigene-fotos.md), aufgerufen von test_bilder_eigen.py.
// Zwei Arten:
//   node seiten_bilder_eigen.mjs <playwright-modul> seite <basis beispielreise> <basis stadtwochenende> <foto> <texte-json>
//     Die Dienste sind nachgestellt: api/ich liefert die Person (Karl, Mo, Lea oder niemand), api/bilder… nimmt Hochladen und
//     Löschen an und merkt sich die Anfragen; alles andere unter api/ ist 404. Hochladen mit echtem setInputFiles.
//   node seiten_bilder_eigen.mjs <playwright-modul> sw <basis beispielreise> <web-ordner> <web-ordner neuer stand> <marke>
//     Service Worker: Seite laden (Vorab-Speicher), dann den neuen Stand (Bild entfernt) an die Stelle legen, neu laden und
//     zählen, wie viele Einträge mit <marke> im Adressnamen noch in den Speichern der Reise liegen.
import fs from "node:fs";

const [, , modul, art, ...rest] = process.argv;
const pw = await import(modul);
const b = await pw[process.env.RH_BROWSER || "chromium"].launch();
const fehler = [];
const beobachten = p => {
  p.on("pageerror", e => fehler.push("pageerror: " + e));
  p.on("console", m => { if (/Content.Security.Policy|Refused to (load|execute)/i.test(m.text())) fehler.push("console: " + m.text()); });
};
const leise = ms => new Promise(r => setTimeout(r, ms));
const genau = text => new RegExp("^\\s*" + text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&").replace(/\s+/g, "\\s+") + "\\s*$");
const teile = vorlage => vorlage.split(/\{[^{}]*\}/).map(s => s.trim()).filter(s => s.length >= 2);

if (art === "seite") {
  const [basis, basisStadt, foto, texteJson] = rest;
  const T = JSON.parse(texteJson);
  const ich = person => ({basis: new URL(basis).origin, meldungen: [],
    konto: person ? {name: person.name, email: person.schluessel + "@beispiel.invalid", sprache: "de"} : null,
    person: person || null});

  async function seite(person, breite = 1300, hoehe = 900) {
    const ctx = await b.newContext({viewport: {width: breite, height: hoehe}, serviceWorkers: "block"});
    const gesendet = [];
    await ctx.route("**/api/**", async r => {
      const req = r.request(), pfad = new URL(req.url()).pathname.split("/api/")[1] || "";
      if (pfad === "ich") return r.fulfill({contentType: "application/json", body: JSON.stringify(ich(person))});
      if (pfad === "bilder" || pfad.startsWith("bilder/")) {
        gesendet.push({methode: req.method(), url: req.url(), laenge: (req.postDataBuffer() || Buffer.alloc(0)).length});
        return r.fulfill({status: req.method() === "POST" ? 201 : 200, contentType: "application/json",
                          body: JSON.stringify({ok: true, id: "BI-99"})});
      }
      return r.fulfill({status: 404, contentType: "application/json", body: "{}"});
    });
    const p = await ctx.newPage();
    p.setDefaultTimeout(4000);   // fehlt ein Element, scheitert der Schritt schnell statt nach 30 s
    beobachten(p);
    return {ctx, p, gesendet};
  }
  const gehe = async (p, url) => { await p.goto(url); await p.waitForSelector("#main > *", {state: "attached"}); await p.waitForTimeout(500); };
  const knopf = (p, text, wurzel = "body") => p.locator(`${wurzel} button, ${wurzel} a, ${wurzel} label, ${wurzel} [role=button]`)
    .filter({hasText: genau(text)}).filter({visible: true});
  const sichtbarerText = (p, vorlage) => p.evaluate(stuecke => {
    const n = s => s.replace(/\s+/g, " ");
    const els = [...document.querySelectorAll("body *")].filter(e => e.getClientRects().length && stuecke.every(t => n(e.textContent).includes(n(t))));
    return els.length > 0;
  }, teile(vorlage));
  async function waehlen(p) {
    const eingabe = p.locator("input[type=file]");
    if (await eingabe.count()) { await eingabe.first().setInputFiles(foto); }
    else {
      const [wahl] = await Promise.all([p.waitForEvent("filechooser", {timeout: 5000}), knopf(p, T.hochladen).first().click()]);
      await wahl.setFiles(foto);
    }
    await p.waitForTimeout(500);
  }
  async function warten(liste, bedingung, ms = 5000) {
    for (let i = 0; i < ms / 100 && !liste.some(bedingung); i++) await leise(100);
  }
  async function loeschen(p, gesendet) {
    const d = {knopf: false};
    const kopf = p.locator("#main .bild.kopf").first();
    if (!(await kopf.count())) return d;
    await kopf.click();
    await p.waitForSelector("#gross[open]", {timeout: 5000}).catch(() => {});
    d.knopf = (await knopf(p, T.entfernen, "#gross").count()) > 0;
    if (!d.knopf) return d;
    await knopf(p, T.entfernen, "#gross").first().click();
    await p.waitForTimeout(400);
    d.dialog = {titel: await sichtbarerText(p, T.titel), zusage: await sichtbarerText(p, T.zusage),
                knoepfe: [(await knopf(p, T.behalten).count()) > 0, (await knopf(p, T.ja).count()) > 0]};
    if (d.dialog.knoepfe[0]) await knopf(p, T.behalten).first().click();
    await p.waitForTimeout(500);
    d.nachBehalten = gesendet.filter(x => x.methode === "DELETE");
    if ((await knopf(p, T.entfernen, "#gross").count()) === 0) {   // Großansicht wieder öffnen, falls sie zu ist
      await kopf.click().catch(() => {});
      await p.waitForSelector("#gross[open]", {timeout: 5000}).catch(() => {});
    }
    await knopf(p, T.entfernen, "#gross").first().click().catch(() => {});
    await p.waitForTimeout(400);
    await knopf(p, T.ja).first().click().catch(() => {});
    await warten(gesendet, x => x.methode === "DELETE");
    d.nachEntfernen = gesendet.filter(x => x.methode === "DELETE");
    return d;
  }

  const aus = {fotoVon: T.fotoVon};
  const karl = {schluessel: "karl", name: "Karl", rolle: "mitwirkend"};

  const abschnitt = async (name, f) => { try { await f(); } catch (e) { fehler.push(name + ": " + String(e).split("\n")[0]); } };
  // Karl (mitwirkend, hat BI-90 hochgeladen): Hochladen mit Hinweis, Nennung, Löschen mit Zusage
  await abschnitt("karl", async () => {
    const {ctx, p, gesendet} = await seite(karl);
    await gehe(p, basis + "#O-01");
    const k = {knopfHochladen: (await knopf(p, T.hochladen).count()) > 0};
    const haken = () => p.evaluate(() => [...document.querySelectorAll("input[type=checkbox]")].filter(e => e.getClientRects().length).length);
    const hakenVorher = await haken();
    await waehlen(p).catch(e => fehler.push("waehlen: " + e));
    k.blatt = await p.evaluate(([hinweis, knopfText]) => {
      const n = s => s.replace(/\s+/g, " ").trim();
      const sichtbar = e => e && e.getClientRects().length > 0;
      const h = [...document.querySelectorAll("body *")].filter(e => sichtbar(e) && n(e.textContent).includes(n(hinweis[0] || "")))
        .sort((a, b) => a.textContent.length - b.textContent.length)[0];
      const kn = [...document.querySelectorAll("button")].filter(e => sichtbar(e) && knopfText.every(t => n(e.textContent).includes(t)))[0];
      return {hinweisSichtbar: !!h, hinweisVorKnopf: !!(h && kn && (h.compareDocumentPosition(kn) & Node.DOCUMENT_POSITION_FOLLOWING))};
    }, [teile(T.hinweis), teile(T.knopf)]);
    k.blatt.haken = (await haken()) - hakenVorher;
    const hochladenKnopf = p.locator("button").filter({hasText: teile(T.knopf)[0] || T.knopf}).filter({visible: true});
    if (await hochladenKnopf.count()) await hochladenKnopf.first().click();
    await warten(gesendet, x => x.methode === "POST");
    k.gesendet = gesendet.filter(x => x.methode === "POST");
    await gehe(p, basis + "#O-01");
    k.nennungen = await p.evaluate(() => [...document.querySelectorAll("#main .nennung, #main figcaption")].map(e => e.textContent.replace(/\s+/g, " ").trim()));
    k.loeschen = await loeschen(p, gesendet);
    aus.karl = k;
    await ctx.close();
  });
  // Mo (mitwirkend, nicht Besitzer): kein Knopf zum Entfernen
  await abschnitt("mo", async () => {
    const {ctx, p, gesendet} = await seite({schluessel: "mo", name: "Mo", rolle: "mitwirkend"});
    await gehe(p, basis + "#O-01");
    aus.mo = {loeschen: await loeschen(p, gesendet)};
    await ctx.close();
  });
  // Nicht angemeldet: Hinweis zum Anmelden
  await abschnitt("gast", async () => {
    const {ctx, p} = await seite(null);
    await gehe(p, basis + "#O-01");
    aus.gast = {anmeldenHinweis: await sichtbarerText(p, T.anmelden)};
    await ctx.close();
  });
  // 360 px: keine Überbreite, auch mit offenem Blatt
  await abschnitt("schmal", async () => {
    const {ctx, p} = await seite(karl, 360, 780);
    await gehe(p, basis + "#O-01");
    const breit = () => p.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1);
    aus.schmal = {ueberbreite: await breit()};
    await waehlen(p).catch(e => fehler.push("waehlen 360: " + e));
    aus.schmal.ueberbreiteBlatt = await breit();
    await ctx.close();
  });
  // Stadtwochenende (ohne Bilder): Lea sieht den Knopf
  await abschnitt("stadt", async () => {
    const {ctx, p} = await seite({schluessel: "lea", name: "Lea", rolle: "mitwirkend"});
    await gehe(p, basisStadt + "#O-02");
    aus.stadt = {knopfHochladen: (await knopf(p, T.hochladen).count()) > 0};
    await ctx.close();
  });
  console.log(JSON.stringify({fehler, aus}));
} else if (art === "sw") {
  const [basis, ordner, ordnerNeu, marke] = rest;
  const ctx = await b.newContext();
  const p = await ctx.newPage();
  p.setDefaultTimeout(15000);
  p.on("pageerror", e => fehler.push("pageerror: " + e));
  const zaehlen = () => p.evaluate(async m => {
    let n = 0;
    for (const name of await caches.keys()) {
      if (!name.startsWith("rh:")) continue;
      for (const r of await (await caches.open(name)).keys()) if (r.url.includes(m)) n++;
    }
    return n;
  }, marke);
  await p.goto(basis);
  await p.evaluate(() => Promise.race([navigator.serviceWorker.ready, new Promise(r => setTimeout(r, 15000))]));
  await p.waitForFunction(() => navigator.serviceWorker.controller !== null, null, {timeout: 15000});
  const vorher = await zaehlen();
  // neuer Stand: das Bild ist entfernt (Dateien weg, Liste ohne Fassungen)
  fs.rmSync(ordner, {recursive: true, force: true});
  fs.cpSync(ordnerNeu, ordner, {recursive: true});
  await p.reload();
  await p.waitForSelector("#main > *", {state: "attached"});
  await p.evaluate(async () => { const r = await navigator.serviceWorker.getRegistration(); if (r) await r.update().catch(() => {}); });
  let nachher = await zaehlen();
  for (let i = 0; i < 100 && nachher > 0; i++) { await leise(100); nachher = await zaehlen(); }
  console.log(JSON.stringify({fehler, vorher, nachher}));
} else {
  console.error("unbekannte Art: " + art);
  process.exitCode = 2;
}
await b.close();
