#!/usr/bin/env python3
"""Push-Nachrichten aufs Handy (Issue #21, Stufe 2; docs/waechter.md „Meldekanäle“, docs/betrieb.md „Push“).

Wer auf der Reiseseite angemeldet ist, kann Benachrichtigungen für dieses Gerät einschalten (Fuß der Seite). Das Gerät
schließt beim Push-Dienst seines Browsers ein Abo ab und gibt es dem Rückmeldedienst (konten.push_abo_speichern). Dieser
Dienst liest danach, was in den Reisen neu ist, und schickt es an die Geräte der Personen:

  meldung       Meldungen an Personen (meldungen.jsonl: Wächter und Erinnerer, Konflikte, Rot beim Veröffentlichen)
  rueckmeldung  neue Rückmeldungen, Fragen und Wünsche von der Seite (eingang.jsonl), an die Organisator:innen
  aufgabe       eine Aufgabe ist dir neu zugewiesen (aufgaben.json, Feld zustaendig), nicht wenn du es selbst warst
  version       ein neues Release der Software ist veröffentlicht (Fuß der Seite, data-release); Tippen aktualisiert

Was jemand bekommt, stellt die Person auf „Mein Konto“ ein, für alle Reisen gleich: welche Arten und eine Ruhezeit auf
der Uhr ihres Geräts (Vorgabe 21:30 bis 7:00). Was in der Ruhezeit anfällt, wartet bis zu ihrem Ende. Was zur selben
Zeit für dieselbe Reise wartet, kommt als eine Nachricht („3 Neuigkeiten“). Eine Reise ohne Kanal push in
regeln.meldekanal schickt nichts. Beim ersten Lauf merkt sich der Dienst nur den Stand; Altes wird nie nachgeschickt.

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

ARTEN = ("meldung", "rueckmeldung", "aufgabe", "version")
RUHE_VORGABE = ("21:30", "07:00")
UHRZEIT = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")
PAUSE = 20                    # Sekunden zwischen zwei Durchgängen des Dienstes
MAX_ALTER = 36 * 3600         # was so lange nicht zugestellt werden konnte, fällt weg (auch nach einer langen Ruhezeit)
MAX_VERSUCHE = 5              # Fehlversuche je Nachricht (Push-Dienst nicht erreichbar), dann aufgeben
TTL = 12 * 3600               # so lange hält der Push-Dienst eine Nachricht für ein ausgeschaltetes Gerät
MAX_TEXT = 240                # Zeichen im Text einer Nachricht (Telefone kürzen ohnehin)
OFFEN = ("offen", "in_arbeit")


# ---------- Einstellungen und Ruhezeit (nur Standardbibliothek) ----------

def einstellungen(roh):
    """Einstellungen eines Kontos bereinigt: {arten: [...], ruhe_von: "HH:MM" | "", ruhe_bis: "HH:MM" | ""}.
    Unbekanntes fällt weg; leere Ruhezeit (beide leer) heißt: keine."""
    roh = roh if isinstance(roh, dict) else {}
    arten = roh.get("arten", list(ARTEN))
    arten = [a for a in ARTEN if isinstance(arten, list) and a in arten]
    von, bis = roh.get("ruhe_von", RUHE_VORGABE[0]), roh.get("ruhe_bis", RUHE_VORGABE[1])
    von = von if isinstance(von, str) and UHRZEIT.match(von) else ""
    bis = bis if isinstance(bis, str) and UHRZEIT.match(bis) else ""
    if not von or not bis or von == bis:
        von = bis = ""
    return {"arten": arten, "ruhe_von": von, "ruhe_bis": bis}


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


def einreihen(kid, reise, art, text, ziel="", jetzt=None):
    """Nachricht für ein Konto vormerken, wenn es Geräte hat und die Art eingeschaltet ist. -> ob vorgemerkt."""
    if art not in einstellungen_von(kid)["arten"] or not konten.push_abos(kid):
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
        ziel = m.get("bezug") if str(m.get("bezug", "")).startswith("AG-") else m.get("ziel", "")
        for kid in _empfaenger(reise, personen, m.get("an") or []):
            n += einreihen(kid, reise, "meldung", m.get("text", ""), "" if ziel in ("reise", "") else ziel, jetzt)
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
    p = Path(os.environ.get("KN_SEITENLINKS") or instanz.zugaenge().with_name("seiten.json"))
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
        ziel = "offen" if all(e["art"] in ("meldung", "rueckmeldung", "aufgabe") for e in eintraege) else ""
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
                    print(f"Push an {a['endpoint'][:40]}…: {type(x).__name__}", file=sys.stderr, flush=True)
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

    def senden(abo, inhalt):
        try:
            webpush({"endpoint": abo["endpoint"], "keys": {"p256dh": abo["p256dh"], "auth": abo["auth"]}},
                    json.dumps(inhalt, ensure_ascii=False), vapid_private_key=vapid,
                    vapid_claims={"sub": kontakt}, ttl=TTL, timeout=15)
            return "ok"
        except WebPushException as x:
            if x.response is not None and x.response.status_code in (404, 410):
                return "weg"
            raise
    return senden


def lauf(senden=None, jetzt=None):
    n = sammeln(jetzt)
    erg = zustellen(senden or webpush_sender(), jetzt)
    return {"vorgemerkt": n, **erg}


def dienst():
    oeffentlich, _ = schluessel()
    print(f"push: {rm.ablage()}, vapid {oeffentlich[:12]}", flush=True)
    senden = webpush_sender()
    while True:
        try:
            erg = lauf(senden)
            if erg["vorgemerkt"] or erg["nachrichten"] or erg["fehler"] or erg["weg"]:
                print(json.dumps(erg), flush=True)
        except Exception as x:   # ein Fehler in einer Reise hält den Dienst nicht an; der nächste Durchgang versucht es
            print(f"Fehler: {type(x).__name__}: {x}", file=sys.stderr, flush=True)
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
