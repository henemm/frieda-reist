#!/usr/bin/env python3
"""Konten: Menschen an ihrer E-Mail-Adresse erkennen (Paket J, Issues #43 und #45).

Jedes Konto hat eine feste, unsichtbare Kennung (K-…), die sich nie ändert; darauf verweisen Mitgliedschaften und
Verlauf. Die E-Mail-Adresse ist der Anmeldename: eindeutig (höchstens ein Konto je Adresse, ohne Unterschied von Groß-
und Kleinschreibung) und änderbar, aber nur mit einem Code an die neue Adresse und nur, wenn sie frei ist.

Angemeldet wird ohne Passwort: Wer seine Adresse eingibt, bekommt einen sechsstelligen Code per Mail (10 Minuten
gültig, einmalig, höchstens 5 Versuche). Das erste Anmelden legt das Konto an (freie Anmeldung). Ohne Einladung hat ein
Konto keine Reisen; Reisen anlegen darf es erst, wenn der Betreiber es freischaltet (es kann darum bitten).

Einladungen gelten für eine Reise und einen Personen-Schlüssel. Hat die eingeladene Adresse schon ein Konto, gilt die
Einladung sofort; sonst beim ersten Anmelden mit dieser Adresse. Der Link aus der Einladungsmail ist selbst ein
Nachweis: Wer ihn öffnet, darf sich dort auch mit einer anderen Adresse anmelden und bekommt die Rolle.
Die Rollen selbst stehen weiter in reise.yaml und einladungen.json; dieses Modul verknüpft nur Konto und Person.

Geheimnisse (Codes, Sitzungen, Einladungen) liegen nur als SHA-256 in der Datenbank. Antworten verraten nie, ob eine
Adresse ein Konto hat. Begrenzung: je Adresse 3 Codes in 15 Minuten, je IP 10 in der Stunde.

Ablage: <FR_KONTEN, sonst Seiten>/_konten/konten.db (SQLite, WAL), nur für den Betreiber lesbar.
Mail: FR_SMTP_HOST, FR_SMTP_PORT (587), FR_SMTP_USER, FR_SMTP_PASS, FR_ABSENDER; Links mit FR_BASIS.
      FR_MAIL_DATEI schreibt Mails stattdessen als JSON-Zeilen in eine Datei (Tests, Probebetrieb).

Aufrufe:
  python3 engine/konten.py liste                               alle Konten mit Reisen und Rechten
  python3 engine/konten.py anfragen                            offene Bitten „Reisen anlegen“
  python3 engine/konten.py freischalten <email> [--nein]       Reisen anlegen erlauben (oder Bitte ablehnen)
  python3 engine/konten.py betreiber <email>                   Betreiber-Recht geben (sieht Anfragen, schaltet frei)
  python3 engine/konten.py sperren|entsperren <email>          sperren meldet alle Geräte ab
  python3 engine/konten.py loeschen <email>                    Konto und Adresse löschen
  python3 engine/konten.py zusammenfuehren <von> <nach>        zwei Konten eines Menschen vereinen
  python3 engine/konten.py einladen <reise> <schluessel> <email> <rolle> <Name> <von>
"""
import datetime
import email.message
import hashlib
import json
import os
import re
import secrets
import smtplib
import sqlite3
import sys
import time
import urllib.parse
from contextlib import closing
from pathlib import Path

import instanz

EMAIL_MUSTER = re.compile(r"^[^@\s]{1,64}@[^@\s]+\.[^@\s]{2,}$")
REISE_MUSTER = re.compile(r"^[a-z0-9][a-z0-9-]{0,40}$")          # wie rueckmeldungen.REISE_MUSTER
PERSON_MUSTER = re.compile(r"^[a-z0-9][a-z0-9_-]{0,40}$")        # wie konnektor.PERSON_MUSTER
ROLLEN = ("reisend", "einbringer", "bestimmer")
RECHTE = ("reise_anlegen", "betreiber")
MAX_NAME = 80

CODE_MINUTEN = 10
CODE_VERSUCHE = 5
JE_ADRESSE = (3, 15 * 60)        # höchstens 3 Codes je Adresse in 15 Minuten
JE_IP = (10, 60 * 60)            # höchstens 10 Codes je IP in der Stunde
SITZUNG_TAGE = 365               # rollierend: jede Nutzung verlängert
EINLADUNG_TAGE = 30


class KontoFehler(Exception):
    """Fehler mit einem Satz, der so dem Menschen gezeigt werden kann."""


class NameNoetig(KontoFehler):
    """Neues Konto ohne Namen: Die Seite fragt „Wie heißt du?“ und schickt denselben Code noch einmal."""


def _jetzt():
    return time.time()


def _datum(t=None):
    return datetime.datetime.fromtimestamp(t if t is not None else _jetzt(), datetime.timezone.utc).isoformat(
        timespec="seconds")


def _hash(*teile):
    return hashlib.sha256("\x1f".join(teile).encode("utf-8")).hexdigest()


def pfad():
    return instanz.konten() / "konten.db"


SCHEMA = """
CREATE TABLE IF NOT EXISTS konten (
  id TEXT PRIMARY KEY, email TEXT NOT NULL UNIQUE, name TEXT NOT NULL DEFAULT '', rechte TEXT NOT NULL DEFAULT '',
  gesperrt INTEGER NOT NULL DEFAULT 0, angelegt TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS codes (
  email TEXT NOT NULL, zweck TEXT NOT NULL, hash TEXT NOT NULL, konto TEXT, ablauf REAL NOT NULL,
  versuche INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (email, zweck));
CREATE TABLE IF NOT EXISTS sitzungen (
  hash TEXT PRIMARY KEY, konto TEXT NOT NULL, geraet TEXT NOT NULL DEFAULT '', erstellt REAL NOT NULL,
  zuletzt REAL NOT NULL, ablauf REAL NOT NULL);
CREATE TABLE IF NOT EXISTS mitgliedschaften (
  konto TEXT NOT NULL, reise TEXT NOT NULL, schluessel TEXT NOT NULL, seit TEXT NOT NULL,
  PRIMARY KEY (konto, reise), UNIQUE (reise, schluessel));
CREATE TABLE IF NOT EXISTS einladungen (
  hash TEXT PRIMARY KEY, reise TEXT NOT NULL, schluessel TEXT NOT NULL, email TEXT NOT NULL, rolle TEXT NOT NULL,
  name TEXT NOT NULL, von TEXT NOT NULL, erstellt REAL NOT NULL, ablauf REAL NOT NULL, eingeloest REAL,
  konto TEXT);
CREATE TABLE IF NOT EXISTS anfragen (
  konto TEXT PRIMARY KEY, erstellt TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'offen', entschieden TEXT);
CREATE TABLE IF NOT EXISTS versand (schluessel TEXT NOT NULL, zeit REAL NOT NULL);
CREATE TABLE IF NOT EXISTS oauth_clients (
  client_id TEXT PRIMARY KEY, name TEXT NOT NULL DEFAULT '', redirect_uris TEXT NOT NULL, art TEXT NOT NULL,
  erstellt REAL NOT NULL);
CREATE TABLE IF NOT EXISTS oauth_codes (
  hash TEXT PRIMARY KEY, client_id TEXT NOT NULL, redirect_uri TEXT NOT NULL, challenge TEXT NOT NULL,
  scope TEXT NOT NULL, konto TEXT NOT NULL, ablauf REAL NOT NULL, benutzt REAL, familie TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS oauth_tokens (
  hash TEXT PRIMARY KEY, art TEXT NOT NULL, konto TEXT NOT NULL, client_id TEXT NOT NULL, scope TEXT NOT NULL,
  familie TEXT NOT NULL, ablauf REAL NOT NULL, benutzt REAL);
CREATE INDEX IF NOT EXISTS oauth_tokens_konto ON oauth_tokens (konto);
CREATE INDEX IF NOT EXISTS versand_schluessel ON versand (schluessel, zeit);
CREATE INDEX IF NOT EXISTS sitzungen_konto ON sitzungen (konto);
"""


def db():
    """Verbindung zur Kontendatenbank; legt sie beim ersten Mal an (Ordner 700, Datei 600)."""
    p = pfad()
    neu = not p.exists()
    if neu:
        p.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(p.parent, 0o700)
    v = sqlite3.connect(p, timeout=10)
    v.row_factory = sqlite3.Row
    v.execute("PRAGMA foreign_keys = ON")
    if neu:
        os.chmod(p, 0o600)
        v.execute("PRAGMA journal_mode = WAL")
    v.executescript(SCHEMA)
    return v


def dienst_geheimnis():
    """Gemeinsames Geheimnis von Konnektor und Rückmeldedienst (Header X-Frieda-Dienst). Nur wer es mitschickt, gilt
    beim Rückmeldedienst als Konnektor; alles andere als Seite (fail-closed). Liegt neben der Datenbank (600) und
    entsteht beim ersten Aufruf; beide Dienste laufen unter demselben Benutzer und lesen dieselbe Datei."""
    p = pfad().parent / "dienst-geheimnis"
    try:
        return p.read_text(encoding="ascii").strip()
    except FileNotFoundError:
        p.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(p.parent, 0o700)
        tmp = p.with_name(f"dienst-geheimnis.{os.getpid()}.tmp")
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="ascii") as f:
            f.write(secrets.token_urlsafe(32))
        try:
            os.link(tmp, p)          # atomar und nur, wenn noch keiner zuvorgekommen ist
        except FileExistsError:
            pass
        finally:
            tmp.unlink()
        return p.read_text(encoding="ascii").strip()


# ---------------------------------------------------------------- Adressen und Mail

def adresse(roh):
    """E-Mail-Adresse normalisieren (Leerzeichen weg, klein) oder KontoFehler."""
    e = (roh or "").strip().lower() if isinstance(roh, str) else ""
    if len(e) > 254 or not EMAIL_MUSTER.match(e):
        raise KontoFehler("Das sieht nicht wie eine E-Mail-Adresse aus.")
    return e


def name_pruefen(roh):
    n = " ".join((roh or "").split()) if isinstance(roh, str) else ""
    if not n or len(n) > MAX_NAME:
        raise KontoFehler(f"Bitte einen Namen mit höchstens {MAX_NAME} Zeichen angeben.")
    return n


def basis():
    return os.environ.get("FR_BASIS", "").rstrip("/")


def mail_senden(an, betreff, text):
    """Eine Mail verschicken (SMTP mit STARTTLS) oder, mit FR_MAIL_DATEI, in eine Datei schreiben."""
    datei = os.environ.get("FR_MAIL_DATEI")
    if datei:
        with open(datei, "a", encoding="utf-8") as f:
            f.write(json.dumps({"an": an, "betreff": betreff, "text": text}, ensure_ascii=False) + "\n")
        return
    host = os.environ.get("FR_SMTP_HOST")
    absender = os.environ.get("FR_ABSENDER")
    if not host or not absender:
        raise KontoFehler("Der Mailversand ist noch nicht eingerichtet. Bitte später noch einmal versuchen.")
    m = email.message.EmailMessage()
    m["From"], m["To"], m["Subject"] = absender, an, betreff
    m.set_content(text)
    try:
        with smtplib.SMTP(host, int(os.environ.get("FR_SMTP_PORT", "587")), timeout=20) as s:
            s.starttls()
            if os.environ.get("FR_SMTP_USER"):
                s.login(os.environ["FR_SMTP_USER"], os.environ.get("FR_SMTP_PASS", ""))
            s.send_message(m)
    except (OSError, smtplib.SMTPException) as f:
        raise KontoFehler("Die Mail ließ sich gerade nicht verschicken. Bitte gleich noch einmal versuchen.") from f


def _begrenzt(v, schluessel, grenze):
    anzahl, sekunden = grenze
    t = _jetzt()
    v.execute("DELETE FROM versand WHERE zeit < ?", (t - 24 * 3600,))
    n = v.execute("SELECT COUNT(*) FROM versand WHERE schluessel = ? AND zeit > ?",
                  (schluessel, t - sekunden)).fetchone()[0]
    return n >= anzahl


# ---------------------------------------------------------------- Codes

def code_anfordern(roh, ip="", zweck="anmelden", konto=None):
    """Schickt einen Anmeldecode an die Adresse. Die Antwort ist für bekannte und unbekannte Adressen gleich.
    zweck „adresse“: Code an eine neue Adresse für das Konto `konto` (nur, wenn die Adresse frei ist)."""
    e = adresse(roh)
    with closing(db()) as v, v:
        if zweck == "adresse":
            if not konto:
                raise KontoFehler("Zum Ändern der Adresse bitte zuerst anmelden.")
            belegt = v.execute("SELECT id FROM konten WHERE email = ?", (e,)).fetchone()
            if belegt:
                raise KontoFehler("Diese Adresse gehört schon zu einem Konto." if belegt["id"] != konto
                                  else "Das ist schon deine Adresse.")
        elif zweck != "anmelden":
            raise ValueError(zweck)
        if _begrenzt(v, "adresse:" + e, JE_ADRESSE) or (ip and _begrenzt(v, "ip:" + ip, JE_IP)):
            raise KontoFehler("Zu viele Codes in kurzer Zeit. Bitte in einer Viertelstunde noch einmal versuchen.")
        code = f"{secrets.randbelow(10 ** 6):06d}"
        v.execute("INSERT OR REPLACE INTO codes (email, zweck, hash, konto, ablauf, versuche) VALUES (?,?,?,?,?,0)",
                  (e, zweck, _hash(e, zweck, code), konto, _jetzt() + CODE_MINUTEN * 60))
        v.execute("INSERT INTO versand VALUES (?, ?)", ("adresse:" + e, _jetzt()))
        if ip:
            v.execute("INSERT INTO versand VALUES (?, ?)", ("ip:" + ip, _jetzt()))
    lesbar = f"{code[:3]} {code[3:]}"
    zeilen = [f"Dein Code für Frieda: {lesbar}", "",
              f"Gib ihn dort ein, wo du dich gerade anmeldest. Er gilt {CODE_MINUTEN} Minuten.", ""]
    if zweck == "anmelden" and basis():   # Link ohne Code: der Code gehört nicht in Protokolle und Verläufe
        zeilen += ["Zur Code-Eingabe auf diesem Gerät:",
                   f"{basis()}/anmelden?{urllib.parse.urlencode({'schritt': 'code', 'email': e})}", ""]
    zeilen += ["Hast du keinen Code angefordert, kannst du diese Mail einfach löschen."]
    betreff = f"Frieda: dein Code {lesbar}" if zweck == "anmelden" else f"Frieda: neue Adresse bestätigen ({lesbar})"
    mail_senden(e, betreff, "\n".join(zeilen))


def _code_einloesen(v, e, zweck, code):
    """Prüft einen Code und verbraucht ihn bei Erfolg. -> Zeile oder KontoFehler (für alle Fehler derselbe Satz)."""
    falsch = KontoFehler("Der Code stimmt nicht oder ist abgelaufen. Bitte einen neuen anfordern.")
    z = v.execute("SELECT * FROM codes WHERE email = ? AND zweck = ?", (e, zweck)).fetchone()
    if not z:
        raise falsch
    code = re.sub(r"\s", "", code or "") if isinstance(code, str) else ""
    if z["ablauf"] < _jetzt() or z["versuche"] >= CODE_VERSUCHE:
        v.execute("DELETE FROM codes WHERE email = ? AND zweck = ?", (e, zweck))
        v.commit()      # sonst nähme der Fehler das Löschen mit zurück
        raise falsch
    if not secrets.compare_digest(z["hash"], _hash(e, zweck, code)):
        v.execute("UPDATE codes SET versuche = versuche + 1 WHERE email = ? AND zweck = ?", (e, zweck))
        v.commit()      # Fehlversuch zählt, auch wenn der Fehler die Verbindung zurückrollt
        raise falsch
    v.execute("DELETE FROM codes WHERE email = ? AND zweck = ?", (e, zweck))
    return z


# ---------------------------------------------------------------- Konten und Sitzungen

def _konto_dict(z):
    if not z:
        return None
    return {"id": z["id"], "email": z["email"], "name": z["name"], "gesperrt": bool(z["gesperrt"]),
            "rechte": [r for r in z["rechte"].split(",") if r], "angelegt": z["angelegt"]}


def konto(kid):
    with closing(db()) as v:
        return _konto_dict(v.execute("SELECT * FROM konten WHERE id = ?", (kid,)).fetchone())


def konto_per_email(roh):
    with closing(db()) as v:
        return _konto_dict(v.execute("SELECT * FROM konten WHERE email = ?", (adresse(roh),)).fetchone())


def _sitzung_anlegen(v, kid, geraet):
    token = secrets.token_urlsafe(32)
    t = _jetzt()
    v.execute("INSERT INTO sitzungen VALUES (?,?,?,?,?,?)",
              (_hash("sitzung", token), kid, (geraet or "")[:120], t, t, t + SITZUNG_TAGE * 86400))
    return token


def anmelden(roh, code, name=None, geraet="", einladung=None):
    """Code prüfen, Konto finden oder anlegen, Einladungen einlösen, Sitzung anlegen.
    -> (sitzungs_token, konto). Ein neues Konto braucht einen Namen (oder eine Einladung, die ihn mitbringt);
    fehlt er, kommt NameNoetig und der Code bleibt gültig."""
    e = adresse(roh)
    with closing(db()) as v, v:
        _code_einloesen(v, e, "anmelden", code)
        z = v.execute("SELECT * FROM konten WHERE email = ?", (e,)).fetchone()
        if not z:
            vorschlag = None
            if einladung:
                ez = _einladung_zeile(v, einladung)
                vorschlag = ez["name"] if ez else None
            if not vorschlag:
                ez = v.execute("SELECT name FROM einladungen WHERE email = ? AND eingeloest IS NULL AND ablauf > ? "
                               "ORDER BY erstellt", (e, _jetzt())).fetchone()
                vorschlag = ez["name"] if ez else None
            if not (name or vorschlag):
                raise NameNoetig("Wie heißt du? Der Name steht bei deinen Beiträgen.")   # Code bleibt gültig
            n = name_pruefen(name or vorschlag)
            kid = "K-" + secrets.token_hex(8)
            v.execute("INSERT INTO konten (id, email, name, angelegt) VALUES (?,?,?,?)", (kid, e, n, _datum()))
            z = v.execute("SELECT * FROM konten WHERE id = ?", (kid,)).fetchone()
        if z["gesperrt"]:
            raise KontoFehler("Dieses Konto ist gesperrt. Bitte wende dich an den Betreiber.")
        # Einladungen an diese Adresse gelten beim Anmelden (Entscheidung 27.10.2026), dazu der Link aus der Mail
        for ez in v.execute("SELECT hash FROM einladungen WHERE email = ? AND eingeloest IS NULL AND ablauf > ?",
                            (e, _jetzt())).fetchall():
            _einloesen(v, ez["hash"], z["id"])
        if einladung:
            ez = _einladung_zeile(v, einladung)
            if ez and ez["eingeloest"] is None:
                _einloesen(v, ez["hash"], z["id"])
        return _sitzung_anlegen(v, z["id"], geraet), _konto_dict(z)


def sitzung(token):
    """Konto zu einem Sitzungs-Token oder None (abgelaufen, abgemeldet, gesperrt). Verlängert rollierend."""
    if not isinstance(token, str) or not 20 <= len(token) <= 100:
        return None
    h = _hash("sitzung", token)
    with closing(db()) as v, v:
        z = v.execute("SELECT s.ablauf, s.zuletzt, k.* FROM sitzungen s JOIN konten k ON k.id = s.konto "
                      "WHERE s.hash = ?", (h,)).fetchone()
        if not z or z["ablauf"] < _jetzt():
            if z:
                v.execute("DELETE FROM sitzungen WHERE hash = ?", (h,))
            return None
        if z["gesperrt"]:
            return None
        if _jetzt() - z["zuletzt"] > 86400:
            v.execute("UPDATE sitzungen SET zuletzt = ?, ablauf = ? WHERE hash = ?",
                      (_jetzt(), _jetzt() + SITZUNG_TAGE * 86400, h))
        return _konto_dict(z)


def abmelden(token):
    with closing(db()) as v, v:
        v.execute("DELETE FROM sitzungen WHERE hash = ?", (_hash("sitzung", token or ""),))


def alle_abmelden(kid):
    """Meldet das Konto auf allen Geräten ab (Sitzungen; ab J3 auch die Tokens der Claude-App)."""
    with closing(db()) as v, v:
        _widerrufen(v, kid)


def _widerrufen(v, kid):
    v.execute("DELETE FROM sitzungen WHERE konto = ?", (kid,))
    v.execute("DELETE FROM oauth_tokens WHERE konto = ?", (kid,))
    v.execute("DELETE FROM oauth_codes WHERE konto = ?", (kid,))


def geraete(kid):
    with closing(db()) as v:
        return [{"geraet": z["geraet"], "seit": _datum(z["erstellt"]), "zuletzt": _datum(z["zuletzt"])}
                for z in v.execute("SELECT * FROM sitzungen WHERE konto = ? ORDER BY zuletzt DESC", (kid,))]


def name_setzen(kid, roh):
    n = name_pruefen(roh)
    with closing(db()) as v, v:
        v.execute("UPDATE konten SET name = ? WHERE id = ?", (n, kid))
    return n


def adresse_aendern(kid, roh, code):
    """Neue Adresse übernehmen, wenn der Code an sie stimmt und sie noch frei ist."""
    e = adresse(roh)
    with closing(db()) as v, v:
        z = _code_einloesen(v, e, "adresse", code)
        if z["konto"] != kid:
            raise KontoFehler("Der Code stimmt nicht oder ist abgelaufen. Bitte einen neuen anfordern.")
        try:
            v.execute("UPDATE konten SET email = ? WHERE id = ?", (e, kid))
        except sqlite3.IntegrityError:
            raise KontoFehler("Diese Adresse gehört schon zu einem Konto.") from None
    return e


def loeschen(kid):
    """Konto und Adresse löschen (auf Wunsch der Person). Verlaufseinträge der Reisen behalten den Namen."""
    with closing(db()) as v, v:
        _widerrufen(v, kid)
        for t in ("mitgliedschaften", "anfragen"):
            v.execute(f"DELETE FROM {t} WHERE konto = ?", (kid,))
        v.execute("DELETE FROM konten WHERE id = ?", (kid,))


def sperren(kid, gesperrt=True):
    with closing(db()) as v, v:
        v.execute("UPDATE konten SET gesperrt = ? WHERE id = ?", (1 if gesperrt else 0, kid))
        if gesperrt:
            _widerrufen(v, kid)


def zusammenfuehren(von, nach):
    """Zwei Konten eines Menschen vereinen: Mitgliedschaften und Rechte gehen an `nach`, `von` wird gelöscht.
    Ist `nach` in einer Reise schon Mitglied, bleibt dessen Personen-Schlüssel."""
    if von == nach:
        raise KontoFehler("Das ist dasselbe Konto.")
    with closing(db()) as v, v:
        a = v.execute("SELECT * FROM konten WHERE id = ?", (von,)).fetchone()
        b = v.execute("SELECT * FROM konten WHERE id = ?", (nach,)).fetchone()
        if not a or not b:
            raise KontoFehler("Konto nicht gefunden.")
        for m in v.execute("SELECT * FROM mitgliedschaften WHERE konto = ?", (von,)).fetchall():
            v.execute("DELETE FROM mitgliedschaften WHERE konto = ? AND reise = ?", (von, m["reise"]))
            v.execute("INSERT OR IGNORE INTO mitgliedschaften VALUES (?,?,?,?)",
                      (nach, m["reise"], m["schluessel"], m["seit"]))
        rechte = sorted(set(filter(None, (a["rechte"] + "," + b["rechte"]).split(","))))
        v.execute("UPDATE konten SET rechte = ? WHERE id = ?", (",".join(rechte), nach))
        v.execute("DELETE FROM anfragen WHERE konto = ?", (von,))
        _widerrufen(v, von)
        v.execute("DELETE FROM konten WHERE id = ?", (von,))


# ---------------------------------------------------------------- Rechte und Anfragen

def recht(k, r):
    return bool(k) and not k.get("gesperrt") and r in k.get("rechte", [])


def recht_setzen(kid, r, an=True):
    if r not in RECHTE:
        raise ValueError(r)
    with closing(db()) as v, v:
        z = v.execute("SELECT rechte FROM konten WHERE id = ?", (kid,)).fetchone()
        if not z:
            raise KontoFehler("Konto nicht gefunden.")
        rechte = set(filter(None, z["rechte"].split(",")))
        rechte = rechte | {r} if an else rechte - {r}
        v.execute("UPDATE konten SET rechte = ? WHERE id = ?", (",".join(sorted(rechte)), kid))


def reisen_anlegen_anfragen(kid):
    """Bitte „Ich möchte Reisen anlegen“. -> 'offen' | 'schon_erlaubt' | 'abgelehnt' (eine Ablehnung bleibt)."""
    with closing(db()) as v, v:
        k = v.execute("SELECT rechte FROM konten WHERE id = ?", (kid,)).fetchone()
        if not k:
            raise KontoFehler("Konto nicht gefunden.")
        if "reise_anlegen" in k["rechte"].split(","):
            return "schon_erlaubt"
        z = v.execute("SELECT status FROM anfragen WHERE konto = ?", (kid,)).fetchone()
        if z:
            return z["status"]
        v.execute("INSERT INTO anfragen (konto, erstellt) VALUES (?, ?)", (kid, _datum()))
        return "offen"


def anfragen(nur_offen=True):
    with closing(db()) as v:
        sql = "SELECT a.*, k.email, k.name FROM anfragen a JOIN konten k ON k.id = a.konto"
        sql += " WHERE a.status = 'offen'" if nur_offen else ""
        return [dict(z) for z in v.execute(sql + " ORDER BY a.erstellt")]


def freischalten(kid, ja=True):
    """Bitte entscheiden (Betreiber): ja = Recht reise_anlegen, nein = Bitte abgelehnt."""
    recht_setzen(kid, "reise_anlegen", ja)
    with closing(db()) as v, v:
        v.execute("INSERT INTO anfragen (konto, erstellt, status, entschieden) VALUES (?,?,?,?) "
                  "ON CONFLICT (konto) DO UPDATE SET status = excluded.status, entschieden = excluded.entschieden",
                  (kid, _datum(), "freigeschaltet" if ja else "abgelehnt", _datum()))


# ---------------------------------------------------------------- Mitgliedschaften und Einladungen

def mitgliedschaften(kid):
    with closing(db()) as v:
        return [dict(z) for z in v.execute("SELECT reise, schluessel, seit FROM mitgliedschaften WHERE konto = ? "
                                           "ORDER BY seit", (kid,))]


def mitglied(kid, reise):
    """Personen-Schlüssel des Kontos in der Reise oder None."""
    with closing(db()) as v:
        z = v.execute("SELECT schluessel FROM mitgliedschaften WHERE konto = ? AND reise = ?",
                      (kid, reise)).fetchone()
        return z["schluessel"] if z else None


def konto_von_person(reise, schluessel):
    with closing(db()) as v:
        z = v.execute("SELECT konto FROM mitgliedschaften WHERE reise = ? AND schluessel = ?",
                      (reise, schluessel)).fetchone()
        return z["konto"] if z else None


def verknuepfen(kid, reise, schluessel):
    """Konto direkt mit einer Person der Reise verknüpfen (z. B. wer eine Reise anlegt, ist dort Bestimmer)."""
    if not REISE_MUSTER.match(reise or "") or not PERSON_MUSTER.match(schluessel or ""):
        raise KontoFehler("Reise oder Person ungültig.")
    with closing(db()) as v, v:
        if not v.execute("SELECT id FROM konten WHERE id = ?", (kid,)).fetchone():
            raise KontoFehler("Konto nicht gefunden.")
        belegt = v.execute("SELECT konto FROM mitgliedschaften WHERE reise = ? AND schluessel = ?",
                           (reise, schluessel)).fetchone()
        if belegt and belegt["konto"] != kid:
            raise KontoFehler("Diese Person ist in der Reise schon mit einem anderen Konto verknüpft.")
        v.execute("INSERT OR IGNORE INTO mitgliedschaften VALUES (?,?,?,?)", (kid, reise, schluessel, _datum()))


def entfernen(reise, schluessel):
    """Nimmt die Person aus der Reise (Verknüpfung weg, offene Einladungen ungültig). -> ob es etwas gab."""
    with closing(db()) as v, v:
        n = v.execute("DELETE FROM mitgliedschaften WHERE reise = ? AND schluessel = ?", (reise, schluessel)).rowcount
        n += v.execute("DELETE FROM einladungen WHERE reise = ? AND schluessel = ? AND eingeloest IS NULL",
                       (reise, schluessel)).rowcount
        return n > 0


def _einladung_zeile(v, token):
    if not isinstance(token, str) or not 20 <= len(token) <= 100:
        return None
    z = v.execute("SELECT * FROM einladungen WHERE hash = ?", (_hash("einladung", token),)).fetchone()
    return z if z and z["ablauf"] >= _jetzt() else None


def _einloesen(v, h, kid):
    z = v.execute("SELECT * FROM einladungen WHERE hash = ?", (h,)).fetchone()
    belegt = v.execute("SELECT konto FROM mitgliedschaften WHERE reise = ? AND schluessel = ?",
                       (z["reise"], z["schluessel"])).fetchone()
    schon = v.execute("SELECT schluessel FROM mitgliedschaften WHERE konto = ? AND reise = ?",
                      (kid, z["reise"])).fetchone()
    if not belegt and not schon:
        v.execute("INSERT INTO mitgliedschaften VALUES (?,?,?,?)", (kid, z["reise"], z["schluessel"], _datum()))
    v.execute("UPDATE einladungen SET eingeloest = ?, konto = ? WHERE hash = ?", (_jetzt(), kid, h))


def einladung(token):
    """Einladung zum Link aus der Mail (noch gültig) oder None: reise, schluessel, name, rolle, email, eingeloest."""
    with closing(db()) as v:
        z = _einladung_zeile(v, token)
        if not z:
            return None
        return {k: z[k] for k in ("reise", "schluessel", "name", "rolle", "email", "von")} | {
            "eingeloest": z["eingeloest"] is not None}


def einladung_einloesen(token, kid):
    """Link aus der Einladungsmail mit einem angemeldeten Konto einlösen (auch mit anderer Adresse)."""
    with closing(db()) as v, v:
        z = _einladung_zeile(v, token)
        if not z or z["eingeloest"] is not None:
            raise KontoFehler("Diese Einladung ist abgelaufen oder schon benutzt.")
        _einloesen(v, z["hash"], kid)
        return z["reise"]


def einladen(reise, schluessel, roh, rolle, name, von, titel=None, seite=None):
    """Lädt eine Adresse in eine Reise ein und schickt die Mail. Hat die Adresse schon ein Konto, gilt die
    Einladung sofort. -> {"sofort": bool}. Der Link in der Mail ist ein Nachweis und bleibt geheim."""
    if not REISE_MUSTER.match(reise or "") or not PERSON_MUSTER.match(schluessel or ""):
        raise KontoFehler("Reise oder Person ungültig.")
    if rolle not in ROLLEN:
        raise KontoFehler("Unbekannte Rolle.")
    e, n, von = adresse(roh), name_pruefen(name), name_pruefen(von)
    token = secrets.token_urlsafe(32)
    with closing(db()) as v, v:
        if _begrenzt(v, "einladung:" + reise, (50, 24 * 3600)):
            raise KontoFehler("Heute wurden für diese Reise schon sehr viele Einladungen verschickt.")
        belegt = v.execute("SELECT k.email FROM mitgliedschaften m JOIN konten k ON k.id = m.konto "
                           "WHERE m.reise = ? AND m.schluessel = ?", (reise, schluessel)).fetchone()
        if belegt and belegt["email"] != e:
            raise KontoFehler("Diese Person ist in der Reise schon mit einem anderen Konto verknüpft.")
        v.execute("INSERT INTO einladungen (hash, reise, schluessel, email, rolle, name, von, erstellt, ablauf) "
                  "VALUES (?,?,?,?,?,?,?,?,?)", (_hash("einladung", token), reise, schluessel, e, rolle, n, von,
                                                 _jetzt(), _jetzt() + EINLADUNG_TAGE * 86400))
        v.execute("INSERT INTO versand VALUES (?, ?)", ("einladung:" + reise, _jetzt()))
        k = v.execute("SELECT id, gesperrt FROM konten WHERE email = ?", (e,)).fetchone()
        sofort = bool(k and not k["gesperrt"])
        if sofort:
            _einloesen(v, _hash("einladung", token), k["id"])
    titel = titel or reise
    rolle_text = {"reisend": "liest mit", "einbringer": "bringst ein", "bestimmer": "bestimmst mit"}[rolle]
    zeilen = [f"Hallo {n},", "", f"{von} hat dich zur Reise „{titel}“ eingeladen (du {rolle_text}).", ""]
    if sofort:
        zeilen += ["Die Reise steht ab jetzt bei deinen Reisen, wenn du dich bei Frieda anmeldest."]
    else:
        zeilen += ["Mitmachen kannst du nach dem Anmelden mit dieser Adresse oder über diesen Link "
                   f"({EINLADUNG_TAGE} Tage gültig, auch wenn du lieber eine andere Adresse nutzt):"]
        if basis():
            zeilen += [f"{basis()}/einladung/{token}"]
    if seite:
        zeilen += ["", "Lesen geht ohne Anmeldung:", seite]
    zeilen += ["", "Frieda ist der Reiseassistent eurer Reisegruppe. Kennst du die Person nicht, lösche diese Mail."]
    mail_senden(e, f"Frieda: Einladung zu „{titel}“", "\n".join(zeilen))
    return {"sofort": sofort}


# ---------------------------------------------------------------- OAuth für die Claude-App (Paket J3)
# Die Endpunkte stehen in engine/oauth.py; hier nur die Ablage. Codes 5 Minuten, Access-Tokens 1 Stunde, Refresh-Tokens
# 90 Tage mit Rotation: Wird ein schon benutzter Refresh-Token noch einmal vorgelegt (gestohlen?), endet die ganze
# Familie. Ein zweimal eingelöster Code widerruft ebenso alles, was aus ihm entstand.
OAUTH_CODE_SEKUNDEN = 300
ACCESS_SEKUNDEN = 3600
REFRESH_TAGE = 90


def oauth_client(client_id):
    with closing(db()) as v:
        z = v.execute("SELECT * FROM oauth_clients WHERE client_id = ?", (client_id or "",)).fetchone()
        return {"client_id": z["client_id"], "name": z["name"], "redirect_uris": json.loads(z["redirect_uris"]),
                "art": z["art"], "erstellt": z["erstellt"]} if z else None


def oauth_client_speichern(client_id, name, redirect_uris, art):
    with closing(db()) as v, v:
        v.execute("INSERT OR REPLACE INTO oauth_clients VALUES (?,?,?,?,?)",
                  (client_id, (name or "")[:200], json.dumps(redirect_uris), art, _jetzt()))


def oauth_registrierung_erlaubt(ip):
    """Begrenzung der Client-Registrierung je IP (20 in der Stunde)."""
    with closing(db()) as v, v:
        if _begrenzt(v, "register:" + (ip or "?"), (20, 3600)):
            return False
        v.execute("INSERT INTO versand VALUES (?, ?)", ("register:" + (ip or "?"), _jetzt()))
        return True


def oauth_code_anlegen(client_id, redirect_uri, challenge, scope, kid):
    code = secrets.token_urlsafe(32)
    with closing(db()) as v, v:
        v.execute("INSERT INTO oauth_codes VALUES (?,?,?,?,?,?,?,NULL,?)",
                  (_hash("code", code), client_id, redirect_uri, challenge, scope, kid,
                   _jetzt() + OAUTH_CODE_SEKUNDEN, secrets.token_hex(8)))
    return code


def _tokens_ausstellen(v, kid, client_id, scope, familie):
    access, refresh = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    t = _jetzt()
    v.execute("INSERT INTO oauth_tokens VALUES (?,?,?,?,?,?,?,NULL)",
              (_hash("access", access), "access", kid, client_id, scope, familie, t + ACCESS_SEKUNDEN))
    v.execute("INSERT INTO oauth_tokens VALUES (?,?,?,?,?,?,?,NULL)",
              (_hash("refresh", refresh), "refresh", kid, client_id, scope, familie, t + REFRESH_TAGE * 86400))
    return {"access_token": access, "token_type": "Bearer", "expires_in": ACCESS_SEKUNDEN, "refresh_token": refresh,
            "scope": scope}


def oauth_code_einloesen(code, client_id, redirect_uri, pruefen):
    """Code gegen Tokens tauschen. pruefen(challenge) -> bool prüft den PKCE-Verifier. -> Antwort oder None (invalid_grant)."""
    with closing(db()) as v, v:
        z = v.execute("SELECT * FROM oauth_codes WHERE hash = ?", (_hash("code", code or ""),)).fetchone()
        if not z:
            return None
        if z["benutzt"] is not None:                     # zweites Einlösen: alles aus diesem Code widerrufen
            v.execute("DELETE FROM oauth_tokens WHERE familie = ?", (z["familie"],))
            return None
        v.execute("UPDATE oauth_codes SET benutzt = ? WHERE hash = ?", (_jetzt(), z["hash"]))
        k = v.execute("SELECT gesperrt FROM konten WHERE id = ?", (z["konto"],)).fetchone()
        if (z["ablauf"] < _jetzt() or z["client_id"] != client_id or z["redirect_uri"] != redirect_uri
                or not pruefen(z["challenge"]) or not k or k["gesperrt"]):
            return None
        return _tokens_ausstellen(v, z["konto"], client_id, z["scope"], z["familie"])


def oauth_erneuern(refresh, client_id):
    """Refresh-Token einlösen (Rotation). -> neue Tokens oder None (invalid_grant)."""
    with closing(db()) as v, v:
        z = v.execute("SELECT * FROM oauth_tokens WHERE hash = ? AND art = 'refresh'",
                      (_hash("refresh", refresh or ""),)).fetchone()
        if not z:
            return None
        if z["benutzt"] is not None:                     # schon rotiert: Diebstahl angenommen, Familie widerrufen
            v.execute("DELETE FROM oauth_tokens WHERE familie = ?", (z["familie"],))
            return None
        k = v.execute("SELECT gesperrt FROM konten WHERE id = ?", (z["konto"],)).fetchone()
        if z["ablauf"] < _jetzt() or z["client_id"] != client_id or not k or k["gesperrt"]:
            return None
        v.execute("UPDATE oauth_tokens SET benutzt = ? WHERE hash = ?", (_jetzt(), z["hash"]))
        v.execute("DELETE FROM oauth_tokens WHERE familie = ? AND art = 'access'", (z["familie"],))
        return _tokens_ausstellen(v, z["konto"], client_id, z["scope"], z["familie"])


def oauth_konto(access):
    """Konto zu einem Access-Token oder None (unbekannt, abgelaufen, gesperrt)."""
    if not isinstance(access, str) or not 20 <= len(access) <= 200:
        return None
    with closing(db()) as v:
        z = v.execute("SELECT t.ablauf AS t_ablauf, k.* FROM oauth_tokens t JOIN konten k ON k.id = t.konto "
                      "WHERE t.hash = ? AND t.art = 'access'", (_hash("access", access),)).fetchone()
        if not z or z["t_ablauf"] < _jetzt() or z["gesperrt"]:
            return None
        return _konto_dict(z)


# ---------------------------------------------------------------- Befehle für den Betreiber

def liste():
    with closing(db()) as v:
        for k in v.execute("SELECT * FROM konten ORDER BY angelegt"):
            reisen = ", ".join(f"{m['reise']}:{m['schluessel']}" for m in
                               v.execute("SELECT * FROM mitgliedschaften WHERE konto = ?", (k["id"],)))
            n = v.execute("SELECT COUNT(*) FROM sitzungen WHERE konto = ?", (k["id"],)).fetchone()[0]
            print(f"{k['id']}  {k['email']}  {k['name']}  rechte: {k['rechte'] or '-'}"
                  f"{'  GESPERRT' if k['gesperrt'] else ''}  geräte: {n}  reisen: {reisen or '-'}")


def _per_email(e):
    k = konto_per_email(e)
    if not k:
        raise KontoFehler(f"Kein Konto mit der Adresse {e}.")
    return k


def main(a):
    try:
        if a[:1] == ["liste"]:
            liste()
        elif a[:1] == ["anfragen"]:
            for z in anfragen():
                print(f"{z['erstellt']}  {z['email']}  {z['name']}")
        elif a[:1] == ["freischalten"] and len(a) in (2, 3):
            freischalten(_per_email(a[1])["id"], ja=a[2:] != ["--nein"])
        elif a[:1] == ["betreiber"] and len(a) == 2:
            recht_setzen(_per_email(a[1])["id"], "betreiber")
        elif a[:1] in (["sperren"], ["entsperren"]) and len(a) == 2:
            sperren(_per_email(a[1])["id"], a[0] == "sperren")
        elif a[:1] == ["loeschen"] and len(a) == 2:
            loeschen(_per_email(a[1])["id"])
        elif a[:1] == ["zusammenfuehren"] and len(a) == 3:
            zusammenfuehren(_per_email(a[1])["id"], _per_email(a[2])["id"])
        elif a[:1] == ["einladen"] and len(a) == 7:
            print("gilt sofort" if einladen(*a[1:])["sofort"] else "Einladung verschickt")
        else:
            print(__doc__)
            return 1
    except KontoFehler as f:
        print(f"FEHLER: {f}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
