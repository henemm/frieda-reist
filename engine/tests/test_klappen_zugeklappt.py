"""Klappen starten zu, ein Pfeil für die ganze Seite (#632, Product Owner 23.11.2026): Beim Laden ist jede Klappe der Seite zu,
offen ist nur der Kern der Ansicht (das gemerkte Tageskapitel, die Packliste wie #511, das Wunschformular mit angefangenem
Entwurf). Pfeil nach rechts heißt zu, Pfeil nach unten heißt offen, bei Kapiteln und allen übrigen Klappen gleich. Sprünge
(Adresse, „zu buchen“, Suche) öffnen weiter alle umgebenden Klappen. Geprüft an beiden Beispielreisen."""
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
from playwright_pfad import PLAYWRIGHT  # noqa: E402

WURZEL = Path(__file__).resolve().parent.parent.parent
REISEN = ["beispielreise", "stadtwochenende"]
RECHTS, UNTEN = 0, 90


@functools.lru_cache(maxsize=None)
def _rundgang(reise, ordner):
    web = Path(ordner) / "web"
    bauen.bauen(WURZEL / "beispiel/reisen" / reise, web / reise)

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(web)))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    try:
        aus = subprocess.run(["node", str(Path(__file__).parent / "klappen_browser.mjs"), str(PLAYWRIGHT),
                              f"http://127.0.0.1:{s.server_address[1]}/{reise}/"],
                             capture_output=True, text=True, timeout=600, env={**os.environ, "RH_BROWSER": "chromium"})
    finally:
        s.shutdown()
    assert aus.returncode == 0, aus.stderr[-2000:]
    return json.loads(aus.stdout.strip().splitlines()[-1])


@pytest.fixture(scope="module", params=REISEN)
def rundgang(request, tmp_path_factory):
    if not PLAYWRIGHT.exists() or not shutil.which("node"):
        pytest.skip("Playwright fehlt")
    e = _rundgang(request.param, str(tmp_path_factory.mktemp(request.param)))
    assert e["fehler"] == [], e["fehler"]
    return request.param, e


def test_beim_laden_ist_ausser_dem_kern_nichts_offen(rundgang):
    """AC-1: Jede Ansicht frisch geladen: keine Klappe offen außer Packliste (gemerktes Kapitel und Entwurf gibt es ohne
    gemerkten Zustand nicht)."""
    reise, e = rundgang
    assert len(e["ansichten"]) > 3, e["ansichten"]
    assert e["regelwidrig"] == {}, (reise, e["regelwidrig"])


def test_pfeil_rechts_heisst_zu_unten_heisst_offen(rundgang):
    """AC-2: Kapitel und übrige Klappen zeigen zu nach rechts und offen nach unten."""
    reise, e = rundgang
    pico = e["pfeil"]["pico"]
    assert pico == {"zu": RECHTS, "offen": UNTEN}, (reise, pico)
    if reise == "beispielreise":   # Tageskapitel gibt es nur an einer Reise mit Hintergrund am Tag
        assert e["pfeil"]["kapitel"] == {"zu": RECHTS, "offen": UNTEN}, (reise, e["pfeil"])
    if e["pfeil"]["kapitel"]:
        assert e["pfeil"]["kapitel"] == pico, (reise, e["pfeil"])


def test_einzelheiten_starten_zu_auch_ungebucht(rundgang):
    """AC-3: Einzelheiten eines Dings und einer Buchung sind beim Laden zu, gebucht oder nicht; daneben bleibt etwas sichtbar
    (Name, Stand, Frist, Preis, Buchen-Handlung stehen außerhalb)."""
    reise, e = rundgang
    if reise == "beispielreise":
        assert any(not x["buchung"] for x in e["einzelheiten"]), e["einzelheiten"]   # Einzelheiten an einem Ding
        assert any(x["buchung"] for x in e["einzelheiten"]), e["einzelheiten"]       # und an einer Buchung
    assert [x for x in e["einzelheiten"] if x["offen"]] == [], (reise, [x for x in e["einzelheiten"] if x["offen"]])
    assert all(x["aussen"] for x in e["einzelheiten"]), (reise, [x for x in e["einzelheiten"] if not x["aussen"]])


def test_erster_abschnitt_eines_wissenstextes_zu(rundgang):
    """AC-4: Auch der erste Abschnitt eines Wissens- oder Recherchetextes ist beim Laden zu."""
    reise, e = rundgang
    if reise == "beispielreise":   # das Stadtwochenende hat keinen Wissenstext mit Abschnitten
        assert e["zaehler"]["bloecke"] > 0, e["zaehler"]
    assert [k for v in e["regelwidrig"].values() for k in v if k.startswith("details.block")] == [], (reise, e["regelwidrig"])


def test_andere_erwogene_plaene_zu(rundgang):
    """AC-5: „Andere erwogene Pläne“ ist beim Laden zu, auch wenn der gezeigte Plan nicht der feste ist."""
    reise, e = rundgang
    if reise == "beispielreise":
        assert e["zaehler"]["weg"] > 0, e["zaehler"]
        w = e["erwogen"]
        assert w and w["mitFest"] and w["mitFest"] + w["mitAnderem"] + w["alle"], w
        assert not any(w["mitFest"] + w["mitAnderem"] + w["alle"]), w   # gezeigt: der feste, ein anderer, alle Pläne
    assert [k for v in e["regelwidrig"].values() for k in v if k.startswith("details.weg")] == [], (reise, e["regelwidrig"])


def test_wunschformular_offen_nur_mit_entwurf(rundgang):
    """AC-6: Ohne Wunsch und ohne Entwurf ist das Wunschformular zu; mit angefangenem Entwurf offen."""
    reise, e = rundgang
    w = e["wunsch"]
    assert w["da"], (reise, w)
    assert w["ohne"] is False, (reise, w)
    assert w["mit"] is True, (reise, w)


def test_sprung_oeffnet_zugeklappte_klappen(rundgang):
    """AC-7: Ein Sprung per Adresse, „zu buchen“ oder Suche auf einen Eintrag in zugeklappten Klappen öffnet alle
    umgebenden, und das Ziel ist sichtbar."""
    reise, e = rundgang
    s = e["sprung"]
    if reise == "beispielreise":
        assert s.get("einzelheiten") == {"zu": [], "sichtbar": True}, s
        assert s.get("zu_buchen", {}).get("da") and s["zu_buchen"]["offen"], s
    for weg in ("hash", "suche"):
        if s.get(weg) is not None:
            assert s[weg]["offen"] and s[weg]["zu"] == [] and s[weg]["sichtbar"], (reise, weg, s)
    if reise == "beispielreise":
        assert s.get("hash") is not None and s.get("suche") is not None, s


def test_packliste_unveraendert_wie_511(rundgang):
    """AC-8: Die Packliste steht beim Laden auf ihrer Vorgabe (Planen: Tabellen offen; Packen: Gruppe offen, solange nicht
    alles Eigene gepackt ist)."""
    reise, e = rundgang
    for ansicht, x in e["packliste"].items():
        assert x["n"] > 0, (reise, ansicht, x)
        assert x["abweichend"] == [], (reise, ansicht, x)


ALT = ["offen bis zur Buchung", "Offen, solange noch gehandelt wird", "offen, solange noch gehandelt wird",
       "offen, solange gehandelt wird"]


def test_doku_nennt_die_neue_regel():
    """AC-9: Doku, Bausteinseite und Kopfkommentar der Vorlage nennen die neue Regel und die eine Pfeil-Konvention; die alte
    Regel „offen bis zur Buchung“ steht nirgends mehr."""
    design = (WURZEL / "docs/design.md").read_text(encoding="utf-8")
    vorlage = (WURZEL / "engine/vorlage.html").read_text(encoding="utf-8")
    for name, text in (("docs/design.md", design), ("engine/vorlage.html", vorlage)):
        gefunden = [a for a in ALT if a in text]
        assert gefunden == [], (name, gefunden)
    assert "beim Laden zu" in design and "offen nur der Kern" in design, "Regel fehlt in docs/design.md"
    assert re.search(r"nach rechts[^.\n]*zu|zu[^.\n]*nach rechts", design), "Pfeil zu = nach rechts fehlt in docs/design.md"
    assert re.search(r"nach unten[^.\n]*offen|offen[^.\n]*nach unten", design), "Pfeil offen = nach unten fehlt in docs/design.md"


def test_einzelheiten_ohne_parameter_offen():
    """Der Startzustand der Einzelheiten steht an genau einer Stelle: einzelheiten(inhalt, titel), kein Aufrufer setzt offen."""
    vorlage = (WURZEL / "engine/vorlage.html").read_text(encoding="utf-8")
    assert re.search(r"function einzelheiten\(inhalt, titel\)", vorlage)
    assert not re.search(r"einzelheiten\(!", vorlage)


def test_erwogene_plaene_ohne_startzustand_offen():
    """AC-5 im Quelltext: Die Beispielreisen haben einen festen Plan, dort ist „Andere erwogene Pläne“ schon heute zu. Ohne
    festen Plan entschied bisher `VARIANTE !== fest?.id` über offen; die Klappe trägt keinen Startzustand offen mehr."""
    vorlage = (WURZEL / "engine/vorlage.html").read_text(encoding="utf-8")
    assert not re.search(r'el\("details", \{class: "weg", open:', vorlage)
