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

// Vor dem ersten Öffnen gibt es keine Großansicht, und die Bibliothek ist nicht geladen
aus.grossVorher = await p.evaluate(() => !!document.getElementById("gross"));
aus.bibliothekVorher = await p.evaluate(() => performance.getEntriesByType("resource").some(e => /photoswipe/.test(e.name)));

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

// Großansicht (PhotoSwipe, #676) an einer Gruppe mit mindestens 3 Bildern: Zähler, Tasten, Fokus, Wischen, Zoomen, Übergang
const gross = Object.entries(gruppen).find(([zu, g]) => zu.startsWith("O-") && g.length >= 3);
aus.gross = null;
const offen = q => q.waitForFunction(() => { const d = document.getElementById("gross");
  // nach dem Übergang (333 ms) liegt der Fokus in der Großansicht
  return d && d.classList.contains("pswp--ui-visible") && !d.querySelector(".pswp__preloader--active") && d.contains(document.activeElement);
}, null, {timeout: 5000}).then(() => q.waitForTimeout(150)).catch(() => {});
const geschlossen = q => q.waitForFunction(() => !document.getElementById("gross"), null, {timeout: 5000}).catch(() => {});
if (gross) {
  const [zu, g] = gross;
  await gehe(p, basis + "#" + zu);
  const knopf = p.locator("#main .bild.kopf").first();
  await knopf.evaluate(k => { window.__ausloeser = k; });
  // Übergang aus dem Vorschaubild (#676): ein kleines Bild der Bildreihe; kurz nach dem Klick liegt das große Bild noch etwa auf
  // ihm und wächst dann
  const klein = p.locator("#main .galerie .bild").first();
  await klein.evaluate(k => { window.__klein = k; });
  await klein.click();
  await p.waitForSelector("#gross", {timeout: 5000}).catch(() => {});
  const uebergang = await p.evaluate(async () => {
    const k = window.__klein.getBoundingClientRect(), breiten = [];
    for (let i = 0; i < 40; i++) {
      const sichtbar = [...document.querySelectorAll("#gross img.pswp__img")].map(z => z.getBoundingClientRect())
        .filter(r => r.width > 0 && r.left >= -5 && r.right <= innerWidth + 5);
      breiten.push(sichtbar.length ? Math.round(Math.max(...sichtbar.map(r => r.width))) : 0);
      await new Promise(r => requestAnimationFrame(r));
    }
    return {vorschau: Math.round(k.width), breiten};
  });
  await offen(p);
  await p.keyboard.press("Escape"); await geschlossen(p);
  await knopf.click();
  await offen(p);
  const stand = () => p.evaluate(() => {
    const d = document.getElementById("gross");
    if (!d) return {offen: false, fokusZurueck: document.activeElement === window.__ausloeser};
    const img = d.querySelector(".pswp__item[aria-hidden=false] img.pswp__img:not(.pswp__img--placeholder)")
      || [...d.querySelectorAll("img.pswp__img:not(.pswp__img--placeholder)")].find(i => { const r = i.getBoundingClientRect(); return r.left >= -5 && r.left < innerWidth / 2; });
    const unten = d.querySelector(".gross-unten");
    return {offen: true, modal: d.getAttribute("role") === "dialog" && d.getAttribute("aria-modal") === "true" && d.contains(document.activeElement),
      label: (document.getElementById(d.getAttribute("aria-labelledby") || "-") || {}).textContent || "",
      text: (d.querySelector(".zaehler") || {}).textContent || "", src: img ? img.getAttribute("src") || "" : "",
      unten: unten ? unten.textContent.replace(/\s+/g, " ") : "", lizenzLink: !!(unten && unten.querySelector(".nennung a[href]")),
      inline: /\son[a-z]+=/i.test(d.outerHTML), pfeile: [...d.querySelectorAll(".pswp__button--arrow")].map(x => getComputedStyle(x).display),
      titel: [...d.querySelectorAll(".pswp__button")].map(x => x.getAttribute("aria-label") || x.title || ""),
      hintergrund: getComputedStyle(d.querySelector(".pswp__bg")).backgroundColor, seitenGrund: getComputedStyle(document.body).backgroundColor,
      // Zoom: Breite des Bildes im aktuellen Fach (das Fach, das gerade links bündig im Bild steht)
      zoom: (() => { const f = [...d.querySelectorAll(".pswp__item")].find(x => Math.abs(x.getBoundingClientRect().left) < 5);
        const i = f && f.querySelector("img.pswp__img:not(.pswp__img--placeholder)"); return i ? Math.round(i.getBoundingClientRect().width) : 0; })()};
  });
  const s = {gruppe: zu, n: g.length, gross: g.map(x => datei(x.gross)), uebergang};
  s.auf = await stand();
  await p.keyboard.press("ArrowRight"); await p.waitForTimeout(500);
  s.rechts = await stand();
  await p.keyboard.press("ArrowLeft"); await p.waitForTimeout(500);
  s.links = await stand();
  // Zoomen: Knopf „Zoomen“ ändert den Maßstab, noch einmal zurück
  const vorher = s.links.zoom;
  await p.locator("#gross .pswp__button--zoom").click().catch(() => {}); await p.waitForTimeout(600);
  s.zoom = {vorher, nachher: (await stand()).zoom};
  await p.locator("#gross .pswp__button--zoom").click().catch(() => {}); await p.waitForTimeout(600);
  await p.keyboard.press("Escape"); await geschlossen(p);
  s.zu = await stand();
  // Wischen mit der Maus (PhotoSwipe nimmt Pointer-Events): waagerecht nach links -> nächstes Bild, nach unten -> schließt
  const wische = async (dx, dy) => {
    const r = await p.evaluate(() => { const r = document.querySelector("#gross .pswp__scroll-wrap").getBoundingClientRect();
      return {x: r.left + r.width / 2, y: r.top + r.height / 2}; });
    await p.mouse.move(r.x, r.y); await p.mouse.down();
    for (let i = 1; i <= 8; i++) { await p.mouse.move(r.x + dx * i / 8, r.y + dy * i / 8); await p.waitForTimeout(16); }
    await p.mouse.up();
  };
  await geschlossen(p);
  await knopf.click();
  await offen(p);
  if (await p.evaluate(() => !!document.getElementById("gross"))) {
    await wische(-300, 0); await p.waitForTimeout(700);
    s.wischWaagerecht = await stand();
    await wische(0, 300); await geschlossen(p);
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
  await offen(h);
  aus.handy.pfeile = await h.evaluate(() => { const d = document.getElementById("gross");
    return d ? [...d.querySelectorAll(".pswp__button--arrow")].map(x => getComputedStyle(x).display) : null; });
}
await ctx2.close();

// Stadtwochenende: keine Bild-Elemente, keine Großansicht
const [ctx3, s] = await kontext(1300, 900);
aus.stadt = {};
for (const ziel of ["", "#plan", "#wissen"]) {
  await gehe(s, basisStadt + ziel);
  aus.stadt[ziel || "start"] = await s.evaluate(() => document.querySelectorAll(
    "#main .bild, #main .mini, #main .galerie, #gross, [data-bild], img[src*='medien/bilder/'], link[href*=photoswipe]").length);
}
await ctx3.close();
await b.close();
console.log(JSON.stringify({fehler, aus}));
