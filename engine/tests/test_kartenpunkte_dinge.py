"""Kartenpunkte werden Dinge, Kategorien gehen in den Arten auf (ADR-0007, Schritt d, frieda-reist#285): neu.py nachziehen stellt
plan/punkte.yaml, die Punkte in inhalt/wissen-punkte.yaml und plan/kategorien.yaml um; die Karten zeigen dieselben Punkte mit denselben
Farben und Symbolen. Die alten Dateien der Beispielreise (Stand vor dem Schritt) liegen als Vorlage in altformen/kartenpunkte."""
import shutil
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import bauen  # noqa: E402
import neu  # noqa: E402
import routen  # noqa: E402

WURZEL = Path(__file__).resolve().parent.parent.parent
ALT = Path(__file__).resolve().parent / "altformen" / "kartenpunkte"
KATEGORIEN = ("wegpunkt", "unterkunft", "einkehr", "wasser", "notfall", "sehenswert", "verkehr")


def alte_form(tmp_path):
    """Die Beispielreise im Format vor ADR-0007 Schritt d: Punkte und Kategorien in eigenen Dateien, keine Dinge dafür."""
    q = tmp_path / "quelle"
    shutil.copytree(WURZEL / "beispiel/reisen/beispielreise", q)
    for datei, ziel in (("kategorien.yaml", "plan"), ("punkte.yaml", "plan"), ("wissen-punkte.yaml", "inhalt")):
        shutil.copy(ALT / datei, q / ziel / datei)
    r = yaml.safe_load((q / "plan/routen.yaml").read_text(encoding="utf-8"))
    r["aufenthalte"] = {k: v for k, v in r["aufenthalte"].items() if k == "A-01"}
    (q / "plan/routen.yaml").write_text(yaml.safe_dump(r, allow_unicode=True, sort_keys=False), encoding="utf-8")
    a = yaml.safe_load((q / "plan/arten.yaml").read_text(encoding="utf-8"))
    a["arten"] = {k: v for k, v in a["arten"].items() if k not in KATEGORIEN}
    (q / "plan/arten.yaml").write_text(yaml.safe_dump(a, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return q


def test_beispielreise_hat_punkte_als_dinge():
    """Die Beispielreise im Repo ist umgestellt: jeder bisherige Punkt hat eine ID und eine Art, die Kategorien sind Arten."""
    d = bauen.bauen(WURZEL / "beispiel/reisen/beispielreise", Path(__import__("tempfile").mkdtemp()) / "x")
    r = d["route"]
    punkte = {aid: a for aid, a in r["aufenthalte"].items() if r["eltern"].get(aid, "")[:2] in ("E-", "W-")}
    assert len(punkte) == 30 and all(a["art"] in KATEGORIEN for a in punkte.values())
    assert all(r["arten"][k]["gruppe"] in ("punkt", "wissen") for k in KATEGORIEN) and not (WURZEL / "beispiel/reisen/beispielreise/plan/kategorien.yaml").exists()


def test_nachziehen_stellt_punkte_und_kategorien_um(tmp_path):
    q = alte_form(tmp_path)
    alt = bauen.bauen(q, tmp_path / "wa" / "x")
    assert sum(len(l) for l in alt["route"]["punkte"].values()) == 26   # vier Wissens-Punkte stehen in der Karte des Wissens
    meldungen = neu.nachziehen(q)
    assert any("map points" in m for m in meldungen)
    assert not (q / "plan/kategorien.yaml").exists() and not (q / "plan/punkte.yaml").exists()
    roh = yaml.safe_load((q / "plan/routen.yaml").read_text(encoding="utf-8"))
    neue = {k: v for k, v in roh["aufenthalte"].items() if k != "A-01"}
    assert len(neue) == 30 and all(v.get("an", "")[:2] in ("E-", "W-") and v["art"] in KATEGORIEN and v["quelle"] for v in neue.values())
    ids = sorted(neue)
    assert ids[0] == "A-02" and ids[-1] == "A-31"   # neue IDs, fortlaufend
    wissen = yaml.safe_load((q / "inhalt/wissen-punkte.yaml").read_text(encoding="utf-8"))
    assert "bloecke" not in wissen
    neu_ = bauen.bauen(q, tmp_path / "wb" / "x")
    # dieselben Punkte mit denselben Namen, Lagen, Kategorien, Nummern und Sorten; dieselben Kategorien mit Farben und Symbolen
    assert neu_["route"]["punkte"] == alt["route"]["punkte"]
    assert neu_["kategorien"] == alt["kategorien"]
    assert neu.nachziehen(q) == []   # zweimal nichts zu tun


def test_kartenpunkte_sind_nicht_ohne_tag_und_nicht_buchbar(tmp_path):
    d = bauen.bauen(WURZEL / "beispiel/reisen/beispielreise", tmp_path / "x")
    r = d["route"]
    for aid, a in r["aufenthalte"].items():
        if (r["arten"].get(a["art"]) or {}).get("gruppe"):
            assert not a["ohne_tag"] and not r["arten"][a["art"]]["buchbar"]


def test_art_ohne_merkmale_und_punkt_an_einer_strecke(tmp_path):
    """Eine Art darf ohne Merkmale sein; ein Ding dieser Art mit an: <Strecke> ist ein Punkt der Karte der Etappe."""
    q = tmp_path / "quelle"
    shutil.copytree(WURZEL / "beispiel/reisen/beispielreise", q)
    a = yaml.safe_load((q / "plan/arten.yaml").read_text(encoding="utf-8"))
    a["arten"]["supermarkt"] = {"grundform": "aufenthalt", "name": "Supermarkt", "farbe": "#336699", "gruppe": "punkt", "buchbar": False}
    (q / "plan/arten.yaml").write_text(yaml.safe_dump(a, allow_unicode=True, sort_keys=False), encoding="utf-8")
    r = yaml.safe_load((q / "plan/routen.yaml").read_text(encoding="utf-8"))
    r["aufenthalte"]["A-90"] = {"name": "Konsum", "art": "supermarkt", "an": "E-01", "quelle": "erfunden (Test)",
                                "merkmale": {"koordinaten": {"typ": "koordinaten", "wert": [50.96, 14.08], "quelle": "erfunden (Test)"}}}
    (q / "plan/routen.yaml").write_text(yaml.safe_dump(r, allow_unicode=True, sort_keys=False), encoding="utf-8")
    d = bauen.bauen(q, tmp_path / "x")
    p = next(p for p in d["route"]["punkte"]["E-01"] if p["name"] == "Konsum")
    assert p["kat"] == "supermarkt" and p["lage"] == [50.96, 14.08]
    assert d["kategorien"]["supermarkt"]["name"] == "Supermarkt" and d["kategorien"]["supermarkt"]["farbe"] == "#336699"
    assert d["route"]["arten"]["supermarkt"].get("symbol") is None


def test_nachziehen_gibt_punkten_ohne_namen_den_namen_der_art(tmp_path):
    """frieda-reist#295: OSM-Treffer wie Trinkwasser haben keinen Namen. Der Bau lehnt Aufenthalte ohne Namen ab; also bekommt der Punkt
    beim Nachziehen den Namen aus der Art (einzahl, sonst name, sonst Schlüssel der Kategorie), wie bei map_points_fetch."""
    q = alte_form(tmp_path)
    k = yaml.safe_load((ALT / "kategorien.yaml").read_text(encoding="utf-8"))
    k["kategorien"]["pumpe"] = {"gruppe": "punkt"}
    (q / "plan/kategorien.yaml").write_text(yaml.safe_dump(k, allow_unicode=True, sort_keys=False), encoding="utf-8")
    p = yaml.safe_load((q / "plan/punkte.yaml").read_text(encoding="utf-8"))
    p["strecken"]["E-01"] += [
        {"kat": "wasser", "art": "quelle", "lage": [51.001, 14.093], "quelle": "erfunden (Beispielwert)"},      # name und kein einzahl → name der Kategorie
        {"kat": "wegpunkt", "nr": 9, "lage": [51.002, 14.094], "quelle": "erfunden (Beispielwert)"},           # einzahl
        {"name": "", "kat": "pumpe", "lage": [51.003, 14.095], "quelle": "erfunden (Beispielwert)"},           # weder noch → Schlüssel
        {"name": "Brunnen mit Namen", "kat": "wasser", "lage": [51.004, 14.096], "quelle": "erfunden (Beispielwert)"},
    ]
    (q / "plan/punkte.yaml").write_text(yaml.safe_dump(p, allow_unicode=True, sort_keys=False), encoding="utf-8")
    neu.nachziehen(q)
    roh = yaml.safe_load((q / "plan/routen.yaml").read_text(encoding="utf-8"))
    namen = [v["name"] for v in roh["aufenthalte"].values()]
    assert all(namen)   # kein Aufenthalt ohne Namen
    neue = [v["name"] for v in roh["aufenthalte"].values() if v.get("an") == "E-01" and v["merkmale"]["koordinaten"]["wert"][0] in (51.001, 51.002, 51.003, 51.004)]
    assert neue == ["Wasser", "Wegpunkt im Buch", "pumpe", "Brunnen mit Namen"]
    bauen.bauen(q, tmp_path / "w" / "x")   # der Bau lehnt nichts ab
    assert neu.nachziehen(q) == []   # idempotent


def test_nachziehen_laesst_nicht_verschobene_punkte_in_der_datei(tmp_path):
    """Punkte, die nicht zu Dingen werden (ohne_karte mit Begründung, ohne Lage mit Suchbegriffen, unbekannte Kategorie), gehen nicht verloren:
    Sie bleiben in plan/punkte.yaml bzw. inhalt/wissen-punkte.yaml, mit allen Feldern; der Bau liest sie wie vorher. Zweiter Lauf: nichts zu tun."""
    q = alte_form(tmp_path)
    p = yaml.safe_load((q / "plan/punkte.yaml").read_text(encoding="utf-8"))
    p["strecken"]["E-01"] += [{"name": "Nicht sicher verortet", "kat": "wasser", "ohne_karte": "in OSM nicht gefunden", "suche": ["Brunnen X"], "gebiet": "elbe"},
                              {"name": "Unbekannte Kategorie", "kat": "gibtsnicht", "lage": [51.001, 14.001], "quelle": "erfunden (Beispielwert)"}]
    (q / "plan/punkte.yaml").write_text(yaml.safe_dump(p, allow_unicode=True, sort_keys=False), encoding="utf-8")
    w = yaml.safe_load((q / "inhalt/wissen-punkte.yaml").read_text(encoding="utf-8"))
    block = next(iter(w["bloecke"]))
    w["bloecke"][block] += [{"name": "Ohne Lage", "kat": "sehenswert", "gebiet": "elbe", "suche": ["Ohne Lage 1", "Ohne Lage 2"]}]
    (q / "inhalt/wissen-punkte.yaml").write_text(yaml.safe_dump(w, allow_unicode=True, sort_keys=False), encoding="utf-8")
    meldungen = neu.nachziehen(q)
    assert any("not moved" in m for m in meldungen)
    rest = yaml.safe_load((q / "plan/punkte.yaml").read_text(encoding="utf-8"))
    assert rest["strecken"] == {"E-01": [p["strecken"]["E-01"][-2], p["strecken"]["E-01"][-1]]}
    wrest = yaml.safe_load((q / "inhalt/wissen-punkte.yaml").read_text(encoding="utf-8"))
    assert wrest["bloecke"] == {block: [{"name": "Ohne Lage", "kat": "sehenswert", "gebiet": "elbe", "suche": ["Ohne Lage 1", "Ohne Lage 2"]}]}
    bauen.bauen(q, tmp_path / "w" / "x")
    assert neu.nachziehen(q) == []   # zweimal nichts zu tun, nichts wird erneut verschoben
