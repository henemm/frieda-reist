// Status der Reise auf der Seite (#513), aufgerufen von test_seite.py. Die Dienste sind nachgestellt: api/ich liefert die
// Person (Rolle aus dem Aufruf) und einen Statushinweis, api/status antwortet wie der Rückmeldedienst; alles andere 404.
// Aufruf: node seiten_status.mjs <playwright-modul> <basis-url> <rolle>
const [, , modul, basis, rolle] = process.argv;
const pw = await import(modul);
const b = await pw[process.env.RH_BROWSER || "chromium"].launch();
const fehler = [], aus = {gesendet: []};
const ctx = await b.newContext({viewport: {width: 390, height: 900}, serviceWorkers: "block"});
await ctx.route("**/api/**", async r => {
  const pfad = new URL(r.request().url()).pathname.split("/api/")[1];
  if (pfad === "ich") return r.fulfill({contentType: "application/json", body: JSON.stringify({
    basis: new URL(basis).origin, konto: {name: "Ida", email: "ida@beispiel.invalid", sprache: "de"},
    person: {schluessel: "ida", name: "Ida", rolle},
    meldungen: [{id: "M-1", erstellt: "2027-05-06T07:10:00+00:00", text: "Die Reise beginnt in 7 Tagen (Do., 13.5.) und steht noch auf „Planung“. Auf „fest“ stellen?",
                 art: "status", status_bei: "planung", status_ziel: "fest", gelesen: false}]})});
  if (pfad === "status") {
    aus.gesendet.push(JSON.parse(r.request().postData() || "{}"));
    return r.fulfill({contentType: "application/json", body: JSON.stringify({ok: true, status: "fest"})});
  }
  return r.fulfill({status: 404, contentType: "application/json", body: "{}"});
});
const p = await ctx.newPage();
p.on("pageerror", e => fehler.push(String(e)));
await p.goto(basis);
await p.waitForSelector("#reiseStatus .status-pille");
const stand = () => p.evaluate(() => ({
  etikett: document.querySelector("#reiseStatus .status-pille").textContent,
  knopf: document.querySelector("#reiseStatus .status-pille").tagName === "BUTTON",
  offen: !!document.querySelector("#reiseStatus .status-feld:not([hidden])"),
  gewaehlt: (document.querySelector("#reiseStatus input:checked") || {}).value || null,
  bestaetigen: (b => b && !b.hidden ? b.textContent : null)(document.querySelector("#reiseStatus .status-knoepfe .ja")),
  meldung: [...document.querySelectorAll("#reiseStatus .status-meldung")].map(x => x.textContent).join(" ").trim(),
  fuerDich: document.querySelector("#fuerDich").hidden ? null : document.querySelector("#fuerDich").textContent,
  hinweisKnopf: (document.querySelector("#fuerDich .fd-knopf") || {}).textContent || null,
  breit: document.documentElement.scrollWidth > innerWidth + 1,
}));
aus.start = await stand();
if (rolle === "organisator") {
  await p.locator("#fuerDich .fd-knopf").click();              // Hinweis öffnet die Auswahl mit „fest“ gewählt
  aus.hinweis = await stand();
  await p.locator("#reiseStatus .status-knoepfe button:not(.ja)").click();
  await p.locator("#reiseStatus button.status-pille").click();   // Etikett öffnet die Auswahl mit dem jetzigen Status
  aus.auf = await stand();
  await p.locator('#reiseStatus input[value="fest"]').check();
  aus.wahl = await stand();
  await p.locator("#reiseStatus .status-knoepfe .ja").click();
  await p.waitForFunction(() => document.querySelector("#reiseStatus .status-pille").textContent.startsWith("Fest"));
  aus.danach = await stand();
}
aus.fehler = fehler;
console.log(JSON.stringify(aus));
await b.close();
