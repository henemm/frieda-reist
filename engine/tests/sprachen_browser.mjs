// Umschalter der Sprache im Browser (ADR-0006), aufgerufen von test_seite_sprachen.py.
// Aufruf: node sprachen_browser.mjs <playwright-modul> <basis-url> <sprache-zum-umschalten>
// Meldet als JSON: Sprache beim Start, Knöpfe, Wirkung des Umschaltens (lang, dir, Wörter, Wochentag), ob die Wahl das Neuladen
// überlebt und ob das Zurückschalten die Ansicht wieder genau wie vorher zeichnet.
const [, , modul, basis, ziel] = process.argv;
const pw = await import(modul);
const b = await pw[process.env.RH_BROWSER || "chromium"].launch();
const ctx = await b.newContext({viewport: {width: 390, height: 900}, serviceWorkers: "block"});
await ctx.route("**/api/**", r => r.abort());
const p = await ctx.newPage();
const fehler = [];
p.on("pageerror", e => fehler.push(String(e)));
await p.clock.setFixedTime(new Date("2026-10-27T10:00:00"));
const stand = () => p.evaluate(() => ({
  lang: document.documentElement.lang, dir: document.documentElement.dir, locale: LOCALE,
  knoepfe: [...document.querySelectorAll("#sprachen button")].map(k => [k.dataset.sprache, k.textContent, k.getAttribute("aria-pressed")]),
  gewaehlt: STATUS_TEXT.gewaehlt, erledigt: AG_STATUS.erledigt, wochentag: wochentag("2027-05-13"),
  main: (() => {   // wie im Rundgang: ohne Karteninhalt (lädt zeitversetzt) und ohne Blitz
    const c = document.querySelector("#main").cloneNode(true);
    c.querySelectorAll(".regionen").forEach(x => x.querySelectorAll("[aria-pressed]").forEach(k => k.removeAttribute("aria-pressed")));
    c.querySelectorAll(".kartenbox").forEach(x => x.replaceWith(Object.assign(document.createElement("div"), {className: "kartenbox"})));
    c.querySelectorAll(".blitz").forEach(x => x.classList.remove("blitz"));
    return c.innerHTML;
  })(),
}));
const oeffnen = async () => { await p.goto(basis + "#varianten"); await p.waitForSelector("#titel:not(:empty)"); await p.waitForTimeout(300); };
await oeffnen();
const start = await stand();
await p.click(`#sprachen button[data-sprache="${ziel}"]`);
await p.waitForTimeout(300);
const umgeschaltet = await stand();
await p.reload();
await p.waitForSelector("#titel:not(:empty)");
await p.waitForTimeout(300);
const nachNeuladen = await stand();
await p.click(`#sprachen button[data-sprache="${start.lang}"]`);
await p.waitForTimeout(300);
const zurueck = await stand();
await b.close();
const kurz = ({main, ...rest}) => rest;
console.log(JSON.stringify({fehler, start: kurz(start), umgeschaltet: kurz(umgeschaltet), nachNeuladen: kurz(nachNeuladen), zurueck: kurz(zurueck),
  gleichNachZurueck: zurueck.main === start.main, anders: umgeschaltet.main !== start.main}));
