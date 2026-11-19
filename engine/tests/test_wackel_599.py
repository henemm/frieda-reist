"""Wackelige Browsertests unter Last (frieda-reist#599): Die Messskripte für Karte und Leiste warten auf den Zustand, an dem
die Seite reagiert hat, statt auf feste Zeiten. Nachgewiesen unter künstlicher Verzögerung (verzoegerung.mjs stellt eine
belastete Maschine nach): ResizeObserver, Zeitgeber und resize-Ereignisse der Seite kommen später. Ein echter Fehler bleibt rot.
Grundlage: Beispielreise und die Seite aus test_karte_popup_310.py (erfundene Koordinaten, Beispielwerte)."""
import functools
import http.server
import json
import os
import re
import shutil
import subprocess
import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import bauen  # noqa: E402
import test_karte_popup_310 as t310  # noqa: E402
from playwright_pfad import PLAYWRIGHT  # noqa: E402

HIER = Path(__file__).resolve().parent
WURZEL = HIER.parent.parent
VERZOEGERUNG = HIER / "verzoegerung.mjs"
STAND_VOR_599 = "5f36075"   # letzter Stand von main mit dem alten Ablauf (feste 600 ms, innerHeight, 500 ms Node-Zeit)
browsertest = pytest.mark.skipif(not PLAYWRIGHT.exists() or not shutil.which("node"), reason="Playwright fehlt")
BROWSER = pytest.mark.parametrize("browser", ["chromium", "webkit"])


def _karte(tmp_path, browser, monkeypatch, verzoegern, skript=None):
    """Seite und Ablauf aus test_karte_popup_310, aber mit verzögerter Seite (und auf Wunsch einem anderen Messskript)."""
    echt = subprocess.run

    def run(args, **kw):
        args = list(args)
        if args[1].endswith("seiten_karte_popup.mjs"):
            args[2] = str(VERZOEGERUNG)
            if skript:
                args[1] = str(skript)
            kw["env"] = {**kw["env"], "RH_PLAYWRIGHT_ECHT": str(PLAYWRIGHT), "RH_VERZOEGERN": json.dumps(verzoegern)}
        return echt(args, **kw)

    monkeypatch.setattr(t310.subprocess, "run", run)
    return t310._seite(tmp_path, browser)


def _leiste(tmp_path, browser, verzoegern, skript=None):
    """Rundgang aus test_seite.py mit verzögerter Seite; zurück kommen nur die Höhen der Leiste (App und Browser)."""
    ziel = tmp_path / "web" / "beispiel"
    bauen.bauen(WURZEL / "beispiel/reisen/beispielreise", ziel)

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(tmp_path / "web")))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    try:
        aus = subprocess.run(["node", str(skript or HIER / "seiten_browser.mjs"), str(VERZOEGERUNG),
                              f"http://127.0.0.1:{s.server_address[1]}/beispiel/"],
                             capture_output=True, text=True, timeout=600,
                             env={**os.environ, "RH_BROWSER": browser, "RH_PLAYWRIGHT_ECHT": str(PLAYWRIGHT),
                                  "RH_VERZOEGERN": json.dumps(verzoegern)})
    finally:
        s.shutdown()
    assert aus.returncode == 0, aus.stderr[-2000:]
    return json.loads(aus.stdout.strip().splitlines()[-1])["leiste"]


def _leiste_stimmt(leiste):
    """Dieselben Erwartungen wie test_seite.py::test_alle_ansichten_der_beispielreise."""
    a, w = leiste["app"], leiste["browser"]
    return (a["start"] == a["klein"] == a["zu"] == a["voll"] == a["luege"] == 788 and a["tippt"] == 488
            and w == {"start": 788, "klein": 488, "tippt": 488, "zu": 488, "voll": 788, "luege": 788})


def _ansicht_stimmt(a):
    """Dieselben Erwartungen wie test_karte_popup_310 an die Ansicht, dazu: nicht der Höchstzoom einer 0-Pixel-Karte."""
    return a["punkte"] == 2 and a["alle"] and a["spanne"][0] < 0.05 and a["spanne"][1] < 0.05 and a["zoom"] < 18


def _alter_stand(tmp_path, datei):
    """Messskript im Stand vor #599 (aus der Geschichte); fehlt sie (flacher Checkout in CI), wird übersprungen."""
    r = subprocess.run(["git", "-C", str(WURZEL), "show", f"{STAND_VOR_599}:engine/tests/{datei}"], capture_output=True, text=True)
    if r.returncode != 0:
        pytest.skip(f"Stand {STAND_VOR_599} nicht im Checkout")
    alt = tmp_path / "alt"
    alt.mkdir(exist_ok=True)
    shutil.copy(HIER / "bild.mjs", alt / "bild.mjs")
    (alt / datei).write_text(r.stdout, encoding="utf-8")
    return alt / datei


@browsertest
@BROWSER
def test_karte_unter_verzoegertem_resizeobserver(tmp_path, browser, monkeypatch):
    """AC-1: Der ResizeObserver der Karte meldet sich erst 1,5 s später; gemessen wird trotzdem der fertige Ausschnitt."""
    aus = _karte(tmp_path, browser, monkeypatch, {"resizeobserver": 1500})
    for breite in ("390", "1300"):
        assert _ansicht_stimmt(aus[breite]["ansicht"]), (breite, aus[breite]["ansicht"])


@browsertest
@BROWSER
def test_leiste_unter_verzoegertem_zeitgeber(tmp_path, browser):
    """AC-2: setTimeout der Seite läuft 700 ms später; nach dem Verlassen des Suchfelds wird erst nach der Messung der Vorlage
    gemessen."""
    leiste = _leiste(tmp_path, browser, {"zeitgeber": 700})
    assert _leiste_stimmt(leiste), leiste


@browsertest
@BROWSER
def test_leiste_unter_verzoegertem_resize(tmp_path, browser):
    """AC-3: resize-Ereignisse kommen 1,5 s später an; nach einer Größenänderung wird erst nach dem Ereignis gemessen."""
    leiste = _leiste(tmp_path, browser, {"resize": 1500})
    assert _leiste_stimmt(leiste), leiste


@browsertest
@pytest.mark.parametrize("browser", ["webkit"])
def test_alter_ablauf_ist_unter_verzoegerung_rot(tmp_path, browser, monkeypatch):
    """AC-4: Der alte Ablauf scheitert unter derselben Verzögerung; der Nachweis trifft also die Wackelstelle."""
    aus = _karte(tmp_path / "karte", browser, monkeypatch, {"resizeobserver": 1500}, _alter_stand(tmp_path, "seiten_karte_popup.mjs"))
    assert not all(_ansicht_stimmt(aus[b]["ansicht"]) for b in ("390", "1300")), aus
    alt = _alter_stand(tmp_path, "seiten_browser.mjs")
    assert not _leiste_stimmt(_leiste(tmp_path / "zeitgeber", browser, {"zeitgeber": 700}, alt))
    assert not _leiste_stimmt(_leiste(tmp_path / "resize", browser, {"resize": 1500}, alt))


@browsertest
@pytest.mark.parametrize("browser", ["webkit"])
def test_echter_fehler_bleibt_rot(tmp_path, browser, monkeypatch):
    """AC-5: Erreicht die Karte nach der Wahl der Ansicht ihren Ausschnitt nie (der ResizeObserver der neu gebauten Karte meldet
    sich erst nach 60 s), misst das Skript nach Ablauf seiner Frist trotzdem und meldet den echten Wert; die Prüfung aus
    test_karte_popup_310 ist dann rot."""
    aus = _karte(tmp_path, browser, monkeypatch, {"resizeobserver": 60000, "ab": ".kartenansichten button"})
    for breite in ("390", "1300"):
        a = aus[breite]["ansicht"]
        assert not a["alle"], (breite, a)


def test_quelltext_wartet_auf_zustand():
    """AC-7 (statisch): Die Karte wartet nicht mehr fest 600 ms, sondern auf einen Zustand mit Frist und weiter bei Ablauf;
    die Leiste hängt vor der Größenänderung einen resize-Hörer ein und wartet nach dem Verlassen des Felds nicht in Node-Zeit."""
    karte = (HIER / "seiten_karte_popup.mjs").read_text(encoding="utf-8")
    nach_ansicht = karte.split(".kartenansichten button", 1)[1]
    assert "waitForTimeout(600)" not in nach_ansicht
    warten = re.search(r"waitForFunction\((.|\n)*?timeout(.|\n)*?\.catch\(", nach_ansicht)
    assert warten, "nach dem Klick auf die Ansicht fehlt waitForFunction mit Frist und .catch"
    assert "KARTE" in warten.group(0) and "_animatingZoom" in warten.group(0), warten.group(0)

    leiste = (HIER / "seiten_browser.mjs").read_text(encoding="utf-8")
    hoehe = re.search(r"const hoehe = async h => \{(.|\n)*?\n  \};", leiste)
    assert hoehe, "hoehe() nicht gefunden"
    rumpf = hoehe.group(0)
    assert "resize" in rumpf and rumpf.index("resize") < rumpf.index("setViewportSize"), rumpf
    nach_blur = leiste.split(".blur()", 1)[1].split("m.zu =", 1)[0]
    assert "waitForTimeout" not in nach_blur, nach_blur
    assert "setTimeout" in nach_blur, nach_blur
