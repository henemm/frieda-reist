#!/usr/bin/python3 -I
"""Installiert die Orte-Datei des Konnektors (<instanz>-konnektor-orte.inc) einer Instanz (#445, Teil 3). Läuft mit Root-Rechten.

Aufruf:  sudo -n <instanz>-nginx-orte-installieren   (die neue Orte-Datei kommt auf stdin, keine Argumente)

Diese Datei gehört auf dem Server root und liegt außerhalb des Repos (/usr/local/sbin); die Software kann sie nicht ändern.
Sie wird aus betrieb/vorlagen/nginx-orte-installieren.py von einrichten.sh erzeugt (Instanz, Snippets-Ordner und Zonen
eingesetzt) und einmal bewusst installiert (docs/betrieb.md). Nur Standardbibliothek, Start mit -I (kein Import aus dem
Arbeitsordner, keine PYTHON-Umgebung). Sie traut dem Aufrufer nichts: Sie prüft den ganzen neuen Text gegen eine feste
Grammatik (GRAMMATIK unten), liest die installierte Datei selbst und lässt sich weder durch Umgebung noch durch Argumente auf
andere Pfade oder Programme lenken (Ziel, NGINX, SYSTEMCTL und die Umgebung der Unterprozesse sind fest).

Ablauf: Eingabe lesen, Sperre, Grammatik, Installiertes lesen, gleich? (2), Sicherung im Root-Ordner SICHERUNG (die letzten 20
bleiben), atomar ersetzen, nginx -t (scheitert er: Sicherung zurück, erneut nginx -t), systemctl reload nginx.

Ausgang: 0 installiert und geladen (auf stdout nur der Dateiname), 2 nichts zu tun, 3 abgelehnt oder vor dem Ersetzen
gescheitert (auch: installierte Datei größer als 64 KiB; installierte Datei unverändert), 4 nginx -t scheiterte, alter Stand zurück, 5 Reload scheiterte (Datei installiert
und getestet), 6 Rückweg nicht gesichert (zweites nginx -t gescheitert oder Zurückschreiben gescheitert), jeweils ohne Reload.
Grund auf stderr.

GRAMMATIK (Spec docs/specs/betrieb/nginx-orte-automatisch-445.md): oben nur location-Blöcke, Kommentarzeilen und Leerzeilen;
Kopf „location = <Pfad> {“, „location ^~ <Pfad> {“ (Pfad endet auf / oder beginnt mit /.well-known/) oder „location ~ ^/…$ {“
(leer, ein Wort oder eine nicht fangende Gruppe aus Wörtern, optional mit ?); kein Ort überdeckt /.well-known/acme-challenge
(Zertifikatsprüfung); im Block, je höchstens einmal: limit_req mit einer
der drei Zonen der Instanz, limit_req_status 429, include des eigenen Konnektor-Bausteins (Pflicht), proxy_buffering off,
proxy_read_timeout. Alles andere lehnt die ganze Eingabe ab. Eine Erweiterung ist eine eigene, geprüfte Änderung.
"""
import fcntl
import os
import re
import stat
import subprocess
import sys
import tempfile
import time
import unicodedata

INSTANZ = "__INSTANZ__"
SNIPPETS = "__SNIPPETS__"
ZONEN = ("__ZONE_MCP__", "__ZONE_ANMELDEN__", "__ZONE_KONTO__")
NAME = INSTANZ + "-konnektor-orte.inc"
INCLUDE = SNIPPETS + "/" + INSTANZ + "-konnektor.inc"
SICHERUNG = "/var/lib/" + INSTANZ + "-nginx-sicherung"
SPERRE = "/var/lib/" + INSTANZ + "-nginx-orte-installieren.sperre"
NGINX = "/usr/sbin/nginx"
SYSTEMCTL = "/usr/bin/systemctl"
UMGEBUNG = {"PATH": "/usr/sbin:/usr/bin:/sbin:/bin"}
MAX_BYTES = 64 * 1024
BEHALTEN = 20
# Die Zertifikatsprüfung (Let's Encrypt, HTTP-01) darf kein Ort der Konnektor-Datei überdecken
ACME = "/.well-known/acme-challenge"

# Pfade der Orte: = und ^~ mit mindestens einem Zeichen nach dem führenden /; ~ verankert, leer, ein Wort oder eine Gruppe
PFAD = re.compile(r"/[A-Za-z0-9._-][A-Za-z0-9._/-]*")
WORT = r"[A-Za-z0-9_-]+"
REGEX = re.compile(r"\^/(?:" + WORT + r"|\(\?:" + WORT + r"(?:\|" + WORT + r")*\)\??)?\$")
# Anweisungen im Block: Name -> Prüfung der Wörter (ohne das abschließende ;)
ANWEISUNGEN = {
    "limit_req": lambda w: (len(w) == 4 and w[1] in tuple("zone=" + z for z in ZONEN)
                            and re.fullmatch(r"burst=[0-9]{1,3}", w[2]) is not None and w[3] == "nodelay"),
    "limit_req_status": lambda w: w == ["limit_req_status", "429"],
    "include": lambda w: w == ["include", INCLUDE],
    "proxy_buffering": lambda w: w == ["proxy_buffering", "off"],
    "proxy_read_timeout": lambda w: len(w) == 2 and re.fullmatch(r"[0-9]{1,4}s", w[1]) is not None,
}
VERBOTEN = set("\"'`\\<>&#")      # außerhalb von Kommentarzeilen; { } ; trennt die Zerlegung, $ | ( ) ? prüfen die Muster
TOKEN = re.compile(r"[{};]|[^ \t\n{};]+")


class Abgelehnt(Exception):
    pass


# Ob in diesem Lauf das Ersetzen der installierten Datei schon begonnen hat: Ein unerwarteter Fehler davor endet mit 3
# (nichts verändert), danach mit 6 (Zustand nicht gesichert).
ERSETZEN_BEGONNEN = []


def pruefe_pfad(modifikator, pfad):
    if modifikator == "~":
        if not REGEX.fullmatch(pfad):
            raise Abgelehnt(f"regex location not allowed: {pfad[:60]!r}")
        return
    if not PFAD.fullmatch(pfad) or "//" in pfad or any(teil in (".", "..") for teil in pfad.split("/")):
        raise Abgelehnt(f"location path not allowed: {pfad[:60]!r}")
    if modifikator == "^~" and not (pfad.endswith("/") or pfad.startswith("/.well-known/")):
        raise Abgelehnt(f"prefix location must end with / (segment boundary): {pfad[:60]!r}")
    if pfad.startswith(ACME) or (modifikator == "^~" and ACME.startswith(pfad)):
        raise Abgelehnt(f"location would cover {ACME}: {pfad[:60]!r}")


def pruefe(daten):
    """Den ganzen Text gegen die Grammatik prüfen; Abgelehnt bei jedem Verstoß. Gibt die Zahl der Blöcke zurück."""
    if len(daten) > MAX_BYTES:
        raise Abgelehnt("input too large")
    try:
        text = daten.decode("utf-8")
    except UnicodeDecodeError:
        raise Abgelehnt("not valid UTF-8")
    if any(c not in "\n\t" and unicodedata.category(c) == "Cc" for c in text):
        raise Abgelehnt("control characters")
    anweisungen = []
    for nr, zeile in enumerate(text.split("\n"), 1):
        if zeile.rstrip(" \t").endswith("\\"):
            raise Abgelehnt(f"line {nr}: line continuation")
        z = zeile.strip(" \t")
        if not z or z.startswith("#"):
            continue      # Leerzeile oder Kommentarzeile (darf Umlaute enthalten)
        if not z.isascii():
            raise Abgelehnt(f"line {nr}: non-ASCII character outside a comment line")
        if VERBOTEN & set(z):
            raise Abgelehnt(f"line {nr}: character not allowed: {''.join(sorted(VERBOTEN & set(z)))!r}")
        anweisungen.append(zeile)
    woerter = TOKEN.findall("\n".join(anweisungen))
    koepfe, bloecke, i = set(), 0, 0
    while i < len(woerter):
        if woerter[i:i + 1] != ["location"] or len(woerter) < i + 4 or woerter[i + 3] != "{":
            raise Abgelehnt(f"only location blocks are allowed at the top level (near {' '.join(woerter[i:i + 4])[:60]!r})")
        modifikator, pfad = woerter[i + 1], woerter[i + 2]
        if modifikator not in ("=", "^~", "~"):
            raise Abgelehnt(f"location modifier not allowed: {modifikator[:20]!r}")
        pruefe_pfad(modifikator, pfad)
        if (modifikator, pfad) in koepfe:
            raise Abgelehnt(f"location {modifikator} {pfad} more than once")
        koepfe.add((modifikator, pfad))
        i += 4
        gesehen, aktuell = set(), []
        while True:
            if i >= len(woerter):
                raise Abgelehnt(f"block of location {pfad} not closed")
            w = woerter[i]
            i += 1
            if w == "}" and not aktuell:
                break
            if w == "{" or w == "}":
                raise Abgelehnt(f"nested block or missing ; in location {pfad}")
            if w != ";":
                aktuell.append(w)
                continue
            if not aktuell:
                raise Abgelehnt(f"empty directive in location {pfad}")
            name = aktuell[0]
            if name not in ANWEISUNGEN or not ANWEISUNGEN[name](aktuell):
                raise Abgelehnt(f"directive not allowed in location {pfad}: {' '.join(aktuell)[:60]!r}")
            if name in gesehen:
                raise Abgelehnt(f"directive {name} more than once in location {pfad}")
            gesehen.add(name)
            aktuell = []
        if "include" not in gesehen:
            raise Abgelehnt(f"location {pfad} does not include {INCLUDE}")
        bloecke += 1
    if not bloecke:
        raise Abgelehnt("no location block")
    return bloecke


def lies_installiert(pfad):
    """Installierte Datei selbst lesen: kein Symlink, reguläre Datei, bei Root-Aufruf im Besitz von root."""
    try:
        fd = os.open(pfad, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)   # folgt keinem Symlink
    except OSError:
        raise Abgelehnt(f"installed {os.path.basename(pfad)} missing or not a plain file (not set up automatically)")
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            raise Abgelehnt(f"installed {os.path.basename(pfad)} is not a regular file")
        if os.geteuid() == 0 and st.st_uid != 0:
            raise Abgelehnt(f"installed {os.path.basename(pfad)} does not belong to root")
        teile, rest = [], MAX_BYTES + 1
        while rest > 0:
            stueck = os.read(fd, rest)
            if not stueck:
                break
            teile.append(stueck)
            rest -= len(stueck)
        if rest <= 0:
            # nie gekürzt sichern oder vergleichen
            raise Abgelehnt(f"installed {os.path.basename(pfad)} is larger than {MAX_BYTES} bytes")
        return b"".join(teile)
    except OSError as e:
        raise Abgelehnt(f"installed file cannot be read: {e}")
    finally:
        os.close(fd)


def sichern(daten, sicherung):
    """Sicherung des Installierten im Root-Ordner (0700); es bleiben die letzten BEHALTEN. Gibt den Pfad zurück."""
    try:
        if not os.path.lexists(sicherung):
            os.mkdir(sicherung, 0o700)
        dfd = os.open(sicherung, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    except OSError as e:
        raise Abgelehnt(f"backup folder {sicherung} cannot be used: {e}")
    try:
        st = os.fstat(dfd)
        if not stat.S_ISDIR(st.st_mode) or (os.geteuid() == 0 and st.st_uid != 0):
            raise Abgelehnt(f"backup folder {sicherung} is not a folder of root")
        os.fchmod(dfd, 0o700)
        name = f"{NAME}.{time.strftime('%Y%m%dT%H%M%S')}.{time.time_ns() % 10**9:09d}"
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=dfd)
        try:
            geschrieben = 0
            while geschrieben < len(daten):
                geschrieben += os.write(fd, daten[geschrieben:])
            os.fsync(fd)
        finally:
            os.close(fd)
        alte = sorted(n for n in os.listdir(dfd) if n.startswith(NAME + ".") and re.fullmatch(r"[0-9T.]+", n[len(NAME) + 1:]))
        for n in alte[:-BEHALTEN]:
            os.unlink(n, dir_fd=dfd)
        return os.path.join(sicherung, name)
    except OSError as e:
        raise Abgelehnt(f"backup in {sicherung} failed: {e}")
    finally:
        os.close(dfd)


def ersetzen(daten, snippets, ziel):
    """Atomar ersetzen: temporäre Datei im Snippets-Ordner (Name ohne .conf/.inc, kein Stern-Include bindet sie ein), fsync,
    0640 root:root, os.replace. Bei jedem Fehler bleibt keine temporäre Datei zurück; der Fehler geht an den Aufrufer."""
    fd, tmp = tempfile.mkstemp(dir=snippets, prefix=".nginx-orte-installieren-", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(daten)
            f.flush()
            os.fsync(f.fileno())
            os.fchmod(f.fileno(), 0o640)
            if os.geteuid() == 0:
                os.fchown(f.fileno(), 0, 0)
        os.replace(tmp, ziel)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _lauf(args, was):
    try:
        r = subprocess.run(args, env=dict(UMGEBUNG), stdin=subprocess.DEVNULL, capture_output=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as e:
        print(f"{was} could not run: {e}", file=sys.stderr)
        return False
    if r.returncode != 0:
        aus = (r.stderr or r.stdout or b"").decode("utf-8", "replace").strip()
        print(f"{was} failed (exit {r.returncode}): {aus[:600]}", file=sys.stderr)
        return False
    return True


def nginx_testen():
    return _lauf([NGINX, "-t"], "nginx -t")


def nginx_neu_laden():
    return _lauf([SYSTEMCTL, "reload", "nginx"], "systemctl reload nginx")


def installieren(neu, snippets=SNIPPETS, sicherung=SICHERUNG, sperre=SPERRE, nginx=NGINX, testen=None, neu_laden=None):
    """Orte-Datei prüfen und ersetzen. 0 installiert, 2 nichts zu tun, 4, 5 oder 6 wie oben; Abgelehnt bei Ausgang 3."""
    testen = testen or nginx_testen
    neu_laden = neu_laden or nginx_neu_laden
    if len(neu) > MAX_BYTES:
        raise Abgelehnt("input too large")
    try:
        sfd = os.open(sperre, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    except OSError as e:
        raise Abgelehnt(f"lock {sperre} cannot be opened: {e}")
    try:
        try:
            fcntl.flock(sfd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise Abgelehnt("busy: another run holds the lock")
        pruefe(neu)
        ziel = os.path.join(snippets, NAME)
        alt = lies_installiert(ziel)
        if neu == alt:
            return 2
        if not os.path.exists(nginx):
            raise Abgelehnt(f"{nginx} is missing")
        gesichert = sichern(alt, sicherung)
        ERSETZEN_BEGONNEN.append(True)
        try:
            ersetzen(neu, snippets, ziel)
        except OSError as e:
            raise Abgelehnt(f"replacing {NAME} failed, installed file unchanged: {e}")
        if not testen():
            try:
                ersetzen(alt, snippets, ziel)
            except OSError as e:
                print(f"rollback failed: {e}; the untested new {NAME} is in place, backup in {gesichert}; not reloaded",
                      file=sys.stderr)
                return 6
            if not testen():
                print(f"rollback untested: nginx -t fails with the previous {NAME} as well (backup in {gesichert}); not reloaded",
                      file=sys.stderr)
                return 6
            print(f"nginx -t failed with the new {NAME}; the previous file is restored, not reloaded", file=sys.stderr)
            return 4
        if not neu_laden():
            print(f"reload failed; the new {NAME} is installed and tested (nginx -t passed)", file=sys.stderr)
            return 5
        return 0
    finally:
        os.close(sfd)      # gibt die Sperre frei


def main(argv, daten=None, **kw):
    if len(argv) != 1:
        print("usage: no arguments (new file on stdin)", file=sys.stderr)
        return 3
    ERSETZEN_BEGONNEN.clear()
    try:
        if daten is None:
            daten = sys.stdin.buffer.read(MAX_BYTES + 1)
        rc = installieren(daten, **kw)
    except Abgelehnt as e:
        print(f"rejected: {e}", file=sys.stderr)
        return 3
    except Exception as e:      # kein Traceback
        if not ERSETZEN_BEGONNEN:
            print(f"rejected: unexpected error before any change: {type(e).__name__}: {e}", file=sys.stderr)
            return 3
        print(f"unexpected error after replacing began, state not secured: {type(e).__name__}: {e}", file=sys.stderr)
        return 6
    if rc == 0:
        print(NAME)
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
