"""Tests für engine/konnektor.py: MCP-Protokoll, Rollen, Werkzeuge, Weitergabe an den Rückmeldedienst."""
import json
import sys
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import bauen  # noqa: E402
import konnektor as kn  # noqa: E402
import rueckmeldungen as rm  # noqa: E402

WURZEL = Path(__file__).resolve().parent.parent.parent
BEISPIEL = WURZEL / "beispiel" / "reisen" / "beispielreise"   # erfundene Reise: ida bestimmer, karl einbringer
ALT_BESTIMMER = "h" * 32  # Link der Bestimmerin Ida (person ida)
MITREISEND = "m" * 32    # alter Link (rolle mitreisend) -> Einbringer ohne festen Namen
KARL = "f" * 32          # Link einer Person (reise.yaml personen: karl, einbringer)
REISEND = "r" * 32       # Link mit Rolle reisend, nur lesen
WEG = "w" * 32           # Link einer Person, die es in reise.yaml nicht (mehr) gibt


@pytest.fixture(scope="module")
def seiten(tmp_path_factory):
    s = tmp_path_factory.mktemp("seiten")
    bauen.bauen(BEISPIEL, s / "beispielreise")
    return s


def starten(handler):
    s = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s, f"http://127.0.0.1:{s.server_address[1]}"


@pytest.fixture
def dienst(seiten, tmp_path, monkeypatch):
    ablage = tmp_path / "ablage"
    (ablage / "beispielreise").mkdir(parents=True)
    zug = tmp_path / "zugaenge.json"
    zug.write_text(json.dumps({ALT_BESTIMMER: {"reise": "beispielreise", "person": "ida"},
                               MITREISEND: {"reise": "beispielreise", "rolle": "mitreisend"},
                               KARL: {"reise": "beispielreise", "person": "karl"},
                               REISEND: {"reise": "beispielreise", "rolle": "reisend"},
                               WEG: {"reise": "beispielreise", "person": "niemand"}}))
    monkeypatch.setenv("RM_ABLAGE", str(ablage))
    monkeypatch.setenv("KN_SEITEN", str(seiten))
    monkeypatch.setenv("KN_ZUGAENGE", str(zug))
    rm._zeiten.clear()
    rs, rurl = starten(rm.Dienst)
    monkeypatch.setenv("KN_RUECKMELDEDIENST", rurl)
    ks, kurl = starten(kn.Dienst)
    yield kurl, ablage
    ks.shutdown()
    rs.shutdown()


def anfrage(url, daten=None, methode="POST"):
    body = json.dumps(daten).encode() if daten is not None else None
    req = urllib.request.Request(url, data=body, method=methode, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")


def rpc(basis, token, methode, params=None, nid=1):
    code, a = anfrage(f"{basis}/{token}", {"jsonrpc": "2.0", "id": nid, "method": methode, "params": params or {}})
    assert code == 200, a
    return a["result"]


def werkzeug(basis, token, werkzeugname, **args):
    r = rpc(basis, token, "tools/call", {"name": werkzeugname, "arguments": args})
    return r["content"][0]["text"], r["isError"]


def test_unbekannter_link(dienst):
    basis, _ = dienst
    assert anfrage(f"{basis}/{'x' * 32}", {"jsonrpc": "2.0", "id": 1, "method": "ping"})[0] == 404
    assert anfrage(f"{basis}/", {"jsonrpc": "2.0", "id": 1, "method": "ping"})[0] == 404
    assert anfrage(f"{basis}/{ALT_BESTIMMER}/x", {"jsonrpc": "2.0", "id": 1, "method": "ping"})[0] == 404


def test_initialize_und_protokoll(dienst):
    basis, _ = dienst
    r = rpc(basis, MITREISEND, "initialize", {"protocolVersion": "2025-03-26", "capabilities": {},
                                              "clientInfo": {"name": "t", "version": "1"}})
    assert r["protocolVersion"] == "2025-03-26"
    assert "tools" in r["capabilities"]
    assert "Beispielreise" in r["serverInfo"]["title"]
    assert "Vornamen" in r["instructions"]
    assert rpc(basis, MITREISEND, "initialize", {"protocolVersion": "1999-01-01"})["protocolVersion"] == kn.PROTOKOLLE[0]
    # Benachrichtigung: 202 ohne Inhalt
    req = urllib.request.Request(f"{basis}/{MITREISEND}", method="POST", headers={"Content-Type": "application/json"},
                                 data=json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}).encode())
    with urllib.request.urlopen(req) as a:
        assert a.status == 202
    assert anfrage(f"{basis}/{MITREISEND}", methode="GET")[0] == 405
    code, a = anfrage(f"{basis}/{MITREISEND}", {"jsonrpc": "2.0", "id": 7, "method": "gibtsnicht"})
    assert a["error"]["code"] == -32601


def test_initialize_meldet_symbol_der_reise(dienst, seiten):
    """Die Claude-App zeigt beim Konnektor das Symbol der Reise (serverInfo.icons), dasselbe wie die Seite."""
    import base64
    basis, _ = dienst
    icons = rpc(basis, MITREISEND, "initialize", {"protocolVersion": "2025-11-25"})["serverInfo"]["icons"]
    assert {i["sizes"][0] for i in icons} == {"32x32", "192x192"}
    for i in icons:
        assert i["mimeType"] == "image/png" and i["src"].startswith("data:image/png;base64,")
        g = i["sizes"][0].split("x")[0]
        assert base64.b64decode(i["src"].split(",", 1)[1]) == (seiten / "beispielreise" / f"icon-{g}.png").read_bytes()


def test_initialize_ohne_symbol_geht_trotzdem(dienst, seiten):
    basis, _ = dienst
    versteckt = [(seiten / "beispielreise" / f"icon-{g}.png") for g in (32, 192)]
    inhalte = [f.read_bytes() for f in versteckt]
    try:
        for f in versteckt:
            f.unlink()
        r = rpc(basis, MITREISEND, "initialize", {"protocolVersion": "2025-11-25"})
        assert "icons" not in r["serverInfo"] and "Beispielreise" in r["serverInfo"]["title"]
    finally:
        for f, b in zip(versteckt, inhalte):
            f.write_bytes(b)


def test_ueberblick_zeigt_stand(dienst, monkeypatch):
    """Man sieht in der App, wann die Reise veröffentlicht wurde und ob der Dienst den neuen Code geladen hat."""
    basis, _ = dienst
    t, f = werkzeug(basis, MITREISEND, "ueberblick")
    assert not f and "## Stand" in t and "Reise zuletzt veröffentlicht:" in t and f"Code {kn._CODE_START}" in t
    assert "Neustart" not in t
    monkeypatch.setattr(kn, "_CODE_START", "00000000")
    t, _ = werkzeug(basis, MITREISEND, "ueberblick")
    assert "braucht einen Neustart" in t


def test_ueberblick_zeigt_einarbeiten_kosten_nur_bestimmern(dienst, tmp_path, monkeypatch):
    """Wartezeit und Kosten des automatischen Einarbeitens sehen nur Bestimmer; alle sehen, wann zuletzt eingearbeitet wurde."""
    basis, _ = dienst
    t, _ = werkzeug(basis, MITREISEND, "ueberblick")
    assert "## Einarbeiten" in t and "Noch nichts automatisch eingearbeitet" in t
    protokoll = tmp_path / "laeufe.jsonl"
    zeilen = [{"zeit": "2026-10-26T10:00:00+00:00", "ergebnis": "ok", "reisen": "beispielreise", "anzahl": 2,
               "eingabe_bis_ende_s": 400, "kosten_usd": 0.8, "online": "ja"},
              {"zeit": "2026-10-26T11:00:00+00:00", "ergebnis": "ok", "reisen": "andere", "anzahl": 1,
               "eingabe_bis_ende_s": 200, "kosten_usd": 0.4, "online": "ja"},
              {"zeit": "2026-10-26T12:00:00+00:00", "ergebnis": "fehler", "reisen": "beispielreise", "anzahl": 1}]
    protokoll.write_text("\n".join(json.dumps(z) for z in zeilen) + "\nkaputt\n")
    monkeypatch.setenv("RM_LAEUFE", str(protokoll))
    monkeypatch.setattr(rm.datetime, "datetime", type("D", (rm.datetime.datetime,), {
        "now": classmethod(lambda cls, tz=None: rm.datetime.datetime(2026, 10, 27, tzinfo=rm.datetime.timezone.utc))}))
    t, _ = werkzeug(basis, MITREISEND, "ueberblick")
    assert "Zuletzt eingearbeitet: 2026-10-26 10:00 UTC, 2 Eingabe(n)" in t      # nur Läufe dieser Reise
    assert "USD" not in t and "Kosten" not in t and "im Schnitt" not in t
    t, _ = werkzeug(basis, ALT_BESTIMMER, "ueberblick")
    assert "(alle Reisen zusammen)" in t and "1.20 USD insgesamt" in t and "im Schnitt 5 min" in t
    assert "Der letzte Lauf ist fehlgeschlagen" in t and "3 Läufe, davon 1 fehlgeschlagen" in t


def test_status_mit_kommentar_erscheint_beim_absender(dienst):
    """Was das Einarbeiten per setze einträgt, sieht der Absender sofort im Werkzeug rueckmeldungen (die Seite liest dieselbe Datei)."""
    basis, _ = dienst
    t, f = werkzeug(basis, KARL, "rueckmeldung_geben", ziel="T-03", art="Kommentar", text="Schön!")
    assert not f
    rid = t.split()[2]
    rm.setze("beispielreise", rid, "uebernommen", "Steht jetzt im Text von T-03.")
    t, f = werkzeug(basis, KARL, "rueckmeldungen")
    assert not f and rid in t and "Steht jetzt im Text von T-03." in t


def test_stapel(dienst):
    basis, _ = dienst
    code, a = anfrage(f"{basis}/{MITREISEND}", [{"jsonrpc": "2.0", "id": 1, "method": "ping"},
                                                {"jsonrpc": "2.0", "method": "notifications/initialized"},
                                                {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}])
    assert code == 200 and [x["id"] for x in a] == [1, 2]


def test_werkzeuge_je_rolle(dienst):
    basis, _ = dienst
    m = {t["name"] for t in rpc(basis, MITREISEND, "tools/list")["tools"]}
    h = {t["name"] for t in rpc(basis, ALT_BESTIMMER, "tools/list")["tools"]}
    assert "auftrag_geben" not in m and "rueckmeldung_geben" in m
    assert h == m | {"auftrag_geben"}
    assert {t["name"] for t in rpc(basis, KARL, "tools/list")["tools"]} == m
    r = {t["name"] for t in rpc(basis, REISEND, "tools/list")["tools"]}
    assert r == m - kn.SCHREIB_WERKZEUGE and "zeige" in r


def test_rollen_aus_reise_yaml(dienst):
    basis, ablage = dienst
    # Person mit Link: Name steht fest, auch wenn ein anderer genannt wird
    t, f = werkzeug(basis, KARL, "rueckmeldung_geben", ziel="T-03", art="Kommentar", text="Schön!", name="Jemand")
    assert not f and rm.eintraege(ablage / "beispielreise")[0]["name"] == "Karl"
    t, f = werkzeug(basis, KARL, "auftrag_geben", auftrag="V-01.b wählen")
    assert f and "nur Bestimmer" in t
    # Rolle reisend: nur lesen
    t, f = werkzeug(basis, REISEND, "zeige", id="T-02")
    assert not f and "T-02" in t
    t, f = werkzeug(basis, REISEND, "rueckmeldung_geben", ziel="T-03", art="Kommentar", text="x", name="Kim")
    assert f and "nur lesen" in t
    t, f = werkzeug(basis, REISEND, "aufgabe_anlegen", titel="x", name="Kim")
    assert f and "nur lesen" in t
    # Link einer Person, die es nicht mehr gibt
    t, f = werkzeug(basis, WEG, "ueberblick")
    assert f and "keiner Person" in t
    # Anleitung nennt Person, Rolle, Bestimmer und Status
    d = kn.daten("beispielreise")
    a = kn.anleitung({"reise": "beispielreise", "person": "karl"}, d)
    assert "Du sprichst mit Karl (Einbringer)" in a and "Ida entscheidet" in a and "Status planung" in a
    assert "Vornamen" not in a
    assert "Du sprichst mit Ida (Bestimmer)" in kn.anleitung({"reise": "beispielreise", "person": "ida"}, d)
    assert "nur lesen" in kn.anleitung({"reise": "beispielreise", "rolle": "reisend"}, d)
    assert "Vornamen" in kn.anleitung({"reise": "beispielreise", "rolle": "mitreisend"}, d)


def test_lesen(dienst):
    basis, _ = dienst
    t, f = werkzeug(basis, MITREISEND, "ueberblick")
    assert not f and "T-01" in t and "Offene Fragen" in t
    t, f = werkzeug(basis, MITREISEND, "zeige", id="E-01")
    assert not f and "Bastei" in t and "E-01.eckdaten" in t
    t, f = werkzeug(basis, MITREISEND, "zeige", id="E-01.eckdaten")
    assert "| Gehzeit | ca. 3:40 h |" in t
    t, f = werkzeug(basis, MITREISEND, "zeige", id="V-03.a")
    assert "gewaehlt" in t and "Ida" in t
    t, f = werkzeug(basis, MITREISEND, "zeige", id="T-99")
    assert f and "gibt es nicht" in t
    t, f = werkzeug(basis, MITREISEND, "suche", begriff="pension burgblick")
    assert "U-02" in t
    t, f = werkzeug(basis, MITREISEND, "offene_fragen")
    assert "F-01" in t
    assert "F-02" not in t   # geklärt, nicht mehr offen
    t, f = werkzeug(basis, MITREISEND, "varianten")
    assert "P-B" in t and "V-01.b" in t


def test_rueckmeldung_mitreisend_braucht_namen(dienst):
    basis, ablage = dienst
    t, f = werkzeug(basis, MITREISEND, "rueckmeldung_geben", ziel="T-03", art="Kommentar", text="Schön!")
    assert f and "Name fehlt" in t
    t, f = werkzeug(basis, MITREISEND, "rueckmeldung_geben", ziel="T-03", art="Kommentar", text="Schön!", name="Anna")
    assert not f and "R-" in t
    e = rm.eintraege(ablage / "beispielreise")
    assert len(e) == 1 and e[0]["name"] == "Anna" and e[0]["quelle"] == "über Claude"
    t, f = werkzeug(basis, MITREISEND, "rueckmeldung_geben", ziel="T-03", art="Unsinn", text="x", name="Anna")
    assert f and "unbekannte Art" in t
    t, _ = werkzeug(basis, MITREISEND, "rueckmeldungen")
    assert "Anna" in t and "Schön!" in t


def test_wunsch_ueber_konnektor(dienst):
    basis, ablage = dienst
    t, f = werkzeug(basis, MITREISEND, "rueckmeldung_geben", art="Wunsch", text="Einmal auf den Lilienstein", name="Lena")
    assert not f and "R-" in t
    e = rm.eintraege(ablage / "beispielreise")[0]
    assert e["ziel"] == rm.WUNSCH_ZIEL and e["art"] == "Wunsch"


def test_anleitung_nennt_wuensche_nur_wenn_eingeschaltet():
    zugang = {"reise": "beispielreise", "rolle": "mitreisend"}
    assert "art Wunsch" not in kn.anleitung(zugang, {"reise": {}})
    assert "art Wunsch" in kn.anleitung(zugang, {"reise": {"bausteine": ["wuensche"]}})


def test_rueckmeldung_alter_bestimmer_name_fest(dienst):
    basis, ablage = dienst
    werkzeug(basis, ALT_BESTIMMER, "rueckmeldung_geben", ziel="F-01", art="Antwort", text="Mit der Bahn", name="Jemand")
    assert rm.eintraege(ablage / "beispielreise")[0]["name"] == "Ida"


def test_auftrag(dienst, capsys):
    basis, ablage = dienst
    t, f = werkzeug(basis, MITREISEND, "auftrag_geben", auftrag="V-01.b wählen")
    assert f and "nur Bestimmer" in t
    assert not (ablage / "beispielreise" / "auftraege.jsonl").exists()
    t, f = werkzeug(basis, ALT_BESTIMMER, "auftrag_geben", ziel="V-01", auftrag="V-01.b wählen, weil Karl die Bahn möchte")
    assert not f and "unverändert" in t
    a = rm.auftraege(ablage / "beispielreise")
    assert len(a) == 1 and a[0]["name"] == "Ida" and a[0]["art"] == "Auftrag" and a[0]["status"] == "neu"
    assert kn.AID_MUSTER.match(a[0]["id"])
    # Nicht auf der Seite (eingang), aber in liste und setze
    assert rm.eintraege(ablage / "beispielreise") == []
    rm.liste("beispielreise", False)
    assert "ÄNDERUNGSAUFTRAG" in capsys.readouterr().out
    rm.setze("beispielreise", a[0]["id"], "uebernommen", "erledigt")
    assert rm.auftraege(ablage / "beispielreise")[0]["status"] == "uebernommen"
    t, _ = werkzeug(basis, ALT_BESTIMMER, "rueckmeldungen")
    assert a[0]["id"] in t and "uebernommen" in t
    t, _ = werkzeug(basis, MITREISEND, "rueckmeldungen")
    assert a[0]["id"] not in t
    t, f = werkzeug(basis, ALT_BESTIMMER, "auftrag_geben", ziel="kein gültiges ziel!", auftrag="x")
    assert f


def test_zugang_anlegen(seiten, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("KN_SEITEN", str(seiten))
    monkeypatch.setenv("KN_ZUGAENGE", str(tmp_path / "k" / "z.json"))
    kn.zugang_anlegen("beispielreise", "karl")
    aus = capsys.readouterr().out.strip()
    assert "Karl, einbringer" in aus
    token = aus.split()[-1].rsplit("/", 1)[1]
    assert kn.zugang_zu(token) == {"reise": "beispielreise", "person": "karl", "angelegt": kn.datetime.date.today().isoformat()}
    assert (tmp_path / "k" / "z.json").stat().st_mode & 0o777 == 0o600
    kn.zugang_anlegen("beispielreise", "einbringer")   # Rolle ohne festen Namen
    token = capsys.readouterr().out.strip().split()[-1].rsplit("/", 1)[1]
    assert kn.zugang_zu(token)["rolle"] == "einbringer"
    assert kn.zugang_zu("kurz") is None
    with pytest.raises(SystemExit):
        kn.zugang_anlegen("andere-reise", "ida")  # nicht veröffentlicht
    with pytest.raises(SystemExit):
        kn.zugang_anlegen("beispielreise", "chef")   # weder Person noch Rolle
    kn.zugaenge_zeigen()
    assert "(karl," in capsys.readouterr().out


def test_text_aus_html():
    assert kn.text('<p>Hallo <a href="https://x.de">Link</a></p><ul><li>a</li><li>b</li></ul>') == \
        "Hallo [Link](https://x.de)\n\n- a\n- b"
    assert kn.text("<table><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>2</td></tr></table>") == "| A | B |\n| 1 | 2 |"


def test_gesund_ohne_token(dienst, tmp_path, monkeypatch):
    basis, _ = dienst
    code, a = anfrage(f"{basis}/gesund", methode="GET")
    assert (code, a) == (200, {"gesund": True})
    # Link auf eine nicht veröffentlichte Reise -> nicht bereit, ohne Details zu verraten
    zug = tmp_path / "zugaenge.json"
    z = json.loads(zug.read_text())
    z["k" * 32] = {"reise": "gibtsnicht", "rolle": "mitreisend"}
    zug.write_text(json.dumps(z))
    code, a = anfrage(f"{basis}/gesund", methode="GET")
    assert (code, a) == (503, {"gesund": False})
    zug.write_text("{kaputt")
    assert anfrage(f"{basis}/gesund", methode="GET")[0] == 503


def test_kaputte_zugaenge(tmp_path, monkeypatch):
    z = tmp_path / "z.json"
    z.write_text("{kaputt")
    monkeypatch.setenv("KN_ZUGAENGE", str(z))
    assert kn.zugang_zu(ALT_BESTIMMER) is None
    z.write_text("[]")
    assert kn.zugang_zu(ALT_BESTIMMER) is None


def test_nacht_ohne_doppelten_namen(seiten, tmp_path, monkeypatch):
    monkeypatch.setenv("KN_SEITEN", str(seiten))
    zugang = {"reise": "beispielreise", "rolle": "mitreisend"}
    t, _ = kn.werkzeug(zugang, "zeige", {"id": "T-03"})
    assert "Nacht: Altendorf, Wanderherberge Altendorf (U-04)" in t
    # Ist die Unterkunft selbst der Ort (gleicher Name, z. B. eine Hütte), steht der Name nur einmal da
    d = json.loads((seiten / "beispielreise" / "daten.json").read_text(encoding="utf-8"))
    d["route"]["orte"]["O-04"]["name"] = "Wanderherberge Altendorf"
    (tmp_path / "s" / "beispielreise").mkdir(parents=True)
    (tmp_path / "s" / "beispielreise" / "daten.json").write_text(json.dumps(d), encoding="utf-8")
    monkeypatch.setenv("KN_SEITEN", str(tmp_path / "s"))
    t, _ = kn.werkzeug(zugang, "zeige", {"id": "T-03"})
    assert "Nacht: Wanderherberge Altendorf (U-04)" in t


def test_aufgaben_ueber_konnektor(dienst):
    basis, ablage = dienst
    m = {t["name"] for t in rpc(basis, MITREISEND, "tools/list")["tools"]}
    assert {"aufgaben", "aufgabe_anlegen", "aufgabe_aendern"} <= m
    t, f = werkzeug(basis, MITREISEND, "aufgabe_anlegen", titel="Pension buchen", bezug=["U-02"])
    assert f and "Name fehlt" in t
    t, f = werkzeug(basis, MITREISEND, "aufgabe_anlegen", titel="Pension buchen", bezug=["U-99"], name="Anna")
    assert f and "U-99" in t
    t, f = werkzeug(basis, MITREISEND, "aufgabe_anlegen", titel="Pension buchen", bezug=["U-02", "T-02"],
                    zustaendig="Anna", prioritaet="hoch", ab="2026-11-03", frist="2026-11-10", name="Anna")
    assert not f and "AG-01" in t and "gilt sofort" in t
    t, f = werkzeug(basis, ALT_BESTIMMER, "aufgabe_anlegen", titel="Bus prüfen", frist="2020-01-01", name="Egal")
    assert not f and rm.aufgaben(ablage / "beispielreise")[1]["erstellt_von"] == "Ida"
    t, _ = werkzeug(basis, MITREISEND, "aufgaben", zustaendig="anna")
    assert "AG-01" in t and "AG-02" not in t
    t, _ = werkzeug(basis, MITREISEND, "aufgaben", bezug="U-02")
    assert "AG-01" in t and "Pension Burgblick" in t
    t, _ = werkzeug(basis, MITREISEND, "zeige", id="T-02")
    assert "Aufgaben hier" in t and "AG-01" in t
    t, _ = werkzeug(basis, MITREISEND, "ueberblick")
    # Fristen zählen erst ab Status fest (test_regeln.py): in der Planung steht die Zahl, aber nichts ist überfällig
    assert "Offene Aufgaben: 2" in t and "überfällig" not in t
    t, f = werkzeug(basis, MITREISEND, "aufgabe_aendern", id="AG-01", status="erledigt", kommentar="gebucht", name="Anna")
    assert not f and "[erledigt]" in t
    t, _ = werkzeug(basis, MITREISEND, "zeige", id="AG-01")
    assert "Anna: status: offen → erledigt; gebucht" in t
    t, _ = werkzeug(basis, MITREISEND, "aufgaben")
    assert "AG-01" not in t and "AG-02" in t
    t, f = werkzeug(basis, MITREISEND, "aufgabe_aendern", id="AG-77", status="erledigt", name="Anna")
    assert f and "nicht gefunden" in t
    t, f = werkzeug(basis, MITREISEND, "aufgabe_aendern", id="AG-02", frist="morgen", name="Anna")
    assert f and "Datum" in t


def test_merkmale_und_alternative(dienst):
    basis, ablage = dienst
    t, f = werkzeug(basis, MITREISEND, "merkmale", ziel="V-03")
    assert not f and "Preis pro Nacht" in t and "85 €" in t and "Fehlt noch" in t and "fragen:" in t
    t, f = werkzeug(basis, MITREISEND, "merkmale", bereich="strecke")
    assert not f and "berechnet" in t
    t, f = werkzeug(basis, MITREISEND, "merkmale", ziel="T-01")
    assert f
    t, _ = werkzeug(basis, MITREISEND, "zeige", id="U-01")
    assert "Preis pro Nacht: 120 €" in t
    # Bestimmer: Auftrag mit strukturierten Daten
    t, f = werkzeug(basis, ALT_BESTIMMER, "alternative_vorschlagen", wahlstelle="V-03", titel="Hotel Test",
                    merkmale={"preis": {"wert": "150 €", "geprueft": "2026-10-26"}, "pool": {"wert": "ja"}})
    assert not f and "Hotel Test" in t and "neues Merkmal" in t
    a = rm.auftraege(ablage / "beispielreise")
    assert a[0]["ziel"] == "V-03" and a[0]["daten"]["merkmale"]["preis"]["wert"] == "150 €"
    t, f = werkzeug(basis, ALT_BESTIMMER, "alternative_vorschlagen", wahlstelle="V-03", titel="X",
                    merkmale={"fruehstueck": {"wert": "vielleicht"}})
    assert f and "erlaubt" in t
    t, f = werkzeug(basis, ALT_BESTIMMER, "alternative_vorschlagen", titel="X", bereich="unterkunft")
    assert f and "an angeben" in t
    # Mitreisende: Rückmeldung der Art Ergänzung, mit Namen
    t, f = werkzeug(basis, MITREISEND, "alternative_vorschlagen", wahlstelle="V-03", titel="Hotel Test")
    assert f and "Name fehlt" in t
    t, f = werkzeug(basis, MITREISEND, "alternative_vorschlagen", wahlstelle="V-03", titel="Hotel Test", name="Anna")
    assert not f
    e = rm.eintraege(ablage / "beispielreise")[0]
    assert e["art"] == "Ergänzung" and e["ziel"] == "V-03" and "Hotel Test" in e["text"]
