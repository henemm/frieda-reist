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
    index.write_text(html.replace("<script>", "<script>throw new Error('Startfehler-Test');", 1), encoding="utf-8")
    aus = probe(gebaut)
    assert aus.returncode == 1
    assert "Startfehler-Test" in aus.stdout + aus.stderr


def test_leere_seite_ist_rot(gebaut):
    (gebaut / "index.html").write_text("<!doctype html><html><body><div id=\"main\"></div></body></html>", encoding="utf-8")
    assert probe(gebaut).returncode == 1
