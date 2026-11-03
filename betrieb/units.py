#!/usr/bin/env python3
"""Abgleich der systemd-Einheiten einer Instanz mit den Vorlagen (#260, Option B).

    units.py pruefen [--json]   erzeugt die Soll-Einheiten (einrichten.sh --erzeugen), vergleicht sie mit den installierten
                                und sagt, was abweicht. Ändert nichts. Ausgang: 0 alles gleich, 3 nur erlaubte Abweichungen
                                (eine Installation wäre ohne Rückfrage möglich), 4 auch gesperrte (braucht einen bewussten
                                Schritt), 1 Fehler.

Erlaubt sind nur ungefährliche Zeilen (Erlaubnisliste ERLAUBT unten): einzelne Umgebungswerte FR_/KN_/RM_ mit engem Wertmuster
und TimeoutStartSec. Alles andere (User, ExecStart, Rechte, neue oder fehlende Einheiten, Timer) ist gesperrt: Es wird gemeldet,
nie automatisch installiert. Nur Standardbibliothek: Dieselbe Prüfung läuft später im Hilfsprogramm mit Root-Rechten.
"""
import json
import os
import re
import subprocess
import sys
import tempfile

# Erlaubnisliste: (Abschnitt, Schlüssel) -> Muster für den ganzen Wert nach dem ersten „=“. Ein neuer Eintrag ist eine
# Sicherheitsentscheidung (docs/betrieb.md, Einheiten abgleichen).
NAME = r"(?:FR|KN|RM)_[A-Z0-9_]+"
WERT = r"[A-Za-z0-9_./:@+,=-]*"   # keine Leerzeichen, Anführungszeichen, Dollar, Prozent, Semikolon oder Backslash
ERLAUBT = {
    ("Service", "Environment"): re.compile(rf"^{NAME}={WERT}$"),
    ("Service", "TimeoutStartSec"): re.compile(r"^(?:[0-9]{1,5}(?:s|min|h)?|infinity)$"),
}
EINHEITEN = re.compile(r"^[A-Za-z0-9_.-]+\.(?:service|timer)$")


def zeilen(text):
    """Einheit als Liste (Abschnitt, Schlüssel, Wert); Kommentare und Leerzeilen entfallen."""
    erg, abschnitt = [], ""
    for roh in text.splitlines():
        z = roh.strip()
        if not z or z[0] in "#;":
            continue
        if z.startswith("[") and z.endswith("]"):
            abschnitt = z[1:-1]
        elif "=" in z:
            k, _, w = z.partition("=")
            erg.append((abschnitt, k.strip(), w.strip()))
    return erg


def erlaubt(z):
    muster = ERLAUBT.get((z[0], z[1]))
    return bool(muster and muster.match(z[2]))


def beschreibe(z):
    return f"[{z[0]}] {z[1]}={z[2]}"


def abgleich(soll, ist, name):
    """Vergleich einer Einheit: (setzen, entfernen, gesperrt). setzen und entfernen sind Listen von (Abschnitt, Schlüssel,
    Wert) mit erlaubten Zeilen, gesperrt eine Liste von Texten. Fehlt die installierte Einheit (ist=None), ist das gesperrt."""
    if ist is None:
        return [], [], [f"{name}: unit is not installed (new)"]
    s, i = zeilen(soll), zeilen(ist)
    fehlt = [z for z in s if z not in i]      # in der Vorlage, nicht installiert
    zuviel = [z for z in i if z not in s]     # installiert, nicht in der Vorlage
    if not name.endswith(".service"):
        # Timer und alles andere: keine erlaubten Zeilen
        return [], [], ([f"{name}: {beschreibe(z)} wanted" for z in fehlt] + [f"{name}: {beschreibe(z)} installed" for z in zuviel])
    setzen, entfernen, gesperrt = [], [], []
    for z in fehlt:
        (setzen if erlaubt(z) else gesperrt).append(z if erlaubt(z) else f"{name}: {beschreibe(z)} wanted")
    for z in zuviel:
        (entfernen if erlaubt(z) else gesperrt).append(z if erlaubt(z) else f"{name}: {beschreibe(z)} installed")
    return setzen, entfernen, gesperrt


def lies(pfad):
    try:
        with open(pfad, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return None


def erzeugen(ziel):
    """Soll-Einheiten nach <ziel>/systemd (einrichten.sh --erzeugen; die Ersetzung steht nur dort)."""
    skript = os.path.join(os.path.dirname(os.path.abspath(__file__)), "einrichten.sh")
    r = subprocess.run(["bash", skript, "--erzeugen"], env=dict(os.environ, EI_ZIEL=ziel), capture_output=True, text=True,
                       timeout=60)
    if r.returncode != 0:
        raise RuntimeError(f"einrichten.sh --erzeugen failed ({r.returncode}): {(r.stderr or r.stdout).strip()[:300]}")


def pruefen(ziel, systemd):
    """Alle Einheiten der Instanz: {Einheit: {setzen, entfernen, gesperrt}} nur für abweichende."""
    erg = {}
    ordner = os.path.join(ziel, "systemd")
    for datei in sorted(os.listdir(ordner)):
        if not EINHEITEN.match(datei):
            continue
        setzen, entfernen, gesperrt = abgleich(lies(os.path.join(ordner, datei)) or "", lies(os.path.join(systemd, datei)), datei)
        if setzen or entfernen or gesperrt:
            erg[datei] = {"setzen": [list(z) for z in setzen], "entfernen": [list(z) for z in entfernen], "gesperrt": gesperrt}
    return erg


def main(argv):
    if not argv or argv[0] != "pruefen":
        print(__doc__, file=sys.stderr)
        return 1
    systemd = os.environ.get("EI_SYSTEMD", "/etc/systemd/system")
    try:
        with tempfile.TemporaryDirectory() as ziel:
            erzeugen(ziel)
            erg = pruefen(ziel, systemd)
    except (RuntimeError, OSError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    if "--json" in argv:
        print(json.dumps(erg, indent=1, sort_keys=True))
    else:
        for einheit, d in erg.items():
            for z in d["setzen"]:
                print(f"{einheit}: allowed, add {beschreibe(z)}")
            for z in d["entfernen"]:
                print(f"{einheit}: allowed, remove {beschreibe(z)}")
            for g in d["gesperrt"]:
                print(f"{einheit}: BLOCKED, {g}")
    if any(d["gesperrt"] for d in erg.values()):
        return 4
    return 3 if erg else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
