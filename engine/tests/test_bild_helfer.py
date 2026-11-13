"""Wackelige Browsertests (#550, #537): Helfer für Vollseitenbilder mit Wiederholung und Wartepunkte der Messskripte.

Der Helfer `bild` in `bild.mjs` wird mit einer gestellten Seite ohne Browser über `node` geprüft. Die Wartepunkte der
Messskripte prüft ein Blick in den Quelltext, damit sie nicht versehentlich verschwinden."""
import json
import re
import shutil
import subprocess
import sys
import warnings
from pathlib import Path

import pytest

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))
sys.path.insert(0, str(HIER.parent))

BILD = HIER / "bild.mjs"


def _bild(fehlschlaege, optionen=None):
    """Ruft `bild` mit einer gestellten Seite auf, deren `screenshot` die ersten `fehlschlaege` Male wirft (-1: immer).
    Ergebnis: {"ergebnis", "aufrufe", "optionen", "geworfen"}."""
    optionen = optionen if optionen is not None else {"path": "x.png", "fullPage": True}
    skript = f"""
const {{bild}} = await import({json.dumps(BILD.as_uri())});
const fehl = {fehlschlaege};
const aufrufe = [];
const page = {{screenshot: async o => {{ aufrufe.push(JSON.parse(JSON.stringify(o)));
  if (fehl < 0 || aufrufe.length <= fehl) throw new Error("Protocol error (Page.captureScreenshot): gestellt"); return Buffer.from(""); }}}};
let ergebnis = null, geworfen = null;
try {{ ergebnis = await bild(page, {json.dumps(optionen)}, {{pause: 10}}); }} catch (e) {{ geworfen = String(e); }}
console.log(JSON.stringify({{ergebnis, aufrufe: aufrufe.length, optionen: aufrufe, geworfen}}));
"""
    aus = subprocess.run(["node", "--input-type=module", "-e", skript], capture_output=True, text=True, timeout=60)
    assert aus.returncode == 0, aus.stderr[-2000:]
    return json.loads(aus.stdout.strip().splitlines()[-1])


braucht_node = pytest.mark.skipif(not shutil.which("node"), reason="node fehlt")


@braucht_node
def test_bild_ohne_fehler_ein_aufruf():
    e = _bild(0)
    assert e["geworfen"] is None and e["ergebnis"] is True and e["aufrufe"] == 1, e


@braucht_node
def test_bild_erfolg_im_zweiten_versuch():
    e = _bild(1)
    assert e["geworfen"] is None and e["ergebnis"] is True and e["aufrufe"] == 2, e


@braucht_node
def test_bild_nach_drei_fehlversuchen_false():
    e = _bild(-1)
    assert e["geworfen"] is None, e          # wirft nicht: das Skript läuft weiter
    assert e["ergebnis"] is False and e["aufrufe"] == 3, e


@braucht_node
def test_bild_gibt_optionen_weiter():
    o = {"path": "bausteine.png", "fullPage": True, "clip": {"x": 0, "y": 0, "width": 390, "height": 32000}}
    e = _bild(-1, o)
    assert e["optionen"] == [o, o, o], e


def _nach(text, marke):
    i = text.find(marke)
    assert i >= 0, marke
    return text[i + len(marke):]


def test_stand_skript_wartet_auf_reise_stand_text():
    """AC-1: nach `reload` wartet das Skript auf „Neu: Reise-Stand“ in #neu (15 s), nicht nur auf das sichtbare #neu."""
    q = (HIER / "stand_browser.mjs").read_text(encoding="utf-8")
    nach = _nach(q, "await p.reload();")
    vor_lesen = nach.split('ergebnis.hinweis', 1)[0]
    assert re.search(r"waitForFunction\([^;]*#neu[^;]*Neu: Reise-Stand[^;]*timeout:\s*15000", vor_lesen, re.S), vor_lesen
    assert ".catch(" in vor_lesen, "bei Zeitüberschreitung weiterlesen, damit der Test mit seiner Meldung scheitert"


def test_packliste_skript_wartet_auf_knopftext():
    """AC-2: vor dem Lesen von knopf0 und von knopf nach `reload` ein Wartepunkt auf nicht leeren Text von .pack-alle."""
    q = (HIER / "seiten_packliste.mjs").read_text(encoding="utf-8")
    wartepunkt = re.compile(r"warte\(p,[^;]*\.pack-alle[^;]*textContent[^;]*\)(\.catch\([^;]*\))?;")
    vor_knopf0 = q.split("const knopf0", 1)[0].rsplit("await haken(p, \"Wanderschuhe\")", 1)[1]
    assert wartepunkt.search(vor_knopf0), vor_knopf0
    klappen = q.split("const knopf0", 1)[1]
    vor_knopf = klappen.split("aus.klappen", 1)[0].split("await p.reload();", 1)[1]
    assert wartepunkt.search(vor_knopf), vor_knopf


def test_vollseitenbilder_ueber_den_helfer():
    """AC-5: alle Vollseitenbilder gehen über `bild`; kein direkter `screenshot` mit fullPage mehr."""
    for name in ("seiten_browser.mjs", "seiten_brett.mjs", "seiten_packliste.mjs"):
        q = (HIER / name).read_text(encoding="utf-8")
        assert re.search(r"import\s*\{\s*bild\s*\}\s*from\s*[\"']\./bild\.mjs[\"']", q), name
        assert not re.search(r"\.screenshot\(\{[^}]*fullPage", q), name
    q = (HIER / "seiten_browser.mjs").read_text(encoding="utf-8")
    assert "bilderFehlen" in q.split("console.log(JSON.stringify(")[-1], "bilderFehlen in der JSON-Ausgabe"


def test_bilderfehlen_ist_warnung_nicht_rot():
    """AC-6: fehlende Bilder geben eine Warnung mit den Dateinamen, der Test bleibt grün."""
    import test_seite
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        test_seite.bilder_fehlen_melden({"bilderFehlen": ["bausteine-webkit-390-hell.png"]})
    assert any("bausteine-webkit-390-hell.png" in str(x.message) for x in w), [str(x.message) for x in w]
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        test_seite.bilder_fehlen_melden({"bilderFehlen": []})
        test_seite.bilder_fehlen_melden({})
    assert not w
    q = (HIER / "test_seite.py").read_text(encoding="utf-8")
    assert "bilder_fehlen_melden(e)" in q, "der Browser-Rundgang ruft die Meldung auf"
