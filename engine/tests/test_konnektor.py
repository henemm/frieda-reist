"""Tests für engine/konnektor.py: MCP-Protokoll, Rollen, Werkzeuge, Weitergabe an den Rückmeldedienst."""
import json
import shutil
import sys
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import bauen  # noqa: E402
import konnektor as kn  # noqa: E402
import rueckmeldungen as rm  # noqa: E402
from schnittstelle_hilfe import N, intern_liste  # noqa: E402
from conftest import mcp_intern, meldet, zugaenge_datei  # noqa: E402

WURZEL = Path(__file__).resolve().parent.parent.parent
BEISPIEL = WURZEL / "beispiel" / "reisen" / "beispielreise"   # erfundene Reise: ida organisator, karl mitwirkend
ALT_ORGANISATOR = "h" * 32  # Kurzname der Organisatorin Ida (person ida)
KARL = "f" * 32          # Kurzname einer Person (reise.yaml personen: karl, mitwirkend)
GAST = "r" * 32       # Kurzname der Person kim, Rolle gast, nur lesen (nur in der Kopie der Testvorbereitung)
WEG = "w" * 32           # Link einer Person, die es in reise.yaml nicht (mehr) gibt
IDA_KONTO = {"konto": "ida", "name": "Ida", "konto_id": "k-ida"}   # wie der Konnektor „Frieda“ reise_anlegen ruft


@pytest.fixture(scope="module")
def seiten(tmp_path_factory):
    """Seiten aus einer Kopie der Beispielreise mit dem Gast Kim (Person kim, Rolle gast); die Beispielreise im Repo
    bleibt ohne Gast (#426)."""
    quelle = tmp_path_factory.mktemp("quelle") / "beispielreise"
    shutil.copytree(BEISPIEL, quelle)
    y = yaml.safe_load((quelle / "reise.yaml").read_text(encoding="utf-8"))
    y["personen"]["kim"] = {"name": "Kim", "rolle": "gast", "reist": True}
    (quelle / "reise.yaml").write_text(yaml.safe_dump(y, allow_unicode=True, sort_keys=False), encoding="utf-8")
    s = tmp_path_factory.mktemp("seiten")
    bauen.bauen(quelle, s / "beispielreise")
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
    zug.write_text(json.dumps({ALT_ORGANISATOR: {"reise": "beispielreise", "person": "ida"},
                               KARL: {"reise": "beispielreise", "person": "karl"},
                               GAST: {"reise": "beispielreise", "person": "kim"},
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
    code, a = mcp_intern(token, {"jsonrpc": "2.0", "id": nid, "method": methode, "params": params or {}})
    assert code == 200, a
    return intern_liste(a["result"]) if methode == "tools/list" else a["result"]


def werkzeug(basis, token, werkzeugname, **args):
    r = rpc(basis, token, "tools/call", {"name": werkzeugname, "arguments": args})
    return r["content"][0]["text"], r["isError"]


def test_unbekannter_link(dienst):
    basis, _ = dienst
    assert anfrage(f"{basis}/{'x' * 32}", {"jsonrpc": "2.0", "id": 1, "method": "ping"})[0] == 404
    assert anfrage(f"{basis}/", {"jsonrpc": "2.0", "id": 1, "method": "ping"})[0] == 404
    assert anfrage(f"{basis}/{ALT_ORGANISATOR}/x", {"jsonrpc": "2.0", "id": 1, "method": "ping"})[0] == 404


def test_initialize_und_protokoll(dienst):
    basis, _ = dienst
    r = rpc(basis, KARL, "initialize", {"protocolVersion": "2025-03-26", "capabilities": {},
                                              "clientInfo": {"name": "t", "version": "1"}})
    assert r["protocolVersion"] == "2025-03-26"
    assert "tools" in r["capabilities"]
    assert "Beispielreise" in r["serverInfo"]["title"]
    assert "Karl" in r["instructions"] and "Vornamen" not in r["instructions"]
    assert rpc(basis, KARL, "initialize", {"protocolVersion": "1999-01-01"})["protocolVersion"] == kn.PROTOKOLLE[0]
    # Benachrichtigung: keine Antwort (über HTTP 202)
    assert mcp_intern(KARL, {"jsonrpc": "2.0", "method": "notifications/initialized"}) == (202, None)
    code, a = mcp_intern(KARL, {"jsonrpc": "2.0", "id": 7, "method": "gibtsnicht"})
    assert a["error"]["code"] == -32601
    # Die geheimen Links je Reise sind abgeschafft (#421): über HTTP gibt es den Weg nicht mehr
    for methode in ("POST", "GET"):
        assert anfrage(f"{basis}/{KARL}", {"jsonrpc": "2.0", "id": 1, "method": "ping"} if methode == "POST" else None,
                       methode=methode)[0] == 404


def test_initialize_meldet_symbol_der_reise(dienst, seiten):
    """Die Claude-App zeigt beim Konnektor das Symbol der Reise (serverInfo.icons), dasselbe wie die Seite."""
    import base64
    basis, _ = dienst
    icons = rpc(basis, KARL, "initialize", {"protocolVersion": "2025-11-25"})["serverInfo"]["icons"]
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
        r = rpc(basis, KARL, "initialize", {"protocolVersion": "2025-11-25"})
        assert "icons" not in r["serverInfo"] and "Beispielreise" in r["serverInfo"]["title"]
    finally:
        for f, b in zip(versteckt, inhalte):
            f.write_bytes(b)


def test_ueberblick_zeigt_stand(dienst, monkeypatch):
    """Man sieht in der App, wann die Reise veröffentlicht wurde und ob der Dienst den neuen Code geladen hat."""
    basis, _ = dienst
    t, f = werkzeug(basis, KARL, "ueberblick")
    assert not f and "## Stand" in t and meldet(t, "konnektor.stand_text.1") and f"Code {kn._CODE_START}" in t
    assert "Neustart" not in t
    monkeypatch.setattr(kn, "_CODE_START", "00000000")
    t, _ = werkzeug(basis, KARL, "ueberblick")
    assert meldet(t, "konnektor.stand_text.3")


def test_ueberblick_nennt_den_kartenstatus(dienst):
    """#233 (K11): overview nennt, ob die Karte gebaut ist, woraus und mit wie vielen Punkten."""
    basis, _ = dienst
    t, f = werkzeug(basis, KARL, "ueberblick")
    assert not f and "Karte: handgepflegt (plan/karte.yaml), 8 Punkte." in t


def test_ueberblick_ohne_einarbeiten(dienst):
    """ADR-0001, O-3: Es gibt keinen Einarbeiten-Lauf mehr; der Überblick nennt ihn nicht, die Anleitung sagt, dass
    Eingetragenes sofort gilt."""
    basis, _ = dienst
    t, _ = werkzeug(basis, ALT_ORGANISATOR, "ueberblick")
    assert "Einarbeiten" not in t and "eingearbeitet" not in t and "## Stand" in t
    anleitung = rpc(basis, ALT_ORGANISATOR, "initialize")["instructions"]
    assert "sag nie, etwas sei schon geändert" not in anleitung and "Einarbeiten" not in anleitung
    assert "schreibt es sofort in die Reise" in anleitung


def test_status_mit_kommentar_erscheint_beim_absender(dienst):
    """Was rueckmeldung_erledigen (oder setze) einträgt, sieht der Absender sofort im Werkzeug rueckmeldungen (die Seite liest dieselbe Datei)."""
    basis, _ = dienst
    t, f = werkzeug(basis, KARL, "rueckmeldung_geben", ziel="T-03", art="Kommentar", text="Schön!")
    assert not f
    rid = t.split()[2]
    rm.setze("beispielreise", rid, "uebernommen", "Steht jetzt im Text von T-03.")
    t, f = werkzeug(basis, KARL, "rueckmeldungen")
    assert not f and rid in t and "Steht jetzt im Text von T-03." in t


def test_stapel(dienst):
    basis, _ = dienst
    code, a = mcp_intern(KARL, [{"jsonrpc": "2.0", "id": 1, "method": "ping"},
                                                {"jsonrpc": "2.0", "method": "notifications/initialized"},
                                                {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}])
    assert code == 200 and [x["id"] for x in a] == [1, 2]


def test_werkzeuge_je_rolle(dienst):
    basis, _ = dienst
    m = {t["name"] for t in rpc(basis, KARL, "tools/list")["tools"]}
    h = {t["name"] for t in rpc(basis, ALT_ORGANISATOR, "tools/list")["tools"]}
    assert "auftrag_geben" not in m and "rueckmeldung_geben" in m
    assert h == m | {"entscheiden", "person_einladen", "person_entfernen", "rueckmeldung_erledigen"}
    assert "frage_beantworten" in m and not {"entscheiden", "person_einladen"} & m   # Paket C
    assert {t["name"] for t in rpc(basis, KARL, "tools/list")["tools"]} == m
    r = {t["name"] for t in rpc(basis, GAST, "tools/list")["tools"]}
    assert r == m - kn.SCHREIB_WERKZEUGE and "zeige" in r
    assert "start_ende_setzen" not in h   # Issue #142: ein Werkzeug des Schreibwegs, ohne ihn nicht angeboten


def test_rollen_aus_reise_yaml(dienst):
    basis, ablage = dienst
    # Person: Name steht fest, auch wenn ein anderer genannt wird
    t, f = werkzeug(basis, KARL, "rueckmeldung_geben", ziel="T-03", art="Kommentar", text="Schön!", name="Jemand")
    assert not f and rm.eintraege(ablage / "beispielreise")[0]["name"] == "Karl"
    t, f = werkzeug(basis, KARL, "entscheiden", option="V-01.b", status="gewaehlt", grund="x")
    assert f and "nur Organisator:innen" in t
    # Rolle gast: nur lesen
    t, f = werkzeug(basis, GAST, "zeige", id="T-02")
    assert not f and "T-02" in t
    t, f = werkzeug(basis, GAST, "rueckmeldung_geben", ziel="T-03", art="Kommentar", text="x", name="Kim")
    assert f and "nur lesen" in t
    t, f = werkzeug(basis, GAST, "aufgabe_anlegen", titel="x", name="Kim")
    assert f and "nur lesen" in t
    # Zugang einer Person, die es nicht mehr gibt
    t, f = werkzeug(basis, WEG, "ueberblick")
    assert f and "keiner Person" in t
    # Anleitung nennt Person, Rolle, Organisator:innen und Status
    d = kn.daten("beispielreise")
    a = kn.anleitung({"reise": "beispielreise", "person": "karl"}, d)
    assert "Du sprichst mit Karl (Mitwirkende:r)" in a and "Ida entscheidet" in a and "Status planung" in a
    assert "Vornamen" not in a
    assert "Du sprichst mit Ida (Organisator:in)" in kn.anleitung({"reise": "beispielreise", "person": "ida"}, d)
    # Frieda spricht in Namen, nicht in Kennungen (28.10.2026)
    assert "Namen statt Kennungen" in a and "IDs in Antworten nennen" not in a
    assert "Du sprichst mit Kim (Rolle gast): nur lesen" in kn.anleitung({"reise": "beispielreise", "person": "kim"}, d)


def test_lesen(dienst):
    basis, _ = dienst
    t, f = werkzeug(basis, KARL, "ueberblick")
    assert not f and "T-01" in t and "Offene Fragen" in t
    t, f = werkzeug(basis, KARL, "zeige", id="E-01")
    assert not f and "Bastei" in t and "E-01.eckdaten" in t
    assert "Gliederung des Lesetexts" in t and "- Charakter: Wie sich der Tag anfühlt" in t   # arten.yaml lesetext
    assert "gehzeit: ca. 3:40 h; aufstieg: 485" in t   # Kennzahlen an der Strecke (#269), nicht mehr in den Eckdaten des Dossiers
    t, f = werkzeug(basis, KARL, "zeige", id="E-01.eckdaten")
    assert "- Höchster Punkt: Bastei, ca. 300 m" in t and "Gehzeit" not in t   # zweispaltige Tabelle als Merkmalliste (#54)
    t, f = werkzeug(basis, KARL, "zeige", id="V-03.a")
    assert "gewaehlt" in t and "Ida" in t
    t, f = werkzeug(basis, KARL, "zeige", id="T-99")
    assert f and "gibt es nicht" in t
    t, f = werkzeug(basis, KARL, "suche", begriff="pension burgblick")
    assert "U-02" in t
    t, f = werkzeug(basis, KARL, "offene_fragen")
    assert "F-01" in t
    assert "F-02" not in t   # geklärt, nicht mehr offen
    t, f = werkzeug(basis, KARL, "varianten")
    assert "P-B" in t and "V-01.b" in t


def test_rueckmeldung_mitwirkend(dienst):
    basis, ablage = dienst
    t, f = werkzeug(basis, KARL, "rueckmeldung_geben", ziel="T-03", art="Kommentar", text="Schön!")
    assert not f and "R-" in t
    e = rm.eintraege(ablage / "beispielreise")
    assert len(e) == 1 and e[0]["name"] == "Karl" and e[0]["quelle"] == "über Claude"
    t, f = werkzeug(basis, KARL, "rueckmeldung_geben", ziel="T-03", art="Unsinn", text="x")
    assert f and "unbekannte Art" in t
    t, _ = werkzeug(basis, KARL, "rueckmeldungen")
    assert "Karl" in t and "Schön!" in t


def test_wunsch_ueber_konnektor(dienst):
    basis, ablage = dienst
    t, f = werkzeug(basis, KARL, "rueckmeldung_geben", art="Wunsch", text="Einmal auf den Lilienstein")
    assert not f and "R-" in t
    e = rm.eintraege(ablage / "beispielreise")[0]
    assert e["ziel"] == rm.WUNSCH_ZIEL and e["art"] == "Wunsch"


def test_anleitung_nennt_wuensche_nur_wenn_eingeschaltet():
    zugang = {"reise": "beispielreise", "person": "karl"}
    karl = {"personen": [{"schluessel": "karl", "name": "Karl", "rolle": "mitwirkend"}]}
    assert "art Wunsch" not in kn.anleitung(zugang, {"reise": karl})
    assert "art Wunsch" in kn.anleitung(zugang, {"reise": {**karl, "bausteine": ["wuensche"]}})


def test_rueckmeldung_alter_organisator_name_fest(dienst):
    basis, ablage = dienst
    werkzeug(basis, ALT_ORGANISATOR, "rueckmeldung_geben", ziel="F-01", art="Antwort", text="Mit der Bahn", name="Jemand")
    assert rm.eintraege(ablage / "beispielreise")[0]["name"] == "Ida"


def test_reise_anlegen_prueft_und_braucht_den_schreibweg(dienst, capsys):
    """reise_anlegen (Konnektor „Frieda“) prüft die Eingaben sofort; ohne eingerichteten Schreibweg legt der Dienst nichts
    an (ADR-0001, O-3). Den alten Konto-Link (Paket H) gibt es nicht mehr (#421)."""
    basis, ablage = dienst
    assert anfrage(f"{basis}/{'c' * 32}", {"jsonrpc": "2.0", "id": 1, "method": "ping"})[0] == 404
    t, f = kn.reise_anlegen(IDA_KONTO, {"titel": "Ski", "von": "2027-02-13", "bis": "2027-02-06"})
    assert f and meldet(t, "pruefung.reise_neu.4")
    t, f = kn.reise_anlegen(IDA_KONTO, {"titel": "Beispielreise", "von": "2027-02-06", "bis": "2027-02-13", "pfad": "beispielreise"})
    assert f and "gibt es schon" in t
    t, f = kn.reise_anlegen(IDA_KONTO, {"titel": "Winterwoche im Allgäu", "von": "2027-02-06", "bis": "2027-02-13",
                                        "personen": [{"vorname": "Karl", "rolle": "mitwirkend"}]})
    assert f and "Schreibweg dieser Instanz ist nicht eingerichtet" in t
    o = rm.ordner_neu()
    assert not (o and (o / "auftraege.jsonl").exists()) and not (ablage / rm.NEU).exists()


def test_alte_befehle_fuer_links_gibt_es_nicht_mehr(capsys):
    """zugang, konto und zugaenge stellten geheime Links aus; seit #421 kennt die Kommandozeile nur noch dienst."""
    for befehl in (["zugang", "beispielreise", "karl"], ["konto", "ida", "Ida"], ["zugaenge"]):
        assert kn.main(befehl) == 1
    assert not hasattr(kn, "zugang_ausstellen") and not hasattr(kn, "zugang_zu")


def test_text_aus_html():
    assert kn.text('<p>Hallo <a href="https://x.de">Link</a></p><ul><li>a</li><li>b</li></ul>') == \
        "Hallo [Link](https://x.de)\n\n- a\n- b"
    assert kn.text("<table><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>2</td></tr></table>") == "| A | B |\n| 1 | 2 |"
    # Merkmalliste aus einer zweispaltigen Tabelle (B2, #54)
    assert kn.text('<p>Vor</p><div class="tabelle merkmale"><dl class="textmerkmale"><div><dt>Ein-/<wbr>Aus</dt><dd>3</dd></div>'
                   '<div><dt>B</dt><dd>2</dd></div></dl></div><p>Nach</p>') == "Vor\n\n- Ein-/Aus: 3\n- B: 2\n\nNach"


def test_gesund_ohne_token(dienst, tmp_path, monkeypatch):
    """Bereit, wenn es freigeschaltete Reisen gibt (seiten.json im Ordner des Konnektors) und jede veröffentlicht ist; die
    Antwort verrät keine Reise."""
    basis, _ = dienst
    assert kn.konnektor_ordner() == tmp_path
    assert anfrage(f"{basis}/gesund", methode="GET") == (503, {"gesund": False})      # noch keine Reise freigeschaltet
    links = tmp_path / "seiten.json"
    links.write_text(json.dumps({"beispielreise": "https://beispiel.invalid/beispielreise/"}))
    assert anfrage(f"{basis}/gesund", methode="GET") == (200, {"gesund": True})
    links.write_text(json.dumps({"beispielreise": "…", "gibtsnicht": "…"}))
    assert anfrage(f"{basis}/gesund", methode="GET") == (503, {"gesund": False})
    links.write_text("{kaputt")
    assert anfrage(f"{basis}/gesund", methode="GET")[0] == 503


def test_gesund_ueberspringt_zur_loeschung_vorgemerkte_reise(dienst, tmp_path, monkeypatch):
    """#539: Eine zur Löschung vorgemerkte Reise (#381) hat keine Seite mehr, steht aber noch in seiten.json; die
    Bereitschaft darf deshalb nicht auf 503 fallen. Ohne den Vormerk bleibt eine fehlende Seite ein Fehler."""
    import konten
    basis, _ = dienst
    monkeypatch.setenv("FR_KONTEN", str(tmp_path / "konten"))
    (tmp_path / "seiten.json").write_text(json.dumps({"beispielreise": "…", "geloeschte-reise": "…"}))
    assert anfrage(f"{basis}/gesund", methode="GET") == (503, {"gesund": False})
    konten.loeschung_vormerken("geloeschte-reise", "k-ida")
    assert anfrage(f"{basis}/gesund", methode="GET") == (200, {"gesund": True})
    # Nur vorgemerkte Reisen: nichts Freigeschaltetes übrig, also nicht bereit
    (tmp_path / "seiten.json").write_text(json.dumps({"geloeschte-reise": "…"}))
    assert anfrage(f"{basis}/gesund", methode="GET") == (503, {"gesund": False})


def test_nacht_ohne_doppelten_namen(seiten, tmp_path, monkeypatch):
    monkeypatch.setenv("KN_SEITEN", str(seiten))
    zugang = {"reise": "beispielreise", "person": "karl"}
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


def _konto_mit_einladung(reise="beispielreise"):
    """Ida hat ein Konto und ist verknüpft; für Karl liegt eine offene Einladung vor (erfundene Adresse)."""
    import konten
    from contextlib import closing
    with closing(konten.db()) as v, v:
        v.execute("INSERT INTO konten (id, email, name, angelegt) VALUES ('K-ida', 'ida@example.invalid', 'Ida', '2026-11-08')")
        v.execute("INSERT INTO einladungen (hash, reise, schluessel, email, rolle, name, von, erstellt, ablauf) "
                  "VALUES ('h1', ?, 'karl', 'karl@example.invalid', 'mitwirkend', 'Karl', 'Ida', 0, 9999999999)", (reise,))
    konten.verknuepfen("K-ida", reise, "ida")


def test_personen_ueber_konnektor(dienst):
    """#406: Alle Mitglieder sehen Name, Rolle, reist mit und von/bis; den Zugangsstand nur Organisator:innen;
    E-Mail-Adressen und Notizen nie."""
    basis, _ = dienst
    _konto_mit_einladung()
    for token in (KARL, GAST, ALT_ORGANISATOR):
        assert "personen" in {t["name"] for t in rpc(basis, token, "tools/list")["tools"]}
    for token in (KARL, GAST):
        t, f = werkzeug(basis, token, "personen")
        assert not f and meldet(t, "konnektor.personen.kopf") and "Ida" in t and "Karl" in t
        assert "organisator" in t and "mitwirkend" in t and "14.5." in t
        assert not meldet(t, "konnektor.personen.zugang_angemeldet") and not meldet(t, "konnektor.personen.zugang_eingeladen")
        assert "@" not in t and "example.invalid" not in t and "Kirnitzschtalbahn" not in t
    t, f = werkzeug(basis, ALT_ORGANISATOR, "personen")
    assert not f and meldet(t, "konnektor.personen.zugang_angemeldet") and meldet(t, "konnektor.personen.zugang_eingeladen")
    assert "@" not in t and "example.invalid" not in t and "Kirnitzschtalbahn" not in t


def test_aufgaben_ueber_konnektor(dienst):
    basis, ablage = dienst
    m = {t["name"] for t in rpc(basis, KARL, "tools/list")["tools"]}
    assert {"aufgaben", "aufgabe_anlegen", "aufgabe_aendern"} <= m
    t, f = werkzeug(basis, KARL, "aufgabe_anlegen", titel="Pension buchen", bezug=["U-99"])
    assert f and "U-99" in t
    t, f = werkzeug(basis, KARL, "aufgabe_anlegen", titel="Pension buchen", bezug=["U-02", "T-02"],
                    zustaendig="Anna", prioritaet="hoch", ab="2026-11-03", frist="2026-11-10")
    assert not f and "AG-01" in t and "gilt sofort" in t
    t, f = werkzeug(basis, ALT_ORGANISATOR, "aufgabe_anlegen", titel="Bus prüfen", frist="2020-01-01", name="Egal")
    assert not f and rm.aufgaben(ablage / "beispielreise")[1]["erstellt_von"] == "Ida"
    t, _ = werkzeug(basis, KARL, "aufgaben", zustaendig="anna")
    assert "AG-01" in t and "AG-02" not in t
    t, _ = werkzeug(basis, KARL, "aufgaben", bezug="U-02")
    assert "AG-01" in t and "Pension Burgblick" in t
    t, _ = werkzeug(basis, KARL, "zeige", id="T-02")
    assert meldet(t, "konnektor.ausgabe.zeige.2") and "AG-01" in t
    t, _ = werkzeug(basis, KARL, "ueberblick")
    # Fristen zählen erst ab Status fest (test_regeln.py): in der Planung steht die Zahl, aber nichts ist überfällig
    assert "Offene Aufgaben: 2" in t and "überfällig" not in t
    t, f = werkzeug(basis, KARL, "aufgabe_aendern", id="AG-01", status="erledigt", kommentar="gebucht")
    assert not f and "[erledigt]" in t
    t, _ = werkzeug(basis, KARL, "zeige", id="AG-01")
    assert "Karl: status: offen → erledigt; gebucht" in t
    t, _ = werkzeug(basis, KARL, "aufgaben")
    assert "AG-01" not in t and "AG-02" in t
    t, f = werkzeug(basis, KARL, "aufgabe_aendern", id="AG-77", status="erledigt")
    assert f and "nicht gefunden" in t
    t, f = werkzeug(basis, KARL, "aufgabe_aendern", id="AG-02", frist="morgen")
    assert f and "Datum" in t


def test_merkmale_lesen(dienst):
    basis, ablage = dienst
    t, f = werkzeug(basis, KARL, "merkmale", ziel="V-03")
    assert not f and "Preis pro Nacht" in t and "85 €" in t and "Fehlt noch" in t and "fragen:" in t
    # Stufen in Worten für Menschen, Schlüssel in Klammern (Product Owner 29.10.2026); „aus“ steht nirgends
    assert "nötig (pflicht)" in t and "gut zu wissen (empfohlen)" in t and "; Pflicht" not in t and "(aus)" not in t
    t, f = werkzeug(basis, KARL, "merkmale", bereich="wandern")
    assert not f and "berechnet" in t
    t, f = werkzeug(basis, KARL, "merkmale", ziel="T-01")
    assert f
    t, _ = werkzeug(basis, KARL, "zeige", id="U-01")
    assert "Preis pro Nacht: 120 €" in t


def test_hinweis_einer_strecke_in_show(dienst):
    """#448: Der Hinweis an einer Strecke (item_update hinweis) steht in show, wie bei Unterkunft und Aufenthalt."""
    basis, _ = dienst
    t, f = werkzeug(basis, KARL, "zeige", id="E-21")
    assert not f and "Abfahrt am Bahnhof auf der anderen Elbseite" in t, t


def test_kategorien_lesen(dienst):
    """Das Gegenstück zu kategorie_definieren: die Kategorien der Reise lassen sich auch lesen."""
    basis, ablage = dienst
    t, f = werkzeug(basis, KARL, "kategorien")
    assert not f and ("Kartenkategorien" in t)
    if "noch keine" not in t:
        assert "Farbe" in t and "Gruppe" in t

def test_merkmale_einer_strecke(dienst):
    """Paket 3 (#18): Merkmale einer Strecke (Liste ihrer Art). Vorschlagen und Werte je Datum gehen seit O-3 über den Schreibweg
    (option_anlegen, wert_eintragen; test_schreiben.py)."""
    basis, ablage = dienst
    # Strecke als Ziel: Liste ihrer Art (E-20 ist eine Bahnfahrt)
    t, f = werkzeug(basis, KARL, "merkmale", ziel="E-20")
    assert not f and "Art bahn" in t and "## E-20" in t and "Fehlt noch" not in t and "gilt" in t   # bahn hat nur empfohlene Merkmale (O-5: kein Fehlt)



def test_aehnliches_merkmal():
    from konnektor import aehnliches_merkmal
    # generisch (Schreibweise, Wortstamm) und über Zweitnamen der Reise (auch); keine Wortliste in der Software (ADR-0001)
    liste = [{"id": "geoeffnet", "name": "Geöffnet am Reisedatum"}, {"id": "preis", "name": "Preis pro Nacht", "auch": ["kosten"]},
             {"id": "fruehstueck", "name": "Frühstück"}]
    assert aehnliches_merkmal("oeffnung", liste)["id"] == "geoeffnet"
    assert aehnliches_merkmal("Öffnungszeiten", liste)["id"] == "geoeffnet"
    assert aehnliches_merkmal("preis_pro_nacht", liste)["id"] == "preis"
    assert aehnliches_merkmal("kosten", liste)["id"] == "preis"
    assert aehnliches_merkmal("frühstück", liste)["id"] == "fruehstueck"
    assert aehnliches_merkmal("pool", liste) is None and aehnliches_merkmal("sauna", liste) is None
    assert aehnliches_merkmal("tarif", liste) is None   # kein Synonymwissen in der Software


# ---------- Ontologie im Gespräch (ADR-0001, O-3): art_definieren, merkmal_definieren ----------

class Schreibweg(kn.BaseHTTPRequestHandler):
    """Nachgestellter Schreibdienst (engine/schreiben.py dienst): merkt sich die Anfrage, antwortet wie der echte."""
    anfragen = []
    antwort = (200, {"ok": True, "text": "Art „Refugi“ angelegt: Schlüssel refugi, Grundform Aufenthalt, Farbe gruen."})
    im_repo = set()   # Buchungen, die der nachgestellte Schreibweg auf main kennt (GET /<reise>/buchung/<B-id>)

    def do_GET(self):
        teile = self.path.strip("/").split("/")
        gibt_es = len(teile) == 3 and teile[1] == "buchung" and teile[2] in Schreibweg.im_repo \
            and self.headers.get("X-Frieda-Dienst") == konten_geheimnis()
        daten = json.dumps({"gibt_es": gibt_es}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(daten)))
        self.end_headers()
        self.wfile.write(daten)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
        Schreibweg.anfragen.append((self.path, self.headers.get("X-Frieda-Dienst"), body))
        code, obj = Schreibweg.antwort
        daten = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(daten)))
        self.end_headers()
        self.wfile.write(daten)

    def log_message(self, *a):
        pass


def konten_geheimnis():
    import konten
    return konten.dienst_geheimnis()


@pytest.fixture
def schreibweg(dienst, monkeypatch, tmp_path):
    monkeypatch.setenv("FR_KONTEN", str(tmp_path / "konten"))
    Schreibweg.anfragen = []
    Schreibweg.im_repo = set()
    s, url = starten(Schreibweg)
    monkeypatch.setenv("KN_SCHREIBDIENST", url)
    yield dienst
    s.shutdown()


def test_ontologie_werkzeuge_nur_mit_schreibweg(dienst, monkeypatch):
    basis, _ = dienst
    monkeypatch.delenv("KN_SCHREIBDIENST", raising=False)
    namen = {t["name"] for t in rpc(basis, ALT_ORGANISATOR, "tools/list")["tools"]}
    assert not namen & set(kn.ONTOLOGIE_WERKZEUGE)
    t, f = werkzeug(basis, ALT_ORGANISATOR, "art_definieren", bezeichnung="Refugi", grundform="aufenthalt")
    assert f and "nicht eingerichtet" in t
    assert "art_definieren" not in rpc(basis, ALT_ORGANISATOR, "initialize")["instructions"]


def test_ontologie_organisator_schreibt_direkt(schreibweg):
    import konten
    basis, ablage = schreibweg
    for token, da in ((ALT_ORGANISATOR, True), (KARL, True), (GAST, False)):
        namen = {t["name"] for t in rpc(basis, token, "tools/list")["tools"]}
        nur_org = {"tag_aendern", "frage_schliessen", "reise_status_setzen", "einstellung_setzen",
                   # Abgleich 29.10.2026: Plan, Eckdaten und Ontologie ändern nur Organisator:innen
                   "tag_anlegen", "termin_setzen", "wahlstelle_aendern", "reise_aendern", "plan_anlegen", "plan_aendern",
                   "merkmal_zusammenfuehren", "arten_uebernehmen",
                   "start_ende_setzen",   # Issue #142
                   "symbol_setzen", "kartenansicht_setzen", "kartenpunkte_holen",   # Issue #252
                   "packliste_uebernehmen"}   # #370
        assert (set(kn.ONTOLOGIE_WERKZEUGE) - nur_org - set(kn.ALIAS_ZU_DING_AENDERN) - set(kn.ALIAS_ZU_ART) <= namen) is da, token
        assert not (set(kn.ALIAS_ZU_DING_AENDERN) | set(kn.ALIAS_ZU_ART) | {"kategorien"}) & namen   # Aliase von item_update (ADR-0007, Schritt c) stehen nicht mehr in der Liste
        assert ("start_ende_setzen" in namen) is (token == ALT_ORGANISATOR), token
        assert ("symbol_setzen" in namen) is (token == ALT_ORGANISATOR), token
    anleitung = rpc(basis, ALT_ORGANISATOR, "initialize")["instructions"]
    assert N("Arten und Merkmale (art_definieren, merkmal_definieren") in anleitung and "schreibt es sofort in die Reise" in anleitung
    t, f = werkzeug(basis, ALT_ORGANISATOR, "art_definieren", bezeichnung="Refugi", grundform="aufenthalt", grund="Hütten am Weg")
    assert not f and t.startswith("Eingetragen und gesichert (Ida): Art „Refugi“ angelegt") and "sobald veröffentlicht ist" in t
    pfad, geheim, body = Schreibweg.anfragen[-1]
    assert pfad == "/beispielreise/art_definieren" and geheim == konten.dienst_geheimnis()
    assert body == {"person": "ida", "name": "Ida", "rolle": "organisator",
                    "args": {"bezeichnung": "Refugi", "grundform": "aufenthalt", "grund": "Hütten am Weg"}}
    assert rm.eintraege(ablage / "beispielreise") == []        # keine Rückmeldung, direkt geschrieben
    # Ablehnung des Schreibwegs kommt mit Grund an
    Schreibweg.antwort = (422, {"ok": False, "fehler": "Die Grundform von „Hotel“ lässt sich nicht ändern (aufenthalt)."})
    t, f = werkzeug(basis, ALT_ORGANISATOR, "art_definieren", art="hotel", grundform="bewegung")
    assert f and t == "Nicht eingetragen: Die Grundform von „Hotel“ lässt sich nicht ändern (aufenthalt)."
    Schreibweg.antwort = (200, {"ok": True, "text": "x"})
    # Ähnliches Merkmal: erst Hinweis, mit trotzdem geht es
    t, f = werkzeug(basis, ALT_ORGANISATOR, "merkmal_definieren", art="hotel", bezeichnung="Frühstück inklusive", typ="auswahl", werte=["ja", "nein"])
    assert f and "ähnliches Merkmal" in t and "fruehstueck" in t
    t, f = werkzeug(basis, ALT_ORGANISATOR, "merkmal_definieren", art="hotel", bezeichnung="Frühstück inklusive", typ="auswahl",
                    werte=["ja", "nein"], trotzdem=True)
    assert not f and Schreibweg.anfragen[-1][2]["args"] == {"art": "hotel", "bezeichnung": "Frühstück inklusive", "typ": "auswahl",
                                                            "werte": ["ja", "nein"]}
    t, f = werkzeug(basis, ALT_ORGANISATOR, "merkmal_definieren", art="hotel", bezeichnung="Stornierung", typ="auswahl", werte=["ja", "nein"])
    assert not f and Schreibweg.anfragen[-1][2]["args"]["bezeichnung"] == "Stornierung"
    # Nicht erreichbar
    Schreibweg.anfragen.clear()
    with pytest.MonkeyPatch.context() as m:
        m.setenv("KN_SCHREIBDIENST", "http://127.0.0.1:9")
        t, f = werkzeug(basis, ALT_ORGANISATOR, "art_definieren", bezeichnung="X", grundform="folge")
    assert f and "nicht erreichbar" in t


def test_arten_uebernehmen_aus_unbekannter_reise_lehnt_ab_statt_abzustuerzen(schreibweg):
    """Die Vorprüfung nutzte REISE_MUSTER ohne Modul (NameError bei jedem Aufruf): eine unbekannte Quellreise wird abgelehnt."""
    basis, _ = schreibweg
    for von in ("gibt-es-nicht-1", "../x", ""):
        t, f = werkzeug(basis, ALT_ORGANISATOR, "arten_uebernehmen", von_reise=von)
        assert f and "Traceback" not in t and "NameError" not in t
        assert "gibt es nicht" in t or "does not exist" in t, t


def test_ontologie_mitwirkende_schlagen_vor(schreibweg):
    basis, ablage = schreibweg
    t, f = werkzeug(basis, KARL, "art_definieren", bezeichnung="Refugi", grundform="aufenthalt")
    assert not f and "Vorschlag R-" in t and "Ida" in t
    assert Schreibweg.anfragen == []                            # nichts direkt geschrieben
    e = rm.eintraege(ablage / "beispielreise")[0]
    assert e["name"] == "Karl" and e["art"] == "Ergänzung" and e["ziel"] == "refugi"
    assert e["text"] == "Art festlegen – bezeichnung: Refugi; grundform: aufenthalt"
    t, f = werkzeug(basis, KARL, "merkmal_definieren", art="hotel", bezeichnung="Stornierung", typ="auswahl", werte=["ja", "nein"], stufe="pflicht")
    assert not f
    e = next(x for x in rm.eintraege(ablage / "beispielreise") if x["ziel"] == "hotel")
    # die Stufe steht im Vorschlag als Wort für Menschen, nicht als Schlüssel (Product Owner 29.10.2026)
    assert e["text"] == "Merkmal festlegen – art: hotel; bezeichnung: Stornierung; typ: auswahl; werte: ja | nein; stufe: nötig (pflicht)"
    t, f = werkzeug(basis, GAST, "art_definieren", bezeichnung="Refugi", grundform="aufenthalt")
    assert f and "nur lesen" in t


def test_kategorie_definieren_ueber_den_schreibweg(schreibweg):
    """kategorie_definieren (O-7): Organisator:innen schreiben direkt, Mitwirkende schlagen vor, Gäste sehen das Werkzeug nicht."""
    import konten
    basis, ablage = schreibweg
    for token, da in ((ALT_ORGANISATOR, True), (KARL, True), (GAST, False)):
        namen = {t["name"] for t in rpc(basis, token, "tools/list")["tools"]}
        assert "kategorie_definieren" not in namen and "kategorien" not in namen, token   # Alias von art_definieren (ADR-0007, Schritt d)
        assert ("art_definieren" in namen) is da, token
    Schreibweg.antwort = (200, {"ok": True, "text": "Kategorie „Aussicht“ angelegt: Schlüssel aussicht, Gruppe punkt, Farbe #336699."})
    t, f = werkzeug(basis, ALT_ORGANISATOR, "kategorie_definieren", kategorie="aussicht", bezeichnung="Aussicht", gruppe="punkt", farbe="#336699")
    assert not f and "Kategorie „Aussicht“ angelegt" in t
    pfad, geheim, body = Schreibweg.anfragen[-1]
    assert pfad == "/beispielreise/kategorie_definieren" and geheim == konten.dienst_geheimnis()
    assert body["args"] == {"kategorie": "aussicht", "bezeichnung": "Aussicht", "gruppe": "punkt", "farbe": "#336699"}
    vorher = len(Schreibweg.anfragen)
    t, f = werkzeug(basis, KARL, "kategorie_definieren", kategorie="aussicht", bezeichnung="Aussicht", gruppe="punkt", farbe="blau",
                    art="viewpoint", art_bezeichnung="Aussichtspunkt")
    assert not f and "Vorschlag R-" in t and len(Schreibweg.anfragen) == vorher       # nichts direkt geschrieben
    e = next(x for x in rm.eintraege(ablage / "beispielreise") if x["ziel"] == "aussicht")
    assert e["name"] == "Karl" and e["art"] == "Ergänzung"
    assert e["text"] == ("Kartenkategorie festlegen – art: viewpoint; kategorie: aussicht; bezeichnung: Aussicht; gruppe: punkt; art_bezeichnung: "
                         "Aussichtspunkt; farbe: blau")


def test_wert_eintragen_ueber_den_schreibweg(schreibweg):
    basis, ablage = schreibweg
    for token, da in ((ALT_ORGANISATOR, True), (KARL, True), (GAST, False)):
        assert "wert_eintragen" not in {t["name"] for t in rpc(basis, token, "tools/list")["tools"]}, token   # Alias von item_update (ADR-0007)
        assert ("ding_aendern" in {t["name"] for t in rpc(basis, token, "tools/list")["tools"]}) is da, token
    Schreibweg.antwort = (200, {"ok": True, "text": "Preis pro Nacht an U-02 Pension Burgblick: 95 € (vorher: 85 €). Herkunft: Website."})
    t, f = werkzeug(basis, KARL, "wert_eintragen", ziel="U-02", merkmal="preis", wert="95 €", quelle="Website", geprueft="2026-10-29")
    assert not f and t.startswith("Eingetragen und gesichert (Karl): Preis pro Nacht an U-02")
    pfad, _, body = Schreibweg.anfragen[-1]
    assert pfad == "/beispielreise/ding_aendern" and body["person"] == "karl"   # kommt als item_update an (ADR-0007, Schritt c) and body["rolle"] == "mitwirkend"
    assert body["args"] == {"ziel": "U-02", "merkmal": "preis", "wert": "95 €", "quelle": "Website", "geprueft": "2026-10-29"}
    assert rm.eintraege(ablage / "beispielreise") == []
    # Eine unbekannte Stelle prüft der Schreibweg mit dem Repo, nicht der Konnektor mit der veröffentlichten Seite (Issue #135:
    # gerade Angelegtes ist sofort nutzbar)
    Schreibweg.antwort = (422, {"ok": False, "fehler": "Die Unterkunft U-77 gibt es nicht."})
    t, f = werkzeug(basis, KARL, "wert_eintragen", ziel="U-77", merkmal="preis", wert="1 €", quelle="x")
    assert f and t == "Nicht eingetragen: Die Unterkunft U-77 gibt es nicht." and Schreibweg.anfragen[-1][0] == "/beispielreise/ding_aendern"
    Schreibweg.antwort = (200, {"ok": True, "text": "ok"})
    t, f = werkzeug(basis, KARL, "wert_eintragen", ziel="U-02", merkmal="lage", wert="x", quelle="x", name="Anna")
    assert not f and Schreibweg.anfragen[-1][2]["name"] == "Karl" and "name" not in Schreibweg.anfragen[-1][2]["args"]
    t, f = werkzeug(basis, GAST, "wert_eintragen", ziel="U-02", merkmal="lage", wert="x", quelle="x")
    assert f and "nur lesen" in t
    Schreibweg.antwort = (422, {"ok": False, "fehler": "preis: „quelle“ fehlt."})
    t, f = werkzeug(basis, ALT_ORGANISATOR, "wert_eintragen", ziel="U-02", merkmal="preis", wert="1 €")
    assert f and t == "Nicht eingetragen: preis: „source“ fehlt."
    assert N("ding_aendern") in rpc(basis, KARL, "initialize")["instructions"]


def test_dinge_optionen_wahlstellen_fragen_ueber_den_schreibweg(schreibweg):
    basis, ablage = schreibweg
    neu = {"ding_anlegen", "ding_aendern", "option_anlegen", "wahlstelle_anlegen", "frage_anlegen"}
    for token, da in ((ALT_ORGANISATOR, True), (KARL, True), (GAST, False)):
        assert (neu <= {t["name"] for t in rpc(basis, token, "tools/list")["tools"]}) is da, token
    assert "alternative_vorschlagen" not in {t["name"] for t in rpc(basis, KARL, "tools/list")["tools"]}
    Schreibweg.antwort = (200, {"ok": True, "text": "Unterkunft U-05 „Pension Elbblick“ angelegt."})
    # Unbekanntes Merkmal: der Konnektor nennt das ähnliche, bevor etwas gesendet wird
    t, f = werkzeug(basis, KARL, "ding_anlegen", was="unterkunft", titel="Pension Elbblick", ort="O-02", art="pension", quelle="Website",
                    merkmale={"oeffnung": "ganzjährig"})
    assert f and "gemeint ist wohl geoeffnet" in t and Schreibweg.anfragen == []
    t, f = werkzeug(basis, KARL, "ding_anlegen", was="unterkunft", titel="Pension Elbblick", ort="O-02", art="pension", quelle="Website",
                    merkmale={"pool": "ja"})
    assert f and N("merkmal_definieren") in t
    t, f = werkzeug(basis, KARL, "ding_anlegen", was="unterkunft", titel="Pension Elbblick", ort="O-02", art="pension", quelle="Website",
                    geprueft="2026-10-29", merkmale={"preis": "90 €"})
    assert not f and t.startswith("Eingetragen und gesichert (Karl): Unterkunft U-05")
    assert Schreibweg.anfragen[-1][0] == "/beispielreise/ding_anlegen" and Schreibweg.anfragen[-1][2]["args"]["merkmale"] == {"preis": "90 €"}
    # Option: Wahlstelle muss es geben; Merkmale werden gegen die Art der Wahlstelle geprüft
    Schreibweg.antwort = (422, {"ok": False, "fehler": "Die Wahlstelle V-77 gibt es nicht (varianten zeigt alle); eine neue mit wahlstelle_anlegen."})
    t, f = werkzeug(basis, KARL, "option_anlegen", wahlstelle="V-77", titel="X")
    assert f and "gibt es nicht" in t and N("wahlstelle_anlegen") in t
    Schreibweg.antwort = (200, {"ok": True, "text": "ok"})
    t, f = werkzeug(basis, KARL, "option_anlegen", wahlstelle="V-03", titel="X", merkmale={"preise": "1 €"})
    assert f and "gemeint ist wohl preis" in t
    t, f = werkzeug(basis, KARL, "option_anlegen", wahlstelle="V-03", titel="Pension Elbblick", unterkuenfte=["U-05"])
    assert not f and Schreibweg.anfragen[-1][0] == "/beispielreise/option_anlegen"
    Schreibweg.antwort = (422, {"ok": False, "fehler": "„an“: T-99 gibt es nicht."})
    t, f = werkzeug(basis, KARL, "wahlstelle_anlegen", titel="Anreise", an=["T-99"], optionen=[{"titel": "a"}])
    assert f and t == "Nicht eingetragen: „at“: T-99 gibt es nicht."
    Schreibweg.antwort = (200, {"ok": True, "text": "ok"})
    t, f = werkzeug(basis, KARL, "wahlstelle_anlegen", titel="Anreise", an=["T-01"], optionen=[{"titel": "a", "strecken": ["E-20"]}])
    assert not f
    Schreibweg.antwort = (422, {"ok": False, "fehler": "U-77 gibt es nicht."})
    t, f = werkzeug(basis, KARL, "ding_aendern", ziel="U-77", hinweis="x")
    assert f and t == "Nicht eingetragen: U-77 gibt es nicht."
    Schreibweg.antwort = (200, {"ok": True, "text": "ok"})
    t, f = werkzeug(basis, KARL, "frage_anlegen", text="Offen?", bezug=["U-01"])
    assert not f and Schreibweg.anfragen[-1][0] == "/beispielreise/frage_anlegen"
    # Gast: nur lesen
    t, f = werkzeug(basis, GAST, "ding_anlegen", was="ort", titel="X", quelle="x")
    assert f and "nur lesen" in t
    assert rm.eintraege(ablage / "beispielreise") == []


def test_entscheiden_ueber_den_schreibweg_und_widerspruch(schreibweg):
    import konten
    basis, ablage = schreibweg
    Schreibweg.antwort = (200, {"ok": True, "text": "Entschieden: V-01.b „Plan B“ (V-01 Letzter Tag) ist gewählt (Ida, 29.10.2026, Grund: Bahn). Frage F-01 ist damit geklärt."})
    t, f = werkzeug(basis, ALT_ORGANISATOR, "entscheiden", option="V-01.b", status="gewaehlt", grund="Karl will die Bahn")
    assert not f and t.startswith("Entschieden: V-01.b „Plan B“") and "es gilt ab jetzt" in t
    pfad, geheim, body = Schreibweg.anfragen[-1]
    assert pfad == "/beispielreise/entscheiden" and geheim == konten.dienst_geheimnis()
    assert body == {"person": "ida", "name": "Ida", "rolle": "organisator", "args": {"option": "V-01.b", "status": "gewaehlt", "grund": "Karl will die Bahn"}}
    assert rm.auftraege(ablage / "beispielreise") == []                 # kein Auftrag mehr, direkt geschrieben
    # Formale Fehler lehnt der Konnektor ab, ohne den Schreibweg zu rufen
    n = len(Schreibweg.anfragen)
    t, f = werkzeug(basis, ALT_ORGANISATOR, "entscheiden", option="V-99.a", status="gewaehlt", grund="x")
    assert f and "gibt es nicht" in t and len(Schreibweg.anfragen) == n
    # Widerspruch: V-03.a ist von Ida gewählt; eine zweite Organisatorin will sie verwerfen -> offene Frage und Meldung, nichts geschrieben
    Schreibweg.antwort = (200, {"ok": True, "text": "Offene Frage F-04 angelegt: Widerspruch …"})
    t, f = werkzeug(basis, ALT_ORGANISATOR, "entscheiden", option="V-03.a", status="verworfen", grund="zu teuer")
    assert not f and "Nicht entschieden" not in t                        # dieselbe Person darf ihre Wahl ändern
    assert Schreibweg.anfragen[-1][0] == "/beispielreise/entscheiden"


def test_konnektor_haengt_hinweise_an_den_text(schreibweg):
    """Issue #142, AC-13: Neue Warnungen aus dem Probebau (Feld hinweise) hängt der Konnektor an den Text; sie sind kein
    Fehler, eingetragen ist trotzdem. Ohne hinweise bleibt der Text wie bisher. Beim allgemeinen Eintragen und bei entscheiden."""
    basis, _ = schreibweg
    hinweise = ["plan: Fixpunkt 20.05. (Konzert am Abend (Test)) liegt außerhalb des Plans.", "T-02: Erfundene Lücke im Ablauf (Test)."]
    try:
        Schreibweg.antwort = (200, {"ok": True, "text": "Preis pro Nacht an U-02 Pension Burgblick: 95 €.", "commit": "abc1234"})
        t, f = werkzeug(basis, KARL, "wert_eintragen", ziel="U-02", merkmal="preis", wert="95 €", quelle="Website", geprueft="2026-10-29")
        assert not f and t.startswith("Eingetragen und gesichert (Karl):") and not meldet(t, "konnektor.ausgabe.hinweise_text.1")
        Schreibweg.antwort = (200, {"ok": True, "text": "Preis pro Nacht an U-02 Pension Burgblick: 95 €.", "commit": "abc1234",
                                    "hinweise": hinweise})
        t, f = werkzeug(basis, KARL, "wert_eintragen", ziel="U-02", merkmal="preis", wert="95 €", quelle="Website", geprueft="2026-10-29")
        assert not f and t.startswith("Eingetragen und gesichert (Karl):")
        assert meldet(t, "konnektor.ausgabe.hinweise_text.1") and all(f"- {h}" in t for h in hinweise)
        Schreibweg.antwort = (200, {"ok": True, "text": "Entschieden: V-01.b „Plan B“ ist gewählt (Ida, Grund: Bahn).", "commit": "abc1234",
                                    "hinweise": hinweise})
        t, f = werkzeug(basis, ALT_ORGANISATOR, "entscheiden", option="V-01.b", status="gewaehlt", grund="Karl will die Bahn")
        assert not f and t.startswith("Entschieden: V-01.b") and meldet(t, "konnektor.ausgabe.hinweise_text.1") and all(f"- {h}" in t for h in hinweise)
    finally:
        Schreibweg.antwort = (200, {"ok": True, "text": "ok"})


def test_reise_aendern_verweist_auf_start_ende_setzen(schreibweg, monkeypatch):
    """Issue #142, AC-28 und AC-32: Start und Ende des Plans setzt das Werkzeug start_ende_setzen (nur Organisator:innen, nur mit
    Schreibweg, Aktion einstellung wie reise_aendern); reise_aendern verweist darauf statt auf die Tage."""
    basis, _ = schreibweg
    beschreibung = kn.texte.t("de", kn.REISE_AENDERN["description"][1:])   # die Beschreibung steht im Katalog
    assert "start_ende_setzen" in beschreibung and "in den Tagen" not in beschreibung
    definition = getattr(kn, "START_ENDE_SETZEN", None)
    assert definition is not None and definition["name"] == "start_ende_setzen"
    assert {"start_ort", "start_datum", "ende_ort", "ende_datum", "grund"} <= set(definition["inputSchema"]["properties"])
    assert "grund" in definition["inputSchema"].get("required", [])
    assert "start_ende_setzen" in kn.ONTOLOGIE_WERKZEUGE and kn.ONTOLOGIE_AKTION["start_ende_setzen"] == "einstellung"
    assert "`start_ende_setzen`" in (WURZEL / "docs" / "konnektor.md").read_text(encoding="utf-8")
    t, f = werkzeug(basis, KARL, "start_ende_setzen", start_datum="2027-05-20", grund="x")
    assert f and "nur Organisator:innen" in t and Schreibweg.anfragen == []
    try:
        Schreibweg.antwort = (200, {"ok": True, "text": "Start des Plans: Datum 2027-05-13 → 2027-05-20.", "commit": "abc1234"})
        t, f = werkzeug(basis, ALT_ORGANISATOR, "start_ende_setzen", start_datum="2027-05-20", grund="Zug später (Test)")
        assert not f and t.startswith("Eingetragen und gesichert (Ida): Start des Plans")
        pfad, _, body = Schreibweg.anfragen[-1]
        assert pfad == "/beispielreise/start_ende_setzen" and body["args"] == {"start_datum": "2027-05-20", "grund": "Zug später (Test)"}
    finally:
        Schreibweg.antwort = (200, {"ok": True, "text": "ok"})
    monkeypatch.delenv("KN_SCHREIBDIENST")
    assert "start_ende_setzen" not in {t["name"] for t in rpc(basis, ALT_ORGANISATOR, "tools/list")["tools"]}


def test_tag_aendern_nur_organisatoren_sehen_es(schreibweg):
    basis, _ = schreibweg
    assert "tag_aendern" in {t["name"] for t in rpc(basis, ALT_ORGANISATOR, "tools/list")["tools"]}
    assert "tag_aendern" not in {t["name"] for t in rpc(basis, KARL, "tools/list")["tools"]}
    t, f = werkzeug(basis, KARL, "tag_aendern", ziel="T-03", nacht="V-03")
    assert f and "nur Organisator:innen" in t
    Schreibweg.antwort = (422, {"ok": False, "fehler": "Den Tag T-99 gibt es nicht."})
    t, f = werkzeug(basis, ALT_ORGANISATOR, "tag_aendern", ziel="T-99", nacht="V-03")
    assert f and t == "Nicht eingetragen: Den Tag T-99 gibt es nicht."
    Schreibweg.antwort = (200, {"ok": True, "text": "T-03: nacht „U-04“ → „V-03“."})
    t, f = werkzeug(basis, ALT_ORGANISATOR, "tag_aendern", ziel="T-03", nacht="V-03", grund="Wahl")
    assert not f and Schreibweg.anfragen[-1][2]["args"] == {"ziel": "T-03", "nacht": "V-03", "grund": "Wahl"}
    assert N("tag_aendern") in rpc(basis, ALT_ORGANISATOR, "initialize")["instructions"]


def test_rueckmeldung_erledigen_und_wissen_und_fragen(schreibweg):
    basis, ablage = schreibweg
    # Rückmeldung von Karl, Ida erledigt sie mit Kommentar; der Status geht über den Rückmeldedienst
    t, f = werkzeug(basis, KARL, "rueckmeldung_geben", art="Korrektur", ziel="U-02", text="Frühstück kostet extra")
    rid = rm.eintraege(ablage / "beispielreise")[0]["id"]
    assert "rueckmeldung_erledigen" not in {t["name"] for t in rpc(basis, KARL, "tools/list")["tools"]}
    t, f = werkzeug(basis, KARL, "rueckmeldung_erledigen", id=rid, status="uebernommen", kommentar="x")
    assert f and "nur Organisator:innen" in t
    t, f = werkzeug(basis, ALT_ORGANISATOR, "rueckmeldung_erledigen", id=rid, status="uebernommen", kommentar="Frühstück steht jetzt als „gegen Aufpreis“")
    assert not f and f"{rid} ist jetzt uebernommen" in t
    st = rm.status_lesen(ablage / "beispielreise")[rid]
    assert st["status"] == "uebernommen" and st["kommentar"].startswith("Frühstück steht") and st["wer"] == "Ida"
    t, f = werkzeug(basis, ALT_ORGANISATOR, "rueckmeldung_erledigen", id="R-20260101-000000-abcd", status="verworfen", kommentar="x")
    assert f and "gibt es nicht" in t
    t, f = werkzeug(basis, ALT_ORGANISATOR, "rueckmeldung_erledigen", id=rid, status="erledigt", kommentar="x")
    assert f and "Status muss" in t
    # Wissen und Fragen über den Schreibweg; unbekannte Abschnitte und Fragen prüft der Schreibweg mit dem Repo (Issue #135)
    Schreibweg.antwort = (200, {"ok": True, "text": "Neuer Abschnitt W-09 „Kirnitzschtalbahn“ in inhalt/wissen.md (Gruppe wissen). Herkunft: Wikipedia."})
    t, f = werkzeug(basis, KARL, "wissen_schreiben", titel="Kirnitzschtalbahn", text="Seit 1898.", quelle="Wikipedia")
    assert not f and Schreibweg.anfragen[-1][0] == "/beispielreise/wissen_schreiben"
    Schreibweg.antwort = (422, {"ok": False, "fehler": "Den Abschnitt „W-99“ gibt es nicht (W-ID aus ueberblick oder zeige)."})
    t, f = werkzeug(basis, KARL, "wissen_schreiben", abschnitt="W-99", text="x", quelle="y")
    assert f and "gibt es nicht" in t
    assert "frage_schliessen" not in {t["name"] for t in rpc(basis, KARL, "tools/list")["tools"]}
    Schreibweg.antwort = (422, {"ok": False, "fehler": "Die Frage F-77 gibt es nicht (offene_fragen zeigt alle)."})
    t, f = werkzeug(basis, ALT_ORGANISATOR, "frage_schliessen", frage="F-77", ergebnis="x")
    assert f and "gibt es nicht" in t
    Schreibweg.antwort = (200, {"ok": True, "text": "Frage F-03 ist geklärt (Ida, 29.10.2026): Fahrplan steht."})
    t, f = werkzeug(basis, ALT_ORGANISATOR, "frage_schliessen", frage="F-03", ergebnis="Fahrplan steht")
    assert not f and Schreibweg.anfragen[-1][2]["args"] == {"frage": "F-03", "ergebnis": "Fahrplan steht"}


def test_einladen_schreibt_person_direkt(schreibweg, monkeypatch, tmp_path):
    basis, ablage = schreibweg
    monkeypatch.setenv("FR_MAIL_DATEI", str(tmp_path / "mails.jsonl"))      # die Einladung geht per Mail (#421)
    Schreibweg.antwort = (200, {"ok": True, "text": "Anna steht jetzt in der Reise (anna, Rolle mitwirkend, reist mit)."})
    t, f = werkzeug(basis, ALT_ORGANISATOR, "person_einladen", vorname="Anna", rolle="mitwirkend", email="anna@beispiel.invalid")
    assert not f and "Anna" in t and "anna@beispiel.invalid" in t
    pfad, _, body = Schreibweg.anfragen[-1]
    assert pfad == "/beispielreise/person_schreiben" and body["person"] == "ida"
    assert body["args"]["schluessel"] == "anna" and body["args"]["vorname"] == "Anna" and body["args"]["rolle"] == "mitwirkend" and body["args"]["reist"] is True
    assert rm.auftraege(ablage / "beispielreise") == []          # kein Auftrag mehr
    assert "anna" in rm.einladungen_lesen(ablage / "beispielreise")   # Zugang gilt sofort, bis reise.yaml veröffentlicht ist


def test_status_einstellungen_und_kein_auftrag_mehr(schreibweg):
    basis, ablage = schreibweg
    namen = {t["name"] for t in rpc(basis, ALT_ORGANISATOR, "tools/list")["tools"]}
    assert {"reise_status_setzen", "einstellung_setzen"} <= namen and "auftrag_geben" not in namen
    assert not {"reise_status_setzen", "einstellung_setzen"} & {t["name"] for t in rpc(basis, KARL, "tools/list")["tools"]}
    t, f = werkzeug(basis, ALT_ORGANISATOR, "auftrag_geben", auftrag="x")
    assert f and "Unbekanntes Werkzeug" in t
    Schreibweg.antwort = (200, {"ok": True, "text": "Die Reise hat jetzt den Status fest (vorher planung; Ida, 29.10.2026, Grund: steht)."})
    t, f = werkzeug(basis, ALT_ORGANISATOR, "reise_status_setzen", status="fest", grund="steht")
    assert not f and Schreibweg.anfragen[-1][2]["args"] == {"status": "fest", "grund": "steht"}
    t, f = werkzeug(basis, KARL, "reise_status_setzen", status="fest", grund="steht")
    assert f and "nur Organisator:innen" in t
    t, f = werkzeug(basis, ALT_ORGANISATOR, "einstellung_setzen", regeln={"einladen": "mitwirkend"})
    assert not f and Schreibweg.anfragen[-1][0] == "/beispielreise/einstellung_setzen"
    assert N("reise_status_setzen, einstellung_setzen") in rpc(basis, ALT_ORGANISATOR, "initialize")["instructions"]
    assert "auftrag_geben" not in rpc(basis, ALT_ORGANISATOR, "initialize")["instructions"]
    assert rm.auftraege(ablage / "beispielreise") == []


def test_neue_reise_ueber_den_schreibweg(schreibweg, tmp_path, monkeypatch):
    basis, ablage = schreibweg
    ausstehend = tmp_path / "ausstehend.jsonl"
    monkeypatch.setenv("KN_AUSSTEHEND", str(ausstehend))
    Schreibweg.antwort = (200, {"ok": True, "text": "Die Reise „Skiwoche“ ist angelegt (Ordner skiwoche-2027, Status Idee)."})
    t, f = kn.reise_anlegen(IDA_KONTO, {"titel": "Skiwoche", "von": "2027-02-06", "bis": "2027-02-13", "sprache": "de",
                                        "personen": [{"vorname": "Karl", "rolle": "mitwirkend"}]})
    assert not f, t
    assert "ist angelegt" in t and "sobald die seite online ist" in t.lower()
    pfad, _, body = Schreibweg.anfragen[-1]
    assert pfad == "/skiwoche-2027/reise_anlegen" and body["args"]["auftrag"]["daten"]["neue_reise"]["titel"] == "Skiwoche"
    assert body["args"]["auftrag"]["daten"]["neue_reise"]["sprache"] == "de"   # ohne Angabe die Sprache der Person (hier der Rückfall der Tests), nicht still die des Bestands
    zeile = json.loads(ausstehend.read_text().strip())
    assert zeile["ordner"] == "skiwoche-2027" and zeile["name"] == "Ida" and zeile["person"] == "ida" and zeile["aid"].startswith("A-")
    o = rm.ordner_neu()
    assert rm.status_lesen(o)[zeile["aid"]]["status"] == "uebernommen"
    # lehnt der Schreibweg ab, bleibt die Anfrage als Rückfrage stehen
    Schreibweg.antwort = (422, {"ok": False, "fehler": "Den Ordner reisen/skiwoche-2027 gibt es schon."})
    t, f = kn.reise_anlegen(IDA_KONTO, {"titel": "Skiwoche zwei", "von": "2027-02-06", "bis": "2027-02-13", "personen": []})
    assert f and "Nicht angelegt" in t
    assert any(v["status"] == "rueckfrage" for v in rm.status_lesen(o).values())


def test_buchung_werkzeuge_und_anzeige(schreibweg):
    """#76: buchung_anlegen und buchung_aendern gehen über den Schreibweg (ab Mitwirkende:r); zeige B-… und ueberblick
    zeigen Buchungen; Belege aus der Ablage sieht nur, wer darf."""
    import belege as bl
    basis, ablage = schreibweg
    for token, da in ((ALT_ORGANISATOR, True), (KARL, True), (GAST, False)):
        namen = {t["name"] for t in rpc(basis, token, "tools/list")["tools"]}
        assert ({"buchung_anlegen", "buchung_aendern"} <= namen) is da, token
    assert N("buchung_anlegen") in rpc(basis, ALT_ORGANISATOR, "initialize")["instructions"]
    Schreibweg.antwort = (200, {"ok": True, "text": "Buchung B-03 angelegt (gebucht) für U-02 Pension Burgblick, Nr. P-7."})
    t, f = werkzeug(basis, KARL, "buchung_anlegen", fuer=["U-02"], nummer="P-7", quelle="Mail vom 29.10.", frist="2027-01-15", frist_was="Anzahlung")
    assert not f and t.startswith("Eingetragen und gesichert (Karl): Buchung B-03 angelegt") and "Kein Beleg mitgegeben" in t
    pfad, _, body = Schreibweg.anfragen[-1]
    assert pfad == "/beispielreise/buchung_anlegen" and body["args"]["fuer"] == ["U-02"] and body["args"]["frist_was"] == "Anzahlung"
    # Unbekannte IDs prüft der Schreibweg (Issue #135: eine gerade angelegte Strecke ist sofort buchbar, auch vor dem Veröffentlichen)
    Schreibweg.antwort = (422, {"ok": False, "fehler": "„fuer“: U-77 gibt es in dieser Reise nicht (Unterkunft U-…, Aufenthalt A-… oder Strecke E-…)."})
    t, f = werkzeug(basis, KARL, "buchung_anlegen", fuer="U-77", quelle="x")
    assert f and t.startswith("Nicht eingetragen: „for“: U-77 gibt es in dieser Reise nicht")
    Schreibweg.antwort = (422, {"ok": False, "fehler": "Die Buchung B-09 gibt es nicht."})
    t, f = werkzeug(basis, KARL, "buchung_aendern", ziel="B-09", status="storniert")
    assert f and t == "Nicht eingetragen: Die Buchung B-09 gibt es nicht."
    # Reisende, Preise je Ding und der Ab-Termin gehen mit (Issue #135)
    Schreibweg.antwort = (200, {"ok": True, "text": "Buchung B-04 angelegt (gebucht) für E-20, E-21, Nr. EW-7."})
    t, f = werkzeug(basis, KARL, "buchung_anlegen", fuer=["E-20", "E-21"], nummer="EW-7", quelle="Mail", personen={"Ida": "Sitz 12A", "Karl": ""},
                    preise={"E-20": "120 €", "E-21": "110 €"}, ab="2027-05-13", ab_was="Online-Check-in")
    assert not f and Schreibweg.anfragen[-1][2]["args"]["personen"] == {"Ida": "Sitz 12A", "Karl": ""} \
        and Schreibweg.anfragen[-1][2]["args"]["preise"]["E-21"] == "110 €" and Schreibweg.anfragen[-1][2]["args"]["ab_was"] == "Online-Check-in"
    Schreibweg.antwort = (200, {"ok": True, "text": "Buchung B-01 (U-01 Hotel am Elbufer): Status „gebucht“ → „storniert“."})
    t, f = werkzeug(basis, ALT_ORGANISATOR, "buchung_aendern", ziel="b-01", status="storniert", grund="Plan geändert")
    assert not f and Schreibweg.anfragen[-1][2]["args"] == {"ziel": "b-01", "status": "storniert", "grund": "Plan geändert"}
    # Anzeige: Beispielreise hat B-01 (Hotel, Ida) und B-02 (Bahn, Karl)
    t, f = werkzeug(basis, KARL, "zeige", id="B-01")
    assert not f and "Buchung gebucht: Hotel am Elbufer" in t and "Nummer: HE-2027-0415" in t and "Storno: kostenlos bis 3 Tage vorher, danach eine Nacht (bis 11.5.2027)" in t
    assert "Quelle: Buchungsbestätigung per Mail" in t and "Belege: keine" in t and "29.10.2026 Ida: angelegt" in t
    t, f = werkzeug(basis, KARL, "zeige", id="U-01")
    assert not f and "Buchung: gebucht (B-01, zeige B-01)" in t
    t, f = werkzeug(basis, KARL, "zeige", id="E-20")   # auch an einer Strecke eine Zeile mit Verweis auf die Buchung (ADR-0003)
    assert not f and "Buchung: gebucht (B-02, zeige B-02)" in t
    t, f = werkzeug(basis, KARL, "zeige", id="B-09")
    assert f and "noch nicht neu gebaut" in t
    t, f = werkzeug(basis, KARL, "ueberblick")
    assert not f and "## Buchungen: 2 gebucht, 1 storniert (zeige B-…)" in t and "B-02" in t and "Frist 13.5.2027 (Ticket in die App laden)" in t \
        and "kostenlos stornierbar bis 11.5.2027" in t
    # Belege: Karl sieht seinen, Ida (Organisatorin) alle, ein Gast keinen (die Ablage ist die des Rückmeldedienstes)
    o = ablage / "beispielreise"
    b1, _ = bl.ablegen(o, "B-01", "Karl", "Bestätigung.pdf", b"%PDF-1.4 x")
    b2, _ = bl.ablegen(o, "B-02", "Ida", "Ticket.png", b"\x89PNG\r\n\x1a\n" + b"x" * 8)
    t, _ = werkzeug(basis, KARL, "zeige", id="B-01")
    assert "Belege: Bestätigung.pdf (Karl, " in t
    t, _ = werkzeug(basis, KARL, "zeige", id="B-02")
    assert "Belege: keine" in t
    t, _ = werkzeug(basis, ALT_ORGANISATOR, "zeige", id="B-02")
    assert "Belege: Ticket.png (Ida, " in t
    bl.aendern(o, b2["id"], {"sichtbar": "alle"}, "Ida", "organisator")
    t, _ = werkzeug(basis, KARL, "zeige", id="B-02")
    assert "Ticket.png (Ida, " in t and "für alle sichtbar" in t


def test_beleg_anlegen_ueber_den_konnektor(schreibweg, seiten, monkeypatch):
    """Issue #135: Einen Beleg hängt die Person auch im Gespräch an, als Abschrift (Text) oder als Datei (Base64); der Konnektor
    schickt ihn an den Rückmeldedienst, den einzigen Schreiber der Ablage. Sichtbar für sie und Organisator:innen; ein Gast hat das
    Werkzeug nicht."""
    import base64
    import belege as bl
    basis, ablage = schreibweg
    monkeypatch.setenv("RM_SEITEN", str(seiten))
    for token, da in ((ALT_ORGANISATOR, True), (KARL, True), (GAST, False)):
        assert ("beleg_anlegen" in {t["name"] for t in rpc(basis, token, "tools/list")["tools"]}) is da, token
    t, f = werkzeug(basis, KARL, "beleg_anlegen", buchung="U-01", text="x")
    assert f and "B-…" in t
    t, f = werkzeug(basis, KARL, "beleg_anlegen", buchung="B-02", dateiname="Bestätigung Bahn")
    assert f and "text (Abschrift) oder daten_base64" in t
    t, f = werkzeug(basis, KARL, "beleg_anlegen", buchung="B-02", dateiname="Bestätigung Bahn", text="Buchung DB-ABC123, 19,90 €, Dresden → Bad Schandau")
    assert not f and t.startswith("Beleg D-01 „Bestätigung Bahn.txt“ an B-02 abgelegt") and "sichtbar für Karl und die Organisator:innen" in t
    o = ablage / "beispielreise"
    assert (o / "belege" / "D-01.txt").read_text(encoding="utf-8") == "Buchung DB-ABC123, 19,90 €, Dresden → Bad Schandau\n"
    b = bl.liste(o, "Karl", "mitwirkend")
    assert len(b) == 1 and b[0]["buchung"] == "B-02" and b[0]["typ"] == "text/plain; charset=utf-8" and b[0]["wer"] == "Karl"
    t, _ = werkzeug(basis, KARL, "zeige", id="B-02")
    assert "Belege: Bestätigung Bahn.txt (Karl, " in t
    t, f = werkzeug(basis, KARL, "beleg_anlegen", buchung="B-02", dateiname="Ticket.png", daten_base64=base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"x" * 8).decode())
    assert not f and "Beleg D-02 „Ticket.png“ an B-02 abgelegt" in t and (o / "belege" / "D-02.png").exists()
    t, f = werkzeug(basis, KARL, "beleg_anlegen", buchung="B-02", dateiname="Ticket.png", daten_base64="%%%")
    assert f and meldet(t, "konnektor.beleg_daten.1")
    t, f = werkzeug(basis, KARL, "beleg_anlegen", buchung="B-02", dateiname="x.gif", daten_base64=base64.b64encode(b"GIF89a....").decode())
    assert f and t.startswith("Nicht abgelegt:")
    t, f = werkzeug(basis, KARL, "beleg_anlegen", buchung="B-99", text="x")
    assert f and "B-99 gibt es nicht" in t
    t, f = werkzeug(basis, GAST, "beleg_anlegen", buchung="B-02", text="x")
    assert f
    # Ida (Organisatorin) sieht Karls Beleg, der Gast keinen
    t, _ = werkzeug(basis, ALT_ORGANISATOR, "zeige", id="B-02")
    assert "Bestätigung Bahn.txt (Karl, " in t
    t, _ = werkzeug(basis, GAST, "zeige", id="B-02")
    assert "Belege: keine" in t


def test_buchung_zeigt_zahlstand_und_merkmale(schreibweg):
    """#166: zeige B-… nennt den Zahlstand in Worten mit seinen Einzelheiten und die Merkmale der Buchung; merkmale zeigt bei
    einer Art auch die Merkmale ihrer Buchungen; zahlung und merkmale gehen an den Schreibweg, englische Aliase stehen im Schema."""
    basis, _ = schreibweg
    t, f = werkzeug(basis, KARL, "zeige", id="B-01")
    assert not f and "Zahlung: angezahlt · Anzahlung 30 € per Überweisung am 29.10.2026 (Beispielwert)" in t
    assert "Zeitraum: 13.5.2027 bis 14.5.2027" in t and "Check-in ab 15:00" in t and "Vor Ort zu zahlen: 90 € Rest" in t, t
    t, f = werkzeug(basis, KARL, "zeige", id="B-02")
    assert not f and "Zahlung: bezahlt · Kreditkarte" in t and "Ticketart: Sparpreis" in t
    t, f = werkzeug(basis, ALT_ORGANISATOR, "merkmale", art="bahn")
    assert not f and meldet(t, "konnektor.ausgabe.merkmale.5") and "- ticketart – Ticketart: auswahl (Sparpreis | Flexpreis | Verbundticket)" in t
    assert "Buchungen dieser Art" not in werkzeug(basis, ALT_ORGANISATOR, "merkmale", art="hotel")[0]
    schema = next(x for x in rpc(basis, KARL, "tools/list")["tools"] if x["name"] == "buchung_anlegen")["inputSchema"]["properties"]
    assert {"open", "paid", "on_site", "included"} <= set(schema["payment"]["enum"]) and "attributes" in schema
    md = next(x for x in rpc(basis, ALT_ORGANISATOR, "tools/list")["tools"] if x["name"] == "merkmal_definieren")["inputSchema"]["properties"]
    assert md["for"]["enum"] == ["thing", "booking"]
    Schreibweg.antwort = (200, {"ok": True, "text": "Buchung B-02 (E-20 …): Zahlung „bezahlt“ → „erstattet“."})
    t, f = werkzeug(basis, KARL, "buchung_aendern", ziel="B-02", zahlung="refunded", merkmale={"wagen": "Wagen 5"})
    assert not f and Schreibweg.anfragen[-1][2]["args"]["zahlung"] == "refunded" and Schreibweg.anfragen[-1][2]["args"]["merkmale"] == {"wagen": "Wagen 5"}


def test_beleg_in_einem_schritt_mit_der_buchung(schreibweg, seiten, monkeypatch):
    """Issue #135: Der Beleg geht beim Anlegen der Buchung gleich mit (beleg_text oder beleg_base64), ohne auf das Veröffentlichen zu
    warten; nachträglich fragt beleg_anlegen den Schreibweg, ob es die Buchung im Repo schon gibt."""
    import belege as bl
    basis, ablage = schreibweg
    monkeypatch.setenv("RM_SEITEN", str(seiten))
    o = ablage / "beispielreise"
    # Beleg fehlerhaft: die Buchung wird gar nicht erst angelegt
    t, f = werkzeug(basis, KARL, "buchung_anlegen", fuer=["E-21"], quelle="Mail", beleg_base64="%%%", beleg_dateiname="x.pdf")
    assert f and meldet(t, "konnektor.beleg_daten.1") and Schreibweg.anfragen == []
    Schreibweg.antwort = (200, {"ok": True, "text": "Buchung B-04 angelegt (gebucht) für E-21 S-Bahn Bad Schandau → Dresden, Nr. DB-7.", "id": "B-04"})
    t, f = werkzeug(basis, KARL, "buchung_anlegen", fuer=["E-21"], nummer="DB-7", quelle="Mail vom 30.10.2026",
                    beleg_text="Buchung DB-7, 19,90 €", beleg_dateiname="Bestätigung Bahn")
    assert not f and "Buchung B-04 angelegt" in t and "Beleg D-01 „Bestätigung Bahn.txt“ an B-04 abgelegt" in t and "Kein Beleg" not in t
    assert "beleg_text" not in Schreibweg.anfragen[-1][2]["args"] and Schreibweg.anfragen[-1][2]["args"]["nummer"] == "DB-7"
    b = bl.liste(o, "Karl", "mitwirkend")
    assert len(b) == 1 and b[0]["buchung"] == "B-04" and (o / "belege" / "D-01.txt").read_text(encoding="utf-8") == "Buchung DB-7, 19,90 €\n"
    # Nennt der Schreibweg keine ID, bleibt die Buchung, der Beleg nicht (Hinweis auf beleg_anlegen)
    Schreibweg.antwort = (200, {"ok": True, "text": "Buchung B-05 angelegt (gebucht) für E-21."})
    t, f = werkzeug(basis, KARL, "buchung_anlegen", fuer=["E-21"], quelle="Mail", beleg_text="x")
    assert not f and "nicht abgelegt" in t and N("beleg_anlegen") in t
    # beleg_* nur bei buchung_anlegen
    t, f = werkzeug(basis, KARL, "buchung_aendern", ziel="B-04", notiz="x", beleg_text="y")
    assert f and N("nur bei buchung_anlegen") in t
    # Nachträglich, vor dem Veröffentlichen: der Schreibweg kennt B-04 im Repo, B-99 nicht
    t, f = werkzeug(basis, KARL, "beleg_anlegen", buchung="B-04", text="Nachtrag")
    assert f and "Die Buchung B-04 gibt es nicht" in t
    Schreibweg.im_repo = {"B-04"}
    t, f = werkzeug(basis, KARL, "beleg_anlegen", buchung="B-04", text="Nachtrag", dateiname="Mail")
    assert not f and "Beleg D-02 „Mail.txt“ an B-04 abgelegt" in t
    t, f = werkzeug(basis, KARL, "beleg_anlegen", buchung="B-99", text="x")
    assert f and "B-99 gibt es nicht" in t
    # Ohne Schreibweg bleibt die veröffentlichte Buchung erreichbar, die unveröffentlichte nicht
    monkeypatch.delenv("KN_SCHREIBDIENST", raising=False)
    t, f = werkzeug(basis, KARL, "beleg_anlegen", buchung="B-04", text="x")
    assert f and "nicht eingerichtet" in t
    t, f = werkzeug(basis, KARL, "beleg_anlegen", buchung="B-02", text="veröffentlicht")
    assert not f and "an B-02 abgelegt" in t


# --- Löschwunsch (#145): Frieda löscht nie; die Texte weisen den passenden Weg und den Rückholweg ---

LOESCH_ZUGAENGE = (("gast", {"reise": "beispielreise", "person": "kim"}),
                   ("mitwirkend", {"reise": "beispielreise", "person": "jo"}),
                   ("organisator", {"reise": "beispielreise", "person": "max"}))
# erfundene Personen, deren Namen nicht in der Beispielreise vorkommen (die Prüfung auf Reisespezifisches sucht Ida und Karl)
LOESCH_DATEN = {"reise": {"personen": [{"schluessel": "kim", "name": "Kim", "rolle": "gast"},
                                       {"schluessel": "jo", "name": "Jo", "rolle": "mitwirkend"},
                                       {"schluessel": "max", "name": "Max", "rolle": "organisator"}]}}


def loesch_absatz(text):
    """Der Absatz (Zeile) der Anleitung, der den Löschwunsch behandelt; leer, wenn es ihn nicht gibt."""
    return next((z for z in text.split("\n") if "Löschwunsch" in z), "")


def aufgabe_werkzeug():
    return next(w for w in kn.WERKZEUGE if w["name"] == "aufgabe_aendern")


@pytest.mark.parametrize("rolle,zugang", LOESCH_ZUGAENGE)
def test_anleitung_nennt_den_loeschwunsch_fuer_jede_rolle(rolle, zugang):
    """Kriterium 1: Frieda löscht nie; Weg je Grundform; erst bestätigen lassen; ein Satz danach; Rückmeldung, wo es keinen Weg gibt."""
    z = loesch_absatz(kn.anleitung(zugang, LOESCH_DATEN))
    assert z, rolle
    for teil in ("löscht nie", "storniert", "verworfen", "entfaellt", "bestätigen", "nicht gelöscht", "rueckmeldung_geben"):
        assert teil in z, (rolle, teil)


def test_werkzeugbeschreibungen_nennen_loeschwunsch_und_rueckholweg():
    """Kriterium 2: je Werkzeug ein Satz mit dem eigenen Weg und dem Rückholweg."""
    erwartet = ((kn.BUCHUNG_AENDERN, ("storniert", "gebucht")),
                (kn.ENTSCHEIDEN, ("verworfen", "gewaehlt")),
                (aufgabe_werkzeug(), ("entfaellt", "offen")),
                (kn.FRAGE_SCHLIESSEN, ("entfaellt", "neue Frage")))
    for w, teile in erwartet:
        satz = next((s for s in kn.lokalisiert([w], "de")[0]["description"].split(". ") if "Löschwunsch" in s), "")
        assert satz, w["name"]
        for t in teile:
            assert t in satz, (w["name"], t)


def test_neue_loeschtexte_nennen_nichts_reisespezifisches():
    """Kriterium 8: keine Pfade, Adressen oder Namen aus Reisen in den neuen Texten."""
    texte = [loesch_absatz(kn.anleitung(z, LOESCH_DATEN)) for _, z in LOESCH_ZUGAENGE]
    for w in (kn.BUCHUNG_AENDERN, kn.ENTSCHEIDEN, kn.FRAGE_SCHLIESSEN, aufgabe_werkzeug()):
        texte += [s for s in kn.lokalisiert([w], "de")[0]["description"].split(". ") if "Löschwunsch" in s]
    assert len(texte) == 7 and all(texte)
    for t in texte:
        for verboten in ("/home", "/var", "http", "@", "Ida", "Karl", "Burgblick", "Elbufer"):
            assert verboten not in t, (verboten, t)


def test_aufgabe_entfaellt_nennt_den_rueckholweg(dienst):
    """Kriterium 6: nach entfaellt steht „wieder offen“ im Antworttext; bei erledigt nicht."""
    basis, _ = dienst
    t, f = werkzeug(basis, ALT_ORGANISATOR, "aufgabe_anlegen", titel="Bus prüfen")
    assert not f and "AG-01" in t
    t, f = werkzeug(basis, ALT_ORGANISATOR, "aufgabe_aendern", id="AG-01", status="erledigt")
    assert not f and t.startswith("Gespeichert (gilt sofort):") and "Nicht gelöscht" not in t
    t, f = werkzeug(basis, ALT_ORGANISATOR, "aufgabe_aendern", id="AG-01", status="entfaellt")
    assert not f and t.startswith("Gespeichert (gilt sofort):")      # bisheriger Satz bleibt vorn (Kriterium 7)
    assert "Nicht gelöscht" in t and "wieder offen" in t and meldet(t, "konnektor.werkzeug.7")


# ---------- Englische Namen der Schnittstelle mit deutschen Aliasen (ADR-0006, M8b) ----------

def test_tools_list_zeigt_englische_namen_und_parameter(schreibweg):
    basis, _ = schreibweg
    liste = rpc(basis, ALT_ORGANISATOR, "tools/list")
    aussen = {w["name_aussen"]: w for w in liste["tools"]}
    assert {"overview", "item_update", "decide", "item_create", "question_create"} <= set(aussen)
    assert not {"ueberblick", "wert_eintragen", "entscheiden", "ding_anlegen", "value_set", "location_set", "track_attach"} & set(aussen)
    eig = aussen["item_update"]["inputSchema"]
    assert {"target", "title", "kind", "parent", "hint", "source", "attributes", "checked", "reason"} <= set(eig["properties"]) and "quelle" not in eig["properties"]
    assert set(eig["required"]) == {"target"}
    # Beschreibungen nennen die Namen, die der Client sieht
    assert "attributes" in aussen["item_update"]["description"] and "merkmale" not in aussen["item_update"]["description"]
    # item_create ist auf die Form geschrumpft (ADR-0007, Schritt c): höchstens 8 Parameter, Sonderfelder stehen in attributes
    erstellen = aussen["item_create"]["inputSchema"]["properties"]
    assert set(erstellen) == {"what", "kind", "parent", "title", "source", "attributes", "hint", "checked"} and len(erstellen) <= 8
    assert not {"from_place", "to_place", "departure", "arrival", "place", "coordinates", "address"} & set(erstellen)


def test_aufruf_englisch_deutsch_und_gemischt_liefert_dasselbe(schreibweg):
    basis, _ = schreibweg
    Schreibweg.antwort = (200, {"ok": True, "text": "Preis an U-02: 95 €."})
    varianten = (("value_set", dict(target="U-02", attribute="preis", value="95 €", source="Website", checked="2026-10-29")),   # Alias von item_update
                 ("wert_eintragen", dict(ziel="U-02", merkmal="preis", wert="95 €", quelle="Website", geprueft="2026-10-29")),
                 ("value_set", dict(ziel="U-02", attribute="preis", wert="95 €", source="Website", geprueft="2026-10-29")))
    ergebnisse = []
    for name, args in varianten:
        t, f = werkzeug(basis, KARL, name, **args)
        pfad, _, body = Schreibweg.anfragen[-1]
        ergebnisse.append((t, f, pfad, body["args"]))
    assert ergebnisse[0] == ergebnisse[1] == ergebnisse[2] and not ergebnisse[0][1]
    assert ergebnisse[0][2] == "/beispielreise/ding_aendern"      # unter dem Rand bleibt alles deutsch; der Alias kommt als item_update an
    # bei Doppelung gewinnt der englische Name
    werkzeug(basis, KARL, "value_set", ziel="U-01", target="U-02", attribute="preis", wert="1 €", source="x")
    assert Schreibweg.anfragen[-1][2]["args"]["ziel"] == "U-02"


def test_enum_alias_wird_auf_den_datenwert_abgebildet(schreibweg):
    basis, _ = schreibweg
    Schreibweg.antwort = (200, {"ok": True, "text": "ok"})
    werkzeug(basis, ALT_ORGANISATOR, "decide", option="V-01.b", status="chosen", reason="passt")
    body = Schreibweg.anfragen[-1][2]["args"]
    assert Schreibweg.anfragen[-1][0] == "/beispielreise/entscheiden" and body["status"] == "gewaehlt" and body["grund"] == "passt"
    werkzeug(basis, ALT_ORGANISATOR, "entscheiden", option="V-01.b", status="verworfen", grund="x")      # deutsch bleibt gültig
    assert Schreibweg.anfragen[-1][2]["args"]["status"] == "verworfen"


def test_keine_namenskollision_der_schnittstelle():
    import schnittstelle as s
    assert len(set(s.NAMEN)) == len(s.NAMEN) and len(set(s.NAMEN.values())) == len(s.NAMEN)
    # ein englischer Parametername darf nie ein anderer interner Name sein (sonst wäre der Alias mehrdeutig)
    intern = set(s.PARAMETER)
    for werkzeug_intern in [None, *s.PARAMETER_JE_WERKZEUG]:
        tab = s.parameter_zu_englisch(werkzeug_intern)
        for i, e in tab.items():
            assert e == i or e not in intern or tab.get(e) == e, (werkzeug_intern, i, e)
        assert len(set(tab.values())) == len(tab), werkzeug_intern    # kein englischer Name doppelt


def test_jedes_werkzeug_hat_einen_englischen_namen():
    """Jedes Werkzeug, das der Konnektor definiert, heißt nach außen englisch (ADR-0006, Punkt 4)."""
    import schnittstelle as s
    namen = {w["name"] for w in vars(kn).values() if isinstance(w, dict) and "inputSchema" in w and isinstance(w.get("name"), str)}
    assert len(namen) > 40
    assert sorted(n for n in namen if n not in s.INTERN_ZU_ENGLISCH) == []


# ---------- Sprache der Reise im Konnektor (ADR-0006, M10) ----------

@pytest.fixture(scope="module")
def seiten_englisch(tmp_path_factory):
    """Die Beispielreise mit sprache: en (Inhalt bleibt deutsch, die Hülle ist englisch)."""
    import shutil
    quelle = tmp_path_factory.mktemp("quelle_en") / "beispielreise"
    shutil.copytree(BEISPIEL, quelle)
    y = quelle / "reise.yaml"
    y.write_text(y.read_text(encoding="utf-8").replace("sprache: de", "sprache: en"), encoding="utf-8")
    s = tmp_path_factory.mktemp("seiten_en")
    bauen.bauen(quelle, s / "beispielreise")
    return s


def test_englische_reise_antwortet_englisch(dienst, seiten_englisch, monkeypatch):
    basis, _ = dienst
    monkeypatch.setenv("KN_SEITEN", str(seiten_englisch))
    anleitung = rpc(basis, ALT_ORGANISATOR, "initialize")["instructions"]
    assert anleitung.startswith("Task: You are helping with the trip") and "Reply in the person's language" in anleitung
    beschr = {w["name_aussen"]: w["description"] for w in rpc(basis, ALT_ORGANISATOR, "tools/list")["tools"]}
    assert beschr["overview"].startswith("Overview of the trip")
    antworten = {}
    for name, args in (("ueberblick", {}), ("zeige", {"id": "E-01"}), ("offene_fragen", {}), ("varianten", {}), ("rueckmeldungen", {}),
                       ("aufgaben", {}), ("suche", {"begriff": "Dresden"})):
        t, f = werkzeug(basis, ALT_ORGANISATOR, name, **args)
        assert not f, (name, t)
        antworten[name] = t
    u = antworten["ueberblick"]
    assert "## Bookings: 2 booked, 1 cancelled" in u and "## Content (look up with show)" in u
    assert "Deadline 13/5/2027" in u and "free cancellation until 11/5/2027" in u
    assert "Fri 14/5/2027" in u and "Fr." not in u and "Frist" not in u and "Buchungen" not in u


def test_ontologie_text_im_rueckfall_englisch(monkeypatch):
    """Die Rückmeldung zu einer Art oder Kategorie liegt in der Ablage in der Sprache des Bestands: Feldnamen, Symbole und Farben
    sind im englischen Rückfall englisch (kein deutsches Wort für eine Person ohne Deutsch)."""
    monkeypatch.setattr(kn.texte, "VORGABE_REISE", "en")
    t = kn.ontologie_text("kategorie_definieren", {"kategorie": "aussicht", "bezeichnung": "Viewpoint", "farbe": "blau", "symbol": "bahn", "stufe": "pflicht"})
    assert "colour: blue" in t and "symbol: train" in t and "label: Viewpoint" in t and "level: needed (required)" in t, t
    assert "farbe" not in t and "bezeichnung" not in t and "blau" not in t


def test_symbol_lesen_und_setzen(schreibweg):
    """icon_set (Issue #252): ohne Bild das aktuelle Symbol als SVG-Text und Vorschau, mit Bild über den Schreibweg; nur Organisator:innen."""
    import base64
    basis, _ = schreibweg
    r = rpc(basis, ALT_ORGANISATOR, "tools/call", {"name": "icon_set", "arguments": {}})
    assert not r["isError"] and len(r["content"]) == 2
    text, bild = r["content"][0]["text"], r["content"][1]
    assert meldet(text, "konnektor.symbol.svg") and "<svg" in text and "Sandsteinfelsen" in text   # Symbol der Beispielreise
    assert bild["type"] == "image" and bild["mimeType"] == "image/png" and base64.b64decode(bild["data"]).startswith(b"\x89PNG")
    assert Schreibweg.anfragen == []
    for args in ({}, {"svg": "<svg/>"}):
        t, f = werkzeug(basis, KARL, "symbol_setzen", **args)
        assert f and "nur Organisator:innen" in t
    assert Schreibweg.anfragen == []
    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" fill="#1f7a57"/></svg>'
    Schreibweg.antwort = (200, {"ok": True, "text": "Das App-Symbol der Reise ist ersetzt (medien/icon.svg)."})
    t, f = werkzeug(basis, ALT_ORGANISATOR, "icon_set", svg=svg, reason="Entwurf aus der App")
    assert not f, t
    pfad, _, body = Schreibweg.anfragen[-1]
    assert pfad == "/beispielreise/symbol_setzen" and body["args"] == {"svg": svg, "grund": "Entwurf aus der App"}
    werkzeug(basis, ALT_ORGANISATOR, "icon_set", remove=True)
    assert Schreibweg.anfragen[-1][2]["args"] == {"entfernen": True}
    liste = rpc(basis, ALT_ORGANISATOR, "tools/list")["tools"]
    w = next(x for x in liste if x["name"] == "symbol_setzen")
    assert {"svg", "png_base64", "remove", "reason"} <= set(w["inputSchema"]["properties"])   # englisch nach außen


def test_symbol_lesen_ohne_eigenes_symbol(schreibweg, tmp_path, monkeypatch):
    basis, _ = schreibweg
    seite = tmp_path / "s" / "beispielreise"
    import shutil
    shutil.copytree(Path(kn.os.environ["KN_SEITEN"]) / "beispielreise", seite)
    (seite / "symbol.svg").unlink()
    monkeypatch.setenv("KN_SEITEN", str(tmp_path / "s"))
    r = rpc(basis, ALT_ORGANISATOR, "tools/call", {"name": "icon_set", "arguments": {}})
    assert meldet(r["content"][0]["text"], "konnektor.symbol.kurzname") and r["content"][1]["type"] == "image"
    (seite / "icon-192.png").unlink()
    t, f = werkzeug(basis, ALT_ORGANISATOR, "icon_set")
    assert f and meldet(t, "konnektor.symbol.keine_seite")
