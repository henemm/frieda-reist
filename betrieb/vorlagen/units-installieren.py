#!/usr/bin/python3 -I
"""Installiert ungefährliche Änderungen einer systemd-Einheit der Instanz (#260, Option B). Läuft mit Root-Rechten.

Aufruf:  sudo -n <instanz>-units-installieren <einheit>   (die neue Einheitendatei kommt auf stdin)

Diese Datei gehört auf dem Server root und liegt außerhalb des Repos (/usr/local/sbin); die Software kann sie nicht ändern.
Sie wird aus betrieb/vorlagen/units-installieren.py von einrichten.sh erzeugt (Instanz und Benutzer eingesetzt) und einmal
bewusst installiert (docs/betrieb.md). Nur Standardbibliothek, Start mit -I (kein Import aus dem Arbeitsordner, keine
PYTHON-Umgebung). Sie traut dem Aufrufer nichts: Sie liest die installierte Datei selbst, rechnet selbst und lässt sich weder
durch Umgebung noch durch Argumente auf andere Pfade oder Programme lenken (SYSTEMD und SYSTEMCTL sind fest).

Ausgang: 0 installiert (auf stdout nur der Name der Einheit), 2 nichts zu tun, 3 abgelehnt (Grund auf stderr).

Installiert wird nur, wenn sich neue und installierte Datei höchstens in den Zeilen der Erlaubnisliste ERLAUBT unterscheiden.
Alles andere (User, ExecStart, Rechte, Reihenfolge, Abschnitte, Drop-ins, Timer, fremde Einheiten) lehnt sie ab.
"""
import os
import re
import stat
import subprocess
import sys
import tempfile

INSTANZ = "__INSTANZ__"
BENUTZER = "__BENUTZER__"
SYSTEMD = "/etc/systemd/system"
SYSTEMCTL = "/usr/bin/systemctl"
MAX_BYTES = 64 * 1024
ARTEN = ("konnektor", "push", "rueckmeldungen", "schreiben", "veroeffentlichen", "waechter")

# Erlaubnisliste (gleich der in betrieb/units.py, ein Test prüft das): (Abschnitt, Schlüssel) -> Muster für den Wert. Bei
# Environment ist der Schlüssel "Environment:<NAME>" und das Muster gilt für den Wert nach "NAME=". Ein neuer Eintrag ist eine
# Sicherheitsentscheidung des Product Owners (docs/betrieb.md, Einheiten abgleichen).
ERLAUBT = {
    ("Service", "Environment:FR_DIENST"): re.compile(r"^/(?!.*(?:^|/)\.\.?(?:/|$))[A-Za-z0-9_./-]+$"),
    ("Service", "Environment:FR_ZEITZONE"): re.compile(r"^[A-Za-z][A-Za-z0-9_+/-]*$"),
    ("Service", "TimeoutStartSec"): re.compile(r"^[1-9][0-9]{0,4}(?:s|min|h)?$"),
}
ABSCHNITT = re.compile(r"^\[([A-Za-z]+)\]$")
SCHLUESSEL = re.compile(r"^[A-Za-z0-9]+$")


class Abgelehnt(Exception):
    pass


def lies(daten):
    """Einheit als Liste (Abschnitt, Schlüssel, Wert) streng einlesen; Kommentare und Leerzeilen entfallen."""
    if len(daten) > MAX_BYTES:
        raise Abgelehnt("input too large")
    try:
        text = daten.decode("utf-8")
    except UnicodeDecodeError:
        raise Abgelehnt("not valid UTF-8")
    if any((ord(c) < 32 and c not in "\n\t") or ord(c) == 127 for c in text):
        raise Abgelehnt("control characters")
    erg, abschnitt = [], ""
    # Nur die Leerzeichen, die auch systemd kennt (Leerzeichen und Tab): Pythons strip() entfernte auch Unicode-Leerraum
    # (U+00A0, U+2003, U+0085 ...) und ließ so eine Zeile "<NBSP>User=hans" für uns wie User= aussehen, für systemd aber wie
    # einen unbekannten, ignorierten Schlüssel. Zeilen werden nur an "\n" getrennt, wie bei systemd.
    for zeile in text.split("\n"):
        if zeile.rstrip(" \t").endswith("\\"):
            raise Abgelehnt("line continuation")
        z = zeile.strip(" \t")
        if not z or z[0] in "#;":
            continue
        m = ABSCHNITT.match(z)
        if m:
            abschnitt = m.group(1)
            erg.append((abschnitt, "", ""))   # Abschnittswechsel gehört zur Reihenfolge
            continue
        schluessel, gleich, wert = z.partition("=")
        schluessel = schluessel.strip(" \t")
        if not gleich or not SCHLUESSEL.match(schluessel):
            raise Abgelehnt(f"unknown line form: {z[:40]!r}")
        erg.append((abschnitt, schluessel, wert.strip(" \t")))
    return erg


def erlaubter_schluessel(z):
    """Schlüssel der Erlaubnisliste, zu dem die Zeile gehört (unabhängig vom Wert), sonst None."""
    abschnitt, schluessel, wert = z
    if schluessel == "Environment":
        schluessel = "Environment:" + wert.partition("=")[0]
    return schluessel if (abschnitt, schluessel) in ERLAUBT else None


def wert_von(z):
    return z[2].partition("=")[2] if z[1] == "Environment" else z[2]


def pruefe_neu(zeilen_neu):
    """Erlaubte Zeilen der neuen Datei: Wertmuster, höchstens einmal je Schlüssel; genau ein User= mit dem Benutzer."""
    gesehen = set()
    for z in zeilen_neu:
        k = erlaubter_schluessel(z)
        if k is None:
            continue
        if k in gesehen:
            raise Abgelehnt(f"{k} more than once")
        gesehen.add(k)
        if not ERLAUBT[(z[0], k)].match(wert_von(z)):
            raise Abgelehnt(f"value of {k} not allowed")


def pruefe_ohne_zuruecksetzen(zeilen_, was):
    """Ein leeres Environment= setzt die Liste zurück: Es würde erlaubte Zeilen davor unwirksam machen."""
    if any(z[1] == "Environment" and not z[2] for z in zeilen_):
        raise Abgelehnt(f"{was}: empty Environment= resets the list")


def pruefe_benutzer(zeilen_, was):
    users = [z for z in zeilen_ if z[1] == "User"]
    if len(users) != 1 or users[0][0] != "Service" or users[0][2] != BENUTZER:
        raise Abgelehnt(f"{was}: User= is not {BENUTZER}")


def rest(zeilen_):
    """Alle Zeilen außerhalb der Erlaubnisliste in Reihenfolge, mit den Abschnittswechseln."""
    return [z for z in zeilen_ if erlaubter_schluessel(z) is None]


def neu_laden():
    subprocess.run([SYSTEMCTL, "daemon-reload"], check=True, env={"PATH": "/usr/bin:/bin"}, stdin=subprocess.DEVNULL)


def installieren(einheit, neu, systemd=SYSTEMD, instanz=INSTANZ, neu_laden=neu_laden):
    """Einheit prüfen und ersetzen. 0 installiert, 2 nichts zu tun; Abgelehnt bei allem anderen."""
    if not re.fullmatch(re.escape(instanz) + r"-(?:" + "|".join(ARTEN) + r")\.service", einheit or ""):
        raise Abgelehnt("unit not allowed")
    pfad = os.path.join(systemd, einheit)
    if os.path.lexists(pfad + ".d"):
        raise Abgelehnt("drop-in folder exists")
    try:
        fd_alt = os.open(pfad, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)   # folgt keinem Symlink
    except OSError:
        raise Abgelehnt("installed unit missing or not a plain file")
    with os.fdopen(fd_alt, "rb") as f:
        st = os.fstat(f.fileno())
        if not stat.S_ISREG(st.st_mode):
            raise Abgelehnt("installed unit is not a regular file")
        if os.geteuid() == 0 and st.st_uid != 0:
            raise Abgelehnt("installed unit does not belong to root")
        alt_daten = f.read(MAX_BYTES + 1)
    alt, neu_z = lies(alt_daten), lies(neu)
    pruefe_benutzer(alt, "installed")
    pruefe_benutzer(neu_z, "new")
    pruefe_ohne_zuruecksetzen(alt, "installed")
    pruefe_ohne_zuruecksetzen(neu_z, "new")
    pruefe_neu(neu_z)
    if rest(alt) != rest(neu_z):
        raise Abgelehnt("lines outside the allowed list differ")
    if neu == alt_daten:
        return 2
    fd, tmp = tempfile.mkstemp(dir=systemd, prefix=".units-installieren-")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(neu)
            f.flush()
            os.fsync(f.fileno())
            os.fchmod(f.fileno(), 0o644)
            if os.geteuid() == 0:
                os.fchown(f.fileno(), 0, 0)
        os.replace(tmp, pfad)
    except BaseException:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise
    neu_laden()
    return 0


def main(argv, daten=None, systemd=SYSTEMD, neu_laden=neu_laden):
    if len(argv) != 2:
        print("usage: <unit> (new unit on stdin)", file=sys.stderr)
        return 3
    if daten is None:
        daten = sys.stdin.buffer.read(MAX_BYTES + 1)
    try:
        rc = installieren(argv[1], daten, systemd=systemd, neu_laden=neu_laden)
    except Abgelehnt as e:
        print(f"rejected: {e}", file=sys.stderr)
        return 3
    if rc == 0:
        print(argv[1])
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
