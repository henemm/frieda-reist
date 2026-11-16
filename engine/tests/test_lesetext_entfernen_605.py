"""Lesetext entfernen (#605): lesetext_schreiben (narrative_write) mit leerem text entfernt den Lesetext einer Etappe, eines Orts,
einer Unterkunft oder eines Aufenthalts. Wie ein leerer Hinweis bei ding_aendern steht der alte Text in der Antwort und damit im
Verlauf; der Grund ist Pflicht, eine Herkunft nicht. Erfundene Testdaten beider Beispielreisen."""
import shutil
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import bauen  # noqa: E402
import konnektor as kn  # noqa: E402
import schnittstelle  # noqa: E402
import schreiben as sb  # noqa: E402
from conftest import meldet  # noqa: E402

BEISPIELE = Path(__file__).resolve().parent.parent.parent / "beispiel" / "reisen"
IDA = {"name": "Ida"}
GRUND = "Text steht jetzt woanders (Test)"


def kopie(tmp_path, reise="beispielreise"):
    q = tmp_path / reise
    shutil.copytree(BEISPIELE / reise, q)
    return q


def routen(q):
    return yaml.safe_load((q / "plan" / "routen.yaml").read_text(encoding="utf-8"))


def leeren(q, ziel, **mehr):
    return sb.lesetext_schreiben(q, IDA, {"ziel": ziel, "text": "", **mehr})


@pytest.mark.parametrize("reise, did", [("beispielreise", "U-02"), ("beispielreise", "A-01"), ("stadtwochenende", "A-02")])
def test_ding_lesetext_entfernen(tmp_path, reise, did):
    q = kopie(tmp_path, reise)
    gruppe = "unterkuenfte" if did.startswith("U-") else "aufenthalte"
    if "lesetext" not in routen(q)[gruppe][did]:   # die Art von A-02 gliedert den Lesetext, die übrigen nicht
        text = "**Sammlung.** Drei Stockwerke (Test).\n\n- Erdgeschoss\n- Dach" if reise == "stadtwochenende" else "Ablauf (Test):\n\n1. Ankommen\n2. Umschauen"
        sb.lesetext_schreiben(q, IDA, {"ziel": did, "text": text, "quelle": "erfunden (Test)"})
    alt = routen(q)[gruppe][did]["lesetext"]["text"].strip()
    titel, antwort = leeren(q, did, grund=GRUND)
    assert meldet(titel, "schreiben.titel.lesetext_entfernt") and meldet(antwort, "schreiben.antwort.lesetext.entfernt")
    assert alt in antwort and GRUND in antwort   # der alte Text steht im Verlauf (Antwort = Text des Vorgangs)
    d = routen(q)[gruppe][did]
    assert "lesetext" not in d and d.get("name")   # sonst nichts verändert
    daten = bauen.bauen(q, tmp_path / "web")
    assert "lesetext" not in daten["route"][gruppe][did]


def test_grund_ist_pflicht_herkunft_nicht(tmp_path):
    q = kopie(tmp_path)
    with pytest.raises(sb.Ablehnung) as e:
        leeren(q, "U-02")
    assert meldet(str(e.value), "schreiben.text_wert.1") and "grund" in str(e.value)
    with pytest.raises(sb.Ablehnung) as e:
        leeren(q, "U-02", text="   \n ", quelle="")   # nur Leerraum zählt als leer
    assert "grund" in str(e.value)
    assert "lesetext" in routen(q)["unterkuenfte"]["U-02"]
    leeren(q, "U-02", grund=GRUND)   # ohne quelle
    assert "lesetext" not in routen(q)["unterkuenfte"]["U-02"]


def test_ohne_lesetext_nichts_zu_entfernen(tmp_path):
    q = kopie(tmp_path)
    assert "lesetext" not in routen(q)["unterkuenfte"]["U-01"]
    with pytest.raises(sb.Ablehnung) as e:
        leeren(q, "U-01", grund=GRUND)
    assert meldet(str(e.value), "schreiben.lesetext_entfernen.keiner")
    with pytest.raises(sb.Ablehnung) as e:
        leeren(q, "A-99", grund=GRUND)
    assert meldet(str(e.value), "schreiben.lesetext_schreiben.ding_fehlt")


def test_text_weiter_pflicht_wenn_er_fehlt(tmp_path):
    """Nur ein leerer text entfernt; fehlt der Parameter ganz, bleibt es bei der Ablehnung („text“ fehlt)."""
    q = kopie(tmp_path)
    with pytest.raises(sb.Ablehnung) as e:
        sb.lesetext_schreiben(q, IDA, {"ziel": "U-02", "grund": GRUND})
    assert meldet(str(e.value), "schreiben.text_wert.1") and "text" in str(e.value)
    assert "lesetext" in routen(q)["unterkuenfte"]["U-02"]


def test_ort_mit_unterabschnitten_behaelt_sie(tmp_path):
    q = kopie(tmp_path)
    titel, antwort = leeren(q, "O-03", grund=GRUND)
    assert "Kleine Stadt mit Burg über dem Polenztal" in antwort
    t = (q / "inhalt" / "orte.md").read_text(encoding="utf-8")
    assert "Kleine Stadt mit Burg" not in t
    assert "## O-03 Hohnstein\n\n### Ankommen\nDie gewählte Pension Burgblick" in t and "[^1]: Frauenkirche" in t
    d = bauen.bauen(q, tmp_path / "web")
    o3 = next(a for a in d["abschnitte"] if a["id"] == "O-03")
    assert "Kleine Stadt" not in (o3.get("intro") or "") and [b["titel"] for b in o3["bloecke"]] == ["Ankommen"]
    with pytest.raises(sb.Ablehnung) as e:   # zweimal: nichts mehr da
        leeren(q, "O-03", grund=GRUND)
    assert meldet(str(e.value), "schreiben.lesetext_entfernen.keiner")


@pytest.mark.parametrize("reise, oid, nachbar, alt", [("beispielreise", "O-02", "## O-04 Altendorf", "Kleine Stadt an der Elbe"),
                                                    ("stadtwochenende", "O-01", "## O-02 Beispielstadt", "Zuhause von Tom und Lea")])
def test_ort_nur_mit_text_verliert_den_abschnitt(tmp_path, reise, oid, nachbar, alt):
    q = kopie(tmp_path, reise)
    vorher = (q / "inhalt" / "orte.md").read_text(encoding="utf-8")
    _, antwort = leeren(q, oid, grund=GRUND)
    assert alt in antwort and "Herkunft:" not in antwort   # der alte Text im Verlauf, ohne die Herkunftszeile des Schreibwegs
    t = (q / "inhalt" / "orte.md").read_text(encoding="utf-8")
    assert f"## {oid} " not in t and nachbar in t and "\n\n\n" not in t and t.endswith("\n")
    assert len(t.splitlines()) < len(vorher.splitlines())
    bauen.bauen(q, tmp_path / "web")
    sb.lesetext_schreiben(q, IDA, {"ziel": oid, "text": "Wieder da (Test).", "quelle": "erfunden (Test)"})   # neu anlegen geht wieder
    assert f"## {oid} " in (q / "inhalt" / "orte.md").read_text(encoding="utf-8")


def test_etappe_verliert_nur_die_zusammenfassung(tmp_path):
    q = kopie(tmp_path)
    f = q / "inhalt" / "etappen.md"
    sb.lesetext_schreiben(q, IDA, {"ziel": "E-02", "text": "Ein Tag über die Hochfläche (Test).", "quelle": "eigene Begehung (Test)"})
    titel, antwort = leeren(q, "e-02", grund=GRUND)
    assert meldet(titel, "schreiben.titel.lesetext_entfernt") and "Ein Tag über die Hochfläche (Test)." in antwort
    t = f.read_text(encoding="utf-8")
    abschnitt = t[t.index("## E-02 "):t.index("## E-03 ")]
    assert "### Zusammenfassung" not in abschnitt and "Hochfläche (Test)" not in t and "### Eckdaten" in abschnitt and "### Wegpunkte" in abschnitt
    assert t.count("### Zusammenfassung") == 3   # die anderen Etappen behalten ihren Text
    bauen.bauen(q, tmp_path / "web")
    with pytest.raises(sb.Ablehnung) as e:
        leeren(q, "E-02", grund=GRUND)
    assert meldet(str(e.value), "schreiben.lesetext_entfernen.keiner")


def test_konnektor_schema_text_und_ziel_pflicht_grund_beschrieben():
    w = kn.LESETEXT_SCHREIBEN["inputSchema"]
    assert w["required"] == ["ziel", "text"] and "grund" in w["properties"]
    aussen = next(x for x in schnittstelle.aussen([kn.LESETEXT_SCHREIBEN]))
    assert aussen["name"] == "narrative_write" and "reason" in aussen["inputSchema"]["properties"]
    assert aussen["inputSchema"]["required"] == [schnittstelle.parameter_zu_englisch("lesetext_schreiben").get("ziel", "ziel"), "text"]
