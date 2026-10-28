"""Jeder Test läuft ohne die Umgebung einer echten Instanz. Die Betriebsskripte rufen die Tests mit ihren Einstellungen
auf (FR_SEITEN …); sonst leitete instanz.py Ordner wie die Konten-Datenbank aus den Ordnern des Servers ab, und Tests
schrieben dorthin. Werte, die ein Test braucht, setzt er selbst."""
import os

import pytest

PRAEFIXE = ("FR_", "RM_", "KN_", "EA_", "VF_", "FS_", "WA_")


@pytest.fixture(autouse=True)
def ohne_instanz(tmp_path, monkeypatch):
    for name in list(os.environ):
        if name.startswith(PRAEFIXE):
            monkeypatch.delenv(name)
    monkeypatch.setenv("FR_WURZEL", str(tmp_path / "keine-instanz"))   # keine betrieb/einstellungen.env
    monkeypatch.setenv("FR_KONTEN", str(tmp_path / "_konten"))
