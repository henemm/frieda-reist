"""Struktur-Prüfung von .github/workflows/tests.yml (#356).

Der CI-Schritt für Playwright und die Paketinstallation hingen am Ubuntu-Spiegel und liefen bis zur Job-Grenze.
Die Zusagen der Spec (docs/specs/betrieb/ci-playwright-zeitgrenze-356.md) werden hier an der Datei geprüft.
"""
import re
from pathlib import Path

import yaml

WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "tests.yml"


def _job():
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]["tests"]


def _schritte():
    return _job()["steps"]


def _index(praedikat):
    for i, s in enumerate(_schritte()):
        if praedikat(s):
            return i
    raise AssertionError("Schritt nicht gefunden")


def _playwright_schritt():
    i = _index(lambda s: str(s.get("name", "")).startswith("Playwright und Browser"))
    return i, _schritte()[i]


def test_playwright_schritt_hat_eigene_zeitgrenze():
    _, schritt = _playwright_schritt()
    assert "timeout-minutes" in schritt, "Der Schritt hat keine eigene Zeitgrenze"
    assert schritt["timeout-minutes"] < _job()["timeout-minutes"]


def test_playwright_install_wird_wiederholt():
    i_pw, schritt = _playwright_schritt()
    run = schritt["run"]
    # Schleife mit zwei Versuchen, je Versuch mit timeout
    assert re.search(r"for\s+\w+\s+in\s+1\s+2\b", run), "keine Schleife mit zwei Versuchen"
    assert re.search(r"\btimeout\s+\d+\s+npx playwright install", run), "Versuch ohne timeout"
    # playwright install steht nur im Schritt mit der Schleife
    for i, s in enumerate(_schritte()):
        if i == i_pw:
            continue
        assert "playwright install" not in str(s.get("run", ""))


def test_apt_hat_zeitgrenzen():
    schritte = _schritte()
    i_pakete = _index(lambda s: s.get("name") == "Python-Pakete")
    vorher = [s for s in schritte[:i_pakete] if "Acquire::Retries" in str(s.get("run", ""))
              and "Acquire::http::Timeout" in str(s.get("run", ""))]
    assert vorher, "Kein Schritt vor „Python-Pakete“ setzt die apt-Zeitgrenzen"
    i_conf = schritte.index(vorher[0])
    for i, s in enumerate(schritte):
        if "apt-get" in str(s.get("run", "")):
            assert i > i_conf, "apt-get läuft vor der Vorbereitung"


def test_browser_cache_schluessel_aus_package_lock():
    schritte = _schritte()
    i_pw, _ = _playwright_schritt()
    caches = [(i, s) for i, s in enumerate(schritte)
              if str(s.get("uses", "")).startswith("actions/cache@")]
    assert caches, "kein actions/cache-Schritt"
    treffer = [
        i for i, s in caches
        if "ms-playwright" in str(s.get("with", {}).get("path", ""))
        and "hashFiles('engine/tests/playwright/package-lock.json')" in str(s.get("with", {}).get("key", ""))
    ]
    assert treffer, "kein Cache für ~/.cache/ms-playwright mit dem Schlüssel aus package-lock.json"
    assert treffer[0] < i_pw, "Cache steht nicht vor dem Install-Schritt"


def test_unveraendert_wichtiges():
    assert _job()["timeout-minutes"] == 25
    assert any(s.get("name") == "Browser-Prüfung darf nicht übersprungen worden sein" for s in _schritte())
    for s in _schritte():
        if "uses" in s:
            assert s["uses"].startswith("actions/"), s["uses"]
