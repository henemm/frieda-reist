// Lesetext an Unterkunft und Aufenthalt (frieda-reist#334), aufgerufen von test_ding_lesetext.py.
// Aufruf: node seiten_ding_lesetext.mjs <playwright-modul> <basis-url> <id>=<textstück>...
// Meldet je Ding: ob seine Karte (Element mit der ID) das Textstück und ein fettes Stichwort trägt, wie oft das Stück im
// ganzen Hauptbereich steht (nur an der Heimat), ob der Lesetext eine Herkunft trägt, die Quellen-Zeilen der Einzelheiten und
// Fehler der Seite.
const [, , modul, basis, ...paare] = process.argv;
const pw = await import(modul);
const b = await pw[process.env.RH_BROWSER || "chromium"].launch();
const fehler = [];
const ctx = await b.newContext({viewport: {width: 1300, height: 900}, serviceWorkers: "block"});
await ctx.route("**/api/**", r => r.abort());
const out = {fehler};
for (const paar of paare) {
  const [id, stueck] = paar.split("=");
  const p = await ctx.newPage();
  p.on("pageerror", e => fehler.push(String(e)));
  await p.goto(basis + "#" + id);
  await p.waitForSelector("#main > *");
  await p.waitForTimeout(400);
  out[id] = await p.evaluate(([id, stueck]) => {
    const k = document.getElementById(id), main = document.querySelector("#main");
    return {karte: !!k, imDing: k ? k.textContent.includes(stueck) : false, fett: k ? k.querySelectorAll("strong").length : 0,
            // #607: unter dem Lesetext keine Herkunft; die Quellen stehen klein in den Einzelheiten
            herkunftImText: k ? [...k.querySelectorAll(".inhalt")].some(x => /Herkunft|geschrieben am/.test(x.textContent)) : false,
            quellen: k ? [...k.querySelectorAll(":scope > details.einzelheiten > .z.klein")].map(x => x.textContent).filter(t => /^Quelle/.test(t)) : [],
            mal: main.textContent.split(stueck).length - 1};
  }, [id, stueck]);
  await p.close();
}
await b.close();
console.log(JSON.stringify(out));
