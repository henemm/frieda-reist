"""Jeder Test läuft ohne die Umgebung einer echten Instanz. Die Betriebsskripte rufen die Tests mit ihren Einstellungen
auf (FR_SEITEN …); sonst leitete instanz.py Ordner wie die Konten-Datenbank aus den Ordnern des Servers ab, und Tests
schrieben dorthin. Werte, die ein Test braucht, setzt er selbst."""
import os

import pytest

PRAEFIXE = ("FR_", "RM_", "KN_", "EA_", "VF_", "FS_", "WA_")


def instanz_leeren(monkeypatch, tmp_path):
    """Entfernt die Umgebung der Instanz. Auch für Fixtures mit größerem Geltungsbereich (scope="module"), die vor
    ohne_instanz laufen: mit pytest.MonkeyPatch.context() aufrufen (sonst griffe z. B. FR_UMZUG_NACH des Servers)."""
    for name in list(os.environ):
        if name.startswith(PRAEFIXE):
            monkeypatch.delenv(name)
    monkeypatch.setenv("FR_WURZEL", str(tmp_path / "keine-instanz"))   # keine betrieb/einstellungen.env
    monkeypatch.setenv("FR_KONTEN", str(tmp_path / "_konten"))


@pytest.fixture(autouse=True)
def ohne_instanz(tmp_path, monkeypatch):
    instanz_leeren(monkeypatch, tmp_path)
