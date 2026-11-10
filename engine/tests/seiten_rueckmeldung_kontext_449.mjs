// Kontext einer Rückmeldung (frieda-reist#449), aufgerufen von test_rueckmeldung_kontext_449.py.
// Aufruf: node seiten_rueckmeldung_kontext_449.mjs <playwright-modul> <url> <hash> <selektor> <modus>
// Modus "online": Dienst antwortet 201; Modus "offline": POST bricht ab, danach Wechsel der Ansicht und Nachreichen.
// Ausgabe: JSON mit den gesendeten Bodys, dem Reise-Stand der Seite und den Skriptfehlern.
const [, , modul, url, hash, selektor, modus] = process.argv;
const pw = await import(modul);
const b = await pw[process.env.RH_BROWSER || "chromium"].launch();
const ctx = await b.newContext({viewport: {width: 1300, height: 900}, serviceWorkers: "block"});
const bodys = [], fehler = [];
let netz = modus !== "offline";
await ctx.route("**/api/**", r => {
  const q = r.request();
  if (q.method() === "POST") {
    if (!netz) return r.abort();
    bodys.push(JSON.parse(q.postData()));
    return r.fulfill({status: 201, contentType: "application/json",
      body: JSON.stringify({id: "R-20260101-000000-abcd", status: "neu", erstellt: "2026-01-01T00:00:00+00:00", ...JSON.parse(q.postData())})});
  }
  return r.fulfill({status: 200, contentType: "application/json", body: "[]"});
});
const p = await ctx.newPage();
p.on("pageerror", e => fehler.push(String(e)));
await p.goto(url + (hash ? "#" + hash : ""));
await p.waitForSelector("#main *");
await p.locator(selektor).first().dispatchEvent("click");   // Karten und Einblendungen verdecken oder bewegen den Knopf: Klick direkt am Knopf auslösen
await p.fill("#rmText", "Was ist das?");
await p.click("#rmForm button[type=submit]");
await p.waitForTimeout(600);
if (modus === "offline") {
  await p.evaluate(() => { document.querySelector("#rm").close(); location.hash = "#wissen"; });
  await p.waitForTimeout(300);
  netz = true;
  await p.evaluate(() => ausgangSenden());
  await p.waitForTimeout(300);
}
const rs = await p.evaluate(() => (typeof RS !== "undefined" && RS) ? RS.nummer : null);
await b.close();
console.log(JSON.stringify({bodys, rs, fehler}));
