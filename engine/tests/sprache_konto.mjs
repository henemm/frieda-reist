// Sprache angemeldet und als Gast (#188), aufgerufen von test_seite_sprachen.py.
// Aufruf: node sprache_konto.mjs <playwright-modul> <basis-url> <sprache-des-kontos>
// Angemeldet (api/ich mit Konto) muss die Seite die Sprache des Kontos sprechen, ohne Umschalter; als Gast (Dienst nicht
// erreichbar) steht der Umschalter als Zeile im Fuß, nie im Kopf.
const [, , modul, basis, kontoSprache] = process.argv;
const pw = await import(modul);
const b = await pw[process.env.RH_BROWSER || "chromium"].launch();
const fehler = [];

async function besuch(ich) {
  const ctx = await b.newContext({viewport: {width: 390, height: 900}, serviceWorkers: "block"});
  await ctx.route("**/api/**", r => ich && r.request().url().endsWith("/api/ich")
    ? r.fulfill({status: 200, contentType: "application/json", body: JSON.stringify(ich)}) : r.abort());
  const p = await ctx.newPage();
  p.on("pageerror", e => fehler.push(String(e)));
  await p.goto(basis);
  await p.waitForSelector("#titel:not(:empty)");
  await p.waitForTimeout(500);
  const stand = await p.evaluate(() => {
    const s = document.querySelector("#sprachen"), f = document.querySelector("#fuss");
    return {
      lang: document.documentElement.lang,
      imKopf: document.querySelectorAll("header [data-sprache]").length,
      imFuss: s.closest("footer") === f ? s.querySelectorAll("button[data-sprache]").length : -1,
      sichtbar: !s.hidden && !f.hidden && s.getBoundingClientRect().height > 0,
      zeile: s.textContent,
      gemerkt: localStorage.getItem(SP + "sprache"),
    };
  });
  await ctx.close();
  return stand;
}

const angemeldet = await besuch({basis: null, anmeldung: "uebergang", person: null,
  konto: {name: "Ida", email: "ida@beispiel.invalid", sprache: kontoSprache}});
const gast = await besuch(null);
await b.close();
console.log(JSON.stringify({fehler, angemeldet, gast}));
