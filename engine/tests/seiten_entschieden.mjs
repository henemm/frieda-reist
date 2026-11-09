// Entschiedene Wahlstelle unter „Entschieden“ (#450), aufgerufen von test_eine_seitenordnung.py.
// Aufruf: node seiten_entschieden.mjs <playwright-modul> <basis-url> <json: {tage, sprung}>
const [, , modul, basis, auftragText] = process.argv;
const auftrag = JSON.parse(auftragText);
const pw = await import(modul);
const b = await pw[process.env.RH_BROWSER || "chromium"].launch();
const ctx = await b.newContext({viewport: {width: 390, height: 844}, serviceWorkers: "block"});
await ctx.route("**/api/**", r => r.abort());
const p = await ctx.newPage();
const fehler = [];
p.on("pageerror", e => fehler.push(String(e)));
await p.clock.setFixedTime(new Date("2026-11-02T10:00:00"));
const gehe = async hash => {
  await p.goto(basis + "#" + hash);
  await p.waitForSelector("#titel:not(:empty)");
  await p.waitForTimeout(300);
};
// über alle Tagesseiten: steht V-01 an einem Tag, oder steht dort „Zur Wahl“?
const tag = {v01: false, zurWahl: false};
for (const t of auftrag.tage) {
  await gehe(t);
  const x = await p.evaluate(() => ({v01: !!document.querySelector("#main [id='V-01']"),
    zurWahl: [...document.querySelectorAll("#main h3")].some(h => h.textContent === "Zur Wahl")}));
  tag.v01 ||= x.v01; tag.zurWahl ||= x.zurWahl;
}
await gehe("varianten");
const reise = await p.evaluate(() => {
  const d = document.querySelector("#main details.entschieden");
  if (!d) return {entschieden: 0};
  const e = d.querySelector("details.entscheidung");
  return {entschieden: d.querySelectorAll("details.entscheidung").length, zu: !d.open && !e.open,
    zeile: [...e.querySelector("summary").children].map(x => x.textContent).join(" ").replace(/\s+/g, " ").trim(), nichtGewaehlt: e.querySelectorAll(":scope > .option").length - 1};
});
const sprung = {};
for (const id of auftrag.sprung) {
  await gehe(id);
  sprung[id] = await p.evaluate(id => {
    const z = document.getElementById(id), blk = z && z.closest("details.entschieden");
    return {reiter: (document.querySelector("#nav a.on") || {getAttribute: () => "#"}).getAttribute("href").slice(1),
      imBlock: !!blk, offen: !!blk && blk.open && !!z.closest("details.entscheidung").open};
  }, id);
}
await b.close();
console.log(JSON.stringify({fehler, tag, reise, sprung}));
