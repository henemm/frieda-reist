"""Messung #689 für die Analyse: Nebenfolgen des verlorenen Klicks (4), Kreuz und Escape während des Öffnens (5), reduzierte
Bewegung (7), langsames Bild, und drei Lösungswege im Vergleich. Die Lösungswege werden nur in der gebauten Seite im Temp-Ordner
eingesetzt; engine/vorlage.html bleibt unverändert. Aufruf: python messung689.py <null|sofort|aufschub|sperre>"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

HIER = pathlib.Path(__file__).parent
WT = HIER.parents[2]
sys.path[:0] = [str(WT / "engine/tests"), str(WT / "engine")]
import test_bilder_eigen as t  # noqa: E402

ALT = "danach = () => bildEntfernenFragen(b); pswp.destroy(); }"
WEGE = {
    "null": ALT,
    # in der Meldung selbst schließen
    "sofort": "danach = () => bildEntfernenFragen(b); if (pswp.opener.isOpen) pswp.destroy();"
              " else pswp.on('openingAnimationEnd', () => pswp.destroy()); }",
    # erst nach der Meldung schließen
    "aufschub": "danach = () => bildEntfernenFragen(b); if (pswp.opener.isOpen) pswp.destroy();"
                " else pswp.on('openingAnimationEnd', () => setTimeout(() => pswp.destroy())); }",
    # Klick während des Öffnens tut nichts und hinterlässt nichts
    "sperre": "if (!pswp.opener.isOpen) return; " + ALT,
    # Klick merken, Blättern verwirft ihn, Schließen nach der Meldung (Empfehlung)
    "plan": "danach = () => bildEntfernenFragen(b); if (pswp.opener.isOpen) pswp.destroy(); }",
}
ZUSATZ_ALT = "    let danach = null;\n    pswp.on(\"uiRegister\""
ZUSATZ_PLAN = ("    let danach = null;\n    pswp.on('change', () => { danach = null; });\n"
               "    pswp.on('openingAnimationEnd', () => setTimeout(() => { if (danach && !pswp.isDestroying) pswp.destroy(); }));\n"
               "    pswp.on(\"uiRegister\"")
ABLAUF = r"""
  const aus = {};
  const karl = {schluessel: "karl", name: "Karl", rolle: "mitwirkend"};
  const stand = p => p.evaluate(() => ({dialoge: document.querySelectorAll("dialog.blatt[open]").length, gross: !!document.getElementById("gross")}));
  const klick = (p, n = 1) => p.evaluate(n => { const w = document.querySelector("#gross .gross-unten button.entfernen");
    const k = {isOpen: GROSS.opener.isOpen};
    for (let i = 0; i < n; i++) w.click(); return k; }, n);
  const auf = async p => {
    await gehe(p, basis + "#O-01");
    await p.evaluate(() => { window.__m = []; setInterval(() => { if (GROSS && !GROSS.__b) { GROSS.__b = 1; const t0 = performance.now();
      for (const n of ["openingAnimationStart", "openingAnimationEnd", "initialZoomInEnd", "closingAnimationStart", "destroy"])
        GROSS.on(n, () => __m.push(n + "@" + Math.round(performance.now() - t0))); } }, 1); });
    await p.locator("#main .bild.kopf").first().click();
    await p.waitForFunction(() => document.querySelector("#gross .gross-unten button.entfernen"));
  };
  const fall = async (name, opt, f) => {
    const {ctx, p, gesendet} = await seite(karl);
    try {
      if (opt.reduziert) await p.emulateMedia({reducedMotion: "reduce"});
      if (opt.langsam) await ctx.route(/BI-90-[^/]*$/, async r => { await leise(opt.langsam); await r.continue(); });
      await auf(p);
      aus[name] = await f(p, gesendet);
      aus[name].meldungen = await p.evaluate(() => __m);
    } catch (e) { aus[name] = {abbruch: String(e).split("\n")[0]}; }
    await ctx.close();
  };
  const geloescht = async (p, g) => { const ja = knopf(p, T.ja);
    if (await ja.count()) { await ja.first().click(); await p.waitForTimeout(500); }
    return g.filter(x => x.methode === "DELETE").map(x => x.url.split("/").pop()); };
  await fall("1 Klick im Öffnen", {}, async p => { const k = await klick(p); await p.waitForTimeout(1500);
    return {k, ...await stand(p), fokusImDialog: await p.evaluate(() => !!document.activeElement.closest("dialog.blatt"))}; });
  await fall("2 Dreifachklick im Öffnen", {}, async p => { const k = await klick(p, 3); await p.waitForTimeout(1500); return {k, ...await stand(p)}; });
  await fall("3 Klick im Öffnen, später Escape", {}, async p => { await klick(p); await p.waitForTimeout(1500);
    const vor = await stand(p); if (!vor.dialoge) { await p.keyboard.press("Escape"); await p.waitForTimeout(1500); }
    return {vor, danach: await stand(p)}; });
  await fall("4 Klick, später blättern, Escape, Entfernen", {}, async (p, g) => {
    const bilder = await p.evaluate(() => GROSS.getNumItems());
    await klick(p); await p.waitForTimeout(1500);
    const zwischen = await stand(p);
    let bild = null;
    if (zwischen.gross) { await p.evaluate(() => GROSS.next()); await p.waitForTimeout(800);
      bild = await p.evaluate(() => GROSS.currSlide.data.bild.id); await p.keyboard.press("Escape"); await p.waitForTimeout(1500); }
    return {bilder, zwischen, zuletztGezeigt: bild, geloescht: await geloescht(p, g)}; });
  for (const art of ["taste", "knopf"]) for (const pause of [0, 150]) await fall(`5 Klick, dann blättern (${art}) nach ${pause} im Öffnen`, {}, async (p, g) => {
    await p.waitForTimeout(pause);
    const k = await klick(p);
    if (art === "taste") await p.keyboard.press("ArrowRight");
    else await p.evaluate(() => document.querySelector("#gross .pswp__button--arrow--next").click());
    await p.waitForTimeout(2500);
    const gezeigt = await p.evaluate(() => GROSS && GROSS.currSlide && GROSS.currSlide.data.bild.id);
    return {k, gezeigt, ...await stand(p), geloescht: await geloescht(p, g)}; });
  await fall("6 Escape im Öffnen", {}, async p => { await p.keyboard.press("Escape"); await p.waitForTimeout(1500); return stand(p); });
  await fall("7 Kreuz im Öffnen", {}, async p => { await p.evaluate(() => document.querySelector("#gross .pswp__button--close").click());
    await p.waitForTimeout(1500); return stand(p); });
  await fall("8 Klick, dann sofort Escape", {}, async p => { await klick(p); await p.keyboard.press("Escape"); await p.waitForTimeout(1500); return stand(p); });
  for (const ms of [0, 100, 300]) await fall("9 reduzierte Bewegung, Klick nach " + ms, {reduziert: true}, async p => { await p.waitForTimeout(ms);
    const k = await klick(p); await p.waitForTimeout(1500); return {k, ...await stand(p)}; });
  await fall("10 Bild lädt 3 s", {langsam: 3000}, async p => { const k = await klick(p); await p.waitForTimeout(1500);
    const n15 = await stand(p); await p.waitForTimeout(4000); return {k, nach1500: n15, nach5500: await stand(p)}; });
  await fall("11 Klick nach dem Öffnen", {}, async p => { await p.waitForTimeout(1200); const k = await klick(p); await p.waitForTimeout(600);
    return {k, ...await stand(p)}; });
  for (const art of ["waehrend", "danach"]) await fall(`12 nur blättern (Pfeilknopf) ${art} des Öffnens`, {}, async (p, g) => {
    await p.waitForTimeout(art === "waehrend" ? 100 : 1200);
    await p.evaluate(() => document.querySelector("#gross .pswp__button--arrow--next").click());
    await p.waitForTimeout(2500);
    const z = await p.evaluate(() => ({index: GROSS.currIndex, folie: !!GROSS.currSlide, zaehler: document.getElementById("gross-zaehler").textContent,
      bilderImBlick: [...document.querySelectorAll("#gross img.pswp__img")].filter(i => { const r = i.getBoundingClientRect();
        return r.width > 100 && r.left < innerWidth - 50 && r.right > 50; }).map(i => i.src.split("/").pop())}));
    await klick(p); await p.waitForTimeout(800);
    return {...z, ...await stand(p), geloescht: await geloescht(p, g)}; });
  console.log(JSON.stringify({fehler, aus}));
}
await b.close();
"""
weg = sys.argv[1] if len(sys.argv) > 1 else "null"
tmp = pathlib.Path(tempfile.mkdtemp())
quelle = (WT / "engine/tests/seiten_bilder_eigen.mjs").read_text()
(tmp / "messung.mjs").write_text(quelle.split("  const aus = {fotoVon")[0] + ABLAUF)
# Weg in der Vorlage eintauschen, bevor gebaut wird (der Hash der Inhaltsrichtlinie stimmt dann)
VORLAGE = WT / "engine/vorlage.html"
lesen = pathlib.Path.read_text


def mit_weg(self, *a, **k):
    s = lesen(self, *a, **k)
    if self.name == "vorlage.html":
        assert s.count(ALT) == 1 and s.count(ZUSATZ_ALT) == 1, "Stelle nicht gefunden"
        s = s.replace(ALT, WEGE[weg])
        if weg == "plan":
            s = s.replace(ZUSATZ_ALT, ZUSATZ_PLAN)
    return s


pathlib.Path.read_text = mit_weg
web = tmp / "web"
q = t._quelle(tmp)
t.eigen_eintragen(q, "BI-91")   # zweites eigenes Foto am selben Ort: Blättern
t.bauen.bauen(q, web / "beispiel")
t.bauen.bauen(t.STADT, web / "stadt")
pathlib.Path.read_text = lesen
datei = tmp / "foto.jpg"
datei.write_bytes(t.foto(1200, 800))
with t._Server(web) as s:
    r = subprocess.run(["node", str(tmp / "messung.mjs"), str(t.PLAYWRIGHT), "seite", s.basis + "/beispiel/", s.basis + "/stadt/",
                        str(datei), json.dumps(t._texte_fuer_browser())], capture_output=True, text=True, timeout=300,
                       env={**os.environ, "RH_BROWSER": os.environ.get("RH_BROWSER", "chromium")})
if r.returncode:
    print(r.stderr[-1500:])
e = json.loads(r.stdout.strip().splitlines()[-1])
print("Weg:", weg, "| Fehler:", e["fehler"])
nur = sys.argv[2] if len(sys.argv) > 2 else ""
for k, v in e["aus"].items():
    if not k.startswith(nur):
        continue
    print(" ", k, "→", json.dumps(v, ensure_ascii=False))
