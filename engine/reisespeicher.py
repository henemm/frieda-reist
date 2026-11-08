"""Reisespeicher (Stufe 1, #346, Epic #345, ADR-0009): Reisedaten als unveränderliche Versionen in SQLite, nur anhängen.

Ein Vorgang ist ein Schreibvorgang (Person, Rolle, Werkzeug, Titel, Grund, Zeit, Kennung); je Vorgang gibt es eine
Version je geänderter Datei (Bytes und SHA-256, ein Tombstone ohne Inhalt für eine gelöschte Datei). Die Stand-Nummer
einer Reise zählt Vorgänge, nicht Dateien (je Schreibvorgang +1, #226). Der Stand s einer Reise ist je Pfad die jüngste
Version unter den Vorgängen mit stand <= s; ein Tombstone heißt: die Datei fehlt in diesem Stand.

Nur anhängen: Trigger verweigern UPDATE und DELETE auf beiden Tabellen (mit recursive_triggers, sonst löschte
INSERT OR REPLACE an ihnen vorbei), der Authorizer der Verbindung aus db() verweigert dazu UPDATE, DELETE, DROP,
ALTER TABLE und PRAGMA writable_schema. Das schützt vor Software-Fehlern und Fehlbedienung, nicht vor jemandem mit
Schreibzugriff auf die Datei; dagegen helfen `pruefen` und die Sicherung außer Haus (ADR-0009).

Ab Stufe 2 (#347) schreibt der Schreibweg (engine/schreiben.py) jede Reise aus FR_SPEICHERREISEN hierher: ein Vorgang je
Schreibvorgang über ordner_als_vorgang, mit erwartet= gegen verlorene Änderungen; die übrigen Reisen schreiben bis Stufe 5
weiter über Git (engine/schreiben_git.py). Daneben beschreiben die Datenbank nur die Befehle unten.

Ab Stufe 3 (#348) baut betrieb/veroeffentlichen.sh diese Reisen aus dem Speicher: materialisieren bringt einen Stand in
einen Ordner für den Generator (<FR_DIENST>/bau/reisen/<reise>, Nummer in <ordner>.stand), staende nennt je Reise die
Nummer im Speicher und auf der Seite. vergleichen hält den Export gegen einen Ordner (betrieb/vergleichslauf.sh: gegen
den Dateistand aus Git), zustand ist der prüfbare Zustand der Sicherung für den Monitor der Instanz. Diese Befehle lesen
nur und legen keine Datenbank an.

Ablage: <FR_SPEICHER, sonst <Seiten>/_speicher>/reisen.db (SQLite, WAL), nur für den Betreiber lesbar;
Schnappschuss unter <Speicher>/sicherung/reisen.db.

Ab Stufe 4 (#349) liegen Medien (Dateien unter medien/ mit einer Endung aus AUSLAGERN, ohne medien/icon.svg und
medien/icon.png) nicht mehr in der Datenbank, sondern einmal je Inhalt als Datei in <Speicher>/ablage/<aa>/<summe>
(SHA-256, Ordner 700, Dateien 400). Die Zeile in versionen bleibt als Verweis (inhalt NULL, Prüfsumme gesetzt,
ausgelagert = 1); ein Tombstone hat weder Inhalt noch Prüfsumme. Die Datei wird vor der Zeile geschrieben, nie geändert
und nie gelöscht (verwaiste Dateien räumt nur der Betreiber auf); beim Lesen wird ihre Prüfsumme nachgerechnet.

Aufrufe:
  python3 engine/reisespeicher.py importieren <ordner> <reise> <wer> [--grund TEXT] [--ab N]   Reiseordner als Vorgang
  python3 engine/reisespeicher.py exportieren <reise> <ziel> [--bis N]       Stand in einen leeren Ordner schreiben
  python3 engine/reisespeicher.py verlauf <reise> [n]                        Vorgänge, neueste zuerst
  python3 engine/reisespeicher.py zuruecksetzen <reise> <bis> <wer> <grund>  neuer Vorgang mit dem Inhalt von Stand <bis>
  python3 engine/reisespeicher.py pruefen [reise]                            Prüfsummen und Stand-Folge nachrechnen
  python3 engine/reisespeicher.py sichern                                    sauberer Schnappschuss nach <Speicher>/sicherung/
  python3 engine/reisespeicher.py materialisieren <reise> <ordner> [--bis N] Stand in einen Ordner bringen (ersetzt ihn)
  python3 engine/reisespeicher.py vergleichen <reise> <ordner> [--bis N]     Exit 0 gleich, 1 Unterschied, 2 Fehler
  python3 engine/reisespeicher.py zustand [--sicherung-max-stunden H]        Exit 0 in Ordnung, 1 Sicherung fehlt/alt, 2 Fehler
  python3 engine/reisespeicher.py staende <reise> …                          je Reise „<reise> <Speicher> <Seite>“ (- = keine)
"""
import collections
import errno
import hashlib
import os
import re
import secrets
import sqlite3
import stat
import sys
import time
from contextlib import closing
from pathlib import Path

import instanz
from stand import zeit_iso

Vorgang = collections.namedtuple("Vorgang", "nummer stand")
Verweis = collections.namedtuple("Verweis", "summe")   # Stand einer ausgelagerten Datei: die Bytes liegen in der Ablage

AUSLAGERN = ("png", "jpg", "jpeg", "webp", "gif", "gpx", "pmtiles")   # Endungen der Medien, die in die Ablage kommen
NICHT_AUSLAGERN = ("medien/icon.svg", "medien/icon.png")   # klein, der Bau braucht sie: bleiben in der Datenbank
SCHEMA_VERSION = 2
_SUMME = re.compile(r"[0-9a-f]{64}")


class VorgangVorhanden(Exception):
    """Die Kennung ist schon eingetragen: Es wurde nichts geschrieben, die Wiederholung ist ungefährlich."""

    def __init__(self, nummer, stand):
        self.nummer, self.stand = nummer, stand
        super().__init__(f"operation already recorded: {nummer} (stand {stand})")


class NichtsGeaendert(ValueError):
    """Gegenüber dem Stand ändert sich nichts: kein Vorgang (der Schreibweg antwortet „nichts geändert“)."""


class StandGeaendert(Exception):
    """Der Stand der Reise ist nicht mehr der erwartete (jemand hat zwischenzeitlich geschrieben): nichts geschrieben."""

    def __init__(self, erwartet, aktuell):
        self.erwartet, self.aktuell = erwartet, aktuell
        super().__init__(f"stand changed: expected {erwartet}, current {aktuell}")


class AblageFehlt(Exception):
    """Eine verwiesene Datei fehlt in der Ablage des Speichers (Stufe 4, #349)."""

    def __init__(self, pfad, summe):
        self.pfad, self.summe = pfad, summe
        super().__init__(f"file missing in store: {pfad} (checksum {summe})")


class AblageFehler(Exception):
    """Eine Datei der Ablage ist beschädigt (Prüfsumme oder Größe stimmen nicht, keine reguläre Datei); nie repariert."""

    def __init__(self, pfad, summe):
        self.pfad, self.summe = pfad, summe
        super().__init__(f"store file damaged: {pfad} (checksum {summe})")


SCHEMA = """
CREATE TABLE IF NOT EXISTS vorgaenge (
  nummer INTEGER PRIMARY KEY AUTOINCREMENT, reise TEXT NOT NULL, stand INTEGER NOT NULL, wann TEXT NOT NULL,
  wer TEXT NOT NULL, rolle TEXT NOT NULL DEFAULT '', werkzeug TEXT NOT NULL, titel TEXT NOT NULL,
  grund TEXT NOT NULL DEFAULT '', kennung TEXT UNIQUE, herkunft TEXT NOT NULL DEFAULT '',
  UNIQUE (reise, stand), UNIQUE (nummer, reise));
CREATE TABLE IF NOT EXISTS versionen (
  vorgang INTEGER NOT NULL, reise TEXT NOT NULL, pfad TEXT NOT NULL, inhalt BLOB, pruefsumme TEXT,
  ausgelagert INTEGER NOT NULL DEFAULT 0,
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
    if aktion == sqlite3.SQLITE_PRAGMA and (a1 or "").lower() == "table_info":
        return sqlite3.SQLITE_OK   # liest nur das Schema einer Tabelle (Spalte ausgelagert, #349)
    if aktion == sqlite3.SQLITE_PRAGMA and (a2 is not None or (a1 or "").lower() == "writable_schema"):
        return sqlite3.SQLITE_DENY   # nur lesende PRAGMAs ohne Wert; db() setzt seine vor dem Authorizer
    return sqlite3.SQLITE_OK


def db(timeout=10):
    """Verbindung zum Reisespeicher; legt ihn beim ersten Mal an (Ordner 700, Datei 600, WAL). Schema und Trigger
    entstehen vor dem Authorizer (executescript committet selbst), danach ist nur noch Anhängen erlaubt. timeout ist die
    Wartezeit auf die Sperre der Datenbank in Sekunden (der Schreibweg gibt die Restzeit seiner Frist); danach
    sqlite3.OperationalError."""
    p = pfad()
    neu = not p.exists()
    if neu:
        p.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(p.parent, 0o700)
    v = sqlite3.connect(p, timeout=timeout)
    v.row_factory = sqlite3.Row
    v.execute("PRAGMA foreign_keys = ON")
    v.execute("PRAGMA recursive_triggers = ON")
    if neu:
        os.chmod(p, 0o600)
        v.execute("PRAGMA journal_mode = WAL")
    v.executescript(SCHEMA)
    if not _hat_spalte(v):   # Speicher der Stufe 3 (#349): Spalte ergänzen, vor dem Authorizer (er verbietet ALTER TABLE)
        try:
            v.execute("ALTER TABLE versionen ADD COLUMN ausgelagert INTEGER NOT NULL DEFAULT 0")
        except sqlite3.OperationalError as e:   # ein anderer Prozess war schneller
            if "duplicate column" not in str(e):
                raise
    if v.execute("PRAGMA user_version").fetchone()[0] < SCHEMA_VERSION:
        v.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    v.set_authorizer(_waechter)
    return v


def _hat_spalte(v):
    """Hat versionen die Spalte ausgelagert? (Lesende Verbindungen sehen auch einen Speicher, der noch nicht gehoben ist.)"""
    return any(z[1] == "ausgelagert" for z in v.execute("PRAGMA table_info(versionen)"))


def auszulagern(p):
    """Kommt die Datei mit diesem Pfad in die Ablage? Nur Pfad und Endung zählen (Entscheidung 3 der Spec 349)."""
    klein = p.lower()
    name = klein.rsplit("/", 1)[-1]
    return (klein.startswith("medien/") and klein not in NICHT_AUSLAGERN and "." in name
            and name.rsplit(".", 1)[1] in AUSLAGERN)


def ablage_pfad(summe):
    """Ort einer Datei in der Ablage: <Speicher>/ablage/<aa>/<summe>. Der Name kommt nur aus der Prüfsumme (64 Hexzeichen,
    klein); alles andere: ValueError."""
    if not isinstance(summe, str) or not _SUMME.fullmatch(summe):
        raise ValueError(f"invalid checksum: {summe!r}")
    return instanz.speicher_ablage() / summe[:2] / summe


def _ablage_oeffnen(summe, pfad_):
    """Ablagedatei zum Lesen öffnen: nur eine reguläre Datei, kein Symlink. Fehlt sie: AblageFehlt, sonst AblageFehler."""
    f = ablage_pfad(summe)
    try:
        st = os.lstat(f)
    except FileNotFoundError:
        raise AblageFehlt(pfad_, summe) from None
    if not stat.S_ISREG(st.st_mode):
        raise AblageFehler(pfad_, summe)
    try:
        return os.fdopen(os.open(f, os.O_RDONLY | os.O_NOFOLLOW), "rb")
    except FileNotFoundError:
        raise AblageFehlt(pfad_, summe) from None
    except OSError as e:
        if e.errno == errno.ELOOP:   # zwischen lstat und open zum Symlink geworden
            raise AblageFehler(pfad_, summe) from None
        raise


def _ablage_pruefen(summe, pfad_="", groesse=None):
    """Prüft eine Ablagedatei streamend (vorhanden, regulär, Größe, SHA-256), ohne sie zu laden; liest nur."""
    with _ablage_oeffnen(summe, pfad_) as f:
        if groesse is not None and os.fstat(f.fileno()).st_size != groesse:
            raise AblageFehler(pfad_, summe)
        if hashlib.file_digest(f, "sha256").hexdigest() != summe:
            raise AblageFehler(pfad_, summe)


def ablage_lesen(summe, pfad_=""):
    """Bytes einer Ablagedatei, Prüfsumme nachgerechnet. Fehlt sie: AblageFehlt; Summe falsch oder Symlink: AblageFehler."""
    with _ablage_oeffnen(summe, pfad_) as f:
        inhalt = f.read()
    if _summe(inhalt) != summe:
        raise AblageFehler(pfad_, summe)
    return inhalt


def _ordner_anlegen(o):
    """Ordner der Ablage anlegen (700); einen vorhandenen lässt es, wie er ist."""
    try:
        o.mkdir()
    except FileExistsError:
        return
    os.chmod(o, 0o700)


def ablage_ablegen(summe, inhalt, pfad_=""):
    """Legt die Bytes unter ihrer Prüfsumme in die Ablage (Datei 400): temporär im Ordner schreiben, fsync, os.link auf den
    Endnamen (nie ersetzen), Temporärdatei weg, fsync des Ordners. Liegt die Datei schon da, wird sie nur geprüft; stimmt
    sie nicht, AblageFehler, und nichts wird überschrieben. -> Pfad der Ablagedatei."""
    inhalt = bytes(inhalt)
    if _summe(inhalt) != summe:
        raise ValueError(f"checksum does not match the content: {pfad_}")
    ziel = ablage_pfad(summe)
    try:
        _ablage_pruefen(summe, pfad_, len(inhalt))
        return ziel
    except AblageFehlt:
        pass
    wurzel = instanz.speicher_ablage()
    wurzel.parent.mkdir(parents=True, exist_ok=True)
    _ordner_anlegen(wurzel)
    _ordner_anlegen(ziel.parent)
    tmp = ziel.parent / f".{summe}.{os.getpid()}.{secrets.token_hex(4)}"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(inhalt)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, 0o400)
        try:
            os.link(tmp, ziel)
        except FileExistsError:   # ein zweiter Schreiber war schneller: gilt als „schon da“, wenn sie stimmt
            _ablage_pruefen(summe, pfad_, len(inhalt))
    finally:
        os.unlink(tmp)   # nur die eigene Temporärdatei
    o = os.open(ziel.parent, os.O_RDONLY)
    try:
        os.fsync(o)
    finally:
        os.close(o)
    return ziel


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
    """Pfad -> Spalte (inhalt oder pruefsumme) im Stand bis (ohne: neuester); unbekannte Reise oder Stand: KeyError.
    Bei inhalt steht für eine ausgelagerte Datei Verweis(summe) statt der Bytes; gelesen wird nur die Datenbank."""
    hoechster = v.execute("SELECT MAX(stand) FROM vorgaenge WHERE reise = ?", (reise,)).fetchone()[0]
    if hoechster is None:
        raise KeyError(reise)
    if bis is None:
        bis = hoechster
    elif not v.execute("SELECT 1 FROM vorgaenge WHERE reise = ? AND stand = ?", (reise, bis)).fetchone():
        raise KeyError(f"{reise}: stand {bis}")
    # Zwei Stufen (#347): innen nur Kennzahlen (pfad, vorgang, weg), erst für die Gewinner-Zeilen wird die Spalte gelesen.
    # Erst eine schlanke Zeilenliste (nur Kennzahlen, materialisiert), damit die Fensterfunktion keine Inhalte mitsortiert.
    # Ein Tombstone hat weder Inhalt noch Prüfsumme; ein Verweis in die Ablage (#349) nur keinen Inhalt.
    lesen = "s.inhalt, s.pruefsumme" if spalte == "inhalt" else f"s.{spalte}"
    zeilen = v.execute(f"""
        WITH k AS MATERIALIZED (
          SELECT s.pfad, s.vorgang, s.inhalt IS NULL AND s.pruefsumme IS NULL AS weg
          FROM versionen s JOIN vorgaenge g ON g.nummer = s.vorgang
          WHERE g.reise = ? AND g.stand <= ?),
        w AS (
          SELECT pfad, vorgang, weg, ROW_NUMBER() OVER (PARTITION BY pfad ORDER BY vorgang DESC) AS rang FROM k)
        SELECT w.pfad, {lesen} FROM w JOIN versionen s ON s.vorgang = w.vorgang AND s.pfad = w.pfad
        WHERE w.rang = 1 AND NOT w.weg ORDER BY w.pfad""", (reise, bis))
    if spalte == "inhalt":
        return {z[0]: Verweis(z[2]) if z[1] is None else z[1] for z in zeilen}
    return {z[0]: z[1] for z in zeilen}


def _eintragen(v, reise, dateien, wer, werkzeug, titel, grund="", kennung=None, rolle="", wann=None, herkunft="",
               ab=0, erwartet=None):
    """Ein Vorgang in der laufenden Transaktion von v (BEGIN IMMEDIATE beim Aufrufer). Erst die Kennung, dann der
    erwartete Stand (0: es gibt noch keinen). Medien (auszulagern) kommen vor der Zeile in die Ablage, auch wenn der
    Vorgang danach scheitert: eine verwaiste Ablagedatei ist harmlos, ein Verweis ohne Datei entsteht so nie (#349).
    Verweis(summe) als Inhalt trägt eine vorhandene Ablagedatei neu ein (zuruecksetzen)."""
    if kennung is not None:
        z = v.execute("SELECT nummer, stand FROM vorgaenge WHERE kennung = ?", (kennung,)).fetchone()
        if z:
            raise VorgangVorhanden(z[0], z[1])
    for p, inhalt in dateien.items():
        _pfad_pruefen(p)
        if inhalt is not None and not isinstance(inhalt, (bytes, bytearray, memoryview, Verweis)):
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
        elif isinstance(inhalt, Verweis):
            if bisher.get(p) != inhalt.summe:
                neu[p] = (inhalt, inhalt.summe)
        else:
            inhalt = bytes(inhalt)
            summe = _summe(inhalt)
            if bisher.get(p) != summe:
                neu[p] = (inhalt, summe)
    for p, (inhalt, summe) in sorted(neu.items()):   # Datei vor Datenbank (Entscheidung 6 der Spec 349)
        if isinstance(inhalt, Verweis):
            _ablage_pruefen(summe, p)
        elif inhalt is not None and auszulagern(p):
            ablage_ablegen(summe, inhalt, p)
    if erwartet is not None:
        aktuell = v.execute("SELECT MAX(stand) FROM vorgaenge WHERE reise = ?", (reise,)).fetchone()[0] or 0
        if aktuell != erwartet:
            raise StandGeaendert(erwartet, aktuell)
    if not neu:
        raise NichtsGeaendert(f"{reise}: nothing changed")
    weg = {p for p, (inhalt, _) in neu.items() if inhalt is None}
    _kollision_pruefen((set(bisher) - weg) | (set(neu) - weg))
    hoechster = v.execute("SELECT MAX(stand) FROM vorgaenge WHERE reise = ?", (reise,)).fetchone()[0]
    stand = (ab if hoechster is None else hoechster) + 1
    nummer = v.execute(
        "INSERT INTO vorgaenge (reise, stand, wann, wer, rolle, werkzeug, titel, grund, kennung, herkunft) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (reise, stand, wann or zeit_iso(), wer, rolle, werkzeug, titel, grund, kennung, herkunft)).lastrowid
    zeilen = []
    for p, (inhalt, summe) in sorted(neu.items()):
        aus = isinstance(inhalt, Verweis) or (inhalt is not None and auszulagern(p))
        zeilen.append((nummer, reise, p, None if aus else inhalt, summe, 1 if aus else 0))
    v.executemany("INSERT INTO versionen (vorgang, reise, pfad, inhalt, pruefsumme, ausgelagert) "
                  "VALUES (?, ?, ?, ?, ?, ?)", zeilen)
    return Vorgang(nummer, stand)


def _transaktion(arbeit, timeout=10):
    """arbeit(v) in einer Schreib-Transaktion (BEGIN IMMEDIATE); bei einem Fehler wird nichts geschrieben."""
    with closing(db(timeout)) as v:
        v.execute("BEGIN IMMEDIATE")
        try:
            ergebnis = arbeit(v)
        except BaseException:
            v.rollback()
            raise
        v.commit()
        return ergebnis


def vorgang_schreiben(reise, dateien, wer, werkzeug, titel, grund="", kennung=None, rolle="", wann=None, herkunft="",
                      erwartet=None, timeout=10):
    """Ein Vorgang: dateien ist Pfad -> Bytes (None = löschen). Unveränderte Dateien werden übersprungen; bleibt nichts,
    ValueError. Bekannte Kennung: VorgangVorhanden. erwartet: Stand-Nummer, von der der Schreiber ausging (0: neue Reise);
    weicht der Stand in der Transaktion ab, StandGeaendert ohne Schreiben (None: keine Prüfung). timeout: Wartezeit auf
    die Sperre der Datenbank. -> Vorgang(nummer, stand)."""
    return _transaktion(lambda v: _eintragen(v, reise, dateien, wer, werkzeug, titel, grund, kennung, rolle, wann,
                                             herkunft, erwartet=erwartet), timeout)


def ordner_als_vorgang(reise, ordner, basis, wer, werkzeug, titel, grund, kennung, rolle, timeout=10):
    """Baustein „Ordner vorher/nachher -> ein Vorgang“ (#347): vergleicht den Ordner (nachher) über Prüfsummen mit dem Stand
    basis (vorher) und schreibt die Unterschiede als einen Vorgang, fehlende Dateien als Tombstone, mit erwartet=basis.
    basis=0: neue Reise. Ohne Unterschied ValueError. Genutzt vom Schreibweg (auch reise_anlegen) und von
    `neu.py nachziehen-speicher` (#348). -> Vorgang(nummer, stand)."""
    nachher = _ordner_lesen(ordner)
    vorher = {}
    if basis:
        try:
            with closing(db(timeout)) as v:
                vorher = _stand(v, reise, basis, "pruefsumme")
        except KeyError:
            vorher = {}
    dateien = {p: None for p in vorher if p not in nachher}
    dateien.update({p: b for p, b in nachher.items() if vorher.get(p) != _summe(b)})
    if not dateien:
        raise NichtsGeaendert(f"{reise}: nothing changed")
    return vorgang_schreiben(reise, dateien, wer, werkzeug, titel, grund, kennung, rolle, erwartet=basis,
                             timeout=timeout)


def reisen():
    """Alle Reisen mit mindestens einem Vorgang, sortiert. Liest nur; ohne Datenbank: leer (legt sie nicht an)."""
    if not pfad().exists():
        return []
    with closing(db()) as v:
        return [z[0] for z in v.execute("SELECT DISTINCT reise FROM vorgaenge ORDER BY reise")]


def datei(reise, pfad_, bis=None):
    """Inhalt einer Datei im Stand bis (ohne: neuester) -> bytes, ohne die übrigen Dateien zu laden. Unbekannte Reise,
    Stand oder Datei, auch gelöscht: KeyError. Pfadregeln wie vorgang_schreiben."""
    _pfad_pruefen(pfad_)
    if not pfad().exists():
        raise KeyError(reise)
    with closing(db()) as v:
        hoechster = v.execute("SELECT MAX(stand) FROM vorgaenge WHERE reise = ?", (reise,)).fetchone()[0]
        if hoechster is None:
            raise KeyError(reise)
        if bis is None:
            bis = hoechster
        elif not v.execute("SELECT 1 FROM vorgaenge WHERE reise = ? AND stand = ?", (reise, bis)).fetchone():
            raise KeyError(f"{reise}: stand {bis}")
        z = v.execute("""SELECT s.inhalt, s.pruefsumme FROM versionen s JOIN vorgaenge g ON g.nummer = s.vorgang
                         WHERE g.reise = ? AND s.pfad = ? AND g.stand <= ? ORDER BY s.vorgang DESC LIMIT 1""",
                      (reise, pfad_, bis)).fetchone()
    if z is None or (z[0] is None and z[1] is None):
        raise KeyError(f"{reise}: {pfad_}")
    if z[0] is None:   # ausgelagert (#349)
        return ablage_lesen(z[1], pfad_)
    return bytes(z[0])


def stand_nummer(reise):
    """Höchste Stand-Nummer der Reise oder None, wenn sie unbekannt ist."""
    with closing(db()) as v:
        return v.execute("SELECT MAX(stand) FROM vorgaenge WHERE reise = ?", (reise,)).fetchone()[0]


def aktueller_stand(reise, bis=None):
    """Pfad -> Bytes der Reise im Stand bis (ohne: neuester); unbekannte Reise oder Stand: KeyError. Ausgelagerte Dateien
    kommen aus der Ablage (AblageFehlt, AblageFehler)."""
    with closing(db()) as v:
        st = _stand(v, reise, bis)
    return {p: ablage_lesen(b.summe, p) if isinstance(b, Verweis) else bytes(b) for p, b in st.items()}


def vorgang_eingetragen(kennung, timeout=10):
    """Vorgang mit dieser Kennung oder None (Nachprüfung nach einer Zeitüberschreitung; liest nur)."""
    with closing(db(timeout)) as v:
        z = v.execute("SELECT nummer, stand FROM vorgaenge WHERE kennung = ?", (kennung,)).fetchone()
    return Vorgang(z[0], z[1]) if z else None


def verlauf(reise, n=None, bis=None):
    """Vorgänge der Reise, neueste zuerst; nummer ist der Stand (wie stand.aenderungen), vorgang die Vorgangs-Nummer.
    bis: nur Vorgänge bis zu diesem Stand (die Seite eines materialisierten Stands, #348)."""
    with closing(db()) as v:
        zeilen = v.execute("SELECT * FROM vorgaenge WHERE reise = ? AND stand <= ? ORDER BY stand DESC LIMIT ?",
                           (reise, 2 ** 62 if bis is None else int(bis), -1 if n is None else int(n))).fetchall()
        return [{"nummer": z["stand"], "zeit": z["wann"], "was": z["titel"], "wer": z["wer"], "vorgang": z["nummer"],
                 "werkzeug": z["werkzeug"], "grund": z["grund"],
                 "dateien": [d[0] for d in v.execute("SELECT pfad FROM versionen WHERE vorgang = ? ORDER BY pfad",
                                                     (z["nummer"],))]}
                for z in zeilen]


def exportieren(reise, ziel, bis=None):
    """Schreibt den Stand in ziel (fehlt oder leerer Ordner, sonst FileExistsError). Alle Pfade werden vorher geprüft;
    ein Pfad, der aus dem Ziel führte, bricht mit ValueError ab, bevor etwas geschrieben ist. Ausgelagerte Dateien werden
    vorher alle geprüft (vorhanden, regulär, Prüfsumme; sonst AblageFehlt/AblageFehler, ehe etwas geschrieben ist) und
    dann als Hardlink aus der Ablage angelegt, auf einem anderen Dateisystem als Kopie (#349)."""
    with closing(db()) as v:
        dateien = _stand(v, reise, bis)
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
        plan.append((p, aus, inhalt))
    for p, _, inhalt in plan:   # Vorab-Runde: kein halber Ordner, wenn die Ablage lückenhaft oder beschädigt ist
        if isinstance(inhalt, Verweis):
            _ablage_pruefen(inhalt.summe, p)
    ziel.mkdir(parents=True, exist_ok=True)
    for p, aus, inhalt in plan:
        fehlend = [o for o in [aus.parent, *aus.parent.parents] if basis in o.parents and not o.exists()]
        aus.parent.mkdir(parents=True, exist_ok=True)
        for o in fehlend:
            os.chmod(o, 0o755)
        if isinstance(inhalt, Verweis):
            try:
                os.link(ablage_pfad(inhalt.summe), aus, follow_symlinks=False)
                continue   # Hardlink behält den Modus 400 der Ablagedatei
            except FileExistsError:
                raise
            except OSError:   # anderes Dateisystem oder nicht unterstützt: Kopie
                inhalt = ablage_lesen(inhalt.summe, p)
        with open(aus, "xb") as f:
            f.write(inhalt)
        os.chmod(aus, 0o644)


def _ordner_lesen(ordner, summen=False):
    """Pfad -> Bytes aller regulären Dateien (auch versteckte, ohne .git); ein Symlink oder Sonderdatei: ValueError.
    summen=True: Pfad -> SHA-256 statt der Bytes (der Vergleich hält keine Inhalte, #348)."""
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
                        dateien[_pfad_pruefen(relativ)] = hashlib.file_digest(f, "sha256").hexdigest() if summen \
                            else f.read()
                else:
                    raise ValueError(f"not a regular file: {relativ}")
    lesen(ordner)
    return dateien


def _nur_lesen(timeout=10):
    """Lesende Verbindung für die Befehle des Betriebs (materialisieren, vergleichen, zustand, staende): legt nichts an
    und schreibt nichts. Ohne Datenbank FileNotFoundError."""
    p = pfad()
    if not p.exists():
        raise FileNotFoundError(f"no trip store: {p}")
    v = sqlite3.connect(p.resolve().as_uri() + "?mode=ro", uri=True, timeout=timeout)
    v.row_factory = sqlite3.Row
    return v


def _hoechster(v, reise):
    return v.execute("SELECT MAX(stand) FROM vorgaenge WHERE reise = ?", (reise,)).fetchone()[0]


def stand_datei(ordner):
    """Datei neben dem materialisierten Ordner mit dessen Stand-Nummer (nie darin: _ordner_lesen läse sie als Reisedatei)."""
    return Path(f"{ordner}.stand")


def _bauordner_entfernen(ordner):
    """Entfernt einen Bauordner (<ordner>.neu oder .alt) samt Inhalt; Symlinks darin werden nur selbst entfernt, nie
    verfolgt. Ein Hardlink aus der Ablage verliert nur diesen Namen, die Ablagedatei bleibt."""
    for wurzel, ordner_namen, datei_namen in os.walk(ordner, topdown=False):
        for name in datei_namen:
            os.unlink(os.path.join(wurzel, name))
        for name in ordner_namen:
            p = os.path.join(wurzel, name)
            if os.path.islink(p):
                os.unlink(p)
            else:
                os.rmdir(p)
    os.rmdir(ordner)


def materialisieren(reise, ordner, bis=None):
    """Bringt Stand bis (ohne: den neuesten) der Reise in ordner, für den Generator (#348). Ein vorhandener Ordner wird
    ersetzt: erst nach <ordner>.neu exportieren, dann umbenennen, nie ein halber Ordner. Die Nummer wird zuerst gelesen
    und genau dieser Stand exportiert; sie steht danach in <ordner>.stand. -> Stand-Nummer."""
    ordner = Path(ordner)
    with closing(_nur_lesen()) as v:
        n = _hoechster(v, reise)
    if n is None:
        raise KeyError(reise)
    if bis is not None:
        n = int(bis)
    neu, alt = Path(f"{ordner}.neu"), Path(f"{ordner}.alt")
    for x in (neu, alt):
        if x.is_symlink() or x.is_file():
            x.unlink()
        elif x.exists():
            _bauordner_entfernen(x)
    exportieren(reise, neu, bis=n)
    if ordner.exists():
        os.rename(ordner, alt)
    os.rename(neu, ordner)
    try:
        _bauordner_entfernen(alt)
    except OSError:
        pass
    s = stand_datei(ordner)
    tmp = Path(f"{s}.{os.getpid()}")
    tmp.write_text(f"{n}\n", encoding="utf-8")
    os.replace(tmp, s)
    return n


def vergleichen(reise, ordner, bis=None):
    """Export der Reise (Stand bis, ohne: neuester) gegen einen Ordner, nur über Prüfsummen (#348). Gleich heißt: gleiche
    Pfadmenge und gleiche Bytes; leere Ordner, Rechte, Zeitstempel und .git zählen nicht. -> sortierte Liste
    [(art, pfad)] mit art „nur im Speicher“, „nur im Ordner“ oder „verschieden“; leer = gleich."""
    im_ordner = _ordner_lesen(ordner, summen=True)
    with closing(_nur_lesen()) as v:
        im_speicher = _stand(v, reise, bis, "pruefsumme")
    unterschiede = []
    for p in sorted(set(im_speicher) | set(im_ordner)):
        if p not in im_ordner:
            unterschiede.append(("nur im Speicher", p))
        elif p not in im_speicher:
            unterschiede.append(("nur im Ordner", p))
        elif im_speicher[p] != im_ordner[p]:
            unterschiede.append(("verschieden", p))
    return unterschiede


SICHERUNG_MAX_STUNDEN = 36   # wie der Stempel waechter-erfolg (docs/betrieb.md, Überwachung)


def zustand(max_stunden=SICHERUNG_MAX_STUNDEN):
    """Prüfbarer Zustand für den Monitor der Instanz (#348), liest nur -> (in_ordnung, [(name, wert)]). In Ordnung: keine
    Datenbank (Instanz ohne Speicher) oder eine Sicherung nicht älter als max_stunden (Änderungszeit von
    <Speicher>/sicherung/reisen.db). Nicht lesbare Datenbank: sqlite3.Error."""
    p = pfad()
    if not p.exists():
        return True, [("reisen", 0), ("sicherung_alter_s", "keine"), ("datenbank", "fehlt"), ("ablage_fehlt", 0)]
    with closing(_nur_lesen()) as v:
        n = v.execute("SELECT COUNT(DISTINCT reise) FROM vorgaenge").fetchone()[0]
        fehlt = len(_fehlende_ablagedateien(v))
    s = p.parent / "sicherung" / "reisen.db"
    alter = max(0, int(time.time() - s.stat().st_mtime)) if s.exists() else None
    ok = alter is not None and alter <= float(max_stunden) * 3600 and not fehlt
    return ok, [("reisen", n), ("sicherung_alter_s", "keine" if alter is None else alter), ("datenbank", "vorhanden"),
                ("ablage_fehlt", fehlt)]


def _fehlende_ablagedateien(v):
    """Verwiesene Summen (ausgelagert = 1), zu denen in der Ablage keine reguläre Datei liegt -> [(summe, pfad)]. Nur
    Vorhandensein, schnell, ohne Summen (die volle Prüfung ist pruefen)."""
    if not _hat_spalte(v):
        return []
    fehlt = []
    for summe, pf in v.execute("SELECT pruefsumme, MIN(pfad) FROM versionen WHERE ausgelagert = 1 "
                               "AND pruefsumme IS NOT NULL GROUP BY pruefsumme ORDER BY pruefsumme"):
        try:
            if not stat.S_ISREG(os.lstat(ablage_pfad(summe)).st_mode):
                fehlt.append((summe, pf))
        except (FileNotFoundError, ValueError):
            fehlt.append((summe, pf))
    return fehlt


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
    wird nie gekürzt. Keine Abweichung: ValueError. Ausgelagerte alte Fassungen werden als Verweis neu eingetragen, wenn
    ihre Ablagedatei stimmt (sonst AblageFehlt/AblageFehler, kein Vorgang)."""
    if not wer or not grund:
        raise ValueError("person and reason are required")
    bis = int(bis)

    def arbeit(v):
        alt, jetzt = _stand(v, reise, bis, "pruefsumme"), _stand(v, reise, spalte="pruefsumme")
        inhalte = _stand(v, reise, bis)
        dateien = {p: None for p in jetzt if p not in alt}
        dateien.update({p: inhalte[p] if isinstance(inhalte[p], Verweis) else bytes(inhalte[p])
                        for p, s in alt.items() if jetzt.get(p) != s})
        if not dateien:
            raise ValueError(f"{reise}: stand {bis} equals the current stand")
        return _eintragen(v, reise, dateien, wer, "zuruecksetzen", f"zuruecksetzen:{bis}", grund,
                          herkunft=f"zuruecksetzen:{bis}")
    return _transaktion(arbeit)


def auslagern(reise, erwartet, wer, werkzeug, titel, grund="", kennung=None):
    """Umstellung bestehender Medien auf die Ablage (Stufe 4, #349, neu.py nachziehen-speicher): Medien im Stand der
    Reise, deren Bytes noch in der Datenbank liegen, kommen in die Ablage und bekommen in einem Vorgang je eine Verweiszeile
    mit gleicher Summe (nur hier darf eine Datei mit gleicher Summe erneut eingetragen werden). Der Inhalt der Reise
    ändert sich nicht. Bekannte Kennung: VorgangVorhanden; anderer Stand als erwartet: StandGeaendert (nichts
    geschrieben, die abgelegten Dateien bleiben). -> Vorgang oder None (nichts umzustellen)."""
    def arbeit(v):
        if kennung is not None:
            z = v.execute("SELECT nummer, stand FROM vorgaenge WHERE kennung = ?", (kennung,)).fetchone()
            if z:
                raise VorgangVorhanden(z[0], z[1])
        vorher = _stand(v, reise, spalte="pruefsumme")
        offen = {p: bytes(b) for p, b in _stand(v, reise).items() if not isinstance(b, Verweis) and auszulagern(p)}
        if not offen:
            return None
        summen = {p: _summe(b) for p, b in offen.items()}
        for p, b in sorted(offen.items()):
            ablage_ablegen(summen[p], b, p)
        aktuell = _hoechster(v, reise) or 0
        if aktuell != erwartet:
            raise StandGeaendert(erwartet, aktuell)
        nummer = v.execute(
            "INSERT INTO vorgaenge (reise, stand, wann, wer, rolle, werkzeug, titel, grund, kennung, herkunft) "
            "VALUES (?, ?, ?, ?, '', ?, ?, ?, ?, ?)",
            (reise, aktuell + 1, zeit_iso(), wer, werkzeug, titel, grund, kennung, titel)).lastrowid
        v.executemany("INSERT INTO versionen (vorgang, reise, pfad, inhalt, pruefsumme, ausgelagert) "
                      "VALUES (?, ?, ?, NULL, ?, 1)", [(nummer, reise, p, summen[p]) for p in sorted(offen)])
        if _stand(v, reise, spalte="pruefsumme") != vorher:   # der Inhalt darf sich nicht ändern
            raise RuntimeError(f"{reise}: offloading changed the content, nothing written")
        return Vorgang(nummer, aktuell + 1)
    return _transaktion(arbeit)


def pruefen(reise=None):
    """Rechnet die SHA-256 jeder Version neu, prüft integrity_check, die Stand-Folge je Reise und Tombstones ohne
    Inhalt, für ausgelagerte Versionen die Ablagedatei (vorhanden, regulär, Prüfsumme; nur gelesen). -> Liste der
    Abweichungen (leer = in Ordnung). Eigene Verbindung, schreibt nichts."""
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
        spalte = "ausgelagert" if _hat_spalte(v) else "0"
        ablage = {}   # Summe -> Fund (None: in Ordnung); jede Ablagedatei wird nur einmal gelesen
        for r, vorgang, pf, inhalt, summe, aus in v.execute(
                f"SELECT reise, vorgang, pfad, inhalt, pruefsumme, {spalte} FROM versionen {bedingung} "
                "ORDER BY vorgang, pfad", werte):
            if aus:
                if inhalt is not None:
                    funde.append(f"{r} {pf} (operation {vorgang}): externalized with content in the database")
                elif summe is None:
                    funde.append(f"{r} {pf} (operation {vorgang}): externalized without checksum")
                else:
                    if summe not in ablage:
                        try:
                            _ablage_pruefen(summe, pf)
                            ablage[summe] = None
                        except AblageFehlt:
                            ablage[summe] = "file missing in store"
                        except (AblageFehler, ValueError):
                            ablage[summe] = "store checksum mismatch"
                    if ablage[summe]:
                        funde.append(f"{r} {pf} (operation {vorgang}): {ablage[summe]}")
            elif inhalt is None:
                if summe is not None:
                    funde.append(f"{r} {pf} (operation {vorgang}): tombstone with checksum")
            elif summe is None:
                funde.append(f"{r} {pf} (operation {vorgang}): content without checksum")
            elif _summe(bytes(inhalt)) != summe:
                funde.append(f"{r} {pf} (operation {vorgang}): checksum mismatch")
    return funde


def sichern():
    """Schnappschuss über die Backup-API von SQLite wie konten.sichern(): geprüft mit integrity_check, ohne WAL, ersetzt
    den vorigen erst, wenn er fertig ist, unter <Speicher>/sicherung/reisen.db (600). Fehlt eine verwiesene Datei in der
    Ablage: AblageFehlt, der vorige bleibt. Die Ablage selbst sichert das Server-Backup (nur anhängend, #349).
    -> Pfad oder None ohne Datenbank."""
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
            fehlt = _fehlende_ablagedateien(kopie)   # ein Schnappschuss mit Verweisen ohne Datei ist wertlos (#349)
            if fehlt:
                raise AblageFehlt(fehlt[0][1], fehlt[0][0])
        os.replace(tmp, ziel)
    finally:
        tmp.unlink(missing_ok=True)
    return ziel


def ablage_satz(fehler, w1):
    """Satz des Katalogs zu AblageFehlt (pruefung.bauen.79) oder AblageFehler (pruefung.bauen.80); w1 ist die Reise."""
    import texte
    if isinstance(fehler, AblageFehler):
        return texte.satz("pruefung.bauen.80", w1=w1, ziel=fehler.pfad, summe=fehler.summe)
    return texte.satz("pruefung.bauen.79", w1=w1, ziel=fehler.pfad, summe=fehler.summe)


def ablage_ausgabe(fehler, w1):
    """Ausgabe eines Baus aus dem Speicher, der an der Ablage scheitert: ERROR-Zeile und der Satz als „ - …“ (so liest
    veroeffentlichen.sh einen roten Bau, baugrund), in der Sprache des Aufrufs."""
    return [f"ERROR: the trip {w1} cannot be built from the trip store:", f" - {ablage_satz(fehler, w1)}"]


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
        elif befehl == "materialisieren":
            rest, o = _optionen(rest, ("--bis",))
            if len(rest) != 2:
                raise _Hilfe()
            try:
                print(f"stand {materialisieren(*rest, bis=int(o['bis']) if 'bis' in o else None)}")
            except (AblageFehlt, AblageFehler) as f:   # Bau aus dem Speicher rot, Exit 2 mit Katalogtext (#349)
                print("\n".join(ablage_ausgabe(f, rest[0])))
                return 2
        elif befehl == "vergleichen":
            # Exit 1 heißt hier nur „Unterschied“: falsche Angaben geben wie jeder Fehler 2
            try:
                rest, o = _optionen(rest, ("--bis",))
            except _Hilfe:
                rest = []
            if len(rest) != 2:
                print("ERROR: usage: reisespeicher.py vergleichen <reise> <ordner> [--bis N]")
                return 2
            unterschiede = vergleichen(*rest, bis=int(o["bis"]) if "bis" in o else None)
            for art, p in unterschiede:
                print(f"{art}: {p}")
            n = len(unterschiede)
            print("gleich" if not n else f"{n} Unterschied" if n == 1 else f"{n} Unterschiede")
            return 1 if n else 0
        elif befehl == "zustand":
            rest, o = _optionen(rest, ("--sicherung-max-stunden",))
            if rest:
                raise _Hilfe()
            ok, werte = zustand(float(o.get("sicherung-max-stunden", SICHERUNG_MAX_STUNDEN)))
            for name, wert in werte:
                print(f"{name} {wert}")
            return 0 if ok else 1
        elif befehl == "staende" and rest:
            import stand
            v = _nur_lesen() if pfad().exists() else None   # ohne Datenbank: keine Reise hat einen Eintrag
            try:
                for r in rest:
                    n = _hoechster(v, r) if v else None
                    pub = stand.veroeffentlicht(r)[0]
                    print(f"{r} {'-' if n is None else n} {'-' if pub is None else pub}")
            finally:
                if v:
                    v.close()
        else:
            raise _Hilfe()
    except _Hilfe:
        print(__doc__)
        return 1
    except KeyError as f:
        print(f"ERROR: unknown trip or stand: {f.args[0] if f.args else ''}")
        return 2
    except (ValueError, OSError, sqlite3.Error, VorgangVorhanden, AblageFehlt, AblageFehler) as f:
        print(f"ERROR: {f}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
