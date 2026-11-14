"""#570: Der Schreibweg stößt das Veröffentlichen in beiden Anordnungen an (alt: Reisen-Repo mit Submodul frieda/, neu:
Software-Klon aus #454) und meldet ein fehlendes Skript mit einer Zeile auf stderr, statt still zurückzukehren.

Die Regel der Anordnung ist dieselbe wie fr_alte_anordnung in betrieb/gemeinsam.sh: alt, wenn <wurzel>/.gitmodules
existiert oder <wurzel>/frieda/betrieb ein Ordner ist; sonst neu. Alle Wurzeln liegen unter tmp_path."""
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import schreiben as sb  # noqa: E402


@pytest.fixture(autouse=True)
def ohne_umgebung(monkeypatch, tmp_path):
    """Kein SB_VEROEFFENTLICHEN aus der Umgebung; Anstoß-Protokoll in einen Ordner unter tmp_path."""
    monkeypatch.delenv("SB_VEROEFFENTLICHEN", raising=False)
    dienst = tmp_path / "dienst"
    dienst.mkdir()
    monkeypatch.setenv("FR_DIENST", str(dienst))


def wurzel_anlegen(tmp_path, name):
    w = tmp_path / name
    w.mkdir()
    return w


def kein_start(monkeypatch):
    """Ersetzt subprocess.Popen; liefert die Liste der versuchten Starts."""
    gerufen = []

    class Stummel:
        def __init__(self, argv, *a, **k):
            gerufen.append(argv)

    monkeypatch.setattr(sb.subprocess, "Popen", Stummel)
    return gerufen


def test_vorgabe_alte_anordnung_mit_gitmodules(tmp_path):
    """AC-1: Wurzel mit .gitmodules -> <wurzel>/frieda/betrieb/veroeffentlichen.sh."""
    w = wurzel_anlegen(tmp_path, "reisen")
    (w / ".gitmodules").write_text("[submodule \"frieda\"]\n\tpath = frieda\n")
    erwartet = w / "frieda" / "betrieb" / "veroeffentlichen.sh"
    assert Path(sb.veroeffentlichen_skript(w)) == erwartet
    assert Path(sb.Schreiber(w, tmp_path / "arbeit").veroeffentlichen) == erwartet


def test_vorgabe_alte_anordnung_mit_ordner(tmp_path):
    """AC-2: Wurzel mit Ordner frieda/betrieb, ohne .gitmodules -> ebenfalls der alte Pfad."""
    w = wurzel_anlegen(tmp_path, "reisen")
    (w / "frieda" / "betrieb").mkdir(parents=True)
    erwartet = w / "frieda" / "betrieb" / "veroeffentlichen.sh"
    assert Path(sb.veroeffentlichen_skript(w)) == erwartet
    assert Path(sb.Schreiber(w, tmp_path / "arbeit").veroeffentlichen) == erwartet


def test_vorgabe_neue_anordnung(tmp_path):
    """AC-3: Software-Klon (ohne .gitmodules, ohne frieda/betrieb) -> <wurzel>/betrieb/veroeffentlichen.sh."""
    w = wurzel_anlegen(tmp_path, "klon")
    (w / "betrieb").mkdir()
    erwartet = w / "betrieb" / "veroeffentlichen.sh"
    assert Path(sb.veroeffentlichen_skript(w)) == erwartet
    assert Path(sb.Schreiber(w, tmp_path / "arbeit").veroeffentlichen) == erwartet
    assert not (w / "frieda").exists()   # die Funktion ändert nichts auf der Platte


def test_vorrang_argument_umgebung_vorgabe(tmp_path, monkeypatch):
    """AC-4: Argument vor SB_VEROEFFENTLICHEN vor der Vorgabe; ein ausdrücklich leeres Argument schaltet aus."""
    w = wurzel_anlegen(tmp_path, "klon")
    arbeit = tmp_path / "arbeit"
    assert Path(sb.Schreiber(w, arbeit).veroeffentlichen) == w / "betrieb" / "veroeffentlichen.sh"
    monkeypatch.setenv("SB_VEROEFFENTLICHEN", str(tmp_path / "aus-umgebung.sh"))
    assert sb.Schreiber(w, arbeit).veroeffentlichen == str(tmp_path / "aus-umgebung.sh")
    assert sb.Schreiber(w, arbeit, str(tmp_path / "argument.sh")).veroeffentlichen == str(tmp_path / "argument.sh")
    assert sb.Schreiber(w, arbeit, "").veroeffentlichen == ""


def test_anstoss_neue_anordnung_startet_skript(tmp_path):
    """AC-5: Im Software-Klon ohne SB_VEROEFFENTLICHEN startet der Anstoß <wurzel>/betrieb/veroeffentlichen.sh."""
    w = wurzel_anlegen(tmp_path, "klon")
    (w / "betrieb").mkdir()
    marke = tmp_path / "gelaufen"
    stummel = w / "betrieb" / "veroeffentlichen.sh"
    stummel.write_text(f"#!/bin/sh\ntouch '{marke}'\n")
    stummel.chmod(0o755)
    sb.Schreiber(w, tmp_path / "arbeit").veroeffentlichen_anstossen()
    ende = time.monotonic() + 10
    while not marke.exists() and time.monotonic() < ende:
        time.sleep(0.05)
    assert marke.exists(), "Veröffentlichen im Software-Klon nicht angestoßen"


def test_fehlendes_skript_schreibt_eine_zeile(tmp_path, monkeypatch, capsys):
    """AC-6: Fehlt das Skript, genau eine Zeile auf stderr, kein Start, keine Ausnahme."""
    gerufen = kein_start(monkeypatch)
    fehlt = tmp_path / "gibt-es-nicht.sh"
    s = sb.Schreiber(wurzel_anlegen(tmp_path, "klon"), tmp_path / "arbeit", str(fehlt))
    s.veroeffentlichen_anstossen()
    zeilen = capsys.readouterr().err.splitlines()
    assert zeilen == [f"Publishing not started ({fehlt}): script missing"]
    assert gerufen == []


def test_leerer_pfad_bleibt_still(tmp_path, monkeypatch, capsys):
    """AC-7: Leerer Pfad (Veröffentlichen ausgeschaltet): still, kein Start."""
    gerufen = kein_start(monkeypatch)
    s = sb.Schreiber(wurzel_anlegen(tmp_path, "klon"), tmp_path / "arbeit")
    s.veroeffentlichen = ""
    s.veroeffentlichen_anstossen()
    assert capsys.readouterr().err == ""
    assert gerufen == []
