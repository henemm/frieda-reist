"""Tests für #454: Software direkt aus dem öffentlichen Repo, alle Reisen im Speicher (Spec
docs/specs/betrieb/software-weg-454.md, ADR-0009 Stufe 5).

Nur mit den beiden erfundenen Beispielreisen (beispielreise: Wanderung mit Varianten, Ida und Karl; stadtwochenende: Reise
ohne Pläne, Tom und Lea) und erfundenen Testdaten, alles unter tmp_path.

Aufbauten:
  l1   Lieferung 1, Python-Ebene: kleiner Git-Bauordner (FR_WURZEL) mit beiden Beispielreisen unter reisen/, leerer
       Speicher, kein FR_SPEICHERREISEN. Im Speicher ist, was im Speicher steht.
  sp   Lieferung 1, Shell-Lauf (aus test_betrieb.py), hier ohne Wirkung von FR_SPEICHERREISEN.
  sw   Lieferung 2, neuer Zustand: Software-Klon <FR_SEITEN>/_software aus einem lokalen Software-Repo (Kopie von betrieb/,
       engine als Verweis), Umzug fertig (<FR_DIENST>/umzug-454), letzter guter Stand in <FR_DIENST>/software-gut, beide
       Beispielreisen im Speicher. Kein Reisen-Repo, kein gh (Attrappe im PATH, die jeden Aufruf festhält und scheitert).
  alt  Lieferung 2, alter Zustand (Bauordner mit Submodul frieda/ aus test_betrieb.vf) für den Umzug.

Attrappen der Lieferung 2 (Vertrag für die Umsetzung):
  VF_CINACHWEIS <url> <commit>   Nachweis der Pflichtprüfungen; gibt „true“ aus, wenn grün; Exit ≠ 0: nicht abrufbar
  VF_PRUEFEN <ordner>            Tests auf dem Server, aufgerufen im Arbeitsbaum des geprüften Commits; „engine/tests“ für
                                 die Software, <FR_DIENST>/instanz/tests für die optionalen Prüfungen der Instanz
  VF_VENV <ordner> <requirements> baut die Python-Umgebung unter <FR_DIENST>/python (Umzug, geänderte Abhängigkeiten)
  VF_UNITS pruefen|installieren  Abgleich der Units; FR_WURZEL und FR_PYTHON in der Umgebung nennen die Pfade
  VF_DEPLOY, VF_FREISCHALTEN, VF_NGINX, VF_ROTMELDEN, VF_JETZT, VF_NACHZIEHEN wie bisher
"""
import json
import os
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
from test_betrieb import (vf, sp, git, ausfuehrbar, freigeben, SAUBER, T0, GIT, GIT_ERLAUBT,  # noqa: E402,F401
                          ALARMSTELLEN)

IDA = {"person": "ida", "name": "Ida", "rolle": "organisator"}
TOM = {"person": "tom", "name": "Tom", "rolle": "organisator"}
ORG = {"beispielreise": IDA, "stadtwochenende": TOM}
REISEN = sorted(ORG)
MINUTE = 60


def _kopie(reise, ziel):
    shutil.copytree(BEISPIEL / reise, ziel, ignore=shutil.ignore_patterns(".git"))


def _commit(ordner, text):
    git(ordner, "add", "-A")
    git(ordner, "commit", "-qm", text)


# ======================================================================================================================
# Lieferung 1: alle Reisen im Speicher
# ======================================================================================================================

@pytest.fixture
def l1(tmp_path, monkeypatch):
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
                 "FR_SPERREN": tmp_path / "sperren", "FR_KONTEN": tmp_path / "konten",
                 "FR_SCHREIBKOPIE": tmp_path / "keine-arbeitskopie", "SB_VEROEFFENTLICHEN": stub,
                 "FR_PYTHON": sys.executable}.items():
        monkeypatch.setenv(k, str(v))
    tmp = tmp_path / "tmp"
    tmp.mkdir()
    monkeypatch.setenv("TMPDIR", str(tmp))
    monkeypatch.setattr(tempfile, "tempdir", str(tmp))
    import instanz
    import reisespeicher as rs
    return types.SimpleNamespace(rs=rs, instanz=instanz, bau=bau, dienst=dienst, pfad=tmp_path)


def _importieren(l, *reisen):
    for r in reisen:
        l.rs.importieren(BEISPIEL / r, r, wer=ORG[r]["name"], grund="Beispiel")


def _nur_im_speicher(l, *reisen):
    """Die Reisen liegen nur im Speicher (aus dem Git-Bauordner entfernt)."""
    _importieren(l, *reisen)
    for r in reisen:
        shutil.rmtree(l.bau / "reisen" / r)
    _commit(l.bau, "nur noch im Speicher")


def _stempel(l, reise):
    datei = l.dienst / "vergleich" / f"{reise}.json"
    return json.loads(datei.read_text()) if datei.exists() else None


def test_speicherreisen_liest_aus_dem_speicher(l1, monkeypatch):
    """AC-1.1: Im Speicher ist, was im Speicher steht; die Liste der Einstellungen zählt nicht (Python und Shell)."""
    _nur_im_speicher(l1, *REISEN)
    monkeypatch.setenv("FR_SPEICHERREISEN", "andere-reise")
    assert l1.instanz.speicherreisen() == REISEN
    r = subprocess.run(["bash", "-c", f'. "{BETRIEB}/gemeinsam.sh"; speicherreisen; '
                                      'ist_speicherreise beispielreise && echo JA; ist_speicherreise andere-reise || echo NEIN'],
                       capture_output=True, text=True, env={**os.environ})
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.split() == REISEN + ["JA", "NEIN"], r.stdout + r.stderr


def test_fr_speicherreisen_ist_wirkungslos(l1, monkeypatch, tmp_path):
    """AC-1.2: FR_SPEICHERREISEN in Umgebung oder Datei macht keine Reise zur Speicherreise, ohne Fehlermeldung."""
    monkeypatch.setenv("FR_SPEICHERREISEN", ",".join(REISEN))
    assert l1.instanz.speicherreisen() == []
    monkeypatch.delenv("FR_SPEICHERREISEN")
    datei = tmp_path / "einstellungen.env"
    datei.write_text(f"FR_SPEICHERREISEN={','.join(REISEN)}\n")
    monkeypatch.setenv("FR_EINSTELLUNGEN", str(datei))
    assert l1.instanz.speicherreisen() == []


def test_speicherreisen_unlesbarer_speicher_ist_fehler(l1):
    """AC-1.3: Speicher nicht lesbar -> Fehler (fail closed, #361), nie eine leere Liste."""
    (l1.pfad / "_speicher" / "reisen.db").mkdir(parents=True)        # an der Stelle der Datenbank liegt ein Ordner
    with pytest.raises(Exception):
        ergebnis = l1.instanz.speicherreisen()
        pytest.fail(f"keine Ausnahme, sondern {ergebnis!r}")


def _anfrage(pfad, titel, wer):
    return {"id": f"A-20261112-120000-{pfad[:4]}", "erstellt": "2026-11-12T12:00:00+00:00", "name": wer, "art": "Auftrag",
            "daten": {"neue_reise": {"titel": titel, "von": "2027-05-01", "bis": "2027-05-03", "ziel": "", "pfad": pfad,
                                     "personen": {wer.lower(): {"name": wer, "rolle": "organisator"}}, "wer": wer,
                                     "notiz": "Beispielwert"}}}


@pytest.mark.parametrize("pfad,titel,wer", [("wanderung-2027", "Wanderung (Beispielwert)", "Ida"),
                                            ("stadtwochenende-2027", "Stadtwochenende (Beispielwert)", "Tom")],
                         ids=["beispielreise", "stadtwochenende"])
def test_reise_anlegen_entsteht_im_speicher(l1, pfad, titel, wer):
    """AC-1.4: Eine neue Reise entsteht im Speicher (Anfangsvorgang), nie als Ordner im Bauordner."""
    kopf = git(l1.bau, "rev-parse", "HEAD")
    code, a = sb.anwenden_extern(sb.Schreiber(l1.bau), pfad, "reise_anlegen",
                                 {"person": None, "name": wer, "rolle": "organisator",
                                  "args": {"auftrag": _anfrage(pfad, titel, wer)}})
    assert code == 200 and a["ok"], (code, a)
    assert pfad in l1.rs.reisen(mit_vorgemerkten=True)
    assert l1.rs.stand_nummer(pfad) >= 1
    assert "reise.yaml" in l1.rs.aktueller_stand(pfad) or any(p.endswith("reise.yaml") for p in l1.rs.aktueller_stand(pfad))
    assert not (l1.bau / "reisen" / pfad).exists()
    assert git(l1.bau, "rev-parse", "HEAD") == kopf and not git(l1.bau, "status", "--porcelain")
    assert pfad in l1.instanz.speicherreisen()


@pytest.mark.parametrize("reise", REISEN)
def test_git_reise_wird_bei_gleich_umgeschaltet(l1, reise):
    """AC-1.6: Eine Git-Reise, inhaltsgleich darstellbar, wird umgeschaltet: Anfangsvorgang, Stempel gleich, Speicherreise."""
    assert reise not in l1.instanz.speicherreisen()
    assert l1.rs.umschalten_automatisch(reise) == "gleich"
    assert l1.rs.stand_nummer(reise) >= 1
    s = _stempel(l1, reise)
    assert s and s["ergebnis"] == "gleich" and s["baum"] == git(l1.bau, "rev-parse", f"HEAD:reisen/{reise}").strip()
    assert l1.rs.umschaltung_frei(reise) == (True, "")
    assert reise in l1.instanz.speicherreisen()
    assert (l1.bau / "reisen" / reise / "reise.yaml").exists()            # nichts gelöscht


def test_git_reise_bleibt_bei_unterschied_in_git(l1):
    """AC-1.7: Vergleich „unterschiedlich“: die Reise bleibt in Git, nichts gelöscht oder geändert, kein zweiter Vorgang.
    Seit F005 gilt das, wenn im Speicher auch geschrieben wurde (ein Vorgang außer Importen); nur Importe: siehe
    test_offene_umschaltung_nur_importe_traegt_git_stand_nach."""
    r = "beispielreise"
    l1.rs.importieren(l1.bau / "reisen" / r, r, wer="Ida", grund="Beispiel")          # offene Umschaltung
    l1.rs.vorgang_schreiben(r, {"speicher-notiz.md": b"Im Speicher geschrieben (Beispielwert)\n"}, "Ida", "item_update",
                            "Notiz im Speicher")
    (l1.bau / "reisen" / r / "git-nachtrag.md").write_text("Änderung in Git (Beispielwert)\n")
    _commit(l1.bau, "Nachtrag in Git")
    kopf, stand = git(l1.bau, "rev-parse", "HEAD"), l1.rs.stand_nummer(r)
    assert l1.rs.umschalten_automatisch(r) == "unterschied"
    assert l1.rs.stand_nummer(r) == stand
    assert git(l1.bau, "rev-parse", "HEAD") == kopf and not git(l1.bau, "status", "--porcelain")
    assert r not in l1.instanz.speicherreisen()
    s = _stempel(l1, r)
    assert s is None or s["ergebnis"] != "gleich"


def test_umschaltung_ist_idempotent(l1):
    """AC-1.8: Eine schon umgeschaltete Reise bleibt, wie sie ist (kein zweiter Anfangsvorgang, gleicher Stempel)."""
    r = "stadtwochenende"
    assert l1.rs.umschalten_automatisch(r) == "gleich"
    stand, stempel = l1.rs.stand_nummer(r), (l1.dienst / "vergleich" / f"{r}.json").read_bytes()
    assert l1.rs.umschalten_automatisch(r) == "schon_im_speicher"
    assert l1.rs.stand_nummer(r) == stand
    assert (l1.dienst / "vergleich" / f"{r}.json").read_bytes() == stempel


def test_umschaltung_nach_abbruch_wird_fortgesetzt(l1):
    """AC-1.9: Abbruch zwischen Anfangsvorgang und Stempel: weiter Git-Reise; der nächste Versuch vergleicht gegen den
    vorhandenen Anfangsvorgang und stempelt, ohne zweiten Anfangsvorgang."""
    r = "beispielreise"
    l1.rs.importieren(l1.bau / "reisen" / r, r, wer="Ida", grund="Beispiel")          # Anfangsvorgang ohne Stempel
    stand = l1.rs.stand_nummer(r)
    assert r not in l1.instanz.speicherreisen()
    assert l1.rs.umschalten_automatisch(r) == "gleich"
    assert l1.rs.stand_nummer(r) == stand
    assert _stempel(l1, r)["ergebnis"] == "gleich"
    assert r in l1.instanz.speicherreisen()


def test_bisherige_speicherreisen_bleiben_ohne_handschritt(l1):
    """AC-1.10: Reisen, die vor Lieferung 1 über FR_SPEICHERREISEN aus dem Speicher veröffentlicht wurden (.gebaut), bleiben
    Speicherreisen, auch wenn sie noch im Git-Bauordner liegen und FR_SPEICHERREISEN fehlt."""
    _importieren(l1, *REISEN)
    for r in REISEN:
        datei = l1.dienst / "reise-stand" / f"{r}.gebaut"
        datei.parent.mkdir(parents=True, exist_ok=True)
        datei.write_text(f"{l1.rs.stand_nummer(r)} alt-kennung\n")
    assert l1.instanz.speicherreisen() == REISEN
    for r in REISEN:
        assert l1.rs.umschaltung_frei(r) == (True, "")


def test_schreibwerkzeuge_speicherreise_unveraendert(l1):
    """AC-1.11: Schreibwerkzeuge auf eine Reise im Speicher wirken wie zuvor, ohne FR_SPEICHERREISEN."""
    _nur_im_speicher(l1, "stadtwochenende")
    vorher = l1.rs.stand_nummer("stadtwochenende")
    code, a = sb.anwenden_extern(sb.Schreiber(l1.bau), "stadtwochenende", "frage_anlegen",
                                 {**TOM, "args": {"text": "Hat der Markt samstags offen? (Beispielwert)"}})
    assert code == 200 and a["ok"], (code, a)
    assert l1.rs.stand_nummer("stadtwochenende") == vorher + 1


# ---------- Lieferung 1 im Lauf des Veröffentlichens ----------

def test_neue_reise_wird_vom_speicher_teil_gebaut(sp):
    """AC-1.5: Eine Reise nur im Speicher wird gebaut, ohne FR_SPEICHERREISEN und ohne dass der Git-Teil sie anfasst."""
    r = sp["lauf"](FR_SPEICHERREISEN="")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "stadtwochenende" in sp["deploys"]()
    assert (sp["seiten"] / "stadtwochenende" / "daten.json").exists()
    assert not (sp["arbeit"] / "reisen" / "stadtwochenende").exists()


def test_lauf_schaltet_git_reise_bei_gleich_um(sp):
    """AC-1.6 im Lauf: Die Git-Reise zweitreise wird umgeschaltet (Stempel gleich, im Speicher), der Lauf bleibt grün."""
    r = sp["lauf"](FR_SPEICHERREISEN="")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "zweitreise" in sp["speicher"].reisen(mit_vorgemerkten=True)
    stempel = json.loads((sp["tmp"] / "dienst" / "vergleich" / "zweitreise.json").read_text())
    assert stempel["ergebnis"] == "gleich"
    assert (sp["arbeit"] / "reisen" / "zweitreise" / "reise.json").exists()


def test_lauf_laesst_ungleiche_git_reise_mit_warnung_in_git(sp):
    """AC-1.7 im Lauf: offene Umschaltung mit Unterschied -> Warnzeile mit Grund, keine high-Meldung, Lauf grün."""
    ordner = sp["tmp"] / "anders"
    (ordner).mkdir()
    (ordner / "reise.json").write_text('{"anders": true}')
    sp["speicher"].importieren(ordner, "zweitreise", "Test", grund="Anfang")       # Anfangsvorgang weicht von Git ab
    sp["speicher"].vorgang_schreiben("zweitreise", {"notiz.md": b"1"}, "Test", "item_update", "im Speicher geschrieben")
    stand = sp["speicher"].stand_nummer("zweitreise")
    r = sp["lauf"](FR_SPEICHERREISEN="")
    assert r.returncode == 0, r.stdout + r.stderr
    assert any("zweitreise" in z and "warning" in z.lower() for z in r.stdout.splitlines()), r.stdout
    assert sp["speicher"].stand_nummer("zweitreise") == stand
    assert not [z for z in sp["zeilen"]("melden.log") if z.startswith("high|")]


# ======================================================================================================================
# Lieferung 2: Software direkt
# ======================================================================================================================

def _software_repo(ziel):
    shutil.copytree(BETRIEB, ziel / "betrieb", ignore=shutil.ignore_patterns("__pycache__"))
    (ziel / "engine").symlink_to(ENGINE)
    (ziel / "LIESMICH").write_text("Software (Beispiel)\n")
    git(ziel, "init", "-q", "-b", "main")
    _commit(ziel, "A")
    return git(ziel, "rev-parse", "HEAD").strip()


@pytest.fixture
def sw(tmp_path, monkeypatch):
    if not shutil.which("flock"):
        pytest.skip("flock fehlt")
    t = tmp_path
    quelle = t / "software"
    a = _software_repo(quelle)
    seiten = t / "seiten"
    dienst, klon, speicher = seiten / "_dienst", seiten / "_software", seiten / "_speicher"
    subprocess.run(["git", "clone", "-q", str(quelle), str(klon)], check=True)
    dienst.mkdir(parents=True)
    (dienst / "umzug-454").write_text("fertig\n")
    (dienst / "software-gut").write_text(a + "\n")
    (t / "ablage").mkdir()
    monkeypatch.setenv("FR_SPEICHER", str(speicher))
    monkeypatch.setenv("FR_KONTEN", str(t / "konten"))
    import reisespeicher
    for r in REISEN:
        reisespeicher.importieren(BEISPIEL / r, r, ORG[r]["name"], grund="Anfang")
    deploy = ausfuehrbar(t / "deploy.sh", f"""#!/bin/sh
kopf=$(git -C "$FR_WURZEL" rev-parse HEAD)
echo "$1 $kopf" >> {t}/deploy.log
[ -e {t}/infra-neu ] && [ "$kopf" = "$(cat {t}/infra-neu)" ] && exit 1
ordner="$FR_DIENST/bau/reisen/$1"
if [ -d "$ordner" ]; then
  mkdir -p "{seiten}/$1"
  for d in index.html sw.js manifest.json; do : > "{seiten}/$1/$d"; done
  printf '{{"reise_stand": {{"nummer": %s}}}}' "$(cat "$ordner.stand")" > "{seiten}/$1/daten.json"
fi
exit 0
""")
    pruefen = ausfuehrbar(t / "pruefen.sh", f"""#!/bin/sh
echo "$1 $(git rev-parse HEAD 2>/dev/null) $(git -C {klon} rev-parse HEAD)" >> {t}/pruefen.log
case "$1" in
  */instanz/tests) [ ! -e {t}/rot-instanz ] ;;
  *) [ ! -e {t}/rot ] ;;
esac
""")
    nachweis = ausfuehrbar(t / "nachweis.sh", f'#!/bin/sh\necho "$2" >> {t}/nachweis.log\n[ ! -e {t}/nachweis-weg ] || exit 1\n'
                                              f'cat {t}/nachweis 2>/dev/null || echo false\n')
    melden = ausfuehrbar(t / "melden.sh", f'#!/bin/sh\necho "$1|$2|$3" >> {t}/melden.log\n')
    ausfuehrbar(t / "bin" / "gh", f'#!/bin/sh\necho "$@" >> {t}/gh.log\nexit 1\n')
    ausfuehrbar(t / "bin" / "curl", f'#!/bin/sh\necho ping >> {t}/pings.log\n')
    nachziehen = ausfuehrbar(t / "nachziehen.sh", f'#!/bin/sh\necho los >> {t}/nachziehen.log\n')
    env = {**SAUBER, "FR_WURZEL": str(klon), "FR_INSTANZ": "probe", "FR_SEITEN": str(seiten), "FR_DIENST": str(dienst),
           "FR_SPEICHER": str(speicher), "FR_KONTEN": str(t / "konten"), "FR_KONNEKTOR": str(t / "konnektor"),
           "FR_ABLAGE": str(t / "ablage"), "FR_SPERREN": str(t), "FR_PYTHON": sys.executable, "FR_SUDO": "",
           "FR_GRUNDKARTE_AUTO": "0", "FR_HEARTBEAT_VEROEFFENTLICHEN": "https://example.invalid/hb",
           "FR_MELDEN": str(melden), "PATH": f"{t / 'bin'}:{os.environ['PATH']}",
           "VF_DEPLOY": str(deploy), "VF_PRUEFEN": str(pruefen), "VF_CINACHWEIS": str(nachweis),
           "VF_NACHZIEHEN": str(nachziehen),
           "VF_FREISCHALTEN": str(ausfuehrbar(t / "frei.sh", "#!/bin/sh\nexit 0\n")),
           "VF_UNITS": str(ausfuehrbar(t / "units.sh", "#!/bin/sh\nexit 0\n")),
           "VF_NGINX": str(ausfuehrbar(t / "nginx.sh", "#!/bin/sh\nexit 0\n")),
           "VF_ROTMELDEN": str(ausfuehrbar(t / "rotmelden.sh", "#!/bin/sh\nexit 0\n"))}

    def lauf(*args, **extra):
        return subprocess.run([str(klon / "betrieb" / "veroeffentlichen.sh"), *args], env={**env, **extra},
                              capture_output=True, text=True)

    def neuer_commit(aendern=None):
        if aendern:
            aendern(quelle)
        else:
            (quelle / "LIESMICH").write_text((quelle / "LIESMICH").read_text() + "neu\n")
        _commit(quelle, "neu")
        return git(quelle, "rev-parse", "HEAD").strip()

    def zeilen(name):
        datei = t / name
        return datei.read_text(encoding="utf-8").splitlines() if datei.exists() else []

    def kopf():
        return git(klon, "rev-parse", "HEAD").strip()

    def lesen(name):
        datei = dienst / name
        return datei.read_text().strip() if datei.exists() else None

    def gebaut(reise):
        return (lesen(f"reise-stand/{reise}.gebaut") or "").split()

    def nachweis_gruen(gruen=True):
        (t / "nachweis").write_text("true\n" if gruen else "false\n")

    return types.SimpleNamespace(lauf=lauf, neuer_commit=neuer_commit, zeilen=zeilen, kopf=kopf, lesen=lesen,
                                 gebaut=gebaut, nachweis_gruen=nachweis_gruen, a=a, t=t, klon=klon, dienst=dienst,
                                 seiten=seiten, quelle=quelle, env=env)


def _hoch(s):
    return [z for z in s.zeilen("melden.log") if z.startswith("high|")]


def _ok(r):
    assert r.returncode == 0, r.stdout + r.stderr
    return r


def test_neuer_commit_wird_ohne_reisen_repo_geholt(sw):
    """AC-2.1: Ein neuer Commit auf main der Software kommt ohne Reisen-Repo, ohne Workflow und ohne Anmeldung an."""
    _ok(sw.lauf())
    sw.nachweis_gruen()
    c = sw.neuer_commit()
    _ok(sw.lauf())
    assert sw.kopf() == c
    assert sw.lesen("software-gut") == c
    assert sw.zeilen("gh.log") == [] and sw.zeilen("nachziehen.log") == []


def test_roter_commit_laesst_klon_unveraendert(sw):
    """AC-2.2: Ohne Nachweis und mit roten Tests auf dem Server bleibt der Klon auf dem bisherigen Commit, Arbeitsbaum
    unverändert; geprüft wird in einem eigenen Arbeitsbaum von C."""
    _ok(sw.lauf())
    c = sw.neuer_commit()
    (sw.t / "rot").touch()
    r = sw.lauf()
    assert r.returncode != 0, r.stdout
    assert sw.kopf() == sw.a
    assert not git(sw.klon, "status", "--porcelain")
    assert (sw.klon / "LIESMICH").read_text() == "Software (Beispiel)\n"
    pruef = [z.split() for z in sw.zeilen("pruefen.log") if z.startswith("engine/tests")]
    assert pruef and pruef[-1][1] == c and pruef[-1][2] == sw.a, pruef


def test_nachweis_gruen_spult_klon_vor_ohne_server_tests(sw):
    """AC-2.3: Pflichtprüfungen von C grün -> Klon auf C, ohne Tests auf dem Server."""
    _ok(sw.lauf())
    (sw.t / "pruefen.log").unlink(missing_ok=True)
    sw.nachweis_gruen()
    c = sw.neuer_commit()
    _ok(sw.lauf())
    assert sw.kopf() == c
    assert c in sw.zeilen("nachweis.log")
    assert not [z for z in sw.zeilen("pruefen.log") if z.startswith("engine/tests")]


def test_nachweis_wird_je_stand_nur_einmal_abgefragt(sw):
    """AC-2.4: Derselbe Commit ohne Nachweis wird in mehreren Läufen nur einmal abgefragt."""
    _ok(sw.lauf())
    (sw.t / "nachweis-weg").touch()
    (sw.t / "rot").touch()
    c = sw.neuer_commit()
    for dt in (0, 5, 10):
        sw.lauf(VF_JETZT=str(T0 + dt * MINUTE))
    assert sw.zeilen("nachweis.log").count(c) == 1, sw.zeilen("nachweis.log")


def test_rueckfall_auf_letzten_guten_stand(sw):
    """AC-2.5: Scheitert der Deploy mit C, arbeiten die Dienste mit dem Commit aus software-gut weiter."""
    _ok(sw.lauf())
    seiten_vorher = {r: (sw.seiten / r / "daten.json").read_text() for r in REISEN}
    sw.nachweis_gruen()
    c = sw.neuer_commit()
    (sw.t / "infra-neu").write_text(c)
    r = sw.lauf()
    assert r.returncode != 0, r.stdout
    assert sw.kopf() == sw.a
    assert sw.lesen("software-gut") == sw.a
    assert {r_: (sw.seiten / r_ / "daten.json").read_text() for r_ in REISEN} == seiten_vorher


def test_rot_datei_am_software_commit_ein_alarm_je_rot_phase(sw):
    """AC-2.6: Roter C: Rot-Datei am Software-Commit, derselbe C wird nicht erneut geprüft, ein Alarm nach der Schwelle."""
    _ok(sw.lauf())
    c = sw.neuer_commit()
    (sw.t / "rot").touch()
    sw.lauf(VF_JETZT=str(T0))
    rot = dict(z.split("=", 1) for z in (sw.dienst / "veroeffentlichen-rot").read_text().splitlines() if "=" in z)
    assert rot["commit"] == c and rot["art"] == "software"
    for dt in (31, 45):
        r = sw.lauf(VF_JETZT=str(T0 + dt * MINUTE))
        assert "Known red state" in r.stdout, r.stdout
    assert len([z for z in sw.zeilen("pruefen.log") if z.startswith("engine/tests")]) == 1
    assert len(_hoch(sw)) == 1
    assert sw.kopf() == sw.a


def test_stempel_und_kennung_sind_software_commit(sw):
    """AC-2.7: Nach grünem Lauf sind veroeffentlicht, Software-Kennung und software-gut derselbe Software-Commit."""
    _ok(sw.lauf())
    sw.nachweis_gruen()
    c = sw.neuer_commit()
    _ok(sw.lauf())
    assert sw.lesen("veroeffentlicht") == c
    assert sw.lesen("software-gut") == c
    for r in REISEN:
        assert sw.gebaut(r)[1] == c, sw.gebaut(r)


@pytest.mark.parametrize("reise", REISEN)
def test_reisen_werden_nach_neuer_kennung_nachgezogen(sw, reise):
    """AC-2.8: Nach einem neuen Software-Commit zieht der Speicher-Teil jede Reise auf die neue Kennung nach."""
    _ok(sw.lauf())
    assert sw.gebaut(reise)[1] == sw.a
    sw.nachweis_gruen()
    c = sw.neuer_commit()
    r = _ok(sw.lauf())
    assert f"converting {reise}" in r.stdout, r.stdout
    assert sw.gebaut(reise)[1] == c
    assert sw.lesen("software-gut") == c


def _gemeinsam(env, *namen):
    skript = f'. "{BETRIEB}/gemeinsam.sh"; ' + "; ".join(f'echo "{n}=${{{n}:-}}"' for n in namen)
    r = subprocess.run(["bash", "-c", skript], capture_output=True, text=True, env={**SAUBER, **env})
    assert r.returncode == 0, r.stdout + r.stderr
    return dict(z.split("=", 1) for z in r.stdout.splitlines() if "=" in z)


def _instanz_wert(env, name):
    r = subprocess.run([sys.executable, "-c", f"import instanz; print(instanz.wert({name!r}) or '')"],
                       capture_output=True, text=True, cwd=ENGINE, env={**SAUBER, **env})
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


def test_einstellungen_reihenfolge_umgebung_instanz_alter_ort(tmp_path):
    """AC-2.9: Einstellungen aus der Umgebung, sonst <FR_DIENST>/instanz/einstellungen.env, sonst (Übergang) alter Ort."""
    wurzel, dienst = tmp_path / "wurzel", tmp_path / "dienst"
    (wurzel / "betrieb").mkdir(parents=True)
    (wurzel / "betrieb" / "einstellungen.env").write_text("FR_TITEL=Alt\nFR_ZEITZONE=Europe/Berlin\n")
    env = {"FR_WURZEL": str(wurzel), "FR_DIENST": str(dienst)}
    assert _gemeinsam(env, "FR_TITEL")["FR_TITEL"] == "Alt"                       # Übergang: alter Ort
    assert _instanz_wert(env, "FR_TITEL") == "Alt"
    (dienst / "instanz").mkdir(parents=True)
    (dienst / "instanz" / "einstellungen.env").write_text("FR_TITEL=Instanz\n")
    assert _gemeinsam(env, "FR_TITEL")["FR_TITEL"] == "Instanz"
    assert _instanz_wert(env, "FR_TITEL") == "Instanz"
    assert _gemeinsam({**env, "FR_TITEL": "Umgebung"}, "FR_TITEL")["FR_TITEL"] == "Umgebung"
    assert _instanz_wert({**env, "FR_TITEL": "Umgebung"}, "FR_TITEL") == "Umgebung"


def test_meldeweg_aus_instanz_ordner(tmp_path):
    """AC-2.10: Der Meldeweg liegt unter <FR_DIENST>/instanz/melden.sh (auch wenn die umgezogene Einstellung noch den
    alten relativen Pfad betrieb/melden.sh nennt); ohne Meldeweg wird nichts gesendet."""
    wurzel, dienst = tmp_path / "wurzel", tmp_path / "dienst"
    wurzel.mkdir()
    env = {"FR_WURZEL": str(wurzel), "FR_DIENST": str(dienst)}
    assert _gemeinsam(env, "FR_MELDEN")["FR_MELDEN"] == ""
    melden = ausfuehrbar(dienst / "instanz" / "melden.sh", f'#!/bin/sh\necho "$1" >> {tmp_path}/gesendet.log\n')
    (dienst / "instanz" / "einstellungen.env").write_text("FR_MELDEN=betrieb/melden.sh\n")
    assert _gemeinsam(env, "FR_MELDEN")["FR_MELDEN"] == str(melden)
    (dienst / "instanz" / "einstellungen.env").write_text("")
    assert _gemeinsam(env, "FR_MELDEN")["FR_MELDEN"] == str(melden)
    r = subprocess.run(["bash", "-c", f'. "{BETRIEB}/gemeinsam.sh"; fr_melden normal Betreff Text'],
                       capture_output=True, text=True, env={**SAUBER, **env})
    assert r.returncode == 0 and (tmp_path / "gesendet.log").read_text().split() == ["normal"]


def test_python_umgebung_ausserhalb_des_klons(sw):
    """AC-2.11: FR_PYTHON liegt fest unter <FR_DIENST>/python, außerhalb des Klons; ein Rückfall des Klons lässt sie stehen;
    eine geänderte Abhängigkeitsliste baut sie vor dem Umschalten neu (VF_VENV)."""
    werte = _gemeinsam({"FR_WURZEL": str(sw.klon), "FR_DIENST": str(sw.dienst)}, "FR_PYTHON")
    assert werte["FR_PYTHON"] == str(sw.dienst / "python" / "bin" / "python")
    marke = sw.dienst / "python" / "marke"
    marke.parent.mkdir(parents=True)
    marke.write_text("bleibt\n")
    venv = ausfuehrbar(sw.t / "venv.sh", f'#!/bin/sh\necho "$1 $2" >> {sw.t}/venv.log\n')
    _ok(sw.lauf(VF_VENV=str(venv)))
    sw.nachweis_gruen()

    def neue_abhaengigkeit(q):
        (q / "requirements-beispiel.txt").write_text("beispielpaket==1.0\n")
    c = sw.neuer_commit(neue_abhaengigkeit)
    (sw.t / "infra-neu").write_text(c)                                    # Deploy mit C scheitert: Rückfall
    sw.lauf(VF_VENV=str(venv))
    assert sw.kopf() == sw.a and marke.read_text() == "bleibt\n"
    assert any(z.startswith(str(sw.dienst / "python")) for z in sw.zeilen("venv.log")), sw.zeilen("venv.log")


def test_anstoss_startet_nur_einen_lauf(sw):
    """AC-2.17: _anstoss.json startet einen Lauf, ohne gh workflow run; die Datei ist danach weg, kein Dauerlauf."""
    _ok(sw.lauf())
    ablage = sw.t / "ablage"
    (ablage / "_anstoss.json").write_text('{"zeit": "2026-11-12T12:00:00+00:00", "reise": "beispielreise", "von": "Ida"}\n')
    r = _ok(sw.lauf())
    assert "workflow" not in r.stdout.lower(), r.stdout
    assert sw.zeilen("gh.log") == [] and sw.zeilen("nachziehen.log") == []
    assert not (ablage / "_anstoss.json").exists()
    assert json.loads((ablage / "_anstoss-ergebnis.json").read_text())["ok"] is True
    vorher = (ablage / "_anstoss-ergebnis.json").read_text()
    _ok(sw.lauf())
    assert (ablage / "_anstoss-ergebnis.json").read_text() == vorher


def test_lauf_ohne_reisen_repo_und_ohne_gh(sw):
    """AC-2.18: Neuer Zustand ohne Reisen-Repo und ohne gh: grüner Lauf, Reisen aus dem Speicher, Stempel und Heartbeat."""
    r = _ok(sw.lauf())
    assert sw.zeilen("gh.log") == [], sw.zeilen("gh.log")
    gebaut = sorted({z.split()[0] for z in sw.zeilen("deploy.log") if not z.startswith("--dienste")})   # F002: Dienste zuerst
    assert gebaut == REISEN, r.stdout
    assert sw.lesen("veroeffentlicht") == sw.a and sw.lesen("software-gut") == sw.a
    assert sw.zeilen("pings.log") == ["ping"]
    assert "trips repo" not in r.stdout


def test_instanz_tests_fehlen_oder_rot_sperren_nicht(sw):
    """AC-2.22: Ohne <FR_DIENST>/instanz/tests wird übersprungen; rot dort ist eine Warnung, der Wechsel geht durch."""
    _ok(sw.lauf())
    c = sw.neuer_commit()
    _ok(sw.lauf())
    assert not [z for z in sw.zeilen("pruefen.log") if "instanz/tests" in z]
    assert sw.kopf() == c
    tests = sw.dienst / "instanz" / "tests"
    tests.mkdir(parents=True)
    (tests / "test_privat.py").write_text("def test_privat():\n    pass\n")
    (sw.t / "rot-instanz").touch()
    d = sw.neuer_commit()
    r = _ok(sw.lauf())
    assert [z for z in sw.zeilen("pruefen.log") if z.split()[0] == str(tests)], sw.zeilen("pruefen.log")
    assert "warning" in r.stdout.lower()
    assert sw.kopf() == d and sw.lesen("software-gut") == d
    assert not _hoch(sw)


def test_skript_startet_sich_nach_umschalten_neu(sw):
    """AC-2.16: Ändert das Vorspulen veroeffentlichen.sh, startet der Lauf mit exec das neue Skript und endet einmal."""
    _ok(sw.lauf())
    sw.nachweis_gruen()

    def skript_aendern(q):
        datei = q / "betrieb" / "veroeffentlichen.sh"
        text = datei.read_text()
        datei.write_text(text.replace("main() {\n", 'main() {\n  echo "NEUES SKRIPT"\n', 1))
    c = sw.neuer_commit(skript_aendern)
    r = _ok(sw.lauf())
    assert sw.kopf() == c
    assert r.stdout.count("NEUES SKRIPT") == 1, r.stdout
    assert r.stdout.count("Done:") + r.stdout.count("Nothing new") <= 1, r.stdout


# ---------- Umzug einer bestehenden Instanz (alter Bauordner mit Submodul) ----------

@pytest.fixture
def alt(vf):
    """vf mit Submodul frieda/ (Software: Kopie von betrieb/ und engine) und Einstellungen und Meldeweg im Reisen-Repo.
    VF_VENV baut die Python-Umgebung (Verweis auf das Test-Python, scheitert über venv-kaputt), VF_UNITS gleicht die Units
    ab: pruefen ist gleich, wenn units-ziel den FR_WURZEL des Aufrufs nennt; installieren schreibt ihn hinein."""
    t = vf["tmp"]
    quelle, software, seiten = t / "quelle", t / "software", t / "seiten"
    _software_repo(software)
    (quelle / "betrieb").mkdir()
    (quelle / "betrieb" / "einstellungen.env").write_text("FR_TITEL=Probe (Beispielwert)\nFR_MELDEN=betrieb/melden.sh\n")
    ausfuehrbar(quelle / "betrieb" / "melden.sh", f'#!/bin/sh\necho "$1|$2" >> {t}/melden-instanz.log\n')
    subprocess.run(["git", "-C", str(quelle), "submodule", "add", "-q", str(software), "frieda"], check=True,
                   capture_output=True, env={**os.environ, **GIT, **GIT_ERLAUBT})
    _commit(quelle, "Software und Einstellungen")
    venv = ausfuehrbar(t / "venv.sh", f'#!/bin/sh\necho "$1" >> {t}/venv.log\n[ ! -e {t}/venv-kaputt ] || exit 1\n'
                                      f'mkdir -p "$1/bin" && ln -sf {sys.executable} "$1/bin/python"\n')
    units = ausfuehrbar(t / "units-abgleich.sh", f"""#!/bin/sh
echo "$1 $FR_WURZEL" >> {t}/units.log
case "$1" in
  pruefen) [ "$(cat {t}/units-ziel)" = "$FR_WURZEL" ] && exit 0; exit 3 ;;
  installieren) echo "$FR_WURZEL" > {t}/units-ziel ;;
esac
""")
    (t / "units-ziel").write_text(str(vf["arbeit"]) + "\n")
    nachweis = ausfuehrbar(t / "nachweis.sh", "#!/bin/sh\necho true\n")
    extra = {**GIT_ERLAUBT, "FR_SEITEN": str(seiten), "FR_PYTHON": sys.executable, "VF_VENV": str(venv),
             "VF_UNITS": str(units), "VF_CINACHWEIS": str(nachweis), "FR_ABLAGE": str(t / "ablage"),
             "FR_GRUNDKARTE_AUTO": "0"}
    klon = seiten / "_software"

    def lauf_alt(**mehr):
        return vf["lauf"](**{**extra, **mehr})

    def lauf_neu(**mehr):
        env = {**vf["env"], **extra, "FR_WURZEL": str(klon), **mehr}
        env.pop("FR_PYTHON", None)
        return subprocess.run([str(klon / "betrieb" / "veroeffentlichen.sh")], env=env, capture_output=True, text=True)

    def umzug():
        datei = t / "dienst" / "umzug-454"
        return datei.read_text().strip() if datei.exists() else None

    def installiert():
        return [z for z in vf["zeilen"]("units.log") if z.startswith("installieren")]

    def bild(ordner):
        """Dateien des alten Bauordners (ohne .git) mit Inhalt, dazu HEAD und Status."""
        dateien = {p.relative_to(ordner).as_posix(): p.read_bytes() for p in sorted(ordner.rglob("*"))
                   if p.is_file() and ".git" not in p.relative_to(ordner).parts and "__pycache__" not in p.parts}
        return dateien, git(ordner, "rev-parse", "HEAD"), git(ordner, "status", "--porcelain")

    return {**vf, "lauf_alt": lauf_alt, "lauf_neu": lauf_neu, "umzug": umzug, "installiert": installiert, "bild": bild,
            "klon": klon, "software": software, "seiten": seiten, "quelle": quelle}


def test_umzug_ohne_handschritt(alt):
    """AC-2.12: Der Lauf im alten Zustand legt den Klon an, kopiert Einstellungen und Meldeweg, baut die Python-Umgebung,
    gleicht die Units ab und setzt den Umzug auf fertig."""
    r = alt["lauf_alt"]()
    assert r.returncode == 0, r.stdout + r.stderr
    dienst, klon = alt["tmp"] / "dienst", alt["klon"]
    assert git(klon, "rev-parse", "HEAD").strip() == git(alt["software"], "rev-parse", "HEAD").strip()
    assert (dienst / "instanz" / "einstellungen.env").read_text() == \
        (alt["arbeit"] / "betrieb" / "einstellungen.env").read_text()
    assert (dienst / "instanz" / "melden.sh").exists()
    assert (dienst / "python" / "bin" / "python").exists()
    assert (alt["tmp"] / "units-ziel").read_text().strip() == str(klon)
    assert alt["umzug"]() == "fertig"


def test_umzug_scheitert_vor_units_alles_beim_alten(alt):
    """AC-2.13 und AC-2.20: Scheitert die Python-Umgebung, bleiben die Units beim alten Bauordner, das Veröffentlichen läuft
    über den alten Weg weiter, keine high-Meldung; Klon und Einstellungen (Schritte 1 und 2) liegen schon bereit."""
    (alt["tmp"] / "venv-kaputt").touch()
    r = alt["lauf_alt"]()
    assert r.returncode == 0, r.stdout + r.stderr
    assert (alt["klon"] / ".git").exists()
    assert (alt["tmp"] / "dienst" / "instanz" / "einstellungen.env").exists()
    assert (alt["tmp"] / "units-ziel").read_text().strip() == str(alt["arbeit"])
    assert alt["umzug"]() != "fertig"
    assert "warning" in r.stdout.lower()
    assert not [z for z in alt["zeilen"]("melden.log") if z.startswith("high|")]


def test_umzug_ist_wiederholbar(alt):
    """AC-2.14: Ein halber Umzug wird fortgesetzt, ohne neuere Einstellungen zu überschreiben, den Klon neu anzulegen oder
    die Units ohne Unterschied neu zu installieren."""
    (alt["tmp"] / "venv-kaputt").touch()
    alt["lauf_alt"]()
    einst = alt["tmp"] / "dienst" / "instanz" / "einstellungen.env"
    einst.write_text("FR_TITEL=Neuer am Zielort (Beispielwert)\n")
    marke = alt["klon"] / ".git" / "marke"
    marke.write_text("derselbe Klon\n")
    (alt["tmp"] / "venv-kaputt").unlink()
    r = alt["lauf_alt"]()
    assert r.returncode == 0, r.stdout + r.stderr
    assert alt["umzug"]() == "fertig"
    assert einst.read_text() == "FR_TITEL=Neuer am Zielort (Beispielwert)\n"
    assert marke.exists()
    assert len(alt["installiert"]()) == 1
    r = alt["lauf_neu"]()
    assert r.returncode == 0, r.stdout + r.stderr
    assert len(alt["installiert"]()) == 1


def test_alter_bauordner_bleibt_und_ist_rueckweg(alt):
    """AC-2.15: Nach dem Umzug bleibt der alte Bauordner unverändert; Läufe im neuen Zustand fassen ihn nicht an."""
    r = alt["lauf_alt"]()
    assert r.returncode == 0, r.stdout + r.stderr
    assert alt["umzug"]() == "fertig"
    vorher = alt["bild"](alt["arbeit"])
    assert "betrieb/einstellungen.env" in vorher[0] and "betrieb/melden.sh" in vorher[0]
    alt["neuer_commit"]()                                                # neuer Stand im Reisen-Repo: zählt nicht mehr
    r = alt["lauf_neu"]()
    assert r.returncode == 0, r.stdout + r.stderr
    assert alt["bild"](alt["arbeit"]) == vorher


def test_umzugsfehler_und_nachweis_sind_keine_high_meldung(sw):
    """AC-2.20: Nicht abrufbarer Nachweis ist keine high-Meldung; die Liste der Alarmstellen bleibt, wie sie ist."""
    _ok(sw.lauf())
    (sw.t / "nachweis-weg").touch()
    c = sw.neuer_commit()
    _ok(sw.lauf())
    assert sw.kopf() == c                                                # Tests auf dem Server grün statt Nachweis
    assert not _hoch(sw)
    assert set(ALARMSTELLEN) == {
        ("waechter.sh", "Watchdog failed"), ("waechter.sh", "Account backup failed"),
        ("waechter.sh", "Trip store backup failed"), ("veroeffentlichen.sh", "Publishing red for $minuten minutes")}


# ---------- Einrichten, Pfade, Doku ----------

def test_einrichten_ohne_gh_und_reisen_repo():
    """AC-2.19: einrichten.sh verlangt weder gh auth noch ein Reisen-Repo, legt Klon und <FR_DIENST>/instanz an; die Units
    starten die Skripte aus dem Klon (__WURZEL__/betrieb/…)."""
    text = (BETRIEB / "einrichten.sh").read_text()
    assert "gh auth" not in text
    assert "ls-remote origin" not in text
    assert "_software" in text and "instanz" in text
    for v in sorted((BETRIEB / "vorlagen").rglob("*")):
        if v.is_file():
            assert "__WURZEL__/frieda/" not in v.read_text(), v.name


def test_keine_instanzspezifischen_werte_in_betrieb():
    """AC-2.23: Vorlagen und Werkzeuge nennen keine Pfade unter frieda/ (Submodul) mehr; Bauordner kommen aus den
    Einstellungen."""
    dateien = [p for p in (BETRIEB / "vorlagen").rglob("*") if p.is_file()]
    dateien += sorted((WURZEL / "werkzeuge").glob("*.py"))
    treffer = [p.relative_to(WURZEL).as_posix() for p in dateien if "frieda/betrieb" in p.read_text()
               or "frieda/werkzeuge" in p.read_text()]
    assert treffer == []


def _abschnitt(text, ueberschrift):
    teile = text.split("\n## ")
    for t in teile:
        if t.startswith(ueberschrift):
            return t
    return ""


def test_dokumentierte_infra_vorbedingung():
    """AC-2.21: docs/betrieb.md nennt die Vorbedingung der Infrastruktur (Monitor und Backup-Aufruf von sichern.sh)."""
    umzug = _abschnitt((WURZEL / "docs" / "betrieb.md").read_text(), "Umzug")
    assert umzug, "Abschnitt „Umzug …“ fehlt in docs/betrieb.md"
    assert "monitor.sh" in umzug and "sichern.sh" in umzug and "Vorbedingung" in umzug


def test_betrieb_md_beschreibt_neuen_weg():
    """AC-2.24: docs/betrieb.md beschreibt Klon, letzten guten Stand, Einstellungen der Instanz, Umzug und Rückweg;
    ADR-0009 nennt #454 in Stufe 5."""
    text = (WURZEL / "docs" / "betrieb.md").read_text()
    for wort in ("_software", "software-gut", "instanz/einstellungen.env", "umzug-454", "Rückweg"):
        assert wort in text, wort
    assert "gh workflow run" not in _abschnitt(text, "Anstoß")
    assert "#454" in (WURZEL / "docs" / "adr" / "0009-reisespeicher.md").read_text()


# ======================================================================================================================
# Befunde des Adversary (F001 bis F007) und Entscheidungen des Tech Leads dazu
# ======================================================================================================================

def _nicht_als_root():
    if os.geteuid() == 0:
        pytest.skip("als root sind Ordner ohne Rechte durchsuchbar")


def test_f001_shell_unlesbarer_speicher_ist_fehler_nie_leere_liste(tmp_path):
    """F001 (#361): Ist der Speicherordner nicht durchsuchbar, endet speicherreisen_lesen mit einem Fehler wie
    instanz.speicherreisen, nie mit einer leeren Liste. Fehlt die Datenbank sicher, ist die Liste leer, ohne Python."""
    _nicht_als_root()
    speicher = tmp_path / "_speicher"
    speicher.mkdir()
    (speicher / "reisen.db").write_bytes(b"")
    falle = ausfuehrbar(tmp_path / "python-falle", f'#!/bin/sh\necho "$@" >> {tmp_path}/py.log\nexec {sys.executable} "$@"\n')
    env = {**SAUBER, "FR_WURZEL": str(tmp_path), "FR_SPEICHER": str(speicher), "FR_PYTHON": str(falle),
           "FR_DIENST": str(tmp_path / "_dienst")}
    skript = f'. "{BETRIEB}/gemeinsam.sh"; speicherreisen_lesen; echo "rc=$? liste=[$fr_speicherreisen_liste]"'
    os.chmod(speicher, 0)
    try:
        r = subprocess.run(["bash", "-c", skript], capture_output=True, text=True, env=env)
        db = subprocess.run([sys.executable, str(ENGINE / "reisespeicher.py"), "datenbank"], capture_output=True, text=True,
                            env={**env, "FR_PYTHON": sys.executable})
    finally:
        os.chmod(speicher, 0o700)
    assert "rc=1" in r.stdout and "cannot be read" in r.stderr, r.stdout + r.stderr
    assert db.returncode == 2, db.stdout + db.stderr
    # sicher keine Datenbank: leer, ohne Python
    (speicher / "reisen.db").unlink()
    (tmp_path / "py.log").unlink(missing_ok=True)
    r = subprocess.run(["bash", "-c", skript], capture_output=True, text=True, env=env)
    assert "rc=0 liste=[]" in r.stdout, r.stdout + r.stderr
    assert not (tmp_path / "py.log").exists()
    db = subprocess.run([sys.executable, str(ENGINE / "reisespeicher.py"), "datenbank"], capture_output=True, text=True,
                        env={**env, "FR_PYTHON": sys.executable})
    assert db.returncode == 1 and db.stdout.strip() == "nein"


def test_f001_lauf_mit_unlesbarem_speicher_ist_rot(sp):
    """F001 im Lauf: Speicherordner nicht durchsuchbar -> der Lauf endet rot, baut keine Reise und schaltet nichts um."""
    _nicht_als_root()
    speicher = Path(sp["env"]["FR_SPEICHER"])
    os.chmod(speicher, 0)
    try:
        r = sp["lauf"]()
    finally:
        os.chmod(speicher, 0o700)
    assert r.returncode != 0, r.stdout + r.stderr
    assert "cannot be read" in r.stdout + r.stderr
    assert sp["deploys"]() == []
    assert not (sp["tmp"] / "dienst" / "veroeffentlichen-erfolg").exists()


def _dienste_mit(sw, c):
    return [z for z in sw.zeilen("deploy.log") if z.split() == ["--dienste", c]]


def _nachgezogen(sw):
    import sqlite3
    from contextlib import closing
    with closing(sqlite3.connect(Path(sw.env["FR_SPEICHER"]) / "reisen.db")) as v:
        return v.execute("SELECT COUNT(*) FROM vorgaenge WHERE werkzeug = 'nachziehen'").fetchone()[0]


def test_f002_rueckfall_mit_rot_datei_kein_erneuter_rollout_und_kein_nachziehen(sw):
    """F002: Scheitert der Deploy der Dienste mit C, fällt die Software auf software-gut zurück, die Rot-Datei nennt C, und
    der nächste Takt rollt C nicht erneut aus. Die Reisen wurden nicht auf die Kennung von C umgestellt."""
    _ok(sw.lauf())
    sw.nachweis_gruen()
    c = sw.neuer_commit()
    (sw.t / "infra-neu").write_text(c)
    r = sw.lauf(VF_JETZT=str(T0))
    assert r.returncode != 0, r.stdout
    assert sw.kopf() == sw.a and sw.lesen("software-gut") == sw.a
    rot = dict(z.split("=", 1) for z in (sw.dienst / "veroeffentlichen-rot").read_text().splitlines() if "=" in z)
    assert rot["commit"] == c and rot["art"] == "software"
    assert len(_dienste_mit(sw, c)) == 1
    assert "converting" not in r.stdout and _nachgezogen(sw) == 0
    for reise in REISEN:
        assert sw.gebaut(reise)[1] == sw.a
    r = sw.lauf(VF_JETZT=str(T0 + 5 * MINUTE))
    assert "Known red state" in r.stdout, r.stdout
    assert len(_dienste_mit(sw, c)) == 1 and sw.kopf() == sw.a


def test_f002_andere_stoerung_ohne_rueckfall(sw):
    """F002: Scheitert nach grünem Deploy der Dienste etwas anderes (hier der Deploy einer Reise), gibt es keinen Rückfall
    und keine Rot-Datei am Commit: der Lauf ist rot, der nächste versucht es wieder."""
    _ok(sw.lauf())
    (sw.t / "deploy.log").unlink()
    sw.nachweis_gruen()
    c = sw.neuer_commit()
    reise_kaputt = ausfuehrbar(sw.t / "deploy-reise-kaputt.sh",
                               f'#!/bin/sh\n[ "$1" = --dienste ] || exit 1\nexec {sw.t}/deploy.sh "$@"\n')
    r = sw.lauf(VF_DEPLOY=str(reise_kaputt))
    assert r.returncode != 0, r.stdout
    assert sw.kopf() == c and sw.lesen("software-gut") == sw.a
    assert len(_dienste_mit(sw, c)) == 1
    assert not _dienste_mit(sw, sw.a), "kein Rückfall"
    rot = sw.dienst / "veroeffentlichen-rot"
    assert not rot.exists() or f"commit={c}" not in rot.read_text()
    _ok(sw.lauf())
    assert sw.kopf() == c and sw.lesen("software-gut") == c


def _venv_attrappe(sw):
    return ausfuehrbar(sw.t / "venv-echt.sh", f'#!/bin/sh\necho "$1" >> {sw.t}/venv.log\n'
                                              f'mkdir -p "$1/bin" && ln -sf {sys.executable} "$1/bin/python"\n')


def _python_vorbereiten(sw):
    """Live-Umgebung gebaut, dann deren Merker auf eine andere Liste: der nächste Commit bringt „neue Abhängigkeiten“."""
    venv = _venv_attrappe(sw)
    _ok(sw.lauf(VF_VENV=str(venv)))
    live = sw.dienst / "python"
    (live / ".requirements.sha256").write_text("alte-liste\n")
    (live / "marke").write_text("laufende Umgebung\n")
    pruefen = ausfuehrbar(sw.t / "pruefen-python.sh",
                          f'#!/bin/sh\necho "$FR_PYTHON" >> {sw.t}/pruef-python.log\nexec {sw.t}/pruefen.sh "$@"\n')
    return {"VF_VENV": str(venv), "VF_PRUEFEN": str(pruefen)}, live


def test_f003_rote_pruefung_laesst_die_laufende_umgebung_unveraendert(sw):
    """F003: Neue Abhängigkeiten werden in einer eigenen Umgebung neben der laufenden gebaut und geprüft; rot verwirft sie,
    die laufende bleibt, wie sie war."""
    extra, live = _python_vorbereiten(sw)
    sw.neuer_commit()
    (sw.t / "rot").touch()
    r = sw.lauf(**extra)
    assert r.returncode != 0, r.stdout
    assert (live / ".requirements.sha256").read_text() == "alte-liste\n" and (live / "marke").exists()
    assert not (sw.dienst / "python.neu").exists()
    assert str(sw.dienst / "python.neu") in sw.zeilen("venv.log")
    assert sw.zeilen("pruef-python.log")[-1] == str(sw.dienst / "python.neu" / "bin" / "python")


def test_f003_gruene_pruefung_tauscht_die_umgebung_und_rueckfall_setzt_sie_zurueck(sw):
    """F003: Grün -> die neue Umgebung steht an der Stelle der laufenden, die vorige als python.alt. Scheitert danach der
    Deploy der Dienste, setzt der Rückfall auch die vorige Umgebung wieder ein."""
    extra, live = _python_vorbereiten(sw)
    c = sw.neuer_commit()
    _ok(sw.lauf(**extra))
    assert sw.kopf() == c
    assert (live / ".requirements.sha256").read_text() != "alte-liste\n" and not (live / "marke").exists()
    assert (sw.dienst / "python.alt" / "marke").exists() and not (sw.dienst / "python.neu").exists()
    # Rückfall: wieder eine „alte“ Liste, neuer Commit mit grünem Nachweis, dessen Deploy der Dienste scheitert
    (live / ".requirements.sha256").write_text("alte-liste\n")
    (live / "marke").write_text("laufende Umgebung\n")
    sw.nachweis_gruen()
    d = sw.neuer_commit()
    (sw.t / "infra-neu").write_text(d)
    r = sw.lauf(**extra)
    assert r.returncode != 0 and sw.kopf() == c, r.stdout
    assert (live / ".requirements.sha256").read_text() == "alte-liste\n" and (live / "marke").exists()


def test_f004_umzug_prueft_je_commit_einmal_und_warnt_einmal(alt):
    """F004: Bleiben die Units gesperrt, wiederholen die folgenden Läufe Python-Umgebung und Prüfung für denselben Commit
    nicht; die Warnzeile zu den Units steht einmal je Commit und Befund im Protokoll."""
    t = alt["tmp"]
    nachweis = ausfuehrbar(t / "nachweis-log.sh", f'#!/bin/sh\necho "$2" >> {t}/nachweis.log\necho true\n')
    units = ausfuehrbar(t / "units-gesperrt.sh", f'#!/bin/sh\necho "$1" >> {t}/units.log\n'
                                                 'echo "probe-veroeffentlichen.service: BLOCKED, ExecStart wanted"\nexit 4\n')
    sub = git(alt["software"], "rev-parse", "HEAD").strip()
    laeufe = [alt["lauf_alt"](VF_CINACHWEIS=str(nachweis), VF_UNITS=str(units))]
    nach_dem_ersten = alt["zeilen"]("nachweis.log").count(sub)
    laeufe += [alt["lauf_alt"](VF_CINACHWEIS=str(nachweis), VF_UNITS=str(units)) for _ in range(2)]
    for r in laeufe:
        assert r.returncode == 0, r.stdout + r.stderr
    assert (t / "dienst" / "umzug-454.geprueft").read_text().strip() == sub
    assert nach_dem_ersten >= 1 and alt["zeilen"]("nachweis.log").count(sub) == nach_dem_ersten, alt["zeilen"]("nachweis.log")
    assert len(alt["zeilen"]("venv.log")) == 1
    warnungen = [sum("units cannot be switched" in z for z in r.stdout.splitlines()) for r in laeufe]
    assert warnungen == [1, 0, 0], warnungen
    assert alt["umzug"]() != "fertig"


def test_f005_offene_umschaltung_nur_importe_traegt_git_stand_nach(l1):
    """F005: Offene Umschaltung, Git hat sich seitdem geändert, im Speicher stehen nur Importe: der Git-Stand wird als
    weiterer Import angehängt (nichts gelöscht), erneut verglichen und gestempelt; die Reise ist Speicherreise."""
    r = "beispielreise"
    l1.rs.importieren(l1.bau / "reisen" / r, r, wer="Ida", grund="Beispiel")          # offene Umschaltung
    (l1.bau / "reisen" / r / "git-nachtrag.md").write_text("Änderung in Git (Beispielwert)\n")
    _commit(l1.bau, "Nachtrag in Git")
    stand = l1.rs.stand_nummer(r)
    assert l1.rs.umschalten_automatisch(r) == "gleich"
    assert l1.rs.stand_nummer(r) == stand + 1
    assert l1.rs.datei(r, "git-nachtrag.md") == "Änderung in Git (Beispielwert)\n".encode()
    assert l1.rs.stand_nummer(r) is not None and stand >= 1                         # der Anfangsvorgang bleibt im Verlauf
    assert _stempel(l1, r)["ergebnis"] == "gleich" and r in l1.instanz.speicherreisen()


def test_f005_offene_umschaltung_mit_schreibvorgang_bleibt_in_git(l1):
    """F005: Stehen im Speicher auch andere Vorgänge als Importe, wird nichts nachgetragen: die Reise bleibt in Git."""
    r = "stadtwochenende"
    l1.rs.importieren(l1.bau / "reisen" / r, r, wer="Tom", grund="Beispiel")
    l1.rs.vorgang_schreiben(r, {"notiz.md": b"Im Speicher (Beispielwert)\n"}, "Tom", "item_update", "Notiz")
    (l1.bau / "reisen" / r / "git-nachtrag.md").write_text("Änderung in Git (Beispielwert)\n")
    _commit(l1.bau, "Nachtrag in Git")
    stand = l1.rs.stand_nummer(r)
    assert l1.rs.umschalten_automatisch(r) == "unterschied"
    assert l1.rs.stand_nummer(r) == stand and r not in l1.instanz.speicherreisen()


def _units_erzeugen(tmp_path, alte_anordnung):
    repo = tmp_path / "repo"
    (repo / "betrieb").mkdir(parents=True, exist_ok=True)
    (repo / "betrieb" / "einstellungen.env").write_text("FR_INSTANZ=probe\nFR_TITEL=Probe\nFR_ADRESSE=https://example.invalid\n")
    (repo / ".gitmodules").unlink(missing_ok=True)
    if alte_anordnung:
        (repo / ".gitmodules").write_text("")
    aus = tmp_path / ("aus-alt" if alte_anordnung else "aus-neu")
    env = {**SAUBER, "FR_WURZEL": str(repo), "FR_SEITEN": str(tmp_path / "srv/probe"), "EI_ZIEL": str(aus),
           "FR_BENUTZER": "reisen", "FR_GRUPPE": "reisen", "FR_HOME": "/home/reisen"}
    r = subprocess.run(["bash", str(BETRIEB / "einrichten.sh"), "--erzeugen"], capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stdout + r.stderr
    return repo, env, {p.name: p.read_text() for p in (aus / "systemd").iterdir()}


def test_f006_units_der_alten_anordnung_gleichen_den_installierten(tmp_path):
    """F006: In der alten Anordnung starten die Units die Skripte aus dem Submodul frieda/ und nennen FR_DIENST nicht als
    Umgebungswert, wie die heute installierten; units.py pruefen meldet nichts (Exit 0). Im Klon: Pfade im Klon."""
    repo, _, neu = _units_erzeugen(tmp_path, False)
    assert f"ExecStart={repo}/betrieb/veroeffentlichen.sh" in neu["probe-veroeffentlichen.service"]
    assert "Environment=FR_DIENST=" in neu["probe-veroeffentlichen.service"]
    # heute installiert (vor #454): Skripte unter <Bauordner>/frieda/betrieb; FR_DIENST als Umgebungswert nur in den Units,
    # die ihn schon vorher hatten (Rückmeldedienst, Konnektor, Push), nicht in denen, die #454 ihn im Klon gibt
    durch_454 = {"probe-veroeffentlichen.service", "probe-waechter.service", "probe-schreiben.service"}
    installiert = tmp_path / "systemd"
    installiert.mkdir()
    for name, text in neu.items():
        text = text.replace(f"{repo}/betrieb/", f"{repo}/frieda/betrieb/")
        text = text.replace(f"{tmp_path}/srv/probe/_dienst/python/bin/python", f"{repo}/engine/.venv/bin/python")   # Python vorher
        if name in durch_454:
            assert "Environment=FR_DIENST=" in text, name
            text = "\n".join(z for z in text.split("\n") if not z.startswith("Environment=FR_DIENST="))
        (installiert / name).write_text(text)
    _, env, alt_ = _units_erzeugen(tmp_path, True)
    assert f"ExecStart={repo}/frieda/betrieb/veroeffentlichen.sh" in alt_["probe-veroeffentlichen.service"]
    assert f"ExecStart={repo}/frieda/betrieb/waechter.sh" in alt_["probe-waechter.service"]
    assert not any("Environment=FR_DIENST=" in alt_[n] for n in durch_454)
    r = subprocess.run([sys.executable, str(BETRIEB / "units.py"), "pruefen"], capture_output=True, text=True,
                       env={**env, "EI_SYSTEMD": str(installiert)})
    assert r.returncode == 0, r.stdout + r.stderr


def test_f007_aufrufhilfen_der_werkzeuge_nennen_den_neuen_weg():
    """F007: Die Aufrufhilfen der Werkzeuge nennen weder das Reisen-Repo noch engine/.venv als einzigen Weg."""
    for p in sorted((WURZEL / "werkzeuge").glob("*.py")):
        text = p.read_text(encoding="utf-8")
        assert "Reisen-Repo" not in text and "engine/.venv/bin/python werkzeuge/" not in text, p.name
