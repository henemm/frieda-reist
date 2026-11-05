// Route „zu-tun“ und alter Link „#offen“ (frieda-reist#215), aufgerufen von test_altformen_rest_215.py.
// Aufruf: node seiten_altformen_215.mjs <playwright-modul> <basis-url>
// Meldet: Hash nach Klick auf den Reiter, ob der Reiter aktiv und der Inhalt sichtbar ist, dasselbe für den alten Link #offen
// (mit Länge des Verlaufs vorher und nachher) und den Reiter, auf dem die Seite ohne Sprungziel beginnt.
const [, , modul, basis] = process.argv;
const pw = await import(modul);
const b = await pw[process.env.RH_BROWSER || "chromium"].launch();
const ctx = await b.newContext({viewport: {width: 390, height: 844}, serviceWorkers: "block"});
await ctx.route("**/api/**", r => r.abort());
const p = await ctx.newPage();
const fehler = [];
p.on("pageerror", e => fehler.push(String(e)));
const warte = async () => { await p.waitForSelector("#titel:not(:empty)"); await p.waitForTimeout(400); };
const zustand = () => p.evaluate(() => ({
  hash: location.hash,
  aktiv: !!document.querySelector('nav a[href="#zu-tun"][aria-current], nav a[href="#zu-tun"].aktiv, nav a[href="#zu-tun"][aria-selected="true"]'),
  sichtbar: !!document.querySelector("#main #zu-buchen, #main #aufgaben, #main #zu-entscheiden, #main #fragen, #main #rueckmeldungen"),
}));

// Test 1: Reiter anklicken
await p.goto(basis);
await warte();
const start = await p.evaluate(() => (document.querySelector("nav a[aria-current], nav a.aktiv, nav a[aria-selected='true']") || {}).hash || "");
await p.click('nav a[href="#zu-tun"]');
await p.waitForTimeout(400);
const reiter = await zustand();

// Test 2: alter Link #offen beim Start
await p.goto("about:blank");
await p.goto(basis + "#offen");
await warte();
const vorher = await p.evaluate(() => history.length);
const alt = await zustand();
const nachher = await p.evaluate(() => history.length);

// hashchange: von einem anderen Reiter auf #offen wechseln
await p.evaluate(() => { location.hash = "wissen"; });
await p.waitForTimeout(300);
await p.evaluate(() => { location.hash = "offen"; });
await p.waitForTimeout(400);
const gewechselt = await p.evaluate(() => location.hash);

// Test 3: Startreiter ohne Sprungziel
await p.goto("about:blank");
await p.goto(basis);
await warte();
const beginn = await p.evaluate(() => {
  const a = document.querySelector("nav a[aria-current], nav a.aktiv, nav a[aria-selected='true']");
  return a ? a.getAttribute("href").replace("#", "") : "";
});
await b.close();
console.log(JSON.stringify({
  fehler, start,
  reiter_hash: reiter.hash, reiter_aktiv: reiter.aktiv, reiter_sichtbar: reiter.sichtbar,
  alt_hash: alt.hash, alt_aktiv: alt.aktiv, alt_sichtbar: alt.sichtbar,
  alt_verlauf_vorher: vorher, alt_verlauf: nachher, alt_hashchange: gewechselt, start_aktiv: beginn,
}));
