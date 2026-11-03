// Elternbezug (ADR-0007, frieda-reist#282), aufgerufen von test_elternbezug.py.
// Aufruf: node seiten_elternbezug.mjs <playwright-modul> <basis-url> <aufenthalt> <ort>
// Meldet, wo der Aufenthalt vollständig steht (Ortsseite) und wo nur als Zeile mit Link (Reise, Karte).
const [, , modul, basis, aid, ort] = process.argv;
const pw = await import(modul);
const b = await pw[process.env.RH_BROWSER || "chromium"].launch();
const fehler = [];
const ctx = await b.newContext({viewport: {width: 1300, height: 900}, serviceWorkers: "block"});
await ctx.route("**/api/**", r => r.abort());
const seite = async hash => {
  const p = await ctx.newPage();
  p.on("pageerror", e => fehler.push(String(e)));
  await p.goto(basis + (hash ? "#" + hash : ""));
  await p.waitForSelector("#main > *");
  return p;
};
const messen = (p, aid) => p.evaluate(aid => ({
  hash: location.hash,
  voll: document.querySelectorAll(`#main [data-ziel="${aid}"]`).length,
  zeilen: [...document.querySelectorAll("#main .z.aufenthalt")].filter(z => !z.hasAttribute("data-ziel") && z.textContent.includes(aid) || false).length,
  links: [...document.querySelectorAll(`#main a[href="#${aid}"]`)].length,
  tagseite: !!document.querySelector(".tagseite"),
}), aid);
const out = {};
let p = await seite(ort);
out.ort = await messen(p, aid);
await p.close();
p = await seite("");
out.start = await messen(p, aid);
await p.close();
p = await seite("karte");
out.karte = await messen(p, aid);
await p.close();
// Der Link führt zur Heimat: auf die Ortsseite
p = await seite(aid);
out.ziel = await messen(p, aid);
out.ziel.ortsseite = await p.evaluate(ort => !!document.querySelector(`#main h2[data-ziel="${ort}"], #main [data-ziel="${ort}"]`), ort);
await p.close();
await b.close();
console.log(JSON.stringify({fehler, ...out}));
