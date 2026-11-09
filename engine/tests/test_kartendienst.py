"""Tests für den eigenen Kartendienst (Overpass bei Bedarf, #444; Spec docs/specs/betrieb/eigener-kartendienst-444.md).

Ohne Docker und ohne echtes Netz: zwei lokale Stummel-Server auf 127.0.0.1 (eigen über FR_KARTENDIENST, öffentlich über
FR_OVERPASS), abdeckung.json in einem Testordner mit erfundenen Rahmen, für die Fristen eine ersetzte Uhr.

Was diese Tests als Schnittstelle festlegen (über die Spec hinaus, Entscheidung in der RED-Phase):
  kartendienst.TEILFRIST_EIGEN = 10
  kartendienst.eigener_dienst() -> Adresse aus FR_KARTENDIENST oder None (leer zählt als nicht gesetzt)
  kartendienst.abdeckung(ordner) -> [(süd, west, nord, ost), ...]; ordner None oder kaputte Datei -> [] (nie eine Ausnahme)
  kartendienst.rahmen_abgedeckt(rahmen, abdeckung) -> bool
  kartendienst.rahmen_aus_abfrage(abfrage) -> (süd, west, nord, ost) um alle Rahmen der Abfrage, ohne Rahmen None
  kartendienst.dienst_waehlen(rahmen) -> ("eigen", Adresse) oder ("oeffentlich", Adresse)
  kartendienst.stempeln(antwort, dienst) -> Antwort mit "dienst" und "stand" (osm3s.timestamp_osm_base oder None)
  schreiben.overpass_holen(abfrage, frist, rahmen=None): ohne rahmen wird er aus der Abfrage gelesen
      (rahmen_aus_abfrage); so bleiben die Aufrufer und alle bestehenden Ersatzfunktionen (q, frist) unverändert.
  Gestempelt wird nur, wenn FR_KARTENDIENST gesetzt ist; ohne die Einstellung ist die Antwort genau die des Dienstes (AC-1).
  Netzzugriffe nur über urllib.request.urlopen, zur Laufzeit nachgeschlagen (wie bisher in overpass_holen).
"""
import json
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import schreiben as sb  # noqa: E402

ABFRAGE = '[out:json];(nwr["amenity"="drinking_water"](50.9,14.0,51.0,14.1););out center tags;'
RAHMEN = (50.9, 14.0, 51.0, 14.1)
STAND = "2026-10-01T12:00:00Z"
TREFFER = {"type": "node", "id": 1, "lat": 50.96, "lon": 14.07, "tags": {"amenity": "drinking_water", "name": "Brunnen (erfunden)"}}


def kd():
    import kartendienst
    return kartendienst


class Stummel:
    """Lokaler Overpass-Ersatz: antwortet nacheinander mit den Einträgen von `antworten`:
    200 (Treffer mit Stand), "leer" (gültig, keine Treffer), "kein_json", ein anderer HTTP-Code oder ("haengen", s)."""

    def __init__(self, antworten):
        self.antworten, self.anfragen = list(antworten), []
        st = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_POST(self):
                self.rfile.read(int(self.headers.get("Content-Length") or 0))
                st.anfragen.append(time.monotonic())
                art = st.antworten.pop(0) if st.antworten else 200
                if isinstance(art, tuple):
                    time.sleep(art[1])
                    art = 200
                code, koerper = 200, json.dumps({"osm3s": {"timestamp_osm_base": STAND}, "elements": [TREFFER]})
                if art == "leer":
                    koerper = json.dumps({"osm3s": {"timestamp_osm_base": STAND}, "elements": []})
                elif art == "kein_json":
                    koerper = "<html>kein json</html>"
                elif art != 200:
                    code, koerper = art, "fehler"
                try:
                    self.send_response(code)
                    self.send_header("Content-Length", str(len(koerper.encode())))
                    self.end_headers()
                    self.wfile.write(koerper.encode())
                except OSError:
                    pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.server.daemon_threads = True
        self.adresse = f"http://127.0.0.1:{self.server.server_address[1]}/api/interpreter"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def schliessen(self):
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def dienste(monkeypatch, tmp_path):
    """-> starten(eigen=[...], oeffentlich=[...], rahmen=[[s, w, n, o], ...] oder Text der abdeckung.json) -> (eigen, öffentlich)."""
    offen = []

    def starten(eigen=(), oeffentlich=(), rahmen=((50.0, 13.0, 52.0, 15.0),), datei=None):
        e, o = Stummel(eigen), Stummel(oeffentlich)
        offen.extend((e, o))
        ordner = tmp_path / "kartendienst"
        ordner.mkdir(exist_ok=True)
        text = datei if datei is not None else json.dumps({"stand": STAND, "regionen_pruefsumme": "abc",
                                                           "rahmen": [list(r) for r in rahmen]})
        (ordner / "abdeckung.json").write_text(text, encoding="utf-8")
        monkeypatch.setenv("FR_KARTENDIENST", e.adresse)
        monkeypatch.setenv("FR_KARTENDIENST_ORDNER", str(ordner))
        monkeypatch.setenv("FR_OVERPASS", o.adresse)
        return e, o
    yield starten
    for s in offen:
        s.schliessen()


# ---------- Bausteine des Moduls ----------

def test_rahmen_aus_abfrage():
    assert kd().rahmen_aus_abfrage(ABFRAGE) == RAHMEN
    zwei = '[out:json];(nwr["a"="b"](50.9,14.0,51.0,14.1);nwr["c"](50.8,14.05,50.95,14.2););out center tags;'
    assert kd().rahmen_aus_abfrage(zwei) == (50.8, 14.0, 51.0, 14.2)
    assert kd().rahmen_aus_abfrage('[out:json];node(id:1);out;') is None


@pytest.mark.parametrize("abdeckung, erwartet", [
    ([(50.0, 13.0, 52.0, 15.0)], True),
    ([RAHMEN], True),                                               # Rand zählt als innen
    ([(50.95, 13.0, 52.0, 15.0)], False),                           # ragt über den Rand
    ([(50.0, 13.0, 50.95, 15.0), (50.95, 13.0, 52.0, 15.0)], False),  # über zwei Regionen verteilt
    ([(10.0, 10.0, 11.0, 11.0), (50.0, 13.0, 52.0, 15.0)], True),
    ([], False),
])
def test_rahmen_abgedeckt(abdeckung, erwartet):
    assert kd().rahmen_abgedeckt(RAHMEN, abdeckung) is erwartet


@pytest.mark.parametrize("text", [None, "", "{nicht json", "[]", '{"rahmen": []}', '{"stand": "x"}', '{"rahmen": [["a", "b", "c", "d"]]}',
                                  '{"rahmen": [[52.0, 15.0, 50.0, 13.0]]}', '{"rahmen": [[50, 13, 52]]}', '{"rahmen": "50,13,52,15"}'])
def test_abdeckung_kaputt_ist_leer(tmp_path, text):
    if text is not None:
        (tmp_path / "abdeckung.json").write_text(text, encoding="utf-8")
    assert kd().abdeckung(tmp_path) == []
    assert kd().abdeckung(None) == []


def test_abdeckung_liest_rahmen(tmp_path):
    (tmp_path / "abdeckung.json").write_text(json.dumps({"stand": STAND, "rahmen": [[42.4, 1.4, 42.7, 1.8], [50, 13, 52, 15]]}))
    assert kd().abdeckung(tmp_path) == [(42.4, 1.4, 42.7, 1.8), (50.0, 13.0, 52.0, 15.0)]


def test_dienst_waehlen_und_stempeln(dienste, monkeypatch):
    e, o = dienste()
    assert kd().eigener_dienst() == e.adresse
    assert kd().dienst_waehlen(RAHMEN) == ("eigen", e.adresse)
    assert kd().dienst_waehlen((10.0, 10.0, 11.0, 11.0)) == ("oeffentlich", o.adresse)
    assert kd().dienst_waehlen(None) == ("oeffentlich", o.adresse)
    gestempelt = kd().stempeln({"osm3s": {"timestamp_osm_base": STAND}, "elements": []}, "eigen")
    assert gestempelt["dienst"] == "eigen" and gestempelt["stand"] == STAND and gestempelt["elements"] == []
    assert kd().stempeln({"elements": []}, "oeffentlich")["stand"] is None
    monkeypatch.setenv("FR_KARTENDIENST", "")
    assert kd().eigener_dienst() is None


# ---------- AC-1 bis AC-6: Abrufweg ----------

def test_ohne_einstellung_wie_bisher(dienste, monkeypatch):
    """AC-1: Ohne FR_KARTENDIENST geht jede Abfrage nur an FR_OVERPASS; die Antwort ist unverändert (kein Stempel)."""
    e, o = dienste()
    monkeypatch.delenv("FR_KARTENDIENST")
    antwort = sb.overpass_holen(ABFRAGE, 20)
    assert antwort == {"osm3s": {"timestamp_osm_base": STAND}, "elements": [TREFFER]}
    assert len(o.anfragen) == 1 and e.anfragen == []


def test_innerhalb_der_abdeckung_fragt_eigenen_dienst(dienste):
    """AC-2: Rahmen ganz in der Abdeckung (auch genau auf dem Rand): eigener Dienst, Stempel eigen mit Stand, öffentlich nie."""
    for rahmen in ([(50.0, 13.0, 52.0, 15.0)], [RAHMEN]):
        e, o = dienste(rahmen=rahmen)
        antwort = sb.overpass_holen(ABFRAGE, 20)
        assert antwort["dienst"] == "eigen" and antwort["stand"] == STAND and antwort["elements"] == [TREFFER]
        assert len(e.anfragen) == 1 and o.anfragen == []
    e, o = dienste(rahmen=[(10.0, 10.0, 11.0, 11.0)])
    assert sb.overpass_holen(ABFRAGE, 20, rahmen=(10.2, 10.2, 10.4, 10.4))["dienst"] == "eigen"   # übergebener Rahmen gilt


@pytest.mark.parametrize("rahmen", [
    [(10.0, 10.0, 11.0, 11.0)],                                    # ganz außerhalb
    [(50.95, 13.0, 52.0, 15.0)],                                   # ragt über den Rand
    [(50.0, 13.0, 50.95, 15.0), (50.95, 13.0, 52.0, 15.0)],        # über zwei Regionen
])
def test_ausserhalb_geht_an_oeffentlichen_dienst(dienste, rahmen):
    """AC-3"""
    e, o = dienste(rahmen=rahmen)
    antwort = sb.overpass_holen(ABFRAGE, 20)
    assert antwort["dienst"] == "oeffentlich" and antwort["stand"] == STAND
    assert e.anfragen == [] and len(o.anfragen) == 1


@pytest.mark.parametrize("datei", ["", "{nicht json", '{"stand": "x"}', '{"rahmen": [["a", "b", "c", "d"]]}',
                                   '{"rahmen": [[52.0, 15.0, 50.0, 13.0]]}', "ohne_ordner", "ohne_datei"])
def test_kaputte_abdeckung_geht_an_oeffentlichen_dienst(dienste, monkeypatch, datei):
    """AC-4"""
    e, o = dienste(datei="" if datei.startswith("ohne") else datei)
    if datei == "ohne_ordner":
        monkeypatch.delenv("FR_KARTENDIENST_ORDNER")
    if datei == "ohne_datei":
        (Path(sb.instanz.wert("FR_KARTENDIENST_ORDNER", "")) / "abdeckung.json").unlink()
    antwort = sb.overpass_holen(ABFRAGE, 20)
    assert antwort["dienst"] == "oeffentlich" and e.anfragen == [] and len(o.anfragen) == 1


def test_leere_antwort_innerhalb_abdeckung_gilt(dienste):
    """AC-5"""
    e, o = dienste(eigen=["leer"])
    antwort = sb.overpass_holen(ABFRAGE, 20)
    assert antwort["elements"] == [] and antwort["dienst"] == "eigen"
    assert len(e.anfragen) == 1 and o.anfragen == []


@pytest.mark.parametrize("fehler", [500, 502, "kein_json", "unerreichbar"])
def test_fehler_des_eigenen_dienstes_faellt_zurueck(dienste, monkeypatch, fehler):
    """AC-6: Fehler des eigenen Dienstes -> öffentlicher Dienst (ohne Wiederholung beim eigenen); scheitert auch er,
    die bisherige Ablehnung."""
    monkeypatch.setattr(sb, "OSM_PAUSE", 0.05)
    e, o = dienste(eigen=[] if fehler == "unerreichbar" else [fehler, 200])
    if fehler == "unerreichbar":
        monkeypatch.setenv("FR_KARTENDIENST", "http://127.0.0.1:9/api/interpreter")
    antwort = sb.overpass_holen(ABFRAGE, 20)
    assert antwort["dienst"] == "oeffentlich" and len(o.anfragen) == 1
    assert len(e.anfragen) == (0 if fehler == "unerreichbar" else 1)
    e, o = dienste(eigen=[502], oeffentlich=[429, 429])
    with pytest.raises(sb.Ablehnung) as a:
        sb.overpass_holen(ABFRAGE, 20)
    assert a.value.schluessel == "schreiben.kartenpunkte.limit"
    e, o = dienste(eigen=[502], oeffentlich=[500])
    with pytest.raises(sb.Ablehnung) as a:
        sb.overpass_holen(ABFRAGE, 20)
    assert a.value.schluessel == "schreiben.kartenpunkte.dienst"


# ---------- AC-7: Teilfrist und Gesamtfrist mit ersetzter Uhr ----------

class Uhr:
    def __init__(self):
        self.jetzt = 1000.0

    def monotonic(self):
        return self.jetzt

    def sleep(self, s):
        self.jetzt += s


@pytest.mark.parametrize("frist_name", ["OSM_FRIST_VORAB", "OSM_ZEIT"])
def test_teilfrist_und_gesamtfrist(dienste, monkeypatch, frist_name):
    """AC-7: Hängt der eigene Dienst, wird er nach höchstens TEILFRIST_EIGEN aufgegeben; der öffentliche Dienst bekommt
    höchstens den Rest, die Summe bleibt in der Gesamtfrist. Die Uhr ist ersetzt, es wird nicht gewartet."""
    e, o = dienste()
    frist = getattr(sb, frist_name)
    uhr, zugriffe = Uhr(), []
    monkeypatch.setattr(time, "monotonic", uhr.monotonic)
    monkeypatch.setattr(time, "sleep", uhr.sleep)

    class Antwort:
        def __init__(self, daten):
            self.daten = daten

        def read(self, *a):
            return self.daten

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def urlopen(req, timeout=None):
        zugriffe.append((req.full_url, timeout))
        if req.full_url == e.adresse:
            uhr.jetzt += timeout          # hängt bis zum Ende seiner Frist
            raise TimeoutError("hängt")
        return Antwort(json.dumps({"osm3s": {"timestamp_osm_base": STAND}, "elements": []}).encode())
    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    start = uhr.jetzt
    antwort = sb.overpass_holen(ABFRAGE, frist)
    assert antwort["dienst"] == "oeffentlich", antwort
    assert [z[0] for z in zugriffe] == [e.adresse, o.adresse], zugriffe
    (_, t_eigen), (_, t_oeff) = zugriffe
    assert 0 < t_eigen <= min(kd().TEILFRIST_EIGEN, frist)
    assert 0 < t_oeff <= frist - t_eigen + 1e-6
    assert t_eigen + t_oeff <= frist + 1e-6 and uhr.jetzt - start <= frist + 1e-6
