"""Tests für Paket J2 (Issue #46): Anmeldeseiten und Rückmeldedienst mit Sitzung. Alle Beispiele sind erfunden."""
import http.client
import json
import re
import sys
import urllib.parse
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import konten  # noqa: E402
from test_regeln import Umgebung  # noqa: E402

BASIS = "https://frieda.beispiel.invalid"
SEITE = f"{BASIS}/beispielreise-0123456789abcdef01234567/"
IDA, KARL, MO = "ida@beispiel.invalid", "karl@beispiel.invalid", "mo@beispiel.invalid"


@pytest.fixture
def welt(tmp_path, monkeypatch):
    monkeypatch.setenv("FR_BASIS", BASIS)
    monkeypatch.setenv("FR_MAIL_DATEI", str(tmp_path / "mails.jsonl"))
    erzeugt = []

    def neu(**kw):
        u = Umgebung(tmp_path / f"u{len(erzeugt)}", monkeypatch, **kw)
        links = tmp_path / f"seiten{len(erzeugt)}.json"
        links.write_text(json.dumps({"beispielreise": SEITE}))
        monkeypatch.setenv("KN_SEITENLINKS", str(links))
        u.mails = tmp_path / "mails.jsonl"
        erzeugt.append(u)
        return u
    yield neu
    for u in erzeugt:
        u.schliessen()


def abruf(url, methode="GET", felder=None, cookie=None, origin=BASIS, json_body=None, kopf=None):
    """Eine Anfrage ohne Weiterleitungen zu folgen. -> (status, kopfzeilen, text)"""
    t = urllib.parse.urlsplit(url)
    c = http.client.HTTPConnection(t.hostname, t.port, timeout=10)
    h = dict(kopf or {})
    body = None
    if felder is not None:
        body = urllib.parse.urlencode(felder).encode()
        h["Content-Type"] = "application/x-www-form-urlencoded"
    if json_body is not None:
        body = json.dumps(json_body).encode()
        h["Content-Type"] = "application/json"
    if cookie:
        h["Cookie"] = f"__Host-frieda={cookie}"
    if origin and methode != "GET":
        h["Origin"] = origin
    c.request(methode, t.path + (f"?{t.query}" if t.query else ""), body=body, headers=h)
    r = c.getresponse()
    return r.status, r.getheaders(), r.read().decode()


def kopf(kopfzeilen, name):
    return [v for k, v in kopfzeilen if k.lower() == name.lower()]


def code_aus(u, an):
    zeilen = [json.loads(z) for z in u.mails.read_text().splitlines()]
    m = [z for z in zeilen if z["an"] == an][-1]
    return re.search(r"Dein Code für Frieda: (\d{3}) (\d{3})", m["text"]).expand(r"\1\2")


def anmelden(u, an, name=None, einladung="", zurueck=""):
    """Ganzer Ablauf über die Seiten. -> (sitzungs_token, Location)"""
    s, _, t = abruf(f"{u.kurl}/anmelden", "POST", {"schritt": "adresse", "email": an, "einladung": einladung,
                                                   "zurueck": zurueck})
    assert s == 200 and "Code eingeben" in t, t
    felder = {"schritt": "code", "email": an, "code": code_aus(u, an), "einladung": einladung, "zurueck": zurueck}
    if name:
        felder["name"] = name
    s, h, t = abruf(f"{u.kurl}/anmelden", "POST", felder)
    assert s == 303, t
    keks = kopf(h, "Set-Cookie")[0]
    return re.match(r"__Host-frieda=([^;]+)", keks).group(1), kopf(h, "Location")[0]


def test_anmelden_von_null(welt):
    u = welt()
    s, h, t = abruf(f"{u.kurl}/anmelden")
    assert s == 200 and "Bei Frieda anmelden" in t and "Konto jederzeit selbst löschen" in t
    assert "frame-ancestors 'none'" in kopf(h, "Content-Security-Policy")[0]
    s, _, t = abruf(f"{u.kurl}/anmelden", "POST", {"schritt": "adresse", "email": "Ida@Beispiel.invalid"})
    assert s == 200 and IDA in t
    code = code_aus(u, IDA)
    s, h, t = abruf(f"{u.kurl}/anmelden", "POST", {"schritt": "code", "email": IDA, "code": code})
    assert s == 200 and "Wie heißt du?" in t and not kopf(h, "Set-Cookie")      # neues Konto: Name fehlt
    s, h, t = abruf(f"{u.kurl}/anmelden", "POST", {"schritt": "code", "email": IDA, "code": code, "name": "Ida"})
    assert s == 303 and kopf(h, "Location") == ["/konto"]
    keks = kopf(h, "Set-Cookie")[0]
    for teil in ("__Host-frieda=", "Path=/", "Secure", "HttpOnly", "SameSite=Lax"):
        assert teil in keks
    token = re.match(r"__Host-frieda=([^;]+)", keks).group(1)
    s, _, t = abruf(f"{u.kurl}/konto", cookie=token)
    assert s == 200 and "Hallo Ida" in t and "Noch keine Reisen" in t and "Ich möchte Reisen anlegen" in t


def test_aenderungen_nur_von_friedas_adresse(welt):
    u = welt()
    for origin in (None, "https://www.beispiel.invalid", "null"):
        s, _, t = abruf(f"{u.kurl}/anmelden", "POST", {"schritt": "adresse", "email": IDA}, origin=origin)
        assert s == 403 and "nicht von Frieda" in t
    assert not u.mails.exists()


def test_link_aus_der_mail_ohne_code(welt):
    u = welt()
    abruf(f"{u.kurl}/anmelden", "POST", {"schritt": "adresse", "email": "ida+reise@beispiel.invalid"})
    m = json.loads(u.mails.read_text().splitlines()[-1])["text"]
    link = re.search(r"https://frieda\.beispiel\.invalid(/anmelden\?\S+)", m).group(1)
    code = re.search(r"(\d{3}) (\d{3})", m).expand(r"\1\2")
    assert code not in link and "ida%2Breise%40beispiel.invalid" in link
    s, h, t = abruf(f"{u.kurl}{link}")
    assert s == 200 and "Code eingeben" in t and "ida+reise@beispiel.invalid" in t and not kopf(h, "Set-Cookie")
    s, h, _ = abruf(f"{u.kurl}/anmelden", "POST", {"schritt": "code", "email": "ida+reise@beispiel.invalid",
                                                    "code": code, "name": "Ida"})
    assert s == 303 and kopf(h, "Set-Cookie")


def test_rueckweg_nur_auf_friedas_adresse(welt):
    u = welt()
    _, ziel = anmelden(u, IDA, "Ida", zurueck="//boese.invalid/x")
    assert ziel == "/konto"
    _, ziel = anmelden(u, KARL, "Karl", zurueck="/beispielreise-0123456789abcdef01234567/#wuensche")
    assert ziel == "/beispielreise-0123456789abcdef01234567/#wuensche"


def test_einladung_mit_anderer_adresse(welt):
    u = welt()
    konten.einladen("beispielreise", "karl", "karl.arbeit@beispiel.invalid", "mitwirkend", "Karl", "Ida",
                    titel="Malerweg")
    link = re.search(r"/einladung/(\S+)", json.loads(u.mails.read_text().splitlines()[-1])["text"]).group(1)
    s, _, t = abruf(f"{u.kurl}/einladung/{link}")
    assert s == 200 and "Ida hat Karl zur Reise" in t and "Beispielreise" in t and "andere E-Mail-Adresse" in t
    token, ziel = anmelden(u, KARL, einladung=link)            # Name kommt aus der Einladung
    assert ziel == SEITE                                         # direkt zur Reise
    s, _, t = abruf(f"{u.kurl}/konto", cookie=token)
    assert "Hallo Karl" in t and "Beispielreise" in t and "bringt ein" in t and SEITE in t
    s, _, t = abruf(f"{u.kurl}/einladung/{link}")
    assert "schon angenommen" in t
    assert abruf(f"{u.kurl}/einladung/{'x' * 40}")[0] == 404


def test_einladung_angemeldet_annehmen(welt):
    u = welt()
    token, _ = anmelden(u, KARL, "Karl")
    konten.einladen("beispielreise", "karl", "karl.arbeit@beispiel.invalid", "mitwirkend", "Karl", "Ida")
    link = re.search(r"/einladung/(\S+)", json.loads(u.mails.read_text().splitlines()[-1])["text"]).group(1)
    s, _, t = abruf(f"{u.kurl}/einladung/{link}", cookie=token)
    assert "Annehmen als Karl" in t
    s, h, _ = abruf(f"{u.kurl}/einladung/{link}", "POST", {}, cookie=token)
    assert s == 303 and kopf(h, "Location") == [SEITE]


def mitmachen(u, token=None, origin=BASIS, kopf=None, **eintrag):
    return abruf(f"{u.rurl}/beispielreise/rueckmeldungen", "POST", cookie=token, origin=origin, kopf=kopf,
                 json_body={"art": "Kommentar", "ziel": "T-01", "text": "Schöner Tag", **eintrag})


def test_rueckmeldung_traegt_den_namen_aus_der_sitzung(welt):
    u = welt()
    konten.einladen("beispielreise", "karl", KARL, "mitwirkend", "Karl", "Ida")
    token, _ = anmelden(u, KARL)
    s, _, t = mitmachen(u, token, name="Jemand anderes")
    assert s == 201 and json.loads(t)["name"] == "Karl"
    s, _, t = abruf(f"{u.rurl}/beispielreise/ich", cookie=token)
    ich = json.loads(t)
    assert ich["person"] == {"schluessel": "karl", "name": "Karl", "rolle": "mitwirkend"}
    assert ich["konto"]["email"] == KARL and ich["basis"] == BASIS and ich["anmeldung"] == "uebergang"
    assert json.loads(abruf(f"{u.rurl}/beispielreise/ich")[2])["konto"] is None
    # mit Sitzung, aber von fremder Adresse (CSRF): nein
    s, _, t = mitmachen(u, token, origin="https://www.beispiel.invalid", name="Karl")
    assert s == 403 and "nicht von Frieda" in t
    # Übergang: ohne Anmeldung geht der eingetippte Name noch
    s, _, t = mitmachen(u, name="Hanna", text="Ohne Anmeldung")
    assert s == 201 and json.loads(t)["name"] == "Hanna"


def test_regel_noetig(welt):
    u = welt(regeln={"anmeldung": "noetig"})
    s, _, t = mitmachen(u, name="Hanna")
    assert s == 401 and "melde dich an" in t
    token, _ = anmelden(u, MO, "Mo")                            # angemeldet, aber nicht eingeladen
    s, _, t = mitmachen(u, token)
    assert s == 403 and "nicht eingeladen" in t
    konten.einladen("beispielreise", "karl", KARL, "mitwirkend", "Karl", "Ida")
    karl, _ = anmelden(u, KARL)
    ida_t = None
    konten.einladen("beispielreise", "ida", IDA, "organisator", "Ida", "Ida")
    ida_t, _ = anmelden(u, IDA)
    s, _, t = mitmachen(u, ida_t)
    rid = json.loads(t)["id"]
    # Zurückziehen nur Eigenes
    s, _, t = abruf(f"{u.rurl}/beispielreise/rueckmeldungen/{rid}", "DELETE", cookie=karl)
    assert s == 403 and "geschrieben hat" in t
    assert abruf(f"{u.rurl}/beispielreise/rueckmeldungen/{rid}", "DELETE")[0] == 401
    assert abruf(f"{u.rurl}/beispielreise/rueckmeldungen/{rid}", "DELETE", cookie=ida_t)[0] == 200
    # Aufgaben ebenso
    s, _, t = abruf(f"{u.rurl}/beispielreise/aufgaben", "POST", json_body={"titel": "Karten kaufen", "name": "X"})
    assert s == 401
    s, _, t = abruf(f"{u.rurl}/beispielreise/aufgaben", "POST", cookie=karl,
                   json_body={"titel": "Karten kaufen", "name": "X"})
    assert s == 201 and json.loads(t)["erstellt_von"] == "Karl"


def test_einplanen_als_angemeldete_organisatorin(welt):
    u = welt()
    konten.einladen("beispielreise", "ida", IDA, "organisator", "Ida", "Ida")
    konten.einladen("beispielreise", "karl", KARL, "mitwirkend", "Karl", "Ida")
    ida_t, _ = anmelden(u, IDA)
    karl_t, _ = anmelden(u, KARL)
    s, _, t = mitmachen(u, karl_t, art="Wunsch", ziel="wuensche", text="Bastei bei Sonnenaufgang")
    rid = json.loads(t)["id"]
    url = f"{u.rurl}/beispielreise/rueckmeldungen/{rid}"
    assert abruf(url, "PATCH", cookie=karl_t, json_body={"eingeplant": True})[0] == 403
    assert abruf(url, "PATCH", json_body={"name": "Ida", "eingeplant": True})[0] == 403    # nur eingetippt
    s, _, t = abruf(url, "PATCH", cookie=ida_t, json_body={"eingeplant": True, "bezug": ["T-02"]})
    assert s == 200 and json.loads(t)["eingeplant"]["wer"] == "Ida"


def test_kontoseite(welt):
    u = welt()
    ida, _ = anmelden(u, IDA, "Ida")
    konten.recht_setzen(konten.konto_per_email(IDA)["id"], "betreiber")
    mo, _ = anmelden(u, MO, "Mo")
    assert abruf(f"{u.kurl}/konto")[0] == 303                    # ohne Anmeldung zur Anmeldeseite
    assert abruf(f"{u.kurl}/konto", "POST", {"aktion": "name", "name": "Mo Beispiel"}, cookie=mo)[0] == 303
    assert konten.konto_per_email(MO)["name"] == "Mo Beispiel"
    # Bitte „Reisen anlegen“: Meldung an den Betreiber, der auf seiner Kontoseite entscheidet
    abruf(f"{u.kurl}/konto", "POST", {"aktion": "anfragen"}, cookie=mo)
    assert "liegt beim Betreiber" in abruf(f"{u.kurl}/konto", cookie=mo)[2]
    m = [json.loads(z) for z in (u.ablage / "_neu" / "meldungen.jsonl").read_text().splitlines()]
    assert m[-1]["an"] == ["Ida"] and "Mo Beispiel" in m[-1]["text"]
    s, _, t = abruf(f"{u.kurl}/konto", cookie=ida)
    assert "Mo Beispiel" in t and "Freischalten" in t
    mo_id = konten.konto_per_email(MO)["id"]
    assert abruf(f"{u.kurl}/konto", "POST", {"aktion": "freischalten", "wer": mo_id}, cookie=mo)[0] == 400
    abruf(f"{u.kurl}/konto", "POST", {"aktion": "freischalten", "wer": mo_id}, cookie=ida)
    assert "Du darfst Reisen anlegen" in abruf(f"{u.kurl}/konto", cookie=mo)[2]
    # Adresse ändern mit Code an die neue Adresse
    s, _, t = abruf(f"{u.kurl}/konto", "POST", {"aktion": "adresse_code", "email": IDA}, cookie=mo)
    assert "gehört schon zu einem Konto" in t
    neu = "mo.neu@beispiel.invalid"
    s, _, t = abruf(f"{u.kurl}/konto", "POST", {"aktion": "adresse_code", "email": neu}, cookie=mo)
    assert "Code an die neue Adresse" in t
    code = re.search(r"(\d{3}) (\d{3})", json.loads(u.mails.read_text().splitlines()[-1])["text"]).expand(r"\1\2")
    assert abruf(f"{u.kurl}/konto", "POST", {"aktion": "adresse", "email": neu, "code": code}, cookie=mo)[0] == 303
    assert konten.konto(mo_id)["email"] == neu
    # Abmelden, überall abmelden, löschen
    s, h, _ = abruf(f"{u.kurl}/abmelden", "POST", {}, cookie=mo)
    assert s == 303 and "Max-Age=0" in kopf(h, "Set-Cookie")[0] and konten.sitzung(mo) is None
    assert abruf(f"{u.kurl}/konto", "POST", {"aktion": "loeschen"}, cookie=ida)[0] == 400   # ohne Häkchen nicht
    s, _, t = abruf(f"{u.kurl}/konto", "POST", {"aktion": "loeschen", "sicher": "ja"}, cookie=ida)
    assert s == 200 and "Konto gelöscht" in t and konten.konto_per_email(IDA) is None


def test_konnektor_braucht_das_geheimnis(welt):
    """Der Konnektor ruft den Rückmeldedienst mit dem Dienst-Geheimnis; ohne es wäre es die Seite."""
    u = welt(regeln={"anmeldung": "noetig"})
    from test_regeln import KARL as KARL_LINK
    text, fehler = u.werkzeug(KARL_LINK, "rueckmeldung_geben", art="Kommentar", ziel="T-01", text="Aus der App")
    assert not fehler, text
    e = [json.loads(z) for z in (u.o / "eingang.jsonl").read_text().splitlines()]
    assert e[-1]["name"] == "Karl" and e[-1]["text"] == "Aus der App"
    s, _, _ = mitmachen(u, name="Karl", kopf={"X-Frieda-Dienst": "geraten"})
    assert s == 401


def test_doppeltes_absenden_zeigt_keinen_fehler(welt):
    """Handy sendet das Formular zweimal ab (28./30.10.2026): erst Erfolg, dann schon angemeldet, nicht „Code stimmt nicht“."""
    u = welt()
    abruf(f"{u.kurl}/anmelden", "POST", {"schritt": "adresse", "email": IDA})
    felder = {"schritt": "code", "email": IDA, "code": code_aus(u, IDA), "name": "Ida"}
    s, h, _ = abruf(f"{u.kurl}/anmelden", "POST", felder)
    assert s == 303
    token = re.match(r"__Host-frieda=([^;]+)", kopf(h, "Set-Cookie")[0]).group(1)
    s, h, t = abruf(f"{u.kurl}/anmelden", "POST", felder, cookie=token)       # mit Sitzung
    assert s == 303 and kopf(h, "Location") == ["/konto"], t
    s, h, t = abruf(f"{u.kurl}/anmelden", "POST", felder)                     # Cookie noch nicht angekommen
    assert s == 303 and kopf(h, "Set-Cookie"), t
    s, _, t = abruf(f"{u.kurl}/anmelden", "POST", {**felder, "code": "000000"})
    assert s == 200 and "stimmt nicht" in t
    s, _, t = abruf(f"{u.kurl}/anmelden", "POST", {**felder, "code": "000000"})
    s, _, t = abruf(f"{u.kurl}/anmelden", "POST", felder)                     # Fehlversuche beleben den Code nicht
    assert s == 303


def test_eingeloester_code_gilt_nach_der_nachfrist_nicht_mehr(welt, monkeypatch):
    import konten
    monkeypatch.setattr(konten, "CODE_NACHFRIST", -1)
    u = welt()
    abruf(f"{u.kurl}/anmelden", "POST", {"schritt": "adresse", "email": IDA})
    felder = {"schritt": "code", "email": IDA, "code": code_aus(u, IDA), "name": "Ida"}
    assert abruf(f"{u.kurl}/anmelden", "POST", felder)[0] == 303
    s, _, t = abruf(f"{u.kurl}/anmelden", "POST", felder)
    assert s == 200 and "stimmt nicht" in t
