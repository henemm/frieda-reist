"""Tests für instanz.speicherreisen bei unlesbarer Einstellungsdatei (#361, Epic #345, Befund F003 aus #347; Spec
docs/specs/betrieb/einstellungen-fail-closed-361.md, AC-1 bis AC-4). Seit #454 nennt die Datei nicht mehr die Reisen (im
Speicher ist, was im Speicher steht), aber womöglich den Ort des Speichers: Ist sie unlesbar und FR_SPEICHER nicht in der
Umgebung, bleibt speicherreisen() fail closed. Nur erfundene Testdaten unter tmp_path."""
import os
import sys
from pathlib import Path

import pytest

ENGINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENGINE))
import instanz  # noqa: E402


@pytest.fixture(autouse=True)
def sauber(monkeypatch):
    for k in list(os.environ):
        if k.startswith(("FR_", "RM_", "KN_")):
            monkeypatch.delenv(k)


def datei_als_verzeichnis(tmp_path, monkeypatch):
    """Die Einstellungsdatei existiert, ist aber keine lesbare Datei (läuft auch unter root)."""
    d = tmp_path / "einstellungen.env"
    d.mkdir()
    monkeypatch.setenv("FR_EINSTELLUNGEN", str(d))


def test_speicherreisen_unlesbare_datei_loest_aus(tmp_path, monkeypatch):
    datei_als_verzeichnis(tmp_path, monkeypatch)
    assert issubclass(instanz.EinstellungenNichtLesbar, OSError)
    with pytest.raises(instanz.EinstellungenNichtLesbar):
        instanz.speicherreisen()


def test_speicherreisen_gepatchtes_lesen_loest_aus(tmp_path, monkeypatch):
    d = tmp_path / "einstellungen.env"
    d.write_text("FR_SPEICHERREISEN=beispielreise\n", encoding="utf-8")
    monkeypatch.setenv("FR_EINSTELLUNGEN", str(d))

    def kaputt(self, *a, **k):
        raise OSError(5, "Input/output error")
    monkeypatch.setattr(Path, "read_text", kaputt)
    with pytest.raises(instanz.EinstellungenNichtLesbar):
        instanz.speicherreisen()


@pytest.mark.skipif(os.geteuid() == 0, reason="unter root greifen entzogene Rechte nicht")
def test_speicherreisen_chmod_000(tmp_path, monkeypatch):
    d = tmp_path / "einstellungen.env"
    d.write_text("FR_SPEICHERREISEN=beispielreise\n", encoding="utf-8")
    d.chmod(0)
    monkeypatch.setenv("FR_EINSTELLUNGEN", str(d))
    try:
        with pytest.raises(instanz.EinstellungenNichtLesbar):
            instanz.speicherreisen()
    finally:
        d.chmod(0o644)


def test_speicherreisen_fehlende_datei_ist_leer(tmp_path, monkeypatch):
    monkeypatch.setenv("FR_EINSTELLUNGEN", str(tmp_path / "gibt-es-nicht.env"))
    assert instanz.speicherreisen() == []
    monkeypatch.delenv("FR_EINSTELLUNGEN")
    monkeypatch.setenv("FR_WURZEL", str(tmp_path))          # keine Einstellungsdatei unter betrieb/
    assert instanz.speicherreisen() == []


def test_speicherreisen_umgebung_gilt_vor_unlesbarer_datei(tmp_path, monkeypatch):
    """#454: FR_SPEICHERREISEN in der Umgebung ersetzt die Datei nicht mehr; auch mit dem Ort des Speichers in der Umgebung
    bleibt eine unlesbare Datei ein Fehler (fail closed, #361)."""
    datei_als_verzeichnis(tmp_path, monkeypatch)
    monkeypatch.setenv("FR_SPEICHER", str(tmp_path / "speicher"))
    monkeypatch.setenv("FR_SPEICHERREISEN", "beispielreise, stadtwochenende")
    with pytest.raises(instanz.EinstellungenNichtLesbar):
        instanz.speicherreisen()


def test_einstellungen_und_wert_bleiben_nachsichtig(tmp_path, monkeypatch):
    datei_als_verzeichnis(tmp_path, monkeypatch)
    assert instanz.einstellungen() == {}
    assert instanz.wert("FR_ZEITZONE", "Europe/Berlin") == "Europe/Berlin"


def test_lesbare_datei_nennt_keine_reisen_mehr(tmp_path, monkeypatch):
    """#454: FR_SPEICHERREISEN in der Datei ist wirkungslos; ohne Datenbank des Speichers gibt es keine Speicherreisen."""
    d = tmp_path / "einstellungen.env"
    d.write_text(f"FR_SPEICHERREISEN=stadtwochenende\nFR_SPEICHER={tmp_path / 'speicher'}\n", encoding="utf-8")
    monkeypatch.setenv("FR_EINSTELLUNGEN", str(d))
    assert instanz.speicherreisen() == []
