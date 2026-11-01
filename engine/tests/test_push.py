"""Tests für Push-Nachrichten (Issue #21, engine/push.py): Einstellungen und Ruhezeit, Geräte an- und abmelden, was der
Dienst aus den Reisen sammelt und wie er es zustellt, Versand mit echter Verschlüsselung (Web Push, gegen eine Attrappe des
Push-Dienstes), Mein Konto und der Anstoß „Veröffentlichen“ von der Seite. Alle Personen und Adressen sind erfunden."""
import base64
import datetime
import html
import json
import os
import re
import sys
from contextlib import closing
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import konten  # noqa: E402
import push  # noqa: E402
import rueckmeldungen as rm  # noqa: E402
from test_anmeldung import BASIS, IDA, KARL, SEITE, abruf, anmelden, welt  # noqa: E402,F401

MITTAG = datetime.datetime(2027, 5, 14, 10, 0, tzinfo=datetime.timezone.utc).timestamp()   # 12:00 in Berlin
NACHT = datetime.datetime(2027, 5, 14, 22, 0, tzinfo=datetime.timezone.utc).timestamp()    # 0:00 in Berlin


def abo(n, p256dh="B" * 87, auth="A" * 22):
    return {"endpoint": f"https://push.beispiel.invalid/geraet-{n}", "keys": {"p256dh": p256dh, "auth": auth}}


def konto(kid, email, name):
    with closing(konten.db()) as v, v:
        v.execute("INSERT INTO konten (id, email, name, angelegt) VALUES (?,?,?,?)", (kid, email, name, "2026-11-01"))
    return kid


# ---------- Einstellungen und Ruhezeit ----------

def test_einstellungen_bereinigt_mit_vorgaben():
    assert push.einstellungen({}) == {"arten": list(push.ARTEN), "ruhe_von": "21:30", "ruhe_bis": "07:00"}
    assert push.einstellungen({"arten": ["version", "erfunden", "meldung"], "ruhe_von": "22:00", "ruhe_bis": "06:30"}) == \
        {"arten": ["meldung", "version"], "ruhe_von": "22:00", "ruhe_bis": "06:30"}
    # leer, kaputt oder gleich: keine Ruhezeit
    for von, bis in (("", ""), ("25:00", "07:00"), ("08:00", "08:00"), ("8 Uhr", "07:00")):
        e = push.einstellungen({"ruhe_von": von, "ruhe_bis": bis})
        assert e["ruhe_von"] == e["ruhe_bis"] == ""
    assert push.einstellungen("kaputt")["arten"] == list(push.ARTEN)


@pytest.mark.parametrize("utc,zone,ruhig", [
    ((2027, 5, 14, 19, 45), "Europe/Berlin", True),     # 21:45 Ortszeit
    ((2027, 5, 14, 19, 15), "Europe/Berlin", False),    # 21:15
    ((2027, 5, 15, 4, 59), "Europe/Berlin", True),      # 6:59
    ((2027, 5, 15, 5, 0), "Europe/Berlin", False),      # 7:00: die Ruhe ist vorbei
    ((2027, 5, 15, 5, 0), "America/New_York", True),    # 1:00 in New York
    ((2027, 5, 15, 5, 0), "", True),                    # ohne Zone gilt UTC: 5:00
    ((2027, 5, 15, 5, 0), "Erfunden/Nirgends", True),   # unbekannte Zone: UTC
])
def test_ruhezeit_auf_der_uhr_des_geraets(utc, zone, ruhig):
    e = push.einstellungen({"ruhe_von": "21:30", "ruhe_bis": "07:00"})
    assert push.ruhig(e, datetime.datetime(*utc, tzinfo=datetime.timezone.utc), zone) is ruhig


def test_ruhezeit_am_tag_und_ohne():
    t = datetime.datetime(2027, 5, 14, 12, 30, tzinfo=datetime.timezone.utc)
    assert push.ruhig(push.einstellungen({"ruhe_von": "12:00", "ruhe_bis": "14:00"}), t, "UTC")
    assert not push.ruhig(push.einstellungen({"ruhe_von": "13:00", "ruhe_bis": "14:00"}), t, "UTC")
    assert not push.ruhig(push.einstellungen({"ruhe_von": "", "ruhe_bis": ""}), t, "UTC")


# ---------- Geräte (konten.py) ----------

def test_abo_speichern_ersetzen_entfernen():
    ida, karl = konto("K-ida", IDA, "Ida"), konto("K-karl", KARL, "Karl")
    for kaputt in ({"endpoint": "http://unsicher.invalid/x", "keys": {"p256dh": "B" * 87, "auth": "A" * 22}},
                   {"endpoint": "https://push.beispiel.invalid/x", "keys": {"p256dh": "<b>", "auth": "A" * 22}},
                   {"endpoint": "https://push.beispiel.invalid/x"}, "kaputt", None):
        with pytest.raises(konten.KontoFehler):
            konten.push_abo_speichern(ida, kaputt)
    konten.push_abo_speichern(ida, abo(1), "beispielreise", SEITE, "geraet-ida-1", "Europe/Berlin")
    konten.push_abo_speichern(ida, abo(2), "andere-reise", "", "geraet-ida-1", "Europe/Berlin")
    assert {a["endpoint"][-8:] for a in konten.push_abos(ida)} == {"geraet-1", "geraet-2"}
    # dasselbe Gerät schließt für dieselbe Reise ein neues Abo ab: das alte fällt weg
    konten.push_abo_speichern(ida, abo(3), "beispielreise", SEITE, "geraet-ida-1", "Europe/Lisbon")
    abos = konten.push_abos(ida)
    assert {a["endpoint"][-8:] for a in abos} == {"geraet-2", "geraet-3"} and abos[0]["zeitzone"] == "Europe/Lisbon"
    assert abos[0]["seite"] == SEITE and abos[0]["reise"] == "beispielreise"
    # unsaubere Angaben neben dem Abo fallen weg, das Abo bleibt
    konten.push_abo_speichern(ida, abo(4), "../x", "javascript:x", "<g>", "Europe/Berlin; rm")
    a = next(a for a in konten.push_abos(ida) if a["endpoint"].endswith("geraet-4"))
    assert (a["reise"], a["seite"], a["geraet"], a["zeitzone"]) == ("", "", "", "")
    # abmelden nur das eigene Konto
    assert not konten.push_abo_entfernen(karl, abo(3)["endpoint"])
    assert konten.push_abo_entfernen(ida, abo(3)["endpoint"])
    # höchstens MAX_PUSH_ABOS je Konto, die ältesten fallen weg
    for n in range(20):
        konten.push_abo_speichern(ida, abo(100 + n), "beispielreise", SEITE, f"geraet-viele-{n:02d}")
    assert len(konten.push_abos(ida)) == konten.MAX_PUSH_ABOS
    # gesperrt: keine Geräte mehr; gelöscht: auch die Einstellungen weg
    konten.push_abo_speichern(karl, abo(9), "beispielreise", SEITE, "geraet-karl")
    konten.sperren(karl)
    assert konten.push_abos(karl) == []
    push.einstellungen_von(ida, {"arten": ["meldung"]})
    konten.loeschen(ida)
    assert konten.push_abos(ida) == [] and konten.push_einstellungen(ida) == {}


def test_je_geraet_ein_abo_das_der_reise_zuerst():
    abos = [{"endpoint": "e3", "geraet": "g1", "reise": "andere"}, {"endpoint": "e2", "geraet": "g1", "reise": "beispielreise"},
            {"endpoint": "e1", "geraet": "g2", "reise": "andere"}, {"endpoint": "e0", "geraet": "", "reise": "x"}]
    assert sorted(a["endpoint"] for a in push.ziele(abos, "beispielreise")) == ["e0", "e1", "e2"]


# ---------- Rückmeldedienst: api/push ----------

def test_geraet_an_und_abmelden_ueber_die_seite(welt):
    u = welt()
    konten.einladen("beispielreise", "karl", KARL, "mitwirkend", "Karl", "Ida")
    karl, _ = anmelden(u, KARL)
    url = f"{u.rurl}/beispielreise/push"
    assert json.loads(abruf(url)[2]) == {"schluessel": None}       # Push-Dienst noch nie gestartet
    oeffentlich, privat = push.schluessel()
    assert push.schluessel() == (oeffentlich, privat)               # einmal angelegt, danach derselbe
    assert len(base64.urlsafe_b64decode(oeffentlich + "==")) == 65 and "PRIVATE KEY" in privat
    assert json.loads(abruf(url)[2]) == {"schluessel": oeffentlich}  # nie der private
    daten = {"abo": abo(1), "geraet": "geraet-karl-1", "zeitzone": "Europe/Berlin", "seite": SEITE}
    s, _, t = abruf(url, "POST", json_body=daten)
    assert s == 401 and "anmelden" in t
    assert abruf(url, "POST", json_body=daten, cookie=karl, origin="https://boese.invalid")[0] == 403
    s, _, t = abruf(url, "POST", json_body={**daten, "abo": {"endpoint": "https://x.invalid/y"}}, cookie=karl)
    assert s == 400 and "kein gültiges Abo" in t
    assert abruf(url, "POST", json_body=daten, cookie=karl)[0] == 200
    kid = konten.sitzung(karl)["id"]
    [a] = konten.push_abos(kid)
    assert (a["reise"], a["seite"], a["zeitzone"], a["geraet"]) == ("beispielreise", SEITE, "Europe/Berlin", "geraet-karl-1")
    s, _, t = abruf(url, "POST", json_body={"abmelden": abo(1)["endpoint"]}, cookie=karl)
    assert s == 200 and json.loads(t) == {"entfernt": True} and konten.push_abos(kid) == []


# ---------- Sammeln und Zustellen ----------

@pytest.fixture
def reise(welt):
    """Ida organisiert, Karl wirkt mit; beide haben ein Gerät mit Benachrichtigungen (Berlin)."""
    u = welt()
    konten.einladen("beispielreise", "ida", IDA, "organisator", "Ida", "Ida")
    konten.einladen("beispielreise", "karl", KARL, "mitwirkend", "Karl", "Ida")
    u.ida, _ = anmelden(u, IDA)
    u.karl, _ = anmelden(u, KARL)
    u.ida_id, u.karl_id = konten.sitzung(u.ida)["id"], konten.sitzung(u.karl)["id"]
    konten.push_abo_speichern(u.ida_id, abo("ida"), "beispielreise", SEITE, "geraet-ida-1", "Europe/Berlin")
    konten.push_abo_speichern(u.karl_id, abo("karl"), "beispielreise", SEITE, "geraet-karl-1", "Europe/Berlin")
    assert push.sammeln(MITTAG) == 0        # erster Lauf: nur den Stand merken, nichts Altes nachschicken
    u.gesendet = []

    def senden(a, inhalt):
        u.gesendet.append((a["endpoint"].rsplit("-", 1)[1], inhalt))
        return "ok"
    u.senden = senden
    return u


def rueckmeldung(u, token, **f):
    return abruf(f"{u.rurl}/beispielreise/rueckmeldungen", "POST", cookie=token,
                 json_body={"art": "Kommentar", "ziel": "T-01", "text": "Wir landen erst 21 Uhr.", "name": "x", **f})


def aufgabe(u, token, **f):
    return json.loads(abruf(f"{u.rurl}/beispielreise/aufgaben", "POST", cookie=token, json_body={"name": "x", **f})[2])


def test_rueckmeldung_meldung_und_aufgabe_kommen_an(reise):
    u = reise
    assert rueckmeldung(u, u.karl)[0] == 201                      # an Ida (organisiert), nicht an Karl selbst
    rm.meldung_anlegen(u.o, ["Karl"], "konflikt", "V-01", "Ida und Max haben verschieden entschieden.")
    aufgabe(u, u.ida, titel="Tickets kaufen", zustaendig="Karl")    # Ida weist Karl eine Aufgabe zu
    aufgabe(u, u.karl, titel="Rucksack packen", zustaendig="Karl")  # selbst übernommen: keine Nachricht
    assert push.sammeln(MITTAG) == 3
    assert push.sammeln(MITTAG) == 0                                 # nichts doppelt
    erg = push.zustellen(u.senden, MITTAG)
    assert erg["nachrichten"] == 2 and erg["geraete"] == 2 and erg["warten"] == 0
    an = dict(u.gesendet)
    assert an["ida"]["text"] == "Karl schreibt: Wir landen erst 21 Uhr." and an["ida"]["url"] == SEITE + "#T-01"
    assert an["ida"]["titel"] == "Beispiel" and an["ida"]["tag"] == "frieda-beispielreise"
    # Karl: zwei Neuigkeiten in einer Nachricht, die neueste zuerst genannt, Tippen öffnet „Offen“
    assert an["karl"]["text"] == "2 Neuigkeiten, zuletzt: Neue Aufgabe für dich: Tickets kaufen (von Ida)"
    assert an["karl"]["url"] == SEITE + "#offen"
    u.gesendet.clear()
    assert push.zustellen(u.senden, MITTAG)["nachrichten"] == 0 and not u.gesendet


def test_ruhezeit_wartet_bis_zum_morgen(reise):
    u = reise
    rueckmeldung(u, u.karl, text="Spät noch eine Frage")
    push.sammeln(NACHT)
    erg = push.zustellen(u.senden, NACHT)                            # 0:00 in Berlin: Ruhezeit (Vorgabe 21:30 bis 7:00)
    assert erg["warten"] == 1 and not u.gesendet
    morgen = NACHT + 7.5 * 3600                                      # 7:30
    assert push.zustellen(u.senden, morgen)["nachrichten"] == 1 and u.gesendet[0][1]["text"].endswith("Spät noch eine Frage")
    # ohne Ruhezeit kommt es sofort; was zu lange wartet, verfällt
    push.einstellungen_von(u.ida_id, {"ruhe_von": "", "ruhe_bis": ""})
    rueckmeldung(u, u.karl, text="Noch eine")
    push.sammeln(NACHT)
    assert push.zustellen(u.senden, NACHT + push.MAX_ALTER + 60)["nachrichten"] == 0


def test_arten_abschalten_und_kanal_der_reise(reise, welt):
    u = reise
    push.einstellungen_von(u.karl_id, {"arten": ["meldung"]})
    aufgabe(u, u.ida, titel="Tickets kaufen", zustaendig="Karl")
    assert push.sammeln(MITTAG) == 0
    # Eine Reise ohne Kanal push schickt nichts, merkt sich aber den Stand
    v = welt(regeln={"meldekanal": ["app"]})
    konten.einladen("beispielreise", "ida", IDA, "organisator", "Ida", "Ida")
    assert push.sammeln(MITTAG) == 0
    rm.meldung_anlegen(v.o, ["Ida"], "konflikt", "V-01", "Konflikt")
    assert push.sammeln(MITTAG) == 0


def test_neues_release_meldet_sich_einmal(reise):
    u = reise
    index = u.seiten / "beispielreise" / "index.html"
    text = index.read_text(encoding="utf-8")
    alt = re.search(r'data-release="([^"]*)"', text).group(1)
    neu = html.escape(json.dumps({"nummer": 412, "kennung": "abc1234", "commit": "abc1234" * 5, "github": None}), quote=True)
    index.write_text(text.replace(alt, neu, 1), encoding="utf-8")
    assert push.sammeln(MITTAG) == 2 and push.sammeln(MITTAG) == 0
    push.zustellen(u.senden, MITTAG)
    an = dict(u.gesendet)
    assert an["karl"]["text"] == "Frieda Release 412 ist da. Tippen zum Aktualisieren."
    assert an["karl"]["url"] == SEITE + "?aktualisieren=1"


def test_abo_weg_und_fehler(reise):
    u = reise
    rueckmeldung(u, u.karl)
    push.sammeln(MITTAG)
    assert push.zustellen(lambda a, i: "weg", MITTAG)["weg"] == 1
    assert konten.push_abos(u.ida_id) == []
    # Push-Dienst nicht erreichbar: es bleibt stehen und wird wiederholt, nach MAX_VERSUCHE aufgegeben
    konten.push_abo_speichern(u.ida_id, abo("ida"), "beispielreise", SEITE, "geraet-ida-1", "Europe/Berlin")
    rueckmeldung(u, u.karl, text="Zweiter Versuch")
    push.sammeln(MITTAG)

    def kaputt(a, i):
        raise OSError("kein Netz")
    for _ in range(push.MAX_VERSUCHE - 1):
        assert push.zustellen(kaputt, MITTAG)["fehler"] == 1
    assert push.zustellen(kaputt, MITTAG)["fehler"] == 1
    assert push.zustellen(u.senden, MITTAG)["nachrichten"] == 0       # aufgegeben


def test_versand_verschluesselt_mit_vapid(monkeypatch):
    """Ganzer Weg von pywebpush gegen eine Attrappe des Push-Dienstes: der Inhalt ist für das Gerät verschlüsselt
    (aes128gcm), das Gerät kann ihn mit seinem Schlüssel lesen, und der Kopf trägt die VAPID-Unterschrift des Servers."""
    import http_ece
    import requests
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    monkeypatch.setenv("FR_BASIS", BASIS)
    geraet = ec.generate_private_key(ec.SECP256R1())
    geheim = os.urandom(16)
    b64 = lambda d: base64.urlsafe_b64encode(d).rstrip(b"=").decode()   # noqa: E731
    a = {"endpoint": "https://push.beispiel.invalid/geraet-1", "auth": b64(geheim),
         "p256dh": b64(geraet.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint))}
    gesehen = []

    class Antwort:
        def __init__(self, code):
            self.status_code, self.text, self.headers, self.reason = code, "", {}, "Gone"

    def post(url, data=None, headers=None, timeout=None, **_):
        gesehen.append((url, data, headers))
        return Antwort(410 if url.endswith("weg") else 201)
    monkeypatch.setattr(requests, "post", post)
    senden = push.webpush_sender()
    assert senden(a, {"titel": "Beispiel", "text": "Grüße", "url": SEITE}) == "ok"
    url, data, kopf = gesehen[0]
    assert url == a["endpoint"] and kopf["content-encoding"] == "aes128gcm" and int(kopf["ttl"]) == push.TTL
    assert kopf["authorization"].startswith("vapid t=") and push.schluessel()[0] in kopf["authorization"]
    klar = http_ece.decrypt(data, private_key=geraet, auth_secret=geheim, version="aes128gcm")
    assert json.loads(klar) == {"titel": "Beispiel", "text": "Grüße", "url": SEITE}
    assert senden({**a, "endpoint": a["endpoint"] + "-weg"}, {"text": "x"}) == "weg"


# ---------- Mein Konto ----------

def test_kontoseite_benachrichtigungen(reise):
    u = reise
    s, _, t = abruf(f"{u.kurl}/konto", cookie=u.karl)
    assert s == 200 and "Benachrichtigungen" in t and "1 Gerät bekommt Benachrichtigungen." in t
    assert 'name="ruhe_von" value="21:30"' in t and 'name="art_version" value="ja" checked' in t
    s, _, t = abruf(f"{u.kurl}/konto", "POST", {"aktion": "push_einstellungen", "art_meldung": "ja", "ruhe_von": "22:15",
                                                "ruhe_bis": "06:45"}, cookie=u.karl)
    assert s == 200 and "Benachrichtigungen gespeichert." in t
    assert push.einstellungen_von(u.karl_id) == {"arten": ["meldung"], "ruhe_von": "22:15", "ruhe_bis": "06:45"}
    s, _, t = abruf(f"{u.kurl}/konto", "POST", {"aktion": "push_aus"}, cookie=u.karl)
    assert "auf allen Geräten ausgeschaltet" in t and konten.push_abos(u.karl_id) == []


# ---------- Anstoß „Veröffentlichen“ (api/aktualisieren) ----------

def test_anstoss_nur_organisatorinnen(reise):
    u = reise
    url = f"{u.rurl}/beispielreise/aktualisieren"
    assert json.loads(abruf(url)[2]) == {"darf": False, "angestossen": None, "ergebnis": None}
    assert json.loads(abruf(url, cookie=u.ida)[2])["darf"] is True
    assert abruf(url, "POST", json_body={})[0] == 401
    s, _, t = abruf(url, "POST", json_body={}, cookie=u.karl)
    assert s == 403 and "Organisator:innen" in t
    s, _, t = abruf(url, "POST", json_body={}, cookie=u.ida)
    a = json.loads(t)["angestossen"]
    assert s == 200 and a["von"] == "Ida" and a["reise"] == "beispielreise"
    datei = u.ablage / rm.ANSTOSS
    assert json.loads(datei.read_text()) == a
    # ein zweiter Anstoß vor dem Veröffentlichen ändert nichts
    assert json.loads(abruf(url, "POST", json_body={}, cookie=u.ida)[2])["angestossen"] == a
