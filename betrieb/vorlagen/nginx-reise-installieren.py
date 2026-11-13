#!/usr/bin/python3 -I
"""Legt den nginx-Baustein einer Reise an, erneuert, nennt oder entfernt ihn (#552). Läuft mit Root-Rechten.

Aufruf:  sudo -n <instanz>-nginx-reise-installieren               Baustein anlegen oder erneuern (Reisename auf stdin)
         sudo -n <instanz>-nginx-reise-installieren --pfad        nur den Pfad des vorhandenen Bausteins nennen (Lesemodus)
         sudo -n <instanz>-nginx-reise-installieren --entfernen   Baustein entfernen

Diese Datei gehört auf dem Server root und liegt außerhalb des Repos (/usr/local/sbin); die Software kann sie nicht ändern.
Sie wird aus betrieb/vorlagen/nginx-reise-installieren.py von einrichten.sh erzeugt: Instanz, Snippets-Ordner, Seitenordner, Port
des Rückmeldedienstes, Zone und die Vorlage des Bausteins (vorlagen/nginx-reise.conf) sind eingebacken; nichts davon kommt aus
dem Repo, der Umgebung oder der Eingabe. Nur Standardbibliothek, Start mit -I (kein Import aus dem Arbeitsordner, keine
PYTHON-Umgebung). Muster: nginx-orte-installieren.py (#445).

Eingabe: auf stdin genau ein Reisename (MUSTER, höchstens ein Zeilenende dahinter), keine Argumente außer --pfad oder --entfernen.
Den geheimen Teil des Links (Token) erzeugt das Programm selbst; ein vorhandener Baustein behält seinen Pfad, auch einen von Hand
angelegten, der nicht mit dem Namen der Reise beginnt. Den Baustein liest es selbst (kein Symlink, reguläre Datei, root).

Ablauf beim Anlegen und Entfernen: Sperre, Installiertes lesen, gleich? (2), Sicherung im Root-Ordner SICHERUNG (je Baustein die
letzten 20), atomar ersetzen (0640 root:<Gruppe des Dienstbenutzers>) bzw. entfernen, nginx -t (scheitert er: alter Stand zurück, erneut nginx -t),
systemctl reload nginx.

Ausgang: 0 angelegt, erneuert oder entfernt und geladen, 2 nichts zu tun (Lesemodus: kein Baustein da), 3 abgelehnt oder vor dem
Ersetzen gescheitert, 4 nginx -t scheiterte, alter Stand zurück, 5 Reload scheiterte (Baustein installiert und getestet),
6 Rückweg nicht gesichert (zweites nginx -t oder Zurückschreiben gescheitert), jeweils ohne Reload. Auf stdout steht nur der Pfad
(erstes Glied des Links, „<reise>-<token>“) bei 0 und 2 des Anlegens und im Lesemodus, nie der Inhalt des Bausteins; Grund auf stderr.
"""
import fcntl
import grp
import os
import re
import secrets
import stat
import subprocess
import sys
import tempfile
import time

INSTANZ = "__INSTANZ__"
SNIPPETS = "__SNIPPETS__"
# Gruppe des Dienstbenutzers (#552): Bausteine 0640 root:GRUPPE, damit nginx.py pruefen ohne sudo liest; eingebacken
GRUPPE = "__GRUPPE__"
SEITEN = "__SEITEN__"
RM_PORT = "__RM_PORT__"
ZONE = "__ZONE__"
# Vorlage des Bausteins (vorlagen/nginx-reise.conf mit den Werten der Instanz); @PFAD@, @TOKEN@ und @REISE@ setzt das Programm
VORLAGE = __VORLAGE__
SICHERUNG = "/var/lib/" + INSTANZ + "-nginx-sicherung"
SPERRE = "/var/lib/" + INSTANZ + "-nginx-reise-installieren.sperre"
NGINX = "/usr/sbin/nginx"
SYSTEMCTL = "/usr/bin/systemctl"
UMGEBUNG = {"PATH": "/usr/sbin:/usr/bin:/sbin:/bin"}
MUSTER = re.compile(r"[a-z0-9][a-z0-9-]{1,39}\Z")
MAX_BYTES = 64 * 1024
BEHALTEN = 20
MODI = ("--pfad", "--entfernen")
# Pfad im ersten location-Block eines Bausteins (wie bisher freischalten.sh)
PFAD_IM_BAUSTEIN = re.compile(r"^location \^~ /([^/\s]+)/ \{", re.M)


class Abgelehnt(Exception):
    pass


# Ob in diesem Lauf das Ersetzen schon begonnen hat: Ein unerwarteter Fehler davor endet mit 3, danach mit 6.
ERSETZEN_BEGONNEN = []


def reise_lesen(daten):
    """Den Reisenamen aus der Eingabe prüfen (höchstens ein Zeilenende dahinter); Abgelehnt bei jedem Verstoß."""
    if daten is None or len(daten) > 64:
        raise Abgelehnt("input missing or too long")
    if daten.endswith(b"\n"):
        daten = daten[:-1]
    try:
        reise = daten.decode("ascii")
    except UnicodeDecodeError:
        raise Abgelehnt("trip name: lowercase letters, digits and hyphen only")
    if not MUSTER.match(reise):
        raise Abgelehnt("trip name: lowercase letters, digits and hyphen only, 2 to 40 characters")
    return reise


def name(reise):
    return f"{INSTANZ}-{reise}.conf"


def rendern(pfad, reise):
    """Baustein aus der Vorlage; der Pfad wird als Ganzes eingesetzt (von Hand angelegte Bausteine behalten ihren Link)."""
    return VORLAGE.replace("@PFAD@", pfad).replace("@TOKEN@", pfad.rsplit("-", 1)[-1]).replace("@REISE@", reise).encode("utf-8")


def pfad_aus(daten, ziel):
    treffer = PFAD_IM_BAUSTEIN.search(daten.decode("utf-8", "replace"))
    if not treffer:
        raise Abgelehnt(f"no path in the block {os.path.basename(ziel)} (location ^~ /<reise>-<token>/ is missing)")
    return treffer.group(1)


def lies_installiert(pfad):
    """Installierten Baustein selbst lesen -> Inhalt oder None, wenn es ihn nicht gibt. Kein Symlink, reguläre Datei, bei
    Root-Aufruf im Besitz von root."""
    try:
        fd = os.open(pfad, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)   # folgt keinem Symlink
    except FileNotFoundError:
        return None
    except OSError:
        raise Abgelehnt(f"installed {os.path.basename(pfad)} is not a plain file")
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
            raise Abgelehnt(f"installed {os.path.basename(pfad)} is larger than {MAX_BYTES} bytes")
        return b"".join(teile)
    except OSError as e:
        raise Abgelehnt(f"installed block cannot be read: {e}")
    finally:
        os.close(fd)


def sichern(daten, sicherung, datei):
    """Sicherung des Installierten im Root-Ordner (0700); je Baustein bleiben die letzten BEHALTEN. Gibt den Pfad zurück."""
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
        jetzt = time.time_ns()
        neu = f"{datei}.{time.strftime('%Y%m%dT%H%M%S', time.localtime(jetzt // 10**9))}.{jetzt % 10**9:09d}"
        fd = os.open(neu, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=dfd)
        try:
            geschrieben = 0
            while geschrieben < len(daten):
                geschrieben += os.write(fd, daten[geschrieben:])
            os.fsync(fd)
        finally:
            os.close(fd)
        alte = sorted(n for n in os.listdir(dfd) if n.startswith(datei + ".") and re.fullmatch(r"[0-9T.]+", n[len(datei) + 1:]))
        for n in alte[:-BEHALTEN]:
            os.unlink(n, dir_fd=dfd)
        return os.path.join(sicherung, neu)
    except OSError as e:
        raise Abgelehnt(f"backup in {sicherung} failed: {e}")
    finally:
        os.close(dfd)


def gruppe_gid():
    """Kennung der eingebackenen Gruppe; fehlt sie auf dem Server, wird nichts installiert."""
    try:
        return grp.getgrnam(GRUPPE).gr_gid
    except (KeyError, TypeError, AttributeError):
        raise Abgelehnt(f"group {GRUPPE!r} does not exist (einrichten.sh, FR_GRUPPE)")


def ersetzen(daten, snippets, ziel):
    """Atomar ersetzen: temporäre Datei im Snippets-Ordner (Name ohne .conf, kein Stern-Include bindet sie ein), fsync,
    0640 root:GRUPPE (#552), os.replace. Bei jedem Fehler bleibt keine temporäre Datei zurück; der Fehler geht an den Aufrufer."""
    fd, tmp = tempfile.mkstemp(dir=snippets, prefix=".nginx-reise-installieren-", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(daten)
            f.flush()
            os.fsync(f.fileno())
            os.fchmod(f.fileno(), 0o640)
            if os.geteuid() == 0:
                os.fchown(f.fileno(), 0, gruppe_gid())
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


def _sperre(sperre):
    try:
        sfd = os.open(sperre, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    except OSError as e:
        raise Abgelehnt(f"lock {sperre} cannot be opened: {e}")
    try:
        fcntl.flock(sfd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        os.close(sfd)
        raise Abgelehnt("busy: another run holds the lock")
    return sfd


def _wechseln(neu, alt, snippets, ziel, sicherung, testen, neu_laden):
    """Neuen Stand (None: entfernen) an die Stelle von alt (None: gab es nicht), prüfen, laden. -> 0, 4, 5 oder 6."""
    datei = os.path.basename(ziel)
    if os.geteuid() == 0:
        gruppe_gid()     # vor jeder Änderung: gibt es die Gruppe?
    gesichert = sichern(alt, sicherung, datei) if alt is not None else None
    ERSETZEN_BEGONNEN.append(True)
    try:
        if neu is None:
            os.unlink(ziel)
        else:
            ersetzen(neu, snippets, ziel)
    except OSError as e:
        raise Abgelehnt(f"changing {datei} failed, installed state unchanged: {e}")
    if not testen():
        try:
            if alt is None:
                os.unlink(ziel)
            else:
                ersetzen(alt, snippets, ziel)
        except OSError as e:
            print(f"rollback failed: {e}; the untested state of {datei} is in place"
                  f"{f', backup in {gesichert}' if gesichert else ''}; not reloaded", file=sys.stderr)
            return 6
        if not testen():
            print(f"rollback untested: nginx -t fails with the previous state of {datei} as well"
                  f"{f' (backup in {gesichert})' if gesichert else ''}; not reloaded", file=sys.stderr)
            return 6
        print(f"nginx -t failed with the new state of {datei}; the previous state is restored, not reloaded", file=sys.stderr)
        return 4
    if not neu_laden():
        print(f"reload failed; the new state of {datei} is in place and tested (nginx -t passed)", file=sys.stderr)
        return 5
    return 0


def installieren(reise, snippets=SNIPPETS, sicherung=SICHERUNG, sperre=SPERRE, nginx=NGINX, testen=None, neu_laden=None):
    """Baustein der Reise anlegen oder erneuern. -> (Ausgang, Pfad): 0, 2, 4, 5 oder 6; Abgelehnt bei Ausgang 3."""
    sfd = _sperre(sperre)
    try:
        ziel = os.path.join(snippets, name(reise))
        alt = lies_installiert(ziel)
        pfad = pfad_aus(alt, ziel) if alt is not None else f"{reise}-{secrets.token_hex(12)}"
        neu = rendern(pfad, reise)
        if neu == alt:
            return 2, pfad
        if not os.path.exists(nginx):
            raise Abgelehnt(f"{nginx} is missing")
        rc = _wechseln(neu, alt, snippets, ziel, sicherung, testen or nginx_testen, neu_laden or nginx_neu_laden)
        if rc == 0:
            print("block created" if alt is None else "block renewed", file=sys.stderr)
        return rc, pfad
    finally:
        os.close(sfd)      # gibt die Sperre frei


def pfad_lesen(reise, snippets=SNIPPETS):
    """Lesemodus: Pfad des vorhandenen Bausteins oder None; nie der Inhalt."""
    ziel = os.path.join(snippets, name(reise))
    alt = lies_installiert(ziel)
    return None if alt is None else pfad_aus(alt, ziel)


def entfernen(reise, snippets=SNIPPETS, sicherung=SICHERUNG, sperre=SPERRE, nginx=NGINX, testen=None, neu_laden=None):
    """Baustein der Reise entfernen (mit Sicherung, nginx -t und Rückweg). -> 0, 2, 4, 5 oder 6; Abgelehnt bei Ausgang 3."""
    sfd = _sperre(sperre)
    try:
        ziel = os.path.join(snippets, name(reise))
        alt = lies_installiert(ziel)
        if alt is None:
            return 2
        if not os.path.exists(nginx):
            raise Abgelehnt(f"{nginx} is missing")
        return _wechseln(None, alt, snippets, ziel, sicherung, testen or nginx_testen, neu_laden or nginx_neu_laden)
    finally:
        os.close(sfd)


def main(argv, daten=None, **kw):
    if len(argv) > 2 or (len(argv) == 2 and argv[1] not in MODI):
        print("usage: no arguments, --pfad or --entfernen (trip name on stdin)", file=sys.stderr)
        return 3
    modus = argv[1] if len(argv) == 2 else None
    ERSETZEN_BEGONNEN.clear()
    try:
        if daten is None:
            daten = sys.stdin.buffer.read(65)
        reise = reise_lesen(daten)
        if modus == "--pfad":
            pfad = pfad_lesen(reise, snippets=kw.get("snippets", SNIPPETS))
            if pfad is None:
                return 2
            print(pfad)
            return 0
        if modus == "--entfernen":
            return entfernen(reise, **kw)
        rc, pfad = installieren(reise, **kw)
    except Abgelehnt as e:
        print(f"rejected: {e}", file=sys.stderr)
        return 3
    except Exception as e:      # kein Traceback
        if not ERSETZEN_BEGONNEN:
            print(f"rejected: unexpected error before any change: {type(e).__name__}: {e}", file=sys.stderr)
            return 3
        print(f"unexpected error after changing began, state not secured: {type(e).__name__}: {e}", file=sys.stderr)
        return 6
    if rc in (0, 2):
        print(pfad)
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
