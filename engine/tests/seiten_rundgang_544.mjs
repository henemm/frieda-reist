// Rundgang vom 12.11.2026 (frieda-reist#544, #545), aufgerufen von test_rundgang_544.py.
// Aufruf: node seiten_rundgang_544.mjs <playwright-modul> <basis-url>
// Öffnet jede Kennung der Reise als Adresse (#U-03 …) am Handy (390 px) und am Rechner (1300 px) und meldet:
// ohneZiel: die Kennung führt zu keinem sichtbaren Ziel (ADR-0003: ein Link führt zur Heimat, das Ding steht dort sichtbar);
// roh: „undefined“, „NaN“ oder ein Schlüssel des Textkatalogs im sichtbaren Text; komma: eine Marke der Zeitachse, deren Text
// nach dem Doppelpunkt mit einem Satzzeichen beginnt; klein: Kopier-Knopf einer Buchungsnummer mit Tippfläche unter 40 px.
const [, , modul, basis] = process.argv;
const pw = await import(modul);
const b = await pw[process.env.RH_BROWSER || "chromium"].launch();
const aus = {fehler: [], ohneZiel: [], roh: [], komma: [], klein: [], geprueft: 0};
for (const breite of [390, 1300]) {
  const ctx = await b.newContext({viewport: {width: breite, height: 900}, serviceWorkers: "block", hasTouch: breite < 700});
  await ctx.route("**/api/**", r => r.abort());
  const p = await ctx.newPage();
  await p.clock.setFixedTime(new Date("2026-10-27T10:00:00"));
  p.on("pageerror", e => aus.fehler.push(`${breite}: ${e}`));
  await p.goto(basis);
  await p.waitForSelector("#titel:not(:empty)");
  await p.waitForTimeout(300);
  const ids = await p.evaluate(() => [...new Set([...abschnitte.flatMap(a => [a.id, ...a.bloecke.map(x => x.id)]), ...D.fragen.zeilen.map(z => z.id),
    ...(R ? [...R.tage.map(t => t.id), ...Object.keys(R.weitere_tage), ...Object.keys(R.unterkuenfte), ...Object.keys(R.strecken), ...Object.keys(R.orte),
      ...R.wahlstellen.flatMap(v => [v.id, ...v.optionen.map(o => o.id)]), ...R.plaene.map(x => x.id),
      ...Object.keys(R.aufenthalte || {}), ...Object.keys(R.buchungen || {})] : []), ...PL_JE.keys()])]);
  for (const h of ["", "zu-tun", "wissen", "packliste", "bausteine", ...ids]) {
    await p.evaluate(h => { location.hash = h; }, h);
    await p.waitForTimeout(30);
    const m = await p.evaluate(h => {
      const sichtbar = e => { if (!e || !e.getClientRects().length) return false;
        for (let x = e.parentElement; x; x = x.parentElement) if (x.tagName === "DETAILS" && !x.open && !(e.tagName === "SUMMARY" && e.parentElement === x)) return false;
        return true; };
      const main = document.querySelector("#main"), r = {};
      // Ziel: das Element der Kennung selbst oder das markierte Ziel (Ersatz, Elternelement, sichtbares Gegenstück)
      if (/^(T|E|O|U|A|B|V|P|F|W|G)-/.test(h)) r.ziel = sichtbar(document.getElementById(h)) || [...document.querySelectorAll(".blitz")].some(sichtbar);
      const roh = main.innerText.match(/\bundefined\b|\[object |\bNaN\b/g) || [];
      for (const d of main.querySelectorAll("details:not([open])")) roh.push(...(d.textContent.match(/\bundefined\b|\[object |\bNaN\b/g) || []));
      if (roh.length) r.roh = [...new Set(roh)];
      r.komma = [...main.querySelectorAll(".tz-marken .chip")].map(c => c.textContent).filter(t => /:\s*[,;:–-]/.test(t));
      r.klein = [...main.querySelectorAll(".chip.nummer .kopieren")].filter(sichtbar).map(k => { const q = getComputedStyle(k, "::after");
        return Math.min(parseFloat(q.width) || 0, parseFloat(q.height) || 0); }).filter(x => x < 40);
      return r;
    }, h);
    aus.geprueft++;
    if (m.ziel === false) aus.ohneZiel.push(`${breite}#${h}`);
    if (m.roh) aus.roh.push(`${breite}#${h}: ${m.roh}`);
    if (m.komma.length) aus.komma.push(`${breite}#${h}: ${m.komma}`);
    if (m.klein.length && breite < 700) aus.klein.push(`${breite}#${h}: ${m.klein}`);
  }
  await ctx.close();
}
await b.close();
console.log(JSON.stringify(aus));
