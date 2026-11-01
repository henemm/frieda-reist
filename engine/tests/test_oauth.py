"""Tests für Paket J3 (Issue #47): ein Konnektor „Frieda“ mit OAuth 2.1 für alle Reisen eines Kontos.
Alle Beispiele sind erfunden."""
import base64
import hashlib
import io
import json
import re
import secrets
import sys
import urllib.parse
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import konnektor as kn  # noqa: E402
import konten  # noqa: E402
import oauth  # noqa: E402
from test_anmeldung import BASIS, abruf, anmelden, kopf, welt  # noqa: E402,F401  (welt: Fixture)
from schnittstelle_hilfe import intern_liste  # noqa: E402

CALLBACK = "https://claude.ai/api/mcp/auth_callback"
IDA, KARL, BEN = "ida@beispiel.invalid", "karl@beispiel.invalid", "ben@beispiel.invalid"


def pkce():
    v = secrets.token_urlsafe(48)
    return v, base64.urlsafe_b64encode(hashlib.sha256(v.encode()).digest()).rstrip(b"=").decode()


def registrieren(u, uris=(CALLBACK,)):
    s, _, t = abruf(f"{u.kurl}/register", "POST", json_body={"client_name": "Claude", "redirect_uris": list(uris)},
                    origin=None)
    return s, json.loads(t)


def autorisieren(u, sitzung, client, redirect=CALLBACK, challenge=None, state="zustand-1"):
    """Zustimmung geben. -> Location (mit code)"""
    q = {"response_type": "code", "client_id": client, "redirect_uri": redirect, "code_challenge": challenge,
         "code_challenge_method": "S256", "state": state, "scope": "frieda offline_access", "resource": BASIS + "/mcp"}
    s, h, t = abruf(f"{u.kurl}/authorize?{urllib.parse.urlencode(q)}", cookie=sitzung)
    assert s == 200 and "Zugriff erlauben?" in t, t
    s, h, _ = abruf(f"{u.kurl}/authorize", "POST", {**q, "aktion": "erlauben"}, cookie=sitzung)
    assert s == 303
    return kopf(h, "Location")[0]


def code_aus(location):
    return urllib.parse.parse_qs(urllib.parse.urlsplit(location).query)["code"][0]


def token(u, **felder):
    s, _, t = abruf(f"{u.kurl}/token", "POST", felder, origin=None)
    return s, json.loads(t)


def mcp(u, access, methode, params=None):
    s, h, t = abruf(f"{u.kurl}/mcp", "POST", json_body={"jsonrpc": "2.0", "id": 1, "method": methode,
                                                         "params": params or {}},
                    kopf={"Authorization": f"Bearer {access}"} if access else None, origin=None)
    antwort = json.loads(t) if t else None
    if methode == "tools/list" and antwort and "result" in antwort:
        intern_liste(antwort["result"])
    return s, h, antwort


def verbinden(u, email, name=None):
    """Wie die Claude-App: registrieren, anmelden, zustimmen, Token holen. -> (tokens, client_id)"""
    _, c = registrieren(u)
    sitzung, _ = anmelden(u, email, name)
    v, ch = pkce()
    loc = autorisieren(u, sitzung, c["client_id"], challenge=ch)
    s, t = token(u, grant_type="authorization_code", code=code_aus(loc), redirect_uri=CALLBACK,
                 client_id=c["client_id"], code_verifier=v)
    assert s == 200, t
    return t, c["client_id"]


def aufruf(u, access, werkzeug, **args):
    s, _, a = mcp(u, access, "tools/call", {"name": werkzeug, "arguments": args})
    assert s == 200, a
    return a["result"]["content"][0]["text"], a["result"]["isError"]


def test_metadaten(welt):
    u = welt()
    s, _, t = abruf(f"{u.kurl}/.well-known/oauth-protected-resource/mcp")
    m = json.loads(t)
    assert s == 200 and m["resource"] == BASIS + "/mcp" and m["authorization_servers"] == [BASIS]
    s, _, t = abruf(f"{u.kurl}/.well-known/oauth-authorization-server")
    m = json.loads(t)
    assert m["issuer"] == BASIS and m["code_challenge_methods_supported"] == ["S256"]
    assert m["token_endpoint_auth_methods_supported"] == ["none"] and m["client_id_metadata_document_supported"] is True
    assert "offline_access" in m["scopes_supported"] and m["registration_endpoint"] == BASIS + "/register"


def test_symbol_von_frieda(welt):
    """Favicon und App-Symbol unter Friedas Adresse (die Claude-App zeigt es beim Konnektor), Icons in serverInfo."""
    import http.client
    u = welt()
    t = urllib.parse.urlsplit(u.kurl)
    for pfad, art, anfang in (("/favicon.ico", "image/x-icon", b"\x00\x00\x01\x00"), ("/favicon.svg", "image/svg+xml", b"<svg"),
                              ("/apple-touch-icon.png", "image/png", b"\x89PNG"), ("/icon-512.png", "image/png", b"\x89PNG")):
        c = http.client.HTTPConnection(t.hostname, t.port, timeout=10)
        c.request("GET", pfad)
        r = c.getresponse()
        assert r.status == 200 and r.getheader("Content-Type") == art and r.read().startswith(anfang), pfad
    s, h, text = abruf(f"{u.kurl}/anmelden")
    assert '<link rel="icon" href="/favicon.svg"' in text and "img-src 'self'" in kopf(h, "Content-Security-Policy")[0]
    t_, _ = verbinden(u, IDA, "Ida")
    s, _, a = mcp(u, t_["access_token"], "initialize", {"protocolVersion": "2025-06-18"})
    icons = a["result"]["serverInfo"]["icons"]
    assert [i["src"] for i in icons] == [BASIS + "/icon-192.png", BASIS + "/icon-512.png", BASIS + "/favicon.svg"]


def test_ohne_token_401_mit_zeiger(welt):
    u = welt()
    s, h, _ = mcp(u, None, "initialize")
    assert s == 401
    assert kopf(h, "WWW-Authenticate") == [f'Bearer resource_metadata="{BASIS}/.well-known/oauth-protected-resource/mcp"']
    s, h, _ = mcp(u, "x" * 43, "initialize")
    assert s == 401 and 'error="invalid_token"' in kopf(h, "WWW-Authenticate")[0]


def test_ganzer_ablauf_wie_die_claude_app(welt):
    u = welt()
    konten.einladen("beispielreise", "karl", KARL, "mitwirkend", "Karl", "Ida")
    s, c = registrieren(u)
    assert s == 201 and c["token_endpoint_auth_method"] == "none"
    v, ch = pkce()
    # ohne Sitzung: erst anmelden, dann zurück zur Zustimmung
    q = {"response_type": "code", "client_id": c["client_id"], "redirect_uri": CALLBACK, "code_challenge": ch,
         "code_challenge_method": "S256", "state": "abc"}
    s, h, _ = abruf(f"{u.kurl}/authorize?{urllib.parse.urlencode(q)}")
    assert s == 303 and kopf(h, "Location")[0].startswith("/anmelden?zurueck=%2Fauthorize%3F")
    zurueck = urllib.parse.parse_qs(urllib.parse.urlsplit(kopf(h, "Location")[0]).query)["zurueck"][0]
    sitzung, ziel = anmelden(u, KARL, zurueck=zurueck)
    assert ziel == zurueck
    s, h, t = abruf(f"{u.kurl}{ziel}", cookie=sitzung)
    assert "Karl" in t and "claude.ai" in t and "form-action 'self' https://claude.ai" in kopf(h, "Content-Security-Policy")[0]
    loc = autorisieren(u, sitzung, c["client_id"], challenge=ch, state="abc")
    teile = urllib.parse.urlsplit(loc)
    assert loc.startswith(CALLBACK + "?") and urllib.parse.parse_qs(teile.query)["state"] == ["abc"]
    assert urllib.parse.parse_qs(teile.query)["iss"] == [BASIS]
    s, t = token(u, grant_type="authorization_code", code=code_aus(loc), redirect_uri=CALLBACK,
                 client_id=c["client_id"], code_verifier=v)
    assert s == 200 and t["token_type"] == "Bearer" and t["expires_in"] == 3600 and t["refresh_token"]
    # MCP mit dem Token: ein Konnektor für alle Reisen
    s, _, a = mcp(u, t["access_token"], "initialize", {"protocolVersion": "2025-06-18"})
    assert s == 200 and a["result"]["serverInfo"]["name"] == "frieda"
    assert "## Reise beispielreise" in a["result"]["instructions"]
    s, _, a = mcp(u, t["access_token"], "tools/list")
    werkzeuge = {w["name"]: w for w in a["result"]["tools"]}
    assert {"meine_reisen", "reisen_anlegen_anfragen", "ueberblick", "rueckmeldung_geben"} <= set(werkzeuge)
    assert "reise_anlegen" not in werkzeuge and "anfrage_entscheiden" not in werkzeuge
    eig = werkzeuge["rueckmeldung_geben"]["inputSchema"]["properties"]
    assert eig["trip"]["enum"] == ["beispielreise"] and "name" not in eig
    text, fehler = aufruf(u, t["access_token"], "meine_reisen")
    assert not fehler and "Beispielreise" in text and "reise: beispielreise" in text and "du: mitwirkend" in text
    text, fehler = aufruf(u, t["access_token"], "rueckmeldung_geben", art="Kommentar", ziel="T-01", text="Aus der App",
                          name="Jemand")
    assert not fehler, text
    e = [json.loads(z) for z in (u.o / "eingang.jsonl").read_text().splitlines()]
    assert e[-1]["name"] == "Karl" and e[-1]["text"] == "Aus der App"
    # Refresh mit Rotation; ein schon benutzter Refresh-Token beendet die ganze Familie
    s, t2 = token(u, grant_type="refresh_token", refresh_token=t["refresh_token"], client_id=c["client_id"])
    assert s == 200 and t2["refresh_token"] != t["refresh_token"]
    assert mcp(u, t["access_token"], "ping")[0] == 401                     # altes Access-Token ist ersetzt
    assert mcp(u, t2["access_token"], "ping")[0] == 200
    s, f = token(u, grant_type="refresh_token", refresh_token=t["refresh_token"], client_id=c["client_id"])
    assert s == 400 and f == {"error": "invalid_grant"}
    assert mcp(u, t2["access_token"], "ping")[0] == 401


def test_pkce_und_code_nur_einmal(welt):
    u = welt()
    _, c = registrieren(u)
    sitzung, _ = anmelden(u, KARL, "Karl")
    v, ch = pkce()
    loc = autorisieren(u, sitzung, c["client_id"], challenge=ch)
    falsch, _ = pkce()
    s, f = token(u, grant_type="authorization_code", code=code_aus(loc), redirect_uri=CALLBACK,
                 client_id=c["client_id"], code_verifier=falsch)
    assert s == 400 and f["error"] == "invalid_grant"
    s, _ = token(u, grant_type="authorization_code", code=code_aus(loc), redirect_uri=CALLBACK,
                 client_id=c["client_id"], code_verifier=v)
    assert s == 400                                                         # Code war schon verbraucht
    loc = autorisieren(u, sitzung, c["client_id"], challenge=ch)
    s, t = token(u, grant_type="authorization_code", code=code_aus(loc), redirect_uri=CALLBACK,
                 client_id=c["client_id"], code_verifier=v)
    assert s == 200
    s, _ = token(u, grant_type="authorization_code", code=code_aus(loc), redirect_uri=CALLBACK,
                 client_id=c["client_id"], code_verifier=v)
    assert s == 400 and mcp(u, t["access_token"], "ping")[0] == 401        # zweites Einlösen widerruft alles
    assert token(u, grant_type="password", client_id=c["client_id"])[1]["error"] == "unsupported_grant_type"
    assert token(u, grant_type="refresh_token", refresh_token="x", client_id="unbekannt")[0] == 401


def test_nur_erlaubte_ruecksprungadressen(welt):
    u = welt()
    for falsch in (["https://boese.invalid/cb"], ["http://beispiel.invalid/cb"], [], ["https://claude.ai/anders"]):
        s, f = registrieren(u, falsch)
        assert s == 400 and f["error"] == "invalid_redirect_uri"
    s, c = registrieren(u, ["http://localhost/callback"])
    assert s == 201
    sitzung, _ = anmelden(u, KARL, "Karl")
    v, ch = pkce()
    q = {"response_type": "code", "client_id": c["client_id"], "redirect_uri": "http://localhost:54321/callback",
         "code_challenge": ch, "code_challenge_method": "S256"}
    s, h, t = abruf(f"{u.kurl}/authorize?{urllib.parse.urlencode(q)}", cookie=sitzung)
    assert s == 200 and "Programm auf diesem Gerät" in t                    # Loopback: jeder Port, mit Warnung
    assert "http://localhost:*" in kopf(h, "Content-Security-Policy")[0]
    for anders in ("http://localhost:54321/anders", "https://boese.invalid/cb", CALLBACK):
        s, h, t = abruf(f"{u.kurl}/authorize?{urllib.parse.urlencode({**q, 'redirect_uri': anders})}", cookie=sitzung)
        assert s == 400 and "nicht erlaubt" in t and not kopf(h, "Location")
    s, _, t = abruf(f"{u.kurl}/authorize?{urllib.parse.urlencode({**q, 'code_challenge_method': 'plain'})}",
                    cookie=sitzung)
    assert s == 400 and "PKCE" in t
    s, _, t = abruf(f"{u.kurl}/authorize?{urllib.parse.urlencode({**q, 'resource': 'https://anders.invalid/mcp'})}",
                    cookie=sitzung)
    assert s == 400
    # Zustimmung nur von Friedas eigener Adresse
    s, _, _ = abruf(f"{u.kurl}/authorize", "POST", {**q, "aktion": "erlauben"}, cookie=sitzung,
                    origin="https://boese.invalid")
    assert s == 403
    # Abbrechen: Fehler an den Client, kein Code
    s, h, _ = abruf(f"{u.kurl}/authorize", "POST", {**q, "aktion": "abbrechen", "state": "z"}, cookie=sitzung)
    assert s == 303 and "error=access_denied" in kopf(h, "Location")[0] and "code=" not in kopf(h, "Location")[0]


class _Antwort(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_client_id_metadata_document(welt, monkeypatch):
    u = welt()
    cid = "https://claude.ai/oauth/mcp-client-metadata"
    abrufe = []

    class Oeffner:
        def open(self, req, timeout):
            abrufe.append(req.full_url)
            # claude.ai weist die Standardkennung von Python ab (403); ohne eigene Kennung scheitert jede Verbindung
            assert req.get_header("User-agent", "").startswith("Frieda-Reist/")
            return _Antwort(json.dumps({"client_id": cid, "client_name": "Claude", "redirect_uris": [CALLBACK]}).encode())
    monkeypatch.setattr(oauth.urllib.request, "build_opener", lambda *a: Oeffner())
    assert not oauth.cimd_erlaubt("https://boese.invalid/meta") and not oauth.cimd_erlaubt("http://claude.ai/x")
    assert oauth.client_finden("https://boese.invalid/meta") is None and abrufe == []   # fremde Hosts: nie abrufen
    sitzung, _ = anmelden(u, KARL, "Karl")
    v, ch = pkce()
    loc = autorisieren(u, sitzung, cid, challenge=ch)
    s, t = token(u, grant_type="authorization_code", code=code_aus(loc), redirect_uri=CALLBACK, client_id=cid,
                 code_verifier=v)
    assert s == 200 and abrufe == [cid]                                     # einmal geladen, dann aus dem Speicher


def test_sperren_und_ueberall_abmelden_beenden_den_zugriff(welt):
    u = welt()
    t, _ = verbinden(u, KARL, "Karl")
    k = konten.konto_per_email(KARL)
    konten.alle_abmelden(k["id"])
    assert mcp(u, t["access_token"], "ping")[0] == 401
    t, cid = verbinden(u, KARL)
    konten.sperren(k["id"])
    assert mcp(u, t["access_token"], "ping")[0] == 401
    assert token(u, grant_type="refresh_token", refresh_token=t["refresh_token"], client_id=cid)[0] == 400


def test_einladen_per_mail(welt):
    u = welt()
    konten.einladen("beispielreise", "ida", IDA, "organisator", "Ida", "Ida")
    t, _ = verbinden(u, IDA)
    s, _, a = mcp(u, t["access_token"], "tools/list")
    einl = next(w for w in a["result"]["tools"] if w["name"] == "person_einladen")
    assert "email" in einl["inputSchema"]["required"]
    text, fehler = aufruf(u, t["access_token"], "person_einladen", vorname="Hanna", rolle="mitwirkend")
    assert fehler and "email" in text
    text, fehler = aufruf(u, t["access_token"], "person_einladen", vorname="Hanna", rolle="mitwirkend",
                          email="Hanna@beispiel.invalid")
    assert not fehler and "hanna@beispiel.invalid" in text and "https://" not in text
    m = [json.loads(z) for z in u.mails.read_text().splitlines() if '"hanna@beispiel.invalid"' in z][-1]
    assert "Ida hat dich zur Reise „Beispielreise" in m["text"] and "/einladung/" in m["text"]
    einladungen = json.loads((u.o / "einladungen.json").read_text())
    assert einladungen["hanna"]["rolle"] == "mitwirkend"
    # Karl gibt es schon in der Reise: wird mit seinem Konto verknüpft (Umstellung bisheriger Personen)
    text, fehler = aufruf(u, t["access_token"], "person_einladen", vorname="Karl", email=KARL)
    assert not fehler and "verschickt" in text
    _, k = anmelden(u, KARL)
    assert konten.mitglied(konten.konto_per_email(KARL)["id"], "beispielreise") == "karl"


def test_reisen_anlegen_mit_recht(welt):
    u = welt()
    t, _ = verbinden(u, BEN, "Ben")
    text, _ = aufruf(u, t["access_token"], "reise_anlegen", titel="X", von="2027-02-06", bis="2027-02-13")
    assert "noch nicht" in text
    text, _ = aufruf(u, t["access_token"], "reisen_anlegen_anfragen")
    assert "beim Betreiber" in text
    konten.freischalten(konten.konto_per_email(BEN)["id"])
    s, _, a = mcp(u, t["access_token"], "tools/list")
    w = next(x for x in a["result"]["tools"] if x["name"] == "reise_anlegen")
    assert "email" in w["inputSchema"]["properties"]["people"]["items"]["properties"]
    text, fehler = aufruf(u, t["access_token"], "reise_anlegen", titel="Winterwoche im Allgäu", von="2027-02-06",
                          bis="2027-02-13", ziel="Oberstdorf",
                          personen=[{"vorname": "Mo", "rolle": "mitwirkend", "email": "mo@beispiel.invalid"},
                                    {"vorname": "Kai"}])
    assert not fehler and "Einladung per Mail" in text, text
    e = json.loads((u.ablage / "_neu" / "auftraege.jsonl").read_text().splitlines()[-1])
    assert e["konto_id"] == konten.konto_per_email(BEN)["id"] and e["name"] == "Ben"
    assert e["einladen"] == [{"schluessel": "mo", "email": "mo@beispiel.invalid", "rolle": "mitwirkend", "name": "Mo"}]
    assert "mo@beispiel.invalid" not in json.dumps(e["daten"])              # Adressen nicht in den Reisedaten
    # Die Reise entsteht sofort über den Schreibweg (hier nachgestellt): Anfrage erledigt, Links folgen nach dem Veröffentlichen
    st = json.loads((u.ablage / "_neu" / "status.json").read_text())[e["id"]]
    assert st["status"] == "uebernommen" and "Angelegt als winterwoche-im-allgaeu-2027" in st["kommentar"]
    assert "winterwoche-im-allgaeu-2027" in Path(__import__("os").environ["KN_ZUGAENGE"]).with_name("neue-reisen-ausstehend.jsonl").read_text()
    assert "Winterwoche im Allgäu" not in aufruf(u, t["access_token"], "meine_reisen")[0]   # steht dort, sobald die Seite online ist


def test_betreiber_entscheidet_bitten(welt):
    u = welt()
    ida, _ = verbinden(u, IDA, "Ida")
    konten.recht_setzen(konten.konto_per_email(IDA)["id"], "betreiber")
    ben, _ = verbinden(u, BEN, "Ben")
    aufruf(u, ben["access_token"], "reisen_anlegen_anfragen")
    text, _ = aufruf(u, ida["access_token"], "meine_reisen")
    assert "Ben (ben@beispiel.invalid)" in text
    text, fehler = aufruf(u, ben["access_token"], "anfrage_entscheiden", email=BEN, erlauben=True)
    assert fehler                                                           # nur der Betreiber
    text, fehler = aufruf(u, ida["access_token"], "anfrage_entscheiden", email=BEN, erlauben=True)
    assert not fehler and konten.recht(konten.konto_per_email(BEN), "reise_anlegen")


def test_alter_link_geht_weiter(welt):
    """Übergang: Die bisherigen Konnektor-Links funktionieren neben dem neuen Konnektor weiter."""
    u = welt()
    from test_regeln import KARL as KARL_LINK
    assert "rueckmeldung_geben" in u.werkzeuge(KARL_LINK)


def test_person_entfernen(welt):
    u = welt()
    konten.einladen("beispielreise", "ida", IDA, "organisator", "Ida", "Ida")
    konten.einladen("beispielreise", "karl", KARL, "mitwirkend", "Karl", "Ida")
    ida, _ = verbinden(u, IDA)
    karl, _ = verbinden(u, KARL)
    from test_regeln import KARL as KARL_LINK
    assert "person_entfernen" not in {w["name"] for w in mcp(u, karl["access_token"], "tools/list")[2]["result"]["tools"]}
    assert aufruf(u, ida["access_token"], "person_entfernen", person="Ida")[1]          # sich selbst nicht
    # Die Person wird über den Schreibweg zum Gast, der nicht mitreist (hier nachgestellt)
    geschrieben = []
    with pytest.MonkeyPatch.context() as m:
        m.setenv("KN_SCHREIBDIENST", "http://127.0.0.1:9")
        m.setattr(kn, "schreib_anfrage", lambda reise, w, anfrage: (geschrieben.append((reise, w, anfrage)) or {"ok": True, "text": "x"}, None))
        text, fehler = aufruf(u, ida["access_token"], "person_entfernen", person="karl", grund="fährt nicht mit")
    assert not fehler and "endet sofort" in text, text
    assert konten.mitglied(konten.konto_per_email(KARL)["id"], "beispielreise") is None
    assert "Noch keine Reise" in aufruf(u, karl["access_token"], "meine_reisen")[0]
    assert KARL_LINK not in json.loads(Path(__import__("os").environ["KN_ZUGAENGE"]).read_text())   # alter Link weg
    assert geschrieben and geschrieben[-1][1] == "person_schreiben" and geschrieben[-1][2]["args"]["schluessel"] == "karl"
    assert geschrieben[-1][2]["args"]["rolle"] == "gast" and "fährt nicht mit" in geschrieben[-1][2]["args"]["notiz"]


def test_niemand_uebernimmt_eine_bestehende_person(welt):
    """Prüfung J3: Wer eine bestehende, noch nicht verknüpfte Person mit der eigenen Adresse „einlädt“, spräche danach als
    sie. Organisator:innen verknüpft nur der Betreiber; bestehende Personen verknüpfen nur Organisator:innen."""
    u = welt(regeln={"einladen": "mitwirkend"})
    konten.einladen("beispielreise", "max", "max@beispiel.invalid", "organisator", "Max", "Ida")
    konten.einladen("beispielreise", "karl", KARL, "mitwirkend", "Karl", "Ida")
    maxe, _ = verbinden(u, "max@beispiel.invalid")
    karl, _ = verbinden(u, KARL)
    text, fehler = aufruf(u, maxe["access_token"], "person_einladen", vorname="Ida", email="max.zwei@beispiel.invalid")
    assert fehler and "Betreiber" in text
    assert konten.konto_von_person("beispielreise", "ida") is None
    text, fehler = aufruf(u, karl["access_token"], "person_einladen", vorname="Kim", email="karl.zwei@beispiel.invalid")
    assert fehler and "nur ein:e Organisator:in" in text
    assert konten.konto_von_person("beispielreise", "kim") is None
    # neue Personen einladen darf ein:e Mitwirkende:r hier weiterhin (höchstens die eigene Rolle)
    text, fehler = aufruf(u, karl["access_token"], "person_einladen", vorname="Lea", email="lea@beispiel.invalid")
    assert not fehler, text


def test_sprache_am_konto_im_konnektor(welt):
    """Das Konto trägt eine Sprache (ADR-0006): das Werkzeug sprache_setzen ändert sie, die Anleitung folgt ihr nach der Änderung;
    eine unbekannte Sprache lehnt es in der Sprache der Person ab."""
    u = welt()
    t, _ = verbinden(u, IDA, "Ida")
    acc = t["access_token"]
    s, _, r = mcp(u, acc, "tools/list")
    werk = {w["name"]: w for w in r["result"]["tools"]}
    assert "sprache_setzen" in werk and werk["sprache_setzen"]["inputSchema"]["properties"]["language"]["enum"][:2] == ["de", "en"]
    # Das Konto wurde mit Accept-Language: de angelegt (Testhelfer); Beschreibung und Antwort kommen deutsch
    assert werk["sprache_setzen"]["description"].startswith("Stellt die Sprache dieses Kontos ein")
    s, _, r = mcp(u, acc, "tools/call", {"name": "sprache_setzen", "arguments": {"sprache": "en"}})
    assert not r["result"]["isError"] and r["result"]["content"][0]["text"].startswith("Language set to English.")
    s, _, r = mcp(u, acc, "tools/list")
    assert {w["name"]: w for w in r["result"]["tools"]}["sprache_setzen"]["description"].startswith("Sets the language of this account")
    s, _, r = mcp(u, acc, "tools/call", {"name": "sprache_setzen", "arguments": {"sprache": "klingonisch"}})
    assert r["result"]["isError"] and r["result"]["content"][0]["text"] == "That language does not exist."
    import konten as k
    assert k.konto_per_email(IDA)["sprache"] == "en"


def ohne_beschreibung(x):
    if isinstance(x, dict):
        return {k: ohne_beschreibung(v) for k, v in x.items() if k != "description"}
    if isinstance(x, list):
        return [ohne_beschreibung(e) for e in x]
    return x


def test_anleitung_und_werkzeuge_in_der_sprache_des_kontos(welt):
    """Anleitung und Beschreibungen kommen aus dem Katalog in der Sprache des Kontos (ADR-0006, M8): Namen, Schemata und
    Hinweise sind in beiden Sprachen gleich, nur die Texte unterscheiden sich; Datenwerte bleiben deutsch und werden erklärt."""
    u = welt()
    t, _ = verbinden(u, IDA, "Ida")
    acc = t["access_token"]
    _, _, de_init = mcp(u, acc, "initialize")
    _, _, de_list = mcp(u, acc, "tools/list")
    assert "Aufgabe: Du bist Frieda" in de_init["result"]["instructions"] and "Antworte in der Sprache der Person" in de_init["result"]["instructions"]
    mcp(u, acc, "tools/call", {"name": "sprache_setzen", "arguments": {"sprache": "en"}})
    _, _, en_init = mcp(u, acc, "initialize")
    _, _, en_list = mcp(u, acc, "tools/list")
    assert en_init["result"]["instructions"].startswith("Task: You are Frieda") and "Reply in the person's language" in en_init["result"]["instructions"]
    assert ohne_beschreibung(de_list["result"]["tools"]) == ohne_beschreibung(en_list["result"]["tools"])
    de_t = {w["name"]: w["description"] for w in de_list["result"]["tools"]}
    en_t = {w["name"]: w["description"] for w in en_list["result"]["tools"]}
    assert de_t.keys() == en_t.keys() and all(de_t[n] != en_t[n] for n in de_t if n != "sprache_setzen" or True)
    assert en_t["meine_reisen"].startswith("Your trips with role, status")
    assert not any("@konnektor" in d or d.startswith("TODO-EN") for d in en_t.values())
