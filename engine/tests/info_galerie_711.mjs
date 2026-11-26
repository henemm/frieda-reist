// Browsertest der Galerie auf den Erklärseiten unter /info/ (#711), aufgerufen von test_funktionsseiten_711.py.
// Aufruf: node info_galerie_711.mjs <playwright-modul> <seiten-url> <zaehler-vorlage>
// Misst an 390 px (Handy) und 1280 px (Rechner) die Bildreihe, öffnet am Handy Bild 2, blättert weiter, schließt und prüft den
// Fall #706 (Pfeil sofort beim Öffnen). Gibt ein JSON mit den Messwerten und allen Seitenfehlern aus.
const [, , modul, url, zaehler] = process.argv;
const pw = await import(modul);
const b = await pw.chromium.launch();
const aus = {fehler: []};
const erwartet = (galerie, i, n) => zaehler.replace("{galerie}", galerie).replace("{i}", i).replace("{n}", n);

async function streifen(p) {
  return p.evaluate(() => {
    const s = document.querySelector(".pswp .unterschrift-streifen"), r = s && s.getBoundingClientRect();
    const bild = [...document.querySelectorAll(".pswp__item")].map(i => i.querySelector("img.pswp__img"))
      .find(i => i && i.getBoundingClientRect().left >= -2 && i.getBoundingClientRect().left < window.innerWidth - 10);
    return s && {text: s.innerText, zahl: (s.querySelector("small") || {}).textContent || "",
      grund: getComputedStyle(s).backgroundColor, oben: r.top, bildUnten: bild ? bild.getBoundingClientRect().bottom : null,
      bildAlt: bild ? bild.alt : null};
  });
}

for (const breite of [390, 1280]) {
  const c = await b.newContext({viewport: {width: breite, height: 800}});
  const p = await c.newPage();
  p.on("pageerror", e => aus.fehler.push(String(e)));
  await p.goto(url);
  const m = await p.evaluate(() => {
    const r = document.querySelector(".bilder.reihe"), figs = [...r.querySelectorAll("figure")];
    const w = document.querySelector(".wisch");
    return {galerie: r.dataset.galerie, reihe: r.getBoundingClientRect().width, scroll: r.scrollWidth > r.clientWidth + 2,
      bild: figs[0].getBoundingClientRect().width, oben: figs.map(f => Math.round(f.getBoundingClientRect().top)),
      anzahl: figs.length, hinweis: !!(w && w.getClientRects().length),
      symbol: !!figs[0].querySelector("a > .lupe svg") && figs[0].querySelector(".lupe").getBoundingClientRect().width > 20,
      ueber: document.documentElement.scrollWidth > window.innerWidth};
  });
  aus[breite] = m;
  if (breite === 390) {
    await p.locator(".bilder.reihe figure a").nth(1).click();
    await p.waitForSelector(".pswp--open");
    await p.waitForTimeout(700);
    m.offen = await streifen(p);
    await p.keyboard.press("ArrowRight");
    await p.waitForTimeout(600);
    m.weiter = await streifen(p);
    await p.keyboard.press("Escape");
    await p.waitForTimeout(700);
    m.zu = await p.evaluate(() => !document.querySelector(".pswp"));
    // #706: Pfeil weiter sofort beim Öffnen; danach passt der Streifen zum gezeigten Bild
    await p.setViewportSize({width: 1280, height: 800});
    await p.locator(".bilder.reihe figure a").nth(0).click();
    await p.locator(".pswp__button--arrow--next").click({timeout: 2000}).catch(() => {});
    await p.waitForTimeout(1200);
    m.schnell = await streifen(p);
    await p.keyboard.press("Escape");
    await p.waitForTimeout(700);
    // Taste sofort beim Öffnen ebenso; danach gehören Zähler und Unterschrift zum gezeigten Bild
    await p.locator(".bilder.reihe figure a").nth(0).click();
    await p.keyboard.press("ArrowRight");
    await p.waitForTimeout(1200);
    m.taste = await streifen(p);
    await p.keyboard.press("Escape");
    await p.waitForTimeout(700);
    // Schmales Handy (320 px): auch eine lange Unterschrift liegt nie auf dem Bild, bei jedem Bild
    await p.setViewportSize({width: 320, height: 640});
    m.schmal = [];
    for (let i = 0; i < m.anzahl; i++) {
      await p.locator(".bilder.reihe figure a").nth(i).evaluate(a => a.click());
      await p.waitForSelector(".pswp--open");
      await p.waitForTimeout(900);
      m.schmal.push(await streifen(p));
      await p.keyboard.press("Escape");
      await p.waitForTimeout(700);
    }
    // Fenster bei offener Großansicht schmaler: der Streifen wird höher, das Bild rückt mit
    await p.setViewportSize({width: 1280, height: 640});
    await p.locator(".bilder.reihe figure a").nth(m.anzahl - 1).click();
    await p.waitForSelector(".pswp--open");
    await p.waitForTimeout(900);
    await p.setViewportSize({width: 320, height: 640});
    await p.waitForTimeout(900);
    m.verkleinert = await streifen(p);
    await p.keyboard.press("Escape");
  }
  m.erwartet = {offen: erwartet(m.galerie, 2, m.anzahl), weiter: erwartet(m.galerie, 3, m.anzahl)};
  await c.close();
}
await b.close();
console.log(JSON.stringify(aus));
