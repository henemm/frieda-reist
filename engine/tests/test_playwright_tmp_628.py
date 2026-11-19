"""Tests für #628: Tests installieren keine echte Playwright-Kopie (Spec docs/specs/betrieb/playwright-tmp-tests.md).

Ein echtes npm im PATH hat je Test der Software-Weg-Tests eine vollständige Playwright-Installation (rund 930 MB) unter
tmp_path abgelegt. Hier ersetzt eine npm-Attrappe im PATH das echte Programm: Sie hält jeden Aufruf fest und legt nur
leere Ordner an, wie sie eine Installation hinterließe. Nur erfundene Testdaten, alles unter tmp_path.
"""
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_betrieb import ausfuehrbar  # noqa: E402
from test_software_weg_454 import sw  # noqa: E402,F401
import conftest  # noqa: E402


def _npm_attrappe(bin_ordner, protokoll):
    """npm im PATH: hält jeden Aufruf fest und legt im aktuellen Ordner node_modules/playwright an (wie npm ci)."""
    return ausfuehrbar(bin_ordner / "npm", f'#!/bin/sh\necho "$PWD $*" >> {protokoll}\n'
                                           'mkdir -p node_modules/playwright\n: > node_modules/playwright/index.mjs\n'
                                           'mkdir -p browser\nexit 0\n')


def test_sw_legt_keine_playwright_kopie_an(sw):
    """AC-1: Mit npm im PATH erreicht der Software-Weg im Test nie npm; unter dem Dienstordner liegt keine
    Playwright-Installation, die Ausgabe nennt „npm missing“."""
    protokoll = sw.t / "npm.log"
    _npm_attrappe(sw.t / "bin", protokoll)
    ausgaben = []
    r = sw.lauf()
    ausgaben.append(r.stdout + r.stderr)
    sw.nachweis_gruen()
    sw.neuer_commit()
    r = sw.lauf()
    ausgaben.append(r.stdout + r.stderr)
    assert r.returncode == 0, ausgaben
    assert not protokoll.exists(), protokoll.read_text()
    assert not (sw.dienst / "playwright" / "node_modules").exists()
    assert any("npm missing" in a for a in ausgaben), ausgaben


def test_instanz_leeren_setzt_vf_npm():
    """AC-2: Nach instanz_leeren zeigt VF_NPM auf eine Datei, die es nicht gibt; Unterprozesse mit os.environ erreichen
    so nie ein echtes npm."""
    wert = os.environ.get("VF_NPM")
    assert wert, "VF_NPM ist nicht gesetzt"
    assert not Path(wert).exists(), wert


def test_waechter_erkennt_installation():
    """AC-3: Die Wächter-Prüfung findet eine Playwright-Installation bis Tiefe 3 und nennt den Fundort; tiefer liegt
    die bewusste Grenze. Die Attrappe liegt außerhalb von tmp_path, damit der Wächter dieses Tests selbst still bleibt."""
    with tempfile.TemporaryDirectory() as d:
        wurzel = Path(d)
        for tiefe, teile in enumerate([(), ("a",), ("a", "b")], start=1):
            ziel = wurzel.joinpath(*teile, "playwright", "node_modules")
            ziel.mkdir(parents=True)
            funde = conftest.playwright_funde(wurzel)
            assert any(str(ziel) in str(f) for f in funde), (tiefe, funde)
            for f in list(wurzel.iterdir()):
                shutil.rmtree(f)
        tief = wurzel / "a" / "b" / "c" / "playwright" / "node_modules"
        tief.mkdir(parents=True)
        assert conftest.playwright_funde(wurzel) == []


def test_waechter_schweigt_ohne_installation(tmp_path):
    """AC-3: Ohne Playwright-Installation, aber mit ähnlich benannten Ordnern, meldet der Wächter nichts."""
    (tmp_path / "playwright").mkdir()
    (tmp_path / "x" / "playwright" / "browser").mkdir(parents=True)
    (tmp_path / "node_modules" / "playwright").mkdir(parents=True)
    assert conftest.playwright_funde(tmp_path) == []
