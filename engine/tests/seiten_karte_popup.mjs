// Punkte der automatischen Karte mit Popup und Kurztext (frieda-reist#310), aufgerufen von test_karte_popup_310.py.
// Aufruf: node seiten_karte_popup.mjs <playwright-modul> <basis-url> <ding-id> <ansicht>
// 390 px: Tipp auf den Punkt, meldet das Popup (Text, Links, ganz im Bild). 1300 px: Überfahren, meldet den Kurztext.
// Danach die Ansicht: Ausschnitt der Karte und ob er alle Punkte der Ansicht enthält.
const [, , modul, basis, did, ansicht] = process.argv;
const pw = await import(modul);
const b = await pw[process.env.RH_BROWSER || "chromium"].launch();
const fehler = [], aus = {};
const punkt = did => `.kartenbox:not(.ekarte) .leaflet-marker-icon[title="${did}"], .kartenbox:not(.ekarte) .leaflet-marker-icon[alt="${did}"]`;
for (const breite of [390, 1300]) {
  const ctx = await b.newContext({viewport: {width: breite, height: 844}, serviceWorkers: "block", hasTouch: breite < 500});
  await ctx.route("**/api/**", r => r.abort());
  const p = await ctx.newPage();
  p.on("pageerror", e => fehler.push(`${breite}: ${e}`));
  await p.goto(basis + "#karte");
  await p.waitForSelector(".kartenbox .rh-ding", {state: "attached"});
  await p.waitForTimeout(400);
  const name = await p.evaluate(did => (R.aufenthalte[did] || R.unterkuenfte[did]).name, did);
  const m = await p.$(punkt(name));
  await m.scrollIntoViewIfNeeded();
  const a = aus[breite] = {};
  if (breite < 500) {
    await m.tap();
    await p.waitForSelector(".leaflet-popup-content", {timeout: 3000}).catch(() => {});
    a.popup = await p.evaluate(() => {
      const c = document.querySelector(".leaflet-popup-content");
      if (!c) return null;
      const r = c.getBoundingClientRect();
      return {text: c.innerText, links: [...c.querySelectorAll("a")].map(x => x.getAttribute("href")),
              imBild: r.top >= 0 && r.left >= 0 && r.bottom <= innerHeight && r.right <= innerWidth};
    });
  } else {
    await m.hover();
    await p.waitForTimeout(300);
    a.kurztext = await p.evaluate(() => [...document.querySelectorAll(".kartenbox .leaflet-tooltip")].filter(t => !t.classList.contains("leaflet-tooltip-permanent")
      && getComputedStyle(t).opacity !== "0").map(t => t.innerText.trim()));
  }
  await p.click(`.kartenansichten button:text-is("${ansicht}")`);
  await p.waitForSelector(".kartenbox .rh-ding", {state: "attached"});
  await p.waitForTimeout(600);
  a.ansicht = await p.evaluate(() => {
    const bb = KARTE.getBounds();
    const lagen = [];
    KARTE.eachLayer(l => { if (l.getLatLng && l.options.icon && /rh-pw/.test(l.options.icon.options.className || "")) lagen.push(l.getLatLng()); });
    return {zoom: KARTE.getZoom(), spanne: [bb.getNorth() - bb.getSouth(), bb.getEast() - bb.getWest()],
            alle: lagen.length > 0 && lagen.every(x => bb.contains(x)), punkte: lagen.length};
  });
  await ctx.close();
}
await b.close();
console.log(JSON.stringify({fehler, aus}));
