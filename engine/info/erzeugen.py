"""Bildschirmbilder der Reiseseite für die Infoseite „Was ist Frieda?“ (#436), aus den erfundenen Beispielreisen.

Aufruf:  engine/.venv/bin/python engine/info/erzeugen.py [--ziel <ordner>]

Baut beide Beispielreisen je Sprache der Software (die Hülle der Seite in dieser Sprache, die Inhalte bleiben in der Sprache der
Reise), nimmt im Browser je Bild eine Handy-Ansicht auf (aufnehmen.mjs, Playwright) und legt sie als <name>-<sprache>.webp in
diesen Ordner (Vorgabe) oder nach --ziel. Neu erzeugen, wenn sich die Reiseseite sichtbar ändert; die Infoseite nimmt die
Dateien beim nächsten Deploy (betrieb/deploy.sh). Nur Beispielreisen, nie echte Reisen: das Repo ist öffentlich.
"""
import argparse
import functools
import http.server
import json
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

HIER = Path(__file__).resolve().parent
ENGINE = HIER.parent
WURZEL = ENGINE.parent
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(ENGINE / "tests"))

from PIL import Image  # noqa: E402

import anmeldung  # noqa: E402
import bauen  # noqa: E402
import texte  # noqa: E402

BEISPIELE = WURZEL / "beispiel" / "reisen"
# Je Bild der Infoseite (anmeldung.INFO_BILDER): welche Beispielreise und welche Ansicht
BILDER = {
    "reise": {"reise": "beispielreise", "hash": ""},
    "tag": {"reise": "beispielreise", "hash": "T-02"},
    "wahl": {"reise": "beispielreise", "hash": "V-03"},
    "packliste": {"reise": "stadtwochenende", "hash": "packliste"},
}
BREITE, HOEHE = 585, 1050   # Pixel der Dateien (390 × 700 CSS-Pixel in anderthalbfacher Dichte); die Infoseite rechnet damit


def playwright():
    from playwright_pfad import PLAYWRIGHT
    if not PLAYWRIGHT.exists() or not shutil.which("node"):
        raise SystemExit("Playwright fehlt (engine/tests/playwright_pfad.py)")
    return PLAYWRIGHT


def bauen_in(web, sprache):
    """Kopie jeder Beispielreise mit der Sprache der Hülle bauen; -> Ordner, den der Server ausliefert."""
    for reise in sorted({b["reise"] for b in BILDER.values()}):
        quelle = web.parent / "quelle" / sprache / reise
        shutil.copytree(BEISPIELE / reise, quelle)
        yaml = quelle / "reise.yaml"
        text = yaml.read_text(encoding="utf-8")
        alt = next(z for z in text.splitlines() if z.startswith("sprache:"))
        yaml.write_text(text.replace(alt, f"sprache: {sprache}", 1), encoding="utf-8")
        bauen.bauen(quelle, web / reise)


def aufnehmen(web, aus):
    """-> {"fehler": [...], "texte": {name: Text der Ansicht}}; legt <name>.png in aus."""
    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(web)))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    liste = [{"name": n, **b} for n, b in BILDER.items()]
    try:
        r = subprocess.run(["node", str(HIER / "aufnehmen.mjs"), str(playwright()), f"http://127.0.0.1:{s.server_address[1]}",
                            str(aus), json.dumps(liste)], capture_output=True, text=True, timeout=300)
    finally:
        s.shutdown()
    if r.returncode:
        raise SystemExit(r.stderr[-2000:])
    return json.loads(r.stdout.strip().splitlines()[-1])


def erzeugen(ziel=HIER, sprachen=None):
    """Alle Bilder in allen Sprachen der Software; -> {sprache: Bericht von aufnehmen}."""
    assert set(BILDER) == set(anmeldung.INFO_BILDER), "BILDER und anmeldung.INFO_BILDER müssen dieselben Namen haben"
    berichte = {}
    with tempfile.TemporaryDirectory() as tmp:
        for sp in sprachen or texte.SPRACHEN:
            web = Path(tmp) / "web" / sp
            bauen_in(web, sp)
            png = Path(tmp) / "png" / sp
            png.mkdir(parents=True)
            berichte[sp] = aufnehmen(web, png)
            for name in BILDER:
                with Image.open(png / f"{name}.png") as bild:
                    bild.convert("RGB").resize((BREITE, HOEHE), Image.LANCZOS).save(
                        Path(ziel) / f"{name}-{sp}.webp", "WEBP", quality=78, method=6)
    return berichte


if __name__ == "__main__":
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--ziel", default=str(HIER), help="Ordner für die Bilder (Vorgabe: engine/info/)")
    ziel = Path(a.parse_args().ziel)
    ziel.mkdir(parents=True, exist_ok=True)
    for sp, bericht in erzeugen(ziel).items():
        if bericht["fehler"]:
            raise SystemExit(f"{sp}: Skriptfehler auf der Seite: {bericht['fehler']}")
        print(f"{sp}: {', '.join(f'{n}-{sp}.webp' for n in BILDER)}")
