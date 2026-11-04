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

Die Zone der Reise-Bausteine (<instanz>_api) steht in <instanz>-zone.conf. Steht sie noch in einer anderen conf.d/*.conf (früher die
gemeinsame Drossel-Datei), meldet „pruefen“ das, und „anwenden“ entfernt dort genau die Zeile (mit dem Kommentarblock direkt darüber) im selben Lauf
mit derselben Sicherung und demselben „nginx -t“ (#316): nginx verbietet doppelte Zonen, ein Zwischenstand wird nie geladen. Ist die Definition
nicht eindeutig (doppelt, mit weiteren Direktiven in der Zeile), ändert „anwenden“ nichts und endet mit 1.

Orte (Vorgaben, Tests und Instanzen lenken sie um): conf.d aus EI_NGINX_CONFD (/etc/nginx/conf.d), Snippets aus FR_NGINX_SNIPPETS
(/etc/nginx/snippets); Bausteine mit Rechten 640 root liest FR_SUDO (Vorgabe „sudo -n“) mit cat. Prüfung und Neuladen von nginx:
EI_NGINX_TEST (nginx -t) und EI_NGINX_LADEN (systemctl reload nginx), jeweils hinter FR_SUDO. Nur Standardbibliothek.
"""
import difflib
import os
import re
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


def fremde_zone(instanz, confd, sudo):
    """{Pfad: (alter Inhalt, neuer Inhalt, Modus)} für jede andere conf.d/*.conf, die die Zone <instanz>_api definiert; die Definition ist dort entfernt.
    Mehrdeutiges (zwei Definitionen, weitere Direktiven in der Zeile) ist ein Fehler, damit nichts Fremdes angefasst wird."""
    zone = instanz.replace("-", "_") + "_api"
    nennt = re.compile(r"zone=" + re.escape(zone) + r"(?![\w-])")
    streng = re.compile(r"^\s*limit_req_zone\s+\S+\s+zone=" + re.escape(zone) + r":\S+\s+rate=\S+\s*;\s*(#.*)?$")
    erg = {}
    if not os.path.isdir(confd):
        return erg
    for name in sorted(os.listdir(confd)):
        pfad = os.path.join(confd, name)
        if not name.endswith(".conf") or name == f"{instanz}-zone.conf" or not os.path.isfile(pfad):
            continue
        text = lies(pfad, sudo)
        zeilen = text.splitlines(keepends=True)
        treffer = [i for i, z in enumerate(zeilen) if not z.lstrip().startswith("#") and "limit_req_zone" in z and nennt.search(z)]
        if not treffer:
            continue
        if len(treffer) > 1 or not streng.match(zeilen[treffer[0]].rstrip("\n")):
            raise RuntimeError(f"{pfad}: the definition of the zone {zone} is not unambiguous (line {treffer[-1] + 1}); "
                               f"remove it by hand, nothing was changed")
        i = start = treffer[0]
        while start > 0 and zeilen[start - 1].lstrip().startswith("#"):
            start -= 1
        del zeilen[start:i + 1]
        if 0 < start < len(zeilen) and not zeilen[start - 1].strip() and not zeilen[start].strip():
            del zeilen[start]      # keine doppelte Leerzeile zurücklassen
        erg[pfad] = (text, "".join(zeilen), "%o" % (os.stat(pfad).st_mode & 0o777))
    return erg


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
    zone = instanz.replace("-", "_") + "_api"
    for pfad, (alt, neu, _) in fremde_zone(instanz, confd, sudo).items():
        diff = list(difflib.unified_diff(alt.splitlines(), neu.splitlines(), "installed", "without the zone", lineterm="", n=1))
        erg.append(f"{os.path.basename(pfad)}: defines the zone {zone}, which belongs in {instanz}-zone.conf ({confd})\n" + "\n".join(diff[:40]))
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
    # (Pfad der installierten Datei, Ordner, Quelle des Solls, Pfad in der Sicherung, Modus)
    liste = [(os.path.join(ordner, n), ordner, os.path.join(ziel, "nginx", n), n, modus(n)) for n, ordner in dateien(instanz, confd, snippets)]
    for pfad, (_, neu, mod) in fremde_zone(instanz, confd, sudo).items():
        name = os.path.basename(pfad)
        quelle = os.path.join(ziel, "fremd", name)
        os.makedirs(os.path.dirname(quelle), exist_ok=True)
        with open(quelle, "w", encoding="utf-8") as f:
            f.write(neu)
        liste.append((pfad, confd, quelle, os.path.join("fremd", name), mod))
    sicherung = os.path.join(dienst, "nginx-sicherung", time.strftime("%Y%m%dT%H%M%S"))
    if os.path.islink(os.path.join(dienst, "nginx-sicherung")):
        raise RuntimeError(f"{dienst}/nginx-sicherung is a symlink, refusing to write the backup through it")
    os.makedirs(sicherung, exist_ok=False)
    alt = {}
    for pfad, _, _, rel, _ in liste:
        inhalt = lies(pfad, sudo)
        alt[pfad] = inhalt
        if inhalt is not None:
            os.makedirs(os.path.dirname(os.path.join(sicherung, rel)), exist_ok=True)
            with open(os.path.join(sicherung, rel), "w", encoding="utf-8") as f:
                f.write(inhalt)
    print(f"backup of the installed files: {sicherung}")
    if erg is None:
        print("first installation: none of the blocks is installed yet.")

    def installiere(quelle, pfad, ordner, mod):
        # unter dem Namen der Zieldatei installieren (die Quelle der Sicherung heißt gleich, liegt aber in einem Unterordner)
        r = subprocess.run(sudo + ["install", "-m", mod, quelle, ordner.rstrip("/") + "/"], capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            raise RuntimeError(f"install {os.path.basename(pfad)} failed: {(r.stderr or r.stdout).strip()[:200]}")

    def zurueck():
        for pfad, ordner, _, rel, mod in liste:
            try:
                if alt[pfad] is None:
                    subprocess.run(sudo + ["rm", "-f", pfad], capture_output=True, timeout=60)
                else:
                    installiere(os.path.join(sicherung, rel), pfad, ordner, mod)
            except (RuntimeError, OSError, subprocess.SubprocessError) as e:
                print(f"ROLLBACK PROBLEM for {os.path.basename(pfad)}: {e} (backup in {sicherung})", file=sys.stderr)
    pruef = shlex.split(os.environ.get("EI_NGINX_TEST", "nginx -t"))
    laden = shlex.split(os.environ.get("EI_NGINX_LADEN", "systemctl reload nginx"))
    try:
        # erst die eigene Zonendatei, dann die fremde: beide vor dem einen „nginx -t“, geladen wird erst danach
        for pfad, ordner, quelle, _, mod in liste:
            installiere(quelle, pfad, ordner, mod)
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
