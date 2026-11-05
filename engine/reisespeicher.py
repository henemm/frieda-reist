"""Reisespeicher (Stufe 1, #346, Epic #345, ADR-0008): Reisedaten als unveränderliche Versionen in SQLite, nur anhängen.

Ein Vorgang ist ein Schreibvorgang (Person, Rolle, Werkzeug, Titel, Grund, Zeit, Kennung); je Vorgang gibt es eine
Version je geänderter Datei (Bytes und SHA-256, ein Tombstone ohne Inhalt für eine gelöschte Datei). Die Stand-Nummer
einer Reise zählt Vorgänge, nicht Dateien (je Schreibvorgang +1, #226). Der Stand s einer Reise ist je Pfad die jüngste
Version unter den Vorgängen mit stand <= s; ein Tombstone heißt: die Datei fehlt in diesem Stand.

Nur anhängen: Trigger verweigern UPDATE und DELETE auf beiden Tabellen (mit recursive_triggers, sonst löschte
INSERT OR REPLACE an ihnen vorbei), der Authorizer der Verbindung aus db() verweigert dazu UPDATE, DELETE, DROP,
ALTER TABLE und PRAGMA writable_schema. Das schützt vor Software-Fehlern und Fehlbedienung, nicht vor jemandem mit
Schreibzugriff auf die Datei; dagegen helfen `pruefen` und die Sicherung außer Haus (ADR-0008).

In Stufe 1 schreibt der Schreibweg nicht hierher; die Datenbank beschreiben nur die Befehle unten. Der Schreibweg
(engine/schreiben.py) nutzt die Funktionen ab Stufe 2 (#347).

Ablage: <FR_SPEICHER, sonst <Seiten>/_speicher>/reisen.db (SQLite, WAL), nur für den Betreiber lesbar;
Schnappschuss unter <Speicher>/sicherung/reisen.db.

Aufrufe:
  python3 engine/reisespeicher.py importieren <ordner> <reise> <wer> [--grund TEXT] [--ab N]   Reiseordner als Vorgang
  python3 engine/reisespeicher.py exportieren <reise> <ziel> [--bis N]       Stand in einen leeren Ordner schreiben
  python3 engine/reisespeicher.py verlauf <reise> [n]                        Vorgänge, neueste zuerst
  python3 engine/reisespeicher.py zuruecksetzen <reise> <bis> <wer> <grund>  neuer Vorgang mit dem Inhalt von Stand <bis>
  python3 engine/reisespeicher.py pruefen [reise]                            Prüfsummen und Stand-Folge nachrechnen
  python3 engine/reisespeicher.py sichern                                    sauberer Schnappschuss nach <Speicher>/sicherung/
"""
import collections
import hashlib
import os
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

import instanz
from stand import zeit_iso

Vorgang = collections.namedtuple("Vorgang", "nummer stand")


class VorgangVorhanden(Exception):
    """Die Kennung ist schon eingetragen: Es wurde nichts geschrieben, die Wiederholung ist ungefährlich."""

    def __init__(self, nummer, stand):
        self.nummer, self.stand = nummer, stand
        super().__init__(f"operation already recorded: {nummer} (stand {stand})")


SCHEMA = """
CREATE TABLE IF NOT EXISTS vorgaenge (
  nummer INTEGER PRIMARY KEY AUTOINCREMENT, reise TEXT NOT NULL, stand INTEGER NOT NULL, wann TEXT NOT NULL,
  wer TEXT NOT NULL, rolle TEXT NOT NULL DEFAULT '', werkzeug TEXT NOT NULL, titel TEXT NOT NULL,
  grund TEXT NOT NULL DEFAULT '', kennung TEXT UNIQUE, herkunft TEXT NOT NULL DEFAULT '',
  UNIQUE (reise, stand), UNIQUE (nummer, reise));
CREATE TABLE IF NOT EXISTS versionen (
  vorgang INTEGER NOT NULL, reise TEXT NOT NULL, pfad TEXT NOT NULL, inhalt BLOB, pruefsumme TEXT,
  PRIMARY KEY (vorgang, pfad), FOREIGN KEY (vorgang, reise) REFERENCES vorgaenge (nummer, reise));
CREATE INDEX IF NOT EXISTS versionen_pfad ON versionen (reise, pfad, vorgang);
CREATE TRIGGER IF NOT EXISTS vorgaenge_kein_update BEFORE UPDATE ON vorgaenge
  BEGIN SELECT RAISE(ABORT, 'append only: vorgaenge'); END;
CREATE TRIGGER IF NOT EXISTS vorgaenge_kein_delete BEFORE DELETE ON vorgaenge
  BEGIN SELECT RAISE(ABORT, 'append only: vorgaenge'); END;
CREATE TRIGGER IF NOT EXISTS versionen_kein_update BEFORE UPDATE ON versionen
  BEGIN SELECT RAISE(ABORT, 'append only: versionen'); END;
CREATE TRIGGER IF NOT EXISTS versionen_kein_delete BEFORE DELETE ON versionen
  BEGIN SELECT RAISE(ABORT, 'append only: versionen'); END;
"""
TABELLEN = ("vorgaenge", "versionen")
VERBOTEN = {sqlite3.SQLITE_DROP_TABLE, sqlite3.SQLITE_DROP_TEMP_TABLE, sqlite3.SQLITE_DROP_TRIGGER,
            sqlite3.SQLITE_DROP_TEMP_TRIGGER, sqlite3.SQLITE_DROP_INDEX, sqlite3.SQLITE_DROP_TEMP_INDEX,
            sqlite3.SQLITE_DROP_VIEW, sqlite3.SQLITE_DROP_TEMP_VIEW, sqlite3.SQLITE_ALTER_TABLE,
            sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH}   # ATTACH: dieselbe Datei ein zweites Mal ohne Schutz


def pfad():
    return instanz.speicher() / "reisen.db"


def _waechter(aktion, a1, a2, datenbank, ausloeser):
    """Authorizer: nur anhängen (zweite Schicht neben den Triggern)."""
    if aktion in (sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE) and a1 in TABELLEN:
        return sqlite3.SQLITE_DENY
    if aktion in VERBOTEN:
        return sqlite3.SQLITE_DENY
    if aktion == sqlite3.SQLITE_PRAGMA and (a2 is not None or (a1 or "").lower() == "writable_schema"):
        return sqlite3.SQLITE_DENY   # nur lesende PRAGMAs ohne Wert; db() setzt seine vor dem Authorizer
    return sqlite3.SQLITE_OK


def db():
    """Verbindung zum Reisespeicher; legt ihn beim ersten Mal an (Ordner 700, Datei 600, WAL). Schema und Trigger
    entstehen vor dem Authorizer (executescript committet selbst), danach ist nur noch Anhängen erlaubt."""
    p = pfad()
    neu = not p.exists()
    if neu:
        p.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(p.parent, 0o700)
    v = sqlite3.connect(p, timeout=10)
    v.row_factory = sqlite3.Row
    v.execute("PRAGMA foreign_keys = ON")
    v.execute("PRAGMA recursive_triggers = ON")
    if neu:
        os.chmod(p, 0o600)
        v.execute("PRAGMA journal_mode = WAL")
    v.executescript(SCHEMA)
    if v.execute("PRAGMA user_version").fetchone()[0] < 1:
        v.execute("PRAGMA user_version = 1")
    v.set_authorizer(_waechter)
    return v


def _pfad_pruefen(p):
    """Pfadregeln: POSIX, relativ, nicht leer, keine leeren Teile, kein '.', '..' oder '.git', kein NUL, kein Backslash."""
    if not isinstance(p, str) or not p or "\x00" in p or "\\" in p or p.startswith("/"):
        raise ValueError(f"invalid path: {p!r}")
    if any(t in ("", ".", "..", ".git") for t in p.split("/")):
        raise ValueError(f"invalid path: {p!r}")
    return p


def _kollision_pruefen(pfade):
    """Eine Datei darf nicht zugleich Ordner einer anderen sein (q und q/r): Der Export könnte sie nicht schreiben."""
    pfade = set(pfade)
    for p in pfade:
        teile = p.split("/")
        for i in range(1, len(teile)):
            if "/".join(teile[:i]) in pfade:
                raise ValueError(f"file and folder with the same name: {'/'.join(teile[:i])!r} and {p!r}")


def _summe(inhalt):
    return hashlib.sha256(inhalt).hexdigest()


def _stand(v, reise, bis=None, spalte="inhalt"):
    """Pfad -> Spalte (inhalt oder pruefsumme) im Stand bis (ohne: neuester); unbekannte Reise oder Stand: KeyError."""
    hoechster = v.execute("SELECT MAX(stand) FROM vorgaenge WHERE reise = ?", (reise,)).fetchone()[0]
    if hoechster is None:
        raise KeyError(reise)
    if bis is None:
        bis = hoechster
    elif not v.execute("SELECT 1 FROM vorgaenge WHERE reise = ? AND stand = ?", (reise, bis)).fetchone():
        raise KeyError(f"{reise}: stand {bis}")
    zeilen = v.execute(f"""
        SELECT pfad, {spalte} FROM (
          SELECT s.pfad, s.{spalte}, s.inhalt IS NULL AS weg,
                 ROW_NUMBER() OVER (PARTITION BY s.pfad ORDER BY s.vorgang DESC) AS rang
          FROM versionen s JOIN vorgaenge g ON g.nummer = s.vorgang
          WHERE g.reise = ? AND g.stand <= ?)
        WHERE rang = 1 AND NOT weg ORDER BY pfad""", (reise, bis))
    return {z[0]: z[1] for z in zeilen}


def _eintragen(v, reise, dateien, wer, werkzeug, titel, grund="", kennung=None, rolle="", wann=None, herkunft="",
               ab=0):
    """Ein Vorgang in der laufenden Transaktion von v (BEGIN IMMEDIATE beim Aufrufer)."""
    if kennung is not None:
        z = v.execute("SELECT nummer, stand FROM vorgaenge WHERE kennung = ?", (kennung,)).fetchone()
        if z:
            raise VorgangVorhanden(z[0], z[1])
    for p, inhalt in dateien.items():
        _pfad_pruefen(p)
        if inhalt is not None and not isinstance(inhalt, (bytes, bytearray, memoryview)):
            raise TypeError(f"content must be bytes or None: {p}")
    try:
        bisher = _stand(v, reise, spalte="pruefsumme")
    except KeyError:
        bisher = {}
    neu = {}
    for p, inhalt in dateien.items():
        if inhalt is None:
            if p in bisher:
                neu[p] = (None, None)
        else:
            inhalt = bytes(inhalt)
            summe = _summe(inhalt)
            if bisher.get(p) != summe:
                neu[p] = (inhalt, summe)
    if not neu:
        raise ValueError(f"{reise}: nothing changed")
    weg = {p for p, (inhalt, _) in neu.items() if inhalt is None}
    _kollision_pruefen((set(bisher) - weg) | (set(neu) - weg))
    hoechster = v.execute("SELECT MAX(stand) FROM vorgaenge WHERE reise = ?", (reise,)).fetchone()[0]
    stand = (ab if hoechster is None else hoechster) + 1
    nummer = v.execute(
        "INSERT INTO vorgaenge (reise, stand, wann, wer, rolle, werkzeug, titel, grund, kennung, herkunft) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (reise, stand, wann or zeit_iso(), wer, rolle, werkzeug, titel, grund, kennung, herkunft)).lastrowid
    v.executemany("INSERT INTO versionen (vorgang, reise, pfad, inhalt, pruefsumme) VALUES (?, ?, ?, ?, ?)",
                  [(nummer, reise, p, inhalt, summe) for p, (inhalt, summe) in sorted(neu.items())])
    return Vorgang(nummer, stand)


def _transaktion(arbeit):
    """arbeit(v) in einer Schreib-Transaktion (BEGIN IMMEDIATE); bei einem Fehler wird nichts geschrieben."""
    with closing(db()) as v:
        v.execute("BEGIN IMMEDIATE")
        try:
            ergebnis = arbeit(v)
        except BaseException:
            v.rollback()
            raise
        v.commit()
        return ergebnis


def vorgang_schreiben(reise, dateien, wer, werkzeug, titel, grund="", kennung=None, rolle="", wann=None, herkunft=""):
    """Ein Vorgang: dateien ist Pfad -> Bytes (None = löschen). Unveränderte Dateien werden übersprungen; bleibt nichts,
    ValueError. Bekannte Kennung: VorgangVorhanden. -> Vorgang(nummer, stand)."""
    return _transaktion(lambda v: _eintragen(v, reise, dateien, wer, werkzeug, titel, grund, kennung, rolle, wann,
                                             herkunft))


def stand_nummer(reise):
    """Höchste Stand-Nummer der Reise oder None, wenn sie unbekannt ist."""
    with closing(db()) as v:
        return v.execute("SELECT MAX(stand) FROM vorgaenge WHERE reise = ?", (reise,)).fetchone()[0]


def aktueller_stand(reise, bis=None):
    """Pfad -> Bytes der Reise im Stand bis (ohne: neuester); unbekannte Reise oder Stand: KeyError."""
    with closing(db()) as v:
        return {p: bytes(b) for p, b in _stand(v, reise, bis).items()}


def vorgang_eingetragen(kennung):
    """Vorgang mit dieser Kennung oder None (Nachprüfung nach einer Zeitüberschreitung)."""
    with closing(db()) as v:
        z = v.execute("SELECT nummer, stand FROM vorgaenge WHERE kennung = ?", (kennung,)).fetchone()
    return Vorgang(z[0], z[1]) if z else None


def verlauf(reise, n=None):
    """Vorgänge der Reise, neueste zuerst; nummer ist der Stand (wie stand.aenderungen), vorgang die Vorgangs-Nummer."""
    with closing(db()) as v:
        zeilen = v.execute("SELECT * FROM vorgaenge WHERE reise = ? ORDER BY stand DESC LIMIT ?",
                           (reise, -1 if n is None else int(n))).fetchall()
        return [{"nummer": z["stand"], "zeit": z["wann"], "was": z["titel"], "wer": z["wer"], "vorgang": z["nummer"],
                 "werkzeug": z["werkzeug"], "grund": z["grund"],
                 "dateien": [d[0] for d in v.execute("SELECT pfad FROM versionen WHERE vorgang = ? ORDER BY pfad",
                                                     (z["nummer"],))]}
                for z in zeilen]


def exportieren(reise, ziel, bis=None):
    """Schreibt den Stand in ziel (fehlt oder leerer Ordner, sonst FileExistsError). Alle Pfade werden vorher geprüft;
    ein Pfad, der aus dem Ziel führte, bricht mit ValueError ab, bevor etwas geschrieben ist."""
    dateien = aktueller_stand(reise, bis)
    ziel = Path(ziel)
    if ziel.is_symlink():
        raise ValueError(f"target is a symlink: {ziel}")
    if ziel.exists() and (not ziel.is_dir() or any(ziel.iterdir())):
        raise FileExistsError(str(ziel))
    basis = ziel.resolve()
    plan = []
    _kollision_pruefen(dateien)
    for p, inhalt in sorted(dateien.items()):
        _pfad_pruefen(p)
        aus = (basis / p).resolve()
        if basis not in aus.parents:
            raise ValueError(f"path leaves the target: {p!r}")
        plan.append((aus, inhalt))
    ziel.mkdir(parents=True, exist_ok=True)
    for aus, inhalt in plan:
        fehlend = [o for o in [aus.parent, *aus.parent.parents] if basis in o.parents and not o.exists()]
        aus.parent.mkdir(parents=True, exist_ok=True)
        for o in fehlend:
            os.chmod(o, 0o755)
        with open(aus, "xb") as f:
            f.write(inhalt)
        os.chmod(aus, 0o644)


def _ordner_lesen(ordner):
    """Pfad -> Bytes aller regulären Dateien (auch versteckte, ohne .git); ein Symlink oder Sonderdatei: ValueError."""
    ordner = Path(ordner)
    if ordner.is_symlink() or not ordner.is_dir():
        raise ValueError(f"not a folder: {ordner}")
    dateien = {}

    def lesen(o):
        with os.scandir(o) as eintraege:
            for e in eintraege:
                if e.name == ".git":
                    continue
                relativ = Path(e.path).relative_to(ordner).as_posix()
                if e.is_symlink():
                    raise ValueError(f"symlink not allowed: {relativ}")
                if e.is_dir(follow_symlinks=False):
                    lesen(e.path)
                elif e.is_file(follow_symlinks=False):
                    with open(e.path, "rb") as f:
                        dateien[_pfad_pruefen(relativ)] = f.read()
                else:
                    raise ValueError(f"not a regular file: {relativ}")
    lesen(ordner)
    return dateien


def importieren(ordner, reise, wer, grund="", ab=0):
    """Liest einen Reiseordner als Vorgang ein (Anfangsvorgang mit Stand ab + 1). Ist die Reise schon vorhanden,
    werden nur Unterschiede eingetragen, fehlende Dateien als Tombstone. -> Vorgang(nummer, stand)."""
    dateien = _ordner_lesen(ordner)
    name = Path(ordner).name

    def arbeit(v):
        try:
            bisher = _stand(v, reise, spalte="pruefsumme")
        except KeyError:
            bisher = {}
        alles = {**{p: None for p in bisher if p not in dateien}, **dateien}
        return _eintragen(v, reise, alles, wer, "importieren", f"import:{name}", grund, herkunft=f"import:{name}",
                          ab=ab)
    return _transaktion(arbeit)


def zuruecksetzen(reise, bis, wer, grund):
    """Neuer Vorgang mit dem Inhalt von Stand bis (alte Fassungen, Tombstones); Person und Grund Pflicht, der Verlauf
    wird nie gekürzt. Keine Abweichung: ValueError."""
    if not wer or not grund:
        raise ValueError("person and reason are required")
    bis = int(bis)

    def arbeit(v):
        alt, jetzt = _stand(v, reise, bis), _stand(v, reise)
        dateien = {p: None for p in jetzt if p not in alt}
        dateien.update({p: bytes(b) for p, b in alt.items() if jetzt.get(p) != b})
        if not dateien:
            raise ValueError(f"{reise}: stand {bis} equals the current stand")
        return _eintragen(v, reise, dateien, wer, "zuruecksetzen", f"zuruecksetzen:{bis}", grund,
                          herkunft=f"zuruecksetzen:{bis}")
    return _transaktion(arbeit)


def pruefen(reise=None):
    """Rechnet die SHA-256 jeder Version neu, prüft integrity_check, die Stand-Folge je Reise und Tombstones ohne
    Inhalt. -> Liste der Abweichungen (leer = in Ordnung). Eigene Verbindung, schreibt nichts."""
    p = pfad()
    if not p.exists():
        return []
    funde = []
    with closing(sqlite3.connect(p, timeout=10)) as v:
        ergebnis = [z[0] for z in v.execute("PRAGMA integrity_check")]
        if ergebnis != ["ok"]:
            funde += [f"integrity_check: {z}" for z in ergebnis]
        bedingung, werte = ("WHERE reise = ?", (reise,)) if reise is not None else ("", ())
        letzter = {}
        for r, nummer, stand in v.execute(f"SELECT reise, nummer, stand FROM vorgaenge {bedingung} ORDER BY nummer",
                                          werte):
            if r in letzter and stand <= letzter[r]:
                funde.append(f"{r}: stand {stand} of operation {nummer} does not follow stand {letzter[r]}")
            letzter[r] = stand
        for r, vorgang, pf, inhalt, summe in v.execute(
                f"SELECT reise, vorgang, pfad, inhalt, pruefsumme FROM versionen {bedingung} ORDER BY vorgang, pfad",
                werte):
            if inhalt is None:
                if summe is not None:
                    funde.append(f"{r} {pf} (operation {vorgang}): tombstone with checksum")
            elif summe is None:
                funde.append(f"{r} {pf} (operation {vorgang}): content without checksum")
            elif _summe(bytes(inhalt)) != summe:
                funde.append(f"{r} {pf} (operation {vorgang}): checksum mismatch")
    return funde


def sichern():
    """Schnappschuss über die Backup-API von SQLite wie konten.sichern(): geprüft mit integrity_check, ohne WAL, ersetzt
    den vorigen erst, wenn er fertig ist, unter <Speicher>/sicherung/reisen.db (600). -> Pfad oder None ohne Datenbank."""
    p = pfad()
    if not p.exists():
        return None
    ordner = p.parent / "sicherung"
    ordner.mkdir(exist_ok=True)
    os.chmod(ordner, 0o700)
    ziel, tmp = ordner / "reisen.db", ordner / f".reisen.db.{os.getpid()}"
    tmp.unlink(missing_ok=True)
    try:
        with closing(sqlite3.connect(p, timeout=10)) as quelle, closing(sqlite3.connect(tmp)) as kopie:
            os.chmod(tmp, 0o600)
            quelle.backup(kopie)
            kopie.execute("PRAGMA journal_mode = DELETE")   # eine Datei ohne -wal, so wie sie im Backup liegt
            if kopie.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise sqlite3.DatabaseError("integrity_check")
        os.replace(tmp, ziel)
    finally:
        tmp.unlink(missing_ok=True)
    return ziel


class _Hilfe(Exception):
    """Unbekannter Befehl oder falsche Angaben: Hilfe zeigen."""


def _optionen(a, namen):
    """Trennt --name WERT von den übrigen Angaben."""
    rest, werte, i = [], {}, 0
    while i < len(a):
        if a[i] in namen:
            if i + 1 >= len(a):
                raise _Hilfe()
            werte[a[i][2:]] = a[i + 1]
            i += 2
        else:
            rest.append(a[i])
            i += 1
    return rest, werte


def main(a):
    try:
        befehl, rest = (a[0], a[1:]) if a else ("", [])
        if befehl == "importieren":
            rest, o = _optionen(rest, ("--grund", "--ab"))
            if len(rest) != 3:
                raise _Hilfe()
            print(f"stand {importieren(*rest, grund=o.get('grund', ''), ab=int(o.get('ab', 0))).stand}")
        elif befehl == "exportieren":
            rest, o = _optionen(rest, ("--bis",))
            if len(rest) != 2:
                raise _Hilfe()
            exportieren(*rest, bis=int(o["bis"]) if "bis" in o else None)
            print(rest[1])
        elif befehl == "verlauf" and len(rest) in (1, 2):
            for e in verlauf(rest[0], int(rest[1]) if len(rest) == 2 else None):
                print(f"{e['nummer']}  {e['zeit']}  {e['wer']}  {e['werkzeug']}  {e['was']}  "
                      f"({len(e['dateien'])} files)")
        elif befehl == "zuruecksetzen" and len(rest) == 4:
            print(f"stand {zuruecksetzen(rest[0], int(rest[1]), rest[2], rest[3]).stand}")
        elif befehl == "pruefen" and len(rest) <= 1:
            funde = pruefen(rest[0] if rest else None)
            for f in funde:
                print(f)
            if funde:
                return 3
            print("ok")
        elif befehl == "sichern" and not rest:
            z = sichern()   # ohne Datenbank: nichts zu sichern, keine Ausgabe
            if z:
                print(z)
        else:
            raise _Hilfe()
    except _Hilfe:
        print(__doc__)
        return 1
    except KeyError as f:
        print(f"ERROR: unknown trip or stand: {f.args[0] if f.args else ''}")
        return 2
    except (ValueError, OSError, sqlite3.Error, VorgangVorhanden) as f:
        print(f"ERROR: {f}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
