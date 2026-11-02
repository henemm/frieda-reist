"""Tests sehen nie die Umgebung einer Instanz, auch nicht in Fixtures mit größerem Geltungsbereich (#204)."""
import os
import subprocess
import sys
from pathlib import Path

PROBE = '''
import os
import pytest


@pytest.fixture(scope="module")
def umgebung_im_modul():
    return {n: os.environ.get(n) for n in ("FR_UMZUG_NACH", "FR_SEITEN", "KN_PORT", "FR_WURZEL")}


def test_modul_fixture_ohne_instanz(umgebung_im_modul):
    u = umgebung_im_modul
    assert u["FR_UMZUG_NACH"] is None and u["FR_SEITEN"] is None and u["KN_PORT"] is None, u
    assert u["FR_WURZEL"] and "/srv/" not in u["FR_WURZEL"], u
'''


def test_modul_fixtures_laufen_ohne_umgebung_des_servers(tmp_path):
    (tmp_path / "test_probe.py").write_text(PROBE, encoding="utf-8")
    env = {**os.environ, "FR_UMZUG_NACH": "https://neu.example.org", "FR_SEITEN": "/srv/beispiel",
           "KN_PORT": "8782", "FR_WURZEL": "/srv/beispiel/_bau", "PYTHONPATH": str(Path(__file__).parent)}
    # conftest.py dieses Ordners als Plugin: die Probe läuft mit denselben Vorbereitungen wie jeder Test hier
    aus = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-p", "conftest", str(tmp_path)],
                         cwd=tmp_path, env=env, capture_output=True, text=True, timeout=120)
    assert aus.returncode == 0, aus.stdout[-2000:] + aus.stderr[-2000:]
