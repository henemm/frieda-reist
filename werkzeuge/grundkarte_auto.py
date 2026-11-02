#!/usr/bin/env python3
"""Offline-Grundkarte der automatischen Karte holen (Epic #225, #239: K9 Straßen und Ortsnamen ohne Handarbeit, K18 Zoom nach Fläche).

Läuft beim Veröffentlichen vor dem Bau jeder Reise (betrieb/veroeffentlichen.sh). Baut die Daten der Reise zur Probe und nimmt
den Plan der Grundkarte aus der automatischen Karte (engine/karte.py, grundkarten_plan): Übersicht in der Zoomstufe nach
Fläche, bei langen Fahrten dazu Detailkarten der Gebiete. Hat sich der Plan seit dem letzten Holen nicht geändert und liegen die
Dateien da, tut es nichts. Sonst holt es die Karten mit werkzeuge/karte-holen.sh (Protomaps-Tagesbuild, OpenStreetMap, ODbL)
nach reisen/<reise>/medien/karte/ (nicht im Repo, .gitignore) und merkt sich den Plan in medien/karte/grundkarte.json.
Reisen mit handgepflegter Karte (plan/karte.yaml) und ohne Baustein Karte bleiben unberührt.

Ohne Netz scheitert nichts: Das Skript endet mit 1, das Veröffentlichen baut trotzdem (die Karte bleibt schematisch oder alt,
der Kartenstatus nennt es nicht als Fehler). Aufruf: FR_WURZEL=<Bauordner> frieda/werkzeuge/grundkarte_auto.py <reise>
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER.parent / "engine"))
import bauen  # noqa: E402
import instanz  # noqa: E402


def plan_von(reise_dir):
    """Plan der Grundkarte der automatischen Karte -> dict oder None (keine automatische Karte, Bau scheitert)."""
    with tempfile.TemporaryDirectory(prefix="frieda-grundkarte-") as tmp:
        try:
            d = bauen.Bauer(Path(reise_dir), tmp).daten()
        except bauen.BauFehler:
            return None
    k = (d.get("route") or {}).get("karte") or {}
    return k.get("grundkarten") if k.get("auto") else None


def bbox(r):
    return ",".join(f"{v:.4f}" for v in (r["west"], r["sued"], r["ost"], r["nord"]))


def karte_holen(reise_dir, name, rahmen, zoom):
    """Eine Karte mit werkzeuge/karte-holen.sh holen -> True bei Erfolg."""
    reise_dir = Path(reise_dir)
    env = {**os.environ, "FR_WURZEL": str(reise_dir.parent.parent), "FR_KARTE_BBOX": bbox(rahmen), "FR_KARTE_ZIEL": name, "MAXZOOM": str(zoom)}
    r = subprocess.run([str(HIER / "karte-holen.sh"), reise_dir.name], env=env)
    return r.returncode == 0


def main(reise_dir, holen=karte_holen):
    reise_dir = Path(reise_dir)
    plan = plan_von(reise_dir)
    if plan is None:
        print(f"{reise_dir.name}: no automatic map, nothing to fetch.")
        return 0
    ordner = reise_dir / "medien" / "karte"
    stand = ordner / "grundkarte.json"
    karten = [("grundkarte", plan["rahmen"], plan["zoom"])] + [(d["name"], d["rahmen"], d["zoom"]) for d in plan["details"]]
    try:
        alt = json.loads(stand.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        alt = None
    if alt == plan and all((ordner / f"{n}.pmtiles").exists() for n, _, _ in karten):
        print(f"{reise_dir.name}: base map unchanged.")
        return 0
    ok = True
    for name, rahmen, zoom in karten:
        print(f"{reise_dir.name}: fetching {name} (zoom {zoom}, {bbox(rahmen)}).")
        ok = holen(reise_dir, name, rahmen, zoom) and ok
    # Detailkarten, die der Plan nicht mehr kennt, fallen weg
    for f in ordner.glob("detail-*.pmtiles"):
        if f.stem not in {n for n, _, _ in karten}:
            f.unlink()
    if not ok:
        print(f"{reise_dir.name}: base map not (fully) fetched; the page is built with the map it has.")
        return 1
    ordner.mkdir(parents=True, exist_ok=True)
    stand.write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Aufruf: grundkarte_auto.py <reise>")
    sys.exit(main(Path(instanz.wurzel()) / "reisen" / sys.argv[1]))
