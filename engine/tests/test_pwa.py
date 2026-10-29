"""Tests für die PWA-Hülle (Issue #6): Manifest, Icons, sw.js mit Inhalts-Hash, Browser-Prüfung."""
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

WURZEL = Path(__file__).resolve().parent.parent.parent
# Playwright für die Browser-Prüfung: PLAYWRIGHT_MODUL oder ~/playwright-tool (fehlt beides, wird übersprungen)
from playwright_pfad import PLAYWRIGHT  # noqa: E402


def mini_reise(tmp_path):
    r = tmp_path / "reise"
    (r / "medien").mkdir(parents=True)
    from PIL import Image
    Image.new("RGB", (40, 30), "red").save(r / "medien/karte.png")
    (r / "plan.md").write_text("# Plan\n\n## Tagesplan\n\nTag 1\n\n![Karte](medien/karte.png)\n", encoding="utf-8")
    (r / "reise.json").write_text(json.dumps({
        "titel": "Testreise – Untertitel", "pfad": "test", "plan": "plan.md",
        "abschnitte": {"plan.md": {"Tagesplan": ["W-01", "plan"]}}}), encoding="utf-8")
    return r


def sw_daten(ziel):
    sw = (ziel / "sw.js").read_text(encoding="utf-8")
    version = re.search(r'const VERSION = "([0-9a-f]{12})"', sw).group(1)
    dateien = json.loads(re.search(r"const DATEIEN = (\[.*\]);", sw).group(1))
    return version, dateien


def test_huelle_vollstaendig(tmp_path):
    ziel = tmp_path / "dist"
    bauen.bauen(mini_reise(tmp_path), ziel)
    m = json.loads((ziel / "manifest.json").read_text(encoding="utf-8"))
    assert m["short_name"] == "Testreise" and m["start_url"] == "./" and m["scope"] == "./"
    for f in ("icon-180.png", "icon-192.png", "icon-512.png"):
        assert (ziel / f).stat().st_size > 0
    version, dateien = sw_daten(ziel)
    assert "medien/karte.png" in dateien and "index.html" in dateien and "sw.js" not in dateien
    # Pico CSS liegt lokal und wird vorab gespeichert, sonst öffnet die App offline ungestaltet
    assert "pico-2.1.1.min.css" in dateien and 'href="pico-2.1.1.min.css"' in (ziel / "index.html").read_text(encoding="utf-8")
    assert "Licensed under MIT" in (ziel / "pico-2.1.1.min.css").read_text(encoding="utf-8")[:300]
    assert {"leaflet-1.9.4.js", "leaflet-1.9.4.css"} <= set(dateien)
    assert "Leaflet 1.9.4" in (ziel / "leaflet-1.9.4.js").read_text(encoding="utf-8")[:200]
    assert all((ziel / f).exists() for f in dateien)
    html = (ziel / "index.html").read_text(encoding="utf-8")
    assert 'rel="manifest" href="manifest.json"' in html and 'register("sw.js")' in html
    assert 'rel="icon" type="image/png" sizes="32x32" href="icon-32.png"' in html and "icon-32.png" in dateien


def test_eigenes_app_symbol(tmp_path):
    from PIL import Image
    reise, ziel = mini_reise(tmp_path), tmp_path / "dist"
    bauen.bauen(reise, ziel)
    text_icon = (ziel / "icon-192.png").read_bytes()
    (reise / "medien/icon.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
                                           '<rect width="10" height="10" fill="#d23a2c"/></svg>', encoding="utf-8")
    bauen.bauen(reise, ziel)
    for g in (32, 180, 192, 512):
        im = Image.open(ziel / f"icon-{g}.png")
        assert im.size == (g, g) and im.mode == "RGB" and im.getpixel((g // 2, g // 2)) == (0xd2, 0x3a, 0x2c)
    assert (ziel / "icon-192.png").read_bytes() != text_icon
    m = json.loads((ziel / "manifest.json").read_text(encoding="utf-8"))
    assert all(i["purpose"] == "any maskable" for i in m["icons"])


def test_version_folgt_dem_inhalt(tmp_path):
    reise, ziel = mini_reise(tmp_path), tmp_path / "dist"
    bauen.bauen(reise, ziel)
    v1, _ = sw_daten(ziel)
    bauen.bauen(reise, ziel)
    assert sw_daten(ziel)[0] == v1            # nichts geändert -> kein Update-Hinweis
    (reise / "plan.md").write_text("# Plan\n\n## Tagesplan\n\nTag 1 geändert\n", encoding="utf-8")
    bauen.bauen(reise, ziel)
    v2, dateien = sw_daten(ziel)
    assert v2 != v1
    # das Bild wird nicht mehr verwendet: weder ausgeliefert noch vorab geladen
    assert "medien/karte.png" not in dateien and not (ziel / "medien/karte.png").exists()


@pytest.mark.skipif(not PLAYWRIGHT.exists() or not shutil.which("node"), reason="Playwright fehlt")
@pytest.mark.parametrize("browser", ["chromium", "webkit"])
def test_offline_im_browser(tmp_path, browser):
    web = tmp_path / "web"
    ziel = web / "test-abc"
    bauen.bauen(mini_reise(tmp_path), ziel)
    netz = {"an": True}
    geladen = []

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            if self.path.startswith("/__netz/"):
                netz["an"] = self.path.endswith("/an")
                self.send_response(204)
                self.end_headers()
            elif self.path.startswith("/__log/"):
                daten = json.dumps(geladen).encode()
                if self.path.endswith("/leeren"):
                    geladen.clear()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(daten)
            elif not netz["an"]:
                self.close_connection = True   # keine Antwort: Abbruch wie ohne Netz
            else:
                geladen.append(self.path.split("?")[0])
                super().do_GET()

    handler = functools.partial(Handler, directory=str(web))
    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    try:
        aus = subprocess.run(["node", str(Path(__file__).parent / "pwa_browser.mjs"), str(PLAYWRIGHT),
                              f"http://localhost:{s.server_address[1]}/test-abc/", str(ziel)],
                             capture_output=True, text=True, timeout=120, env={**os.environ, "RH_BROWSER": browser})
    finally:
        s.shutdown()
    assert aus.returncode == 0, aus.stderr[-2000:]
    e = json.loads(aus.stdout.strip().splitlines()[-1])
    assert e["gespeichert"] == e["erwartet"]
    assert e["offlineTitel"] == "Testreise – Untertitel" and e["offlineBild"]
    assert e["offlineHinweis"] in (True, None)
    assert not e["kaputtHinweis"] and e["kaputtVersion"] == e["version1"]
    assert e["updateHinweis"] and e["version2"] == "neu" and e["speicherNachUpdate"] == 1
    # Update: unveränderte Dateien kommen aus dem alten Speicher, geladen wird nur sw.js (Issue #64).
    # Nach dem Neuladen fragt die Seite den Rückmeldedienst; die Seite selbst darf je nach Zeitpunkt vom Netz kommen.
    # sw.js darf mehrfach kommen: Der Browser prüft es bei jeder Registrierung und jedem Update-Aufruf neu (das
    # machte den Test gelegentlich rot, 25.10.2026). Entscheidend ist, dass sonst nichts nachgeladen wird.
    assert set(e["geladenBeimInstallieren"]) == {"/test-abc/sw.js"}, e["geladenBeimInstallieren"]
    assert {x for x in e["geladenBeimUpdate"] if "/api/" not in x} <= {"/test-abc/sw.js", "/test-abc/"}, e["geladenBeimUpdate"]
    assert e["fehler"] == []


def test_gleicher_inhalt_gleiche_version(tmp_path):
    """Mit anderer Hash-Saat (andere Reihenfolge in Python-Mengen) muss dieselbe Version herauskommen,
    sonst erscheint nach jeder Veröffentlichung „Neue Version bereit“ ohne neuen Inhalt. Geprüft an der
    Beispielreise, weil sie Route, Pläne, Karte und Punkte hat."""
    reise = WURZEL / "beispiel" / "reisen" / "beispielreise"
    versionen = []
    for saat in ("1", "2"):
        ziel = tmp_path / saat
        code = (f"import sys; sys.path.insert(0, {str(WURZEL / 'engine')!r}); import bauen, pathlib; "
                f"bauen.bauen(pathlib.Path({str(reise)!r}), pathlib.Path({str(ziel)!r}))")
        subprocess.run([sys.executable, "-c", code], check=True, capture_output=True,
                       env={**os.environ, "PYTHONHASHSEED": saat})
        versionen.append(sw_daten(ziel)[0])
    assert versionen[0] == versionen[1]


def test_umzug_service_worker(tmp_path, monkeypatch):
    """Ohne Umzug bleibt der Worker wie gehabt; mit Adresse räumt er auf und schickt Fenster zur neuen Domain."""
    monkeypatch.delenv("FR_UMZUG_NACH", raising=False)
    r = mini_reise(tmp_path)
    bauen.bauen(r, tmp_path / "alt")
    assert "const UMZUG_NACH = null;" in (tmp_path / "alt/sw.js").read_text(encoding="utf-8")
    bauen.bauen(r, tmp_path / "neu", "https://neu.example/")
    sw = (tmp_path / "neu/sw.js").read_text(encoding="utf-8")
    assert 'const UMZUG_NACH = "https://neu.example";' in sw and "__UMZUG__" not in sw
    assert "self.skipWaiting()" in sw and "registration.unregister()" in sw and "navigate" not in sw.split("function umziehen")[1].split("self.addEventListener")[0].replace("Client.navigate", "")
    html = (tmp_path / "neu/index.html").read_text(encoding="utf-8")
    assert html.count('if (location.origin !== "https://neu.example") location.replace("https://neu.example" + location.pathname') == 1
    assert "location.replace(" not in (tmp_path / "alt/index.html").read_text(encoding="utf-8").split("</head>")[0]
    monkeypatch.setenv("FR_UMZUG_NACH", "https://aus-umgebung.example")
    bauen.bauen(r, tmp_path / "env")
    assert 'const UMZUG_NACH = "https://aus-umgebung.example";' in (tmp_path / "env/sw.js").read_text(encoding="utf-8")
