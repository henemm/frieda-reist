// Ort im Ort (ADR-0008, Schritt d, frieda-reist#335), aufgerufen von test_ort_im_ort.py.
// Aufruf: node seiten_ort_im_ort.mjs <playwright-modul> <basis-url> <ort>...
// Meldet je Ortsseite: Titel, „liegt in“ (Text und Link), die Orte darin, die Ortskarte (Marken) und Fehler der Seite.
const [, , modul, basis, ...orte] = process.argv;
const pw = await import(modul);
const b = await pw[process.env.RH_BROWSER || "chromium"].launch();
const fehler = [];
const ctx = await b.newContext({viewport: {width: 1300, height: 900}, serviceWorkers: "block"});
await ctx.route("**/api/**", r => r.abort());
const out = {fehler};
for (const oid of orte) {
  const p = await ctx.newPage();
  p.on("pageerror", e => fehler.push(String(e)));
  await p.goto(basis + "#" + oid);
  await p.waitForSelector("#main > *");
  await p.waitForTimeout(400);
  out[oid] = await p.evaluate(oid => {
    const l = document.querySelector("#main .ort-liegt-in"), d = document.querySelector("#main .ort-darin"), k = document.querySelector("#main .ortskarte");
    return {
      titel: (document.querySelector("#main h2") || {}).textContent || "",
      liegtIn: l ? l.textContent.trim() : null,
      liegtInLink: l && l.querySelector("a") ? l.querySelector("a").getAttribute("href") : null,
      darin: d ? [...d.querySelectorAll(".wzeile")].map(z => ({href: z.getAttribute("href"), id: z.id || null, text: z.textContent})) : [],
      darinKopf: d ? d.querySelector("h3").textContent : null,
      karte: !!k,
      hier: k ? k.querySelectorAll(".rh-hier").length : 0,
      darinMarken: k ? k.querySelectorAll(".rh-darin").length : 0,
      dinge: k ? k.querySelectorAll(".rh-ding").length : 0,
    };
  }, oid);
  await p.close();
}
await b.close();
console.log(JSON.stringify(out));
