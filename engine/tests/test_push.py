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
from conftest import meldet  # noqa: E402

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
    vorgabe_mail = {"wichtig": "nach_tag", "rueckmeldungen": "nie", "fristen": "nie"}
    assert push.einstellungen({}) == {"push": {"wichtig": True, "rueckmeldungen": True, "fristen": True, "leise": False},
                                      "mail": vorgabe_mail, "ruhe_von": "21:30", "ruhe_bis": "07:00"}
    e = push.einstellungen({"push": {"leise": True, "wichtig": "ja", "erfunden": True},
                            "mail": {"wichtig": "sofort", "fristen": "taeglich", "rueckmeldungen": "erfunden"},
                            "ruhe_von": "22:00", "ruhe_bis": "06:30"})
    assert e["push"] == {"wichtig": True, "rueckmeldungen": True, "fristen": True, "leise": True}
    assert e["mail"] == {"wichtig": "sofort", "rueckmeldungen": "nie", "fristen": "taeglich"} and e["ruhe_von"] == "22:00"
    # alte Einstellungen (arten, bis #517) gelten weiter
    assert push.einstellungen({"arten": ["version"]})["push"] == {"wichtig": False, "rueckmeldungen": False, "fristen": False,
                                                                 "leise": False}
    assert push.einstellungen({"arten": ["aufgabe", "meldung"]})["push"] == {"wichtig": True, "rueckmeldungen": True,
                                                                            "fristen": True, "leise": False}
    # leer, kaputt oder gleich: keine Ruhezeit
    for von, bis in (("", ""), ("25:00", "07:00"), ("08:00", "08:00"), ("8 Uhr", "07:00")):
        e = push.einstellungen({"ruhe_von": von, "ruhe_bis": bis})
        assert e["ruhe_von"] == e["ruhe_bis"] == ""
    assert push.einstellungen("kaputt")["push"] == push.PUSH_VORGABE


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
    push.einstellungen_von(ida, {"push": {"wichtig": True}})
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
    assert s == 400 and meldet(t, "konto.fehler.push_abo_ungueltig")
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
    # Karl: zwei Neuigkeiten in einer Nachricht, die neueste zuerst genannt, Tippen öffnet „Zu tun“
    assert an["karl"]["text"] == "2 Neuigkeiten, zuletzt: Neue Aufgabe für dich: Tickets kaufen (von Ida)"
    assert an["karl"]["url"] == SEITE + "#zu-tun"
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
    push.einstellungen_von(u.karl_id, {"push": {"rueckmeldungen": False}})
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
    for kid in (u.ida_id, u.karl_id):      # neue Versionen sind „Leises“ (#517): aufs Handy nur, wenn eingeschaltet
        push.einstellungen_von(kid, {"push": {**push.PUSH_VORGABE, "leise": True}})
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
    assert s == 200 and "Benachrichtigungen" in t and meldet(t, "konto.push.geraete.one")
    assert 'name="ruhe_von" value="21:30"' in t and 'name="push_wichtig" value="ja" checked' in t
    assert 'name="push_leise" value="ja">' in t and '<option value="nach_tag" selected>' in t and 'name="mail_leise"' not in t
    s, _, t = abruf(f"{u.kurl}/konto", "POST", {"aktion": "push_einstellungen", "push_wichtig": "ja", "mail_wichtig": "sofort",
                                                "mail_fristen": "taeglich", "ruhe_von": "22:15", "ruhe_bis": "06:45"},
                    cookie=u.karl)
    assert s == 200 and meldet(t, "konto.push.gespeichert")
    assert push.einstellungen_von(u.karl_id) == {
        "push": {"wichtig": True, "rueckmeldungen": False, "fristen": False, "leise": False},
        "mail": {"wichtig": "sofort", "rueckmeldungen": "nie", "fristen": "taeglich"}, "ruhe_von": "22:15", "ruhe_bis": "06:45"}
    s, _, t = abruf(f"{u.kurl}/konto", "POST", {"aktion": "push_aus"}, cookie=u.karl)
    assert meldet(t, "konto.push.alle_aus_hinweis") and konten.push_abos(u.karl_id) == []


def test_kontoseite_schalter_der_frieda_app(welt):
    """Entscheidung A (2.11.2026): Ein- und ausgeschaltet wird je Gerät auf Mein Konto; das Abo gehört zu keiner Reise.
    Die Seite bringt Schlüssel und Texte für das Skript mit, Speichern trägt den Zustand (data-aenderung)."""
    u = welt()
    konten.einladen("beispielreise", "karl", KARL, "mitwirkend", "Karl", "Ida")
    karl, _ = anmelden(u, KARL)
    kid = konten.sitzung(karl)["id"]
    oeffentlich, _ = push.schluessel()
    s, h, t = abruf(f"{u.kurl}/konto", cookie=karl)
    assert s == 200 and '<script src="/konto.js" defer></script>' in t and '<link rel="manifest" href="/manifest.webmanifest">' in t
    platz = re.search(r'<div id="push-geraet" hidden data-schluessel="([^"]*)" data-texte="([^"]*)">', t)
    assert platz and platz.group(1) == oeffentlich
    texte_js = json.loads(html.unescape(platz.group(2)))
    assert texte_js["einschalten"] == "Auf diesem Gerät einschalten" and texte_js["schritt2"].startswith("„Zum Home-Bildschirm“")
    # Einstellungen merken Änderungen, Handlungen (alle aus) nicht
    assert t.count("data-aenderung") == 2 and 'action="/konto" data-aenderung autocomplete="off"><input type="hidden" name="aktion" value="push_einstellungen">' in t
    csp = dict((k.lower(), v) for k, v in h).get("content-security-policy", "")
    for quelle in ("script-src 'self'", "worker-src 'self'", "manifest-src 'self'", "connect-src 'self'"):
        assert quelle in csp, csp
    assert "unsafe-inline" not in csp.split("script-src", 1)[1].split(";", 1)[0]
    # Einschalten: nur angemeldet und von Friedas Adresse
    felder = {"aktion": "push_an", "abo": json.dumps(abo("app")), "geraet": "geraet-karl-app", "zeitzone": "Europe/Berlin"}
    assert abruf(f"{u.kurl}/konto", "POST", felder)[0] == 401
    assert abruf(f"{u.kurl}/konto", "POST", felder, cookie=karl, origin="https://boese.invalid")[0] == 403
    s, _, t = abruf(f"{u.kurl}/konto", "POST", {**felder, "abo": "{kaputt"}, cookie=karl)
    assert s == 400 and meldet(t, "konto.fehler.push_abo_ungueltig")
    assert abruf(f"{u.kurl}/konto", "POST", felder, cookie=karl)[0] == 204
    [a] = konten.push_abos(kid)
    assert (a["reise"], a["seite"], a["geraet"], a["zeitzone"]) == ("", f"{BASIS}/konto", "geraet-karl-app", "Europe/Berlin")
    assert abruf(f"{u.kurl}/konto", "POST", felder, cookie=karl)[0] == 204 and len(konten.push_abos(kid)) == 1   # auffrischen
    s, _, t = abruf(f"{u.kurl}/konto?push=an", cookie=karl)
    assert meldet(t, "konto.push.hier_an") and meldet(t, "konto.push.geraete.one")
    # Ausschalten: nur das eigene Abo
    assert abruf(f"{u.kurl}/konto", "POST", {"aktion": "push_ab", "endpoint": abo("app")["endpoint"]}, cookie=karl)[0] == 204
    assert konten.push_abos(kid) == []


def test_ausschalten_dieses_geraets_steht_unter_konfigurieren(welt):
    """Issue #249: Eingeschaltet steht an der Stelle des Einschaltknopfs nur der Zustand; „Auf diesem Gerät ausschalten“
    hat seinen Platz in den Einstellungen hinter „Konfigurieren“, vor „Auf allen Geräten ausschalten“."""
    u = welt()
    konten.einladen("beispielreise", "karl", KARL, "mitwirkend", "Karl", "Ida")
    karl, _ = anmelden(u, KARL)
    kid = konten.sitzung(karl)["id"]
    konten.push_abo_speichern(kid, abo("karl"), "", f"{BASIS}/konto", "geraet-karl-1", "Europe/Berlin")
    s, _, t = abruf(f"{u.kurl}/konto?push=an", cookie=karl)
    assert s == 200
    platz = re.search(r'<div id="push-geraet" hidden[^>]*></div>', t)
    assert platz, "der Platz des Schalters bleibt leer, bis das Skript ihn füllt"
    texte_js = json.loads(html.unescape(re.search(r'data-texte="([^"]*)"', platz.group(0)).group(1)))
    assert texte_js["aus_wo"] == "Ausschalten unter ‚Konfigurieren‘."
    # Der Platz zum Ausschalten liegt in den aufklappbaren Einstellungen, vor dem Formular push_aus
    karte = t[t.index('id="push"'):]
    details = karte[karte.index("<details"):karte.index("</details>")]
    assert '<div id="push-geraet-aus" hidden></div>' in details
    assert details.index('id="push-geraet-aus"') < details.index('name="aktion" value="push_aus"')
    assert t.count('id="push-geraet-aus"') == 1
    # Auch ohne eingeschaltetes Gerät ist der Platz da (das Skript füllt ihn nur, wenn dieses Gerät an ist)
    konten.push_abo_entfernen(kid, abo("karl")["endpoint"])
    _, _, t = abruf(f"{u.kurl}/konto", cookie=karl)
    assert '<div id="push-geraet-aus" hidden></div>' in t


def test_skript_haengt_ausschalten_nicht_an_die_stelle_des_einschaltens():
    """Issue #249, Prüfung des Quelltexts (im Testbrowser lässt sich Push nicht abonnieren): Eingeschaltet zeigt
    #push-geraet nur Zustand und Hinweis; der Knopf zum Ausschalten kommt in #push-geraet-aus."""
    js = (Path(__file__).resolve().parent.parent / "app" / "konto.js").read_text(encoding="utf-8")
    assert 'getElementById("push-geraet-aus")' in js
    eingeschaltet = js[js.index("if (a) {"):]
    eingeschaltet = eingeschaltet[:eingeschaltet.index("\n    }\n")]
    assert 't("aus_wo")' in eingeschaltet
    zeigen_aufruf = re.search(r"return zeigen\((.*)\);", eingeschaltet, re.S)
    assert zeigen_aufruf and "ausschalten" not in zeigen_aufruf.group(1) and not re.search(r"\baus\b", zeigen_aufruf.group(1)), \
        "der Knopf zum Ausschalten darf nicht in #push-geraet stehen"


def test_nachricht_an_die_frieda_app_fuehrt_zur_reise(reise):
    """Ein Abo ohne Reise (Frieda-App) bekommt die Nachrichten aller Reisen; der Link führt zur Reiseseite."""
    u = reise
    konten.push_abo_entfernen(u.karl_id, abo("karl")["endpoint"])
    konten.push_abo_speichern(u.karl_id, abo("karl-app"), "", f"{BASIS}/konto", "geraet-karl-app", "Europe/Berlin")
    aufgabe(u, u.ida, titel="Fähre buchen", zustaendig="karl")
    push.sammeln(MITTAG)
    push.zustellen(u.senden, MITTAG)
    [(ziel, inhalt)] = [g for g in u.gesendet if g[0] == "app"]
    assert inhalt["url"].startswith(SEITE) and inhalt["tag"] == "frieda-beispielreise"

# ---------- Nur über die Frieda-App, sobald es sie gibt (#709) ----------
# iOS schreibt unter jede Nachricht „from <Name der Web-App>“, die das Abo hält. Alte Abos einer Reiseseite (vor
# Entscheidung A, 2.11.2026) gehören der als App installierten Reiseseite; ihre Gerätekennung ist eine andere als die
# der Frieda-App. Hat ein Konto die Frieda-App mit Push, gehen Nachrichten nur noch dorthin.

def _app(e, g="geraet-app"):
    return {"endpoint": e, "geraet": g, "reise": ""}


def _alt(e, reise="beispielreise", g="geraet-alt"):
    return {"endpoint": e, "geraet": g, "reise": reise}


def test_wirksam_nur_app_abos():
    abos = [_app("a2", "g2"), _app("a1", "g1")]
    assert push.wirksam(abos) == abos


def test_wirksam_nur_alte_reise_abos():
    abos = [_alt("r2", "stadtwochenende", "g1"), _alt("r1", "beispielreise", "g1")]
    assert push.wirksam(abos) == abos
    assert push.ziele(push.wirksam(abos), "beispielreise") == push.ziele(abos, "beispielreise")


def test_wirksam_app_abo_verdraengt_alte():
    abos = [_alt("r2", "stadtwochenende", "g-alt-2"), _app("a1"), _alt("r1", "beispielreise", "g-alt-1")]
    assert [a["endpoint"] for a in push.wirksam(abos)] == ["a1"]
    for reise in ("", "beispielreise"):
        assert [a["endpoint"] for a in push.ziele(push.wirksam(abos), reise)] == ["a1"]


def test_wirksam_app_abo_ohne_geraetekennung():
    abos = [_alt("r1", "beispielreise", "g-alt"), _app("a1", "")]
    assert [a["endpoint"] for a in push.ziele(push.wirksam(abos), "beispielreise")] == ["a1"]


def test_zustellen_nur_ueber_die_frieda_app(reise):
    u = reise
    konten.push_abo_speichern(u.ida_id, abo("ida-app"), "", f"{BASIS}/konto", "geraet-ida-app", "Europe/Berlin")
    assert rueckmeldung(u, u.karl)[0] == 201                               # Nachricht zu beispielreise an Ida
    rm.meldung_anlegen(rm.ordner_neu(anlegen=True), [u.ida_id], "loeschung", "reise", "Eine Reise wird gelöscht.")
    assert push.sammeln(MITTAG) == 2
    push.zustellen(u.senden, MITTAG)
    an_ida = [ziel for ziel, _ in u.gesendet if ziel in ("ida", "app")]
    assert an_ida == ["app", "app"], "je Nachricht genau ein Versand, nur an die Frieda-App, nie an das alte Reise-Abo"


def test_kontoseite_zaehlt_geraete_ueber_wirksame_abos(reise):
    u = reise
    konten.push_abo_speichern(u.ida_id, abo("ida-app"), "", f"{BASIS}/konto", "geraet-ida-app", "Europe/Berlin")
    s, _, t = abruf(f"{u.kurl}/konto", cookie=u.ida)
    assert s == 200 and meldet(t, "konto.push.geraete.one") and not meldet(t, "konto.push.geraete.other")


def test_dateien_der_frieda_app():
    """Manifest (Scope /, Start Mein Konto), Worker nur für Push (kein fetch-Handler: er liegt über Anmeldung und OAuth)."""
    app = Path(__file__).resolve().parent.parent / "app"
    m = json.loads((app / "manifest.webmanifest").read_text(encoding="utf-8"))
    assert (m["scope"], m["start_url"], m["display"]) == ("/", "/konto", "standalone")
    assert {i["src"] for i in m["icons"]} >= {"/icon-192.png", "/icon-512.png"}
    sw = (app / "sw.js").read_text(encoding="utf-8")
    assert 'addEventListener("push"' in sw and 'addEventListener("notificationclick"' in sw
    assert 'addEventListener("fetch"' not in sw and "caches." not in sw


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
    datei = u.ablage / rm.ANSTOSS
    ganz = json.loads(datei.read_text())
    assert s == 200 and ganz["von"] == "Ida" and ganz["reise"] == "beispielreise"
    assert a == {"zeit": ganz["zeit"]}      # die Antwort nennt weder Reise noch Person: Sie ist mit jedem Seitenlink lesbar
    # ein zweiter Anstoß vor dem Veröffentlichen ändert nichts
    assert json.loads(abruf(url, "POST", json_body={}, cookie=u.ida)[2])["angestossen"] == a


# ---------- Statushinweise: Push auch ohne Wächter, Mail als Rückfall (#513) ----------

def test_statushinweis_per_push_und_mail_rueckfall(reise):
    u = reise
    status = rm.zustand("beispielreise")["status"]
    jetzt = datetime.datetime.fromtimestamp(MITTAG, datetime.timezone.utc)
    m = rm.meldung_anlegen(u.o, ["Ida", "Karl"], "status", "reise", "Heute geht es los! Auf „unterwegs“ stellen?",
                           schluessel=f"status:{status}:unterwegs", bezug="reise", zeit=jetzt,
                           extra={"status_bei": status, "status_ziel": "unterwegs"})
    assert push.sammeln(MITTAG) == 2                                 # Art status kommt auch ohne Baustein waechter
    # Mail erst nach einem Tag, nur an Personen ohne Gerät, nur einmal
    konten.push_abo_entfernen(u.ida_id, abo("ida")["endpoint"])
    gesendet = []
    post = lambda an, betreff, text: gesendet.append((an, betreff, text))  # noqa: E731
    assert push.mail_rueckfall(post, MITTAG + 23 * 3600) == 0
    assert push.mail_rueckfall(post, MITTAG + 25 * 3600) == 1
    (an, betreff, text), = gesendet
    assert an == IDA and betreff == "Beispiel: wichtig für deine Reise"
    assert text.startswith("Hallo Ida,") and "Auf „unterwegs“ stellen?" in text and SEITE in text
    assert BASIS + "/konto" in text
    assert push.mail_rueckfall(post, MITTAG + 26 * 3600) == 0 and len(gesendet) == 1
    # nach dem Wechsel oder zu alt: keine Mail
    rm.meldung_anlegen(u.o, ["Ida"], "status", "reise", "alt", zeit=jetzt, extra={"status_bei": "idee"})
    rm.meldung_anlegen(u.o, ["Ida"], "status", "reise", "lange her", zeit=jetzt - datetime.timedelta(days=5),
                       extra={"status_bei": status})
    assert push.mail_rueckfall(post, MITTAG + 30 * 3600) == 0
    assert m["id"] and len(gesendet) == 1


def test_mail_rueckfall_fehler_und_kanal(reise, welt):
    u = reise
    status = rm.zustand("beispielreise")["status"]
    konten.push_abo_entfernen(u.ida_id, abo("ida")["endpoint"])
    rm.meldung_anlegen(u.o, ["Ida"], "status", "reise", "Auf „fest“ stellen?",
                       zeit=datetime.datetime.fromtimestamp(MITTAG, datetime.timezone.utc), extra={"status_bei": status})
    versuche = []

    def kaputt(an, betreff, text):
        versuche.append(an)
        raise konten.KontoFehler("konto.fehler.mail_nicht_eingerichtet")
    t = MITTAG + 25 * 3600
    assert push.mail_rueckfall(kaputt, t) == 0 and push.mail_rueckfall(kaputt, t + 60) == 0 and len(versuche) == 1
    for i in range(1, 5):
        push.mail_rueckfall(kaputt, t + i * push.MAIL_PAUSE + 1)
    assert len(versuche) == push.MAIL_VERSUCHE
    # Reise ohne Kanal mail: nichts
    v = welt(regeln={"meldekanal": ["app", "push"]})
    konten.einladen("beispielreise", "ida", IDA, "organisator", "Ida", "Ida")
    rm.meldung_anlegen(v.o, ["Ida"], "status", "reise", "x", zeit=datetime.datetime.fromtimestamp(MITTAG, datetime.timezone.utc),
                       extra={"status_bei": rm.zustand("beispielreise")["status"]})
    assert push.mail_rueckfall(lambda *a: versuche.append(a), t) == 0


# ---------- Stufen und tägliche Zusammenfassung (#517) ----------

def test_gruppen_der_meldungen():
    k = push.kategorie
    assert k("meldung", {"art": "status"}) == k("meldung", {"art": "konflikt"}) == k("meldung", {"art": "betrieb"}) == "wichtig"
    assert k("meldung", {"art": "erinnerung", "schluessel": "ueberfaellig:AG-01:2027-05-01"}) == "wichtig"
    assert k("meldung", {"art": "erinnerung", "schluessel": "frist:AG-01:2027-05-01"}) == "fristen"
    assert k("meldung", {"art": "pruefung"}) == k("version") == "leise"
    assert k("rueckmeldung") == k("aufgabe") == k("meldung", {"art": "hinweis"}) == "rueckmeldungen"


def test_pruefungen_leise_und_wichtiges_sofort_per_mail(reise):
    u = reise
    jetzt = datetime.datetime.fromtimestamp(MITTAG, datetime.timezone.utc)
    rm.meldung_anlegen(u.o, ["Ida"], "pruefung", "U-01", "Preis zuletzt geprüft vor 70 Tagen", zeit=jetzt)
    assert push.sammeln(MITTAG) == 0                                # leise: nicht aufs Handy
    k = rm.meldung_anlegen(u.o, ["Ida"], "konflikt", "V-01", "Ida und Karl haben verschieden entschieden.", zeit=jetzt)
    assert push.sammeln(MITTAG) == 1
    gesendet = []
    post = lambda an, betreff, text: gesendet.append((an, betreff, text))  # noqa: E731
    assert push.mail_rueckfall(post, MITTAG + 60) == 0                # Vorgabe: erst nach einem Tag, und Ida hat ein Gerät
    push.einstellungen_von(u.ida_id, {"mail": {"wichtig": "sofort"}})
    assert push.mail_rueckfall(post, MITTAG + 120) == 1 and "verschieden entschieden" in gesendet[0][2]
    assert "sofort per Mail" in gesendet[0][2]
    assert push.mail_rueckfall(post, MITTAG + 180) == 0                 # nur einmal
    # nach einem Tag, ohne Gerät, aber gelesen: keine Mail
    push.einstellungen_von(u.ida_id, {})
    konten.push_abo_entfernen(u.ida_id, abo("ida")["endpoint"])
    zweite = rm.meldung_anlegen(u.o, ["Ida"], "konflikt", "V-02", "Noch ein Widerspruch.", zeit=jetzt)
    konten.gelesen_merken(u.ida_id, [zweite["id"]])
    assert push.mail_rueckfall(post, MITTAG + 25 * 3600) == 0 and len(gesendet) == 1 and k["id"]


def test_taegliche_zusammenfassung(reise):
    u = reise
    push.einstellungen_von(u.ida_id, {"mail": {"rueckmeldungen": "taeglich"}})
    assert rueckmeldung(u, u.karl)[0] == 201
    rueckmeldung(u, u.karl, text="Und abends Pizza?")
    push.sammeln(MITTAG)                                             # 12:00 in Berlin: aufs Handy und gesammelt
    gesendet = []
    post = lambda an, betreff, text: gesendet.append((an, betreff, text))  # noqa: E731
    assert push.zusammenfassungen(post, MITTAG) == 1                 # nach 7:30: noch heute
    (an, betreff, text), = gesendet
    assert an == IDA and betreff == "Frieda: 2 Neuigkeiten aus deinen Reisen"
    assert "Karl schreibt: Wir landen erst 21 Uhr." in text and "Und abends Pizza?" in text and "Beispiel" in text
    assert push.zusammenfassungen(post, MITTAG + 3600) == 0           # leer und heute schon verschickt
    rueckmeldung(u, u.karl, text="Noch was")
    push.sammeln(MITTAG + 3600)
    assert push.zusammenfassungen(post, MITTAG + 7200) == 0           # einmal am Tag
    morgen_frueh = MITTAG + 18 * 3600                                # 6:00 in Berlin: zu früh
    assert push.zusammenfassungen(post, morgen_frueh) == 0
    assert push.zusammenfassungen(post, morgen_frueh + 2 * 3600) == 1 and "Noch was" in gesendet[1][2]
    # Karl hat nichts gewählt: keine Zusammenfassung
    assert all(a == IDA for a, _, _ in gesendet)


# ---------- Meldungen ohne Reise: Warteliste, Bitte „Reisen anlegen“, neue Reise, Löschung (#631) ----------
# Sie liegen in der Ablage ohne Reise (<Konten>/neu/meldungen.jsonl) und gehen an Konto-Kennungen. Der Push-Dienst liest
# sie wie die Meldungen einer Reise: Gruppe rueckmeldungen, Ruhezeit, tägliche Zusammenfassung, einmal je Eintrag.

import anmeldung  # noqa: E402
import texte  # noqa: E402
from conftest import text  # noqa: E402

BEISPIELE = Path(__file__).resolve().parents[2] / "beispiel" / "reisen"
TOM = {"name": "Tom", "email": "tom@beispiel.invalid"}


def betreiber(kid, email, name, sprache="de", rechte="betreiber", gesperrt=0):
    """Erfundenes Konto mit Rechten und Sprache (Betreiber:innen bekommen die Anfragen ohne Reise)."""
    with closing(konten.db()) as v, v:
        v.execute("INSERT INTO konten (id, email, name, angelegt, sprache, rechte, gesperrt) VALUES (?,?,?,?,?,?,?)",
                  (kid, email, name, "2026-11-01", sprache, rechte, gesperrt))
    return kid


def warteschlange():
    with closing(konten.db()) as v:
        return [dict(z) for z in v.execute("SELECT konto, reise, art, text, ziel FROM push_warteschlange ORDER BY id")]


@pytest.fixture
def betrieb(welt):
    """Ida (deutsch) und Karl (englisch) betreiben die Instanz; beide haben die Frieda-App mit Benachrichtigungen (Berlin).
    Der erste Lauf geschieht, bevor es die Ablage ohne Reise gibt: die erste Meldung danach kommt trotzdem an."""
    u = welt()
    u.ida = betreiber("K-ida", IDA, "Ida")
    u.karl = betreiber("K-karl", KARL, "Karl", sprache="en")
    for kid, n in ((u.ida, "ida"), (u.karl, "karl")):
        konten.push_abo_speichern(kid, abo(n), "", f"{BASIS}/konto", f"geraet-{n}-1", "Europe/Berlin")
    assert push.sammeln(MITTAG) == 0
    u.gesendet = []

    def senden(a, inhalt):
        u.gesendet.append((a["endpoint"].rsplit("-", 1)[1], inhalt))
        return "ok"
    u.senden = senden
    return u


def warteliste(email="lea@beispiel.invalid"):
    """Wie anmeldung.py, wenn jemand die Adresse auf der Warteliste bestätigt."""
    anmeldung.betreiber_melden(None, "anfrage_warteliste",
                               texte.t(texte.VORGABE_REISE, "konto.betreiber.warteliste", email=email),
                               [("konto.meldungen.text.anfrage_warteliste", {"email": email})])


def test_warteliste_meldung_geht_als_push_an_betreiber(betrieb):
    u = betrieb
    rm.meldung_anlegen(rm.ordner_neu(anlegen=True), [u.ida], "anfrage_warteliste", "reise", "lea@beispiel.invalid wartet.")
    assert push.sammeln(MITTAG) == 1
    [w] = warteschlange()
    assert (w["konto"], w["reise"], w["art"], w["ziel"]) == (u.ida, "", "meldung", "freischalten")
    erg = push.zustellen(u.senden, MITTAG)
    assert erg["nachrichten"] == 1 and erg["geraete"] == 1
    [(geraet, inhalt)] = u.gesendet
    assert geraet == "ida" and inhalt["text"] == "lea@beispiel.invalid wartet."


def test_bitte_reisen_anlegen_geht_als_push(betrieb):
    u = betrieb
    anmeldung.betreiber_melden(TOM)                                   # an alle Betreiber:innen
    assert push.sammeln(MITTAG) == 2
    push.zustellen(u.senden, MITTAG)
    an = dict(u.gesendet)
    assert set(an) == {"ida", "karl"}
    assert an["ida"]["text"] == text("konto.meldungen.text.anfrage_reisen", **TOM)
    assert an["ida"]["url"] == f"{BASIS}/konto#freischalten"


@pytest.mark.parametrize("sprache", ["de", "en"])
def test_nachricht_ohne_reise_hat_titel_und_ziel_mein_konto(betrieb, monkeypatch, sprache):
    u = betrieb
    kid = u.ida if sprache == "de" else u.karl
    assert text("push.titel_ohne_reise", sprache) != "push.titel_ohne_reise", "Schlüssel fehlt im Katalog"
    for ziel in ("freischalten", "meldungen"):
        n = push.nachricht(kid, "", [{"art": "meldung", "text": "Etwas Neues", "ziel": ziel}])
        assert n["titel"] == text("push.titel_ohne_reise", sprache)
        assert n["url"] == f"{BASIS}/konto#{ziel}" and n["tag"] == "frieda-konto" and n["text"] == "Etwas Neues"
    # mehrere: eine Nachricht, Ziel die Meldungen auf Mein Konto
    n = push.nachricht(kid, "", [{"art": "meldung", "text": "A", "ziel": "freischalten"},
                                 {"art": "meldung", "text": "B", "ziel": "meldungen"}])
    assert n["titel"] == text("push.titel_ohne_reise", sprache) and n["url"] == f"{BASIS}/konto#meldungen"
    assert "#reise" not in n["url"] and n["tag"] == "frieda-konto"
    monkeypatch.delenv("FR_BASIS")
    assert push.nachricht(kid, "", [{"art": "meldung", "text": "x", "ziel": "freischalten"}])["url"] == "/konto#freischalten"


def test_ruhezeit_haelt_meldung_ohne_reise_zurueck(betrieb):
    u = betrieb
    rm.meldung_anlegen(rm.ordner_neu(anlegen=True), [u.ida], "anfrage_warteliste", "reise", "Spät bestätigt")
    assert push.sammeln(NACHT) == 1
    erg = push.zustellen(u.senden, NACHT)                            # 0:00 in Berlin
    assert erg["warten"] == 1 and not u.gesendet
    rm.meldung_anlegen(rm.ordner_neu(), [u.ida], "anfrage_reisen", "reise", "Noch jemand")
    push.sammeln(NACHT + 60)
    erg = push.zustellen(u.senden, NACHT + 7.5 * 3600)               # 7:30: beide als eine Nachricht
    assert erg["nachrichten"] == 1
    [(geraet, inhalt)] = u.gesendet
    assert geraet == "ida" and inhalt["text"].endswith("Noch jemand") and inhalt["tag"] == "frieda-konto"


def test_gruppe_rueckmeldungen_aus_kein_push(betrieb):
    u = betrieb
    push.einstellungen_von(u.ida, {"push": {"rueckmeldungen": False}})
    konten.push_abo_entfernen(u.karl, abo("karl")["endpoint"])        # Karl ohne Gerät
    anmeldung.betreiber_melden(TOM)
    assert push.sammeln(MITTAG) == 0 and warteschlange() == []
    assert push.stand("meldungen:_neu") is not None                  # gesehen ist es trotzdem


def test_mail_taeglich_nimmt_meldung_ohne_reise_mit_eigener_ueberschrift(betrieb):
    u = betrieb
    push.einstellungen_von(u.ida, {"mail": {"rueckmeldungen": "taeglich"}})
    push.einstellungen_von(u.karl, {"mail": {"rueckmeldungen": "taeglich"}})
    konten.push_abo_entfernen(u.karl, abo("karl")["endpoint"])        # auch ohne Gerät in die Zusammenfassung
    warteliste()
    push.sammeln(MITTAG)
    gesendet = []
    post = lambda an, betreff, text_: gesendet.append((an, betreff, text_))  # noqa: E731
    assert push.zusammenfassungen(post, MITTAG) == 2
    mails = {an: t for an, _, t in gesendet}
    for an, sp in ((IDA, "de"), (KARL, "en")):
        assert text("push.mail.zusammenfassung.ohne_reise", sp) != "push.mail.zusammenfassung.ohne_reise"
        zeilen = mails[an].splitlines()
        kopf = [z for z in zeilen if text("push.mail.zusammenfassung.ohne_reise", sp) in z]
        assert len(kopf) == 1 and f"{BASIS}/konto" in kopf[0], mails[an]
        eintrag = f"- {text('konto.meldungen.text.anfrage_warteliste', sp, email='lea@beispiel.invalid')}"
        assert eintrag in zeilen and zeilen.index(eintrag) > zeilen.index(kopf[0])
        assert ":" not in [z.strip() for z in zeilen], "keine leere Überschrift einer Reise"
    # Mail „nie“: kein Eintrag
    for kid in (u.ida, u.karl):
        push.einstellungen_von(kid, {"mail": {"rueckmeldungen": "nie"}})
    warteliste("max@beispiel.invalid")
    push.sammeln(MITTAG + 86400)
    assert push.zusammenfassungen(post, MITTAG + 86400) == 0 and len(gesendet) == 2


def test_erster_lauf_merkt_nur(welt):
    welt()
    ida = betreiber("K-ida", IDA, "Ida")
    konten.push_abo_speichern(ida, abo("ida"), "", f"{BASIS}/konto", "geraet-ida-1", "Europe/Berlin")
    push.einstellungen_von(ida, {"mail": {"rueckmeldungen": "taeglich"}})
    rm.meldung_anlegen(rm.ordner_neu(anlegen=True), [ida], "anfrage_warteliste", "reise", "Altbestand")
    assert push.sammeln(MITTAG) == 0
    assert warteschlange() == [] and not push.stand(f"sammel:{ida}")
    rm.meldung_anlegen(rm.ordner_neu(), [ida], "anfrage_warteliste", "reise", "Danach")
    assert push.sammeln(MITTAG) == 1 and [w["text"] for w in warteschlange()] == ["Danach"]


def test_kein_doppelversand(betrieb):
    u = betrieb
    o = rm.ordner_neu(anlegen=True)
    rm.meldung_anlegen(o, [u.ida], "anfrage_warteliste", "reise", "Erste")
    assert push.sammeln(MITTAG) == 1
    assert push.sammeln(MITTAG) == 0 and push.sammeln(MITTAG) == 0 and len(warteschlange()) == 1
    # zwei Meldungen in derselben Sekunde gehen beide durch, auch über zwei Läufe
    zeit = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=5)
    rm.meldung_anlegen(o, [u.ida], "anfrage_warteliste", "reise", "Zweite", zeit=zeit)
    assert push.sammeln(MITTAG) == 1
    rm.meldung_anlegen(o, [u.ida], "anfrage_warteliste", "reise", "Dritte", zeit=zeit)
    assert push.sammeln(MITTAG) == 1 and push.sammeln(MITTAG) == 0
    assert [w["text"] for w in warteschlange()] == ["Erste", "Zweite", "Dritte"]


def test_nur_bestehende_nicht_gesperrte_konten(betrieb):
    u = betrieb
    gesperrt = betreiber("K-weg", "weg@beispiel.invalid", "Weg", gesperrt=1)
    konten.push_abo_speichern(gesperrt, abo("weg"), "", f"{BASIS}/konto", "geraet-weg-1", "Europe/Berlin")
    rm.meldung_anlegen(rm.ordner_neu(anlegen=True), [gesperrt, "K-unbekannt", "Karl", u.ida], "anfrage_reisen", "reise", "Bitte")
    assert push.sammeln(MITTAG) == 1
    assert [w["konto"] for w in warteschlange()] == [u.ida]


def test_neue_reise_und_loeschung_laufen_denselben_weg(betrieb):
    u = betrieb
    o = rm.ordner_neu(anlegen=True)
    rm.meldung_anlegen(o, [u.ida], "neue_reise", "neue-reise", "Deine neue Reise ist angelegt.",
                       teile=[("konto.meldungen.text.neue_reise", {"titel": "Neue Reise"})])
    rm.meldung_anlegen(o, ["Karl"], "neue_reise", "andere-reise", "Rückfall mit Namen")   # Name statt Kennung: nichts
    rm.meldung_anlegen(o, [u.karl], "loeschung", "reise", "Die Reise wird gelöscht.")
    assert push.sammeln(MITTAG) == 2
    assert [(w["konto"], w["reise"], w["art"], w["ziel"]) for w in warteschlange()] == [
        (u.ida, "", "meldung", "meldungen"), (u.karl, "", "meldung", "meldungen")]
    push.zustellen(u.senden, MITTAG)
    an = dict(u.gesendet)
    assert an["ida"]["url"] == an["karl"]["url"] == f"{BASIS}/konto#meldungen"
    assert an["ida"]["titel"] == text("push.titel_ohne_reise") and an["karl"]["titel"] == text("push.titel_ohne_reise", "en")
    # gleiche Gruppe: ausgeschaltet kommt nichts
    push.einstellungen_von(u.ida, {"push": {"rueckmeldungen": False}})
    rm.meldung_anlegen(o, [u.ida], "loeschung", "reise", "Noch eine Löschung")
    assert push.sammeln(MITTAG) == 0


def test_text_in_sprache_des_empfaengers(betrieb):
    u = betrieb
    warteliste()                                                     # mit Teilen: je Sprache aus dem Katalog
    rm.meldung_anlegen(rm.ordner_neu(), [u.ida, u.karl], "anfrage_reisen", "reise", "Nur gespeicherter Text")
    assert push.sammeln(MITTAG) == 4
    texte_je = {}
    for w in warteschlange():
        texte_je.setdefault(w["konto"], []).append(w["text"])
    email = "lea@beispiel.invalid"
    assert texte_je[u.ida] == [text("konto.meldungen.text.anfrage_warteliste", "de", email=email), "Nur gespeicherter Text"]
    assert texte_je[u.karl] == [text("konto.meldungen.text.anfrage_warteliste", "en", email=email), "Nur gespeicherter Text"]


def test_bestand_mit_beiden_beispielreisen_unveraendert(reise):
    """Beide Beispielreisen in der Ablage: Meldungen der Reise kommen wie bisher, die ohne Reise zusätzlich und getrennt."""
    import bauen
    u = reise
    bauen.bauen(BEISPIELE / "stadtwochenende", u.seiten / "stadtwochenende")
    (u.ablage / "stadtwochenende").mkdir()
    with closing(konten.db()) as v, v:
        v.execute("UPDATE konten SET rechte = 'betreiber' WHERE id = ?", (u.ida_id,))
    assert push.sammeln(MITTAG) == 0                                 # ohne neue Meldungen: nichts
    rm.meldung_anlegen(u.o, ["Karl"], "konflikt", "V-01", "Ida und Max haben verschieden entschieden.")
    warteliste()
    assert push.sammeln(MITTAG) == 2 and push.sammeln(MITTAG) == 0
    assert {(w["konto"], w["reise"]) for w in warteschlange()} == {(u.karl_id, "beispielreise"), (u.ida_id, "")}
    assert push.stand("meldungen:stadtwochenende") is not None and push.stand("meldungen:beispielreise") is not None
    push.zustellen(u.senden, MITTAG)
    an = dict(u.gesendet)
    assert an["karl"]["url"] == SEITE + "#V-01" and an["karl"]["tag"] == "frieda-beispielreise"
    assert an["ida"]["url"] == f"{BASIS}/konto#freischalten" and an["ida"]["tag"] == "frieda-konto"


def test_neue_texte_in_allen_sprachen():
    for sp in texte.SPRACHEN:
        for k in ("push.titel_ohne_reise", "push.mail.zusammenfassung.ohne_reise"):
            assert texte.t(sp, k) != k, f"{k} fehlt in {sp}"
            assert not re.search(r"\{[^{}]*\}", texte.t(sp, k)), f"{k} hat in {sp} Platzhalter"
