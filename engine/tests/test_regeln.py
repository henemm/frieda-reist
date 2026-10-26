"""Tests für Paket B: Regeln im Code (Rechte je Rolle, Verhalten je Status, Bausteine, Konflikt) gegen die Beispielreise."""
import datetime
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
import reise as rg  # noqa: E402
import rueckmeldungen as rm  # noqa: E402

WURZEL = Path(__file__).resolve().parent.parent.parent
BEISPIEL = WURZEL / "beispiel" / "reisen" / "beispielreise"   # ida bestimmer, karl einbringer
IDA, MAX, KARL, KIM = "i" * 32, "x" * 32, "k" * 32, "q" * 32
ALLE_BAUSTEINE = ["varianten", "karte", "tagesseiten", "rueckmeldungen", "fragen", "aufgaben", "wuensche"]


def reise_bauen(tmp, status="planung", bausteine=None, luecke=False):
    """Beispielreise mit gewünschtem Status und Bausteinen bauen; Max als zweiter Bestimmer, Kim als Reisende.
    -> Seitenordner (<seiten>/beispielreise/daten.json)"""
    quelle = tmp / "quelle"
    shutil.copytree(BEISPIEL, quelle)
    y = yaml.safe_load((quelle / "reise.yaml").read_text(encoding="utf-8"))
    y["personen"]["max"] = {"name": "Max", "rolle": "bestimmer", "reist": False}
    y["personen"]["kim"] = {"name": "Kim", "rolle": "reisend", "reist": True}
    if status != "planung":
        y["status"] = {"wert": status, "verlauf": y["status"]["verlauf"] + [
            {"datum": datetime.date(2026, 10, 25), "wert": status, "wer": "Ida", "grund": "Test"}]}
    if bausteine is not None:
        y["bausteine"] = bausteine
    (quelle / "reise.yaml").write_text(yaml.safe_dump(y, allow_unicode=True), encoding="utf-8")
    if luecke:   # Start in einem anderen Ort: der Plan geht nicht auf (Warnung)
        r = quelle / "plan" / "routen.yaml"
        r.write_text(r.read_text(encoding="utf-8").replace("ort: O-01}", "ort: O-03}", 1), encoding="utf-8")
    seiten = tmp / "seiten"
    bauen.bauen(quelle, seiten / "beispielreise")
    return seiten


def starten(handler):
    s = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s, f"http://127.0.0.1:{s.server_address[1]}"


def anfrage(url, daten=None, methode="POST"):
    body = json.dumps(daten).encode() if daten is not None else None
    req = urllib.request.Request(url, data=body, method=methode, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")


class Umgebung:
    """Rückmeldedienst und Konnektor gegen eine gebaute Beispielreise."""

    def __init__(self, tmp, monkeypatch, status="planung", bausteine=None):
        self.seiten = reise_bauen(tmp, status, bausteine)
        self.ablage = tmp / "ablage"
        (self.ablage / "beispielreise").mkdir(parents=True)
        zug = tmp / "zugaenge.json"
        zug.write_text(json.dumps({t: {"reise": "beispielreise", "person": p} for t, p in
                                   ((IDA, "ida"), (MAX, "max"), (KARL, "karl"), (KIM, "kim"))}))
        monkeypatch.setenv("RM_ABLAGE", str(self.ablage))
        monkeypatch.setenv("KN_SEITEN", str(self.seiten))
        monkeypatch.setenv("KN_ZUGAENGE", str(zug))
        rm._zeiten.clear()
        self.rs, self.rurl = starten(rm.Dienst)
        monkeypatch.setenv("KN_RUECKMELDEDIENST", self.rurl)
        self.ks, self.kurl = starten(kn.Dienst)
        self.o = self.ablage / "beispielreise"

    def schliessen(self):
        self.ks.shutdown()
        self.rs.shutdown()

    def rpc(self, token, methode, params=None):
        code, a = anfrage(f"{self.kurl}/{token}", {"jsonrpc": "2.0", "id": 1, "method": methode, "params": params or {}})
        assert code == 200, a
        return a["result"]

    def werkzeug(self, token, name, **args):
        r = self.rpc(token, "tools/call", {"name": name, "arguments": args})
        return r["content"][0]["text"], r["isError"]

    def werkzeuge(self, token):
        return {t["name"] for t in self.rpc(token, "tools/list")["tools"]}


@pytest.fixture
def umgebung(tmp_path, monkeypatch):
    erzeugt = []

    def neu(status="planung", bausteine=None):
        u = Umgebung(tmp_path / f"u{len(erzeugt)}", monkeypatch, status, bausteine)
        erzeugt.append(u)
        return u
    yield neu
    for u in erzeugt:
        u.schliessen()


# ---------- Regeln ohne Dienst ----------

@pytest.mark.parametrize("status", rg.STATUS)
@pytest.mark.parametrize("rolle", rg.ROLLEN)
def test_rechte_je_rolle_und_status(rolle, status):
    erlaubt = {a: rg.erlaubt(a, rolle, status, ALLE_BAUSTEINE)[0] for a in rg.AKTIONEN}
    schreiben = rg.verhalten(status)["schreiben"]
    if rolle == "reisend":
        assert not any(erlaubt.values())            # lesen, sonst nichts
        return
    # Rückmeldung und Aufgabe: in der Nachlese (danach) noch erlaubt, im Archiv nicht
    assert erlaubt["rueckmeldung"] == erlaubt["aufgabe"] == (schreiben != "nichts")
    # Wunsch und Alternative ändern den Plan: nur bei vollem Schreibrecht
    assert erlaubt["wunsch"] == erlaubt["alternative"] == (schreiben == "alles")
    # Aufträge: nur Bestimmer, und nur solange der Plan nicht gesperrt ist
    assert erlaubt["auftrag"] == (rolle == "bestimmer" and schreiben == "alles")


def test_auftrag_an_die_reise_geht_in_jedem_status():
    for status in rg.STATUS:
        assert rg.erlaubt("auftrag", "bestimmer", status, [], "reise")[0]
        assert not rg.erlaubt("auftrag", "einbringer", status, [], "reise")[0]
    ok, grund = rg.erlaubt("auftrag", "bestimmer", "archiv", [], "V-01")
    assert not ok and "archiviert" in grund and "zurücksetzen" in grund


def test_ausgeschalteter_baustein_sperrt_schreiben():
    for aktion, baustein in (("rueckmeldung", "rueckmeldungen"), ("wunsch", "wuensche"), ("aufgabe", "aufgaben"),
                             ("alternative", "varianten")):
        rest = [b for b in ALLE_BAUSTEINE if b != baustein]
        ok, grund = rg.erlaubt(aktion, "einbringer", "planung", rest)
        assert not ok and baustein in grund
        assert rg.erlaubt(aktion, "einbringer", "planung", ALLE_BAUSTEINE)[0]
    assert rg.erlaubt("wunsch", "einbringer", "planung", None)[0]   # unbekannt: nicht prüfen


def test_verhalten_je_status():
    v = {s: rg.verhalten(s) for s in rg.STATUS}
    assert not v["idee"]["warnungen"] and v["planung"]["warnungen"]
    assert [s for s in rg.STATUS if v[s]["mahnung_planung"]] == ["fest", "unterwegs"]
    assert [s for s in rg.STATUS if v[s]["fristen"]] == ["fest", "unterwegs"]
    assert [s for s in rg.STATUS if v[s]["start"] == "heute"] == ["unterwegs"]
    assert [s for s in rg.STATUS if v[s]["ausloeser_vor"]] == ["unterwegs"]
    assert [v[s]["schreiben"] for s in ("danach", "archiv")] == ["nachlese", "nichts"]
    assert rg.verhalten("gibt-es-nicht") == rg.verhalten("planung")


def test_widerspruch_zwischen_bestimmern():
    def e(wer, ziel, was):
        return {"wer": wer, "ziel": ziel, "entscheidung": was}
    assert rg.widerspruch(e("Ida", "V-01.a", "gewaehlt"), e("Max", "V-01.a", "verworfen"))
    assert rg.widerspruch(e("Ida", "V-01.a", "gewaehlt"), e("Max", "V-01.b", "gewaehlt"))
    assert not rg.widerspruch(e("Ida", "V-01.a", "gewaehlt"), e("Max", "V-01.b", "verworfen"))   # verträgt sich
    assert not rg.widerspruch(e("Ida", "V-01.a", "gewaehlt"), e("Max", "V-01.a", "gewaehlt"))    # dasselbe
    assert not rg.widerspruch(e("Ida", "V-01.a", "gewaehlt"), e("Max", "V-02.a", "gewaehlt"))    # andere Stelle
    assert not rg.widerspruch(e("Ida", "V-01.a", "gewaehlt"), e("Ida", "V-01.a", "verworfen"))   # eine Person ändert sich
    assert len(rg.konflikte(e("Ida", "V-01.a", "gewaehlt"), [e("Max", "V-01.a", "verworfen"), e("Max", "V-02.a", "gewaehlt")])) == 1


# ---------- Verhalten je Status im Bau ----------

def daten_von(seiten):
    return json.loads((seiten / "beispielreise" / "daten.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("status", rg.STATUS)
def test_bau_traegt_verhalten(tmp_path, status):
    d = daten_von(reise_bauen(tmp_path, status))
    assert d["reise"]["status"]["wert"] == status
    assert d["reise"]["verhalten"] == rg.verhalten(status)


def test_mahnungen_erst_ab_fest(tmp_path):
    ids = {}
    for status in ("idee", "planung", "fest", "unterwegs", "danach"):
        r = daten_von(reise_bauen(tmp_path / status, status))["route"]
        ids[status] = [m["bezug"] for m in r["mahnungen"]]
    assert ids["idee"] == ids["planung"] == ids["danach"] == []
    assert "V-01" in ids["fest"] and ids["fest"] == ids["unterwegs"]
    assert "offen, obwohl die Reise fest ist" in next(m["text"] for m in daten_von(reise_bauen(tmp_path / "x", "fest"))["route"]["mahnungen"] if m["bezug"] == "V-01")


def test_idee_ohne_warnungen(tmp_path):
    assert daten_von(reise_bauen(tmp_path / "a", "planung", luecke=True))["route"]["warnungen"]
    assert daten_von(reise_bauen(tmp_path / "b", "idee", luecke=True))["route"]["warnungen"] == []


# ---------- Rückmeldedienst: Rechte beim Schreiben ----------

def rueck(u, name, art="Kommentar", ziel="T-01", text="Hallo"):
    return anfrage(f"{u.rurl}/beispielreise/rueckmeldungen", {"name": name, "art": art, "ziel": ziel, "text": text})


def aufgabe(u, name):
    return anfrage(f"{u.rurl}/beispielreise/aufgaben", {"name": name, "titel": "Etwas tun"})


def test_dienst_reisende_person_darf_nichts_schreiben(umgebung):
    u = umgebung()
    for code, a in (rueck(u, "Kim"), rueck(u, "kim", art="Wunsch", ziel=""), aufgabe(u, "Kim")):
        assert code == 403 and "nur lesen" in a["fehler"]
    assert rueck(u, "Karl")[0] == 201 and rueck(u, "Eine Besucherin")[0] == 201   # Einbringer und unbekannte Namen
    assert aufgabe(u, "Karl")[0] == 201
    assert {e["name"] for e in rm.eintraege(u.o)} == {"Eine Besucherin", "Karl"}


def test_dienst_aufgabe_aendern_wird_geprueft(umgebung):
    u = umgebung()
    code, a = aufgabe(u, "Karl")
    code, _ = anfrage(f"{u.rurl}/beispielreise/aufgaben/{a['id']}", {"name": "Kim", "status": "erledigt"}, "PATCH")
    assert code == 403
    code, a = anfrage(f"{u.rurl}/beispielreise/aufgaben/{a['id']}", {"name": "Karl", "status": "erledigt"}, "PATCH")
    assert code == 200 and a["status"] == "erledigt"


@pytest.mark.parametrize("status, wunsch, rueckmeldung, auf", [
    ("planung", 201, 201, 201), ("fest", 201, 201, 201), ("unterwegs", 201, 201, 201),
    ("danach", 403, 201, 201), ("archiv", 403, 403, 403)])
def test_dienst_verhalten_je_status(umgebung, status, wunsch, rueckmeldung, auf):
    u = umgebung(status)
    assert rueck(u, "Karl", art="Wunsch", ziel="")[0] == wunsch
    assert rueck(u, "Karl")[0] == rueckmeldung
    assert aufgabe(u, "Karl")[0] == auf


def test_dienst_zurueckziehen_im_archiv_gesperrt(umgebung):
    u = umgebung("archiv")
    (u.o / "eingang.jsonl").write_text(json.dumps({"id": "R-20261026-120000-abcd", "name": "Karl"}) + "\n")
    code, a = anfrage(f"{u.rurl}/beispielreise/rueckmeldungen/R-20261026-120000-abcd", methode="DELETE")
    assert code == 403 and "archiviert" in a["fehler"]


def test_dienst_ausgeschalteter_baustein(umgebung):
    u = umgebung(bausteine=["varianten", "rueckmeldungen"])   # kein aufgaben, kein wuensche
    assert aufgabe(u, "Karl")[0] == 403
    code, a = rueck(u, "Karl", art="Wunsch", ziel="")
    assert code == 403 and "wuensche" in a["fehler"]
    assert rueck(u, "Karl")[0] == 201


def test_dienst_ohne_veroeffentlichte_seite_wie_bisher(tmp_path, monkeypatch):
    ablage = tmp_path / "ablage"
    (ablage / "beispielreise").mkdir(parents=True)
    monkeypatch.setenv("RM_ABLAGE", str(ablage))
    monkeypatch.setenv("RM_SEITEN", str(tmp_path / "leer"))
    rm._zeiten.clear()
    s, url = starten(rm.Dienst)
    try:
        assert anfrage(f"{url}/beispielreise/rueckmeldungen", {"name": "Kim", "art": "Kommentar", "ziel": "T-01", "text": "x"})[0] == 201
    finally:
        s.shutdown()


# ---------- Konnektor: Werkzeuge je Rolle, Status und Baustein ----------

def test_konnektor_werkzeuge_je_status(umgebung):
    u = umgebung("planung")
    nur_lesen = u.werkzeuge(KIM)
    assert not nur_lesen & kn.SCHREIB_WERKZEUGE and "auftrag_geben" not in nur_lesen
    assert kn.SCHREIB_WERKZEUGE <= u.werkzeuge(KARL) and "auftrag_geben" in u.werkzeuge(IDA)

    danach = umgebung("danach")
    w = danach.werkzeuge(KARL)
    assert {"rueckmeldung_geben", "aufgabe_anlegen"} <= w and "alternative_vorschlagen" not in w
    art = next(t for t in danach.rpc(KARL, "tools/list")["tools"] if t["name"] == "rueckmeldung_geben")
    assert "Wunsch" not in art["inputSchema"]["properties"]["art"]["enum"]
    assert "auftrag_geben" in danach.werkzeuge(IDA)      # bleibt sichtbar: Status zurücksetzen geht

    archiv = umgebung("archiv")
    assert not archiv.werkzeuge(KARL) & kn.SCHREIB_WERKZEUGE
    assert "zeige" in archiv.werkzeuge(KARL)


def test_konnektor_prueft_beim_aufruf_auch_ohne_werkzeugliste(umgebung):
    u = umgebung("archiv")
    for name, args in (("rueckmeldung_geben", {"art": "Kommentar", "ziel": "T-01", "text": "x"}),
                       ("aufgabe_anlegen", {"titel": "x"}),
                       ("alternative_vorschlagen", {"titel": "x", "wahlstelle": "V-03"})):
        t, f = u.werkzeug(KARL, name, **args)
        assert f and "archiviert" in t, name
    t, f = u.werkzeug(IDA, "auftrag_geben", ziel="V-01", auftrag="V-01.a wählen")
    assert f and "archiviert" in t and not (u.o / "auftraege.jsonl").exists()
    t, f = u.werkzeug(IDA, "auftrag_geben", ziel="reise", auftrag="Status wieder auf danach setzen")
    assert not f and (u.o / "auftraege.jsonl").exists()
    t, f = u.werkzeug(KIM, "auftrag_geben", ziel="reise", auftrag="x")
    assert f and "nur Bestimmer" in t
    assert u.werkzeug(KARL, "auftrag_geben", ziel="reise", auftrag="x")[1]


def test_konnektor_danach_nur_nachlese(umgebung):
    u = umgebung("danach")
    t, f = u.werkzeug(KARL, "rueckmeldung_geben", art="Kommentar", ziel="T-01", text="Es war schön")
    assert not f
    t, f = u.werkzeug(KARL, "rueckmeldung_geben", art="Wunsch", text="Nochmal hin")
    assert f and "schreibgeschützt" in t
    t, f = u.werkzeug(KARL, "alternative_vorschlagen", titel="x", wahlstelle="V-03")
    assert f and "schreibgeschützt" in t
    assert not u.werkzeug(KARL, "aufgabe_anlegen", titel="Fotos sortieren")[1]


def test_konnektor_bausteine_blenden_aus(umgebung):
    u = umgebung(bausteine=["rueckmeldungen", "karte"])
    w = u.werkzeuge(KARL)
    assert "aufgaben" not in w and "aufgabe_anlegen" not in w and "varianten" not in w
    assert "alternative_vorschlagen" not in w and "merkmale" not in w and "offene_fragen" not in w
    assert {"ueberblick", "zeige", "suche", "rueckmeldungen", "rueckmeldung_geben"} <= w
    art = next(t for t in u.rpc(KARL, "tools/list")["tools"] if t["name"] == "rueckmeldung_geben")
    assert "Wunsch" not in art["inputSchema"]["properties"]["art"]["enum"]
    for name, args in (("aufgaben", {}), ("varianten", {}), ("offene_fragen", {}),
                       ("aufgabe_anlegen", {"titel": "x"}), ("rueckmeldung_geben", {"art": "Wunsch", "text": "x"})):
        t, f = u.werkzeug(KARL, name, **args)
        assert f and ("ausgeschaltet" in t), name
    ue, _ = u.werkzeug(KARL, "ueberblick")
    assert "Offene Fragen" not in ue and "Offene Aufgaben" not in ue and "Wahlstellen (Werkzeug" not in ue
    anleitung = u.rpc(KARL, "initialize")["instructions"]
    assert "ausgeschaltet" in anleitung and "aufgaben" in anleitung and "art Wunsch" not in anleitung


def test_konnektor_ueberblick_je_status(umgebung):
    # Jede Umgebung setzt die Pfade im Prozess neu: eine nach der anderen benutzen
    u = umgebung("planung")
    text, _ = u.werkzeug(KARL, "ueberblick")
    assert "Mahnungen" not in text and "## Heute" not in text
    planung = text[text.index("## Wahlstellen"):]
    u = umgebung("fest")
    text, _ = u.werkzeug(KARL, "ueberblick")
    assert "## Mahnungen" in text and "V-01" in text
    u = umgebung("unterwegs")
    text, _ = u.werkzeug(KARL, "ueberblick")
    assert "## Heute: kein Tag im Plan" in text        # die Beispielreise liegt im Mai 2027
    unterwegs = text[text.index("## Wahlstellen"):]
    assert "unterwegs wählen" in unterwegs and "unterwegs wählen" not in planung
    # Wahlstellen mit Auslöser rücken vor: nur im Status unterwegs ändert sich die Reihenfolge
    ids = lambda t: [z.split()[1] for z in t.splitlines() if z.startswith("- V-")]
    assert ids(unterwegs)[0] == "V-02" and sorted(ids(unterwegs)) == sorted(ids(planung))


def test_fristen_zaehlen_erst_ab_fest(umgebung):
    for status, ueberfaellig in (("planung", False), ("fest", True), ("unterwegs", True), ("danach", False)):
        u = umgebung(status)
        assert u.werkzeug(KARL, "aufgabe_anlegen", titel="Hotel buchen", frist="2020-01-01")[0]
        t, _ = u.werkzeug(KARL, "ueberblick")
        assert ("davon 1 überfällig" in t) == ueberfaellig, status
        t, _ = u.werkzeug(KARL, "aufgaben")
        assert ("ÜBERFÄLLIG" in t) == ueberfaellig, status


def test_verfassung_ist_kurz_und_nennt_aufgabe_grenzen_rollen(umgebung):
    u = umgebung("fest")
    for token, rolle in ((IDA, "Bestimmer"), (KARL, "Einbringer"), (KIM, "reisend")):
        text = u.rpc(token, "initialize")["instructions"]
        assert len(text) < 2600, len(text)
        assert text.startswith("Aufgabe:") and "Grenzen:" in text and "Rollen:" in text and rolle in text
        assert "Status: Der Plan steht" in text


# ---------- Konflikt zwischen Bestimmern ----------

def test_konflikt_zwischen_zwei_auftraegen(umgebung):
    u = umgebung()
    t, f = u.werkzeug(IDA, "auftrag_geben", ziel="V-01.a", entscheidung="gewaehlt", auftrag="Direktverbindung nehmen")
    assert not f and "widerspricht" not in t
    t, f = u.werkzeug(MAX, "auftrag_geben", ziel="V-01.b", entscheidung="gewaehlt", auftrag="Kirnitzschtalbahn nehmen")
    assert not f and "widerspricht" in t and "offene Frage" in t and "Ida" in t
    auf = {a["name"]: a for a in rm.auftraege(u.o)}
    assert set(auf) == {"Ida", "Max"} and all(a["status"] == "konflikt" for a in auf.values())
    assert all(a["daten"]["entscheidung"] == "gewaehlt" for a in auf.values())
    ms = rm.meldungen(u.o)
    assert len(ms) == 1 and ms[0]["an"] == ["Ida", "Max"] and ms[0]["art"] == "konflikt"
    assert sorted(ms[0]["auftraege"]) == sorted(a["id"] for a in auf.values())
    # Die Beteiligten sehen die Meldung in der Rückmeldeliste, Karl nicht
    assert "Meldungen an dich" in u.werkzeug(IDA, "rueckmeldungen")[0]
    assert "Meldungen an dich" in u.werkzeug(MAX, "rueckmeldungen")[0]
    assert "Meldungen an dich" not in u.werkzeug(KARL, "rueckmeldungen")[0]
    # Claude Code sieht sie in der Liste nicht als „neu“, sondern mit Hinweis
    assert not [e for e in rm.auftraege(u.o) if e["status"] == "neu"]


def test_konflikt_gegen_veroeffentlichte_entscheidung(umgebung):
    u = umgebung()      # V-03.a ist im Plan von Ida gewählt
    t, f = u.werkzeug(MAX, "auftrag_geben", ziel="V-03.a", entscheidung="verworfen", auftrag="Doch nicht dort schlafen")
    assert not f and "widerspricht" in t and "Ida am 2026-10-20 im Plan" in t
    assert rm.auftraege(u.o)[0]["status"] == "konflikt"
    assert rm.meldungen(u.o)[0]["an"] == ["Ida", "Max"]


def test_kein_konflikt_bei_vertraeglichem_und_bei_derselben_person(umgebung):
    u = umgebung()
    u.werkzeug(IDA, "auftrag_geben", ziel="V-01.a", entscheidung="gewaehlt", auftrag="a nehmen")
    t, _ = u.werkzeug(MAX, "auftrag_geben", ziel="V-01.b", entscheidung="verworfen", auftrag="b verwerfen")   # verträgt sich
    assert "widerspricht" not in t
    t, _ = u.werkzeug(IDA, "auftrag_geben", ziel="V-01.a", entscheidung="verworfen", auftrag="Ich habe es mir anders überlegt")
    assert "widerspricht" not in t                                                                              # dieselbe Person
    t, _ = u.werkzeug(IDA, "auftrag_geben", auftrag="Nur ein Wunsch ohne Entscheidung")
    assert "widerspricht" not in t
    assert all(a["status"] == "neu" for a in rm.auftraege(u.o)) and rm.meldungen(u.o) == []


def test_entscheidung_braucht_ziel_und_bekannten_wert(umgebung):
    u = umgebung()
    assert u.werkzeug(IDA, "auftrag_geben", entscheidung="gewaehlt", auftrag="x")[1]
    assert u.werkzeug(IDA, "auftrag_geben", ziel="V-01.a", entscheidung="vielleicht", auftrag="x")[1]
    assert not (u.o / "auftraege.jsonl").exists()


def test_liste_zeigt_konflikt(umgebung, capsys):
    u = umgebung()
    u.werkzeug(IDA, "auftrag_geben", ziel="V-01.a", entscheidung="gewaehlt", auftrag="a")
    u.werkzeug(MAX, "auftrag_geben", ziel="V-01.b", entscheidung="gewaehlt", auftrag="b")
    rm.liste("beispielreise", True)
    out = capsys.readouterr().out
    assert out.count("KONFLIKT") == 2 and "[konflikt]" in out and "Offene Frage (F-…) anlegen" in out
    rm.setze("beispielreise", rm.auftraege(u.o)[0]["id"], "rueckfrage", "siehe F-09")
