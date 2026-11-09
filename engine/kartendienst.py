"""Eigener Kartendienst: Overpass bei Bedarf für die Regionen der Instanz (#444, Spec docs/specs/betrieb/eigener-kartendienst-444.md).

Die Instanz kann einen eigenen Overpass-Dienst betreiben (betrieb/kartendienst.sh, Vorlagen in betrieb/vorlagen/kartendienst/),
der nur die eingestellten Regionen enthält. Dieses Modul wählt je Abfrage den Dienst: Liegt der Rahmen der Abfrage ganz in einem
Rahmen der Abdeckung (<FR_KARTENDIENST_ORDNER>/abdeckung.json), zuerst der eigene Dienst (FR_KARTENDIENST), sonst der
öffentliche (FR_OVERPASS). Ohne FR_KARTENDIENST ist der eigene Dienst aus. Den Abruf selbst macht schreiben.overpass_holen.

abdeckung.json: {"stand": "<Zeitpunkt>", "regionen_pruefsumme": "<Summe>", "rahmen": [[süd, west, nord, ost], ...]}
"""
import json
import re
from pathlib import Path

import instanz

OVERPASS = "https://overpass-api.de/api/interpreter"   # Vorgabe des öffentlichen Dienstes; FR_OVERPASS überschreibt sie
AUSZUEGE = "https://download.geofabrik.de"   # Regionsauszüge (ODbL) für betrieb/kartendienst.sh; Regionen als Pfade, z. B. europe/andorra
TEILFRIST_EIGEN = 10   # Sekunden für den eigenen Dienst (Kaltstart rund 2 s gemessen, Puffer bei Speicherdruck)
ABDECKUNG = "abdeckung.json"
ZAHL = r"\s*(-?\d+(?:\.\d+)?)\s*"
RAHMEN_IN_ABFRAGE = re.compile(r"\(" + ",".join([ZAHL] * 4) + r"\)")


def eigener_dienst():
    """Adresse des eigenen Dienstes aus FR_KARTENDIENST oder None (leer zählt als nicht gesetzt)."""
    return instanz.wert("FR_KARTENDIENST") or None


def oeffentlicher_dienst():
    """Adresse des öffentlichen Dienstes: FR_OVERPASS, sonst die Vorgabe."""
    return instanz.wert("FR_OVERPASS", OVERPASS)


def _rahmen_gueltig(r):
    """Ein Rahmen [süd, west, nord, ost] aus Zahlen, in den Grenzen der Erde, Süd unter Nord und West unter Ost."""
    if not isinstance(r, (list, tuple)) or len(r) != 4:
        return False
    if not all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in r):
        return False
    s, w, n, o = r
    return -90 <= s < n <= 90 and -180 <= w < o <= 180


def abdeckung(ordner):
    """Rahmen der Abdeckung aus <ordner>/abdeckung.json -> [(süd, west, nord, ost), ...]. Fehlender Ordner, fehlende, unlesbare,
    leere oder formal falsche Datei -> [] (nie eine Ausnahme): dann gilt der öffentliche Dienst."""
    if not ordner:
        return []
    try:
        daten = json.loads((Path(ordner) / ABDECKUNG).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    rahmen = daten.get("rahmen") if isinstance(daten, dict) else None
    if not isinstance(rahmen, list) or not rahmen or not all(_rahmen_gueltig(r) for r in rahmen):
        return []
    return [tuple(float(x) for x in r) for r in rahmen]


def rahmen_abgedeckt(rahmen, abdeckung):
    """Liegt der Rahmen (süd, west, nord, ost) ganz in EINEM Rahmen der Abdeckung? Der Rand zählt als innen."""
    s, w, n, o = rahmen
    return any(a_s <= s and a_w <= w and n <= a_n and o <= a_o for a_s, a_w, a_n, a_o in abdeckung)


def rahmen_aus_abfrage(abfrage):
    """Rahmen (süd, west, nord, ost) um alle Rahmen „(s,w,n,o)“ einer Overpass-Abfrage; ohne Rahmen None. Mit einem Umkreis
    (around) ist der Rahmen der Abfrage unbekannt: None, also der öffentliche Dienst."""
    if "around" in (abfrage or ""):
        return None
    alle = [tuple(float(x) for x in m) for m in RAHMEN_IN_ABFRAGE.findall(abfrage or "")]
    if not alle:
        return None
    return (min(r[0] for r in alle), min(r[1] for r in alle), max(r[2] for r in alle), max(r[3] for r in alle))


def dienst_waehlen(rahmen):
    """-> ("eigen", Adresse), wenn ein eigener Dienst eingestellt ist und der Rahmen ganz in seiner Abdeckung liegt,
    sonst ("oeffentlich", Adresse)."""
    eigen = eigener_dienst()
    if eigen and rahmen and rahmen_abgedeckt(rahmen, abdeckung(instanz.wert("FR_KARTENDIENST_ORDNER"))):
        return "eigen", eigen
    return "oeffentlich", oeffentlicher_dienst()


def stempeln(antwort, dienst):
    """Antwort um den antwortenden Dienst ("eigen" oder "oeffentlich") und den Stand der Daten (osm3s.timestamp_osm_base
    oder None) ergänzen -> neues dict."""
    osm3s = antwort.get("osm3s") if isinstance(antwort.get("osm3s"), dict) else {}
    return {**antwort, "dienst": dienst, "stand": osm3s.get("timestamp_osm_base")}
