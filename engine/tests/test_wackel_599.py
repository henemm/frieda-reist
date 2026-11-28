"""Wackelige Browsertests unter Last (frieda-reist#599): Die Messskripte für Karte und Leiste warten auf den Zustand, an dem
die Seite reagiert hat, statt auf feste Zeiten. Nachgewiesen unter künstlicher Verzögerung (verzoegerung.mjs stellt eine
belastete Maschine nach): ResizeObserver, Zeitgeber und resize-Ereignisse der Seite kommen später. Ein echter Fehler bleibt rot.
Grundlage: Beispielreise und die Seite aus test_karte_popup_310.py (erfundene Koordinaten, Beispielwerte)."""
import contextlib
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
from conftest import meldet  # noqa: E402
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


@contextlib.contextmanager
def _server(tmp_path, seite_aendern=None):
    """Baut die Beispielreise in tmp_path und stellt sie bereit; seite_aendern ändert vorher die gebaute Seite (nur diese Kopie)."""
    ziel = tmp_path / "web" / "beispiel"
    bauen.bauen(WURZEL / "beispiel/reisen/beispielreise", ziel)
    if seite_aendern:
        seite = ziel / "index.html"
        seite.write_text(seite_aendern(seite.read_text(encoding="utf-8")), encoding="utf-8")

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(tmp_path / "web")))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{s.server_address[1]}/beispiel/"
    finally:
        s.shutdown()


def _rundgang(tmp_path, browser, verzoegern, skript=None, seite_aendern=None, frist=600, erwarte_ok=True):
    """Rundgang aus test_seite.py mit verzögerter Seite; zurück kommen seine Ausgabe und die gespeicherten Ansichten.
    Mit erwarte_ok=False ist ein Absturz (Rückgabecode ≠ 0) kein Testfehler, zurück kommt dann None (#697)."""
    with _server(tmp_path, seite_aendern) as basis:
        aus = subprocess.run(["node", str(skript or HIER / "seiten_browser.mjs"), str(VERZOEGERUNG), basis, str(tmp_path / "dom.json")],
                             capture_output=True, text=True, timeout=frist,
                             env={**os.environ, "RH_BROWSER": browser, "RH_PLAYWRIGHT_ECHT": str(PLAYWRIGHT),
                                  "RH_VERZOEGERN": json.dumps(verzoegern)})
    if not erwarte_ok and aus.returncode != 0:
        return None
    assert aus.returncode == 0, aus.stderr[-2000:]
    return json.loads(aus.stdout.strip().splitlines()[-1]), json.loads((tmp_path / "dom.json").read_text(encoding="utf-8"))


def _leiste(tmp_path, browser, verzoegern, skript=None, erwarte_ok=True):
    """Nur die Höhen der Leiste (App und Browser) aus dem Rundgang; None, wenn der Rundgang abgestürzt ist (erwarte_ok=False)."""
    aus = _rundgang(tmp_path, browser, verzoegern, skript, erwarte_ok=erwarte_ok)
    return None if aus is None else aus[0]["leiste"]


def _v01_stimmt(v01):
    """Dieselben Erwartungen wie test_seite.py::test_alle_ansichten_der_beispielreise an die Ansicht der Wahlstelle V-01."""
    return bool(meldet(v01, "seite.vergleich.setzt_voraus_label") and meldet(v01, "seite.vergleich.schliesst_aus_label")
                and "(im Plan)" in v01
                and re.search(r'class="(mk-w )?mk-luecke"[^>]*>Lücke am Anfang: Altendorf → Bad Schandau<', v01))


def _gehe_quelle():
    """Der Helfer gehe(p, h) aus dem Rundgang, wie er dort steht."""
    m = re.search(r"^(?:async function gehe\(p, h\)|const gehe = async \(p, h\) =>) \{(.|\n)*?^\};?$",
                  (HIER / "seiten_browser.mjs").read_text(encoding="utf-8"), re.M)
    assert m, "gehe(p, h) fehlt in seiten_browser.mjs"
    return m.group(0)


def _leiste_stimmt(leiste):
    """Dieselben Erwartungen wie test_seite.py::test_alle_ansichten_der_beispielreise; ein abgestürzter Rundgang (None) stimmt nie."""
    if leiste is None:
        return False
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
    assert not _leiste_stimmt(_leiste(tmp_path / "zeitgeber", browser, {"zeitgeber": 700}, alt, erwarte_ok=False))
    assert not _leiste_stimmt(_leiste(tmp_path / "resize", browser, {"resize": 1500}, alt, erwarte_ok=False))


@pytest.mark.skipif(not shutil.which("node"), reason="node fehlt")
def test_absturz_des_alten_ablaufs_zaehlt_als_rot(tmp_path):
    """#697: Stürzt der alte Rundgang unter Last ab (Rückgabecode ≠ 0), zählt das als nicht stimmende Leiste, ohne dass der
    Test scheitert; der neue Ablauf (Standard) bleibt bei einem Absturz rot. Ersatzskript statt Browser."""
    skript = tmp_path / "absturz.mjs"
    skript.write_text("process.stderr.write(\"TypeError: null is not an object (evaluating 'box.parentElement')\\n\");\n"
                      "process.exit(1);\n", encoding="utf-8")
    assert _leiste_stimmt(_leiste(tmp_path / "a", "webkit", {}, skript, erwarte_ok=False)) is False
    with pytest.raises(AssertionError):
        _leiste(tmp_path / "b", "webkit", {}, skript)


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


@browsertest
@BROWSER
def test_rundgang_unter_verzoegertem_wechsel_auf_v03(tmp_path, browser):
    """#661, AC-1: Der Wechsel auf V-03 (letzte Route vor dem Vergleich bei 1300 px) kommt 200 ms später an; der Rundgang stürzt
    nicht ab und misst den Vergleich in der schmalen Spalte."""
    aus, _ = _rundgang(tmp_path, browser, {"hashchange": 200, "hash": "V-03"})
    assert aus["fehler"] == []
    vergleich = aus["behaelter"]["spalte"]["vergleich"]
    assert vergleich["karten"] > 0 and vergleich["breite"] == 340, vergleich


@browsertest
@BROWSER
def test_rundgang_unter_verzoegertem_wechsel_auf_v01(tmp_path, browser):
    """#664, AC-2: Der Wechsel auf V-01 kommt 200 ms später an; gespeichert wird trotzdem V-01, nicht der vorige Tag."""
    _, dom = _rundgang(tmp_path, browser, {"hashchange": 200, "hash": "V-01"})
    assert _v01_stimmt(dom["1200#V-01"]), dom["1200#V-01"][:300]


@browsertest
@BROWSER
def test_echter_fehler_im_wechsel_bleibt_rot(tmp_path, browser):
    """AC-3: Die Seite wirft beim Wechsel auf E-02 und zeichnet V-01 nicht; das Warten verdeckt beides nicht und hängt nicht."""
    def kaputt(html):
        neu, n = re.subn(r'(addEventListener\("hashchange", \(\) => \{.*?)\broute\(\);',
                         r'\1if (location.hash === "#E-02") throw new Error("Wurf 661"); if (location.hash !== "#V-01") route();', html)
        assert n == 1, n
        return bauen.skripte_festlegen(neu)   # die Sicherheitsregel der Seite für das geänderte Skript neu festlegen

    aus, dom = _rundgang(tmp_path, browser, {}, seite_aendern=kaputt, frist=300)
    assert any("Wurf 661" in f for f in aus["fehler"]), aus["fehler"]
    assert not _v01_stimmt(dom["1200#V-01"])


@browsertest
@BROWSER
def test_gleicher_hash_haengt_nicht(tmp_path, browser):
    """AC-4: Wechsel ohne Änderung der Adresse (Startseite auf "", zweimal derselbe Hash) lösen kein hashchange aus; gehe kehrt
    trotzdem zurück, und die Seite zeigt die Ansicht."""
    skript = tmp_path / "gleich.mjs"
    skript.write_text("""const [, , modul, basis, browser] = process.argv;
const b = await (await import(modul))[browser].launch();
""" + _gehe_quelle() + """
const p = await (await b.newContext({serviceWorkers: "block"})).newPage();
await p.goto(basis);
await p.waitForSelector("#titel:not(:empty)");
const aus = [];
for (const h of ["", "V-01", "V-01"]) {
  let uhr;
  const fertig = await Promise.race([gehe(p, h).then(() => true), new Promise(r => { uhr = setTimeout(() => r(false), 5000); })]);
  clearTimeout(uhr);
  aus.push({fertig, html: await p.evaluate(() => document.querySelector("#main").outerHTML)});
}
await b.close();
console.log(JSON.stringify(aus));
""", encoding="utf-8")
    with _server(tmp_path) as basis:
        aus = subprocess.run(["node", str(skript), str(PLAYWRIGHT), basis, browser], capture_output=True, text=True, timeout=120)
    assert aus.returncode == 0, aus.stderr[-2000:]
    start, erst, zweit = json.loads(aus.stdout.strip().splitlines()[-1])
    assert start["fertig"] and erst["fertig"] and zweit["fertig"]
    assert _v01_stimmt(erst["html"]) and _v01_stimmt(zweit["html"]) and not _v01_stimmt(start["html"])


def test_quelltext_wechsel_ueber_gehe():
    """AC-5 (statisch): Nur gehe setzt location.hash; nach einem Wechsel wartet der Rundgang nicht mehr fest 15 ms."""
    q = (HIER / "seiten_browser.mjs").read_text(encoding="utf-8")
    gehe = _gehe_quelle()
    assert "location.hash =" in gehe and "location.hash =" not in q.replace(gehe, "")
    assert "waitForTimeout(15)" not in q
    assert "hashchange" in gehe and gehe.index("hashchange") < gehe.index("location.hash =")
    assert gehe.count("requestAnimationFrame") == 2
    assert len(re.findall(r"await gehe\(p, h\)", q)) == 4
