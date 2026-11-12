"""Startfehler-Meldung statt leerem Bildschirm (frieda-reist#387, Rest; Spec docs/specs/oberflaeche/startfehler-meldung-387.md).

Bricht das Skript der Seite beim Start ab, zeigt die Seite eine Meldung mit dem Knopf „Neu laden“ (#startfehler). Fehler nach dem
Start bleiben unbeachtet. Alle Tests nutzen die beiden Beispielreisen (erfunden); die Browsertests brauchen Playwright."""
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
import texte  # noqa: E402
from playwright_pfad import PLAYWRIGHT  # noqa: E402

WURZEL = Path(__file__).resolve().parents[2]
BEISPIELE = WURZEL / "beispiel" / "reisen"
VORLAGE = (WURZEL / "engine" / "vorlage.html").read_text(encoding="utf-8")
SKRIPT = Path(__file__).parent / "seiten_startfehler_387.mjs"
REISEN = ["beispielreise", "stadtwochenende"]
SCHLUESSEL = ("seite.fehler.start_titel", "seite.fehler.start_neu_laden")
PLATZHALTER = "/*__STARTFEHLER__*/null"
HAUPT = "const D = "
browser = pytest.mark.skipif(not PLAYWRIGHT.exists() or not shutil.which("node"), reason="Playwright fehlt")


def gebaut(tmp_path, reise, name="r"):
    bauen.bauen(BEISPIELE / reise, tmp_path / "web" / name)
    return tmp_path / "web" / name / "index.html"


def kaputt(index, einsatz):
    """Setzt `einsatz` unmittelbar vor das Hauptskript (vor `const D`), also nach dem Fänger."""
    html = index.read_text(encoding="utf-8")
    assert html.count(HAUPT) == 1
    index.write_text(bauen.skripte_festlegen(html.replace(HAUPT, einsatz + HAUPT, 1)), encoding="utf-8")   # Prüfsummen der Skripte neu


def lauf(tmp_path, modus):
    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(tmp_path / "web")))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    try:
        aus = subprocess.run(["node", str(SKRIPT), str(PLAYWRIGHT), f"http://127.0.0.1:{s.server_address[1]}/r/", modus],
                             capture_output=True, text=True, timeout=120, env={**os.environ, "RH_BROWSER": "chromium"})
    finally:
        s.shutdown()
    assert aus.returncode == 0, aus.stderr[-2000:]
    return json.loads(aus.stdout.strip().splitlines()[-1])


def titel_und_knopf(kuerzel):
    t = texte.sprache(kuerzel).TEXTE
    return t["seite.fehler.start_titel"], t["seite.fehler.start_neu_laden"]


# ---------- Test 1 (AC-1 bis AC-3): erzwungener Startfehler ----------

@browser
@pytest.mark.parametrize("reise", REISEN)
@pytest.mark.parametrize("fehler", ["throw new Error('Startfehler-Test');", "}}} ", "Promise.reject(new Error('Versprechen'));"],
                         ids=["laufzeitfehler", "syntaxfehler", "abgelehntes-versprechen"])
def test_startfehler_zeigt_meldung_mit_knopf(tmp_path, reise, fehler):
    kaputt(gebaut(tmp_path, reise), fehler)
    m = lauf(tmp_path, "start")["vorher"]
    assert m["da"], "keine Meldung #startfehler"
    assert m["anzahl"] == 1
    assert m["rolle"] == "alert"
    assert m["sichtbar"] and m["imFenster"], m
    titel, knopf = titel_und_knopf(m["lang"] or "de")
    assert titel in m["text"] and m["knopf"] == knopf, m


@browser
@pytest.mark.parametrize("reise", REISEN)
def test_knopf_laedt_neu(tmp_path, reise):
    kaputt(gebaut(tmp_path, reise), "throw new Error('Startfehler-Test');")
    assert lauf(tmp_path, "start")["neuGeladen"] is True


@browser
def test_sprache_der_reise_und_rueckfall(tmp_path):
    """Englisch in <html lang>: englischer Text; unbekannte Sprache: Text der ersten Sprache des Ausschnitts."""
    index = gebaut(tmp_path, "stadtwochenende")
    kaputt(index, "throw new Error('x');")
    html = index.read_text(encoding="utf-8")
    erste = next(iter(texte.SPRACHEN))
    for neu, erwartet in (("en", "en"), ("zz", erste)):
        index.write_text(re.sub(r'(<html[^>]*\blang=")[^"]*', rf"\g<1>{neu}", html, count=1), encoding="utf-8")
        m = lauf(tmp_path, "start")["vorher"]
        titel, knopf = titel_und_knopf(erwartet)
        assert titel in m["text"] and m["knopf"] == knopf, (neu, m)


# ---------- Test 2 (AC-4): gesunde Seite, Fehler nach dem Start ----------

@browser
@pytest.mark.parametrize("reise", REISEN)
def test_gesunde_seite_und_spaete_fehler_zeigen_keine_meldung(tmp_path, reise):
    gebaut(tmp_path, reise)
    e = lauf(tmp_path, "spaet")
    assert e["vorher"]["da"] is False
    assert e["nachher"]["da"] is False, "Fehler nach dem Start dürfen keine Meldung zeigen"


# ---------- Test 3 (AC-5): Fänger ----------

def faenger():
    m = re.search(r"<script>(?:(?!</script>).)*?window\.__startFertig(?:(?!</script>).)*?</script>", VORLAGE, re.S)
    assert m, "kein Fänger-Skript mit __startFertig in der Vorlage"
    assert m.start() < VORLAGE.index(HAUPT), "der Fänger muss vor dem Hauptskript stehen"
    return re.sub(r"/\*(?!__STARTFEHLER__).*?\*/|//[^\n]*", "", m.group(0), flags=re.S)


def test_faenger_greift_nicht_auf_das_hauptskript_zu():
    f = faenger()
    for verboten in (r"\bD\b", r"\bTEXTE\b", r"\bT\(", r"\bel\("):
        assert not re.search(verboten, f), verboten
    assert "createElement" in f and "textContent" in f
    assert "innerHTML" not in f
    assert "try" in f and "catch" in f
    assert PLATZHALTER in f


def test_hauptskript_setzt_startmarke_als_letzte_anweisung():
    haupt = VORLAGE[VORLAGE.index(HAUPT):VORLAGE.rindex("</script>")].rstrip()
    assert re.search(r"window\.__startFertig = true;\s*$", haupt), haupt[-200:]


@browser
def test_faenger_wirft_selbst_nichts_bei_syntaxfehler(tmp_path):
    kaputt(gebaut(tmp_path, "beispielreise"), "}}} ")
    aus = lauf(tmp_path, "start")
    assert aus["vorher"]["da"] and aus["vorher"]["anzahl"] == 1


# ---------- Test 4 (AC-7): Katalog ----------

def test_schluessel_in_jeder_sprache(monkeypatch):
    monkeypatch.setenv("FR_TEXTE_ZUSATZ", "xx")
    monkeypatch.syspath_prepend(str(Path(__file__).parent))
    assert "xx" in texte.SPRACHEN
    for k in texte.SPRACHEN:
        katalog = texte.sprache(k).TEXTE
        for s in SCHLUESSEL:
            assert katalog.get(s, "").strip(), (k, s)


# ---------- Test 6 (AC-6): Platzhalter und Ausschnitt ----------

def test_platzhalter_ersetzt_und_ausschnitt_hat_alle_sprachen(tmp_path):
    assert VORLAGE.count(PLATZHALTER) == 1
    for reise in REISEN:
        html = gebaut(tmp_path, reise, reise).read_text(encoding="utf-8")
        assert "/*__STARTFEHLER__*/" not in html
        for kuerzel in texte.SPRACHEN:
            for text in titel_und_knopf(kuerzel):
                assert bauen.js_einbetten(json.dumps(text, ensure_ascii=False)[1:-1]) in html, (reise, kuerzel)


@pytest.mark.parametrize("aenderung", [PLATZHALTER + ";" + PLATZHALTER, "null"], ids=["zweimal", "fehlt"])
def test_platzhalter_nicht_genau_einmal_ist_baufehler(tmp_path, monkeypatch, aenderung):
    echt = Path.read_text

    def lesen(self, *a, **k):
        text = echt(self, *a, **k)
        return text.replace(PLATZHALTER, aenderung, 1) if self.name == "vorlage.html" else text

    monkeypatch.setattr(Path, "read_text", lesen)
    with pytest.raises(bauen.BauFehler):
        bauen.bauen(BEISPIELE / "beispielreise", tmp_path / "web" / "r")
