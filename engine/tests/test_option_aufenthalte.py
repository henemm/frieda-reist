"""Aufenthalte ohne Nacht (A-…) als Möglichkeiten einer Wahlstelle, auch gemischt mit Strecken (#353, Schritt 1).
Product Owner, 6.11.2026: jedes Ding außer dem Tag kann Alternative sein; eine Wahlstelle darf Dinge verschiedener Arten mischen,
der Vergleich zeigt die Merkmale aller beteiligten Arten, jede Möglichkeit füllt ihre eigenen."""
import json
import pathlib
import shutil
import sys
import tempfile

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from test_regeln import reise_bauen  # noqa: E402
from test_schreiben import KARL, repo, routen_auf_main, schreiber  # noqa: E402,F401
import schreiben as sb  # noqa: E402
from playwright_pfad import PLAYWRIGHT  # noqa: E402
from test_seite import seite_der_variante  # noqa: E402

AUFENTHALT = ("  A-02:\n    name: \"Stadt Wehlen\"", """  A-90:
    name: Festung Königstein
    ort: O-03
    art: besichtigung
    quelle: "erfunden (Beispiel)"
    merkmale:
      geoeffnet: {wert: ja, quelle: "erfunden (Beispiel)", geprueft: 2026-11-01}
      eintritt: {wert: "12 €", quelle: "erfunden (Beispiel)", geprueft: 2026-11-01}
  A-02:
    name: "Stadt Wehlen\"""")
TAG = ("  T-03: {titel: \"Hohnstein → Brand → Altendorf\", wahl: [V-06], strecken: [E-02], nacht: U-04}",
       "  T-03: {titel: \"Hohnstein → Brand → Altendorf\", wahl: [V-06, V-90], strecken: [E-02], nacht: U-04}")
WAHL = ("wahlstellen:\n  V-01:", """wahlstellen:
  V-90:
    titel: "Nachmittag: Festung oder Wanderung (erfundenes Beispiel)"
    wann: unterwegs
    optionen:
      - id: V-90.a
        titel: "Festung besichtigen"
        aufenthalte: [A-90]
        quelle: "erfunden (Beispiel)"
        verlauf:
          - {datum: 2026-10-20, status: vorgeschlagen, wer: Claude}
      - id: V-90.b
        titel: "Statt dessen zum Wasserfall wandern"
        strecken: [E-04]
        quelle: "erfunden (Beispiel)"
        verlauf:
          - {datum: 2026-10-20, status: vorgeschlagen, wer: Claude}
  V-01:""")


def routen(ersetzen):
    d = pathlib.Path(tempfile.mkdtemp())
    seiten = reise_bauen(d, routen_ersetzen=ersetzen)
    daten = json.loads((pathlib.Path(seiten) / "beispielreise" / "daten.json").read_text(encoding="utf-8"))
    return daten["route"]


def test_aufenthalt_als_option_wird_gelesen_und_gemischt_verglichen():
    r = routen([AUFENTHALT, TAG, WAHL])
    w = next(x for x in r["wahlstellen"] if x["id"] == "V-90")
    a, b = w["optionen"]
    assert a["aufenthalte"] == ["A-90"] and b["strecken"] == ["E-04"]
    ids = {k["id"] for k in w["kriterien"]}
    assert {"geoeffnet", "eintritt"} <= ids, "Merkmale der Besichtigung stehen im Vergleich"
    assert ids - {"geoeffnet", "eintritt", "dauer"}, "und die der Wanderung"
    assert a["merkmale"]["eintritt"]["wert"] == "12 €"
    assert "eintritt" not in b["merkmale"]


def test_gemischte_wahlstelle_mahnt_nur_die_eigenen_pflichtmerkmale():
    r = routen([AUFENTHALT, TAG, WAHL])
    b = next(x for x in r["wahlstellen"] if x["id"] == "V-90")["optionen"][1]
    assert "geoeffnet" not in b["fehlt"], "die Wanderung braucht kein „Geöffnet am Reisedatum“ der Besichtigung"


def test_aufenthalt_der_aktiven_option_steht_am_tag():
    r = routen([AUFENTHALT, TAG, WAHL])
    t = next(x for x in r["tage"] if x["id"] == "T-03")
    assert "A-90" in t["aufenthalte"] and "V-90" in t["wahlstellen"]
    assert t["aufenthalte_offen"] == [], "unterwegs: nichts davon ist eine offene Planungswahl"


def test_unbekannter_aufenthalt_in_option_ist_ein_fehler():
    falsch = (WAHL[0], WAHL[1].replace("aufenthalte: [A-90]", "aufenthalte: [A-77]"))
    with pytest.raises(BaseException) as e:
        routen([AUFENTHALT, TAG, falsch])
    assert "A-77" in str(e.value)


@pytest.mark.skipif(not PLAYWRIGHT.exists() or not shutil.which("node"), reason="Playwright fehlt")
@pytest.mark.parametrize("browser", ["chromium", "webkit"])
def test_seite_zeigt_aufenthalt_der_option_im_vergleich_und_in_der_zeitleiste(tmp_path, browser):
    e = seite_der_variante(tmp_path, browser, skript="seiten_option_aufenthalt.mjs", routen_ersetzen=[AUFENTHALT, TAG, WAHL])
    assert not e["fehler"], e["fehler"]
    assert e["wahl"] and "Festung besichtigen" in e["wahl"] and "Eintritt" in e["wahl"] and "12 €" in e["wahl"], e["wahl"]
    assert any("Festung Königstein" in z for z in e["verlauf"]), e["verlauf"]


def test_schreibweg_nimmt_aufenthalte_in_optionen(repo):
    """option_anlegen und option_aendern: aufenthalte: [A-…]; mit strecken zusammen erlaubt, sonst nur eine Sorte."""
    _, origin, _, _ = repo
    s = schreiber(repo)
    a = s.schreiben("beispielreise", "option_anlegen", {**KARL, "args": {"wahlstelle": "V-02", "titel": "Burg statt Weg", "aufenthalte": ["A-01"],
                                                                         "quelle": "Karl im Gespräch"}})
    assert "V-02.c" in a["text"]
    r, _ = routen_auf_main(origin)
    o = next(o for o in r["wahlstellen"]["V-02"]["optionen"] if o["id"] == "V-02.c")
    assert o["aufenthalte"] == ["A-01"]
    s.vorbereiten()
    s.schreiben("beispielreise", "option_aendern", {**KARL, "args": {"ziel": "V-02.c", "strecken": ["E-04"]}})   # Weg und Rast
    r, _ = routen_auf_main(origin)
    o = next(o for o in r["wahlstellen"]["V-02"]["optionen"] if o["id"] == "V-02.c")
    assert o["aufenthalte"] == ["A-01"] and o["strecken"] == ["E-04"]
    s.vorbereiten()
    with pytest.raises(sb.Ablehnung) as e:
        s.schreiben("beispielreise", "option_aendern", {**KARL, "args": {"ziel": "V-02.c", "unterkuenfte": ["U-02"]}})
    assert e.value.schluessel == "schreiben.option_aendern.5"
    with pytest.raises(sb.Ablehnung, match="gibt es nicht"):
        s.schreiben("beispielreise", "option_anlegen", {**KARL, "args": {"wahlstelle": "V-02", "titel": "X", "aufenthalte": ["A-77"], "quelle": "x"}})


def test_zweite_beispielreise_museum_oder_cafe_gemischt(tmp_path):
    """Städtewochenende (ohne Wanderung, ohne Varianten): Museum oder Café, zwei Arten in einer Wahlstelle, am Samstag."""
    import shutil
    import bauen
    quelle = tmp_path / "quelle"
    shutil.copytree(pathlib.Path(__file__).resolve().parent.parent.parent / "beispiel" / "reisen" / "stadtwochenende", quelle)
    r = quelle / "plan" / "routen.yaml"
    t = r.read_text(encoding="utf-8")
    t = t.replace("buchungen:\n", """  A-90:
    name: Naturkundemuseum
    ort: O-02
    art: museum
    quelle: "erfunden (Beispiel)"
    merkmale:
      geoeffnet: {wert: ja, quelle: "erfunden (Beispiel)", geprueft: 2026-11-01}
      eintritt: {wert: "6 €", quelle: "erfunden (Beispiel)", geprueft: 2026-11-01}
  A-91:
    name: Café am Markt
    ort: O-02
    art: essen
    quelle: "erfunden (Beispiel)"

buchungen:
""", 1)
    t = t.replace('T-02: {titel: "Samstag in Beispielstadt", aufenthalte: [A-01], nacht: U-01}',
                  'T-02: {titel: "Samstag in Beispielstadt", aufenthalte: [A-01], wahl: [V-90], nacht: U-01}', 1)
    t += """
wahlstellen:
  V-90:
    titel: "Samstagnachmittag: Museum oder Café (erfundenes Beispiel)"
    wann: unterwegs
    optionen:
      - id: V-90.a
        titel: "Naturkundemuseum"
        aufenthalte: [A-90]
        quelle: "erfunden (Beispiel)"
        verlauf:
          - {datum: 2026-11-01, status: vorgeschlagen, wer: Tom}
      - id: V-90.b
        titel: "Café am Markt"
        aufenthalte: [A-91]
        quelle: "erfunden (Beispiel)"
        verlauf:
          - {datum: 2026-11-01, status: vorgeschlagen, wer: Lea}
"""
    r.write_text(t, encoding="utf-8")
    route = bauen.bauen(quelle, tmp_path / "web" / "b")["route"]
    w = next(x for x in route["wahlstellen"] if x["id"] == "V-90")
    a, b = w["optionen"]
    assert {"geoeffnet", "eintritt"} <= {k["id"] for k in w["kriterien"]}
    assert a["merkmale"]["eintritt"]["wert"] == "6 €"
    assert "eintritt" not in b["merkmale"] and "eintritt" not in b["fehlt"], "das Café braucht keinen Eintritt"
    assert "geoeffnet" in b["fehlt"], "aber das Café braucht seine eigene Pflichtangabe"
    tag = next(x for x in route["tage"] if x["id"] == "T-02")
    assert tag["aufenthalte"] == ["A-01", "A-90"]
