// Startfehler-Meldung (frieda-reist#387), aufgerufen von test_startfehler_meldung_387.py.
// Aufruf: node seiten_startfehler_387.mjs <playwright-modul> <url> <modus>
// Modus "start": Seite laden, Zustand der Meldung berichten; bei vorhandener Meldung zusätzlich den Knopf drücken und prüfen,
//   ob die Seite neu geladen wurde. Modus "spaet": Seite laden, danach Fehler nach dem Start auslösen (Zeitgeber, abgelehntes Versprechen,
//   abgelehntes fetch) und prüfen, ob die Meldung fehlt.
const [, , modul, url, modus] = process.argv;
const pw = await import(modul);
const b = await pw[process.env.RH_BROWSER || "chromium"].launch();
const ctx = await b.newContext({viewport: {width: 1300, height: 900}, serviceWorkers: "block"});
await ctx.route("**/api/**", r => r.abort());
const p = await ctx.newPage();
p.on("pageerror", () => {});
await p.goto(url);
await p.waitForTimeout(800);
const lies = () => p.evaluate(() => {
  const e = document.getElementById("startfehler");
  const r = e ? e.getBoundingClientRect() : null;
  const k = e ? e.querySelector("button") : null;
  return {da: !!e, rolle: e ? e.getAttribute("role") : null, text: e ? e.textContent : "", knopf: k ? k.textContent : null,
          sichtbar: !!r && r.width > 0 && r.height > 0 && getComputedStyle(e).visibility !== "hidden" && getComputedStyle(e).display !== "none",
          imFenster: !!r && r.bottom > 0 && r.top < innerHeight, lang: document.documentElement.lang,
          anzahl: document.querySelectorAll("#startfehler").length};
});
const aus = {vorher: await lies()};
if (modus === "spaet") {
  await p.evaluate(() => {
    setTimeout(() => { throw new Error("spaeter Fehler"); }, 0);
    Promise.reject(new Error("spaeteres Versprechen"));
    fetch("/gibt-es-nicht-" + Date.now() + "/x.json").then(r => { throw new Error("fetch " + r.status); });
    fetch("http://127.0.0.1:1/").catch(() => {});
  });
  await p.waitForTimeout(800);
  aus.nachher = await lies();
} else if (aus.vorher.da) {
  await p.evaluate(() => { window.__marke = 1; });
  await Promise.all([p.waitForNavigation({timeout: 5000}).catch(() => null), p.click("#startfehler button")]);
  await p.waitForTimeout(500);
  aus.neuGeladen = await p.evaluate(() => window.__marke !== 1);
}
await b.close();
console.log(JSON.stringify(aus));
