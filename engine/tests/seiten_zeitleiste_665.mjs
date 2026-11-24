// Zeitleiste einer Bewegung (#665), aufgerufen von test_zeitleiste_bewegung.py.
// Aufruf: node seiten_zeitleiste_665.mjs <playwright-modul> <basis-url> <ids, mit Komma> <breite>
// Meldet je Ding an seiner Heimat: die Zeitleiste (ol.zeit) mit ihren Punkten, die Kopfzeile, den übrigen Text und ob etwas überläuft.
const [, , modul, basis, ids, breite] = process.argv;
const pw = await import(modul);
const b = await pw[process.env.RH_BROWSER || "chromium"].launch();
const ctx = await b.newContext({viewport: {width: Number(breite || 390), height: 900}, serviceWorkers: "block"});
await ctx.route("**/api/**", r => r.abort());
const p = await ctx.newPage();
const fehler = [];
p.on("pageerror", e => fehler.push(String(e)));
const dinge = {};
for (const id of ids.split(",")) {
  await p.goto(basis + "#" + id);
  await p.waitForSelector("#" + id);
  await p.waitForTimeout(150);
  dinge[id] = await p.evaluate(id => {
    const z = document.getElementById(id);
    const stil = e => e ? getComputedStyle(e) : null;
    const leisten = z.querySelectorAll("ol.zeit");
    const zl = leisten[0] || null;
    const punkte = zl ? [...zl.children].map(li => {
      const name = li.querySelector(".leisten-name"), zeit = li.querySelector(".leisten-zeit"), tag = zeit && zeit.querySelector(".tag");
      const punkt = li.querySelector(".leisten-punkt"), marke = li.querySelector(".leisten-marke");
      const zusatz = [...li.querySelectorAll(".leisten-zusatz")];
      return {art: li.dataset.art || null, merkmal: li.dataset.merkmal || null,
        name: name ? name.textContent.trim() : null, nameFett: name ? Number(stil(name).fontWeight) : null, nameFarbe: name ? stil(name).color : null,
        voll: !!(punkt && punkt.classList.contains("voll")), punkt: !!punkt,
        zeit: zeit ? zeit.textContent.replace(/\s+/g, " ").trim() : null, zeitGroesse: zeit ? stil(zeit).fontSize : null,
        zeitFett: zeit ? Number(stil(zeit).fontWeight) : null,
        tag: tag ? tag.textContent.trim() : null, tagGroesse: tag ? stil(tag).fontSize : null, tagFett: tag ? Number(stil(tag).fontWeight) : null,
        tagUnterZeit: tag ? tag.getBoundingClientRect().top >= zeit.getBoundingClientRect().top + 4 && Math.abs(tag.getBoundingClientRect().left - zeit.getBoundingClientRect().left) < 2 : null,
        marke: marke ? marke.textContent.trim() : null,
        zusatz: zusatz.map(x => x.textContent.replace(/\s+/g, " ").trim()),
        zusatzGroesse: zusatz.length ? stil(zusatz[0]).fontSize : null, zusatzFarbe: zusatz.length ? stil(zusatz[0]).color : null};
    }) : [];
    const kopf = z.querySelector(".zeitleiste-kopf");
    // Text ohne Zeitleiste: Kopfzeile, Merkmalliste, Buchungsblock, „Aus der Planung“ (auch zugeklappt)
    const rest = z.cloneNode(true);
    rest.querySelectorAll("ol.zeit").forEach(x => x.remove());
    const kleinZeilen = [...z.children].filter(x => x.matches("div.z.klein")).map(x => x.textContent.replace(/\s+/g, " ").trim());
    const r = (typeof R !== "undefined" ? R : {}), s = (r.strecken || {})[id] || {};
    return {anzahl: leisten.length, punkte, schrift: getComputedStyle(document.body).fontSize,
      kopf: kopf ? {text: kopf.textContent.replace(/\s+/g, " ").trim(), groesse: stil(kopf).fontSize, fett: Number(stil(kopf).fontWeight)} : null,
      kleinZeilen, rest: rest.textContent.replace(/\s+/g, " ").trim(), text: z.textContent.replace(/\s+/g, " ").trim(),
      werte: Object.fromEntries(Object.entries(s.merkmale || {}).map(([k, v]) => [k, v && v.wert])),
      ueberlauf: document.documentElement.scrollWidth > window.innerWidth + 1};
  }, id);
}
await b.close();
console.log(JSON.stringify({dinge, fehler}));
