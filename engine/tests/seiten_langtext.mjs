// Baustein Langtext (#594), aufgerufen von test_textform.py.
// Aufruf: node seiten_langtext.mjs <playwright-modul> <basis-url> <anker>...
// Meldet je Anker, was die Langtexte im Hauptbereich zeigen (Listenpunkte, Fettes, Links mit Ziel, eingeschleuste Tags als
// Element) und Fehler der Seite.
const [, , modul, basis, ...anker] = process.argv;
const pw = await import(modul);
const b = await pw[process.env.RH_BROWSER || "chromium"].launch();
const fehler = [];
const ctx = await b.newContext({viewport: {width: 1300, height: 900}, serviceWorkers: "block"});
await ctx.route("**/api/**", r => r.abort());
const out = {fehler};
for (const a of anker) {
  const p = await ctx.newPage();
  p.on("pageerror", e => fehler.push(String(e)));
  await p.goto(basis + "#" + a);
  await p.waitForSelector("#main > *");
  await p.waitForTimeout(400);
  out[a] = await p.evaluate(() => {
    const lt = [...document.querySelectorAll("#main .langtext")];
    const text = lt.map(e => e.textContent).join(" | ");
    return {anzahl: lt.length, li: lt.reduce((n, e) => n + e.querySelectorAll("li").length, 0),
            fett: lt.reduce((n, e) => n + e.querySelectorAll("strong").length, 0),
            links: lt.flatMap(e => [...e.querySelectorAll("a[href^='http']")].map(x => [x.getAttribute("target"), x.getAttribute("rel")])),
            fremd: lt.reduce((n, e) => n + e.querySelectorAll("img, script, h1, h2, h3, table, iframe").length, 0),
            sterne: /\*\*/.test(text), text};
  });
  await p.close();
}
await b.close();
console.log(JSON.stringify(out));
