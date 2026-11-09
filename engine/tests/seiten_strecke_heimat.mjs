// Fahrt an ihrer Heimat (#448), aufgerufen von test_seite.py.
// Aufruf: node seiten_strecke_heimat.mjs <playwright-modul> <basis-url> <datum>
// Meldet, wohin #E-20 führt und was die Fahrt an ihrer Heimat (Tagesseite) zeigt.
const [, , modul, basis] = process.argv;
const pw = await import(modul);
const b = await pw[process.env.RH_BROWSER || "chromium"].launch();
const ctx = await b.newContext({viewport: {width: 390, height: 900}, serviceWorkers: "block"});
await ctx.route("**/api/**", r => r.abort());
const p = await ctx.newPage();
const fehler = [];
p.on("pageerror", e => fehler.push(String(e)));
await p.goto(basis + "#E-20");
await p.waitForSelector("#E-20");
const heimat = await p.evaluate(() => {
  const z = document.getElementById("E-20");
  return {hash: location.hash, tagseite: !!z.closest(".tagseite"), text: z.textContent.replace(/\s+/g, " ").trim(),
    eigenerLink: !!z.querySelector('a[href="#E-20"]')};
});
await b.close();
console.log(JSON.stringify({heimat, fehler}));
