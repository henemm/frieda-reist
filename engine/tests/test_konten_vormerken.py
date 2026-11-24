"""Tests für #648: Betreiberbefehl `konten.py vormerken <reise>` (Löschen vormerken ohne Sitzung, normale Schonfrist).
Spec: docs/specs/betrieb/testkonto-648.md (Tests 12 bis 14, AC-8).

Nur erfundene Daten: die beiden Beispielreisen im Reisespeicher (Fixture `speicher` aus test_loeschen_reise).

Schnittstelle, die diese Tests festlegen:
  konten.main(["vormerken", <reise>]) -> 0      Reise vorgemerkt, Vormerkender ist der Betreiber (Konto leer),
                                                Frist = FR_LOESCHFRIST_TAGE (Vorgabe 14) Tage
  Reise nicht im Reisespeicher oder schon vorgemerkt: Exit-Code ungleich 0, ohne Wirkung
"""
import subprocess
import sys
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import konten  # noqa: E402
from test_loeschen_reise import TAG, _abdruck, _spaeter, speicher  # noqa: E402,F401  (speicher: Fixture)


# ---------- Test 12: vormerken ----------

def test_vormerken_merkt_die_reise_mit_normaler_frist_vor(speicher, capsys):
    assert konten.main(["vormerken", "beispielreise"]) == 0
    assert konten.reise_vorgemerkt("beispielreise")
    assert not konten.reise_vorgemerkt("stadtwochenende")
    z, = konten.loeschungen()
    assert z["reise"] == "beispielreise" and z["konto"] is None
    assert z["frist"] - z["wann"] == 14 * TAG
    assert "beispielreise" in capsys.readouterr().out


def test_vormerken_nutzt_die_frist_der_instanz(speicher, monkeypatch):
    monkeypatch.setenv("FR_LOESCHFRIST_TAGE", "21")
    assert konten.main(["vormerken", "stadtwochenende"]) == 0
    z, = konten.loeschungen()
    assert z["frist"] - z["wann"] == 21 * TAG


def test_vorgemerkte_reise_fehlt_in_den_reisen_des_kontos(speicher):
    """Die Reise verschwindet sofort überall: auch aus aktiver Liste und Archiv (my_trips), die über reise_vorgemerkt
    filtern."""
    import reisespeicher as rs
    assert "beispielreise" in rs.reisen()
    assert konten.main(["vormerken", "beispielreise"]) == 0
    assert "beispielreise" not in rs.reisen()
    assert "beispielreise" in rs.reisen(mit_vorgemerkten=True)


# ---------- Test 13: verweigern ----------

def test_vormerken_verweigert_unbekannte_reise(speicher, capsys):
    assert konten.main(["vormerken", "gibt-es-nicht"]) != 0
    assert konten.loeschungen() == []
    assert not konten.reise_vorgemerkt("gibt-es-nicht")
    assert "gibt-es-nicht" in capsys.readouterr().out


def test_vormerken_verweigert_ungueltige_kennung(speicher):
    assert konten.main(["vormerken", "../beispielreise"]) != 0
    assert konten.loeschungen() == []


def test_vormerken_verweigert_schon_vorgemerkte_reise(speicher, monkeypatch):
    assert konten.main(["vormerken", "beispielreise"]) == 0
    erste, = konten.loeschungen()
    _spaeter(monkeypatch, 3)
    assert konten.main(["vormerken", "beispielreise"]) != 0
    assert konten.loeschungen() == [erste]


def test_vormerken_ohne_reise_zeigt_hilfe(speicher, capsys):
    assert konten.main(["vormerken"]) != 0
    assert "vormerken <reise>" in capsys.readouterr().out


def test_hilfetext_nennt_vormerken():
    p = subprocess.run([sys.executable, str(ENGINE / "konten.py")], capture_output=True, text=True, timeout=60)
    assert "vormerken <reise>" in p.stdout


# ---------- Test 14: der Wächter entfernt sie nach der Frist ----------

def test_waechter_entfernt_die_vorgemerkte_reise_nach_der_frist(speicher, monkeypatch):
    import waechter as wa
    assert konten.main(["vormerken", "beispielreise"]) == 0
    _spaeter(monkeypatch, 13)
    wa.loeschungen_ausfuehren()
    assert _abdruck(speicher, "beispielreise") != ([], [])        # vor Fristende bleibt alles
    _spaeter(monkeypatch, 15)
    wa.loeschungen_ausfuehren()
    assert _abdruck(speicher, "beispielreise") == ([], [])
    assert "beispielreise" in konten.loeschprotokoll()
    assert not (speicher.t / "seiten" / "beispielreise").exists()
    assert _abdruck(speicher, "stadtwochenende") != ([], [])
