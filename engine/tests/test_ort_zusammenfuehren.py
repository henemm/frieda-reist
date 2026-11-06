"""Eine Lage je Stelle beim Nachziehen (ADR-0008, Schritt c, frieda-reist #335): neu.py nachziehen führt einen Ort und die gleichnamigen
Wegpunkte zusammen (der Ort übernimmt Koordinaten und Herkunft, die Wegpunkte verweisen mit bezug auf ihn) und meldet Unklares,
statt zu raten. Erfundene Testdaten der Beispielreise."""
import datetime
import shutil
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import bauen  # noqa: E402
import neu  # noqa: E402
from conftest import meldet  # noqa: E402

BEISPIELE = Path(__file__).resolve().parent.parent.parent / "beispiel" / "reisen"
WEHLEN = [50.9585, 14.0325]
HERKUNFT = "eigene Schätzung, 26.10.2026"


def kopie(tmp_path):
    q = tmp_path / "beispielreise"
    shutil.copytree(BEISPIELE / "beispielreise", q)
    neu.nachziehen(q)   # Altlasten der Beispielreise (Rolle kosten in arten.yaml) gehören nicht zu diesem Schritt
    return q


def lesen(q, datei="routen.yaml"):
    return yaml.safe_load((q / "plan" / datei).read_text(encoding="utf-8"))


def schreiben(q, d, datei="routen.yaml"):
    (q / "plan" / datei).write_text(yaml.safe_dump(d, allow_unicode=True, sort_keys=False), encoding="utf-8")


def alte_form(q, aendern=None):
    """Stadt Wehlen wie vor ADR-0008: der Ort ohne Lage, der Wegpunkt A-02 an E-01 mit eigenen Koordinaten und ohne bezug."""
    d = lesen(q)
    d["orte"]["O-02"].pop("merkmale", None)
    mk = d["aufenthalte"]["A-02"]["merkmale"]
    mk.pop("station", None)
    mk["koordinaten"] = {"typ": "koordinaten", "wert": list(WEHLEN), "quelle": HERKUNFT, "geprueft": datetime.date(2026, 10, 26)}
    if aendern:
        aendern(d)
    schreiben(q, d)


def test_beispielreise_ist_zusammengefuehrt(tmp_path):
    """Die Beispielreise im Repo hat den Stand nach dem Schritt: ein zweiter Lauf hat nichts zu tun."""
    q = kopie(tmp_path)
    assert neu.nachziehen(q) == []
    d = lesen(q)
    for oid, aids in (("O-02", ["A-02"]), ("O-03", ["A-08", "A-10"]), ("O-04", ["A-16", "A-18", "A-24"]), ("O-05", ["A-22"]), ("O-06", ["A-27"])):
        assert d["orte"][oid]["merkmale"]["koordinaten"]["wert"]
        for aid in aids:
            mk = d["aufenthalte"][aid]["merkmale"]
            assert "koordinaten" not in mk and mk["station"]["wert"] == oid


def test_ort_uebernimmt_lage_und_herkunft_vom_wegpunkt(tmp_path):
    q = kopie(tmp_path)
    alte_form(q)
    m = neu.nachziehen(q)
    assert meldet(m, "pruefung.neu.nachziehen.ort_lage") and meldet(m, "pruefung.neu.nachziehen.ort_bezug")
    assert not any(t.startswith(("OFFEN", "OPEN")) for t in m)
    d = lesen(q)
    k = d["orte"]["O-02"]["merkmale"]["koordinaten"]
    assert k["typ"] == "koordinaten" and k["wert"] == WEHLEN and k["quelle"] == HERKUNFT and str(k["geprueft"]) == "2026-10-26"
    mk = d["aufenthalte"]["A-02"]["merkmale"]
    assert "koordinaten" not in mk and mk["station"] == {"wert": "O-02", "quelle": HERKUNFT} and mk["nummer"]["wert"] == 1
    r = bauen.bauen(q, tmp_path / "web" / "b")["route"]   # der Bau nimmt es, der Wegpunkt liegt beim Ort
    assert r["aufenthalte"]["A-02"]["punkt"]["von"] == "O-02" and r["aufenthalte"]["A-02"]["punkt"]["wert"] == WEHLEN
    assert neu.nachziehen(q) == []   # idempotent


def test_art_ohne_bezug_bekommt_das_merkmal_ort(tmp_path):
    q = kopie(tmp_path)
    alte_form(q)
    a = lesen(q, "arten.yaml")
    a["arten"]["wegpunkt"]["merkmale"].pop("station")
    schreiben(q, a, "arten.yaml")
    for aid in ("A-08", "A-10"):   # die übrigen Wegpunkte mit station wieder mit eigener Lage, sonst verweisen sie ins Leere
        d = lesen(q)
        d["aufenthalte"][aid]["merkmale"].pop("station")
        schreiben(q, d)
    neu.nachziehen(q)
    m = lesen(q, "arten.yaml")["arten"]["wegpunkt"]["merkmale"]["station"]
    assert m["rolle"] == "bezug" and m["typ"] == "text" and m["name"] == "Ort"
    assert lesen(q)["aufenthalte"]["A-02"]["merkmale"]["station"]["wert"] == "O-02"
    bauen.bauen(q, tmp_path / "web" / "b")


def test_weit_auseinander_wird_gemeldet(tmp_path):
    q = kopie(tmp_path)
    alte_form(q, lambda d: d["aufenthalte"]["A-02"]["merkmale"]["koordinaten"].update(wert=[50.9585, 14.0325]) or d["aufenthalte"].update(
        {"A-99": {"name": "Stadt Wehlen", "art": "wegpunkt", "an": "E-20", "quelle": "Test",
                  "merkmale": {"koordinaten": {"typ": "koordinaten", "wert": [50.9625, 14.0325], "quelle": "Test"}}}}))   # gut 400 m
    vorher = lesen(q)
    m = neu.nachziehen(q)
    assert meldet(m, "pruefung.neu.nachziehen.ort_weit") and any(t.startswith("OFFEN O-02") and "A-02, A-99" in t for t in m)
    assert lesen(q) == vorher   # nichts geraten


def test_nahe_wegpunkte_werden_eine_stelle(tmp_path):
    """Etappenende und -anfang im selben Dorf liegen ein paar Meter auseinander: der Ort nimmt die Lage des ersten."""
    q = kopie(tmp_path)
    alte_form(q, lambda d: d["aufenthalte"].update(
        {"A-99": {"name": "Stadt Wehlen", "art": "wegpunkt", "an": "E-20", "quelle": "Test",
                  "merkmale": {"koordinaten": {"typ": "koordinaten", "wert": [50.9588, 14.0327], "quelle": "Test"}}}}))   # gut 35 m
    neu.nachziehen(q)
    d = lesen(q)
    assert d["orte"]["O-02"]["merkmale"]["koordinaten"]["wert"] == WEHLEN
    assert all(d["aufenthalte"][a]["merkmale"]["station"]["wert"] == "O-02" for a in ("A-02", "A-99"))


def test_wegpunkt_mit_anderem_bezug_bleibt(tmp_path):
    """Der Wegpunkt ist schon die Lage einer Unterkunft: er bleibt, wie er ist, und wird gemeldet."""
    q = kopie(tmp_path)
    alte_form(q, lambda d: d["aufenthalte"]["A-02"]["merkmale"].update(station={"wert": "U-02", "quelle": "Test"}))
    m = neu.nachziehen(q)
    assert meldet(m, "pruefung.neu.nachziehen.ort_fremd") and any("A-02" in t and "U-02" in t for t in m)
    d = lesen(q)
    assert "merkmale" not in d["orte"]["O-02"] and d["aufenthalte"]["A-02"]["merkmale"]["koordinaten"]["wert"] == WEHLEN


def test_wegpunkt_einer_unterkunft_am_ort_bleibt_still(tmp_path):
    """Ist der Wegpunkt die Lage einer Unterkunft an diesem Ort (eine Hütte am Etappenende), liegt der Ort schon über sie dort."""
    q = kopie(tmp_path)
    alte_form(q, lambda d: (d["aufenthalte"]["A-02"]["merkmale"].update(station={"wert": "U-02", "quelle": "Test"}),
                            d["unterkuenfte"]["U-02"].update(ort="O-02")))
    vorher = lesen(q)
    assert not any("O-02" in t for t in neu.nachziehen(q)) and lesen(q) == vorher


def test_nur_aehnlicher_name_wird_gemeldet(tmp_path):
    q = kopie(tmp_path)
    alte_form(q, lambda d: d["aufenthalte"]["A-02"].update(name="stadt-wehlen"))
    m = neu.nachziehen(q)
    assert meldet(m, "pruefung.neu.nachziehen.ort_aehnlich") and "merkmale" not in lesen(q)["orte"]["O-02"]


def test_region_und_ausserhalb_werden_kein_punkt(tmp_path):
    q = kopie(tmp_path)
    alte_form(q, lambda d: d["orte"]["O-06"].update(an="O-02"))
    m = neu.nachziehen(q)
    assert meldet(m, "pruefung.neu.nachziehen.ort_region") and "merkmale" not in lesen(q)["orte"]["O-02"]
    q2 = tmp_path / "zwei"
    shutil.copytree(q, q2)
    alte_form(q2, lambda d: (d["orte"]["O-06"].pop("an"), d["orte"]["O-02"].update(ausserhalb=True)))
    assert not any("O-02" in t for t in neu.nachziehen(q2)) and "merkmale" not in lesen(q2)["orte"]["O-02"]


def test_gleichnamiges_ohne_strecke_bleibt_unberuehrt(tmp_path):
    """Nur Wegpunkte (Aufenthalte an einer Strecke) sind Teil des Schritts; der Lichtenhainer Wasserfall am Wissen (A-30) bleibt."""
    q = kopie(tmp_path)
    vorher = lesen(q)["aufenthalte"]["A-30"]
    assert neu.nachziehen(q) == [] and lesen(q)["aufenthalte"]["A-30"] == vorher and "koordinaten" in vorher["merkmale"]
