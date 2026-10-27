// Anmeldung auf der Reiseseite (Paket J2), aufgerufen von test_seite.py mit laufendem Rückmeldedienst.
// Aufruf: node seiten_konto.mjs <playwright-modul> <basis-url> <dienst-url> <sitzung|->
// Die Seite spricht api/… an; die Anfragen gehen an den echten Dienst, mit dem Sitzungs-Cookie, wenn eins angegeben ist
// (der Cookie __Host-… verlangt https, deshalb setzt ihn hier die Weiterleitung statt des Browsers).
// Meldet: Konto-Knopf (Text, Ziel), Namensfeld, Meldung nach dem Senden und Skriptfehler.
const [, , modul, basis, dienst, sitzung] = process.argv;
const pw = await import(modul);
const b = await pw[process.env.RH_BROWSER || "chromium"].launch();
const fehler = [], aus = {};
const reise = new URL(basis).pathname.split("/").filter(Boolean)[0];

const ctx = await b.newContext({viewport: {width: 390, height: 900}, serviceWorkers: "block"});
await ctx.route("**/api/**", async r => {
  const pfad = new URL(r.request().url()).pathname.split("/api/")[1];
  const kopf = await r.request().allHeaders();
  if (sitzung !== "-") kopf.cookie = `__Host-frieda=${sitzung}`;
  r.fulfill({response: await r.fetch({url: `${dienst}/${reise}/${pfad}`, headers: kopf})});
});
await ctx.addInitScript(() => localStorage.setItem("rh-name", "Hanna"));
const p = await ctx.newPage();
p.on("pageerror", e => fehler.push(String(e)));
await p.goto(basis + "#plan");
await p.waitForSelector("#konto", {timeout: 5000}).catch(() => {});
aus.knopf = await p.evaluate(() => { const k = document.querySelector("#konto"); return k ? {text: k.textContent, ziel: k.getAttribute("href")} : null; });
await p.locator("[data-rm]").first().click();
await p.waitForSelector("#rmForm");
aus.nameFeld = await p.evaluate(() => { const n = document.querySelector("#rmName"); return n ? n.type : null; });
aus.hinweis = await p.evaluate(() => [...document.querySelectorAll("#rmForm .meldung")].map(x => x.textContent));
await p.fill("#rmText", "Gern früher losgehen");
await p.locator('#rmForm button[type="submit"]').click();
await p.waitForFunction(() => /Danke|Gespeichert|Nicht angenommen/.test((document.querySelector("#rmMeldung") || {}).textContent || ""), null, {timeout: 5000});
aus.meldung = await p.locator("#rmMeldung").textContent();
aus.fehler = fehler;
await b.close();
console.log(JSON.stringify(aus));
