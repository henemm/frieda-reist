"""Service-Worker-Test „vergisst gelöschtes Bild“ (frieda-reist#654, Spec docs/specs/betrieb/wackelige-browsertests-654.md):
Wiederholt wird nur der Anstoß des Updates, nie die Prüfung. Nachgewiesen mit eingespielten Fehlern (sw.js abgebrochen,
gleiche Änderungszeit) und mit Gegenproben: Ein echter Fehler des Produkts bleibt rot und nennt seinen Grund.
Ablauf und Prüfung sind dieselben wie in test_bilder_eigen.py (_sw_ablauf, _sw_pruefen). Nur erfundene Daten."""
import shutil
import sys
import urllib.error
import urllib.request
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import bauen  # noqa: E402
import test_bilder_eigen as tbe  # noqa: E402

BROWSER = pytest.mark.parametrize("browser", ["chromium", "webkit"])
AUFRUF = "    await bilderVergessen(alt);\n"
INSTALL = 'self.addEventListener("install", event => {\n'
VIELE = 10 ** 6   # „dauerhaft“


@pytest.fixture(scope="module")
def gebaut(tmp_path_factory):
    """Alter Stand (mit BI-90) und neuer Stand (BI-90 entfernt), einmal gebaut."""
    tbe._browser_bereit()
    ordner = tmp_path_factory.mktemp("gebaut")
    bauen.bauen(tbe._quelle(ordner), ordner / "web" / "beispiel")
    bauen.bauen(tbe._quelle(ordner, entfernt=True), ordner / "web-neu" / "beispiel")
    return ordner


@pytest.fixture
def staende(gebaut, tmp_path):
    """Eigene Kopie der beiden Stände: Der Ablauf überschreibt den alten, die Gegenproben ändern den neuen."""
    for name in ("web", "web-neu"):
        shutil.copytree(gebaut / name, tmp_path / name)
    return tmp_path / "web", tmp_path / "web-neu"


def _server(web, **fehler):
    return tbe._Server(web, neuer_stand_von=web / "beispiel", **fehler)


def _ersetzen(neu_web, alt, neu):
    """Ersetzt einen Text in sw.js der gebauten Kopie und belegt, dass er genau einmal da war."""
    p = neu_web / "beispiel" / "sw.js"
    roh = p.read_text(encoding="utf-8")
    assert roh.count(alt) == 1, f"nicht genau einmal in sw.js: {alt!r}"
    p.write_text(roh.replace(alt, neu), encoding="utf-8")


def _rot(e, server):
    with pytest.raises(AssertionError) as grund:
        tbe._sw_pruefen(e, server)
    return str(grund.value)


def _abgebrochen_gruen(staende, browser, anzahl):
    web, neu_web = staende
    with _server(web, abbrechen=anzahl) as s:
        e = tbe._sw_ablauf(s, web, neu_web, browser)
        tbe._sw_pruefen(e, s)
        assert s.anfragen("sw.js").count("abgebrochen") == anzahl, s.anfragen("sw.js")   # der Fehler wurde eingespielt
    return e


@BROWSER
def test_sw_einmal_abgebrochen_gruen(staende, browser):
    """AC-1: ein abgebrochener Abruf von sw.js macht den Test nicht rot; jeder gescheiterte Anstoß steht in der Ausgabe. (Unter
    Last kann der eigene Abruf des Browsers nach dem Laden den Abbruch verbrauchen, dann gelingt schon der erste Anstoß; dass
    Fehler gesammelt werden, belegen auch die drei Abbrüche und der dauerhafte.)"""
    e = _abgebrochen_gruen(staende, browser, 1)
    assert len(e["updateFehler"]) <= 1 and e["anstoesse"] == len(e["updateFehler"]) + 1, e


@BROWSER
def test_sw_mehrfach_abgebrochen_gruen(staende, browser):
    """AC-2: auch drei abgebrochene Abrufe nicht, innerhalb der Frist von 20 s."""
    e = _abgebrochen_gruen(staende, browser, 3)
    assert e["updateFehler"] and e["anstoesse"] > 1 and e["dauerMs"] < 20000, e


@BROWSER
def test_sw_gleiche_aenderungszeit_gruen(staende, browser):
    """AC-3: trägt die neue sw.js die Änderungszeit der alten, antwortet der Testserver trotzdem nie mit 304."""
    web, neu_web = staende
    datei = web / "beispiel" / "sw.js"
    zeit, inhalt = datei.stat().st_mtime_ns, datei.read_bytes()
    with _server(web, zeit_behalten=True) as s:
        e = tbe._sw_ablauf(s, web, neu_web, browser)
        assert datei.stat().st_mtime_ns == zeit and datei.read_bytes() != inhalt   # der Fehler wurde eingespielt
        assert 304 not in [status for _, status in s.protokoll], (s.anfragen("sw.js"), e)
        tbe._sw_pruefen(e, s)


@BROWSER
def test_sw_dauerhaft_abgebrochen_rot_mit_grund(staende, browser):
    """AC-4: Kommt der neue Worker nie, ist der Test rot (nicht übersprungen) und nennt Fehler, Zustände und Anfragen."""
    web, neu_web = staende
    with _server(web, abbrechen=VIELE) as s:
        e = tbe._sw_ablauf(s, web, neu_web, browser, frist_ms=3000)
        grund = _rot(e, s)
    assert "kein wartender neuer Worker" in grund and "Bild noch im Speicher" in grund, grund
    assert e.get("updateFehler") and all(e["updateFehler"]) and repr(e["updateFehler"]) in grund, grund
    assert len(e["updateFehler"]) == e["anstoesse"] > 1, e
    assert e["zustaende"]["nachher"] == e["zustaende"]["vorher"] and repr(e["zustaende"]) in grund, grund
    assert "Anfragen an sw.js: [200" in grund and "'abgebrochen'" in grund, grund
    assert e["dauerMs"] < 10000, e   # die Frist begrenzt hart


@BROWSER
def test_sw_ohne_bilder_vergessen_rot(staende, browser):
    """AC-5, Gegenprobe Produktfehler: vergisst der neue Worker das Bild nicht, bleibt der Test rot, und nur deshalb."""
    web, neu_web = staende
    _ersetzen(neu_web, AUFRUF, "")
    with _server(web) as s:
        e = tbe._sw_ablauf(s, web, neu_web, browser)
        grund = _rot(e, s)
    assert e["nachher"] > 0 and grund.startswith("Bild noch im Speicher |"), grund


@BROWSER
def test_sw_sofortige_uebernahme_rot(staende, browser):
    """AC-6, Gegenprobe Übernahme: activate löscht den alten Speicher; das allein erfüllt die Prüfung nicht. Die Seite lädt
    bei der Übernahme neu, das Messskript gibt trotzdem sein Ergebnis aus."""
    web, neu_web = staende
    _ersetzen(neu_web, AUFRUF, "")
    _ersetzen(neu_web, INSTALL, INSTALL + "  self.skipWaiting();\n")
    with _server(web) as s:
        e = tbe._sw_ablauf(s, web, neu_web, browser)
        grund = _rot(e, s)
    assert e["fehler"] == [] and e["vorher"] > 0 and e["nachher"] == 0, e
    assert grund.startswith("kein wartender neuer Worker; alter Worker nicht mehr aktiv |"), grund
    nach, vor = e["zustaende"]["nachher"], e["zustaende"]["vorher"]
    assert not nach["waiting"] and nach["active"] and nach["active"] != vor["active"], e


def test_server_queue_nocache_kein_304(tmp_path):
    """AC-7: Testserver wie im Betrieb (no-cache), mit langer Warteschlange und immer dem aktuellen Inhalt."""
    (tmp_path / "sw.js").write_text("// Beispielwert\n", encoding="utf-8")
    with tbe._Server(tmp_path) as s:
        with urllib.request.urlopen(s.basis + "/sw.js") as r:
            kopf = r.headers
        anfrage = urllib.request.Request(s.basis + "/sw.js", headers={"If-Modified-Since": kopf["Last-Modified"]})
        try:
            with urllib.request.urlopen(anfrage) as r:
                status, inhalt = r.status, r.read()
        except urllib.error.HTTPError as f:
            status, inhalt = f.code, b""
        assert (status, inhalt) == (200, b"// Beispielwert\n")
        assert kopf["Cache-Control"] == "no-cache"
        assert s.s.request_queue_size == 128
        assert s.anfragen("sw.js") == [200, 200]
