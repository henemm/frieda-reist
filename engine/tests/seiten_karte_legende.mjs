// Legende der Karten nach Arten am Telefon (ADR-0007 Schritt d, frieda-reist#296), aufgerufen von test_karte_legende.py.
// Aufruf: node seiten_karte_legende.mjs <playwright-modul> <basis-url> <breite>
// Misst an der Etappenkarte (Ebenenwahl nach Arten) und an der Karte eines Wissensabschnitts (Legende unter der Karte):
// Einträge mit Art-Namen, alles im Fenster, kein waagerechtes Scrollen, Ebene ausblenden und einblenden.
const [, , modul, basis, breite] = process.argv;
const pw = await import(modul);
const b = await pw[process.env.RH_BROWSER || "chromium"].launch();
const fehler = [], aus = {};
const ctx = await b.newContext({viewport: {width: Number(breite), height: 900}, serviceWorkers: "block", hasTouch: Number(breite) < 600, isMobile: Number(breite) < 600});
await ctx.route("**/api/**", r => r.abort());
const p = await ctx.newPage();
p.on("pageerror", e => fehler.push(String(e)));
const imFenster = (sel, ctxSel = "document") => p.evaluate(([s]) => [...document.querySelectorAll(s)].map(x => {
  const r = x.getBoundingClientRect();
  return {text: x.textContent.trim(), links: Math.round(r.left), rechts: Math.round(r.right), breit: Math.round(r.width), hoch: Math.round(r.height), innen: r.left >= -1 && r.right <= innerWidth + 1};
}), [sel]);
// Etappenkarte
await p.goto(basis + "#E-01");
await p.waitForSelector(".ekarte", {state: "attached"});
await p.locator(".ekarte").first().scrollIntoViewIfNeeded();   // gezeichnet wird erst, wenn die Karte im Bild ist
await p.waitForSelector(".ekarte .leaflet-marker-icon", {state: "attached"});
const marken = () => p.evaluate(() => document.querySelectorAll(".ekarte .rh-pw").length);
aus.etappe = {markenVorher: await marken(), schalter: await imFenster(".ekarte .leaflet-control-layers-toggle")};
await p.locator(".ekarte .leaflet-control-layers-toggle").first().click();
aus.etappe.ebenen = await imFenster(".ekarte .leaflet-control-layers-list label");
if (aus.etappe.ebenen.length) {
  // Leaflet klappt die Ebenenwahl beim Verlassen mit der Maus zu; Playwright rollt vor dem Klick, darum schaltet das DOM selbst
  const schalten = () => p.evaluate(() => document.querySelector(".ekarte .leaflet-control-layers-list input").click());
  await schalten();
  aus.etappe.markenAus = await marken();
  await schalten();
  aus.etappe.markenWieder = await marken();
}
aus.etappe.waagerecht = await p.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1);
// Karte eines Wissensabschnitts
const bloecke = await p.evaluate(() => Object.keys(D.wissen_karte ? D.wissen_karte.punkte : {}));
aus.bloecke = bloecke;
if (bloecke.length) {
  await p.goto(basis + "#" + bloecke[0].split(".")[0]);
  await p.waitForSelector(".wkarte", {state: "attached"});
  await p.locator(".wkarte").first().scrollIntoViewIfNeeded();
  await p.waitForSelector(".wkarte .legende span", {state: "attached"});
  aus.wissen = {legende: await imFenster(".wkarte .legende span"), waagerecht: await p.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1)};
}
await ctx.close();
await b.close();
console.log(JSON.stringify({fehler, aus}));
