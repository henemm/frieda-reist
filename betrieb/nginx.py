#!/usr/bin/env python3
"""Abgleich der nginx-Bausteine einer Instanz mit den Vorlagen (#206, #260, #445).

    nginx.py pruefen   erzeugt die Soll-Bausteine (einrichten.sh --erzeugen) in einem Temp-Ordner, vergleicht sie mit den
                       installierten (Zonendatei in conf.d, Konnektor-Baustein und .inc in den Snippets) und sagt, was abweicht,
                       mit dem einen Befehl zum Beheben. Installiert nichts und schreibt nie unter /etc.
                       Ausgang: 0 gleich (oder die Instanz hat die Bausteine noch nicht eingerichtet: kein Abgleich), 3 weicht ab, 1 Fehler.

    nginx.py installieren
                       seit #445: weicht ausschließlich die Orte-Datei <instanz>-konnektor-orte.inc ab, übergibt er ihr Soll auf
                       stdin dem Hilfsprogramm mit Root-Rechten (FR_NGINX_HELFER, Vorgabe /usr/local/sbin/<instanz>-nginx-orte-installieren;
                       davor FR_SUDO, Vorgabe „sudo -n“). Das Hilfsprogramm prüft die Datei gegen eine feste Grammatik, sichert,
                       installiert, prüft mit „nginx -t“ (sonst Rückweg) und lädt neu. Danach prüft er erneut. Weicht noch etwas
                       anderes ab (Konnektor-Baustein, Zonendatei, fremde Zone) oder fehlt die Orte-Datei, ruft er nichts auf und gibt
                       die Abweichungen aus. Läuft automatisch beim Veröffentlichen. Ausgang wie pruefen; 5, wenn das Hilfsprogramm
                       fehlt oder scheitert (mit dessen Ausgang).

    nginx.py anwenden  der Befehl aus der Meldung, von Hand mit Root-Rechten (sudo env … nginx.py anwenden): erzeugt das Soll neu, sichert die installierten Dateien
                       nach <FR_DIENST>/nginx-sicherung/<Zeit>, installiert (sudo), prüft mit „nginx -t“ und lädt erst bei bestandener
                       Prüfung neu; besteht sie nicht, stellt er die Sicherung wieder her (neue Dateien werden entfernt) und endet mit 1.
                       Läuft nie automatisch: Konnektor-Baustein und Zonendatei (proxy_pass, Kopfzeilen, http-Kontext) bleiben ein
                       bewusster Schritt eines Menschen. Ausgang: 0 angewendet (oder nichts zu tun), 1 Fehler oder zurückgerollt.

Die Zone der Reise-Bausteine (<instanz>_api) steht in <instanz>-zone.conf. Steht sie noch in einer anderen conf.d/*.conf (früher die
gemeinsame Drossel-Datei), meldet „pruefen“ das, und „anwenden“ entfernt dort genau die Zeile (mit dem Kommentarblock direkt darüber) im selben Lauf
mit derselben Sicherung und demselben „nginx -t“ (#316): nginx verbietet doppelte Zonen, ein Zwischenstand wird nie geladen. Ist die Definition
nicht eindeutig (doppelt, mit weiteren Direktiven in der Zeile), ändert „anwenden“ nichts und endet mit 1.

Orte (Vorgaben, Tests und Instanzen lenken sie um): conf.d aus EI_NGINX_CONFD (/etc/nginx/conf.d), Snippets aus FR_NGINX_SNIPPETS
(/etc/nginx/snippets). Gelesen wird ohne sudo (#552: keine sudo-Regel mehr für cat); die Bausteine der Reisen liest nur ihr
Hilfsprogramm (nginx-reise-installieren). Eine Datei, die der Aufrufer nicht lesen darf, ist ein Fehler (Ausgang 1), nie „fehlt“.
„anwenden“ läuft mit Root-Rechten und installiert ohne sudo, die Bausteine der Instanz mit 0640 root:<FR_GRUPPE>. Prüfung und Neuladen von nginx: EI_NGINX_TEST (nginx -t) und
EI_NGINX_LADEN (systemctl reload nginx), jeweils hinter FR_SUDO. Nur Standardbibliothek.
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


def lies(pfad, sudo=None):
    """Inhalt der installierten Datei, None wenn es sie nicht gibt. Ohne sudo (#552); nicht lesbar ist kein Beweis, dass sie
    fehlt: Fehler statt „fehlt“."""
    try:
        with open(pfad, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return None
    except PermissionError:
        raise RuntimeError(f"{pfad} cannot be read without root rights (no access)")


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
        try:
            text = lies(pfad, sudo)
        except RuntimeError:
            # Fremde Datei, die der Dienstbenutzer nicht lesen darf (#552: kein sudo cat mehr): kein Abgleich möglich.
            # Definierte sie die Zone der Instanz doppelt, fiele das bei nginx -t auf; „anwenden“ (Root) liest sie.
            continue
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


def abweichungen(ziel, instanz, confd, snippets, sudo):
    """(Text-Blöcke, Befunde) zu Abweichungen; Befunde sind Paare (Datei, „differs“ | „missing“ | „zone“). (None, None) =
    nichts eingerichtet (keine der Dateien installiert)."""
    ist = {n: lies(os.path.join(ordner, n), sudo) for n, ordner in dateien(instanz, confd, snippets)}
    if all(v is None for v in ist.values()):
        return None, None
    erg, befunde = [], []
    for name, ordner in dateien(instanz, confd, snippets):
        soll = lies(os.path.join(ziel, "nginx", name), [])
        if ist[name] is None:
            erg.append(f"{name}: missing in {ordner}")
            befunde.append((name, "missing"))
        elif ist[name] != soll:
            diff = list(difflib.unified_diff(ist[name].splitlines(), soll.splitlines(), "installed", "template", lineterm="", n=1))
            kopf = "\n".join(diff[:40]) + (f"\n… ({len(diff) - 40} more lines)" if len(diff) > 40 else "")
            erg.append(f"{name}: differs from the template ({ordner})\n{kopf}")
            befunde.append((name, "differs"))
    zone = instanz.replace("-", "_") + "_api"
    for pfad, (alt, neu, _) in fremde_zone(instanz, confd, sudo).items():
        diff = list(difflib.unified_diff(alt.splitlines(), neu.splitlines(), "installed", "without the zone", lineterm="", n=1))
        erg.append(f"{os.path.basename(pfad)}: defines the zone {zone}, which belongs in {instanz}-zone.conf ({confd})\n" + "\n".join(diff[:40]))
        befunde.append((os.path.basename(pfad), "zone"))
    return erg, befunde


def pruefen(ziel, instanz, confd, snippets, sudo):
    """Liste von Text-Blöcken zu Abweichungen; leer = gleich. None = nichts eingerichtet (keine der Dateien installiert)."""
    return abweichungen(ziel, instanz, confd, snippets, sudo)[0]


# Bausteine der Instanz: 0640 root:<Gruppe des Dienstbenutzers> (#552), damit pruefen sie ohne sudo lesen kann
MODI = {"zone": "640", "orte": "640"}


def modus(name):
    return MODI["zone"] if name.endswith("-zone.conf") else MODI["orte"]


def gruppe_des_dienstes():
    """Gruppe des Dienstbenutzers: FR_GRUPPE, sonst die eigene Gruppe des Aufrufers (veroeffentlichen.sh läuft als er). Mit
    Root-Rechten nur FR_GRUPPE: die Gruppe von root ist nie die des Dienstbenutzers; leer heißt unbekannt."""
    import grp
    if os.environ.get("FR_GRUPPE"):
        return os.environ["FR_GRUPPE"]
    if os.geteuid() == 0:
        return ""
    try:
        return grp.getgrgid(os.getgid()).gr_name
    except KeyError:
        return ""


def meldung(schluessel, **werte):
    """Text aus dem Katalog der Software (engine/texte_<sprache>.py, ADR-0006) in der Sprache der Software."""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "engine"))
    import texte
    return texte.t(texte.VORGABE_REISE, schluessel, **werte)


def install_befehl(mod, quelle, ordner, gruppe, root, besitzer="root"):
    """install-Aufruf für eine Datei. Mit Root-Rechten und Gruppe: Besitz <besitzer>:<gruppe>, für die Bausteine der Instanz
    root:<FR_GRUPPE> (#552), für fremde Dateien ihr bisheriger Besitz (Nummern aus stat; install legte sie sonst als root:root
    an). Läufe ohne Root (Tests) behalten den Besitz."""
    besitz = ["-o", besitzer, "-g", gruppe] if root and gruppe else []
    return ["install", "-m", mod, *besitz, quelle, ordner.rstrip("/") + "/"]


def anwenden(ziel, dienst, instanz, confd, snippets, sudo):
    """Soll installieren, mit Sicherung und Rückweg. Ausgang 0 oder 1."""
    erg = pruefen(ziel, instanz, confd, snippets, sudo)
    if erg == []:
        print("nothing to do: installed blocks equal the templates.")
        return 0
    gruppe = gruppe_des_dienstes()
    root = os.geteuid() == 0
    if root and not gruppe:
        raise RuntimeError(meldung("dienst.nginx.gruppe_fehlt"))
    # (Pfad der installierten Datei, Ordner, Quelle des Solls, Pfad in der Sicherung, Modus, (Besitzer, Gruppe))
    liste = [(os.path.join(ordner, n), ordner, os.path.join(ziel, "nginx", n), n, modus(n), ("root", gruppe))
             for n, ordner in dateien(instanz, confd, snippets)]
    for pfad, (_, neu, mod) in fremde_zone(instanz, confd, sudo).items():
        name = os.path.basename(pfad)
        quelle = os.path.join(ziel, "fremd", name)
        os.makedirs(os.path.dirname(quelle), exist_ok=True)
        with open(quelle, "w", encoding="utf-8") as f:
            f.write(neu)
        st = os.stat(pfad)      # fremde Datei: Modus und Besitz bleiben (AC-21)
        liste.append((pfad, confd, quelle, os.path.join("fremd", name), mod, (str(st.st_uid), str(st.st_gid))))
    sicherung = os.path.join(dienst, "nginx-sicherung", time.strftime("%Y%m%dT%H%M%S"))
    if os.path.islink(os.path.join(dienst, "nginx-sicherung")):
        raise RuntimeError(f"{dienst}/nginx-sicherung is a symlink, refusing to write the backup through it")
    os.makedirs(sicherung, exist_ok=False)
    alt = {}
    for pfad, _, _, rel, _, _ in liste:
        inhalt = lies(pfad, sudo)
        alt[pfad] = inhalt
        if inhalt is not None:
            os.makedirs(os.path.dirname(os.path.join(sicherung, rel)), exist_ok=True)
            with open(os.path.join(sicherung, rel), "w", encoding="utf-8") as f:
                f.write(inhalt)
    print(f"backup of the installed files: {sicherung}")
    if erg is None:
        print("first installation: none of the blocks is installed yet.")

    def installiere(quelle, pfad, ordner, mod, besitz):
        # unter dem Namen der Zieldatei installieren (die Quelle der Sicherung heißt gleich, liegt aber in einem Unterordner)
        # anwenden läuft mit Root-Rechten (sudo env … nginx.py anwenden): install ohne sudo davor (#552)
        r = subprocess.run(install_befehl(mod, quelle, ordner, besitz[1], root, besitzer=besitz[0]),
                           capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            raise RuntimeError(f"install {os.path.basename(pfad)} failed: {(r.stderr or r.stdout).strip()[:200]}")

    def zurueck():
        for pfad, ordner, _, rel, mod, besitz in liste:
            try:
                if alt[pfad] is None:
                    if os.path.lexists(pfad):
                        os.remove(pfad)
                else:
                    installiere(os.path.join(sicherung, rel), pfad, ordner, mod, besitz)
            except (RuntimeError, OSError, subprocess.SubprocessError) as e:
                print(f"ROLLBACK PROBLEM for {os.path.basename(pfad)}: {e} (backup in {sicherung})", file=sys.stderr)
    pruef = shlex.split(os.environ.get("EI_NGINX_TEST", "nginx -t"))
    laden = shlex.split(os.environ.get("EI_NGINX_LADEN", "systemctl reload nginx"))
    try:
        # erst die eigene Zonendatei, dann die fremde: beide vor dem einen „nginx -t“, geladen wird erst danach
        for pfad, ordner, quelle, _, mod, besitz in liste:
            installiere(quelle, pfad, ordner, mod, besitz)
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
    env = [("FR_WURZEL", os.environ.get("FR_WURZEL", "")), ("FR_INSTANZ", instanz), ("FR_DIENST", dienst), ("FR_NGINX_SNIPPETS", snippets),
           ("FR_GRUPPE", gruppe_des_dienstes())]
    gesetzt = " ".join(f"{k}={shlex.quote(v)}" for k, v in env if v)
    return f"sudo env {gesetzt} {shlex.quote(os.path.abspath(__file__))} anwenden"


def ausgeben(erg, instanz, dienst, confd, snippets):
    """Ergebnis von pruefen ausgeben; Ausgang 0 (gleich oder nicht eingerichtet) oder 3 (weicht ab)."""
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


def installieren(ziel, dienst, instanz, confd, snippets, sudo):
    """Nur die Orte-Datei weicht ab: über das Hilfsprogramm mit Root-Rechten installieren (#445), danach erneut prüfen.
    Ausgang wie pruefen, 5 wenn das Hilfsprogramm fehlt oder mit einem Ausgang außer 0 und 2 endet."""
    orte = f"{instanz}-konnektor-orte.inc"
    erg, befunde = abweichungen(ziel, instanz, confd, snippets, sudo)
    if befunde != [(orte, "differs")]:
        # nichts abweichend, nicht eingerichtet, oder mehr als die Orte-Datei: kein Aufruf, nur die Abweichungen; die letzte
        # Zeile fasst zusammen (veroeffentlichen.sh nimmt sie für „Install attempt:“, ohne die Liste zu wiederholen)
        rc = ausgeben(erg, instanz, dienst, confd, snippets)
        if befunde:
            print(f"install skipped: other files differ (only a differing {orte} is installed automatically)")
        return rc
    helfer = os.environ.get("FR_NGINX_HELFER") or f"/usr/local/sbin/{instanz}-nginx-orte-installieren"
    if not os.path.exists(helfer):
        print(f"helper missing ({helfer})")
        return 5
    with open(os.path.join(ziel, "nginx", orte), "rb") as f:
        soll = f.read()
    try:
        r = subprocess.run(sudo + [helfer], input=soll, capture_output=True, timeout=180)
        rc, grund = r.returncode, (r.stderr or r.stdout).decode("utf-8", "replace").strip()
        grund = " | ".join(z.strip() for z in grund.splitlines() if z.strip())      # eine Zeile für die Meldung
    except (OSError, subprocess.SubprocessError) as e:
        rc, grund = "not started", str(e)
    if rc not in (0, 2):
        bedeutung = {3: "rejected, nothing changed", 4: "nginx -t failed, previous file restored",
                     5: "installed and tested, but nginx reload failed", 6: "rollback not secured, not reloaded"}.get(rc, "unknown")
        print(f"helper {os.path.basename(helfer)} failed (exit {rc}, {bedeutung}): {grund[:300]}")
        return 5
    erneut = pruefen(ziel, instanz, confd, snippets, sudo)
    if rc == 0 and not erneut:
        print(f"{orte} installed by the helper, nginx tested and reloaded.")
    return ausgeben(erneut, instanz, dienst, confd, snippets)


def main(argv):
    if argv not in (["pruefen"], ["anwenden"], ["installieren"]):
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
            if argv == ["installieren"]:
                return installieren(ziel, dienst, instanz, confd, snippets, sudo)
            erg = pruefen(ziel, instanz, confd, snippets, sudo)
    except (RuntimeError, OSError, subprocess.SubprocessError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    return ausgeben(erg, instanz, dienst, confd, snippets)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
