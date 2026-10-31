// Heimat einer Unterkunft über mehrere Nächte (ADR-0003, frieda-reist#157), aufgerufen von test_heimat_unterkunft.py.
// Aufruf: node seiten_heimat_unterkunft.mjs <playwright-modul> <basis-url> <unterkunft> <tag> [<tag> …]
// Ruft die Tagesseite jeder Nacht direkt auf und meldet, ob die Nacht die Unterkunft vollständig (Karte) oder als Zeile
// zeigt und wohin ihre Links führen. Danach folgt es dem Link der letzten Nacht und meldet, wo es landet.
const [, , modul, basis, uid, ...tage] = process.argv;
const pw = await import(modul);
const b = await pw[process.env.RH_BROWSER || "chromium"].launch();
const fehler = [], naechte = [];
const ctx = await b.newContext({viewport: {width: 1300, height: 900}, serviceWorkers: "block"});
await ctx.route("**/api/**", r => r.abort());
const neu = async () => {
  const p = await ctx.newPage();
  p.on("pageerror", e => fehler.push(String(e)));
  return p;
};
const nacht = (p, uid) => p.evaluate(uid => {
  const s = document.querySelector("#main #nacht");
  return {
    tag: location.hash.slice(1),
    da: !!s,
    karten: s ? s.querySelectorAll(`.karte[data-ziel="${uid}"]`).length : 0,
    links: s ? [...s.querySelectorAll(".meldung a")].map(a => a.getAttribute("href")) : [],
    kopf: (document.querySelector("#main .tagdatum") || {}).textContent || "",
  };
}, uid);
let p;
for (const tag of tage) {
  p = await neu();
  await p.goto(basis + "#" + tag);
  await p.waitForSelector(".tagseite");
  naechte.push(await nacht(p, uid));
  if (tag !== tage[tage.length - 1]) await p.close();
}
// Der Link der letzten (weiteren) Nacht führt zur Heimat: dort steht die Karte der Unterkunft
let ziel = null;
const a = await p.$("#main #nacht .meldung a");
if (a) {
  await a.click();
  await p.waitForFunction(uid => !!document.querySelector(`#main .karte[data-ziel="${uid}"]`), uid, {timeout: 10000}).catch(() => {});
  ziel = await p.evaluate(uid => ({
    hash: location.hash,
    tagseite: !!document.querySelector(".tagseite"),
    kopf: (document.querySelector("#main .tagdatum") || {}).textContent || "",
    karte: !!document.querySelector(`#main #nacht .karte[data-ziel="${uid}"]`),
  }), uid);
}
await p.close();
await b.close();
console.log(JSON.stringify({fehler, naechte, ziel}));
