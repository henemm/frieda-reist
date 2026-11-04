#!/usr/bin/env python3
"""Abgleich der systemd-Einheiten einer Instanz mit den Vorlagen (#260, Option B).

    units.py pruefen [--json]   erzeugt die Soll-Einheiten (einrichten.sh --erzeugen), vergleicht sie mit den installierten
                                und sagt, was abweicht. Ändert nichts. Ausgang: 0 alles gleich, 3 nur erlaubte Abweichungen
                                (eine Installation wäre ohne Rückfrage möglich), 4 auch gesperrte (braucht einen bewussten
                                Schritt), 1 Fehler.

    units.py installieren       installiert Einheiten, die nur erlaubte Abweichungen haben, über das Hilfsprogramm mit Root-Rechten
                                (FR_UNITS_HELFER, Vorgabe /usr/local/sbin/<instanz>-units-installieren; FR_SUDO, Vorgabe „sudo -n“),
                                startet die Dauerdienste neu und prüft erneut. Ausgang wie pruefen, 5 wenn das Hilfsprogramm
                                fehlt oder scheitert.

Erlaubt sind nur ungefährliche Zeilen (Erlaubnisliste ERLAUBT unten): FR_DIENST, FR_ZEITZONE (Umgebungswerte mit engem Wertmuster)
und TimeoutStartSec. Alles andere (User, ExecStart, Rechte, neue oder fehlende Einheiten, Timer) ist gesperrt: Es wird gemeldet,
nie automatisch installiert. Nur Standardbibliothek: Dieselbe Prüfung läuft später im Hilfsprogramm mit Root-Rechten.
"""
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile

# Erlaubnisliste, gleich der im Hilfsprogramm mit Root-Rechten (vorlagen/units-installieren.py; ein Test prüft die Gleichheit):
# (Abschnitt, Schlüssel) -> Muster für den Wert. Bei Environment ist der Schlüssel "Environment:<NAME>", das Muster gilt für den
# Wert nach "NAME=". Ein neuer Eintrag ist eine Sicherheitsentscheidung des Product Owners (docs/betrieb.md).
ERLAUBT = {
    ("Service", "Environment:FR_DIENST"): re.compile(r"^/(?!.*(?:^|/)\.\.?(?:/|$))[A-Za-z0-9_./-]+$"),
    ("Service", "Environment:FR_ZEITZONE"): re.compile(r"^[A-Za-z][A-Za-z0-9_+/-]*$"),
    ("Service", "TimeoutStartSec"): re.compile(r"^[1-9][0-9]{0,4}(?:s|min|h)?$"),
}
EINHEITEN = re.compile(r"^[A-Za-z0-9_.-]+\.(?:service|timer)$")
DAUERDIENSTE = ("rueckmeldungen", "konnektor", "schreiben", "push")   # werden nach dem Installieren neu gestartet


def zeilen(text):
    """Einheit als Liste (Abschnitt, Schlüssel, Wert); Kommentare und Leerzeilen entfallen, ein Abschnittswechsel ist
    (Abschnitt, "", "") und gehört zur Reihenfolge."""
    erg, abschnitt = [], ""
    for roh in text.split("\n"):
        z = roh.strip(" \t")      # wie systemd und das Hilfsprogramm: nur Leerzeichen und Tab, nie Unicode-Leerraum
        if not z or z[0] in "#;":
            continue
        if z.startswith("[") and z.endswith("]"):
            abschnitt = z[1:-1]
            erg.append((abschnitt, "", ""))
        elif "=" in z:
            k, _, w = z.partition("=")
            erg.append((abschnitt, k.strip(" \t"), w.strip(" \t")))
    return erg


def schluessel(z):
    """Schlüssel der Erlaubnisliste, zu dem die Zeile gehört (unabhängig vom Wert), sonst None."""
    k = z[1]
    if k == "Environment":
        k = "Environment:" + z[2].partition("=")[0]
    return k if (z[0], k) in ERLAUBT else None


def erlaubt(z):
    """Zeile gehört zur Erlaubnisliste und ihr Wert passt zum Muster."""
    k = schluessel(z)
    wert = z[2].partition("=")[2] if z[1] == "Environment" else z[2]
    return k is not None and bool(ERLAUBT[(z[0], k)].match(wert))


def beschreibe(z):
    return f"[{z[0]}] {z[1]}={z[2]}" if z[1] else f"section [{z[0]}]"


def abgleich(soll, ist, name):
    """Vergleich einer Einheit: (setzen, entfernen, gesperrt). setzen und entfernen sind Listen von (Abschnitt, Schlüssel,
    Wert) mit erlaubten Zeilen, gesperrt eine Liste von Texten. Fehlt die installierte Einheit (ist=None), ist das gesperrt.
    Strenger oder gleich streng wie das Hilfsprogramm: Was hier erlaubt ist, nimmt es an."""
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
        # Eine installierte Zeile der Erlaubnisliste darf weichen, auch mit unpassendem Wert (sie wird überschrieben)
        (entfernen if schluessel(z) else gesperrt).append(z if schluessel(z) else f"{name}: {beschreibe(z)} installed")
    if any(z[1] == "Environment" and not z[2] for z in s + i):
        gesperrt.append(f"{name}: empty Environment= resets the list")
    schluessel_soll = [schluessel(z) for z in s if schluessel(z)]
    if not gesperrt and len(schluessel_soll) != len(set(schluessel_soll)):
        gesperrt.append(f"{name}: an allowed line appears more than once")
    # Reihenfolge und doppelte Zeilen außerhalb der Erlaubnisliste: gleiche Mengen, aber andere Folge wäre sonst unsichtbar
    if not gesperrt and [z for z in s if not schluessel(z)] != [z for z in i if not schluessel(z)]:
        gesperrt.append(f"{name}: order or number of other lines differs")
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
        if os.path.lexists(os.path.join(systemd, datei + ".d")):
            gesperrt = gesperrt + [f"{datei}: drop-in folder {datei}.d exists (not compared, not installed)"]
        if setzen or entfernen or gesperrt:
            erg[datei] = {"setzen": [list(z) for z in setzen], "entfernen": [list(z) for z in entfernen], "gesperrt": gesperrt}
    return erg


def ausgeben(erg, json_ausgabe=False):
    if json_ausgabe:
        print(json.dumps(erg, indent=1, sort_keys=True))
        return
    for einheit, d in erg.items():
        for z in d["setzen"]:
            print(f"{einheit}: allowed, add {beschreibe(z)}")
        for z in d["entfernen"]:
            print(f"{einheit}: allowed, remove {beschreibe(z)}")
        for g in d["gesperrt"]:
            print(f"{einheit}: BLOCKED, {g}")


def ausgang(erg):
    if any(d["gesperrt"] for d in erg.values()):
        return 4
    return 3 if erg else 0


def installieren(ziel, systemd):
    """Einheiten mit ausschließlich erlaubten Abweichungen über das Hilfsprogramm mit Root-Rechten installieren, die
    betroffenen Dauerdienste neu starten und neu prüfen. Ausgang wie pruefen, 5 wenn das Hilfsprogramm fehlt oder scheitert."""
    erg = pruefen(ziel, systemd)
    zu_tun = sorted(e for e, d in erg.items() if (d["setzen"] or d["entfernen"]) and not d["gesperrt"])
    if not zu_tun:
        ausgeben(erg)
        return ausgang(erg)
    instanz = next((e[:-len("-rueckmeldungen.service")] for e in os.listdir(os.path.join(ziel, "systemd"))
                    if e.endswith("-rueckmeldungen.service")), "")
    helfer = os.environ.get("FR_UNITS_HELFER") or f"/usr/local/sbin/{instanz}-units-installieren"
    sudo = shlex.split(os.environ.get("FR_SUDO", "sudo -n"))
    fehler, geaendert = False, []
    if not os.path.exists(helfer):
        print(f"units helper {helfer} is not installed, nothing installed (docs/betrieb.md, Einheiten abgleichen).")
        return 5
    for einheit in zu_tun:
        soll = lies(os.path.join(ziel, "systemd", einheit)) or ""
        r = subprocess.run(sudo + [helfer, einheit], input=soll.encode("utf-8"), capture_output=True, timeout=60)
        if r.returncode == 0:
            geaendert.append(einheit)
        elif r.returncode != 2:
            print(f"{einheit}: install failed (exit {r.returncode}): {r.stderr.decode('utf-8', 'replace').strip()[:200]}")
            fehler = True
    for einheit in geaendert:
        dienst = einheit[:-len(".service")]
        if dienst.rsplit("-", 1)[-1] in DAUERDIENSTE:
            r = subprocess.run(sudo + ["systemctl", "restart", dienst], capture_output=True, timeout=120)
            if r.returncode != 0:
                print(f"{dienst}: restart failed (exit {r.returncode})")
                fehler = True
    erneut = pruefen(ziel, systemd)
    ausgeben(erneut)
    return 5 if fehler else ausgang(erneut)


def main(argv):
    if not argv or argv[0] not in ("pruefen", "installieren"):
        print(__doc__, file=sys.stderr)
        return 1
    systemd = os.environ.get("EI_SYSTEMD", "/etc/systemd/system")
    try:
        with tempfile.TemporaryDirectory() as ziel:
            erzeugen(ziel)
            if argv[0] == "installieren":
                return installieren(ziel, systemd)
            erg = pruefen(ziel, systemd)
    except (RuntimeError, OSError, subprocess.SubprocessError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    ausgeben(erg, "--json" in argv)
    return ausgang(erg)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
