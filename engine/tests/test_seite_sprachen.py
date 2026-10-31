"""Sprache der Seite im Browser (ADR-0006): Start in der Sprache der Reise, Umschalter, Wahl überlebt das Neuladen, Zurückschalten
ergibt dieselbe Ansicht. Die Pseudo-Sprache xx (andere Ziffern, rtl, sechs Pluralkategorien) beweist, dass eine dritte Sprache
nur eine Datei ist."""
import functools
import http.server
import json
import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bauen  # noqa: E402
import texte  # noqa: E402
from playwright_pfad import PLAYWRIGHT  # noqa: E402

WURZEL = Path(__file__).resolve().parent.parent.parent
BEISPIEL = WURZEL / "beispiel/reisen/beispielreise"
ohne_browser = pytest.mark.skipif(not PLAYWRIGHT.exists() or not shutil.which("node"), reason="Playwright fehlt")


def seite_bauen(tmp_path, sprache=None):
    """Baut eine Kopie der Beispielreise (mit gesetzter Sprache) und gibt den Ordner zurück, den ein Server ausliefert."""
    reise = tmp_path / "quelle" / "beispielreise"
    shutil.copytree(BEISPIEL, reise)
    if sprache:
        yaml = reise / "reise.yaml"
        text = yaml.read_text(encoding="utf-8")
        yaml.write_text(text.replace("pfad: beispielreise\n", f"pfad: beispielreise\nsprache: {sprache}\n") if "sprache:" not in text
                        else text.replace("sprache: de", f"sprache: {sprache}"), encoding="utf-8")
    ziel = tmp_path / "web" / "beispiel"
    bauen.bauen(reise, ziel)
    return tmp_path / "web"


def im_browser(web, zielsprache, browser="chromium"):
    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(web)))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    try:
        aus = subprocess.run(["node", str(Path(__file__).parent / "sprachen_browser.mjs"), str(PLAYWRIGHT),
                              f"http://127.0.0.1:{s.server_address[1]}/beispiel/", zielsprache],
                             capture_output=True, text=True, timeout=120, env={**os.environ, "RH_BROWSER": browser})
    finally:
        s.shutdown()
    assert aus.returncode == 0, aus.stderr[-2000:]
    return json.loads(aus.stdout.strip().splitlines()[-1])


def test_seite_traegt_sprache_und_katalog(tmp_path):
    web = seite_bauen(tmp_path)
    html = (web / "beispiel" / "index.html").read_text(encoding="utf-8")
    assert '<html lang="de" dir="ltr">' in html and "/*__TEXTE__*/" not in html
    manifest = json.loads((web / "beispiel" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["lang"] == "de"
    daten = json.loads((web / "beispiel" / "daten.json").read_text(encoding="utf-8"))
    assert daten["reise"]["sprache"] == "de"


def test_reise_in_englisch_baut_mit_englischer_huelle(tmp_path):
    web = seite_bauen(tmp_path, "en")
    html = (web / "beispiel" / "index.html").read_text(encoding="utf-8")
    assert '<html lang="en" dir="ltr">' in html
    assert json.loads((web / "beispiel" / "manifest.json").read_text(encoding="utf-8"))["lang"] == "en"


def test_unbekannte_sprache_ist_ein_baufehler(tmp_path):
    with pytest.raises(bauen.BauFehler) as e:
        seite_bauen(tmp_path, "klingonisch")
    assert "sprache: unbekannt" in str(e.value.args[0])


@ohne_browser
@pytest.mark.parametrize("browser", ["chromium", "webkit"])
def test_umschalten_auf_englisch_und_zurueck(tmp_path, browser):
    e = im_browser(seite_bauen(tmp_path), "en", browser)
    assert e["fehler"] == []
    assert e["start"]["lang"] == "de" and e["start"]["gewaehlt"] == "gewählt" and e["start"]["wochentag"] == "Do"
    assert [k[0] for k in e["start"]["knoepfe"]] == ["de", "en"]
    assert [k[2] for k in e["start"]["knoepfe"]] == ["true", "false"]
    assert e["umgeschaltet"]["lang"] == "en" and e["umgeschaltet"]["locale"] == "en-GB"
    assert e["umgeschaltet"]["gewaehlt"] == "chosen" and e["umgeschaltet"]["erledigt"] == "done"
    assert e["umgeschaltet"]["wochentag"] == "Thu"
    assert [k[2] for k in e["umgeschaltet"]["knoepfe"]] == ["false", "true"]
    # Deutsch wörtlich wie bisher; Englisch mit Datum, Zahl, Dauer und Plural der Sprache (M2)
    s, u = e["start"], e["umgeschaltet"]
    assert (s["datum"], s["datumFern"], s["zahl"], s["km"], s["dauer"], s["zeit"]) == ("Do 13.5.", "2.1.2031", "1.234,5", "12,4", "2:05 h", "18:05")
    assert s["tage"] == ["1 Tag", "2 Tage", "3 Tage", "11 Tage"]
    assert (u["datum"], u["datumFern"], u["zahl"], u["km"], u["dauer"], u["zeit"]) == ("Thu 13/5", "2/1/2031", "1,234.5", "12.4", "2:05 h", "18:05")
    assert u["tage"] == ["1 day", "2 days", "3 days", "11 days"] and u["sortiert"] == [-1, -1]
    assert e["anders"]                                   # die Ansicht wurde neu gezeichnet
    assert e["nachNeuladen"]["lang"] == "en" and e["nachNeuladen"]["gewaehlt"] == "chosen"   # die Wahl bleibt
    assert e["zurueck"]["lang"] == "de" and e["zurueck"]["gewaehlt"] == "gewählt"
    assert e["gleichNachZurueck"]                        # Deutsch zeichnet wieder genau wie vorher


@ohne_browser
@pytest.mark.parametrize("browser", ["chromium", "webkit"])
def test_pseudo_sprache_dritter_knopf_und_rtl(tmp_path, monkeypatch, browser):
    monkeypatch.setenv("FR_TEXTE_ZUSATZ", "xx")
    assert "xx" in texte.SPRACHEN
    e = im_browser(seite_bauen(tmp_path), "xx", browser)
    assert e["fehler"] == []
    assert [k[0] for k in e["start"]["knoepfe"]] == ["de", "en", "xx"]   # ein Knopf je Sprache des Katalogs
    assert e["umgeschaltet"]["lang"] == "xx" and e["umgeschaltet"]["dir"] == "rtl" and e["umgeschaltet"]["locale"] == "ar-EG"
    assert e["umgeschaltet"]["gewaehlt"] == "[xx chosen]"
    # andere Ziffern der Locale (ar-EG), Pluralkategorie few für 3 und many für 11 aus der Regel der Sprache, nicht aus dem Code
    u = e["umgeschaltet"]
    assert u["zeit"] == "١٨:٠٥" and u["dauer"].startswith("[xx ٢:٠٥") and u["zahl"] == "١٬٢٣٤٫٥", u
    assert u["tage"][2].startswith("[xx few ") and u["tage"][3].startswith("[xx many ") and u["tage"][1].startswith("[xx two ")
    assert e["zurueck"]["dir"] == "ltr" and e["gleichNachZurueck"]


def rundgang(web, sprache, browser="chromium"):
    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(web)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        aus = subprocess.run(["node", str(Path(__file__).parent / "sprachen_rundgang.mjs"), str(PLAYWRIGHT),
                              f"http://127.0.0.1:{srv.server_address[1]}/beispiel/", sprache],
                             capture_output=True, text=True, timeout=900, env={**os.environ, "RH_BROWSER": browser})
    finally:
        srv.shutdown()
    assert aus.returncode == 0, aus.stderr[-2000:]
    return json.loads(aus.stdout.strip().splitlines()[-1])


@ohne_browser
def test_rundgang_pseudo_sprache_alles_im_katalog_und_umschalten_ist_vollstaendig(tmp_path, monkeypatch):
    """Jede Ansicht in der Pseudo-Sprache: kein Text bleibt deutsch (jeder Text außer dem Inhalt der Reise trägt die Marke),
    und Umschalten ergibt dieselbe Ansicht wie ein Start in der Sprache (nichts bleibt vom Start stehen)."""
    monkeypatch.setenv("FR_TEXTE_ZUSATZ", "xx")
    e = rundgang(seite_bauen(tmp_path), "xx")
    if os.environ.get("RH_DUMP"):   # zur Durchsicht: alle Funde in eine Datei
        Path(os.environ["RH_DUMP"]).write_text(json.dumps(e, ensure_ascii=False), encoding="utf-8")
    assert e["fehler"] == [] and e["routen"] > 60
    assert e["stale"] == {}, dict(list(e["stale"].items())[:6])
    assert e["marke"] == {}, dict(list(e["marke"].items())[:10])
