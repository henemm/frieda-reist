"""#529: Veröffentlichen lässt eine zur Löschung vorgemerkte Reise im echten Durchlauf aus (Testnachzug zu #381, AC-6).

betrieb/veroeffentlichen.sh wird echt ausgeführt, in der neuen Anordnung (Fixture sw, main_klon, #454) und in der alten
Anordnung (Fixture sp). Vorgemerkt wird mit den echten Funktionen von engine/konten.py; die Liste für den Lauf liefert der
echte Befehl konten.py vorgemerkt. Nachweistests zu bestehendem Verhalten, Spec: docs/specs/betrieb/vorgemerkte-durchlauf-529.md.

Reisen: beispielreise (Wanderung mit Varianten, bleibt unberührt) und stadtwochenende (ohne Wanderung, wird vorgemerkt).
Das Konto ist erfunden.
"""
import sys
from contextlib import closing
from pathlib import Path

import pytest

ENGINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import konten  # noqa: E402
from test_betrieb import vf, sp  # noqa: E402,F401  (Fixtures)
from test_software_weg_454 import sw  # noqa: E402,F401  (Fixture)

VORGEMERKT = "stadtwochenende"   # Reise ohne Wanderung, wird zur Löschung vorgemerkt
ANDERE = "beispielreise"         # Wanderung, bleibt unberührt
MELDUNG = "is marked for deletion: page removed."
FEHLER = "the list of deleted trips cannot be read"


# ---------- Aufbau ----------

def konto_anlegen(konten_ordner, monkeypatch, tmp_path):
    """Kontendatenbank unter konten_ordner mit einem erfundenen Konto k-ida (Muster: kdb in test_nginx_baustein_loeschen_527)."""
    monkeypatch.setenv("FR_KONTEN", str(konten_ordner))
    monkeypatch.setenv("FR_MAIL_DATEI", str(tmp_path / "mails.jsonl"))
    with closing(konten.db()) as v, v:
        v.execute("INSERT INTO konten (id, email, name, angelegt, sprache) VALUES (?,?,?,?,?)",
                  ("k-ida", "ida@example.invalid", "Ida", "2026-11-01T00:00:00+00:00", "de"))
    return Path(konten_ordner)


@pytest.fixture
def kdb(sp, tmp_path, monkeypatch):
    """Alte Anordnung: Kontendatenbank im tmp-Ordner, FR_KONTEN auch in der Laufumgebung."""
    ordner = konto_anlegen(tmp_path / "konten", monkeypatch, tmp_path)

    def lauf(*args, **mehr):
        return sp["lauf"](*args, **{"FR_KONTEN": str(ordner), "FR_SPEICHERREISEN": "", **mehr})

    return {**sp, "lauf": lauf, "konten_ordner": ordner}


@pytest.fixture
def swk(sw, tmp_path, monkeypatch):
    """Neue Anordnung: Kontendatenbank an dem FR_KONTEN, das sw für Lauf und Test setzt."""
    sw.konten_ordner = konto_anlegen(sw.env["FR_KONTEN"], monkeypatch, tmp_path)
    return sw


def _seite_da(seiten, reise):
    return (Path(seiten) / reise / "daten.json").exists()


def _neue_deploys(sw, vorher):
    """Reisenamen aus deploy.log seit dem Zählerstand vorher (ohne Dienste-Zeilen)."""
    return [z.split()[0] for z in sw.zeilen("deploy.log")[vorher:] if z and not z.startswith("--")]


def _ok(r):
    assert r.returncode == 0, r.stdout + r.stderr
    return r


def _db_kaputt(ordner):
    (Path(ordner) / "konten.db").write_text("das ist keine SQLite-Datei\n" * 50)


# ---------- Neue Anordnung (sw, main_klon) ----------

def _beide_gebaut(sw):
    _ok(sw.lauf())
    assert _seite_da(sw.seiten, ANDERE) and _seite_da(sw.seiten, VORGEMERKT)


def test_neu_vorgemerkte_reise_wird_entfernt_und_nicht_gebaut(swk):
    """AC-1: vorgemerkt → Exit 0, Seite weg, kein Deploy der Reise, Meldung in der Ausgabe."""
    _beide_gebaut(swk)
    konten.loeschung_vormerken(VORGEMERKT, "k-ida")
    vorher = len(swk.zeilen("deploy.log"))
    r = _ok(swk.lauf())
    assert not (swk.seiten / VORGEMERKT).exists(), r.stdout
    assert VORGEMERKT not in _neue_deploys(swk, vorher), r.stdout
    assert f"{VORGEMERKT} {MELDUNG}" in r.stdout


def test_neu_andere_reise_bleibt_unberuehrt(swk):
    """AC-2: die nicht vorgemerkte Reise behält ihre Seite und wird ohne Änderung nicht neu gebaut."""
    _beide_gebaut(swk)
    seite_vorher = (swk.seiten / ANDERE / "daten.json").read_text()
    konten.loeschung_vormerken(VORGEMERKT, "k-ida")
    vorher = len(swk.zeilen("deploy.log"))
    r = _ok(swk.lauf())
    assert (swk.seiten / ANDERE / "daten.json").read_text() == seite_vorher, r.stdout
    assert ANDERE not in _neue_deploys(swk, vorher), r.stdout
    assert f"{ANDERE} {MELDUNG}" not in r.stdout


def test_neu_immer_baut_vorgemerkte_reise_nicht(swk):
    """AC-3: mit --immer wird die andere Reise gebaut, die vorgemerkte nicht, ihre Seite bleibt weg."""
    _beide_gebaut(swk)
    konten.loeschung_vormerken(VORGEMERKT, "k-ida")
    _ok(swk.lauf())
    vorher = len(swk.zeilen("deploy.log"))
    r = _ok(swk.lauf("--immer"))
    neu = _neue_deploys(swk, vorher)
    assert ANDERE in neu, r.stdout
    assert VORGEMERKT not in neu, r.stdout
    assert not (swk.seiten / VORGEMERKT).exists()


def test_neu_zurueckgeholte_reise_wird_wieder_gebaut(swk):
    """AC-4: nach dem Zurückholen baut der nächste Lauf die Reise wieder, die Seite ist wieder da."""
    _beide_gebaut(swk)
    konten.loeschung_vormerken(VORGEMERKT, "k-ida")
    _ok(swk.lauf())
    assert not (swk.seiten / VORGEMERKT).exists()
    konten.loeschung_zurueckholen(VORGEMERKT, "k-ida")
    vorher = len(swk.zeilen("deploy.log"))
    r = _ok(swk.lauf())
    assert VORGEMERKT in _neue_deploys(swk, vorher), r.stdout
    assert _seite_da(swk.seiten, VORGEMERKT), r.stdout


def test_neu_unlesbare_liste_fail_closed(swk):
    """AC-5: Kontendatenbank ist kein SQLite → Exit 1, Fehlerzeile, kein Deploy, keine Seite entfernt."""
    _beide_gebaut(swk)
    seiten_vorher = {r: (swk.seiten / r / "daten.json").read_text() for r in (ANDERE, VORGEMERKT)}
    _db_kaputt(swk.konten_ordner)
    vorher = len(swk.zeilen("deploy.log"))
    r = swk.lauf("--immer")
    assert r.returncode == 1, r.stdout + r.stderr
    assert FEHLER in r.stdout + r.stderr
    assert _neue_deploys(swk, vorher) == [], r.stdout
    assert {x: (swk.seiten / x / "daten.json").read_text() for x in (ANDERE, VORGEMERKT)} == seiten_vorher


# ---------- Alte Anordnung (sp) ----------

def test_alt_vorgemerkte_reise_wird_entfernt_und_nicht_gebaut(kdb):
    """AC-6: alte Anordnung, vorgemerkt → Exit 0, Seite weg, kein Deploy, Meldung."""
    _ok(kdb["lauf"]())
    assert _seite_da(kdb["seiten"], VORGEMERKT)
    kdb["deploys"]()
    konten.loeschung_vormerken(VORGEMERKT, "k-ida")
    r = _ok(kdb["lauf"]("--immer"))
    assert not (kdb["seiten"] / VORGEMERKT).exists(), r.stdout
    assert VORGEMERKT not in kdb["deploys"](), r.stdout
    assert f"{VORGEMERKT} {MELDUNG}" in r.stdout


def test_alt_unlesbare_liste_fail_closed(kdb):
    """AC-6: alte Anordnung, unlesbare Kontendatenbank → Exit 1, Fehlerzeile, kein Deploy, Seiten bleiben."""
    _ok(kdb["lauf"]())
    assert _seite_da(kdb["seiten"], VORGEMERKT)
    kdb["deploys"]()
    _db_kaputt(kdb["konten_ordner"])
    r = kdb["lauf"]("--immer")
    assert r.returncode == 1, r.stdout + r.stderr
    assert FEHLER in r.stdout + r.stderr
    assert kdb["deploys"]() == [], r.stdout
    assert _seite_da(kdb["seiten"], VORGEMERKT)
