"""Jeder Test läuft ohne die Umgebung einer echten Instanz. Die Betriebsskripte rufen die Tests mit ihren Einstellungen
auf (FR_SEITEN …); sonst leitete instanz.py Ordner wie die Konten-Datenbank aus den Ordnern des Servers ab, und Tests
schrieben dorthin. Werte, die ein Test braucht, setzt er selbst."""
import os

import pytest

PRAEFIXE = ("FR_", "RM_", "KN_", "EA_", "VF_", "FS_", "WA_")


@pytest.fixture(autouse=True, scope="session")
def ohne_instanz_im_lauf(tmp_path_factory):
    """Entfernt die Einstellungen der Instanz einmal für den ganzen Lauf, vor allen Vorbereitungen mit scope="module"
    oder "session". Die Vorbereitung je Test (ohne_instanz) greift erst danach; eine Modul-Vorbereitung, die eine Seite
    baut, sah sonst die Einstellungen des Servers (etwa FR_UMZUG_NACH: die Testseite leitete auf die neue Adresse um
    und erschien nie)."""
    mp = pytest.MonkeyPatch()
    for name in list(os.environ):
        if name.startswith(PRAEFIXE):
            mp.delenv(name)
    mp.setenv("FR_WURZEL", str(tmp_path_factory.mktemp("lauf") / "keine-instanz"))
    yield
    mp.undo()


@pytest.fixture(autouse=True)
def ohne_instanz(tmp_path, monkeypatch):
    for name in list(os.environ):
        if name.startswith(PRAEFIXE):
            monkeypatch.delenv(name)
    monkeypatch.setenv("FR_WURZEL", str(tmp_path / "keine-instanz"))   # keine betrieb/einstellungen.env
    monkeypatch.setenv("FR_KONTEN", str(tmp_path / "_konten"))
