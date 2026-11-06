"""Tests für Stufe 3 des Reisespeichers (#348, Epic #345, ADR-0009), Python-Ebene: Materialisieren, Vergleichen, Zustand,
Nachziehen aus dem Speicher. Spec: docs/specs/betrieb/speicher-348-stufe3.md (AC-1 bis AC-6, AC-18, AC-20 bis AC-21,
AC-29, AC-31, AC-33). Ohne Git, alles unter tmp_path; Reisen sind die beiden erfundenen Beispielreisen.

Die Shell-Läufe (AC-7, AC-9 bis AC-17, AC-24 bis AC-28, AC-32) stehen in test_betrieb.py.
RED: materialisieren, vergleichen, zustand und nachziehen-speicher gibt es noch nicht.
"""
import os
import shutil
import sqlite3
import subprocess
import sys
import time
from contextlib import closing
from pathlib import Path

import pytest

ENGINE = Path(__file__).resolve().parents[1]
WURZEL = ENGINE.parent
BEISPIEL = WURZEL / "beispiel" / "reisen"
sys.path.insert(0, str(ENGINE))

REISEN = ["beispielreise", "stadtwochenende"]


@pytest.fixture
def rs(tmp_path, monkeypatch):
    monkeypatch.setenv("FR_SPEICHER", str(tmp_path / "_speicher"))
    import reisespeicher
    return reisespeicher


def _baum(ordner):
    ordner = Path(ordner)
    return {p.relative_to(ordner).as_posix(): p.read_bytes() for p in sorted(ordner.rglob("*"))
            if p.is_file() and ".git" not in p.relative_to(ordner).parts}


def _importiert(rs, reise, ab=0):
    rs.importieren(BEISPIEL / reise, reise, "Test", grund="Anfang", ab=ab)
    return reise


def _cli(rs, *a):
    """Befehl wie im Betrieb: eigener Prozess, Ausgabe und Exit-Code."""
    p = subprocess.run([sys.executable, str(ENGINE / "reisespeicher.py"), *a], capture_output=True, text=True,
                       env={**os.environ, "FR_SPEICHER": os.environ["FR_SPEICHER"]})
    return p.returncode, p.stdout


# ---------- Teil 1 ----------

@pytest.mark.parametrize("reise", REISEN)
def test_materialisieren_ersetzt_den_ordner_byte_gleich(rs, tmp_path, reise):
    _importiert(rs, reise)
    ziel = tmp_path / "bau" / "reisen" / reise
    code, aus = _cli(rs, "materialisieren", reise, str(ziel))
    assert code == 0 and aus.strip() == f"stand {rs.stand_nummer(reise)}"
    assert _baum(ziel) == _baum(BEISPIEL / reise)
    assert Path(str(ziel) + ".stand").read_text().strip() == str(rs.stand_nummer(reise))
    # zweiter Aufruf: ersetzt, behält nichts Altes
    (ziel / "alt.txt").write_text("übrig")
    code, _ = _cli(rs, "materialisieren", reise, str(ziel))
    assert code == 0 and not (ziel / "alt.txt").exists()
    assert not Path(str(ziel) + ".neu").exists()
    assert _baum(ziel) == _baum(BEISPIEL / reise)


def test_materialisieren_haelt_nummer_und_inhalt_zusammen(rs, tmp_path):
    reise = _importiert(rs, "stadtwochenende")
    ziel = tmp_path / "m"
    n = rs.stand_nummer(reise)
    assert _cli(rs, "materialisieren", reise, str(ziel), "--bis", str(n))[0] == 0
    rs.vorgang_schreiben(reise, {"neu.txt": b"x"}, "Test", "test", "Nachtrag")
    assert Path(str(ziel) + ".stand").read_text().strip() == str(n)
    assert rs.stand_nummer(reise) == n + 1
    assert not (ziel / "neu.txt").exists()


@pytest.mark.parametrize("reise", REISEN)
def test_vergleichen_beispielreisen_ohne_unterschied(rs, reise):
    _importiert(rs, reise)
    code, aus = _cli(rs, "vergleichen", reise, str(BEISPIEL / reise))
    assert code == 0 and aus.strip().splitlines()[-1] == "gleich"


def test_vergleichen_nennt_jeden_unterschied_exit_1(rs, tmp_path):
    reise = _importiert(rs, "beispielreise")
    kopie = tmp_path / "k"
    shutil.copytree(BEISPIEL / reise, kopie)
    dateien = sorted(p for p in kopie.rglob("*") if p.is_file())
    geaendert, geloescht = dateien[0], dateien[1]
    geaendert.write_bytes(geaendert.read_bytes() + b"\nmehr")
    geloescht.unlink()
    (kopie / "neu.txt").write_text("neu")
    code, aus = _cli(rs, "vergleichen", reise, str(kopie))
    zeilen = aus.strip().splitlines()
    assert code == 1
    assert f"verschieden: {geaendert.relative_to(kopie).as_posix()}" in zeilen
    assert f"nur im Speicher: {geloescht.relative_to(kopie).as_posix()}" in zeilen
    assert "nur im Ordner: neu.txt" in zeilen
    assert zeilen[-1] == "3 Unterschiede"


def test_vergleichen_fehler_geben_exit_2(rs, tmp_path):
    reise = _importiert(rs, "stadtwochenende")
    kopie = tmp_path / "k"
    shutil.copytree(BEISPIEL / reise, kopie)
    fehlerfaelle = [("unbekannt", str(kopie)), (reise, str(tmp_path / "gibtesnicht"))]
    mit_link = tmp_path / "l"
    shutil.copytree(BEISPIEL / reise, mit_link)
    (mit_link / "link").symlink_to(mit_link / "reise.yaml")
    fehlerfaelle.append((reise, str(mit_link)))
    for r, o in fehlerfaelle:
        code, aus = _cli(rs, "vergleichen", r, o)
        assert code == 2 and aus.startswith("ERROR:"), (r, o, aus)
    assert _cli(rs, "vergleichen", reise)[0] == 2     # falsche Angaben: auch 2, nicht 1
    # gesperrte Datenbank: Schreibsperre einer zweiten Verbindung
    sperre = sqlite3.connect(rs.pfad(), timeout=0.1, isolation_level=None)
    sperre.execute("PRAGMA locking_mode = EXCLUSIVE")
    sperre.execute("BEGIN EXCLUSIVE")
    try:
        code, aus = _cli(rs, "vergleichen", reise, str(kopie))
    finally:
        sperre.close()
    assert code == 2 and aus.startswith("ERROR:")


def test_vergleichen_liest_keine_inhalte(rs, tmp_path, monkeypatch):
    reise = _importiert(rs, "beispielreise")

    def falle(*a, **k):
        raise AssertionError("Inhalte gelesen")
    monkeypatch.setattr(rs, "aktueller_stand", falle)
    assert rs.main(["vergleichen", reise, str(BEISPIEL / reise)]) == 0


# ---------- Teil 3 ----------

def _alt_machen(reise, ordner):
    """Beispielreise im alten Format: ohne `sprache:` in reise.yaml (und `typ:` statt `art:` bei der Unterkunft)."""
    y = ordner / "reise.yaml"
    y.write_text("\n".join(z for z in y.read_text().splitlines() if not z.startswith("sprache:")) + "\n")


def _neu(*a, rs=None):
    return subprocess.run([sys.executable, str(ENGINE / "neu.py"), *a], capture_output=True, text=True,
                          env={**os.environ, "FR_SPEICHER": os.environ["FR_SPEICHER"]})


@pytest.mark.parametrize("reise", REISEN)
def test_nachziehen_speicher_schreibt_einen_vorgang(rs, tmp_path, reise):
    alt = tmp_path / "alt" / reise
    shutil.copytree(BEISPIEL / reise, alt)
    _alt_machen(reise, alt)
    rs.importieren(alt, reise, "Test", grund="alt")
    vorher = rs.stand_nummer(reise)
    p = _neu("nachziehen-speicher", reise, str(tmp_path / "arbeit"), rs=rs)
    assert p.returncode == 0, p.stdout + p.stderr
    assert rs.stand_nummer(reise) == vorher + 1
    letzter = rs.verlauf(reise, 1)[0]
    assert letzter["wer"] == "Software-Nachziehen" and letzter["werkzeug"] == "nachziehen"
    erwartet = tmp_path / "erwartet" / reise
    shutil.copytree(alt, erwartet)
    assert _neu("nachziehen", str(erwartet)).returncode == 0
    assert rs.aktueller_stand(reise) == {p_: b for p_, b in _baum(erwartet).items()}


@pytest.mark.parametrize("reise", REISEN)
def test_nachziehen_speicher_ist_idempotent(rs, tmp_path, reise):
    alt = tmp_path / "alt" / reise
    shutil.copytree(BEISPIEL / reise, alt)
    _alt_machen(reise, alt)
    rs.importieren(alt, reise, "Test", grund="alt")
    assert _neu("nachziehen-speicher", reise, str(tmp_path / "a1")).returncode == 0
    n = rs.stand_nummer(reise)
    p = _neu("nachziehen-speicher", reise, str(tmp_path / "a2"))
    assert p.returncode == 0 and "nichts umzustellen" in p.stdout
    assert rs.stand_nummer(reise) == n


# ---------- Teil 4 ----------

def test_zustand_meldet_alter_der_sicherung_und_schreibt_nichts(rs, tmp_path):
    # kein Speicher: in Ordnung
    assert _cli(rs, "zustand")[0] == 0
    _importiert(rs, "stadtwochenende")
    # Datenbank ohne Sicherung: melden
    code, aus = _cli(rs, "zustand")
    assert code == 1 and aus.strip()
    # frische Sicherung
    sicherung = rs.sichern()
    db_zeit = Path(rs.pfad()).stat().st_mtime_ns
    s_zeit = Path(sicherung).stat().st_mtime_ns
    code, aus = _cli(rs, "zustand")
    assert code == 0 and "1" in aus                     # nennt Alter und Zahl der Reisen
    # alte Sicherung
    alt = time.time() - 72 * 3600
    os.utime(sicherung, (alt, alt))
    s_zeit = Path(sicherung).stat().st_mtime_ns
    assert _cli(rs, "zustand")[0] == 1
    assert Path(rs.pfad()).stat().st_mtime_ns == db_zeit and Path(sicherung).stat().st_mtime_ns == s_zeit
    # nicht lesbare Datenbank
    Path(rs.pfad()).write_bytes(b"kein sqlite" * 100)
    assert _cli(rs, "zustand")[0] == 2


def test_doku_beschreibt_die_pruefbaren_zustaende():
    text = (WURZEL / "docs" / "betrieb.md").read_text()
    assert "reisespeicher.py zustand" in text


# ---------- Teil 2/3: Listen und Einheiten ----------

def test_speicherreisen_shell_und_python_stimmen_ueberein(monkeypatch):
    monkeypatch.setenv("FR_SPEICHERREISEN", " a , ,b ,")
    import instanz
    assert instanz.speicherreisen() == ["a", "b"]
    sh = (WURZEL / "betrieb" / "gemeinsam.sh").read_text()
    assert "ist_speicherreise" in sh
    p = subprocess.run(["bash", "-c", f'source "{WURZEL}/betrieb/gemeinsam.sh"; '
                        'for r in a b c ""; do ist_speicherreise "$r" && echo "$r"; done'],
                       capture_output=True, text=True, env={**os.environ, "FR_SPEICHERREISEN": " a , ,b ,"})
    assert p.stdout.split() == ["a", "b"]


def test_keine_neue_einheit_fuer_stufe3():
    vorlagen = sorted(p.name for p in (WURZEL / "betrieb" / "vorlagen").iterdir() if p.suffix in (".service", ".timer"))
    sys.path.insert(0, str(WURZEL / "betrieb"))
    import units
    assert "vergleichslauf" not in " ".join(vorlagen)
    assert hasattr(units, "ERLAUBT")


# ---------- Teil 3 in-process: roter Probebau (AC-22), Wettlauf (AC-23) ----------
# Festgelegte Stellen: `neu.probebau(ordner)` (Probebau mit der laufenden Software, Exception = rot) und
# `reisespeicher.ordner_als_vorgang` (Eintragen, wirft StandGeaendert).

def _alte_reise(rs, tmp_path, reise="stadtwochenende"):
    alt = tmp_path / "alt" / reise
    shutil.copytree(BEISPIEL / reise, alt)
    _alt_machen(reise, alt)
    rs.importieren(alt, reise, "Test", grund="alt")
    return reise


def test_nachziehen_speicher_schreibt_nichts_bei_rotem_bau(rs, tmp_path, monkeypatch, capsys):
    reise = _alte_reise(rs, tmp_path)
    import neu
    n = rs.stand_nummer(reise)

    def rot(ordner):
        raise ValueError("Bau gescheitert")
    monkeypatch.setattr(neu, "probebau", rot)
    assert neu.main(["nachziehen-speicher", reise, str(tmp_path / "a")]) == 2
    assert "Bau gescheitert" in capsys.readouterr().out
    assert rs.stand_nummer(reise) == n


def test_nachziehen_speicher_wiederholt_bei_wettlauf_hoechstens_dreimal(rs, tmp_path, monkeypatch):
    reise = _alte_reise(rs, tmp_path)
    import neu
    n = rs.stand_nummer(reise)
    echt = rs.ordner_als_vorgang
    aufrufe = []

    def wettlauf(*a, **k):
        aufrufe.append(1)
        raise rs.StandGeaendert(n, n + 1)
    monkeypatch.setattr(rs, "ordner_als_vorgang", wettlauf)
    assert neu.main(["nachziehen-speicher", reise, str(tmp_path / "a")]) == 1
    assert len(aufrufe) == 3 and rs.stand_nummer(reise) == n          # höchstens dreimal, kein Vorgang

    # ein Fehlschlag, dann gelingt es: neu materialisiert, kein Verlust der Schreib-Änderung
    aufrufe.clear()

    def einmal(*a, **k):
        aufrufe.append(1)
        if len(aufrufe) == 1:
            rs.vorgang_schreiben(reise, {"zwischen.md": b"x"}, "Test", "test", "dazwischen")
            raise rs.StandGeaendert(n, n + 1)
        return echt(*a, **k)
    monkeypatch.setattr(rs, "ordner_als_vorgang", einmal)
    assert neu.main(["nachziehen-speicher", reise, str(tmp_path / "b")]) == 0
    assert len(aufrufe) == 2 and "zwischen.md" in rs.aktueller_stand(reise)


# ---------- Nachträge aus der Prüfung (Adversary, F001, F003, F005) ----------

def test_nachziehen_speicher_kaputte_reise_ist_rot_nicht_stoerung(rs, tmp_path, capsys):
    """F001: Scheitert das Umstellen selbst (kaputte reise.yaml im Speicher), zählt das wie ein gescheiterter Bau: Exit 2,
    nichts geschrieben. Exit 1 hieße Störung und hielte den ganzen Lauf an."""
    reise = _importiert(rs, "stadtwochenende")
    rs.vorgang_schreiben(reise, {"reise.yaml": b"titel: [kaputt\n  sprache: :\n"}, "Test", "test", "kaputt")
    n = rs.stand_nummer(reise)
    import neu
    assert neu.main(["nachziehen-speicher", reise, str(tmp_path / "a")]) == 2
    assert capsys.readouterr().out.startswith("ERROR:")
    assert rs.stand_nummer(reise) == n


def test_ist_speicherreise_zuverlaessig_unter_pipefail(tmp_path):
    """F003: Unter set -euo pipefail (wie in den Skripten) darf die Frage nie falsch negativ sein, auch bei langer Liste
    (eine Pipe mit grep -q liefe in SIGPIPE)."""
    liste = ",".join(f"r{i}" for i in range(3000))
    p = subprocess.run(["bash", "-c", f'set -euo pipefail; source "{WURZEL}/betrieb/gemeinsam.sh"; f=0; '
                        'for i in $(seq 20); do ist_speicherreise r0 || f=$((f+1)); done; '
                        'ist_speicherreise r2999 || f=$((f+1)); ! ist_speicherreise r3000 || f=$((f+1)); echo "$f"'],
                       capture_output=True, text=True,
                       env={**os.environ, "FR_WURZEL": str(tmp_path), "FR_SPEICHERREISEN": liste})
    assert p.stdout.split() == ["0"], p.stdout + p.stderr


def test_reise_ohne_plaene_materialisieren_vergleichen_nachziehen(rs, tmp_path):
    """Fehler- und Randfälle: eine erfundene Reise im Status Idee (ohne plan/routen.yaml) läuft durch Materialisieren,
    Vergleich und nachziehen-speicher ohne Fehler."""
    import datetime
    import neu
    d = neu.anlegen(tmp_path / "reisen", titel="Idee am Meer", von=datetime.date(2027, 6, 1), bis=datetime.date(2027, 6, 3),
                    personen={"ida": {"name": "Ida", "rolle": "organisator"}}, wer="Ida", heute=datetime.date(2026, 11, 6))
    assert not (d / "plan" / "routen.yaml").exists()
    rs.importieren(d, d.name, "Test", grund="Anfang")
    ziel = tmp_path / "m" / d.name
    assert _cli(rs, "materialisieren", d.name, str(ziel))[0] == 0
    assert _cli(rs, "vergleichen", d.name, str(d))[0] == 0
    p = _neu("nachziehen-speicher", d.name, str(ziel))
    assert p.returncode == 0, p.stdout + p.stderr
