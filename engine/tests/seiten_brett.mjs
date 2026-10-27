// Wunsch-Brett im Browser (Paket G), aufgerufen von test_seite.py mit laufendem Rückmeldedienst.
// Aufruf: node seiten_brett.mjs <playwright-modul> <basis-url> <dienst-url> <name>
// Die Seite spricht api/… an; die Anfragen gehen an den echten Dienst (<dienst-url>/<reise>/…), solange „netz“ an ist.
// Mit RH_BILDER=<ordner> entstehen Bilder des Bretts (Handy und Rechner).
// Meldet je Schritt die Spalten (Wunschtext -> Spalte), die Bilanz, überstehende Breite am Handy und Skriptfehler.
const [, , modul, basis, dienst, name] = process.argv;
const pw = await import(modul);
const b = await pw[process.env.RH_BROWSER || "chromium"].launch();
const fehler = [], aus = {};
let netz = true, einmal429 = false;
const reise = new URL(basis).pathname.split("/").filter(Boolean)[0];

async function seite(breite) {
  const ctx = await b.newContext({viewport: {width: breite, height: 900}, serviceWorkers: "block"});
  await ctx.route("**/api/**", async r => {
    if (!netz) return r.abort();
    if (einmal429 && r.request().method() === "PATCH") { einmal429 = false; return r.fulfill({status: 429, contentType: "text/html", body: "<html>429</html>"}); }
    const pfad = new URL(r.request().url()).pathname.split("/api/")[1];
    r.fulfill({response: await r.fetch({url: `${dienst}/${reise}/${pfad}`})});
  });
  await ctx.addInitScript(n => localStorage.setItem("rh-name", n), name);
  const p = await ctx.newPage();
  p.on("pageerror", e => fehler.push(`${breite}: ${e}`));
  p.on("dialog", d => d.accept());
  await p.clock.setFixedTime(new Date("2027-05-14T10:00:00"));
  await p.goto(basis + "#wuensche");
  await p.waitForSelector(".brett .wu-karte");
  return p;
}

const stand = p => p.evaluate(() => ({
  spalten: Object.fromEntries([...document.querySelectorAll(".brett .wu-karte")].map(k =>
    [k.querySelector(".wu-kopf .text").textContent, k.closest(".spalte").dataset.spalte])),
  bilanz: [...document.querySelectorAll(".wu-person")].map(x => x.textContent),
  nachreichen: document.querySelectorAll(".wu-karte .chip.offen").length,
  breit: document.documentElement.scrollWidth > innerWidth + 1,
}));
const karte = (p, text) => p.locator(".wu-karte", {hasText: text});
const warte = (p, f, ...a) => p.waitForFunction(f, ...a, {timeout: 5000});

const p = await seite(390);
aus.start = await stand(p);
// Punkte auf den eigenen Wunsch
await karte(p, "Kirnitzschtalbahn").locator('[data-delta="1"]').click();
await warte(p, () => (document.querySelector(".wu-karte .wu-zahl") || {}).textContent === "1");
aus.punkte = await karte(p, "Kirnitzschtalbahn").locator(".wu-zahl").textContent();
aus.fremdePunkte = await karte(p, "Hohnstein").locator("[data-wu-punkte]").count();
// Abhaken (auch fremde Wünsche)
await karte(p, "Hohnstein").locator("[data-wu-erlebt]").click();
await warte(p, () => document.querySelector('[data-spalte="erlebt"] .wu-karte'));
aus.erlebt = await stand(p);
// Ohne Netz abhaken: wird gemerkt und beim nächsten Kontakt nachgereicht
netz = false;
await karte(p, "Kirnitzschtalbahn").locator("[data-wu-erlebt]").click();
await warte(p, () => document.querySelectorAll('[data-spalte="erlebt"] .wu-karte').length === 2);
aus.offline = await stand(p);
const ausgang = () => p.evaluate(r => JSON.parse(localStorage.getItem(`rh-${r}-brett-ausgang`) || "[]").length, reise);
aus.offline.ausgang = await ausgang();
// Ohne Netz einen Haken zurücknehmen, der schon auf dem Server ist: geht nicht (sonst löscht das Nachreichen fremde Haken)
await karte(p, "Hohnstein").locator("[data-wu-erlebt]").click();
await p.waitForTimeout(200);
aus.offline.zuruecknehmen = (await stand(p)).spalten;
// Wieder Netz, aber der Server meldet einmal „zu viele“ (429): der Haken bleibt gemerkt und kommt beim nächsten Mal an
netz = true; einmal429 = true;
await p.evaluate(() => dispatchEvent(new Event("online")));
for (let i = 0; i < 50 && einmal429; i++) await p.waitForTimeout(100);
await p.waitForTimeout(300);
aus.nach429 = await ausgang();
await p.evaluate(() => dispatchEvent(new Event("online")));
await warte(p, r => localStorage.getItem(`rh-${r}-brett-ausgang`) === "[]", reise);
await p.waitForTimeout(200);
aus.nachgereicht = await stand(p);
const bild = (x, n) => process.env.RH_BILDER ? x.screenshot({path: `${process.env.RH_BILDER}/brett-${n}.png`, fullPage: true}) : null;
await bild(p, "390");
// Breite Ansicht: Spalten nebeneinander
const g = await seite(1200);
await bild(g, "1200");
aus.breit = await g.evaluate(() => new Set([...document.querySelectorAll(".brett .spalte")].map(s => Math.round(s.getBoundingClientRect().left))).size);
await b.close();
console.log(JSON.stringify({...aus, fehler}));
