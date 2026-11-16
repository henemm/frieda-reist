// Bilder Stufe 1, P2 (#455, Spec docs/specs/oberflaeche/bilder-455-p2.md): Titelbild, Mini in der Tagesliste, Kopfbilder an
// Ort, Etappe, Tag und Unterkunft, Bildreihe, Bild im Text und Bildlink, Großansicht (Zähler, Tasten, Fokus, Wischen), 360 px
// ohne Überbreite, Stadtwochenende ohne jedes Bild-Element. Aufgerufen von test_seite_bilder.py.
// Aufruf: node seiten_bilder_p2.mjs <playwright-modul> <basis-url beispielreise> <basis-url stadtwochenende>
// Die Gruppen kommen aus daten.json (bilder), damit der Test nicht an Kennungen der Beispielbilder hängt.
const [, , modul, basis, basisStadt] = process.argv;
const pw = await import(modul);
const b = await pw[process.env.RH_BROWSER || "chromium"].launch();
const fehler = [], aus = {};
const beobachten = p => {
  p.on("pageerror", e => fehler.push("pageerror: " + e));
  p.on("console", m => { if (/Content.Security.Policy|Refused to (load|execute)/i.test(m.text())) fehler.push("console: " + m.text()); });
};
const kontext = async (breite, hoehe) => {
  const ctx = await b.newContext({viewport: {width: breite, height: hoehe}, serviceWorkers: "block"});
  await ctx.route(u => /\/api\//.test(u.pathname), r => r.abort());
  const p = await ctx.newPage();
  beobachten(p);
  return [ctx, p];
};
const gehe = async (p, url) => { await p.goto(url); await p.waitForSelector("#main > *", {state: "attached"}); await p.waitForTimeout(250); };
const bilderLaden = p => p.evaluate(async () => {
  for (const i of document.querySelectorAll("#main img")) { i.loading = "eager"; }
  await Promise.all([...document.querySelectorAll("#main img")].map(i => i.complete ? null : new Promise(r => { i.onload = i.onerror = r; setTimeout(r, 5000); })));
});

const [ctx, p] = await kontext(1300, 900);
await gehe(p, basis);
const D = await p.evaluate(async () => (await fetch("daten.json")).json());
const bilder = D.bilder || [];
aus.anzahl = bilder.length;
const gruppen = {};
for (const x of bilder) (gruppen[x.zu] = gruppen[x.zu] || []).push(x);
aus.gruppen = Object.fromEntries(Object.entries(gruppen).map(([k, g]) => [k, g.map(x => x.id)]));
const datei = s => (s || "").split("/").pop();

// Vor dem ersten Öffnen gibt es keine Großansicht
aus.grossVorher = await p.evaluate(() => !!document.getElementById("gross"));

// Reise: Titelbild vor dem Reisekopf, Mini in der Tagesliste nur bei Tagen mit Kopfbild
await gehe(p, basis + "#plan");
await bilderLaden(p);
aus.reise = await p.evaluate(() => {
  const t = document.querySelector("#main .bild.titel"), kopf = document.querySelector("#main .reisekopf");
  const r = t ? t.getBoundingClientRect() : null, fig = t ? t.closest("figure") : null;
  const cs = t ? getComputedStyle(t) : null;
  return {
    titel: t ? {src: t.querySelector("img")?.getAttribute("src") || "", seite: r.width / r.height,
      radius: cs.borderTopLeftRadius, token: getComputedStyle(document.documentElement).getPropertyValue("--r-gross").trim(),
      vorKopf: !!(kopf && (t.compareDocumentPosition(kopf) & Node.DOCUMENT_POSITION_FOLLOWING)),
      nennung: fig ? ((fig.querySelector("figcaption .nennung") || {}).textContent || "") : "",
      label: t.getAttribute("aria-label") || "", zoom: cs.cursor} : null,
    tage: [...document.querySelectorAll("#main a.tagzeile[data-tag]")].map(z => {
      const m = z.querySelector(".mini"), mr = m ? m.getBoundingClientRect() : null;
      return {tag: z.dataset.tag, mini: m ? {b: Math.round(mr.width), h: Math.round(mr.height), src: (m.querySelector("img") || {}).src || ""} : null};
    })};
});

// Kopfbilder an Ort, Etappe, Tag und Unterkunft (Heimat), Bildreihe mit „n Bilder“
aus.kopf = {};
for (const [zu, g] of Object.entries(gruppen)) {
  if (!/^(O|E|T|U)-/.test(zu)) continue;
  await gehe(p, basis + "#" + zu);
  await bilderLaden(p);
  aus.kopf[zu] = await p.evaluate(([klein, gross, n]) => {
    const k = [...document.querySelectorAll("#main .bild.kopf")].find(x => {
      const s = x.querySelector("img")?.getAttribute("src") || "";
      return s.endsWith(klein) || s.endsWith(gross);
    });
    if (!k) return null;
    const r = k.getBoundingClientRect(), fig = k.closest("figure"), gal = document.querySelector("#main .galerie");
    return {seite: r.width / r.height, breite: Math.round(r.width), nennung: fig ? ((fig.querySelector("figcaption .nennung") || {}).textContent || "") : null,
      galerie: gal ? {bilder: [...gal.querySelectorAll(".bild")].map(x => { const q = x.getBoundingClientRect(); return [Math.round(q.width), Math.round(q.height)]; }),
        text: gal.textContent} : null};
  }, [datei(g[0].klein), datei(g[0].gross), g.length]);
}

// Unterkünfte: Kopfbild nur an der Heimat (erste Nacht), an anderen Nächten nur ein Mini
aus.naechte = {};
const tage = (D.route && D.route.tage) || [];
for (const t of tage) {
  await gehe(p, basis + "#" + t.id);
  aus.naechte[t.id] = await p.evaluate(dateien => {
    const src = x => x.querySelector("img")?.getAttribute("src") || "";
    const trifft = (x, d) => d.some(n => src(x).endsWith(n));
    const o = {};
    for (const [zu, d] of Object.entries(dateien)) {
      o[zu] = {kopf: [...document.querySelectorAll("#main .bild.kopf")].filter(x => trifft(x, d)).length,
        mini: [...document.querySelectorAll("#main .mini")].filter(x => trifft(x, d)).length};
    }
    return o;
  }, Object.fromEntries(Object.entries(gruppen).filter(([zu]) => zu.startsWith("U-")).map(([zu, g]) => [zu, [datei(g[0].klein), datei(g[0].gross)]])));
}

// Bild im Text und Bildlink im Satz (Wissen): #wissen ist nur die Liste, der Text steht an der Seite seines Abschnitts (W-…)
const wissenText = "#" + ((D.abschnitte || []).find(a => a.typ === "wissen" && JSON.stringify(a).includes("data-bild=")) || {id: "wissen"}).id;
await gehe(p, basis + wissenText);
await bilderLaden(p);
aus.text = await p.evaluate(() => [...document.querySelectorAll("#main figure button.bild.text[data-bild]")].map(k => {
  const fig = k.closest("figure"), r = fig.getBoundingClientRect(), vorher = fig.previousElementSibling;
  return {bild: k.dataset.bild, bildtext: (fig.querySelector("figcaption .bildtext") || {}).textContent || "",
    nennung: (fig.querySelector("figcaption .nennung") || {}).textContent || "", breite: Math.round(r.width),
    nachSatz: vorher ? vorher.textContent.slice(-200) : ""};
}));
// F001: jedes Bild genau einmal verpackt: kein figure im figure, jeder button[data-bild] mit genau einem img, je figure höchstens
// ein figcaption (Wissenstext und die Tagesseiten, auf denen Etappentexte mit Bildern stehen)
const verpackung = q => q.evaluate(() => ({
  verschachtelt: document.querySelectorAll("#main figure figure, #main button[data-bild] figure, #main button[data-bild] button").length,
  knopfOhneEinBild: [...document.querySelectorAll("#main button[data-bild]")].filter(k => k.querySelectorAll("img").length !== 1).length,
  figcaptions: [...document.querySelectorAll("#main figure")].filter(f => f.querySelectorAll("figcaption").length > 1).length,
  knoepfe: document.querySelectorAll("#main button[data-bild]").length}));
aus.verpackung = {[wissenText]: await verpackung(p)};
for (const t of tage) { await gehe(p, basis + "#" + t.id); aus.verpackung[t.id] = await verpackung(p); }

// Großansicht an einer Gruppe mit mindestens 3 Bildern
const gross = Object.entries(gruppen).find(([zu, g]) => zu.startsWith("O-") && g.length >= 3);
aus.gross = null;
if (gross) {
  const [zu, g] = gross;
  await gehe(p, basis + "#" + zu);
  const knopf = p.locator("#main .bild.kopf").first();
  await knopf.evaluate(k => { window.__ausloeser = k; });
  await knopf.click();
  await p.waitForSelector("#gross[open]", {timeout: 5000}).catch(() => {});
  const stand = () => p.evaluate(() => {
    const d = document.getElementById("gross");
    if (!d) return null;
    const img = d.querySelector("img");
    return {offen: d.open, modal: d.matches(":modal"), text: d.textContent.replace(/\s+/g, " "), src: img ? img.getAttribute("src") || "" : "",
      inline: /\son[a-z]+=/i.test(d.outerHTML), pfeile: [...d.querySelectorAll(".pfeil")].map(x => getComputedStyle(x).display),
      fokusZurueck: document.activeElement === window.__ausloeser, hintergrund: getComputedStyle(d).backgroundColor};
  });
  const s = {gruppe: zu, n: g.length, gross: g.map(x => datei(x.gross))};
  s.auf = await stand();
  await p.keyboard.press("ArrowRight"); await p.waitForTimeout(150);
  s.rechts = await stand();
  await p.keyboard.press("ArrowLeft"); await p.waitForTimeout(150);
  s.links = await stand();
  await p.keyboard.press("Escape"); await p.waitForTimeout(200);
  s.zu = await stand();
  // Wischen (Pointer-Events, wie ein Finger): waagerecht nach links -> nächstes Bild, nach unten -> schließt
  const wische = (dx, dy) => p.evaluate(([dx, dy]) => {
    const d = document.getElementById("gross"), z = d.querySelector("img") || d;
    const r = z.getBoundingClientRect(), x = r.left + r.width / 2, y = r.top + r.height / 2;
    const e = (typ, x, y) => z.dispatchEvent(new PointerEvent(typ, {clientX: x, clientY: y, pointerId: 7, pointerType: "touch", isPrimary: true, bubbles: true, cancelable: true}));
    e("pointerdown", x, y);
    for (let i = 1; i <= 5; i++) e("pointermove", x + dx * i / 5, y + dy * i / 5);
    e("pointerup", x + dx, y + dy);
  }, [dx, dy]);
  await knopf.click();
  await p.waitForSelector("#gross[open]", {timeout: 5000}).catch(() => {});
  if (await p.evaluate(() => !!document.getElementById("gross"))) {
    await wische(-160, 0); await p.waitForTimeout(200);
    s.wischWaagerecht = await stand();
    await wische(0, 220); await p.waitForTimeout(250);
    s.wischUnten = await stand();
  }
  aus.gross = s;
}
await ctx.close();

// Handy: 360 px ohne Überbreite, Pfeile der Großansicht ausgeblendet
const [ctx2, h] = await kontext(360, 780);
aus.handy = {ueberbreite: {}};
for (const ziel of ["#plan", "#wissen", wissenText, ...Object.keys(gruppen).filter(z => /^(O|E|T|U)-/.test(z)), ...tage.map(t => t.id)]) {
  await gehe(h, basis + ziel.replace(/^(?!#)/, "#"));
  await bilderLaden(h);
  aus.handy.ueberbreite[ziel] = await h.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
}
if (gross) {
  await gehe(h, basis + "#" + gross[0]);
  await h.locator("#main .bild.kopf").first().click();
  await h.waitForSelector("#gross[open]", {timeout: 5000}).catch(() => {});
  aus.handy.pfeile = await h.evaluate(() => { const d = document.getElementById("gross");
    return d ? [...d.querySelectorAll(".pfeil")].map(x => getComputedStyle(x).display) : null; });
}
await ctx2.close();

// Stadtwochenende: keine Bild-Elemente, keine Großansicht
const [ctx3, s] = await kontext(1300, 900);
aus.stadt = {};
for (const ziel of ["", "#plan", "#wissen"]) {
  await gehe(s, basisStadt + ziel);
  aus.stadt[ziel || "start"] = await s.evaluate(() => document.querySelectorAll(
    "#main .bild, #main .mini, #main .galerie, #gross, [data-bild], img[src*='medien/bilder/']").length);
}
await ctx3.close();
await b.close();
console.log(JSON.stringify({fehler, aus}));
