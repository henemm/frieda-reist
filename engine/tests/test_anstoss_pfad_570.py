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
    """Kein SB_VEROEFFENTLICHEN aus der Umgebung; Dienstordner (Anstoß-Merker, #624) unter tmp_path."""
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


def test_alte_anordnung_gibt_es_nicht_mehr(tmp_path):
    """AC-1/AC-2 nach #557: Auch mit .gitmodules oder einem Ordner frieda/betrieb gilt nur noch der Software-Klon,
    <wurzel>/betrieb/veroeffentlichen.sh; die alte Anordnung (Reisen-Repo mit Submodul) ist entfernt."""
    w = wurzel_anlegen(tmp_path, "reisen")
    (w / ".gitmodules").write_text("[submodule \"frieda\"]\n\tpath = frieda\n")
    (w / "frieda" / "betrieb").mkdir(parents=True)
    erwartet = w / "betrieb" / "veroeffentlichen.sh"
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


def merker(tmp_path):
    """Der Anstoß-Merker im Dienstordner der Fixture (#624)."""
    return tmp_path / "dienst" / "veroeffentlichen-anstoss"


def test_anstoss_legt_nur_merker(tmp_path, monkeypatch):
    """#624 AC-1: Mit gesetztem SB_VEROEFFENTLICHEN legt der Anstoß nur den Merker <FR_DIENST>/veroeffentlichen-anstoss an;
    das Skript selbst startet die Path-Einheit, nicht der Schreibweg (kein Kindprozess, kein Lauf des Stummels)."""
    gerufen = kein_start(monkeypatch)
    w = wurzel_anlegen(tmp_path, "klon")
    marke = tmp_path / "gelaufen"
    stummel = tmp_path / "veroeffentlichen.sh"
    stummel.write_text(f"#!/bin/sh\ntouch '{marke}'\n")
    stummel.chmod(0o755)
    monkeypatch.setenv("SB_VEROEFFENTLICHEN", str(stummel))
    sb.Schreiber(w, tmp_path / "arbeit").veroeffentlichen_anstossen()
    assert merker(tmp_path).is_file(), "Anstoß-Merker fehlt"
    time.sleep(0.3)
    assert gerufen == [] and not marke.exists(), "Der Schreibweg hat das Skript selbst gestartet"
    assert not (tmp_path / "dienst" / "veroeffentlichen-anstoss.log").exists()   # das Anstoß-Protokoll entfällt
    # Ein zweiter Anstoß, solange der Merker liegt: wirft nicht, der Merker bleibt einer
    sb.Schreiber(w, tmp_path / "arbeit").veroeffentlichen_anstossen()
    assert merker(tmp_path).is_file() and gerufen == []


def test_leeres_skript_legt_keinen_merker(tmp_path, monkeypatch):
    """#624 AC-2: Leer = aus: Ist SB_VEROEFFENTLICHEN leer gesetzt, entsteht kein Merker."""
    gerufen = kein_start(monkeypatch)
    monkeypatch.setenv("SB_VEROEFFENTLICHEN", "")
    sb.Schreiber(wurzel_anlegen(tmp_path, "klon"), tmp_path / "arbeit").veroeffentlichen_anstossen()
    assert not merker(tmp_path).exists() and gerufen == []


def test_anstoss_wirft_nie(tmp_path, monkeypatch, capsys):
    """#624 AC-3: Ist der Dienstordner nicht beschreibbar (hier: ein Pfad unter einer Datei), wirft der Anstoß nicht; der
    Fehler steht als Zeile im Protokoll (stderr, das Journal des Dienstes)."""
    gerufen = kein_start(monkeypatch)
    stummel = tmp_path / "veroeffentlichen.sh"
    stummel.write_text("#!/bin/sh\nexit 0\n")
    stummel.chmod(0o755)
    keine_mappe = tmp_path / "datei"
    keine_mappe.write_text("kein Ordner")
    monkeypatch.setenv("FR_DIENST", str(keine_mappe / "dienst"))
    monkeypatch.setenv("SB_VEROEFFENTLICHEN", str(stummel))
    sb.Schreiber(wurzel_anlegen(tmp_path, "klon"), tmp_path / "arbeit").veroeffentlichen_anstossen()
    err = capsys.readouterr().err
    assert "veroeffentlichen-anstoss" in err, err
    assert gerufen == []


def test_anstoss_startet_keinen_prozess():
    """#624 AC-13: Der Quelltext des Anstoßes startet keinen Prozess (kein Popen, kein subprocess, kein nice/ionice)."""
    import inspect
    quelle = inspect.getsource(sb.Schreiber.veroeffentlichen_anstossen)
    for wort in ("Popen", "subprocess", "ionice", "os.system", "os.spawn"):
        assert wort not in quelle, wort
    assert "veroeffentlichen-anstoss" in quelle


def test_fehlendes_skript_schreibt_eine_zeile(tmp_path, monkeypatch, capsys):
    """AC-6: Fehlt das Skript, genau eine Zeile auf stderr, kein Start, keine Ausnahme."""
    gerufen = kein_start(monkeypatch)
    fehlt = tmp_path / "gibt-es-nicht.sh"
    s = sb.Schreiber(wurzel_anlegen(tmp_path, "klon"), tmp_path / "arbeit", str(fehlt))
    s.veroeffentlichen_anstossen()
    zeilen = capsys.readouterr().err.splitlines()
    assert zeilen == [f"Publishing not started ({fehlt}): script missing"]
    assert gerufen == []
    assert not merker(tmp_path).exists()


def test_leerer_pfad_bleibt_still(tmp_path, monkeypatch, capsys):
    """AC-7: Leerer Pfad (Veröffentlichen ausgeschaltet): still, kein Start, kein Merker (#624)."""
    gerufen = kein_start(monkeypatch)
    s = sb.Schreiber(wurzel_anlegen(tmp_path, "klon"), tmp_path / "arbeit")
    s.veroeffentlichen = ""
    s.veroeffentlichen_anstossen()
    assert capsys.readouterr().err == ""
    assert gerufen == []
    assert not merker(tmp_path).exists()
