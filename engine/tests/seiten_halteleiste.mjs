// Gegenprobe der Halteleiste (#665): Maße, Abstände und Farben von Punkt, Linie, Zeit und Halt-Marke, hell und dunkel, Handy
// und Rechner. Aufgerufen von test_zeitleiste_bewegung.py; die Werte vor dem Umbau auf gemeinsame Atome stehen in halteleiste_vorher.json.
// Aufruf: node seiten_halteleiste.mjs <playwright-modul> <basis-url> <datum>
const [, , modul, basis] = process.argv;
const pw = await import(modul);
const b = await pw[process.env.RH_BROWSER || "chromium"].launch();
const fehler = [], aus = {};
for (const [name, breite, schema] of [["handy-hell", 390, "light"], ["handy-dunkel", 390, "dark"], ["rechner-hell", 1200, "light"], ["rechner-dunkel", 1200, "dark"]]) {
  const ctx = await b.newContext({viewport: {width: breite, height: 900}, colorScheme: schema, serviceWorkers: "block"});
  await ctx.route("**/api/**", r => r.abort());
  const p = await ctx.newPage();
  p.on("pageerror", e => fehler.push(String(e)));
  await p.goto(basis + "#E-20");
  await p.waitForSelector("#E-20 ol.halte");
  await p.waitForTimeout(150);
  aus[name] = await p.evaluate(() => {
    const ol = document.querySelector("#E-20 ol.halte");
    const r = e => { const x = e.getBoundingClientRect(), o = ol.getBoundingClientRect();
      return [Math.round(x.left - o.left), Math.round(x.top - o.top), Math.round(x.width), Math.round(x.height)]; };
    const s = (e, ...felder) => { const c = getComputedStyle(e); return Object.fromEntries(felder.map(f => [f, c[f]])); };
    const linie = li => { const c = getComputedStyle(li, "::before");
      return {left: c.left, top: c.top, bottom: c.bottom, width: c.width, background: c.backgroundColor}; };
    return {ol: r(ol), punkte: [...ol.children].map(li => {
      const p = li.querySelector(".hl-p"), zeit = li.querySelector(".hl-zeit"), halt = li.querySelector(".hl-halt");
      return {klasse: li.className, box: r(li), linie: linie(li),
        punkt: p ? {box: r(p), ...s(p, "borderTopColor", "borderTopWidth", "backgroundColor", "borderRadius", "visibility")} : null,
        zeit: zeit ? {box: r(zeit), ...s(zeit, "fontSize", "color", "fontWeight", "fontVariantNumeric")} : null,
        halt: halt ? {box: r(halt), ...s(halt, "fontSize", "color", "backgroundColor", "borderRadius", "paddingLeft")} : null};
    })};
  });
  await ctx.close();
}
await b.close();
console.log(JSON.stringify({aus, fehler}));
