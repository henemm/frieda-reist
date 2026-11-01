// Namen statt Kennungen in Buchung und Anschlusswarnung (#189), aufgerufen von test_seite.py.
// Aufruf: node namen_browser.mjs <playwright-modul> <basis-url>
// Meldet: Text und Links der „Einzelheiten zur Buchung“ von B-02 und alle Anschlusswarnungen, die auf den Ansichten stehen.
const [, , modul, basis] = process.argv;
const pw = await import(modul);
const b = await pw[process.env.RH_BROWSER || "chromium"].launch();
const ctx = await b.newContext({viewport: {width: 390, height: 900}, serviceWorkers: "block"});
await ctx.route("**/api/**", r => r.abort());
const p = await ctx.newPage();
const fehler = [];
p.on("pageerror", e => fehler.push(String(e)));
await p.clock.setFixedTime(new Date("2026-10-27T10:00:00"));
const oeffnen = async hash => { await p.goto(basis + hash); await p.waitForSelector("#titel:not(:empty)"); await p.waitForTimeout(300); };

await oeffnen("#B-02");
const buchung = await p.evaluate(() => {
  const d = [...document.querySelectorAll("#B-02 details.einzelheiten")].pop();
  return d ? {text: d.textContent, links: [...d.querySelectorAll("a[href^='#E-']")].map(a => [a.getAttribute("href"), a.textContent])} : null;
});
const warnungen = new Set();
for (const h of ["", "#plan", "#varianten", "#T-02"]) {
  await oeffnen(h);
  for (const t of await p.evaluate(() => [...document.querySelectorAll(".warnungen li")].map(li => li.textContent)))
    if (/Anschluss/.test(t)) warnungen.add(t);
}
await b.close();
console.log(JSON.stringify({fehler, buchung, warnungen: [...warnungen]}));
