#!/usr/bin/env python3
"""Push-Nachrichten aufs Handy (Issue #21, Stufe 2; docs/waechter.md „Meldekanäle“, docs/betrieb.md „Push“).

Wer angemeldet ist, schaltet Benachrichtigungen je Gerät auf „Mein Konto“ ein (Frieda-App, engine/app/; ältere Abos der
Reiseseiten gelten weiter). Das Gerät schließt beim Push-Dienst seines Browsers ein Abo ab und gibt es Friedas Konto
(konten.push_abo_speichern). Dieser
Dienst liest danach, was in den Reisen neu ist, und schickt es an die Geräte der Personen:

  meldung       Meldungen an Personen (meldungen.jsonl: Wächter und Erinnerer, Konflikte, Rot beim Veröffentlichen)
  rueckmeldung  neue Rückmeldungen, Fragen und Wünsche von der Seite (eingang.jsonl), an die Organisator:innen
  aufgabe       eine Aufgabe ist dir neu zugewiesen (aufgaben.json, Feld zustaendig), nicht wenn du es selbst warst
  version       ein neues Release der Software ist veröffentlicht (Fuß der Seite, data-release); Tippen aktualisiert

Was jemand bekommt, stellt die Person auf „Mein Konto“ ein, für alle Reisen gleich: welche Arten und eine Ruhezeit auf
der Uhr ihres Geräts (Vorgabe 21:30 bis 7:00). Was in der Ruhezeit anfällt, wartet bis zu ihrem Ende. Was zur selben
Zeit für dieselbe Reise wartet, kommt als eine Nachricht („3 Neuigkeiten“). Eine Reise ohne Kanal push in
regeln.meldekanal schickt nichts. Beim ersten Lauf merkt sich der Dienst nur den Stand; Altes wird nie nachgeschickt.

Stufen (#517, Product Owner 11.11.2026): Jede Nachricht gehört zu einer Gruppe (KATEGORIEN). „wichtig“ (Status fällig,
Konflikt, Frist überfällig, Veröffentlichen rot) kommt sofort aufs Handy und, je nach Einstellung, nach einem Tag ohne
Wirkung und ohne Gerät mit Benachrichtigungen (Vorgabe), sofort oder nie per Mail (Kanal mail der Reise). „rueckmeldungen“
(Rückmeldungen, Aufgaben, Anfragen, Hinweise) und „fristen“ (Frist naht, ab, Storno, Zahlung) kommen aufs Handy und auf
Wunsch als tägliche Zusammenfassung per Mail. „leise“ (Prüfungen veränderlicher Angaben, neue Versionen) steht nur auf
der Seite, unter Mein Konto und in der Claude-App; aufs Handy nur, wenn die Person es einschaltet.

Frieda enthält keine eigene KI (ADR-0001): Der Dienst liest und stellt zu, er deutet nichts und ändert keine Reise.
Versand über Web Push (RFC 8030/8291/8292) mit pywebpush (MPL-2.0, engine/requirements.txt). Darum läuft er mit dem
Python der Software (FR_PYTHON), nicht mit dem des Systems; alles außer dem Versand nutzt nur die Standardbibliothek,
damit Rückmeldedienst und Konnektor dieses Modul für Einstellungen und Ruhezeiten laden können.

Aufrufe:
  python3 engine/push.py dienst                       Dienst: alle PAUSE Sekunden sammeln und zustellen
  python3 engine/push.py lauf                         ein Durchgang
  python3 engine/push.py schluessel                   VAPID-Schlüssel anlegen (falls nötig) und den öffentlichen zeigen
  python3 engine/push.py probe <email>                Probenachricht an die Geräte eines Kontos
Umgebung: RM_ABLAGE, RM_SEITEN, FR_KONTEN (Standard aus engine/instanz.py), KN_SEITENLINKS, FR_BASIS
"""
import base64
import datetime
import html
import json
import os
import re
import sys
import time
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import instanz  # noqa: E402
import konten  # noqa: E402
import reise as rg  # noqa: E402
import rueckmeldungen as rm  # noqa: E402
import texte  # noqa: E402

ARTEN = ("meldung", "rueckmeldung", "aufgabe", "version")     # Arten der Warteschlange (Inhalt und Ziel der Nachricht)
KATEGORIEN = ("wichtig", "rueckmeldungen", "fristen", "leise")  # Gruppen der Einstellungen (#517)
PUSH_VORGABE = {"wichtig": True, "rueckmeldungen": True, "fristen": True, "leise": False}
MAIL_WERTE = {"wichtig": ("nach_tag", "sofort", "nie"), "rueckmeldungen": ("nie", "taeglich"), "fristen": ("nie", "taeglich")}
ZUSAMMENFASSUNG_UM = "07:30"  # tägliche Zusammenfassung ab dieser Uhrzeit auf der Uhr der Person
RUHE_VORGABE = ("21:30", "07:00")
UHRZEIT = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")
PAUSE = 20                    # Sekunden zwischen zwei Durchgängen des Dienstes
MAX_ALTER = 36 * 3600         # was so lange nicht zugestellt werden konnte, fällt weg (auch nach einer langen Ruhezeit)
MAX_VERSUCHE = 5              # Fehlversuche je Nachricht (Push-Dienst nicht erreichbar), dann aufgeben
TTL = 12 * 3600               # so lange hält der Push-Dienst eine Nachricht für ein ausgeschaltetes Gerät
MAX_TEXT = 240                # Zeichen im Text einer Nachricht (Telefone kürzen ohnehin)
OFFEN = ("offen", "in_arbeit")
MAIL_NACH = 24 * 3600         # so lange nach einem Statushinweis ohne Wechsel kommt er per Mail (#513)
MAIL_BIS = 3 * 86400          # ältere Hinweise gehen nicht mehr per Mail (etwa nach einer Pause des Dienstes)
MAIL_VERSUCHE = 3             # Fehlversuche je Mail, dann aufgeben
MAIL_PAUSE = 3600             # Sekunden zwischen zwei Versuchen


# ---------- Einstellungen und Ruhezeit (nur Standardbibliothek) ----------

def einstellungen(roh):
    """Einstellungen eines Kontos bereinigt: {push: {kategorie: bool}, mail: {kategorie: wert}, ruhe_von: "HH:MM" | "",
    ruhe_bis: "HH:MM" | ""}. Unbekanntes fällt weg; leere Ruhezeit (beide leer) heißt: keine. Alte Einstellungen (arten,
    bis #517) gelten weiter: meldung schaltet wichtig und fristen, rueckmeldung oder aufgabe die Rückmeldungen."""
    roh = roh if isinstance(roh, dict) else {}
    alt = roh.get("arten") if isinstance(roh.get("arten"), list) else None
    vorgabe = dict(PUSH_VORGABE)
    if alt is not None:
        vorgabe.update(wichtig="meldung" in alt, fristen="meldung" in alt,
                       rueckmeldungen="rueckmeldung" in alt or "aufgabe" in alt)
    push_roh = roh.get("push") if isinstance(roh.get("push"), dict) else {}
    push_ = {k: push_roh[k] if isinstance(push_roh.get(k), bool) else vorgabe[k] for k in KATEGORIEN}
    mail_roh = roh.get("mail") if isinstance(roh.get("mail"), dict) else {}
    mail = {k: mail_roh.get(k) if mail_roh.get(k) in werte else werte[0] for k, werte in MAIL_WERTE.items()}
    von, bis = roh.get("ruhe_von", RUHE_VORGABE[0]), roh.get("ruhe_bis", RUHE_VORGABE[1])
    von = von if isinstance(von, str) and UHRZEIT.match(von) else ""
    bis = bis if isinstance(bis, str) and UHRZEIT.match(bis) else ""
    if not von or not bis or von == bis:
        von = bis = ""
    return {"push": push_, "mail": mail, "ruhe_von": von, "ruhe_bis": bis}


def kategorie(art, m=None):
    """Gruppe einer Nachricht (#517): art der Warteschlange, bei art meldung dazu die Meldung (meldungen.jsonl)."""
    if art in ("rueckmeldung", "aufgabe"):
        return "rueckmeldungen"
    if art == "version":
        return "leise"
    m = m or {}
    if m.get("art") in ("status", "konflikt", "betrieb"):
        return "wichtig"
    if m.get("art") == "erinnerung":
        return "wichtig" if str(m.get("schluessel") or "").startswith("ueberfaellig:") else "fristen"
    if m.get("art") == "pruefung":
        return "leise"
    return "rueckmeldungen"


def einstellungen_von(kid, neu=None):
    """Einstellungen eines Kontos (bereinigt); mit neu: bereinigt speichern."""
    if neu is not None:
        return konten.push_einstellungen(kid, einstellungen(neu))
    return einstellungen(konten.push_einstellungen(kid))


def _minuten(hhmm):
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def ortszeit(zeitpunkt, zone):
    """Zeitpunkt (UTC) auf der Uhr des Geräts; unbekannte Zone: UTC."""
    try:
        from zoneinfo import ZoneInfo
        return zeitpunkt.astimezone(ZoneInfo(zone)) if zone else zeitpunkt
    except (ImportError, ValueError, KeyError, OSError):
        return zeitpunkt


def ruhig(einst, zeitpunkt, zone):
    """Liegt der Zeitpunkt in der Ruhezeit der Person (auf der Uhr ihres Geräts)? Eine Ruhezeit über Mitternacht
    (21:30 bis 7:00) gilt von abends bis morgens."""
    if not einst["ruhe_von"]:
        return False
    jetzt = ortszeit(zeitpunkt, zone)
    m = jetzt.hour * 60 + jetzt.minute
    von, bis = _minuten(einst["ruhe_von"]), _minuten(einst["ruhe_bis"])
    return von <= m < bis if von < bis else (m >= von or m < bis)


# ---------- Stand: was schon gesehen ist ----------

def stand(schluessel, wert=None):
    with closing(konten.db()) as v, v:
        if wert is not None:
            v.execute("INSERT INTO push_stand (schluessel, wert) VALUES (?, ?) ON CONFLICT (schluessel) "
                      "DO UPDATE SET wert = excluded.wert", (schluessel, json.dumps(wert, ensure_ascii=False)))
            return wert
        z = v.execute("SELECT wert FROM push_stand WHERE schluessel = ?", (schluessel,)).fetchone()
        return json.loads(z["wert"]) if z else None


def _jsonl(pfad):
    liste = []
    try:
        zeilen = pfad.read_text(encoding="utf-8").splitlines()
    except OSError:
        return liste
    for z in zeilen:
        try:
            e = json.loads(z)
        except json.JSONDecodeError:
            continue
        if isinstance(e, dict) and e.get("id") and e.get("erstellt"):
            liste.append(e)
    return liste


def neue(eintraege, schluessel):
    """Einträge (mit id und erstellt), die seit dem letzten Lauf dazugekommen sind. Gemerkt wird der späteste Zeitpunkt
    und die IDs an ihm, damit zwei Einträge derselben Sekunde nicht verloren gehen. Erster Lauf: nur merken."""
    alt = stand(schluessel)
    bis = max((e["erstellt"] for e in eintraege), default="")
    neu_stand = {"bis": bis, "ids": sorted(e["id"] for e in eintraege if e["erstellt"] == bis)}
    if alt is None:
        stand(schluessel, neu_stand)
        return []
    gesehen = set(alt.get("ids") or [])
    frisch = [e for e in eintraege if e["erstellt"] > alt.get("bis", "")
              or (e["erstellt"] == alt.get("bis") and e["id"] not in gesehen)]
    if frisch:
        if bis == alt.get("bis"):
            neu_stand["ids"] = sorted(gesehen | set(neu_stand["ids"]))
        stand(schluessel, neu_stand)
    return sorted(frisch, key=lambda e: e["erstellt"])


def release_von(reise):
    """Release der veröffentlichten Seite (data-release im Fuß, engine/bauen.py) oder None."""
    try:
        kopf = (rm.seiten() / reise / "index.html").read_text(encoding="utf-8")
    except OSError:
        return None
    m = re.search(r'data-release="([^"]*)"', kopf)
    try:
        r = json.loads(html.unescape(m.group(1))) if m else None
    except ValueError:
        return None
    return r if isinstance(r, dict) and r.get("kennung") else None


# ---------- Sammeln: was ist neu, wer bekommt es ----------

def _reisen():
    a = rm.ablage()
    return sorted(o.name for o in a.iterdir() if o.is_dir() and rm.REISE_MUSTER.match(o.name)) if a.is_dir() else []


def _empfaenger(reise, personen, namen):
    """Namen (wie in Meldungen und Aufgaben) -> {konto: person} der Personen, die ein Konto haben."""
    nach_name = {str(p.get("name", "")).casefold(): p for p in personen}
    aus = {}
    for n in namen:
        p = nach_name.get(str(n or "").strip().casefold())
        kid = konten.konto_von_person(reise, p["schluessel"]) if p and p.get("schluessel") else None
        if kid:
            aus[kid] = p
    return aus


def _kurz(text):
    text = " ".join(str(text or "").split())
    return text if len(text) <= MAX_TEXT else text[:MAX_TEXT - 1].rstrip() + "…"


def einreihen(kid, reise, art, text, ziel="", jetzt=None, kat=None):
    """Nachricht für ein Konto vormerken, wenn es Geräte hat und ihre Gruppe aufs Handy soll; wer für die Gruppe die
    tägliche Zusammenfassung gewählt hat, bekommt sie dort auch (#517). -> ob aufs Handy vorgemerkt."""
    kat = kat or kategorie(art)
    e = einstellungen_von(kid)
    if e["mail"].get(kat) == "taeglich":
        sammeln_fuer_mail(kid, reise, text, jetzt)
    if not e["push"].get(kat) or not konten.push_abos(kid):
        return False
    with closing(konten.db()) as v, v:
        v.execute("INSERT INTO push_warteschlange (konto, reise, art, text, ziel, erstellt) VALUES (?,?,?,?,?,?)",
                  (kid, reise, art, _kurz(text), ziel or "", jetzt or time.time()))
    return True


def sprache_von(kid):
    k = konten.konto(kid) or {}
    return k.get("sprache") if texte.gueltig(k.get("sprache") or "") else texte.VORGABE


def sammeln_reise(reise, jetzt=None):
    """Neues einer Reise vormerken. -> Zahl der vorgemerkten Nachrichten. Der Stand wird auch gemerkt, wenn die Reise
    nichts schickt (Kanal push aus), damit Altes beim Einschalten nicht nachkommt."""
    o = rm.ordner(reise)
    z = rm.zustand(reise)
    if o is None or z is None:
        return 0
    an = "push" in ((z.get("regeln") or {}).get("meldekanal") or rg.VORGABEN["meldekanal"])
    personen = z.get("personen") or []
    n = 0
    # Meldungen an Personen; die des Wächters nur, solange sein Baustein an ist (wie im Konnektor)
    for m in neue(_jsonl(o / "meldungen.jsonl"), f"meldungen:{reise}"):
        if not an or (m.get("art") in rm.WAECHTER_ARTEN and "waechter" not in (z.get("bausteine") or [])):
            continue
        ziel = rm.meldung_anker(m)      # dieselbe Stelle wie auf Mein Konto (#407)
        for kid in _empfaenger(reise, personen, m.get("an") or []):
            n += einreihen(kid, reise, "meldung", m.get("text", ""), ziel, jetzt, kategorie("meldung", m))
    # Rückmeldungen von der Seite an die Organisator:innen, nicht an die Person, die sie geschrieben hat
    organisatoren = [p["name"] for p in personen if rg.rolle_neu(p.get("rolle")) == "organisator" and p.get("name")]
    for e in neue(_jsonl(o / "eingang.jsonl"), f"eingang:{reise}"):
        if not an:
            continue
        for kid, p in _empfaenger(reise, personen, organisatoren).items():
            if str(p.get("name", "")).casefold() == str(e.get("name", "")).casefold():
                continue
            text = texte.t(sprache_von(kid), "push.rueckmeldung", name=e.get("name", ""), text=e.get("text", ""))
            n += einreihen(kid, reise, "rueckmeldung", text, "wuensche" if e.get("ziel") == rm.WUNSCH_ZIEL else e.get("ziel", ""), jetzt)
    # Aufgaben, die jemandem neu zugewiesen sind
    alt = stand(f"aufgaben:{reise}")
    jetzt_zu = {a["id"]: a.get("zustaendig", "") for a in rm.aufgaben(o) if a.get("status") in OFFEN}
    if alt is not None and an:
        for a in rm.aufgaben(o):
            zu = jetzt_zu.get(a["id"], "")
            if not zu or alt.get(a["id"]) == zu:
                continue
            von = ((a.get("verlauf") or [{}])[-1]).get("wer", "")
            for kid, p in _empfaenger(reise, personen, [zu]).items():
                if str(von).casefold() == str(p.get("name", "")).casefold():
                    continue
                text = texte.t(sprache_von(kid), "push.aufgabe", titel=a.get("titel", ""), von=von)
                n += einreihen(kid, reise, "aufgabe", text, a["id"], jetzt)
    if alt != jetzt_zu:
        stand(f"aufgaben:{reise}", jetzt_zu)
    # Neues Release der Software auf der veröffentlichten Seite
    r = release_von(reise)
    if r:
        alt_r = stand(f"release:{reise}")
        if alt_r != r["kennung"]:
            stand(f"release:{reise}", r["kennung"])
            if alt_r is not None and an:
                for kid in _empfaenger(reise, personen, [p.get("name") for p in personen]):
                    sp = sprache_von(kid)
                    text = (texte.t(sp, "push.version", nummer=r["nummer"]) if r.get("nummer")
                            else texte.t(sp, "push.version_ohne_nummer"))
                    n += einreihen(kid, reise, "version", text, "", jetzt)
    return n


def sammeln(jetzt=None):
    return sum(sammeln_reise(r, jetzt) for r in _reisen())


# ---------- Zustellen ----------

def seite_von(reise):
    """Adresse der Reiseseite: aus einem Abo, das auf ihr abgeschlossen wurde, sonst aus seiten.json des Betriebs."""
    for a in konten.push_abos():
        if a["reise"] == reise and a["seite"]:
            return a["seite"]
    p = Path(os.environ.get("KN_SEITENLINKS") or instanz.konnektor() / "seiten.json")
    try:
        links = json.loads(p.read_text(encoding="utf-8"))
        return links.get(reise) if isinstance(links, dict) else None
    except (OSError, ValueError):
        return None


def titel_von(reise):
    try:
        d = json.loads((rm.seiten() / reise / "daten.json").read_text(encoding="utf-8"))["reise"]
        return d.get("kurz") or d.get("titel") or reise
    except (OSError, ValueError, KeyError, TypeError):
        return reise


def ziele(abos, reise):
    """Je Gerät ein Abo: das der Reise, um die es geht, sonst das zuletzt aufgefrischte. Ein Gerät ohne Kennung zählt
    als eigenes Gerät."""
    je = {}
    for a in abos:   # neueste zuerst
        g = a["geraet"] or a["endpoint"]
        if g not in je or (a["reise"] == reise and je[g]["reise"] != reise):
            je[g] = a
    return list(je.values())


def nachricht(kid, reise, eintraege):
    """Inhalt der Nachricht an ein Gerät: Titel (Kurzname der Reise), Text, Link zur Stelle, Kennung für das Ersetzen."""
    sp = sprache_von(kid)
    seite = seite_von(reise) or ""
    if len(eintraege) == 1:
        e = eintraege[0]
        text, ziel = e["text"], e["ziel"]
    else:
        text = texte.t(sp, "push.mehrere", n=len(eintraege), zuletzt=eintraege[-1]["text"])
        ziel = "zu-tun" if all(e["art"] in ("meldung", "rueckmeldung", "aufgabe") for e in eintraege) else ""
    url = seite + (f"#{ziel}" if ziel else "")
    if any(e["art"] == "version" for e in eintraege) and seite:
        url = seite + "?aktualisieren=1" + (f"#{ziel}" if ziel else "")
    return {"titel": titel_von(reise), "text": _kurz(text), "url": url, "tag": f"frieda-{reise}"}


def zustellen(senden, jetzt=None):
    """Wartende Nachrichten an die Geräte schicken. senden(abo, nachricht) -> "ok" | "weg" (Abo gibt es nicht mehr) oder
    eine Ausnahme. -> {"nachrichten", "geraete", "weg", "fehler", "warten"}"""
    jetzt = jetzt or time.time()
    zeitpunkt = datetime.datetime.fromtimestamp(jetzt, datetime.timezone.utc)
    erg = {"nachrichten": 0, "geraete": 0, "weg": 0, "fehler": 0, "warten": 0}
    with closing(konten.db()) as v, v:
        v.execute("DELETE FROM push_warteschlange WHERE gesendet IS NOT NULL AND gesendet < ?", (jetzt - 7 * 86400,))
        v.execute("DELETE FROM push_warteschlange WHERE gesendet IS NULL AND erstellt < ?", (jetzt - MAX_ALTER,))
        offen = [dict(z) for z in v.execute("SELECT * FROM push_warteschlange WHERE gesendet IS NULL ORDER BY id")]
    je_konto = {}
    for e in offen:
        je_konto.setdefault(e["konto"], []).append(e)
    for kid, liste in je_konto.items():
        abos = konten.push_abos(kid)
        if not abos:
            _erledigt([e["id"] for e in liste], jetzt)
            continue
        if ruhig(einstellungen_von(kid), zeitpunkt, abos[0]["zeitzone"]):
            erg["warten"] += len(liste)
            continue
        je_reise = {}
        for e in liste:
            je_reise.setdefault(e["reise"], []).append(e)
        for reise, eintraege in je_reise.items():
            inhalt = nachricht(kid, reise, eintraege)
            ok = weg = 0
            geraete = ziele(abos, reise)
            for a in geraete:
                try:
                    if senden(a, inhalt) == "weg":
                        konten.push_abo_weg(a["endpoint"])
                        weg += 1
                    else:
                        konten.push_abo_ok(a["endpoint"])
                        ok += 1
                except Exception as x:   # Push-Dienst nicht erreichbar, Zeitüberschreitung: später noch einmal
                    erg["fehler"] += 1
                    print(f"Push to {a['endpoint'][:40]}…: {type(x).__name__}", file=sys.stderr, flush=True)
            erg["geraete"] += ok
            erg["weg"] += weg
            ids = [e["id"] for e in eintraege]
            if ok or weg == len(geraete) or max(e["versuche"] for e in eintraege) + 1 >= MAX_VERSUCHE:
                _erledigt(ids, jetzt)
                erg["nachrichten"] += 1 if ok else 0
            else:
                with closing(konten.db()) as v, v:
                    v.executemany("UPDATE push_warteschlange SET versuche = versuche + 1 WHERE id = ?", [(i,) for i in ids])
    return erg


def _erledigt(ids, jetzt):
    with closing(konten.db()) as v, v:
        v.executemany("UPDATE push_warteschlange SET gesendet = ? WHERE id = ?", [(jetzt, i) for i in ids])


# ---------- Versand über Web Push (pywebpush, nur im Dienst) ----------

def _b64(daten):
    return base64.urlsafe_b64encode(daten).rstrip(b"=").decode("ascii")


def schluessel():
    """VAPID-Schlüsselpaar des Servers, beim ersten Aufruf angelegt (P-256). -> (öffentlich, privat als PEM)."""
    oeffentlich, privat = konten.push_schluessel("vapid_oeffentlich"), konten.push_schluessel("vapid_privat")
    if oeffentlich and privat:
        return oeffentlich, privat
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    k = ec.generate_private_key(ec.SECP256R1())
    pem = k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                          serialization.NoEncryption()).decode("ascii")
    pub = _b64(k.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint))
    # Erst der private, dann der öffentliche: Wer den öffentlichen liest (Rückmeldedienst), findet den privaten schon vor
    privat = konten.push_schluessel("vapid_privat", pem)
    if privat != pem:   # ein anderer Prozess war schneller: dessen Paar gilt
        while not konten.push_schluessel("vapid_oeffentlich"):
            time.sleep(0.1)
        return konten.push_schluessel("vapid_oeffentlich"), privat
    return konten.push_schluessel("vapid_oeffentlich", pub), privat


def webpush_sender():
    """senden(abo, nachricht) für zustellen(), mit pywebpush. Kontakt (VAPID sub) ist die Adresse der Instanz."""
    from py_vapid import Vapid02
    from pywebpush import WebPushException, webpush
    _, privat = schluessel()
    vapid = Vapid02.from_pem(privat.encode("ascii"))
    kontakt = konten.basis() or "mailto:push@localhost"

    import requests

    class OhneUmleitung:
        """Ein Push-Dienst leitet nicht um; einer Umleitung zu folgen hieße, eine Anfrage an eine Adresse zu schicken,
        die niemand geprüft hat (etwa einen Dienst im eigenen Netz)."""
        @staticmethod
        def post(url, **kw):
            return requests.post(url, **{**kw, "allow_redirects": False})

    sitzung = OhneUmleitung()

    def senden(abo, inhalt):
        if not konten.push_endpunkt_erlaubt(abo["endpoint"]):
            return "weg"      # altes Abo an eine Adresse, die kein Push-Dienst ist: nicht senden, Abo löschen
        try:
            webpush({"endpoint": abo["endpoint"], "keys": {"p256dh": abo["p256dh"], "auth": abo["auth"]}},
                    json.dumps(inhalt, ensure_ascii=False), vapid_private_key=vapid,
                    vapid_claims={"sub": kontakt}, ttl=TTL, timeout=15, requests_session=sitzung)
            return "ok"
        except WebPushException as x:
            if x.response is not None and x.response.status_code in (404, 410):
                return "weg"
            raise
    return senden


# ---------- Mail als Rückfall für Statushinweise (#513) ----------

def _sekunden(iso):
    try:
        return datetime.datetime.fromisoformat(str(iso)).timestamp()
    except ValueError:
        return None


def mail_text(kid, reise, m, name, wann="nach_tag"):
    """-> (Betreff, Text) einer Mail zu einer wichtigen Meldung, in der Sprache des Kontos."""
    sp = sprache_von(kid)
    seite = seite_von(reise) or ""
    zeilen = [texte.t(sp, "push.mail.anrede", name=name), "", rm.meldung_text_in(m, sp) or m.get("text", "")]
    if seite:
        zeilen += ["", texte.t(sp, "push.mail.seite", seite=seite)]
    zeilen += ["", texte.t(sp, "push.mail.warum." + wann)]
    if konten.basis():
        zeilen.append(konten.basis() + "/konto#push")
    return texte.t(sp, "push.mail.betreff", titel=titel_von(reise)), "\n".join(zeilen)


def _senden_gemerkt(senden, schl, an, betreff, text, jetzt, wo):
    """Eine Mail höchstens einmal (push_stand), bei Fehlern höchstens MAIL_VERSUCHE Mal im Abstand MAIL_PAUSE. -> ob gesendet."""
    vorher = stand(schl) or {}
    if vorher.get("gesendet") or vorher.get("versuche", 0) >= MAIL_VERSUCHE or jetzt - vorher.get("zuletzt", 0) < MAIL_PAUSE:
        return False
    try:
        senden(an, betreff, text)
    except konten.KontoFehler as x:
        stand(schl, {"versuche": vorher.get("versuche", 0) + 1, "zuletzt": jetzt})
        print(f"Mail {wo}: {x.schluessel}", file=sys.stderr, flush=True)
        return False
    stand(schl, {"gesendet": jetzt})
    return True


def _mail_an(reise_regeln):
    return "mail" in ((reise_regeln or {}).get("meldekanal") or rg.VORGABEN["meldekanal"])


def mail_rueckfall(senden=None, jetzt=None):
    """Wichtige Meldungen (#513, #517) per Mail, je nach Einstellung der Person: „nach_tag“ (Vorgabe) einmal, wenn sie nach
    MAIL_NACH noch gilt, ungelesen ist und die Person kein Gerät mit Benachrichtigungen für Wichtiges hat; „sofort“ gleich
    beim ersten Durchgang; „nie“ gar nicht. Ältere als MAIL_BIS gehen nicht mehr. -> Zahl der verschickten Mails."""
    senden = senden or konten.mail_senden
    jetzt = jetzt or time.time()
    n = 0
    for reise in _reisen():
        o, z = rm.ordner(reise), rm.zustand(reise)
        if o is None or z is None or not _mail_an(z.get("regeln")):
            continue
        offene_aufgaben = None
        for m in _jsonl(o / "meldungen.jsonl"):
            erstellt = _sekunden(m["erstellt"])
            if kategorie("meldung", m) != "wichtig" or erstellt is None or jetzt - erstellt > MAIL_BIS:
                continue
            for kid, p in _empfaenger(reise, z.get("personen") or [], m.get("an") or []).items():
                e = einstellungen_von(kid)
                wann = e["mail"]["wichtig"]
                if wann == "nie" or (wann == "nach_tag" and (jetzt - erstellt < MAIL_NACH
                                                             or (e["push"]["wichtig"] and konten.push_abos(kid))
                                                             or m["id"] in konten.gelesen(kid))):
                    continue
                if offene_aufgaben is None:
                    offene_aufgaben = rm.aufgaben(o)
                gilt = {x["id"] for x in rm.meldungen_aktuell(o, p.get("name") or "", offene_aufgaben, z.get("status"),
                                                              z.get("bausteine"), tage=MAIL_BIS // 86400 + 1)}
                k = konten.konto(kid)
                if m["id"] not in gilt or not k or k["gesperrt"] or not k["email"]:
                    continue
                betreff, text = mail_text(kid, reise, m, p.get("name") or k["name"], wann)
                n += _senden_gemerkt(senden, f"mail:{m['id']}:{kid}", k["email"], betreff, text, jetzt, f"{reise} {m['id']}")
    return n


# ---------- Tägliche Zusammenfassung per Mail (#517) ----------
MAX_SAMMEL = 200   # Einträge je Konto bis zur nächsten Zusammenfassung


def sammeln_fuer_mail(kid, reise, text, jetzt=None):
    """Einen Eintrag für die tägliche Zusammenfassung eines Kontos merken (nur Reisen mit Kanal mail)."""
    if not _mail_an((rm.zustand(reise) or {}).get("regeln")):
        return
    liste = stand(f"sammel:{kid}") or []
    liste.append({"reise": reise, "text": _kurz(text), "zeit": jetzt or time.time()})
    stand(f"sammel:{kid}", liste[-MAX_SAMMEL:])


def _zone_von(kid):
    abos = konten.push_abos(kid)
    return (abos[0]["zeitzone"] if abos and abos[0].get("zeitzone") else "") or instanz.zeitzone()


def zusammenfassungen(senden=None, jetzt=None):
    """Einmal am Tag, ab ZUSAMMENFASSUNG_UM auf der Uhr der Person, die gesammelten Einträge als eine Mail. -> Zahl."""
    senden = senden or konten.mail_senden
    jetzt = jetzt or time.time()
    zeitpunkt = datetime.datetime.fromtimestamp(jetzt, datetime.timezone.utc)
    with closing(konten.db()) as v:
        kids = [z["schluessel"][len("sammel:"):] for z in v.execute("SELECT schluessel FROM push_stand WHERE schluessel LIKE 'sammel:%'")]
    n = 0
    for kid in kids:
        liste = stand(f"sammel:{kid}") or []
        ort = ortszeit(zeitpunkt, _zone_von(kid))
        tag = ort.date().isoformat()
        if not liste or ort.hour * 60 + ort.minute < _minuten(ZUSAMMENFASSUNG_UM) or stand(f"sammel_tag:{kid}") == tag:
            continue
        k = konten.konto(kid)
        if not k or k["gesperrt"] or not k["email"]:
            stand(f"sammel:{kid}", [])
            continue
        sp = sprache_von(kid)
        zeilen = [texte.t(sp, "push.mail.anrede", name=k["name"]), "", texte.t(sp, "push.mail.zusammenfassung.einleitung")]
        for reise in dict.fromkeys(e["reise"] for e in liste):
            zeilen += ["", titel_von(reise) + (f" ({seite_von(reise)})" if seite_von(reise) else "") + ":"]
            zeilen += [f"- {e['text']}" for e in liste if e["reise"] == reise]
        zeilen += ["", texte.t(sp, "push.mail.zusammenfassung.warum")]
        if konten.basis():
            zeilen.append(konten.basis() + "/konto#push")
        betreff = texte.t(sp, "push.mail.zusammenfassung.betreff", n=len(liste))
        if _senden_gemerkt(senden, f"sammel_mail:{kid}:{tag}", k["email"], betreff, "\n".join(zeilen), jetzt, f"summary {kid}"):
            stand(f"sammel:{kid}", [])
            stand(f"sammel_tag:{kid}", tag)
            n += 1
    return n


def lauf(senden=None, jetzt=None, mail=None):
    n = sammeln(jetzt)
    erg = zustellen(senden or webpush_sender(), jetzt)
    return {"vorgemerkt": n, **erg, "mails": mail_rueckfall(mail, jetzt) + zusammenfassungen(mail, jetzt)}


def dienst():
    oeffentlich, _ = schluessel()
    print(f"Push service, store {rm.ablage()}, key {oeffentlich[:12]}…", flush=True)
    senden = webpush_sender()
    while True:
        try:
            erg = lauf(senden)
            if erg["vorgemerkt"] or erg["nachrichten"] or erg["fehler"] or erg["weg"] or erg["mails"]:
                print(json.dumps(erg), flush=True)
        except Exception as x:   # ein Fehler in einer Reise hält den Dienst nicht an; der nächste Durchgang versucht es
            print(f"Error: {type(x).__name__}: {x}", file=sys.stderr, flush=True)
        time.sleep(PAUSE)


def probe(email):
    k = konten.konto_per_email(email)
    if not k:
        sys.exit(texte.t(texte.VORGABE_REISE, "konto.fehler.konto_nicht_gefunden"))
    senden = webpush_sender()
    inhalt = {"titel": "Frieda", "text": texte.t(sprache_von(k["id"]), "push.probe"), "url": "", "tag": "frieda-probe"}
    for a in konten.push_abos(k["id"]):
        try:
            print(a["endpoint"][:50], senden(a, inhalt))
        except Exception as x:
            print(a["endpoint"][:50], type(x).__name__, x)


def main(a):
    if a[:1] == ["dienst"]:
        dienst()
    elif a[:1] == ["lauf"]:
        print(json.dumps(lauf()))
    elif a[:1] == ["schluessel"]:
        print(schluessel()[0])
    elif a[:1] == ["probe"] and len(a) == 2:
        probe(a[1])
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
