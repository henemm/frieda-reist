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
BEISPIEL = WURZEL / "beispiel" / "reisen" / "beispielreise"   # ida organisator, karl mitwirkend
IDA, MAX, KARL, KIM = "i" * 32, "x" * 32, "k" * 32, "q" * 32
ALLE_BAUSTEINE = ["varianten", "karte", "tagesseiten", "rueckmeldungen", "fragen", "aufgaben", "wuensche"]


def reise_bauen(tmp, status="planung", bausteine=None, luecke=False, regeln=None, darstellung=None, fest=False):
    """Beispielreise mit gewünschtem Status, Bausteinen und Darstellung bauen; Max als zweite Organisator:in, Kim als Gast.
    -> Seitenordner (<seiten>/beispielreise/daten.json)"""
    quelle = tmp / "quelle"
    shutil.copytree(BEISPIEL, quelle)
    y = yaml.safe_load((quelle / "reise.yaml").read_text(encoding="utf-8"))
    y["personen"]["max"] = {"name": "Max", "rolle": "organisator", "reist": False}
    y["personen"]["kim"] = {"name": "Kim", "rolle": "gast", "reist": True}
    if status != "planung":
        y["status"] = {"wert": status, "verlauf": y["status"]["verlauf"] + [
            {"datum": datetime.date(2026, 10, 25), "wert": status, "wer": "Ida", "grund": "Test"}]}
    if bausteine is not None:
        y["bausteine"] = bausteine
    if regeln:
        y.setdefault("regeln", {}).update(regeln)
    if darstellung:
        y.setdefault("darstellung", {}).update(darstellung)
    (quelle / "reise.yaml").write_text(yaml.safe_dump(y, allow_unicode=True), encoding="utf-8")
    if luecke:   # Start in einem anderen Ort: der Plan geht nicht auf (Warnung)
        r = quelle / "plan" / "routen.yaml"
        r.write_text(r.read_text(encoding="utf-8").replace("ort: O-01}", "ort: O-03}", 1), encoding="utf-8")
    if fest:     # Plan A gewählt (V-01.a): der Plan steht fest, die Seite hat Tagesseiten
        r = quelle / "plan" / "routen.yaml"
        alt = '{datum: 2026-10-20, status: vorgeschlagen, wer: Claude, grund: "kürzeste Verbindung zum Bahnhof"}'
        r.write_text(r.read_text(encoding="utf-8").replace(
            alt, alt + '\n          - {datum: 2026-10-25, status: gewaehlt, wer: Ida, grund: "Test"}', 1), encoding="utf-8")
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

    def __init__(self, tmp, monkeypatch, status="planung", bausteine=None, regeln=None):
        self.seiten = reise_bauen(tmp, status, bausteine, regeln=regeln)
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
        # Nachgestellter Schreibweg (engine/schreiben.py dienst): merkt sich, was der Konnektor schreiben will
        monkeypatch.setenv("FR_KONTEN", str(tmp / "konten"))
        self.schreibweg = []
        umgebung = self

        class Schreibweg(kn.BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
                umgebung.schreibweg.append((self.path, body))
                daten = json.dumps({"ok": True, "text": f"geschrieben: {self.path}"}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(daten)))
                self.end_headers()
                self.wfile.write(daten)

            def log_message(self, *a):
                pass
        self.ss, surl = starten(Schreibweg)
        monkeypatch.setenv("KN_SCHREIBDIENST", surl)
        self.ks, self.kurl = starten(kn.Dienst)
        self.o = self.ablage / "beispielreise"

    def schliessen(self):
        self.ks.shutdown()
        self.rs.shutdown()
        self.ss.shutdown()

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

    def neu(status="planung", bausteine=None, regeln=None):
        u = Umgebung(tmp_path / f"u{len(erzeugt)}", monkeypatch, status, bausteine, regeln)
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
    if rolle == "gast":
        assert not any(erlaubt.values())            # lesen, sonst nichts
        return
    # Rückmeldung und Aufgabe: in der Nachlese (danach) noch erlaubt, im Archiv nicht
    assert erlaubt["rueckmeldung"] == erlaubt["aufgabe"] == (schreiben != "nichts")
    # Wunsch und Alternative ändern den Plan: nur bei vollem Schreibrecht
    assert erlaubt["wunsch"] == erlaubt["alternative"] == (schreiben == "alles")
    # Wunsch-Brett: abhaken auch in der Nachlese, einplanen nur Organisator:innen bei vollem Schreibrecht
    assert erlaubt["wunsch_erlebt"] == (schreiben != "nichts")
    assert erlaubt["wunsch_einplanen"] == (rolle == "organisator" and schreiben == "alles")


def test_status_zuruecksetzen_geht_in_jedem_status():
    """Aufträge gibt es seit O-3 nicht mehr; eine gesperrte Reise öffnet ein:e Organisator:in mit reise_status_setzen (Aktion einstellung)."""
    for status in rg.STATUS:
        assert rg.erlaubt("einstellung", "organisator", status, [])[0]
        assert not rg.erlaubt("einstellung", "mitwirkend", status, [])[0]
    ok, grund = rg.erlaubt("alternative", "organisator", "archiv", ALLE_BAUSTEINE, "V-01")
    assert not ok and "archiviert" in grund and "reise_status_setzen" in grund


def test_ausgeschalteter_baustein_sperrt_schreiben():
    for aktion, baustein in (("rueckmeldung", "rueckmeldungen"), ("wunsch", "wuensche"), ("aufgabe", "aufgaben"),
                             ("alternative", "varianten")):
        rest = [b for b in ALLE_BAUSTEINE if b != baustein]
        ok, grund = rg.erlaubt(aktion, "mitwirkend", "planung", rest)
        assert not ok and baustein in grund
        assert rg.erlaubt(aktion, "mitwirkend", "planung", ALLE_BAUSTEINE)[0]
    assert rg.erlaubt("wunsch", "mitwirkend", "planung", None)[0]   # unbekannt: nicht prüfen


def test_verhalten_je_status():
    v = {s: rg.verhalten(s) for s in rg.STATUS}
    assert not v["idee"]["warnungen"] and v["planung"]["warnungen"]
    assert [s for s in rg.STATUS if v[s]["mahnung_planung"]] == ["fest", "unterwegs"]
    assert [s for s in rg.STATUS if v[s]["fristen"]] == ["fest", "unterwegs"]
    assert [s for s in rg.STATUS if v[s]["start"] == "heute"] == ["unterwegs"]
    assert [s for s in rg.STATUS if v[s]["ausloeser_vor"]] == ["unterwegs"]
    assert [v[s]["schreiben"] for s in ("danach", "archiv")] == ["nachlese", "nichts"]
    assert rg.verhalten("gibt-es-nicht") == rg.verhalten("planung")


def test_widerspruch_zwischen_organisatoren():
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
    fest = {m["bezug"]: m["text"] for m in daten_von(reise_bauen(tmp_path / "x", "fest"))["route"]["mahnungen"]}
    assert "offen, obwohl die Reise fest ist" in fest["V-01"]
    # Veränderliche Angabe ohne Prüfdatum (Preis der Beispiel-Unterkunft U-01) ist ab fest eine Mahnung, kein Fehler
    assert "U-01" in fest and "preis" in fest["U-01"] and "ohne Prüfdatum" in fest["U-01"]
    assert "U-01" in ids["unterwegs"] and "U-01" not in ids["planung"]


def test_lage_der_unterkunft(tmp_path):
    """ADR-0004: Lage = Adresse oder Punkt. Der Punkt kommt aus plan/punkte.yaml (id: U-…); ab fest wird eine Unterkunft
    im Plan ohne Lage gemahnt."""
    r = daten_von(reise_bauen(tmp_path / "a", "fest"))["route"]
    u = r["unterkuenfte"]
    assert u["U-01"]["adresse"]["wert"].startswith("Terrassenufer") and u["U-01"]["adresse"]["quelle"]
    assert u["U-02"]["punkt"]["wert"] == [50.9792, 14.1128] and u["U-02"]["punkt"]["quelle"] == "erfunden (Beispiel)"
    assert not any("Lage fehlt" in m["text"] for m in r["mahnungen"])
    # ohne Adresse und ohne Punkt: Mahnung für U-01 (Nacht 1 im Plan)
    quelle = tmp_path / "b" / "quelle"
    seiten = reise_bauen(tmp_path / "b", "fest")
    rt = quelle / "plan" / "routen.yaml"
    rt.write_text("\n".join(z for z in rt.read_text(encoding="utf-8").splitlines() if "Terrassenufer" not in z) + "\n", encoding="utf-8")
    bauen.bauen(quelle, seiten / "beispielreise")
    m = [x for x in daten_von(seiten)["route"]["mahnungen"] if "Lage fehlt" in x["text"]]
    assert [x["bezug"] for x in m] == ["U-01"], m


def test_mahnungen_ohne_kasten_auf_der_seite(tmp_path):
    """Der Kasten „Mahnung“ auf der Seite ist weg (Product Owner 29.10.2026): kein Schalter mehr in den Seitendaten, der alte
    Schlüssel darstellung.mahnungen baut weiter ohne Wirkung; berechnet (für den Konnektor, ueberblick) bleiben die Mahnungen."""
    def bauen_mit(ziel, wert):
        quelle = ziel / "quelle"
        shutil.copytree(BEISPIEL, quelle)
        y = yaml.safe_load((quelle / "reise.yaml").read_text(encoding="utf-8"))
        y["status"] = {"wert": "fest", "verlauf": y["status"]["verlauf"] + [
            {"datum": datetime.date(2026, 10, 25), "wert": "fest", "wer": "Ida", "grund": "Test"}]}
        if wert is not None:
            y["darstellung"]["mahnungen"] = wert
        (quelle / "reise.yaml").write_text(yaml.safe_dump(y, allow_unicode=True), encoding="utf-8")
        bauen.bauen(quelle, ziel / "seiten" / "beispielreise")
        return daten_von(ziel / "seiten"), (ziel / "seiten" / "beispielreise" / "index.html").read_text(encoding="utf-8")
    standard, seite = bauen_mit(tmp_path / "a", None)
    alt, _ = bauen_mit(tmp_path / "b", False)
    assert "mahnungen" not in standard["reise"] and "mahnungen" not in alt["reise"]
    assert alt["route"]["mahnungen"] == standard["route"]["mahnungen"] != []
    assert "function mahnungen(" not in seite and "Mahnung (" not in seite


def test_idee_ohne_warnungen(tmp_path):
    assert daten_von(reise_bauen(tmp_path / "a", "planung", luecke=True))["route"]["warnungen"]
    assert daten_von(reise_bauen(tmp_path / "b", "idee", luecke=True))["route"]["warnungen"] == []


# ---------- Rückmeldedienst: Rechte beim Schreiben ----------

def rueck(u, name, art="Kommentar", ziel="T-01", text="Hallo"):
    return anfrage(f"{u.rurl}/beispielreise/rueckmeldungen", {"name": name, "art": art, "ziel": ziel, "text": text})


def aufgabe(u, name):
    return anfrage(f"{u.rurl}/beispielreise/aufgaben", {"name": name, "titel": "Etwas tun"})


def test_dienst_gast_darf_nichts_schreiben(umgebung):
    u = umgebung()
    for code, a in (rueck(u, "Kim"), rueck(u, "kim", art="Wunsch", ziel=""), aufgabe(u, "Kim")):
        assert code == 403 and "nur lesen" in a["fehler"]
    assert rueck(u, "Karl")[0] == 201 and rueck(u, "Eine Besucherin")[0] == 201   # Mitwirkende und unbekannte Namen
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


def test_dienst_zurueckziehen_prueft_wie_absenden(umgebung):
    """Zurückziehen ist Schreiben: Rolle des Absenders, Baustein und Status gelten wie beim Absenden."""
    u = umgebung(bausteine=["varianten", "rueckmeldungen"])   # Wünsche ausgeschaltet
    zeilen = [{"id": "R-20261026-120000-aaaa", "name": "Kim", "art": "Kommentar"},     # Kim reist nur mit (liest)
              {"id": "R-20261026-120000-bbbb", "name": "Karl", "art": "Wunsch"},
              {"id": "R-20261026-120000-cccc", "name": "Karl", "art": "Kommentar"}]
    (u.o / "eingang.jsonl").write_text("".join(json.dumps(z) + "\n" for z in zeilen))
    url = f"{u.rurl}/beispielreise/rueckmeldungen/"
    code, a = anfrage(url + "R-20261026-120000-aaaa", methode="DELETE")
    assert code == 403 and "nur lesen" in a["fehler"]
    code, a = anfrage(url + "R-20261026-120000-bbbb", methode="DELETE")
    assert code == 403 and "wuensche" in a["fehler"]
    assert anfrage(url + "R-20261026-120000-cccc", methode="DELETE")[0] == 200
    assert [json.loads(z)["id"] for z in (u.o / "eingang.jsonl").read_text().splitlines()] == [
        "R-20261026-120000-aaaa", "R-20261026-120000-bbbb"]


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
    assert not nur_lesen & kn.SCHREIB_WERKZEUGE
    nur_organisator = {"entscheiden", "person_einladen", "person_entfernen", "rueckmeldung_erledigen"}   # Paket C, J, O-3
    assert kn.SCHREIB_WERKZEUGE - nur_organisator <= u.werkzeuge(KARL) and not nur_organisator & u.werkzeuge(KARL)
    assert kn.SCHREIB_WERKZEUGE <= u.werkzeuge(IDA) and "reise_status_setzen" in u.werkzeuge(IDA)

    danach = umgebung("danach")
    w = danach.werkzeuge(KARL)
    assert {"rueckmeldung_geben", "aufgabe_anlegen"} <= w and "option_anlegen" not in w
    art = next(t for t in danach.rpc(KARL, "tools/list")["tools"] if t["name"] == "rueckmeldung_geben")
    assert "Wunsch" not in art["inputSchema"]["properties"]["art"]["enum"]
    assert "reise_status_setzen" in danach.werkzeuge(IDA)      # bleibt sichtbar: Status zurücksetzen geht

    archiv = umgebung("archiv")
    assert not archiv.werkzeuge(KARL) & kn.SCHREIB_WERKZEUGE
    assert "zeige" in archiv.werkzeuge(KARL)


def test_konnektor_prueft_beim_aufruf_auch_ohne_werkzeugliste(umgebung):
    u = umgebung("archiv")
    for name, args in (("rueckmeldung_geben", {"art": "Kommentar", "ziel": "T-01", "text": "x"}),
                       ("aufgabe_anlegen", {"titel": "x"}),
                       ("option_anlegen", {"titel": "x", "wahlstelle": "V-03"})):
        t, f = u.werkzeug(KARL, name, **args)
        assert f and "archiviert" in t, name
    t, f = u.werkzeug(IDA, "entscheiden", option="V-01.a", status="gewaehlt", grund="x")
    assert f and "archiviert" in t and u.schreibweg == []
    t, f = u.werkzeug(IDA, "reise_status_setzen", status="danach", grund="Status wieder auf danach setzen")
    assert not f and u.schreibweg[-1][0] == "/beispielreise/reise_status_setzen"
    t, f = u.werkzeug(KIM, "reise_status_setzen", status="planung", grund="x")
    assert f and ("nur lesen" in t or "nur Organisator:innen" in t)
    assert u.werkzeug(KARL, "reise_status_setzen", status="planung", grund="x")[1]


def test_konnektor_danach_nur_nachlese(umgebung):
    u = umgebung("danach")
    t, f = u.werkzeug(KARL, "rueckmeldung_geben", art="Kommentar", ziel="T-01", text="Es war schön")
    assert not f
    t, f = u.werkzeug(KARL, "rueckmeldung_geben", art="Wunsch", text="Nochmal hin")
    assert f and "schreibgeschützt" in t
    t, f = u.werkzeug(KARL, "option_anlegen", titel="x", wahlstelle="V-03")
    assert f and "schreibgeschützt" in t
    assert not u.werkzeug(KARL, "aufgabe_anlegen", titel="Fotos sortieren")[1]


def test_konnektor_bausteine_blenden_aus(umgebung):
    u = umgebung(bausteine=["rueckmeldungen", "karte"])
    w = u.werkzeuge(KARL)
    assert "aufgaben" not in w and "aufgabe_anlegen" not in w and "varianten" not in w
    assert "option_anlegen" not in w and "merkmale" not in w and "offene_fragen" not in w
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
    for token, rolle in ((IDA, "Organisator:in"), (KARL, "Mitwirkende:r"), (KIM, "gast")):
        text = u.rpc(token, "initialize")["instructions"]
        assert len(text) < 3900, len(text)   # mit Schreibweg: alle Werkzeuge in einem Satz; + Löschwunsch-Absatz, #145
        assert text.startswith("Aufgabe:") and "Grenzen:" in text and "Rollen:" in text and rolle in text
        assert "Status: Der Plan steht" in text


# ---------- Konflikt zwischen Organisator:innen ----------

# ---------- Paket H: neue Reise ----------
@pytest.mark.parametrize("args, text", [
    ({}, "titel fehlt"),
    ({"titel": "a\nb"}, "eine Zeile"),
    ({"titel": "Ski", "von": "8.1.2027", "bis": "2027-02-13"}, "JJJJ-MM-TT"),
    ({"titel": "Ski", "von": "2027-02-06", "bis": "2028-03-01"}, "höchstens ein Jahr"),
    ({"titel": "Ski", "von": "2027-02-06", "bis": "2027-02-13", "personen": [{"vorname": "Karl", "rolle": "chef"}]}, "Rolle muss"),
    ({"titel": "Ski", "von": "2027-02-06", "bis": "2027-02-13", "personen": [{"rolle": "mitwirkend"}]}, "Vornamen"),
    ({"titel": "Ski", "von": "2027-02-06", "bis": "2027-02-13", "personen": [{"vorname": "Karl"}, {"vorname": "karl"}]},
     "zweimal"),
    ({"titel": "Ski", "von": "2027-02-06", "bis": "2027-02-13", "personen": [{"vorname": "Ida", "rolle": "mitwirkend"}]},
     "bestimmt deshalb mit"),
    ({"titel": "Ski", "von": "2027-02-06", "bis": "2027-02-13", "pfad": "Ski Urlaub"}, "pfad: nur Kleinbuchstaben"),
    ({"titel": "Ski", "von": "2027-02-06", "bis": "2027-02-13", "pfad": "x" * 41}, "2 bis 40"),
    ({"titel": "Ski", "von": "2027-02-06", "bis": "2027-02-13", "pfad": "alt"}, "gibt es schon"),
])
def test_neue_reise_pruefen_lehnt_ab(args, text):
    from reise import neue_reise_pruefen
    d, f = neue_reise_pruefen(args, "Ida", {"alt"})
    assert d is None and text in f, f


def test_neue_reise_pruefen():
    from reise import neue_reise_pruefen, reise_pfad
    d, f = neue_reise_pruefen({"titel": " Winterwoche Allgäu ", "von": "2027-02-06", "bis": "2027-02-13",
                               "personen": [{"vorname": "Ida", "rolle": "organisator"}, {"vorname": "Jörg", "notiz": "fährt"}]},
                              "Ida")
    assert f is None and d["pfad"] == "winterwoche-allgaeu-2027" and d["titel"] == "Winterwoche Allgäu"
    assert d["personen"] == {"ida": {"name": "Ida", "rolle": "organisator"},
                             "joerg": {"name": "Jörg", "rolle": "mitwirkend", "notiz": "fährt"}}
    assert neue_reise_pruefen({"titel": "Ski", "von": "2027-02-06", "bis": "2027-02-13"}, None)[1].startswith(
        "Eine Reise anlegen geht nur mit einem persönlichen Konto-Link")
    assert reise_pfad("Island 2028 – Hochland", 2028) == "island-2028-hochland"
    assert len(reise_pfad("Eine sehr lange Reise durch viele Länder und Städte am Mittelmeer", 2027)) <= 40
