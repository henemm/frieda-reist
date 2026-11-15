// Bilder Stufe 1 (#455, #581, V10): die gebaute Beispielreise unter der Meta-CSP img-src 'self' data:, aufgerufen von test_bilder.py.
// Aufruf: node seiten_bilder_csp.mjs <playwright-modul> <basis-url>
// Etappenkarte mit Kacheln (Attrappe) und Ebenen-Symbol (data:-Bild im CSS), Belege an einer Buchung, App-Symbol und ein Bild
// ![…](BI-NN) im Wissenstext mit Nennung. Jede Konsolenmeldung zur CSP („Content Security Policy“, „Refused to load“) und jeder
// Seitenfehler zählt als Fehler.
const [, , modul, basis] = process.argv;
const pw = await import(modul);
const b = await pw[process.env.RH_BROWSER || "chromium"].launch();
const fehler = [], aus = {};
const ctx = await b.newContext({viewport: {width: 1300, height: 900}, serviceWorkers: "block"});
await ctx.route("**/api/belege/**", r => r.fulfill({status: 200, contentType: "application/json", body: JSON.stringify(
  [{id: "x1", buchung: "B-01", name: "Bestätigung Hotel.pdf", groesse: 2048, wer: "Ida", hochgeladen: "2026-10-29T10:00:00", sichtbar: "alle"}])}));
await ctx.route(u => /\/api\//.test(u.pathname) && !/\/api\/belege\//.test(u.pathname), r => r.abort());
const p = await ctx.newPage();
p.on("pageerror", e => fehler.push("pageerror: " + e));
p.on("console", m => { if (/Content.Security.Policy|Refused to load/i.test(m.text())) fehler.push("console: " + m.text()); });

// Etappenkarte: Kacheln und Ebenen-Symbol
await p.goto(basis + "#E-01");
await p.waitForSelector(".ekarte", {state: "attached"});
await p.locator(".ekarte").first().scrollIntoViewIfNeeded();
await p.waitForSelector(".ekarte .leaflet-marker-icon", {state: "attached"});
await p.waitForTimeout(1000);
aus.karte = await p.evaluate(() => {
  const t = document.querySelector(".ekarte .leaflet-control-layers-toggle");
  return {marken: document.querySelectorAll(".ekarte .leaflet-marker-icon").length,
    kacheln: document.querySelectorAll(".ekarte .leaflet-tile").length,
    ebenenSymbol: t ? getComputedStyle(t).backgroundImage.startsWith("url(\"data:") : false};
});

// App-Symbol (Symbole im Kopf der Seite)
aus.symbol = await p.evaluate(async () => {
  const laden = src => new Promise(r => { const i = new Image(); i.onload = () => r(i.naturalWidth > 0); i.onerror = () => r(false); i.src = src; });
  return Promise.all([...document.querySelectorAll("link[rel~=icon], link[rel=apple-touch-icon]")].map(l => laden(l.getAttribute("href"))));
});

// Belege an der Buchung B-01 (Liste vom Rückmeldedienst, hier ersetzt)
await p.goto(basis + "#U-01");
await p.waitForSelector("[id='B-01'] .beleg", {state: "attached", timeout: 15000}).catch(() => {});
aus.beleg = await p.evaluate(() => document.querySelectorAll("[id='B-01'] .beleg a").length);

// Bild im Wissenstext mit Namensnennung
await p.goto(basis + "#W-05");
await p.waitForSelector("img[src^='medien/bilder/']", {state: "attached"});
await p.evaluate(() => document.querySelectorAll("img[src^='medien/bilder/']").forEach(i => { i.loading = "eager"; i.scrollIntoView(); }));
await p.waitForFunction(() => [...document.querySelectorAll("img[src^='medien/bilder/']")].every(i => i.complete), null, {timeout: 15000});
aus.bild = await p.evaluate(() => [...document.querySelectorAll("img[src^='medien/bilder/']")].map(i => ({
  src: i.getAttribute("src"), breite: i.naturalWidth,
  nennung: (i.parentElement.querySelector("small.nennung") || {}).textContent || ""})));
await ctx.close();
await b.close();
console.log(JSON.stringify({fehler, aus}));
