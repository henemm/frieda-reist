#!/usr/bin/env python3
"""Abgleich der nginx-Bausteine einer Instanz mit den Vorlagen (#206, #260).

    nginx.py pruefen   erzeugt die Soll-Bausteine (einrichten.sh --erzeugen) in einem Temp-Ordner, vergleicht sie mit den
                       installierten (Zonendatei in conf.d, Konnektor-Baustein und .inc in den Snippets) und sagt, was abweicht,
                       mit dem einen Befehl zum Beheben. Installiert nie etwas und schreibt nie unter /etc: Jede nginx-Zeile
                       wirkt als Root, deshalb bleibt das Installieren ein bewusster Schritt eines Menschen.
                       Ausgang: 0 gleich (oder die Instanz hat die Bausteine noch nicht eingerichtet: kein Abgleich), 3 weicht ab, 1 Fehler.

    nginx.py anwenden  der Befehl aus der Meldung, von Hand mit Root-Rechten (sudo env … nginx.py anwenden): erzeugt das Soll neu, sichert die installierten Dateien
                       nach <FR_DIENST>/nginx-sicherung/<Zeit>, installiert (sudo), prüft mit „nginx -t“ und lädt erst bei bestandener
                       Prüfung neu; besteht sie nicht, stellt er die Sicherung wieder her (neue Dateien werden entfernt) und endet mit 1.
                       Läuft nie automatisch. Ausgang: 0 angewendet (oder nichts zu tun), 1 Fehler oder zurückgerollt.

Orte (Vorgaben, Tests und Instanzen lenken sie um): conf.d aus EI_NGINX_CONFD (/etc/nginx/conf.d), Snippets aus FR_NGINX_SNIPPETS
(/etc/nginx/snippets); Bausteine mit Rechten 640 root liest FR_SUDO (Vorgabe „sudo -n“) mit cat. Prüfung und Neuladen von nginx:
EI_NGINX_TEST (nginx -t) und EI_NGINX_LADEN (systemctl reload nginx), jeweils hinter FR_SUDO. Nur Standardbibliothek.
"""
import difflib
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import time


def lies(pfad, sudo):
    """Inhalt der installierten Datei, None wenn es sie nicht gibt; ohne Leserecht über „sudo cat“."""
    try:
        with open(pfad, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return None
    except PermissionError:
        if not sudo:
            raise
    r = subprocess.run(sudo + ["cat", pfad], capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        # nicht lesbar und kein Beweis, dass sie fehlt: Fehler statt „fehlt“
        raise RuntimeError(f"{pfad} cannot be read ({(r.stderr or 'no access').strip()[:120]})")
    return r.stdout


def erzeugen(ziel):
    """Soll-Bausteine nach <ziel>/nginx (einrichten.sh --erzeugen; die Ersetzung steht nur dort)."""
    skript = os.path.join(os.path.dirname(os.path.abspath(__file__)), "einrichten.sh")
    r = subprocess.run(["bash", skript, "--erzeugen"], env=dict(os.environ, EI_ZIEL=ziel), capture_output=True, text=True,
                       timeout=60)
    if r.returncode != 0:
        raise RuntimeError(f"einrichten.sh --erzeugen failed ({r.returncode}): {(r.stderr or r.stdout).strip()[:300]}")


def dateien(instanz, confd, snippets):
    """(Name, Zielordner) der Bausteine, die der Abgleich vergleicht."""
    return [(f"{instanz}-zone.conf", confd), (f"{instanz}-konnektor-orte.inc", snippets), (f"{instanz}-konnektor.inc", snippets)]


def pruefen(ziel, instanz, confd, snippets, sudo):
    """Liste von Text-Blöcken zu Abweichungen; leer = gleich. None = nichts eingerichtet (keine der Dateien installiert)."""
    ist = {n: lies(os.path.join(ordner, n), sudo) for n, ordner in dateien(instanz, confd, snippets)}
    if all(v is None for v in ist.values()):
        return None
    erg = []
    for name, ordner in dateien(instanz, confd, snippets):
        soll = lies(os.path.join(ziel, "nginx", name), [])
        if ist[name] is None:
            erg.append(f"{name}: missing in {ordner}")
        elif ist[name] != soll:
            diff = list(difflib.unified_diff(ist[name].splitlines(), soll.splitlines(), "installed", "template", lineterm="", n=1))
            kopf = "\n".join(diff[:40]) + (f"\n… ({len(diff) - 40} more lines)" if len(diff) > 40 else "")
            erg.append(f"{name}: differs from the template ({ordner})\n{kopf}")
    return erg


MODI = {"zone": "644", "orte": "640"}


def modus(name):
    return MODI["zone"] if name.endswith("-zone.conf") else MODI["orte"]


def anwenden(ziel, dienst, instanz, confd, snippets, sudo):
    """Soll installieren, mit Sicherung und Rückweg. Ausgang 0 oder 1."""
    erg = pruefen(ziel, instanz, confd, snippets, sudo)
    if erg == []:
        print("nothing to do: installed blocks equal the templates.")
        return 0
    liste = dateien(instanz, confd, snippets)
    sicherung = os.path.join(dienst, "nginx-sicherung", time.strftime("%Y%m%dT%H%M%S"))
    if os.path.islink(os.path.join(dienst, "nginx-sicherung")):
        raise RuntimeError(f"{dienst}/nginx-sicherung is a symlink, refusing to write the backup through it")
    os.makedirs(sicherung, exist_ok=False)
    alt = {}
    for name, ordner in liste:
        inhalt = lies(os.path.join(ordner, name), sudo)
        alt[name] = inhalt
        if inhalt is not None:
            with open(os.path.join(sicherung, name), "w", encoding="utf-8") as f:
                f.write(inhalt)
    print(f"backup of the installed files: {sicherung}")
    if erg is None:
        print("first installation: none of the blocks is installed yet.")

    def installiere(quelle, name, ordner):
        r = subprocess.run(sudo + ["install", "-m", modus(name), quelle, ordner.rstrip("/") + "/"], capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            raise RuntimeError(f"install {name} failed: {(r.stderr or r.stdout).strip()[:200]}")

    def zurueck():
        for name, ordner in liste:
            try:
                if alt[name] is None:
                    subprocess.run(sudo + ["rm", "-f", os.path.join(ordner, name)], capture_output=True, timeout=60)
                else:
                    installiere(os.path.join(sicherung, name), name, ordner)
            except (RuntimeError, OSError, subprocess.SubprocessError) as e:
                print(f"ROLLBACK PROBLEM for {name}: {e} (backup in {sicherung})", file=sys.stderr)
    pruef = shlex.split(os.environ.get("EI_NGINX_TEST", "nginx -t"))
    laden = shlex.split(os.environ.get("EI_NGINX_LADEN", "systemctl reload nginx"))
    try:
        for name, ordner in liste:
            installiere(os.path.join(ziel, "nginx", name), name, ordner)
        t = subprocess.run(sudo + pruef, capture_output=True, text=True, timeout=60)
    except BaseException as e:      # auch Abbruch von Hand (Strg-C): ungeprüfte Dateien dürfen nicht liegen bleiben
        print(f"ERROR: {e}; restoring the backup.", file=sys.stderr)
        zurueck()
        if isinstance(e, (RuntimeError, OSError, subprocess.SubprocessError)):
            return 1
        raise
    if t.returncode != 0:
        print(f"nginx test failed, restoring the backup:\n{(t.stderr or t.stdout).strip()[:600]}", file=sys.stderr)
        zurueck()
        return 1
    r = subprocess.run(sudo + laden, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        print(f"ERROR: reload failed ({(r.stderr or r.stdout).strip()[:200]}); the files are installed and tested.", file=sys.stderr)
        return 1
    print("installed, nginx tested and reloaded.")
    return 0


def befehl(instanz, dienst, snippets):
    """Der eine Befehl aus der Meldung: mit Root-Rechten (nginx.py ändert /etc/nginx) und der Umgebung der Instanz."""
    env = [("FR_WURZEL", os.environ.get("FR_WURZEL", "")), ("FR_INSTANZ", instanz), ("FR_DIENST", dienst), ("FR_NGINX_SNIPPETS", snippets)]
    gesetzt = " ".join(f"{k}={shlex.quote(v)}" for k, v in env if v)
    return f"sudo env {gesetzt} {shlex.quote(os.path.abspath(__file__))} anwenden"


def main(argv):
    if argv not in (["pruefen"], ["anwenden"]):
        print(__doc__, file=sys.stderr)
        return 1
    instanz, dienst = os.environ.get("FR_INSTANZ", ""), os.environ.get("FR_DIENST", "")
    if not instanz or not dienst:
        print("ERROR: FR_INSTANZ and FR_DIENST must be set", file=sys.stderr)
        return 1
    confd = os.environ.get("EI_NGINX_CONFD", "/etc/nginx/conf.d")
    snippets = os.environ.get("FR_NGINX_SNIPPETS", "/etc/nginx/snippets")
    sudo = shlex.split(os.environ.get("FR_SUDO", "sudo -n"))
    if os.geteuid() == 0:
        sudo = []      # mit Root-Rechten aufgerufen: kein sudo davor
    try:
        # Das Soll liegt in einem eigenen Ordner, nie unter /etc; der Befehl erzeugt es beim Anwenden neu
        with tempfile.TemporaryDirectory() as ziel:
            erzeugen(ziel)
            if argv == ["anwenden"]:
                return anwenden(ziel, dienst, instanz, confd, snippets, sudo)
            erg = pruefen(ziel, instanz, confd, snippets, sudo)
    except (RuntimeError, OSError, subprocess.SubprocessError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    if erg is None:
        print(f"nginx blocks of {instanz} are not set up ({confd}, {snippets}): no comparison.")
        return 0
    if not erg:
        return 0
    print("\n".join(erg))
    print("To fix, after checking the differences (backs up the installed files, installs, tests nginx, reloads only if the test passes, "
          "otherwise restores the backup; run by hand with root rights):")
    print(befehl(instanz, dienst, snippets))
    return 3


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
