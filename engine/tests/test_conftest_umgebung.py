"""Die Einstellungen einer Instanz erreichen auch Vorbereitungen mit scope="module" nicht (conftest.py).

Die Betriebsskripte rufen die Tests mit den Einstellungen des Servers auf. Eine Modul-Vorbereitung lief früher vor dem
Aufräumen je Test und baute die Testseite mit FR_UMZUG_NACH: Sie leitete auf die neue Adresse um, die Browser-Prüfung
lief in die Zeitgrenze, und das Veröffentlichen blieb rot.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

PROBE = '''
import os
import pytest


@pytest.fixture(scope="module")
def gebaut():
    return {n: os.environ.get(n) for n in ("FR_UMZUG_NACH", "KN_ZUGAENGE", "FR_WURZEL")}


def test_modul_vorbereitung_ohne_instanz(gebaut):
    assert gebaut["FR_UMZUG_NACH"] is None and gebaut["KN_ZUGAENGE"] is None, gebaut
    assert gebaut["FR_WURZEL"] != "/srv/probe/_bau", gebaut
'''


def test_modul_vorbereitung_sieht_keine_instanz(tmp_path):
    shutil.copy(Path(__file__).with_name("conftest.py"), tmp_path / "conftest.py")
    (tmp_path / "test_probe.py").write_text(PROBE, encoding="utf-8")
    env = {**os.environ, "FR_UMZUG_NACH": "https://neu.example.invalid", "KN_ZUGAENGE": "/srv/probe/zugaenge.json",
           "FR_WURZEL": "/srv/probe/_bau"}
    aus = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", str(tmp_path)],
                         capture_output=True, text=True, env=env, cwd=tmp_path, timeout=120)
    assert aus.returncode == 0, aus.stdout[-2000:] + aus.stderr[-1000:]
