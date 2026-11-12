"""Merkmale, die die Software für eine Rolle anlegt (Kartenpunkte als Dinge, ADR-0007 Schritt d), heißen in der Sprache der Reise
(frieda-reist#547). Bis dahin standen in deutschen Reisen „Number“, „Sort“, „Place“; neu.py nachziehen stellt das um (#250)."""
import shutil
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import neu  # noqa: E402
import schreiben  # noqa: E402
import texte  # noqa: E402

WURZEL = Path(__file__).resolve().parent.parent.parent
ENGLISCH = {"Nummer": "Number", "Weitere Namen": "Other names", "Ort": "Place", "Sorte": "Sort", "Unterkunft": "Accommodation"}


def alte_form(tmp_path):
    """Die Beispielreise mit den englischen Namen der Rollen-Merkmale, wie die Software sie bis #547 anlegte."""
    q = tmp_path / "reise"
    shutil.copytree(WURZEL / "beispiel/reisen/beispielreise", q)
    p = q / "plan/arten.yaml"
    t = p.read_text(encoding="utf-8")
    for de, en in ENGLISCH.items():
        assert f"        name: {de}\n" in t, de
        t = t.replace(f"        name: {de}\n", f"        name: {en}\n")
    p.write_text(t, encoding="utf-8")
    return q


def namen(q):
    arten = yaml.safe_load((q / "plan/arten.yaml").read_text(encoding="utf-8"))["arten"]
    return {(a, k): m["name"] for a, d in arten.items() for k, m in (d.get("merkmale") or {}).items() if isinstance(m, dict) and m.get("rolle") in
            ("nummer", "alias", "sorte", "osm", "trinkbar", "oeffnung", "bezug")}


def test_neues_merkmal_einer_rolle_heisst_in_der_sprache_der_reise():
    art = {}
    assert schreiben.art_rolle_sichern(art, "nummer", "de") == "nummer"
    assert art["merkmale"]["nummer"]["name"] == texte.t("de", "inhalt.rolle.nummer") == "Nummer"
    art = {}
    schreiben.art_rolle_sichern(art, "sorte", "en")
    assert art["merkmale"]["sorte"]["name"] == "Sort"


def test_nachziehen_benennt_englische_vorgabenamen_in_einer_deutschen_reise_um(tmp_path):
    q = alte_form(tmp_path)
    assert set(namen(q).values()) == set(ENGLISCH.values())
    vorher = (q / "plan/arten.yaml").read_text(encoding="utf-8")
    probe = neu.rollen_namen_nachziehen(q, schreiben=False)
    assert len(probe) == 8 and (q / "plan/arten.yaml").read_text(encoding="utf-8") == vorher   # Probe schreibt nichts
    m = neu.rollen_namen_nachziehen(q)
    assert m == probe
    assert set(namen(q).values()) == set(ENGLISCH)
    nachher = (q / "plan/arten.yaml").read_text(encoding="utf-8")
    # nur die acht Namenszeilen ändern sich, Kommentare und Form der Datei bleiben
    assert len(vorher.splitlines()) == len(nachher.splitlines())
    assert sum(a != b for a, b in zip(vorher.splitlines(), nachher.splitlines())) == 8
    assert nachher == (WURZEL / "beispiel/reisen/beispielreise/plan/arten.yaml").read_text(encoding="utf-8")
    assert neu.rollen_namen_nachziehen(q) == []   # zweiter Lauf: nichts mehr


def test_nachziehen_laesst_eigene_namen_und_englische_reisen(tmp_path):
    q = alte_form(tmp_path)
    p = q / "plan/arten.yaml"
    arten = yaml.safe_load(p.read_text(encoding="utf-8"))
    arten["arten"]["hotel"]["merkmale"]["zimmernummer"] = {"name": "Number", "typ": "text"}   # von der Reise so genannt, ohne Rolle
    arten["arten"]["wegpunkt"]["merkmale"]["nummer"]["name"] = "Nr. im Buch"                    # von der Reise umbenannt
    p.write_text(yaml.safe_dump(arten, allow_unicode=True, sort_keys=False), encoding="utf-8")
    neu.rollen_namen_nachziehen(q)
    arten = yaml.safe_load(p.read_text(encoding="utf-8"))["arten"]
    assert arten["hotel"]["merkmale"]["zimmernummer"]["name"] == "Number"
    assert arten["wegpunkt"]["merkmale"]["nummer"]["name"] == "Nr. im Buch"
    assert arten["einkehr"]["merkmale"]["sorte"]["name"] == "Sorte"
    # eine englische Reise behält die englischen Namen
    e = alte_form(tmp_path / "en")
    r = e / "reise.yaml"
    r.write_text(r.read_text(encoding="utf-8").replace("sprache: de", "sprache: en", 1), encoding="utf-8")
    assert neu.rollen_namen_nachziehen(e) == []
    assert set(namen(e).values()) == set(ENGLISCH.values())
