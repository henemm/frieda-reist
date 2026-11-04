// „Zu tun“ mit erledigten Buchungen (frieda-reist#314), aufgerufen von test_zu_tun_314.py.
// Aufruf: node seiten_zu_tun.mjs <playwright-modul> <basis-url>
// Meldet die Abschnitte von „Zu tun“ in ihrer Reihenfolge, die sichtbaren Zeilen in „Zu buchen“ (offen und gebucht) vor und
// nach dem Aufklappen und ob ein Link auf #zu-buchen den Abschnitt aufgeklappt zeigt.
const [, , modul, basis] = process.argv;
const pw = await import(modul);
const b = await pw[process.env.RH_BROWSER || "chromium"].launch();
const ctx = await b.newContext({viewport: {width: 390, height: 844}, serviceWorkers: "block"});
await ctx.route("**/api/**", r => r.abort());
const p = await ctx.newPage();
const fehler = [];
p.on("pageerror", e => fehler.push(String(e)));
const zeilen = () => p.evaluate(() => {
  const s = document.querySelector("#main #zu-buchen");
  const sichtbar = s ? [...s.querySelectorAll(".wzeile")].filter(z => z.checkVisibility()) : [];
  return {da: !!s, offen: sichtbar.filter(z => z.querySelector(".chip.offen")).length, gebucht: sichtbar.filter(z => !z.querySelector(".chip.offen")).length};
});
await p.goto(basis + "#offen");
await p.waitForSelector("#titel:not(:empty)");
await p.waitForTimeout(400);
const reihe = await p.evaluate(() => [...document.querySelectorAll("#main section.ziel, #main details.ziel")].map(s => s.id));
const vorher = await zeilen();
await p.evaluate(() => document.querySelectorAll("#main #zu-buchen details, #main details#zu-buchen").forEach(d => { d.open = true; }));
const nachher = await zeilen();
await p.goto("about:blank");
await p.goto(basis + "#zu-buchen");
await p.waitForSelector("#titel:not(:empty)");
await p.waitForTimeout(400);
const link = await zeilen();
await b.close();
console.log(JSON.stringify({fehler, reihe, vorher, nachher, link}));
