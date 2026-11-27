// Eigene Fotos (#582, Spec docs/specs/oberflaeche/bilder-582-eigene-fotos.md), aufgerufen von test_bilder_eigen.py.
// Drei Arten:
//   node seiten_bilder_eigen.mjs <playwright-modul> seite <basis beispielreise> <basis stadtwochenende> <foto> <texte-json>
//     Die Dienste sind nachgestellt: api/ich liefert die Person (Karl, Mo, Lea oder niemand), api/bilder… nimmt Hochladen und
//     Löschen an und merkt sich die Anfragen; alles andere unter api/ ist 404. Hochladen mit echtem setInputFiles.
//   node seiten_bilder_eigen.mjs <playwright-modul> oeffnen <dieselben Argumente wie seite>
//     „Foto entfernen“ im Öffnen der Großansicht (#689); die Quelle hat zwei eigene Fotos an O-01, BI-91 zuerst.
//   node seiten_bilder_eigen.mjs <playwright-modul> sw <basis beispielreise> <web-ordner> <web-ordner neuer stand> <marke> [frist_ms]
//     Service Worker: Seite laden (Vorab-Speicher), dann den neuen Stand (Bild entfernt) an die Stelle legen, neu laden, das
//     Update anstoßen und warten, bis der neue Worker wartet oder übernommen hat. Dann einmal zählen, wie viele Einträge mit
//     <marke> im Adressnamen noch in den Speichern der Reise liegen. Wiederholt wird nur ein gescheiterter Anstoß, höchstens
//     bis zum Ende der Frist (Vorgabe 20000), nie die Prüfung (#654). Ausgabe: _sw_ablauf in test_bilder_eigen.py.
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

if (art === "seite" || art === "oeffnen") {
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
  const stand = p => p.evaluate(() => ({dialoge: document.querySelectorAll("dialog.blatt[open]").length,
    gross: !!document.getElementById("gross"), isOpen: !!(GROSS && GROSS.opener.isOpen),
    fokusImDialog: !!document.activeElement.closest("dialog.blatt")}));
  // Großansicht (PhotoSwipe, #676) öffnen und warten, bis der Übergang vorbei ist; „Foto entfernen“ schließt sie und fragt dann
  const grossAuf = async (p, kopf) => {
    await p.waitForFunction(() => !document.getElementById("gross"), null, {timeout: 3000});
    await kopf.click();
    await p.waitForFunction(() => GROSS && GROSS.opener.isOpen, null, {timeout: 15000});
  };
  const frage = (p, frist = 15000) => p.waitForSelector("dialog.blatt[open]", {timeout: frist}).catch(async () => {
    throw new Error("Keine Frage nach „Foto entfernen“: " + JSON.stringify(await stand(p)));
  });
  async function loeschen(p, gesendet) {
    const d = {knopf: false};
    const kopf = p.locator("#main .bild.kopf").first();
    if (!(await kopf.count())) return d;
    await grossAuf(p, kopf);
    d.knopf = (await knopf(p, T.entfernen, "#gross").count()) > 0;
    if (!d.knopf) return d;
    await knopf(p, T.entfernen, "#gross").first().click();
    await frage(p);
    d.dialog = {titel: await sichtbarerText(p, T.titel), zusage: await sichtbarerText(p, T.zusage),
                knoepfe: [(await knopf(p, T.behalten).count()) > 0, (await knopf(p, T.ja).count()) > 0]};
    if (d.dialog.knoepfe[0]) await knopf(p, T.behalten).first().click();
    await p.waitForTimeout(500);
    d.nachBehalten = gesendet.filter(x => x.methode === "DELETE");
    if ((await knopf(p, T.entfernen, "#gross").count()) === 0) await grossAuf(p, kopf);   // Großansicht wieder öffnen
    await knopf(p, T.entfernen, "#gross").first().click().catch(() => {});
    await frage(p);
    await knopf(p, T.ja).first().click().catch(() => {});
    await warten(gesendet, x => x.methode === "DELETE");
    d.nachEntfernen = gesendet.filter(x => x.methode === "DELETE");
    return d;
  }

  const aus = {fotoVon: T.fotoVon};
  const karl = {schluessel: "karl", name: "Karl", rolle: "mitwirkend"};

  const abschnitt = async (name, f) => { if (art === "seite") try { await f(); } catch (e) { fehler.push(name + ": " + String(e).split("\n")[0]); } };
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
  // Art oeffnen (#689): Klick auf „Foto entfernen“, solange die Großansicht öffnet. Die Dauer des Öffnens wird nur hier verlängert
  // (Antwort auf die Bibliothek), damit das Fenster nicht vom Rechner abhängt. Je Ablauf eine eigene Seite; ein Abbruch steht mit
  // Grund im Ergebnis.
  const DAUER = "showAnimationDuration:333", LANG = 3000, FRIST = {timeout: 15000};
  const ablauf = async (name, f, {person = karl, reduziert = false} = {}) => {
    if (art !== "oeffnen") return;
    const ab = fehler.length, a = aus[name] = {verlaengerung: []};
    const {ctx, p, gesendet} = await seite(person);
    try {
      if (reduziert) await p.emulateMedia({reducedMotion: "reduce"});
      await ctx.route("**/photoswipe-*.esm.min.js", async r => {
        const antwort = await r.fetch(), text = await antwort.text();
        a.verlaengerung.push(text.split(DAUER).length - 1);
        await r.fulfill({response: antwort, body: text.replace(DAUER, "showAnimationDuration:" + LANG)});
      });
      await gehe(p, basis + "#O-01");
      await f(a, p, p.locator("#main .bild.kopf").first(), gesendet);
    } catch (e) { a.abbruch = String(e).split("\n")[0]; }
    a.geloescht = gesendet.filter(x => x.methode === "DELETE").map(x => x.url.split("/").pop());
    a.gesendet = gesendet.length;
    await ctx.close();
    a.fehler = fehler.splice(ab);
  };
  // Großansicht öffnen und im Öffnen n-mal „Foto entfernen“ klicken; ist das Fenster nicht wie erwartet (isOpen), scheitert der
  // Ablauf mit Grund
  const klickImOeffnen = async (a, p, kopf, n = 1, isOpen = false) => {
    await kopf.click();
    await p.waitForFunction(() => document.querySelector("#gross.pswp--ui-visible .gross-unten button.entfernen"), null, FRIST);
    if (a.verlaengerung.join() !== "1") throw new Error(`Verlängerung greift nicht: „${DAUER}“ je Abruf ${JSON.stringify(a.verlaengerung)}-mal statt einmal`);
    a.klick = await p.evaluate(n => {
      const weg = document.querySelector("#gross .gross-unten button.entfernen");
      const k = {isOpen: GROSS.opener.isOpen, dauer: GROSS.options.showAnimationDuration, bild: GROSS.currSlide.data.bild.id};
      for (let i = 0; i < n; i++) weg.click();
      return k;
    }, n);
    if (a.klick.isOpen !== isOpen) throw new Error("Fenster verfehlt: " + JSON.stringify(a.klick));
  };
  const offen = p => p.waitForFunction(() => GROSS && GROSS.opener.isOpen, null, FRIST);
  // Frage abwarten; danach noch etwas Zeit für eine zweite, die es nicht geben darf
  const nachFrage = async p => {
    const da = await p.waitForSelector("dialog.blatt[open]", FRIST).then(() => true, () => false);
    await p.waitForTimeout(1000);
    return {da, titel: await sichtbarerText(p, T.titel), ...await stand(p)};
  };
  // Mit Escape schließen; kommt danach doch noch eine Frage, steht sie im Ergebnis
  const schliessen = async p => {
    await p.keyboard.press("Escape");
    await p.waitForFunction(() => !document.getElementById("gross"), null, FRIST);
    await p.waitForTimeout(1500);
    return stand(p);
  };
  await ablauf("einmal", async (a, p, kopf) => { await klickImOeffnen(a, p, kopf); a.danach = await nachFrage(p); });
  await ablauf("dreimal", async (a, p, kopf) => { await klickImOeffnen(a, p, kopf, 3); a.danach = await nachFrage(p); });
  await ablauf("behalten", async (a, p, kopf) => {
    await klickImOeffnen(a, p, kopf);
    a.danach = await nachFrage(p);
    await knopf(p, T.behalten).first().click();
    await p.waitForFunction(() => !document.querySelector("dialog.blatt"), null, FRIST);
    await kopf.click();
    await offen(p);
    a.wiederOffen = await stand(p);
    a.wiederZu = await schliessen(p);
  });
  await ablauf("entfernen", async (a, p, kopf, gesendet) => {
    await klickImOeffnen(a, p, kopf);
    a.danach = await nachFrage(p);
    if (a.danach.gross) {   // Klick verloren: was passiert beim Weiterblättern und Schließen?
      await p.evaluate(() => GROSS.next());
      await p.waitForTimeout(800);
      a.zuletztGezeigt = await p.evaluate(() => GROSS.currSlide.data.bild.id);
      a.zu = await schliessen(p);
    }
    await knopf(p, T.ja).first().click();
    await warten(gesendet, x => x.methode === "DELETE");
  });
  // Pfeilknopf „weiter“ drücken (im selben evaluate: Fenster und Index festhalten); Ansicht: Index, gezeigtes Bild, Zähler (#706)
  const pfeil = p => p.evaluate(() => {
    document.querySelector("#gross .pswp__button--arrow--next").click();
    return {isOpen: GROSS.opener.isOpen, index: GROSS.currIndex};
  });
  const ansicht = p => p.evaluate(() => ({index: GROSS.currIndex, bild: GROSS.currSlide ? GROSS.currSlide.data.bild.id : null,
    zaehler: document.getElementById("gross-zaehler").textContent}));
  // #689 AC-4, seit #706: Klick im Öffnen, dann Pfeilknopf: es blättert nichts, die Frage kommt zum gezeigten Foto
  await ablauf("blaettern", async (a, p, kopf, gesendet) => {
    await klickImOeffnen(a, p, kopf);
    a.pfeil = await pfeil(p);
    a.danach = await nachFrage(p);
    if (a.danach.da) { await knopf(p, T.ja).first().click(); await warten(gesendet, x => x.methode === "DELETE"); }
    else a.zu = await schliessen(p);
  });
  // #706: Pfeilknopf im Öffnen wirkt nicht; nach dem Öffnen steht das angetippte Bild, danach blättert der Pfeil wie gewohnt
  await ablauf("pfeil", async (a, p, kopf) => {
    await kopf.click();
    await p.waitForFunction(() => document.querySelector("#gross.pswp--ui-visible .pswp__button--arrow--next"), null, FRIST);
    a.pfeil = await pfeil(p);
    await offen(p);
    await p.waitForTimeout(300);
    a.nachOeffnen = await ansicht(p);
    a.weiter = await pfeil(p);
    await p.waitForFunction(() => GROSS.currSlide && GROSS.currIndex === 1, null, FRIST).catch(() => {});
    await p.waitForTimeout(300);
    a.nachBlaettern = await ansicht(p);
    a.zu = await schliessen(p);
  });
  // #706 (Nachtrag aus #689): Pfeilknopf, dann „Foto entfernen“ im Öffnen: die Frage meint das gezeigte Foto
  await ablauf("pfeilKlick", async (a, p, kopf, gesendet) => {
    await kopf.click();
    await p.waitForFunction(() => document.querySelector("#gross.pswp--ui-visible .gross-unten button.entfernen"), null, FRIST);
    a.pfeil = await pfeil(p);
    a.klick = await p.evaluate(() => {
      document.querySelector("#gross .gross-unten button.entfernen").click();
      return {isOpen: GROSS.opener.isOpen, index: GROSS.currIndex, gezeigt: GROSS.currSlide ? GROSS.currSlide.data.bild.id : null};
    });
    a.danach = await nachFrage(p);
    if (a.danach.da) { await knopf(p, T.ja).first().click(); await warten(gesendet, x => x.methode === "DELETE"); }
    else a.zu = await schliessen(p);
  });
  await ablauf("escape", async (a, p, kopf) => {
    await klickImOeffnen(a, p, kopf);
    await p.keyboard.press("Escape");
    a.danach = await nachFrage(p);
  });
  await ablauf("reduziert", async (a, p, kopf) => { await klickImOeffnen(a, p, kopf, 1, true); a.danach = await nachFrage(p); }, {reduziert: true});
  // Gegenprobe: Der Dialog bleibt aus (nur in dieser Seite); frage muss das melden statt weiterzulaufen
  await ablauf("gegenprobe", async (a, p, kopf) => {
    await p.evaluate(() => { bildEntfernenFragen = () => {}; });
    await grossAuf(p, kopf);
    await knopf(p, T.entfernen, "#gross").first().click();
    await frage(p, 1500);
    a.verschluckt = true;
  });
  await ablauf("mo", async (a, p, kopf, gesendet) => { a.loeschen = await loeschen(p, gesendet); },
               {person: {schluessel: "mo", name: "Mo", rolle: "mitwirkend"}});
  console.log(JSON.stringify({fehler, aus}));
} else if (art === "sw") {
  const [basis, ordner, ordnerNeu, marke, frist = "20000"] = rest;
  const ctx = await b.newContext();
  const p = await ctx.newPage();
  p.setDefaultTimeout(15000);
  p.on("pageerror", e => fehler.push("pageerror: " + e));
  // Übernimmt ein neuer Worker, lädt die Seite neu (controllerchange) und bricht eine laufende Auswertung ab: dann auf der
  // neu geladenen Seite noch einmal, begrenzt. Andere Fehler bleiben Fehler.
  async function auswerten(f, arg) {
    for (let versuch = 1; ; versuch++) {
      try { return await p.evaluate(f, arg); }
      catch (e) {
        if (versuch >= 5 || !/Execution context was destroyed/.test(e)) throw e;
        await p.waitForSelector("#main > *", {state: "attached"});
      }
    }
  }
  const zaehlen = () => auswerten(async m => {
    let n = 0;
    for (const name of await caches.keys()) {
      if (!name.startsWith("rh:")) continue;
      for (const r of await (await caches.open(name)).keys()) if (r.url.includes(m)) n++;
    }
    return n;
  }, marke);
  // Je Worker der Registrierung seine Version; null nur, wenn es ihn nicht gibt
  const zustaende = () => auswerten(async () => {
    const version = w => w ? new Promise(r => {
      const c = new MessageChannel();
      c.port1.onmessage = e => r(e.data);
      setTimeout(() => r(`keine Antwort (${w.state})`), 5000);
      w.postMessage({typ: "version"}, [c.port2]);
    }) : null;
    const reg = await navigator.serviceWorker.getRegistration() || {};
    const [installing, waiting, active] = await Promise.all([reg.installing, reg.waiting, reg.active].map(version));
    return {installing, waiting, active};
  });
  // Ein Anstoß: null oder der Grund, warum er scheiterte
  const anstossen = ende => auswerten(bis => Promise.race([
    navigator.serviceWorker.getRegistration().then(r => r.update()).then(() => null, e => String(e)),
    new Promise(r => setTimeout(() => r("update() ohne Ergebnis bis zum Ende der Frist"), bis - Date.now())),
  ]), ende);
  // Bis ein neuer Worker wartet oder übernommen hat, spätestens bis zum Ende der Frist. Zweimal derselbe Zustand: Auch ein
  // Worker, der sofort übernimmt, wartet für einen Augenblick. Antwortet ein Worker nicht, ist nichts entschieden.
  async function neuerWorker(alt, ende) {
    for (let letzter = ""; ; await leise(100)) {
      const z = await zustaende(), text = JSON.stringify(z);
      const entschieden = (z.waiting || z.active !== alt.active) && text === letzter && !text.includes("keine Antwort");
      if (entschieden || Date.now() >= ende) return z;
      letzter = text;
    }
  }
  // Nach einer Übernahme räumt activate den alten Speicher auf; gezählt wird erst danach
  const aufgeraeumt = ende => auswerten(async bis => {
    const reg = await navigator.serviceWorker.getRegistration();
    while (reg && reg.active && reg.active.state === "activating" && Date.now() < bis) await new Promise(r => setTimeout(r, 50));
  }, ende);

  await p.goto(basis);
  await p.evaluate(() => Promise.race([navigator.serviceWorker.ready, new Promise(r => setTimeout(r, 15000))]));
  await p.waitForFunction(() => navigator.serviceWorker.controller !== null, null, {timeout: 15000});
  const vorher = await zaehlen();
  const zustandVorher = await zustaende();
  // neuer Stand: das Bild ist entfernt (Dateien weg, Liste ohne Fassungen)
  fs.rmSync(ordner, {recursive: true, force: true});
  fs.cpSync(ordnerNeu, ordner, {recursive: true});
  await p.reload();
  await p.waitForSelector("#main > *", {state: "attached"});
  const start = Date.now(), ende = start + Number(frist), updateFehler = [];
  let anstoesse = 0, grund = null;
  do {
    if (grund) await leise(300);
    anstoesse++;
    grund = await anstossen(ende);
    if (grund) updateFehler.push(grund);
  } while (grund && Date.now() + 300 < ende);
  const zustandNachher = await neuerWorker(zustandVorher, ende);
  await aufgeraeumt(ende);
  const dauerMs = Date.now() - start;
  const nachher = await zaehlen();
  console.log(JSON.stringify({fehler, vorher, nachher, updateFehler, anstoesse, dauerMs,
                              zustaende: {vorher: zustandVorher, nachher: zustandNachher}}));
} else {
  console.error("unbekannte Art: " + art);
  process.exitCode = 2;
}
await b.close();
