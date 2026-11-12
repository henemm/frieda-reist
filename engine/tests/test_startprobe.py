"""Startprobe beim Veröffentlichen (#395, Lehre aus #387): Die gebaute Reise wird im Browser geladen; ein Seitenfehler beim
Start oder eine leere Seite macht die Probe rot, damit deploy.sh die Reise auf dem letzten guten Stand lässt."""
import functools
import http.server
import shutil
import subprocess
import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import bauen  # noqa: E402
from test_tagesseite import PLAYWRIGHT, WURZEL  # noqa: E402

PROBE = WURZEL / "betrieb" / "startprobe.mjs"


def probe(ordner):
    return subprocess.run(["node", str(PROBE), str(PLAYWRIGHT), str(ordner)], capture_output=True, text=True, timeout=120)


@pytest.fixture
def gebaut(tmp_path):
    if not Path(PLAYWRIGHT).exists():
        pytest.skip("Playwright fehlt")
    quelle = tmp_path / "quelle"
    shutil.copytree(WURZEL / "beispiel/reisen/beispielreise", quelle)
    bauen.bauen(quelle, tmp_path / "web" / "beispiel")
    return tmp_path / "web" / "beispiel"


def test_gesunde_seite_besteht(gebaut):
    aus = probe(gebaut)
    assert aus.returncode == 0, aus.stdout + aus.stderr


def test_startfehler_ist_rot(gebaut):
    index = gebaut / "index.html"
    html = index.read_text(encoding="utf-8")
    assert "<script>" in html
    index.write_text(bauen.skripte_festlegen(html.replace("<script>", "<script>throw new Error('Startfehler-Test');", 1)), encoding="utf-8")
    aus = probe(gebaut)
    assert aus.returncode == 1
    assert "Startfehler-Test" in aus.stdout + aus.stderr


def test_leere_seite_ist_rot(gebaut):
    (gebaut / "index.html").write_text("<!doctype html><html><body><div id=\"main\"></div></body></html>", encoding="utf-8")
    assert probe(gebaut).returncode == 1


def test_sichtbare_startfehler_meldung_ist_rot(gebaut):
    """#387: Zeigt die Seite die Startfehler-Meldung, ist die Probe rot (auch wenn die Meldung selbst keinen Seitenfehler wirft)."""
    index = gebaut / "index.html"
    html = index.read_text(encoding="utf-8")
    assert "const D = " in html
    index.write_text(bauen.skripte_festlegen(html.replace("const D = ", "Promise.reject(new Error('Startfehler-Test'));const D = ", 1)), encoding="utf-8")
    aus = probe(gebaut)
    assert aus.returncode == 1
    assert "Startfehler-Meldung sichtbar" in aus.stdout + aus.stderr


def probe_adressen(zeilen):
    return subprocess.run(["node", str(PROBE), str(PLAYWRIGHT), "--adressen"], input=zeilen, capture_output=True, text=True,
                          timeout=120)


@pytest.fixture
def live(gebaut):
    """Die gebaute Seite unter einem geheimen Pfad wie auf dem Server (<reise>-<token>/), ausgeliefert über HTTP."""
    wurzel = gebaut.parent
    (wurzel / "beispiel-geheimeswort123").symlink_to(gebaut, target_is_directory=True)
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(wurzel))
    handler.log_message = lambda *a: None
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}/beispiel-geheimeswort123/"
    server.shutdown()


def test_adressen_gesunde_seite(live):
    """Überwachung (#387, henemm-infra#393): Adressen kommen über stdin, die Ausgabe nennt nur den Namen."""
    aus = probe_adressen(f"beispiel\t{live}\n")
    assert aus.returncode == 0, aus.stdout + aus.stderr
    assert aus.stdout.strip() == "beispiel: gut"


def test_adressen_kaputte_seite_rot_ohne_geheimen_pfad(live, gebaut):
    index = gebaut / "index.html"
    index.write_text(bauen.skripte_festlegen(index.read_text(encoding="utf-8").replace("<script>", "<script>throw new Error('Startfehler-Test');", 1)),
                     encoding="utf-8")
    aus = probe_adressen(f"gut-und-kaputt\t{live}\nfehlt\t{live}gibt-es-nicht/\n")
    assert aus.returncode == 1
    zeilen = aus.stdout.strip().splitlines()
    assert zeilen[0].startswith("gut-und-kaputt: ") and "Startfehler-Test" in zeilen[0]
    assert zeilen[1].startswith("fehlt: ") and "HTTP 404" in zeilen[1]
    assert "geheimeswort123" not in aus.stdout + aus.stderr
