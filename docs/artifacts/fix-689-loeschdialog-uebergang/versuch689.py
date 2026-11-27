"""Nachstellung #689: Klick auf „Foto entfernen“ zu verschiedenen Zeiten nach dem Erscheinen des Knopfs. Das Seitengerüst kommt
aus engine/tests/seiten_bilder_eigen.mjs (Anfang bis vor den Abläufen), der Ablauf steht hier."""
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

ABLAUF = r"""
  const aus = [];
  const karl = {schluessel: "karl", name: "Karl", rolle: "mitwirkend"};
  for (const pause of [0, 50, 100, 200, 300, 600, 1000]) {
    const {ctx, p} = await seite(karl);
    await gehe(p, basis + "#O-01");
    await p.locator("#main .bild.kopf").first().click();
    await p.waitForFunction(() => document.querySelector("#gross .gross-unten button.entfernen"));
    await p.waitForTimeout(pause);
    const klick = () => p.evaluate(() => {
      const z = {uebergangFertig: GROSS.opener.isOpen, oeffnet: GROSS.opener.isOpening, uiSichtbar: GROSS.element.classList.contains("pswp--ui-visible")};
      document.querySelector("#gross .gross-unten button.entfernen").click();
      return z;
    });
    const z = await klick();
    await p.waitForTimeout(5000);
    const dialog = () => p.evaluate(() => !!document.querySelector("dialog.blatt[open]"));
    z.dialogNach5s = await dialog();
    z.grossNochDa = await p.evaluate(() => !!document.getElementById("gross"));
    if (!z.dialogNach5s) { await klick(); await p.waitForTimeout(500); z.dialogNachZweitemKlick = await dialog(); }
    aus.push({pause, ...z});
    await ctx.close();
  }
  console.log(JSON.stringify({fehler, aus}));
}
await b.close();
"""
tmp = pathlib.Path(tempfile.mkdtemp())
quelle = (WT / "engine/tests/seiten_bilder_eigen.mjs").read_text()
(tmp / "versuch.mjs").write_text(quelle.split("  const aus = {fotoVon")[0] + ABLAUF)
web = tmp / "web"
t.bauen.bauen(t._quelle(tmp), web / "beispiel")
t.bauen.bauen(t.STADT, web / "stadt")
datei = tmp / "foto.jpg"
datei.write_bytes(t.foto(1200, 800))
with t._Server(web) as s:
    r = subprocess.run(["node", str(tmp / "versuch.mjs"), str(t.PLAYWRIGHT), "seite", s.basis + "/beispiel/", s.basis + "/stadt/",
                        str(datei), json.dumps(t._texte_fuer_browser())], capture_output=True, text=True, timeout=200,
                       env={**os.environ, "RH_BROWSER": "chromium"})
print(r.stderr[-1500:])
e = json.loads(r.stdout.strip().splitlines()[-1])
print("Fehler:", e["fehler"])
for z in e["aus"]:
    print(z)
