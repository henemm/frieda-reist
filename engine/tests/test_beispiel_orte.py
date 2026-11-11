"""Die Beispielreisen sind Demo und Anschauung: Jeder Ort, der als „Ort des Tages“ erscheint (Start, Ziel einer Strecke,
Ort einer Unterkunft), hat einen Lesetext im Ortsdossier, damit die Tagesseiten keinen Platzhalter „Noch keine Beschreibung.“
zeigen (#452). Für echte Reisen bleibt der Platzhalter: Dort zeigt er ehrlich eine Lücke."""
import json
import re
from pathlib import Path

import pytest
import yaml

BEISPIEL = Path(__file__).resolve().parents[2] / "beispiel" / "reisen"


def orte_des_tages(route):
    orte = {route.get("start", {}).get("ort"), route.get("ende", {}).get("ort")}
    for s in (route.get("strecken") or {}).values():
        orte |= {s.get("von"), s.get("nach")}
    for u in (route.get("unterkuenfte") or {}).values():
        orte.add(u.get("ort"))
    return {o for o in orte if o}


@pytest.mark.parametrize("reise", ["beispielreise", "stadtwochenende"])
def test_orte_des_tages_haben_lesetext(reise):
    d = BEISPIEL / reise
    cfg = json.loads((d / "reise.json").read_text(encoding="utf-8"))
    route = yaml.safe_load((d / cfg["routen"]["datei"]).read_text(encoding="utf-8"))
    mit_text = set()
    for rel in cfg.get("orte_dossiers") or []:
        mit_text |= set(re.findall(r"^##\s+(O-\d+[A-Za-z]?)\s", (d / rel).read_text(encoding="utf-8"), flags=re.M))
    fehlt = sorted(orte_des_tages(route) - mit_text)
    assert not fehlt, f"{reise}: Orte ohne Lesetext: {fehlt}"
