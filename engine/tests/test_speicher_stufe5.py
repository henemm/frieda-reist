"""Tests für Stufe 5 des Reisespeichers (#350, Epic #345, ADR-0009; Spec docs/specs/betrieb/speicher-350-stufe5.md):
Sperre bei der ersten Umschaltung (Funktion, Befehl, Schreibweg, Veröffentlichen), Stempel des Vergleichslaufs mit dem
Git-Baum, Veröffentlichen ohne GitHub, entprellte Warnung „Software-Aktualisierung wartet“, Dokumentation.

Nur mit den beiden erfundenen Beispielreisen (beispielreise: Wanderung mit Varianten, Ida und Karl; stadtwochenende: Reise
ohne Pläne, Tom und Lea) und erfundenen Testdaten, alles unter tmp_path.

Zwei Aufbauten:
  s5   Python-Ebene (AC-1 bis AC-12): ein kleiner Git-Bauordner (FR_WURZEL) mit beiden Beispielreisen unter reisen/, der
       Speicher unter tmp_path mit beiden Reisen (Anfangsvorgang), FR_SPEICHERREISEN mit beiden Namen. Kein Stempel.
  sp   Shell-Läufe (AC-13 bis AC-22) aus test_betrieb.py: Git-Reisen beispielreise und zweitreise im Bauordner, Speicher
       mit beispielreise und stadtwochenende. Die Fixture gibt beispielreise zur Umschaltung frei (AC-23, `freigeben`);
       die Tests hier entfernen diesen Stempel, wo sie die Sperre prüfen.
"""
import inspect
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import types
from pathlib import Path

import pytest

ENGINE = Path(__file__).resolve().parents[1]
WURZEL = ENGINE.parent
BETRIEB = WURZEL / "betrieb"
BEISPIEL = WURZEL / "beispiel" / "reisen"
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import schreiben as sb  # noqa: E402
from test_betrieb import (vf, sp, git, ausfuehrbar, freigeben, SPEICHER_REISEN, T0, hoch,  # noqa: E402,F401
                          _nummer_der_seite)

IDA = {"person": "ida", "name": "Ida", "rolle": "organisator"}
TOM = {"person": "tom", "name": "Tom", "rolle": "organisator"}
ORG = {"beispielreise": IDA, "stadtwochenende": TOM}
REISEN = sorted(ORG)
STUNDE = 3600


# ---------- Aufbau der Python-Ebene ----------

def _kopie(reise, ziel):
    shutil.copytree(BEISPIEL / reise, ziel, ignore=shutil.ignore_patterns(".git"))


def _commit(ordner, text):
    git(ordner, "add", "-A")
    git(ordner, "commit", "-qm", text)


@pytest.fixture
def s5(tmp_path, monkeypatch):
    for k in list(os.environ):
        if k.startswith(("FR_", "SB_", "KN_", "RM_", "VF_")):
            monkeypatch.delenv(k)
    bau = tmp_path / "bau"
    (bau / "reisen").mkdir(parents=True)
    (bau / "software.txt").write_text("Software A\n")
    for r in REISEN:
        _kopie(r, bau / "reisen" / r)
    git(bau, "init", "-q", "-b", "main")
    _commit(bau, "start")
    (tmp_path / "sperren").mkdir()
    stub = ausfuehrbar(tmp_path / "veroeffentlichen.sh", f"#!/bin/sh\necho los >> {tmp_path}/veroeffentlicht\n")
    dienst = tmp_path / "_dienst"
    for k, v in {"FR_WURZEL": bau, "FR_INSTANZ": "probe", "FR_DIENST": dienst, "FR_SPEICHER": tmp_path / "_speicher",
                 "FR_SPEICHERREISEN": ",".join(REISEN), "FR_SPERREN": tmp_path / "sperren",
                 "FR_KONTEN": tmp_path / "konten", "FR_SCHREIBKOPIE": tmp_path / "keine-arbeitskopie",
                 "SB_VEROEFFENTLICHEN": stub, "FR_PYTHON": sys.executable}.items():
        monkeypatch.setenv(k, str(v))
    tmp = tmp_path / "tmp"
    tmp.mkdir()
    monkeypatch.setenv("TMPDIR", str(tmp))
    monkeypatch.setattr(tempfile, "tempdir", str(tmp))
    import reisespeicher as rs
    for r in REISEN:
        rs.importieren(BEISPIEL / r, r, wer=ORG[r]["name"], grund="Beispiel")
    return types.SimpleNamespace(rs=rs, bau=bau, dienst=dienst, tmp=tmp, pfad=tmp_path)


def baum(bau, reise):
    return git(bau, "rev-parse", f"HEAD:reisen/{reise}").strip()


def stempel(s, reise, **felder):
    """Stempel <FR_DIENST>/vergleich/<reise>.json im Format von vergleichslauf.sh; felder überschreiben, None entfernt."""
    d = {"zeit": "2026-11-09T10:00:00Z", "ergebnis": "gleich", "stand": s.rs.stand_nummer(reise),
         "git": git(s.bau, "rev-parse", "HEAD").strip(), "unterschiede": 0, "baum": baum(s.bau, reise)}
    d.update(felder)
    d = {k: v for k, v in d.items() if v is not None}
    datei = s.dienst / "vergleich" / f"{reise}.json"
    datei.parent.mkdir(parents=True, exist_ok=True)
    datei.write_text(json.dumps(d))
    return datei


def gebaut(s, reise):
    datei = s.dienst / "reise-stand" / f"{reise}.gebaut"
    datei.parent.mkdir(parents=True, exist_ok=True)
    datei.write_text(f"{s.rs.stand_nummer(reise)} alt-kennung\n")


def befehl(*args, **env):
    return subprocess.run([sys.executable, str(ENGINE / "reisespeicher.py"), *args], capture_output=True, text=True,
                          env={**os.environ, **env})


def schnappschuss(s):
    dateien = {p.relative_to(s.dienst).as_posix(): p.read_bytes() for p in sorted(s.dienst.rglob("*")) if p.is_file()} \
        if s.dienst.exists() else {}
    return dateien, {r: s.rs.stand_nummer(r) for r in REISEN}


def aendern_in_git(s, reise, text="Änderung in Git (Beispielwert)\n"):
    (s.bau / "reisen" / reise / "git-nachtrag.md").write_text(text)
    _commit(s.bau, f"{reise}: Nachtrag")


# ---------- AC-1 bis AC-6: Funktion und Befehl ----------

@pytest.mark.parametrize("reise", REISEN)
def test_ohne_stempel_ist_die_reise_gesperrt(s5, reise):
    vorher = schnappschuss(s5)
    assert s5.rs.umschaltung_frei(reise) == (False, "kein_stempel")
    r = befehl("umschaltung", reise)
    assert r.returncode == 1 and r.stdout.strip() == "gesperrt kein_stempel", r.stdout + r.stderr
    assert schnappschuss(s5) == vorher


def test_stempel_ungleich_oder_kaputt_sperrt(s5):
    r = "beispielreise"
    for ergebnis in ("unterschied", "fehler"):
        stempel(s5, r, ergebnis=ergebnis)
        assert s5.rs.umschaltung_frei(r) == (False, "stempel_nicht_gleich"), ergebnis
    datei = stempel(s5, r)
    for kaputt in ("", "kein json {", "[]", json.dumps({"stand": 1, "baum": baum(s5.bau, r)})):
        datei.write_text(kaputt)
        assert s5.rs.umschaltung_frei(r) == (False, "stempel_ungueltig"), kaputt
        assert befehl("umschaltung", r).stdout.strip() == "gesperrt stempel_ungueltig"


@pytest.mark.parametrize("reise", REISEN)
def test_stempel_gleich_gibt_die_umschaltung_frei(s5, reise):
    """Der Stempel kommt vom echten betrieb/vergleichslauf.sh (Git-Kopie und Speicher gleich)."""
    v = subprocess.run([str(BETRIEB / "vergleichslauf.sh"), reise], capture_output=True, text=True, env=dict(os.environ))
    assert v.returncode == 0, v.stdout + v.stderr
    assert s5.rs.umschaltung_frei(reise) == (True, "")
    r = befehl("umschaltung", reise)
    assert r.returncode == 0 and r.stdout.strip() == "frei", r.stdout + r.stderr
    # --bis N mit N kleiner als der jetzige Stand: der Schreibweg hat danach geschrieben, der Stempel gilt weiter
    n = s5.rs.stand_nummer(reise)
    s5.rs.vorgang_schreiben(reise, {"nachtrag.md": b"Beispielwert"}, "Test", "test", "nach dem Vergleich")
    v = subprocess.run([str(BETRIEB / "vergleichslauf.sh"), "--bis", str(n), reise], capture_output=True, text=True,
                       env=dict(os.environ))
    assert v.returncode == 0, v.stdout + v.stderr
    assert s5.rs.umschaltung_frei(reise) == (True, "")


def test_veralteter_stempel_sperrt_und_fremde_aenderungen_nicht(s5):
    r = "beispielreise"
    stempel(s5, r)
    assert s5.rs.umschaltung_frei(r) == (True, "")
    # fremde Änderungen: Software und andere Reise
    (s5.bau / "software.txt").write_text("Software B\n")
    _commit(s5.bau, "Software B")
    aendern_in_git(s5, "stadtwochenende")
    assert s5.rs.umschaltung_frei(r) == (True, "")
    # weiterer Vorgang im Speicher nach dem Vergleich: legitime Fortsetzung
    s5.rs.vorgang_schreiben(r, {"nachtrag.md": b"Beispielwert"}, "Test", "test", "nach dem Vergleich")
    assert s5.rs.umschaltung_frei(r) == (True, "")
    # (a) Git ändert sich in reisen/<reise>
    aendern_in_git(s5, r)
    assert s5.rs.umschaltung_frei(r) == (False, "stempel_veraltet")
    # (b) ohne baum
    stempel(s5, r, baum=None)
    assert s5.rs.umschaltung_frei(r) == (False, "stempel_veraltet")
    # (c) stand größer als der Speicher
    stempel(s5, r, stand=s5.rs.stand_nummer(r) + 1)
    assert s5.rs.umschaltung_frei(r) == (False, "stempel_veraltet")
    stempel(s5, r, stand="drei")
    assert s5.rs.umschaltung_frei(r) == (False, "stempel_veraltet")
    stempel(s5, r)
    assert s5.rs.umschaltung_frei(r) == (True, "")


def test_ausnahmen_der_sperre_und_git_nicht_lesbar_sperrt(s5, monkeypatch, tmp_path):
    # (a) nur im Speicher
    shutil.rmtree(s5.bau / "reisen" / "stadtwochenende")
    _commit(s5.bau, "stadtwochenende nur noch im Speicher")
    assert s5.rs.umschaltung_frei("stadtwochenende") == (True, "")
    # (b) schon aus dem Speicher veröffentlicht
    gebaut(s5, "beispielreise")
    assert s5.rs.umschaltung_frei("beispielreise") == (True, "")
    (s5.dienst / "reise-stand" / "beispielreise.gebaut").unlink()
    # (c) nicht in der Liste
    monkeypatch.setenv("FR_SPEICHERREISEN", "stadtwochenende")
    assert s5.rs.umschaltung_frei("beispielreise") == (True, "")
    monkeypatch.setenv("FR_SPEICHERREISEN", ",".join(REISEN))
    # (e) git nicht startbar bei einem Git-Bauordner: gesperrt, nie frei
    leer = tmp_path / "leerer-pfad"
    leer.mkdir()
    monkeypatch.setenv("PATH", str(leer))
    assert s5.rs.umschaltung_frei("beispielreise") == (False, "git_nicht_lesbar")
    monkeypatch.undo()
    # (d) Bauordner ist kein Git-Repo
    s5b = tmp_path / "ohne-git"
    (s5b / "reisen").mkdir(parents=True)
    _kopie("beispielreise", s5b / "reisen" / "beispielreise")
    os.environ.update({"FR_WURZEL": str(s5b), "FR_SPEICHERREISEN": ",".join(REISEN), "FR_DIENST": str(s5.dienst),
                       "FR_SPEICHER": str(s5.pfad / "_speicher")})
    try:
        assert s5.rs.umschaltung_frei("beispielreise") == (True, "")
    finally:
        for k in ("FR_WURZEL", "FR_SPEICHERREISEN", "FR_DIENST", "FR_SPEICHER"):
            os.environ.pop(k, None)


def test_befehl_umschaltung_exit_codes(s5, monkeypatch, tmp_path):
    vorher = schnappschuss(s5)
    for name in ("../x", ""):
        r = befehl("umschaltung", name)
        assert r.returncode == 1 and r.stdout.strip() == "gesperrt stempel_ungueltig", (name, r.stdout + r.stderr)
    assert s5.rs.umschaltung_frei("../x") == (False, "stempel_ungueltig")
    unlesbar = tmp_path / "einstellungen-unlesbar.env"
    unlesbar.mkdir()
    monkeypatch.delenv("FR_SPEICHERREISEN")
    monkeypatch.setenv("FR_EINSTELLUNGEN", str(unlesbar))
    r = befehl("umschaltung", "beispielreise")
    assert r.returncode == 2 and "ERROR" in r.stdout + r.stderr, r.stdout + r.stderr
    assert schnappschuss(s5) == vorher


# ---------- AC-7 bis AC-11: Schreibweg ----------

def schreib(reise, text="Gibt es dort samstags einen Markt? (Beispielwert)"):
    return sb.anwenden_extern(sb.Schreiber(Path(os.environ["FR_WURZEL"])), reise, "frage_anlegen",
                              {**ORG[reise], "args": {"text": text}})


@pytest.fixture
def unterprozesse(monkeypatch):
    """Hält jeden Aufruf von schreiben.befehl_mit_frist fest (der Unterprozess `anwenden`) und reicht ihn weiter."""
    aufrufe = []
    echt = sb.befehl_mit_frist

    def attrappe(*a, **k):
        aufrufe.append(repr(a) + repr(k))
        return echt(*a, **k)
    monkeypatch.setattr(sb, "befehl_mit_frist", attrappe)
    return aufrufe


@pytest.mark.parametrize("reise", REISEN)
def test_schreibweg_lehnt_gesperrte_reise_ab_und_schreibt_nichts(s5, unterprozesse, reise):
    vorher = s5.rs.stand_nummer(reise)
    code, a = schreib(reise)
    assert code == 503 and a["ok"] is False, (code, a)
    assert a["fehler_code"] == "schreiben.dienst.umschaltung_nicht_freigegeben", a
    assert s5.rs.stand_nummer(reise) == vorher
    assert not list(s5.tmp.iterdir()), "temporärer Ordner nicht gelöscht"
    assert not [x for x in unterprozesse if "anwenden" in x], unterprozesse


def test_schreibweg_schreibt_nach_freigabe(s5):
    r = "beispielreise"
    stempel(s5, r)
    vorher = s5.rs.stand_nummer(r)
    code, a = schreib(r)
    assert code == 200 and a["ok"], a
    assert s5.rs.stand_nummer(r) == vorher + 1
    aendern_in_git(s5, r)                                         # Stempel veraltet, kein .gebaut
    code, a = schreib(r, "Zweite Frage (Beispielwert)")
    assert code == 503 and a["fehler_code"] == "schreiben.dienst.umschaltung_nicht_freigegeben", a
    assert s5.rs.stand_nummer(r) == vorher + 1


def test_schreibweg_sperrt_weder_umgeschaltete_noch_neue_reisen(s5):
    gebaut(s5, "beispielreise")                                   # die schon umgeschaltete Testreise (#250)
    code, a = schreib("beispielreise")
    assert code == 200 and a["ok"], a
    shutil.rmtree(s5.bau / "reisen" / "stadtwochenende")
    _commit(s5.bau, "stadtwochenende nur noch im Speicher")
    code, a = schreib("stadtwochenende")
    assert code == 200 and a["ok"], a


def test_reise_nicht_im_speicher_behaelt_ihren_fehler(s5, monkeypatch):
    _kopie("stadtwochenende", s5.bau / "reisen" / "zweitreise")
    _commit(s5.bau, "zweitreise nur in Git")
    monkeypatch.setenv("FR_SPEICHERREISEN", ",".join(REISEN + ["zweitreise"]))
    code, a = sb.anwenden_extern(sb.Schreiber(s5.bau), "zweitreise", "frage_anlegen", {**TOM, "args": {"text": "x"}})
    assert code == 503 and a["fehler_code"] == "schreiben.dienst.reise_nicht_im_speicher", a


def test_umschaltung_text_steht_in_allen_sprachen(monkeypatch):
    import texte
    monkeypatch.setenv("FR_TEXTE_ZUSATZ", "xx")                   # die Pseudo-Sprache der Tests zählt mit
    k = "schreiben.dienst.umschaltung_nicht_freigegeben"
    for sp_ in texte.sprachen():
        assert k in texte.sprache(sp_).TEXTE, sp_
        t = texte.t(sp_, k)
        assert t.strip() not in ("", k) and not re.search(r"\{\w+\}", t), (sp_, t)
    de = texte.t("de", k)
    assert "Vergleich" in de and re.search("[äöüÄÖÜß]", de), de


def test_vergleichslauf_schreibt_den_git_baum(s5):
    for r in REISEN:
        v = subprocess.run([str(BETRIEB / "vergleichslauf.sh"), r], capture_output=True, text=True, env=dict(os.environ))
        assert v.returncode == 0, v.stdout + v.stderr
        s = json.loads((s5.dienst / "vergleich" / f"{r}.json").read_text())
        assert {"zeit", "ergebnis", "stand", "git", "unterschiede", "baum"} <= set(s)
        assert s["baum"] == baum(s5.bau, r) and s["ergebnis"] == "gleich"
        assert s["arbeitsordner"] == 0
    assert git(s5.bau, "status", "--porcelain").strip() == ""


def test_vergleichslauf_nimmt_ignorierte_grundkarten_aus_dem_arbeitsordner(s5):
    """#479: Grundkarten liegen nicht in Git (.gitignore), aber im Bauordner und damit im Import. Der Vergleich nimmt sie
    aus dem Arbeitsordner dazu und vergleicht sie byte-genau; nicht ignorierte, ungesicherte Dateien zählen nicht."""
    r = "beispielreise"
    (s5.bau / ".gitignore").write_text("reisen/*/medien/karte/*.pmtiles\nreisen/*/medien/karte/*.quelle.txt\n")
    _commit(s5.bau, "Grundkarten nicht in Git")
    karte = s5.bau / "reisen" / r / "medien" / "karte"
    karte.mkdir(parents=True, exist_ok=True)
    (karte / "grundkarte.pmtiles").write_bytes(b"Beispielwert Karte\x00\x01")
    (karte / "grundkarte.pmtiles.quelle.txt").write_text("Beispielwert Quelle\n")
    s5.rs.importieren(s5.bau / "reisen" / r, r, wer="Ida", grund="Anfangsvorgang mit Karte")

    def lauf():
        v = subprocess.run([str(BETRIEB / "vergleichslauf.sh"), r], capture_output=True, text=True, env=dict(os.environ))
        return v, json.loads((s5.dienst / "vergleich" / f"{r}.json").read_text())

    v, s = lauf()
    assert v.returncode == 0, v.stdout + v.stderr
    assert s["ergebnis"] == "gleich" and s["arbeitsordner"] == 2, s
    assert s5.rs.umschaltung_frei(r) == (True, "")
    # abweichende Kartendatei: Unterschied, keine Freigabe
    (karte / "grundkarte.pmtiles").write_bytes(b"andere Karte")
    v, s = lauf()
    assert v.returncode == 1 and "verschieden: medien/karte/grundkarte.pmtiles" in v.stdout, v.stdout + v.stderr
    assert s["ergebnis"] == "unterschied" and s5.rs.umschaltung_frei(r)[0] is False
    # fehlende Kartendatei im Arbeitsordner: nur im Speicher
    (karte / "grundkarte.pmtiles").unlink()
    v, s = lauf()
    assert v.returncode == 1 and "nur im Speicher: medien/karte/grundkarte.pmtiles" in v.stdout, v.stdout
    # ungesicherte, nicht ignorierte Datei zählt nicht (nur der Git-Stand und Ignoriertes)
    (karte / "grundkarte.pmtiles").write_bytes(b"Beispielwert Karte\x00\x01")
    (s5.bau / "reisen" / r / "streuner.md").write_text("nicht gesichert\n")
    v, s = lauf()
    assert v.returncode == 0 and s["arbeitsordner"] == 2, v.stdout + v.stderr


# ---------- AC-13 bis AC-17: Sperre im Veröffentlichen (Shell-Läufe über sp) ----------

def sperren(sp, reise):
    """Den Freigabe-Stempel der Fixture entfernen."""
    (sp["tmp"] / "dienst" / "vergleich" / f"{reise}.json").unlink(missing_ok=True)


def git_reisen(sp, *, rein=(), raus=()):
    """Reisen im Reisen-Repo (origin) hinein (Kopie der Beispielreise) oder heraus nehmen, Bauordner nachziehen."""
    quelle = sp["tmp"] / "quelle"
    for r in rein:
        shutil.rmtree(quelle / "reisen" / r, ignore_errors=True)
        _kopie(r, quelle / "reisen" / r)
    for r in raus:
        shutil.rmtree(quelle / "reisen" / r)
    _commit(quelle, "Reisen geändert")
    git(sp["arbeit"], "pull", "-q", "--ff-only")


def handstempel(sp, reise, **felder):
    d = {"zeit": "2026-11-09T10:00:00Z", "ergebnis": "gleich", "stand": sp["speicher"].stand_nummer(reise),
         "git": sp["kopf"](), "unterschiede": 0, "baum": git(sp["arbeit"], "rev-parse", f"HEAD:reisen/{reise}").strip()}
    d.update(felder)
    datei = sp["tmp"] / "dienst" / "vergleich" / f"{reise}.json"
    datei.parent.mkdir(parents=True, exist_ok=True)
    datei.write_text(json.dumps(d))


def nicht_gebaut(sp, reise):
    assert reise not in sp["zeilen"]("deploy.log")
    assert not (sp["tmp"] / "dienst" / "bau" / "reisen" / reise).exists()
    assert not (sp["tmp"] / "dienst" / "reise-stand" / f"{reise}.gebaut").exists()
    assert sp["lauf_stand"](reise) is None


@pytest.mark.parametrize("gesperrt,frei", [("beispielreise", "stadtwochenende"), ("stadtwochenende", "beispielreise")])
def test_veroeffentlichen_baut_gesperrte_reise_nicht(sp, gesperrt, frei):
    git_reisen(sp, rein=[gesperrt], raus=[frei] if frei == "beispielreise" else [])
    sperren(sp, gesperrt)
    sperren(sp, frei)
    r = sp["lauf"]()
    assert r.returncode == 0, r.stdout + r.stderr
    nicht_gebaut(sp, gesperrt)
    assert any(gesperrt in z and "kein_stempel" in z for z in r.stdout.splitlines()), r.stdout
    assert frei in sp["zeilen"]("deploy.log") and frei in sp["zeilen"]("frei.log")
    assert sp["rot"]() is None and sp["pings"]() == 1


def test_veroeffentlichen_baut_nur_mit_gueltigem_stempel(sp):
    r = "beispielreise"
    handstempel(sp, r, ergebnis="unterschied")
    sp["lauf"]()
    nicht_gebaut(sp, r)
    handstempel(sp, r)                                             # gleich, dann ändert sich Git: veraltet
    sp["inhalt"](r)
    git(sp["arbeit"], "pull", "-q", "--ff-only")
    sp["deploys"]()
    sp["lauf"]()
    assert r not in sp["deploys"]()
    assert not (sp["tmp"] / "dienst" / "reise-stand" / f"{r}.gebaut").exists()
    handstempel(sp, r)                                             # gültig
    sp["lauf"]()
    assert r in sp["deploys"]()
    nummer, kennung = (sp["tmp"] / "dienst" / "reise-stand" / f"{r}.gebaut").read_text().split()[:2]
    assert int(nummer) == sp["speicher"].stand_nummer(r) and kennung
    sp["lauf"]()
    assert r not in sp["deploys"]()


@pytest.mark.parametrize("reise", SPEICHER_REISEN)
def test_umschaltung_ende_zu_ende_mit_dem_echten_vergleichslauf(sp, reise, monkeypatch):
    git_reisen(sp, rein=[reise])
    sperren(sp, reise)
    sp["lauf"]()
    nicht_gebaut(sp, reise)                                        # ohne Vergleich keine Umschaltung
    v = subprocess.run([str(BETRIEB / "vergleichslauf.sh"), reise], env=sp["env"], capture_output=True, text=True)
    assert v.returncode == 0, v.stdout + v.stderr
    assert "baum" in json.loads((sp["tmp"] / "dienst" / "vergleich" / f"{reise}.json").read_text())
    sp["lauf"]()
    assert reise in sp["deploys"]()
    # anschließend über den Schreibweg
    for k in ("FR_WURZEL", "FR_DIENST", "FR_SPEICHER", "FR_SPEICHERREISEN", "FR_SPERREN", "FR_INSTANZ"):
        monkeypatch.setenv(k, sp["env"][k])
    monkeypatch.setenv("FR_KONTEN", str(sp["tmp"] / "konten"))
    monkeypatch.setenv("FR_SCHREIBKOPIE", str(sp["tmp"] / "keine-arbeitskopie"))
    monkeypatch.setenv("SB_VEROEFFENTLICHEN", str(ausfuehrbar(sp["tmp"] / "stummel.sh", "#!/bin/sh\nexit 0\n")))
    vorher = sp["speicher"].stand_nummer(reise)
    code, a = schreib(reise)
    assert code == 200 and a["ok"], a
    assert sp["speicher"].stand_nummer(reise) == vorher + 1


def _py_falle(sp):
    py = ausfuehrbar(sp["tmp"] / "python-falle5", f'#!/bin/sh\necho "$@" >> {sp["tmp"]}/py5.log\nexec {sys.executable} "$@"\n')
    sp["env"]["FR_PYTHON"] = str(py)


def test_umgeschaltete_reise_wird_nach_dem_deploy_weiter_gebaut_ohne_handschritt(sp):
    r = "beispielreise"
    sp["lauf"]()                                                   # mit Freigabe der Fixture gebaut, .gebaut liegt
    assert (sp["tmp"] / "dienst" / "reise-stand" / f"{r}.gebaut").exists()
    sperren(sp, r)                                                 # wie die Testreise: kein Stempel vorhanden
    _py_falle(sp)
    sp["deploys"]()
    sp["neuer_commit"]()                                           # Software-Wechsel
    a = sp["lauf"]()
    assert r in sp["deploys"](), a.stdout + a.stderr
    sp["speicher"].vorgang_schreiben(r, {"neu.md": b"1"}, "Test", "test", "neu")
    b = sp["lauf"]("--immer")
    assert r in sp["deploys"](), b.stdout + b.stderr
    assert not any("umschaltung" in z for z in sp["zeilen"]("py5.log"))
    assert "not cleared" not in a.stdout + b.stdout
    assert a.returncode == 0 and b.returncode == 0
    # Schutz: die Prüfung gibt es wirklich (sonst bewiese das Fehlen des Aufrufs nichts)
    assert "umschaltung" in (BETRIEB / "veroeffentlichen.sh").read_text(encoding="utf-8")


def test_nur_im_speicher_baut_und_leere_liste_aendert_nichts(sp):
    sperren(sp, "stadtwochenende")
    _py_falle(sp)
    sp["lauf"]()
    assert "stadtwochenende" in sp["deploys"]()
    (sp["tmp"] / "py5.log").unlink(missing_ok=True)
    sp["env"]["FR_SPEICHERREISEN"] = ""
    sp["lauf"]()
    assert "reisespeicher" not in " ".join(sp["zeilen"]("py5.log"))
    # Schutz: Der Befehl, der hier nicht gerufen werden darf, existiert
    assert befehl("umschaltung", "gibtesnicht", FR_SPEICHERREISEN="").stdout.strip() == "frei"


# ---------- AC-18 bis AC-22: Veröffentlichen ohne GitHub ----------

def ohne_github(sp):
    """origin unerreichbar; gh, ls-remote und der Workflow-Start als Attrappen, die ihren Aufruf festhalten und scheitern."""
    t = sp["tmp"]
    git(sp["arbeit"], "remote", "set-url", "origin", str(t / "gibtes-nicht"))
    ausfuehrbar(t / "bin/gh", f'#!/bin/sh\necho "$@" >> {t}/gh.log\nexit 1\n')
    sp["env"]["VF_LSREMOTE"] = str(ausfuehrbar(t / "ls-remote.sh", f'#!/bin/sh\necho "$@" >> {t}/lsremote.log\nexit 128\n'))
    sp["env"]["VF_NACHZIEHEN"] = str(ausfuehrbar(t / "nachziehen.sh", f'#!/bin/sh\necho los >> {t}/nachziehen.log\nexit 1\n'))


def mit_github(sp):
    git(sp["arbeit"], "remote", "set-url", "origin", str(sp["tmp"] / "quelle"))


def merker(sp):
    datei = sp["tmp"] / "dienst" / "software-wartet"
    if not datei.exists():
        return None
    return dict(z.split("=", 1) for z in datei.read_text(encoding="utf-8").splitlines() if "=" in z)


def test_gh_und_ls_remote_aendern_das_ergebnis_des_laufs_nicht(sp):
    t = sp["tmp"]
    ablage = t / "ablage"
    ablage.mkdir()
    sp["env"]["FR_ABLAGE"] = str(ablage)
    sp["env"]["VF_LSREMOTE"] = str(ausfuehrbar(t / "ls-remote.sh", f'#!/bin/sh\necho "$@" >> {t}/lsremote.log\nexit 128\n'))
    sp["env"]["VF_NACHZIEHEN"] = str(ausfuehrbar(t / "nachziehen.sh", f'#!/bin/sh\necho los >> {t}/nachziehen.log\nexit 1\n'))
    ausfuehrbar(t / "bin/git", f"""#!/bin/sh
case "$*" in *fetch*) [ -e {sp["seiten"]}/stadtwochenende/daten.json ] && echo vorher >> {t}/ablauf.log || echo nachher >> {t}/ablauf.log;; esac
exec /usr/bin/git "$@"
""")
    (ablage / "_anstoss.json").write_text('{"zeit": "2026-11-01T12:00:00+00:00", "reise": "stadtwochenende", "von": "Tom"}\n')
    r = sp["lauf"]()
    assert r.returncode == 0, r.stdout + r.stderr
    assert sp["zeilen"]("ablauf.log") == ["vorher"]               # Speicher-Teil vor git fetch
    assert "could not be started" in r.stdout
    assert len([z for z in sp["zeilen"]("melden.log") if "Publish request failed" in z]) <= 1
    sp["lauf"]()
    assert len([z for z in sp["zeilen"]("melden.log") if "Publish request failed" in z]) <= 1


def test_ohne_github_ist_der_lauf_gruen_wenn_keine_git_reise_uebrig_ist(sp):
    git_reisen(sp, raus=["zweitreise"])                            # in Git liegt nur noch beispielreise (in der Liste)
    ohne_github(sp)
    r = sp["lauf"](VF_JETZT=str(T0))
    assert r.returncode == 0, r.stdout + r.stderr
    for reise in SPEICHER_REISEN:
        assert _nummer_der_seite(sp, reise) == sp["speicher"].stand_nummer(reise)
    assert (sp["tmp"] / "dienst" / "veroeffentlichen-erfolg").exists() and sp["pings"]() == 1
    assert sp["rot"]() is None
    assert "git fetch failed" in r.stdout
    assert merker(sp) == {"seit": str(T0), "gemeldet": "0"}
    assert sp["zeilen"]("gh.log") == [] and sp["zeilen"]("lsremote.log") == [] and sp["zeilen"]("nachziehen.log") == []


def test_ohne_github_mit_git_reise_gruen_aber_ohne_heartbeat(sp):
    sp["speicher"].vorgang_schreiben("stadtwochenende", {"z.md": b"1"}, "Test", "test", "z")
    ohne_github(sp)
    r = sp["lauf"](VF_JETZT=str(T0))
    assert r.returncode == 0, r.stdout + r.stderr
    for reise in SPEICHER_REISEN:
        assert _nummer_der_seite(sp, reise) == sp["speicher"].stand_nummer(reise)
    assert "zweitreise" not in sp["deploys"]() and sp["rot"]() is None
    assert not (sp["tmp"] / "dienst" / "veroeffentlichen-erfolg").exists() and sp["pings"]() == 0
    assert "git fetch failed" in r.stdout and merker(sp)["gemeldet"] == "0"


def test_ohne_speicherreisen_scheitert_git_fetch_wie_bisher(sp):
    sp["env"]["FR_SPEICHERREISEN"] = ""
    ohne_github(sp)
    r = sp["lauf"](VF_JETZT=str(T0))
    assert r.returncode != 0, r.stdout + r.stderr                     # wie bisher (heute Exit 128 aus git fetch)
    assert merker(sp) is None


def test_ohne_github_rote_speicher_reise_endet_mit_exit_1(sp):
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


# ---------- AC-23 bis AC-25: kein Abschalter, Dokumentation ----------

def test_sperre_hat_keinen_schalter_zum_abschalten():
    import reisespeicher
    quelle = inspect.getsource(reisespeicher.umschaltung_frei)
    assert "environ" not in quelle and "getenv" not in quelle, "die Sperre darf keine Umgebungsvariable kennen"
    zeilen = (BETRIEB / "veroeffentlichen.sh").read_text(encoding="utf-8").splitlines()
    stellen = [i for i, z in enumerate(zeilen) if "umschaltung" in z and not z.lstrip().startswith("#")]
    assert stellen, "veroeffentlichen.sh ruft die Prüfung nicht auf"
    for i in stellen:
        umgebung = "\n".join(zeilen[max(0, i - 4):i + 1])
        assert not re.search(r"\$\{?(VF|FR)_\w*(SPERRE|UMSCHALT|PRUEF|OHNE|SKIP)", umgebung), umgebung


def _abschnitt(text, ueberschrift):
    teile = re.split(r"(?m)^(#{2,3} .*)$", text)
    for i, t in enumerate(teile):
        if t.strip().lstrip("#").strip() == ueberschrift:
            return teile[i + 1]
    raise AssertionError(f"Abschnitt „{ueberschrift}“ fehlt")


def test_doku_beschreibt_die_umschaltung_einer_reise():
    text = (WURZEL / "docs" / "betrieb.md").read_text(encoding="utf-8")
    abschnitt = _abschnitt(text, "Umschaltung einer Reise")
    for wort in ("Testreise", "kleinste echte Reise", "importieren", "--ab", "vergleichslauf.sh", "FR_SPEICHERREISEN",
                 "publish_status", "exportieren", "zuruecksetzen", ".gebaut", "Archiv", "FR_SOFTWARE_WARTET_STUNDEN"):
        assert wort in abschnitt, wort
    assert "keine sperre" not in text.lower()
    assert "| `FR_SOFTWARE_WARTET_STUNDEN`" in text or "`FR_SOFTWARE_WARTET_STUNDEN` |" in text
    assert "FR_SOFTWARE_WARTET_STUNDEN" in (BETRIEB / "einstellungen.beispiel").read_text(encoding="utf-8")
    kopf = "\n".join(z for z in (BETRIEB / "veroeffentlichen.sh").read_text(encoding="utf-8").splitlines()[:80]
                     if z.startswith("#"))
    assert "FR_SOFTWARE_WARTET_STUNDEN" in kopf and "git fetch" in kopf and "vergleichslauf" in kopf


def test_vergleichslauf_kopf_nennt_den_stempel_als_voraussetzung():
    kopf = "\n".join(z for z in (BETRIEB / "vergleichslauf.sh").read_text(encoding="utf-8").splitlines()[:25]
                     if z.startswith("#"))
    assert "keine sperre" not in kopf.lower()
    assert "Voraussetzung" in kopf and "baum" in kopf and "#350" in kopf


def test_adr_0009_hat_die_zeile_stufe_5():
    text = (WURZEL / "docs" / "adr" / "0009-reisespeicher.md").read_text(encoding="utf-8")
    for ueberschrift in ("Konsequenzen", "Verlauf"):
        abschnitt = _abschnitt(text, ueberschrift)
        assert any("Stufe 5" in z and "#350" in z for z in abschnitt.splitlines()), ueberschrift


def test_doku_nennt_keinen_handschritt_fuer_umgeschaltete_reisen():
    abschnitt = _abschnitt((WURZEL / "docs" / "betrieb.md").read_text(encoding="utf-8"), "Umschaltung einer Reise")
    saetze = [s for s in re.split(r"(?<=[.:;])\s+", abschnitt) if ".gebaut" in s]
    assert any("kein Handschritt" in s or "keinen Handschritt" in s for s in saetze), saetze
