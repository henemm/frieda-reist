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
import re
import socket
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
    200 (Treffer mit Stand), "leer" (gültig, keine Treffer), "kein_json", "ohne_elements" (gültiges JSON ohne Liste
    „elements“), ein anderer HTTP-Code oder ("haengen", s)."""

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
                elif art == "ohne_elements":
                    koerper = json.dumps({"osm3s": {"timestamp_osm_base": STAND}, "remark": "ohne elements (erfunden)"})
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


# ---------- Gegenprüfung #444: abgebrochene Antworten und Umkreis ----------

class Kaputt:
    """Stummel, der eine kaputte HTTP-Antwort sendet: "statuszeile" (Müll statt HTTP/1.x) oder "abgeschnitten"
    (Content-Length größer als der gesendete Körper, dann Verbindung zu)."""

    def __init__(self, art):
        self.anfragen, self.art = [], art
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(5)
        self.adresse = f"http://127.0.0.1:{self.sock.getsockname()[1]}/api/interpreter"
        self.faden = threading.Thread(target=self.laufen, daemon=True)
        self.faden.start()

    def laufen(self):
        while True:
            try:
                verbindung, _ = self.sock.accept()
            except OSError:
                return
            with verbindung:
                daten = b""
                while b"\r\n\r\n" not in daten:      # ganze Anfrage lesen, sonst setzt der Abbau die Verbindung zurück
                    teil = verbindung.recv(65536)
                    if not teil:                    # Gegenseite hat ohne (ganze) Anfrage geschlossen (#567)
                        break
                    daten += teil
                if b"\r\n\r\n" not in daten:
                    continue
                kopf, _, koerper = daten.partition(b"\r\n\r\n")
                laenge = int(re.search(rb"(?i)content-length:\s*(\d+)", kopf).group(1))
                while len(koerper) < laenge:
                    teil = verbindung.recv(65536)
                    if not teil:
                        break
                    koerper += teil
                if len(koerper) < laenge:
                    continue
                self.anfragen.append(time.monotonic())
                if self.art == "statuszeile":
                    verbindung.sendall(b"KAPUTT\r\n\r\n")
                else:
                    verbindung.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 5000\r\nConnection: close\r\n\r\n{\"elements\": [")
                verbindung.shutdown(socket.SHUT_WR)

    def schliessen(self):
        """#567: shutdown() weckt einen Faden, der in accept() wartet (close() allein tut das unter Linux nicht)."""
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self.sock.close()
        self.faden.join(timeout=3)


@pytest.mark.parametrize("art", ["statuszeile", "abgeschnitten"])
def test_kaputte_antwort_des_eigenen_dienstes_faellt_zurueck(dienste, monkeypatch, art):
    """F001 (AC-6): Bricht der eigene Dienst eine Antwort ab (http.client.HTTPException), antwortet der öffentliche Dienst."""
    e, o = dienste()
    k = Kaputt(art)
    try:
        monkeypatch.setenv("FR_KARTENDIENST", k.adresse)
        antwort = sb.overpass_holen(ABFRAGE, 20)
        assert antwort["dienst"] == "oeffentlich" and len(o.anfragen) == 1 and len(k.anfragen) == 1
    finally:
        k.schliessen()


@pytest.mark.parametrize("art", ["statuszeile", "abgeschnitten"])
def test_kaputte_antwort_des_oeffentlichen_dienstes_wird_abgelehnt(dienste, monkeypatch, art):
    """F001: Bricht der öffentliche Dienst eine Antwort ab, kommt die bisherige Ablehnung statt einer Ausnahme, mit und ohne
    eigenen Dienst."""
    k = Kaputt(art)
    try:
        for eigen in (True, False):
            dienste(eigen=[502])
            monkeypatch.setenv("FR_OVERPASS", k.adresse)
            if not eigen:
                monkeypatch.delenv("FR_KARTENDIENST")
            with pytest.raises(sb.Ablehnung) as a:
                sb.overpass_holen(ABFRAGE, 20)
            assert a.value.schluessel == "schreiben.kartenpunkte.dienst"
    finally:
        k.schliessen()


# ---------- #567: Rückfall hinterlässt eine Protokollzeile, Stummel Kaputt endet sauber ----------

def zeilen_eigener_dienst(capfd):
    """-> Zeilen auf stderr über den eigenen Kartendienst (Protokoll des Rückfalls, #567)."""
    return [z for z in capfd.readouterr().err.splitlines() if "Own map service" in z]


def pruefe_zeile(zeilen, adressen):
    assert len(zeilen) == 1, zeilen
    zeile = zeilen[0]
    assert zeile.endswith("falling back to public"), zeile
    assert len(zeile) <= sb.LOG_LAENGE + len("Own map service failed (), falling back to public"), zeile
    assert "\r" not in zeile and "\t" not in zeile and "  " not in zeile, repr(zeile)
    for adresse in adressen:
        assert adresse not in zeile and "127.0.0.1" not in zeile, zeile
    return zeile


@pytest.mark.parametrize("art", ["statuszeile", "abgeschnitten"])
def test_rueckfall_fehlerantwort_schreibt_protokollzeile(dienste, monkeypatch, capfd, art):
    """AC-1 (#567): Antwortet der eigene Dienst kaputt, steht genau eine Zeile mit Fehlerart auf stderr; Rückfall wie bisher."""
    e, o = dienste()
    k = Kaputt(art)
    try:
        monkeypatch.setenv("FR_KARTENDIENST", k.adresse)
        capfd.readouterr()
        antwort = sb.overpass_holen(ABFRAGE, 20)
        assert antwort["dienst"] == "oeffentlich" and len(o.anfragen) == 1
        zeile = pruefe_zeile(zeilen_eigener_dienst(capfd), [k.adresse, e.adresse, o.adresse])
        assert re.fullmatch(r"Own map service failed \(\w+: .*\), falling back to public", zeile), zeile
    finally:
        k.schliessen()


@pytest.mark.parametrize("fehler", [500, "kein_json"])
def test_rueckfall_http_fehler_und_kein_json_schreibt_protokollzeile(dienste, monkeypatch, capfd, fehler):
    """AC-1 (#567): HTTP-Fehler und Nicht-JSON des eigenen Dienstes hinterlassen ebenfalls genau eine Zeile mit Fehlerart."""
    e, o = dienste(eigen=[fehler])
    capfd.readouterr()
    assert sb.overpass_holen(ABFRAGE, 20)["dienst"] == "oeffentlich"
    zeile = pruefe_zeile(zeilen_eigener_dienst(capfd), [e.adresse, o.adresse])
    erwartet = "HTTPError" if fehler == 500 else "JSONDecodeError"
    assert zeile.startswith(f"Own map service failed ({erwartet}: "), zeile


def test_rueckfall_nicht_erreichbar_schreibt_protokollzeile(dienste, monkeypatch, capfd):
    """AC-1 (#567): Ist der eigene Dienst nicht erreichbar, steht genau eine Zeile mit Fehlerart auf stderr."""
    e, o = dienste()
    unerreichbar = "http://127.0.0.1:9/api/interpreter"
    monkeypatch.setenv("FR_KARTENDIENST", unerreichbar)
    capfd.readouterr()
    assert sb.overpass_holen(ABFRAGE, 20)["dienst"] == "oeffentlich"
    zeile = pruefe_zeile(zeilen_eigener_dienst(capfd), [unerreichbar, o.adresse])
    assert re.fullmatch(r"Own map service failed \(\w+: .*\), falling back to public", zeile), zeile


def test_rueckfall_ohne_elements_schreibt_protokollzeile(dienste, capfd):
    """AC-2 (#567): Gültige Antwort ohne Liste „elements“ -> genau diese Zeile, Rückfall wie bisher."""
    e, o = dienste(eigen=["ohne_elements"])
    capfd.readouterr()
    antwort = sb.overpass_holen(ABFRAGE, 20)
    assert antwort["dienst"] == "oeffentlich" and len(e.anfragen) == 1 and len(o.anfragen) == 1
    assert zeilen_eigener_dienst(capfd) == ["Own map service answered without elements, falling back to public"]


# ---------- #573: Erfolg hinterlässt eine Zeile, Präfix ist der Vertrag mit monitor.sh ----------

VERTRAGSPRAEFIX = "Own map service"   # monitor.sh der Infrastruktur (check_frieda_kartendienst_bereit) liest genau dieses Präfix


@pytest.mark.parametrize("art, anzahl", [(200, 1), ("leer", 0)])
def test_erfolg_schreibt_erfolgszeile(dienste, capfd, art, anzahl):
    """AC-1 (#573, ersetzt AC-3 aus #567): Antwortet der eigene Dienst gültig (auch ohne Treffer), steht genau die Zeile
    „Own map service answered (<n> elements)“ auf stderr, einzeilig und ohne Adresse; Rückgabe wie bisher."""
    e, o = dienste(eigen=[art])
    capfd.readouterr()
    antwort = sb.overpass_holen(ABFRAGE, 20)
    assert antwort["dienst"] == "eigen" and len(antwort["elements"]) == anzahl
    assert len(e.anfragen) == 1 and o.anfragen == []
    zeilen = zeilen_eigener_dienst(capfd)
    assert zeilen == [f"Own map service answered ({anzahl} elements)"], zeilen
    assert e.adresse not in zeilen[0] and "127.0.0.1" not in zeilen[0]


@pytest.mark.parametrize("weg", ["fehler", "ohne_elements", "erfolg"])
def test_protokollzeilen_beginnen_mit_vertragspraefix(dienste, capfd, weg):
    """AC-2 (#573): Jeder der drei Wege hinterlässt genau eine Zeile über den eigenen Dienst, und sie beginnt mit dem
    Vertragspräfix; Rückgabe und Rückfall wie bisher. Ein Kommentar an overpass_eigen benennt das Präfix als Vertrag."""
    eigen = {"fehler": [500], "ohne_elements": ["ohne_elements"], "erfolg": [200]}[weg]
    e, o = dienste(eigen=eigen)
    capfd.readouterr()
    antwort = sb.overpass_holen(ABFRAGE, 20)
    assert antwort["dienst"] == ("eigen" if weg == "erfolg" else "oeffentlich")
    assert len(o.anfragen) == (0 if weg == "erfolg" else 1)
    zeilen = [z for z in capfd.readouterr().err.splitlines() if "map service" in z.lower()]
    assert len(zeilen) == 1 and zeilen[0].startswith(VERTRAGSPRAEFIX), zeilen
    import inspect
    quelle = inspect.getsource(sb.overpass_eigen)
    assert "monitor.sh" in quelle and VERTRAGSPRAEFIX in quelle, "Kommentar zum Vertrag mit monitor.sh fehlt"


def faeden_von(start):
    """-> Fäden, die `start()` neu anlegt (der Stummel merkt sich seinen Faden nicht; so prüft der Test von außen)."""
    vorher = set(threading.enumerate())
    objekt = start()
    return objekt, [f for f in threading.enumerate() if f not in vorher]


@pytest.mark.parametrize("fall", ["wartet_in_accept", "leere_verbindung"])
def test_kaputt_beendet_faden_nach_schliessen(fall):
    """AC-4 (#567): Nach schliessen() läuft kein Faden des Stummels Kaputt mehr: weder einer, der in accept() wartet, noch
    einer, dessen Gegenseite ohne Anfrage schließt (recv() == b"")."""
    k, faeden = faeden_von(lambda: Kaputt("statuszeile"))
    assert len(faeden) == 1, faeden
    if fall == "leere_verbindung":
        with socket.create_connection(("127.0.0.1", int(k.adresse.split(":")[2].split("/")[0])), timeout=2):
            pass
    time.sleep(0.2)                                 # der Faden wartet jetzt in accept() bzw. liest die leere Verbindung
    start = time.monotonic()
    k.schliessen()
    faeden[0].join(timeout=3)
    assert not faeden[0].is_alive(), f"Faden des Stummels läuft nach schliessen() weiter ({fall})"
    assert time.monotonic() - start < 5


def test_umkreis_geht_an_oeffentlichen_dienst(dienste):
    """F002 (AC-3): Eine Abfrage mit Umkreis (around) hat keinen bekannten Rahmen und geht an den öffentlichen Dienst."""
    umkreis = '[out:json];(nwr["amenity"="drinking_water"](around:500,50.95,14.05););out center tags;'
    gemischt = '[out:json];(nwr["a"="b"](50.9,14.0,51.0,14.1);nwr["c"](around:500,50.95,14.05););out center tags;'
    assert kd().rahmen_aus_abfrage(umkreis) is None and kd().rahmen_aus_abfrage(gemischt) is None
    e, o = dienste()
    assert sb.overpass_holen(umkreis, 20)["dienst"] == "oeffentlich"
    assert e.anfragen == [] and len(o.anfragen) == 1


# ---------- #552, AC-10: Kartendienst unter eigenem Benutzer ----------

def test_kartendienst_ohne_dienstbenutzer(tmp_path):
    """Docker läuft nur unter <instanz>-karte; ExecStart und EnvironmentFile liegen weder im Repo noch in Ordnern des
    Dienstbenutzers; das Aktualisieren führt ein root-eigenes, beim Einrichten erzeugtes Skript aus."""
    import os
    import subprocess
    betrieb = Path(__file__).resolve().parents[2] / "betrieb"
    ziel = tmp_path / "soll"
    dienst = tmp_path / "dienst"
    env = {**{k: v for k, v in os.environ.items() if not k.startswith(("FR_", "RM_", "KN_", "EI_"))},
           "FR_WURZEL": str(tmp_path), "FR_INSTANZ": "probe", "FR_TITEL": "Probe", "FR_BENUTZER": "hans", "FR_GRUPPE": "hans",
           "FR_HOME": "/home/hans", "FR_DIENST": str(dienst), "EI_ZIEL": str(ziel),
           "FR_KARTENDIENST_REGIONEN": "europe/andorra", "FR_KARTENDIENST_ORDNER": "/srv/probe/kartendienst"}
    r = subprocess.run(["bash", str(betrieb / "einrichten.sh"), "--erzeugen"], env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    einheiten = {p.name: p.read_text(encoding="utf-8") for p in (ziel / "kartendienst").iterdir()}
    dienstbenutzer_ordner = (str(tmp_path), "/home/hans", str(dienst))
    for name, text in einheiten.items():
        assert "User=hans" not in text, name
        for zeile in text.splitlines():
            if zeile.startswith(("ExecStart=", "ExecStartPre=", "ExecStartPost=", "ExecStop=", "EnvironmentFile=")):
                programm = zeile.split("=", 1)[1].lstrip("-").split()[0]
                assert not any(o in programm for o in dienstbenutzer_ordner), (name, zeile)
    assert "User=probe-karte" in einheiten["probe-kartendienst.service"]
    akt = einheiten["probe-kartendienst-aktualisieren.service"]
    assert re.search(r"^ExecStart=/usr/local/sbin/probe-kartendienst aktualisieren$", akt, re.M), akt
    assert "EnvironmentFile" not in akt



# ---------- #552, Entscheidung 10: Daten im Zustandsordner des Karte-Benutzers ----------

def test_kartendienst_daten_im_zustandsordner(tmp_path):
    """Das Karte-Skript arbeitet in /var/lib/<instanz>-kartendienst/daten; der Zustandsordner ist für Konnektor und Docker
    lesbar (0755); einrichten.sh legt ihn an und zieht vorhandene Daten mit kartendienst-umzug.sh um (Verweis am alten Ort)."""
    import os
    import subprocess
    betrieb = Path(__file__).resolve().parents[2] / "betrieb"
    ziel = tmp_path / "soll"
    env = {**{k: v for k, v in os.environ.items() if not k.startswith(("FR_", "RM_", "KN_", "EI_"))},
           "FR_WURZEL": str(tmp_path), "FR_INSTANZ": "probe", "FR_TITEL": "Probe", "FR_BENUTZER": "hans", "FR_GRUPPE": "hans",
           "FR_HOME": "/home/hans", "EI_ZIEL": str(ziel), "EI_SYSTEMD": str(tmp_path / "systemd"),
           "FR_KARTENDIENST_REGIONEN": "europe/andorra", "FR_KARTENDIENST_ORDNER": "/srv/probe/kartendienst"}
    r = subprocess.run(["bash", str(betrieb / "einrichten.sh"), "--erzeugen"], env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    karte = (ziel / "sbin" / "probe-kartendienst").read_text(encoding="utf-8")
    assert "\nFR_KARTENDIENST_ORDNER=/var/lib/probe-kartendienst/daten\n" in karte
    akt = (ziel / "kartendienst" / "probe-kartendienst-aktualisieren.service").read_text(encoding="utf-8")
    assert "StateDirectory=probe-kartendienst" in akt and "StateDirectoryMode=0755" in akt
    aus = subprocess.run(["bash", str(betrieb / "einrichten.sh")], env=env, capture_output=True, text=True).stdout
    assert "sudo install -d -o probe-karte -g probe-karte -m 755 /var/lib/probe-kartendienst" in aus, aus
    assert f"sudo bash {betrieb}/kartendienst-umzug.sh /srv/probe/kartendienst /var/lib/probe-kartendienst probe-karte" in aus
    assert not re.search(r"install -d [^\n]*/srv/probe/kartendienst", aus), aus
    assert "must belong to probe-karte" not in aus


def test_kartendienst_unit_bindet_den_zustandsordner_ein(tmp_path):
    """Gegenprüfung F001: Der Container (Docker als root) bindet den festen Zustandsordner ein, nie FR_KARTENDIENST_ORDNER.
    Der Verweis liegt in einem Ordner des Dienstbenutzers; ersetzt er ihn (etwa durch /), bände Docker sonst das Ziel
    beschreibbar ein."""
    import os
    import subprocess
    betrieb = Path(__file__).resolve().parents[2] / "betrieb"
    ziel = tmp_path / "soll"
    env = {**{k: v for k, v in os.environ.items() if not k.startswith(("FR_", "RM_", "KN_", "EI_"))},
           "FR_WURZEL": str(tmp_path), "FR_INSTANZ": "probe", "FR_TITEL": "Probe", "FR_BENUTZER": "hans", "FR_GRUPPE": "hans",
           "FR_HOME": "/home/hans", "EI_ZIEL": str(ziel),
           "FR_KARTENDIENST_REGIONEN": "europe/andorra", "FR_KARTENDIENST_ORDNER": "/srv/probe/kartendienst"}
    r = subprocess.run(["bash", str(betrieb / "einrichten.sh"), "--erzeugen"], env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    for p in (ziel / "kartendienst").iterdir():
        assert "/srv/probe/kartendienst" not in p.read_text(encoding="utf-8"), p.name
    assert "/srv/probe/kartendienst" not in (ziel / "sbin" / "probe-kartendienst").read_text(encoding="utf-8")
    unit = (ziel / "kartendienst" / "probe-kartendienst.service").read_text(encoding="utf-8")
    assert "ExecStartPre=/usr/bin/test -f /var/lib/probe-kartendienst/daten/init_done\n" in unit, unit
    assert " -v /var/lib/probe-kartendienst/daten:/db " in unit, unit
