"""Tests für Stufe 5 des Reisespeichers (#350, Epic #345, ADR-0009), soweit sie nach dem Rückbau des Git-Wegs (#557) gilt:
Veröffentlichen ohne GitHub und die entprellte Warnung „Software-Aktualisierung wartet“. Die Sperre bei der ersten
Umschaltung, der Vergleichslauf und der Git-Weg sind mit #557 entfernt, ihre Tests mit ihnen.

Nur mit den beiden erfundenen Beispielreisen (beispielreise: Wanderung mit Varianten, Ida und Karl; stadtwochenende: Reise
ohne Pläne, Tom und Lea) und erfundenen Testdaten, alles unter tmp_path. Aufbau: die Fixture `sp` aus test_betrieb.py
(Software-Klon mit origin, beide Reisen im Speicher).
"""
import sys
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[1]
WURZEL = ENGINE.parent
BETRIEB = WURZEL / "betrieb"
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_betrieb import sp, git, ausfuehrbar, SPEICHER_REISEN, T0, hoch, _nummer_der_seite  # noqa: E402,F401

STUNDE = 3600


def ohne_github(sp):
    """origin unerreichbar; gh als Attrappe, die ihren Aufruf festhält und scheitert."""
    t = sp["tmp"]
    git(sp["arbeit"], "remote", "set-url", "origin", str(t / "gibtes-nicht"))
    ausfuehrbar(t / "bin/gh", f'#!/bin/sh\necho "$@" >> {t}/gh.log\nexit 1\n')


def mit_github(sp):
    git(sp["arbeit"], "remote", "set-url", "origin", str(sp["quelle"]))


def merker(sp):
    datei = sp["tmp"] / "dienst" / "software-wartet"
    if not datei.exists():
        return None
    return dict(z.split("=", 1) for z in datei.read_text(encoding="utf-8").splitlines() if "=" in z)


def test_ohne_github_ist_der_lauf_gruen_mit_heartbeat(sp):
    """AC-18 bis AC-20: Ohne GitHub sind alle Reisen aus dem Speicher veröffentlicht, der Lauf ist grün mit Heartbeat; nur
    die Software wartet (Merker), gh wird nie gerufen."""
    ohne_github(sp)
    r = sp["lauf"](VF_JETZT=str(T0))
    assert r.returncode == 0, r.stdout + r.stderr
    for reise in SPEICHER_REISEN:
        assert _nummer_der_seite(sp, reise) == sp["speicher"].stand_nummer(reise)
    assert (sp["tmp"] / "dienst" / "veroeffentlichen-erfolg").exists() and sp["pings"]() == 1
    assert sp["rot"]() is None
    assert "git fetch of the software failed" in r.stdout
    assert merker(sp) == {"seit": str(T0), "gemeldet": "0"}
    assert sp["zeilen"]("gh.log") == []


def test_ohne_github_rote_speicher_reise_endet_mit_exit_1(sp):
    """AC-21: Eine rote Reise bleibt auch ohne GitHub ein roter Lauf (Exit 1, kein Heartbeat); der Alarm kommt erst über
    der Schwelle."""
    ohne_github(sp)
    (sp["tmp"] / "kaputt-stadtwochenende").write_text("Bau gescheitert")
    r = sp["lauf"](VF_JETZT=str(T0))
    assert r.returncode == 1 and "unbound variable" not in r.stdout + r.stderr, r.stdout + r.stderr
    assert sp["rot"]()["art"] == "reise" and "stadtwochenende" in sp["rot"]()["reisen"]
    assert hoch(sp) == [] and sp["pings"]() == 0
    sp["speicher"].vorgang_schreiben("stadtwochenende", {"r.md": b"1"}, "Test", "test", "r")
    r = sp["lauf"](VF_JETZT=str(T0 + 2 * STUNDE))                   # über der Schwelle
    assert r.returncode == 1 and "unbound variable" not in r.stdout + r.stderr, r.stdout + r.stderr
    assert hoch(sp) and sp["pings"]() == 0


def _warnungen(r):
    return [z for z in r.stdout.splitlines() if "Software update waiting" in z]


def test_software_wartet_warnt_genau_einmal_je_stoerung_ohne_nachricht(sp):
    """AC-22: Nach FR_SOFTWARE_WARTET_STUNDEN (Vorgabe 6) genau eine Warnzeile je Störung, nie eine Nachricht; gelingt
    git fetch wieder, endet die Störung."""
    ohne_github(sp)
    r = sp["lauf"](VF_JETZT=str(T0))
    assert _warnungen(r) == [] and merker(sp) == {"seit": str(T0), "gemeldet": "0"}, r.stdout + r.stderr
    r = sp["lauf"](VF_JETZT=str(T0 + STUNDE))
    assert _warnungen(r) == [] and merker(sp)["gemeldet"] == "0" and merker(sp)["seit"] == str(T0)
    r = sp["lauf"](VF_JETZT=str(T0 + 6 * STUNDE))
    assert len(_warnungen(r)) == 1 and merker(sp)["gemeldet"] == "1", r.stdout
    r = sp["lauf"](VF_JETZT=str(T0 + 7 * STUNDE))
    assert _warnungen(r) == [] and merker(sp)["gemeldet"] == "1"
    mit_github(sp)
    sp["lauf"](VF_JETZT=str(T0 + 8 * STUNDE))
    assert merker(sp) is None
    ohne_github(sp)
    sp["lauf"](VF_JETZT=str(T0 + 10 * STUNDE))
    assert merker(sp) == {"seit": str(T0 + 10 * STUNDE), "gemeldet": "0"}
    assert len(_warnungen(sp["lauf"](VF_JETZT=str(T0 + 16 * STUNDE)))) == 1
    assert sp["zeilen"]("melden.log") == []                          # nie eine Nachricht an den Betrieb
    # ungültige Frist fällt auf 6 Stunden zurück
    for wert in ("abc", "", "-3"):
        (sp["tmp"] / "dienst" / "software-wartet").unlink()
        sp["lauf"](VF_JETZT=str(T0), FR_SOFTWARE_WARTET_STUNDEN=wert)
        assert _warnungen(sp["lauf"](VF_JETZT=str(T0 + 5 * STUNDE), FR_SOFTWARE_WARTET_STUNDEN=wert)) == [], wert
        assert len(_warnungen(sp["lauf"](VF_JETZT=str(T0 + 6 * STUNDE), FR_SOFTWARE_WARTET_STUNDEN=wert))) == 1, wert
    # gültige Frist wirkt
    (sp["tmp"] / "dienst" / "software-wartet").unlink()
    sp["lauf"](VF_JETZT=str(T0), FR_SOFTWARE_WARTET_STUNDEN="2")
    assert len(_warnungen(sp["lauf"](VF_JETZT=str(T0 + 2 * STUNDE), FR_SOFTWARE_WARTET_STUNDEN="2"))) == 1
    assert sp["zeilen"]("melden.log") == []


def test_doku_nennt_die_frist_der_warnung():
    text = (WURZEL / "docs" / "betrieb.md").read_text(encoding="utf-8")
    assert "| `FR_SOFTWARE_WARTET_STUNDEN`" in text or "`FR_SOFTWARE_WARTET_STUNDEN` |" in text
    assert "FR_SOFTWARE_WARTET_STUNDEN" in (BETRIEB / "einstellungen.beispiel").read_text(encoding="utf-8")
    kopf = "\n".join(z for z in (BETRIEB / "veroeffentlichen.sh").read_text(encoding="utf-8").splitlines()[:80]
                     if z.startswith("#"))
    assert "FR_SOFTWARE_WARTET_STUNDEN" in kopf and "git fetch" in kopf
