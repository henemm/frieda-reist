"""#557: Rückbau des Git-Wegs nach dem Umzug auf den Software-Klon (#454). Spec: docs/specs/betrieb/rueckbau-git-weg-557.md.

Nur mit den beiden erfundenen Beispielreisen (beispielreise: Wanderung mit Varianten, Ida und Karl; stadtwochenende: Reise
ohne Pläne, Tom und Lea) und erfundenen Testdaten, alles unter tmp_path.

Aufbauten:
  py   Python-Ebene: ein Ordner FR_WURZEL, der ein Git-Repo ist (wie der Software-Klon) und beide Beispielreisen unter
       reisen/ im Commit hat (wie ein alter Bauordner), beide Reisen im Speicher, kein Stempel, kein .gebaut. Vor dem
       Rückbau filtert die Umschaltung sie aus; danach ist jede Reise mit Vorgang Speicherreise.
  ab   Shell-Lauf im Software-Klon (Fixture sw aus test_software_weg_454.py) mit nachgebautem alten Bauordner
       <FR_SEITEN>/_bau (beide Beispielreisen unter reisen/, Submodul-Attrappe frieda/) und <FR_SEITEN>/_bau-schreiben-<reise>.

Vertrag des Schritts altbau_entfernen (L3) für die Umsetzung:
  Warnzeilen        beginnen mit „Warning:“ und enthalten „old build folder“; bei einer Reise außerhalb des Speichers
                    steht ihr Name in der Zeile. Einmal je Störung (entprellt), der nächste Lauf versucht es erneut.
  Archiv            genau eine Datei unter <FR_DIENST>/archiv/, mit tarfile lesbar, enthält reisen/<reise>/reise.yaml jeder
                    Reise aus _bau (Präfix im Archiv frei), nichts aus _bau-schreiben-*.
  Merker            <FR_DIENST>/altbau-557, erst nach dem Löschen geschrieben.
  VF_PLATZ <ordner> Attrappe der Platzprüfung: gibt den freien Platz des Dateisystems von <ordner> in Bytes aus.
  VF_ARCHIV <archivdatei> <ordner>   Attrappe des Archivbaus (statt tar); danach wird das Archiv gelesen und geprüft.
  VF_UNITS pruefen  Exit 0: alle Units zeigen auf den Klon; Exit 3 mit einer Zeile, die <FR_SEITEN>/_bau nennt: nicht.
"""
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import threading
import types
import urllib.error
import urllib.request
import json
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

ENGINE = Path(__file__).resolve().parents[1]
WURZEL = ENGINE.parent
BETRIEB = WURZEL / "betrieb"
BEISPIEL = WURZEL / "beispiel" / "reisen"
DIESE = Path(__file__).resolve()
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import schreiben as sb  # noqa: E402
from test_betrieb import git, ausfuehrbar, SAUBER, ALARMSTELLEN  # noqa: E402,F401
from test_software_weg_454 import sw  # noqa: E402,F401  (Fixture: Lauf im Software-Klon)

IDA = {"person": "ida", "name": "Ida", "rolle": "organisator"}
TOM = {"person": "tom", "name": "Tom", "rolle": "organisator"}
ORG = {"beispielreise": IDA, "stadtwochenende": TOM}
REISEN = sorted(ORG)
OHNE = ("__pycache__", ".venv", "vendor", "node_modules")


def _text(pfad):
    return (WURZEL / pfad).read_text(encoding="utf-8")


def _dateien(*ordner, endungen=None, ohne_tests=False):
    for o in ordner:
        basis = WURZEL / o
        kandidaten = [basis] if basis.is_file() else basis.rglob("*")
        for p in kandidaten:
            if not p.is_file() or any(t in p.parts for t in OHNE) or p.resolve() == DIESE:
                continue
            if ohne_tests and "tests" in p.relative_to(WURZEL).parts:
                continue
            if endungen and p.suffix not in endungen:
                continue
            yield p


def _funde(muster, *ordner, **kw):
    rx = re.compile(muster)
    return [f"{p.relative_to(WURZEL)}:{n}" for p in _dateien(*ordner, **kw)
            for n, z in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1) if rx.search(z)]


# ======================================================================================================================
# L0, L2: Workflow „Software nachziehen“ und Git-Weg-Werkzeuge
# ======================================================================================================================

def test_kein_workflow_zeitplan_in_der_software():
    """AC-1: Kein Workflow und kein Skript „Software nachziehen“ mehr in Software, CI und Betriebsdoku."""
    assert not (BETRIEB / "software-nachziehen.sh").exists() and not (BETRIEB / "software-nachziehen.yml").exists()
    funde = _funde(r"software-nachziehen|Software nachziehen|FR_NACHZIEHEN", "betrieb", "engine", "werkzeuge", ".github",
                   "docs/betrieb.md", ohne_tests=True)
    assert not funde, funde


def test_betrieb_md_nennt_vorbedingung_monitor():
    """AC-2: Die Doku nennt die Umstellung der Überwachung als Vorbedingung des Aufräumens (altbau_entfernen)."""
    absaetze = [a for a in _text("docs/betrieb.md").split("\n\n") if "altbau_entfernen" in a]
    assert absaetze, "docs/betrieb.md beschreibt altbau_entfernen nicht"
    assert any("monitor.sh" in a for a in absaetze), absaetze


def test_git_weg_werkzeuge_sind_geloescht():
    """AC-18: Werkzeuge des Git-Wegs sind gelöscht; deploy.sh, tests.yml und einstellungen.beispiel nennen sie nicht."""
    weg = ["betrieb/vergleichslauf.sh", "betrieb/software-nachziehen.sh", "betrieb/software-nachziehen.yml",
           "betrieb/messlauf-schreibweg.py", "engine/tests/test_software_nachziehen.py"]
    assert [p for p in weg if (WURZEL / p).exists()] == []
    for datei in ("betrieb/deploy.sh", ".github/workflows/tests.yml", "betrieb/einstellungen.beispiel"):
        text = _text(datei)
        for name in ("vergleichslauf", "software-nachziehen", "messlauf-schreibweg", "FR_NACHZIEHEN", "FR_SPEICHERREISEN"):
            assert name not in text, (datei, name)


def test_kein_gh_workflow_run_in_der_software():
    """AC-39: Kein Skript der Software ruft gh workflow run auf."""
    funde = _funde(r"gh workflow run", "betrieb", "engine", "werkzeuge", ohne_tests=True)
    assert not funde, funde


def test_spec_454_known_limitations_abgeschlossen():
    """AC-39, AC-35: Spec 454 trägt im Kopf den Hinweis auf #557; die Known Limitations zu AC-2.4/2.6, AC-2.17 und den
    Usage-Texten sind als abgeschlossen (#557) vermerkt."""
    text = _text("docs/specs/betrieb/software-weg-454.md")
    kopf = text.split("## Purpose", 1)[0]
    assert "#557" in kopf, "Hinweis auf den Rückbau fehlt im Kopf der Spec 454"
    grenzen = text.split("## Known Limitations", 1)[1].split("\n## ", 1)[0]
    for marke in ("AC-2.4", "AC-2.17", "frieda/"):
        zeile = next(z for z in grenzen.splitlines() if marke in z)
        assert "abgeschlossen (#557)" in zeile, zeile


# ======================================================================================================================
# L1: Engine ohne Git-Weg
# ======================================================================================================================

@pytest.fixture
def py(tmp_path, monkeypatch):
    for k in list(os.environ):
        if k.startswith(("FR_", "SB_", "KN_", "RM_", "VF_")):
            monkeypatch.delenv(k)
    wurzel = tmp_path / "_software"
    for r in REISEN:
        shutil.copytree(BEISPIEL / r, wurzel / "reisen" / r, ignore=shutil.ignore_patterns(".git"))
    (wurzel / "LIESMICH").write_text("Software (Beispiel)\n")
    git(wurzel, "init", "-q", "-b", "main")
    git(wurzel, "add", "-A")
    git(wurzel, "commit", "-qm", "start")
    (tmp_path / "sperren").mkdir()
    stub = ausfuehrbar(tmp_path / "veroeffentlichen.sh", f"#!/bin/sh\necho los >> {tmp_path}/veroeffentlicht\n")
    for k, v in {"FR_WURZEL": wurzel, "FR_INSTANZ": "probe", "FR_DIENST": tmp_path / "_dienst",
                 "FR_SPEICHER": tmp_path / "_speicher", "FR_SPERREN": tmp_path / "sperren",
                 "FR_KONTEN": tmp_path / "konten", "SB_VEROEFFENTLICHEN": stub, "FR_PYTHON": sys.executable}.items():
        monkeypatch.setenv(k, str(v))
    tmp = tmp_path / "tmp"
    tmp.mkdir()
    monkeypatch.setenv("TMPDIR", str(tmp))
    monkeypatch.setattr(tempfile, "tempdir", str(tmp))
    import instanz
    import reisespeicher as rs
    for r in REISEN:
        rs.importieren(BEISPIEL / r, r, wer=ORG[r]["name"], grund="Beispiel")
    return types.SimpleNamespace(rs=rs, instanz=instanz, wurzel=wurzel, pfad=tmp_path,
                                 schreiber=lambda: sb.Schreiber(wurzel))


class Dienst:
    """Der Schreibdienst in einem Thread; get(pfad) -> (code, json)."""

    def __init__(self, schreiber):
        sb.Dienst.schreiber = schreiber
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), sb.Dienst)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.basis = f"http://127.0.0.1:{self.server.server_address[1]}"

    def get(self, pfad):
        try:
            with urllib.request.urlopen(f"{self.basis}/{pfad}", timeout=30) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.server.shutdown()
        sb.Dienst.schreiber = None


def test_git_module_sind_geloescht():
    """AC-3: schreiben_git.py und stand_git.py sind gelöscht, nichts importiert sie."""
    assert not (ENGINE / "schreiben_git.py").exists()
    assert not (ENGINE / "stand_git.py").exists()
    funde = _funde(r"^\s*(import|from)\s+(schreiben_git|stand_git)\b|import\s+.*\b(schreiben_git|stand_git)\b",
                   "engine", "betrieb", "werkzeuge", endungen={".py"})
    assert not funde, funde


def test_gesund_ohne_git_teil_im_klon(py, monkeypatch):
    """AC-4: Die Wurzel ist ein Git-Repo (Klon); /gesund macht keinen Git-Aufruf und hängt nur am Speicher."""
    aufrufe = []
    attrappe = types.ModuleType("schreiben_git")
    attrappe.gesund = lambda s: aufrufe.append(str(s.wurzel)) or False
    monkeypatch.setitem(sys.modules, "schreiben_git", attrappe)
    log = py.pfad / "git.log"
    ausfuehrbar(py.pfad / "bin" / "git", f'#!/bin/sh\necho "$*" >> {log}\nexit 1\n')
    monkeypatch.setenv("PATH", f"{py.pfad / 'bin'}:{os.environ['PATH']}")
    with Dienst(py.schreiber()) as d:
        assert d.get("gesund") == (200, {"gesund": True})
    assert aufrufe == [], "Git-Teil von /gesund gerufen"
    assert not log.exists(), log.read_text()


@pytest.mark.parametrize("reise", REISEN)
def test_speicherreisen_ohne_filter(py, reise):
    """AC-6: Jede Reise mit Vorgang ist Speicherreise, auch wenn sie im Git-Commit der Wurzel liegt und kein Stempel da ist."""
    assert not (Path(os.environ["FR_DIENST"]) / "vergleich").exists()
    assert reise in py.instanz.speicherreisen()
    assert py.instanz.speicherreisen() == REISEN


@pytest.mark.parametrize("reise", REISEN)
def test_schreiber_hat_nur_speicherweg(py, monkeypatch, reise):
    """AC-8: Schreiben geht über den Speicher, auch wenn die Wurzel ein Git-Repo mit der Reise ist; Git bleibt unberührt."""
    monkeypatch.setattr(sb.secrets, "token_hex", lambda n=6: "a1b2c3d4e5f6")
    basis = py.rs.stand_nummer(reise)
    code, a = sb.anwenden_extern(py.schreiber(), reise, "frage_anlegen",
                                 {**ORG[reise], "args": {"text": "Gibt es dort einen Markt? (Beispielwert)"}})
    assert code == 200 and a["ok"], a
    assert py.rs.stand_nummer(reise) == basis + 1
    assert a["commit"] == str(py.rs.verlauf(reise, n=1)[0]["vorgang"])
    assert not git(py.wurzel, "status", "--porcelain")
    assert git(py.wurzel, "rev-list", "--count", "HEAD").strip() == "1"


def test_reise_ohne_speichereintrag_ist_503(py):
    """AC-8: Eine Reise ohne Eintrag im Speicher liefert reise_nicht_im_speicher (kein Git-Weg mehr)."""
    code, a = sb.anwenden_extern(py.schreiber(), "dritte-reise", "frage_anlegen",
                                 {**IDA, "args": {"text": "Markt? (Beispielwert)"}})
    assert code == 503 and a["ok"] is False, a
    assert a["fehler_code"] == "schreiben.dienst.reise_nicht_im_speicher", a
    assert py.rs.stand_nummer("dritte-reise") is None


def test_reisespeicher_hat_keine_umschaltung():
    """AC-9: Keine Umschaltung mehr in reisespeicher.py, auch nicht als Befehl."""
    text = _text("engine/reisespeicher.py")
    for name in ("umschaltung_frei", "umschalten_automatisch", "git_stand_nachtragen", "_git_baum", "stand_git",
                 "vergleich", '"umschalten"', '"umschaltung"'):
        assert name not in text, name
    for befehl in ("umschalten", "umschaltung"):
        r = subprocess.run([sys.executable, str(ENGINE / "reisespeicher.py"), befehl, "beispielreise"],
                           capture_output=True, text=True, env={**SAUBER, "FR_SPEICHER": "/nonexistent-557"})
        assert r.returncode != 0, (befehl, r.stdout)


def test_veroeffentlichen_ruft_keine_umschaltung():
    """AC-10: veroeffentlichen.sh ruft keine entfernten Befehle von reisespeicher.py; stand.py ohne Git-Zweig."""
    assert not re.search(r"reisespeicher\.py\"?\s+umschalt", _text("betrieb/veroeffentlichen.sh"))
    stand = _text("engine/stand.py")
    assert "stand_git" not in stand


def test_fr_speicherreisen_in_einstellungen_wird_ignoriert(tmp_path):
    """AC-11: Eine liegengebliebene Zeile FR_SPEICHERREISEN in den Einstellungen der Instanz stört nicht, wirkt nicht und
    bleibt unverändert; die Software kennt den Namen nicht mehr."""
    wurzel, dienst = tmp_path / "_software", tmp_path / "_dienst"
    wurzel.mkdir()
    (dienst / "instanz").mkdir(parents=True)
    datei = dienst / "instanz" / "einstellungen.env"
    inhalt = "FR_TITEL=Probe\nFR_SPEICHERREISEN=beispielreise,stadtwochenende\n"
    datei.write_text(inhalt)
    r = subprocess.run(["bash", "-c", f'set -e; . "{BETRIEB}/gemeinsam.sh"; echo "TITEL=$FR_TITEL"'],
                       capture_output=True, text=True,
                       env={**SAUBER, "FR_WURZEL": str(wurzel), "FR_DIENST": str(dienst)})
    assert r.returncode == 0 and "TITEL=Probe" in r.stdout, r.stdout + r.stderr
    assert r.stderr == "", r.stderr
    assert datei.read_text() == inhalt
    funde = _funde(r"FR_SPEICHERREISEN", "betrieb", "engine", "werkzeuge", ohne_tests=True)
    assert not funde, funde


def test_deploy_ohne_geloeschte_module_und_ohne_reisen_bau():
    """AC-12: deploy.sh kopiert keine gelöschten Module und baut nichts aus $WURZEL/reisen."""
    text = _text("betrieb/deploy.sh")
    assert "schreiben_git" not in text and "stand_git" not in text
    assert not re.search(r'\$\{?WURZEL\}?"?/reisen', text), "Bau aus $WURZEL/reisen"


def test_entfallene_texte_in_allen_sprachen_weg():
    """AC-13: Entfallene Schlüssel fehlen in jeder Sprachdatei; die Ausnahmelisten sind nicht länger geworden."""
    import test_texte
    for datei in sorted(ENGINE.glob("texte_*.py")):
        text = datei.read_text(encoding="utf-8")
        assert "umschaltung_nicht_freigegeben" not in text, datei.name
    assert sum(test_texte.AUSNAHMEN.values()) <= 1
    assert sum(test_texte.WEICHEN_AUSNAHMEN.values()) == 0


# ======================================================================================================================
# L2: Betriebsskripte
# ======================================================================================================================

def test_veroeffentlichen_hat_nur_den_klon_weg():
    """AC-15: Nur der Weg über den Klon; die Funktionen des alten Wegs sind entfernt, die des Klons bleiben."""
    text = _text("betrieb/veroeffentlichen.sh")
    funktionen = set(re.findall(r"^([a-z_0-9]+)\(\) \{", text, re.M))
    for weg in ("reisen_des_laufs", "ci_nachweis", "anstoss_weitergeben", "software_anstossen", "git_reisen_uebrig",
                "git_reisen_umschalten"):
        assert weg not in funktionen, weg
    assert {f for f in funktionen if f.startswith("umzug_")} <= {"umzug_fertig_im_klon"}, funktionen
    for bleibt in ("main_klon", "software_klon", "software_kennung", "umzug_fertig_im_klon", "speicher_reisen_lauf",
                   "speicher_rot_melden", "pruefen_lauf", "anstoss_lauf"):
        assert bleibt in funktionen, bleibt
    assert "Submodul" not in text


def test_gemeinsam_und_einrichten_ohne_alte_anordnung():
    """AC-17: Keine alte Anordnung, keine Vorgabe für FR_SCHREIBKOPIE, kein FR_SPEICHERREISEN, kein FR_NACHZIEHEN_*;
    die Vorlage schreiben.service ohne ReadWritePaths auf -schreiben."""
    for datei in ("betrieb/gemeinsam.sh", "betrieb/einrichten.sh"):
        text = _text(datei)
        for name in ("fr_alte_anordnung", "nur_bauordner", "FR_SPEICHERREISEN", "FR_NACHZIEHEN_", "Superprojekt",
                     "superproject", "show-superproject-working-tree", "frieda/"):
            assert name not in text, (datei, name)
        assert not re.search(r"FR_SCHREIBKOPIE[:=]", text), datei
    assert "__WURZEL__-schreiben" not in _text("betrieb/vorlagen/schreiben.service")


def test_usage_texte_ohne_frieda_pfad():
    """AC-20: Usage-Texte nennen keinen Pfad mit frieda/."""
    for datei in ("werkzeuge/karte-holen.sh", "betrieb/sichern.sh"):
        assert "frieda/" not in _text(datei), datei


def test_units_ohne_handschritt(tmp_path):
    """AC-21: Die neue Vorlage hat keinen Pfad auf -schreiben mehr. Geändert vom Developer (#557): ReadWritePaths steht
    nicht in der Erlaubnisliste (units.py, Hilfsprogramm mit Root-Rechten), und die Spec verlangt sie unverändert. Eine
    installierte Unit mit der alten Zeile ist deshalb eine gesperrte Abweichung (Exit 4, BLOCKED mit ReadWritePaths), nie
    eine stille Installation; der Abgleich über units.py meldet sie, bis die Units einmal mit einrichten.sh --installieren
    aus dem Klon installiert sind (wie bei #454). Exit 3 wäre nur mit einer neuen Erlaubnis für ReadWritePaths möglich."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (tmp_path / "dienst" / "instanz").mkdir(parents=True)
    (tmp_path / "dienst" / "instanz" / "einstellungen.env").write_text(
        "FR_INSTANZ=probe\nFR_TITEL=Probe\nFR_ADRESSE=https://example.invalid\n")
    aus = tmp_path / "aus"
    env = {**SAUBER, "FR_WURZEL": str(repo), "FR_SEITEN": str(tmp_path / "srv/probe"), "FR_DIENST": str(tmp_path / "dienst"),
           "EI_ZIEL": str(aus), "FR_BENUTZER": "reisen", "FR_GRUPPE": "reisen", "FR_HOME": "/home/reisen"}
    r = subprocess.run(["bash", str(BETRIEB / "einrichten.sh"), "--erzeugen"], capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stdout + r.stderr
    neu = {p.name: p.read_text() for p in (aus / "systemd").iterdir()}
    schreiben = neu["probe-schreiben.service"]
    assert f"{repo}-schreiben" not in schreiben, schreiben
    installiert = tmp_path / "systemd"
    installiert.mkdir()
    for name, text in neu.items():
        if name == "probe-schreiben.service":
            alt = f"ReadWritePaths=-{repo}-schreiben {repo} "
            text = text.replace(f"ReadWritePaths={repo} ", alt, 1)
            assert alt in text, text
        (installiert / name).write_text(text)
    r = subprocess.run([sys.executable, str(BETRIEB / "units.py"), "pruefen"], capture_output=True, text=True,
                       env={**env, "EI_SYSTEMD": str(installiert)})
    assert r.returncode == 4, r.stdout + r.stderr
    gesperrt = [z for z in r.stdout.splitlines() if "BLOCKED" in z]
    assert gesperrt and all("probe-schreiben.service" in z and "ReadWritePaths" in z for z in gesperrt), r.stdout


# ======================================================================================================================
# L3: altbau_entfernen
# ======================================================================================================================

@pytest.fixture
def ab(sw):
    bau = sw.seiten / "_bau"
    for r in REISEN:
        shutil.copytree(BEISPIEL / r, bau / "reisen" / r, ignore=shutil.ignore_patterns(".git"))
    (bau / "frieda").mkdir()
    (bau / "frieda" / "LIESMICH").write_text("alte Software (Beispiel)\n")
    for r in REISEN:
        (sw.seiten / f"_bau-schreiben-{r}").mkdir()
        (sw.seiten / f"_bau-schreiben-{r}" / "arbeit.txt").write_text("Arbeitskopie (Beispiel)\n")
    platz_log = sw.t / "platz.log"
    platz = ausfuehrbar(sw.t / "platz.sh", f'#!/bin/sh\necho "$1" >> {platz_log}\ncat {sw.t}/platz 2>/dev/null || echo 999999999999\n')

    def lauf(*args, **extra):
        return sw.lauf(*args, **{"VF_PLATZ": str(platz), **extra})

    def archive():
        ordner = sw.dienst / "archiv"
        return sorted(p for p in ordner.iterdir()) if ordner.exists() else []

    def warnungen(r):
        return [z for z in r.stdout.splitlines() if z.startswith("Warning") and "old build folder" in z]

    def altbau():
        return sorted(p.name for p in sw.seiten.iterdir() if p.name == "_bau" or p.name.startswith("_bau-schreiben-"))

    return types.SimpleNamespace(sw=sw, lauf=lauf, bau=bau, archive=archive, warnungen=warnungen, altbau=altbau,
                                 merker=sw.dienst / "altbau-557", platz_log=platz_log)


def _gruen(r):
    assert r.returncode == 0, r.stdout + r.stderr
    return r


def _hoch(sw):
    return [z for z in sw.zeilen("melden.log") if z.startswith("high|")]


ALTBAU = ["_bau"] + [f"_bau-schreiben-{r}" for r in REISEN]


def test_altbau_wird_nach_archiv_entfernt(ab):
    """AC-23: Alle Bedingungen erfüllt: Archiv lesbar unter <FR_DIENST>/archiv/, _bau und _bau-schreiben-* weg, Merker
    gesetzt, Lauf grün mit Heartbeat."""
    r = _gruen(ab.lauf())
    assert ab.altbau() == [], r.stdout
    assert ab.merker.exists()
    archive = ab.archive()
    assert len(archive) == 1, archive
    with tarfile.open(archive[0]) as t:
        namen = t.getnames()
    for reise in REISEN:
        assert any(n.endswith(f"reisen/{reise}/reise.yaml") for n in namen), namen[:20]
    assert not any("_bau-schreiben" in n or "arbeit.txt" in n for n in namen)
    assert ab.warnungen(r) == []
    assert ab.sw.zeilen("pings.log") == ["ping"]
    assert (ab.sw.klon / ".git").exists() and (ab.sw.dienst / "umzug-454").exists()


@pytest.mark.parametrize("zustand", [None, "alt"])
def test_altbau_nur_bei_umzug_fertig(ab, zustand):
    """AC-24: Ohne Umzugszustand oder mit alt bleibt alles liegen."""
    datei = ab.sw.dienst / "umzug-454"
    if zustand is None:
        datei.unlink()
    else:
        datei.write_text(zustand + "\n")
    _gruen(ab.lauf())
    assert ab.altbau() == ALTBAU
    assert not ab.merker.exists() and ab.archive() == []


def test_altbau_nur_wenn_units_auf_klon_zeigen(ab):
    """AC-25: Zeigt eine Unit noch auf _bau, wird nichts gelöscht; Warnzeile."""
    units = ausfuehrbar(ab.sw.t / "units-alt.sh",
                        f'#!/bin/sh\n[ "$1" = pruefen ] && echo "probe-schreiben.service: FR_WURZEL={ab.bau}" && exit 3\nexit 1\n')
    r = _gruen(ab.lauf(VF_UNITS=str(units)))
    assert ab.altbau() == ALTBAU
    assert not ab.merker.exists() and ab.archive() == []
    assert ab.warnungen(r), r.stdout


def test_altbau_reine_readwritepaths_abweichung_haelt_nicht_auf(ab):
    """AC-21/AC-25 (Orchestrator, #557): Die Bedingung prüft nur den Ort. Weicht eine Unit des Klons nur in der gesperrten
    Zeile ReadWritePaths ab (alte Schreibkopie <klon>-schreiben, Exit 4 bis zum Einmalschritt einrichten.sh --installieren),
    wird der alte Bauordner trotzdem archiviert und entfernt."""
    zeile = (f"probe-schreiben.service: BLOCKED, probe-schreiben.service: [Service] ReadWritePaths=-{ab.sw.klon}-schreiben "
             f"{ab.sw.klon} {ab.sw.dienst} installed")
    units = ausfuehrbar(ab.sw.t / "units-rwp.sh", f'#!/bin/sh\n[ "$1" = pruefen ] && echo "{zeile}" && exit 4\nexit 1\n')
    r = _gruen(ab.lauf(VF_UNITS=str(units)))
    assert ab.altbau() == [], r.stdout
    assert ab.merker.exists() and len(ab.archive()) == 1
    assert ab.warnungen(r) == []


@pytest.mark.parametrize("reise", REISEN)
def test_altbau_nur_wenn_jede_reise_speicherreise(ab, reise):
    """AC-26: Liegt in _bau/reisen eine Reise, die nicht im Speicher steht, bleibt alles liegen; die Warnzeile nennt sie."""
    fremd = f"{reise}-alt"
    shutil.copytree(BEISPIEL / reise, ab.bau / "reisen" / fremd, ignore=shutil.ignore_patterns(".git"))
    r = _gruen(ab.lauf())
    assert ab.altbau() == ALTBAU
    assert not ab.merker.exists() and ab.archive() == []
    assert any(fremd in z for z in ab.warnungen(r)), r.stdout


def test_altbau_archiv_platzpruefung(ab):
    """AC-27: Reicht der Platz nicht, wird nichts gelöscht und kein halbes Archiv zurückgelassen."""
    (ab.sw.t / "platz").write_text("0\n")
    r = _gruen(ab.lauf())
    assert ab.platz_log.exists(), "Platzprüfung nicht gerufen"
    assert ab.altbau() == ALTBAU
    assert not ab.merker.exists() and ab.archive() == []
    assert ab.warnungen(r), r.stdout


@pytest.mark.parametrize("fall", ["scheitert", "unlesbar"])
def test_altbau_archivfehler_loescht_nichts(ab, fall):
    """AC-28: Scheitert der Archivbau oder ist das Archiv nicht lesbar, bleibt _bau unverändert, der Merker ungesetzt."""
    if fall == "scheitert":
        archiv = ausfuehrbar(ab.sw.t / "archiv.sh", '#!/bin/sh\necho halb > "$1"\nexit 1\n')
    else:
        archiv = ausfuehrbar(ab.sw.t / "archiv.sh", '#!/bin/sh\necho "kein Archiv (Beispiel)" > "$1"\nexit 0\n')
    r = _gruen(ab.lauf(VF_ARCHIV=str(archiv)))
    assert ab.altbau() == ALTBAU
    assert (ab.bau / "reisen" / "beispielreise" / "reise.yaml").exists()
    assert not ab.merker.exists()
    assert ab.warnungen(r), r.stdout


@pytest.mark.parametrize("fall", ["bau_nach_aussen", "schreiben_auf_dienst", "bau_auf_software"])
def test_altbau_pfadpruefung_innerhalb_fr_seiten(ab, fall):
    """AC-29: Links nach außen, auf _dienst oder _software werden nie gelöscht und nie durchlaufen; nichts wird gelöscht."""
    sw = ab.sw
    if fall == "bau_nach_aussen":
        aussen = sw.t / "aussen"
        shutil.move(str(ab.bau), str(aussen))
        ab.bau.symlink_to(aussen)
        schutz = aussen / "reisen" / "beispielreise" / "reise.yaml"
    elif fall == "schreiben_auf_dienst":
        link = sw.seiten / "_bau-schreiben-beispielreise"
        shutil.rmtree(link)
        link.symlink_to(sw.dienst)
        schutz = sw.dienst / "umzug-454"
    else:
        shutil.rmtree(ab.bau)
        ab.bau.symlink_to(sw.klon)
        schutz = sw.klon / "LIESMICH"
    r = _gruen(ab.lauf())
    assert schutz.exists()
    assert (sw.klon / ".git").exists() and (sw.dienst / "software-gut").exists()
    assert ab.altbau() == ALTBAU
    assert not ab.merker.exists()
    assert ab.warnungen(r), r.stdout


def test_altbau_ist_idempotent(ab):
    """AC-30: Zweiter Lauf ändert nichts, kein zweites Archiv, keine Warnzeile; mit Merker bleibt ein neuer _bau liegen."""
    _gruen(ab.lauf())
    archive = ab.archive()
    assert len(archive) == 1
    r = _gruen(ab.lauf("--immer"))
    assert ab.archive() == archive and ab.warnungen(r) == []
    ab.bau.mkdir()
    (ab.bau / "neu.txt").write_text("nach dem Aufräumen angelegt (Beispiel)\n")
    r = _gruen(ab.lauf("--immer"))
    assert (ab.bau / "neu.txt").exists() and ab.archive() == archive and ab.warnungen(r) == []


def test_altbau_fehler_sind_keine_high_meldung(ab):
    """AC-31: Fehler sind eine Warnzeile, einmal je Störung; kein high-Alarm; der nächste Lauf versucht es erneut."""
    (ab.sw.t / "platz").write_text("0\n")
    r1 = _gruen(ab.lauf())
    r2 = _gruen(ab.lauf("--immer"))
    assert len(ab.warnungen(r1)) == 1, r1.stdout
    assert ab.warnungen(r2) == [], r2.stdout
    assert len(ab.platz_log.read_text().splitlines()) >= 2, "der zweite Lauf hat es nicht erneut versucht"
    assert not _hoch(ab.sw)
    (ab.sw.t / "platz").unlink()
    _gruen(ab.lauf("--immer"))
    assert ab.altbau() == [] and ab.merker.exists()


def test_altbau_haelt_den_lauf_nicht_auf(ab):
    """AC-32: Ein Fehler im Schritt lässt Speicher-Teil, Bau und Heartbeat unberührt."""
    archiv = ausfuehrbar(ab.sw.t / "archiv.sh", "#!/bin/sh\nexit 1\n")
    r = _gruen(ab.lauf(VF_ARCHIV=str(archiv)))
    gebaut = sorted({z.split()[0] for z in ab.sw.zeilen("deploy.log") if not z.startswith("--dienste")})
    assert gebaut == REISEN, r.stdout
    assert ab.sw.zeilen("pings.log") == ["ping"]
    assert ab.sw.lesen("veroeffentlicht") == ab.sw.a
    assert ab.warnungen(r), r.stdout


def test_altbau_archivordner_nicht_anlegbar_haelt_den_lauf_nicht_auf(ab):
    """AC-32 (Validierung #557): Lässt sich der Archivordner nicht anlegen (hier: eine Datei liegt an seiner Stelle),
    bricht der Lauf trotz set -e nicht ab: Bau und Heartbeat wie immer, eine Warnzeile, nichts gelöscht, kein Merker."""
    (ab.sw.dienst / "archiv").write_text("keine Ordner (Beispiel)\n")
    r = _gruen(ab.lauf())
    gebaut = sorted({z.split()[0] for z in ab.sw.zeilen("deploy.log") if not z.startswith("--dienste")})
    assert gebaut == REISEN, r.stdout
    assert ab.sw.zeilen("pings.log") == ["ping"]
    assert ab.warnungen(r), r.stdout
    assert "_bau" in ab.altbau()
    assert not ab.merker.exists()


@pytest.mark.parametrize("reise", REISEN)
def test_lauf_im_klon_gruen(sw, reise):
    """AC-16 (Schutz): Ohne Altbau läuft der Klon grün, baut die Reise, pingt einmal und warnt nicht über den Altbau."""
    r = _gruen(sw.lauf())
    assert reise in {z.split()[0] for z in sw.zeilen("deploy.log")}
    assert sw.zeilen("pings.log") == ["ping"]
    assert "old build folder" not in r.stdout
    assert not (sw.dienst / "archiv").exists()


# ======================================================================================================================
# L4: Doku
# ======================================================================================================================

def test_betrieb_md_ohne_git_weg_und_rueckweg():
    """AC-34: betrieb.md beschreibt den Ist-Zustand: kein Zustand alt, kein Rückweg, keine frieda/-Anordnung, kein
    Software nachziehen; dafür das Aufräumen mit Archiv und den bewusst fehlenden Rückweg samt Rückfall."""
    text = _text("docs/betrieb.md")
    for weg in ("Software nachziehen", "software-nachziehen", "frieda/betrieb", "frieda/engine", "Rückweg zum alten",
                "umzug-454 = alt", "vergleichslauf"):
        assert weg not in text, weg
    assert not re.search(r"umzug-454[^\n]{0,40}`alt`", text)
    for da in ("altbau_entfernen", "archiv/", "altbau-557"):
        assert da in text, da
    assert re.search(r"[Kk]ein(en)? Rückweg", text)
    assert "GitHub" in text and "Reisespeicher" in text


def test_adr_und_regeln_ohne_workflow_software_nachziehen():
    """AC-35: ADR-0009, CLAUDE.md und openspec.yaml nennen den Workflow nicht mehr."""
    for datei in ("docs/adr/0009-reisespeicher.md", "CLAUDE.md", "openspec.yaml"):
        text = _text(datei)
        assert "Software nachziehen" not in text and "software-nachziehen" not in text, datei
    assert "#557" in _text("docs/adr/0009-reisespeicher.md")
