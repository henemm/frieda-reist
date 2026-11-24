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


# ---------- #670: konten_wert liest einen einzelnen Namen aus <FR_DIENST>/konten.env ----------
# Spec: docs/specs/konnektor/lesewerkzeuge-670.md (AC-4 bis AC-6). Nur erfundene Werte.

def konten_env(tmp_path, monkeypatch, inhalt):
    d = tmp_path / "dienst"
    d.mkdir(exist_ok=True)
    monkeypatch.setenv("FR_DIENST", str(d))
    monkeypatch.setenv("FR_EINSTELLUNGEN", str(tmp_path / "keine-einstellungen.env"))
    f = d / "konten.env"
    if inhalt is not None:
        f.write_text(inhalt, encoding="utf-8")
    return f


def test_konten_wert_liest_datei_und_entfernt_anfuehrungszeichen(tmp_path, monkeypatch):
    konten_env(tmp_path, monkeypatch, 'FR_BETREIBER_KONTAKT="ida@example.org"\n')
    assert instanz.konten_wert("FR_BETREIBER_KONTAKT") == "ida@example.org"


def test_konten_wert_umgebung_vor_datei(tmp_path, monkeypatch):
    konten_env(tmp_path, monkeypatch, "FR_BETREIBER_KONTAKT=datei@example.org\n")
    monkeypatch.setenv("FR_BETREIBER_KONTAKT", "umgebung@example.org")
    assert instanz.konten_wert("FR_BETREIBER_KONTAKT") == "umgebung@example.org"


def test_konten_wert_datei_fehlt_oder_unlesbar(tmp_path, monkeypatch, capsys):
    konten_env(tmp_path, monkeypatch, None)
    assert instanz.konten_wert("FR_BETREIBER_KONTAKT") is None
    # existiert, ist aber nicht lesbar (Verzeichnis statt Datei, wirkt auch unter root)
    (tmp_path / "dienst" / "konten.env").mkdir()
    assert instanz.konten_wert("FR_BETREIBER_KONTAKT") is None
    aus = capsys.readouterr()
    assert aus.out == "" and aus.err == ""


def test_konten_wert_liefert_nur_den_einen_namen(tmp_path, monkeypatch):
    konten_env(tmp_path, monkeypatch, "FR_MAIL_PASSWORT=geheim-beispiel\n"
                                      "FR_BETREIBER_KONTAKT=ida@example.org\n"
                                      "OHNE_PRAEFIX=karl@example.org\n"
                                      "FR_KAPUTT\n")
    assert instanz.konten_wert("FR_BETREIBER_KONTAKT") == "ida@example.org"
    assert instanz.konten_wert("OHNE_PRAEFIX") is None
    assert instanz.konten_wert("FR_FEHLT") is None
    assert instanz.konten_wert("FR_KAPUTT") is None


def test_wert_liest_konten_env_nicht(tmp_path, monkeypatch):
    konten_env(tmp_path, monkeypatch, "FR_BETREIBER_KONTAKT=ida@example.org\n")
    assert instanz.wert("FR_BETREIBER_KONTAKT") is None
    assert instanz.wert("FR_BETREIBER_KONTAKT", "vorgabe") == "vorgabe"
