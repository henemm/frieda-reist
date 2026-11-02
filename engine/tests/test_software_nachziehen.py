"""Workflow „Software nachziehen“ (#161, #168, #250): Die Vorlage für das Reisen-Repo ermittelt nur den Stand, setzt
das Submodul und ruft frieda/betrieb/software-nachziehen.sh aus dem neuen Stand auf. Das Skript stellt jede Reise um,
prüft (Tor wie beim Veröffentlichen), übernimmt Submodul und Reisen in einem Commit des Bots und legt bei rotem Tor ein
Issue an. Die Vorlage ist allgemein (nichts einer Instanz).

Die Skript-Tests laufen gegen echte Git-Repos: eine Software als eigenes Repo (Kopie von engine/ und betrieb/ aus dem
Arbeitsbaum, Stände A und B), ein Reisen-Repo mit Submodul frieda/ und Bare-Remote, ein Klon wie auf dem Runner.
`neu.py nachziehen` läuft echt. Attrappen über PATH: `python`/`python3` (pytest und bauen.py, alles andere echt) und
`gh` (Issues in einer JSON-Datei). Testhaken des Skripts: SN_PAUSE (Sekunden zwischen zwei Push-Versuchen).
Erfundene Testdaten (Ida, Karl)."""
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

WURZEL = Path(__file__).resolve().parents[2]
VORLAGE = WURZEL / "betrieb" / "software-nachziehen.yml"
SKRIPT = WURZEL / "betrieb" / "software-nachziehen.sh"
BETRIEB_MD = WURZEL / "docs" / "betrieb.md"
VORLAGE_ALT = WURZEL / "engine" / "altformen" / "vorlage-vor-217"
sys.path.insert(0, str(WURZEL / "engine"))
import neu  # noqa: E402

# Lokale Submodule über file:// erlaubt (neuere Git-Versionen sperren sie sonst), beim Aufbau und im Skript
GIT_ERLAUBT = {"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "protocol.file.allow", "GIT_CONFIG_VALUE_0": "always"}
GIT = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
       **GIT_ERLAUBT}
SAUBER = {k: v for k, v in os.environ.items()
          if not k.startswith(("FR_", "VF_", "SN_", "GITHUB_", "GH_", "GIT_", "ALT", "NEU", "RUNNER_"))}


def lade():
    return yaml.safe_load(VORLAGE.read_text(encoding="utf-8"))


def schritte():
    return lade()["jobs"]["nachziehen"]["steps"]


def schritt(name):
    return next(s for s in schritte() if s.get("name") == name)


def aufruf_schritt():
    treffer = [s for s in schritte() if "frieda/betrieb/software-nachziehen.sh" in s.get("run", "")]
    assert len(treffer) == 1, "genau ein Schritt ruft das Skript"
    return treffer[0]


# ---------- Vorlage des Workflows (AC-1) ----------

# Stand der Vorlage auf main vor #250 (74a2d29): diese beiden Schritte bleiben wörtlich gleich.
STAND_VORHER = {
    "name": "Neuer Stand?", "id": "stand",
    "run": 'alt=$(git -C frieda rev-parse HEAD)\n'
           '# Das Submodul ist ein flacher Klon. Vorwärts-Prüfung und Commit-Liste brauchen die volle Historie.\n'
           'git -C frieda fetch -q --unshallow origin main 2>/dev/null || git -C frieda fetch -q origin main\n'
           'neu=$(git -C frieda rev-parse origin/main)\n'
           'neu_da=ja\n'
           'if [ "$alt" = "$neu" ]; then\n'
           '  neu_da=nein\n'
           'elif ! git -C frieda merge-base --is-ancestor "$alt" "$neu"; then\n'
           '  # Nur vorwärts: ein Stand, der nicht auf dem eingebundenen aufbaut, wird nie übernommen.\n'
           '  neu_da=nein\n'
           '  echo "::warning::main der Software liegt nicht vor dem eingebundenen Stand, nichts übernommen"\n'
           'fi\n'
           '{ echo "alt=$alt"; echo "neu=$neu"; echo "neu_da=$neu_da"; } >> "$GITHUB_OUTPUT"\n'}
SUBMODUL_VORHER = {"name": "Submodul setzen", "if": "steps.stand.outputs.neu_da == 'ja'",
                   "run": 'git -C frieda checkout -q "${{ steps.stand.outputs.neu }}"'}


def test_ausloeser_rechte_und_ein_lauf_gleichzeitig():  # AC-1
    w = lade()
    ausloeser = w.get("on", w.get(True))  # PyYAML liest den Schlüssel `on` als True
    assert ausloeser["schedule"] == [{"cron": "7,37 * * * *"}] and "workflow_dispatch" in ausloeser
    assert w["permissions"] == {"contents": "write", "issues": "write"}
    assert w["concurrency"] == {"group": "software-nachziehen", "cancel-in-progress": False}


def test_stand_und_submodul_bleiben_unveraendert():  # AC-1
    assert schritt("Neuer Stand?") == STAND_VORHER
    assert schritt("Submodul setzen") == SUBMODUL_VORHER


def test_volle_historie_fuer_vorwaerts_pruefung():
    """actions/checkout holt Submodule flach; ohne volle Historie scheitert merge-base --is-ancestor immer."""
    run = schritt("Neuer Stand?")["run"]
    assert "fetch -q --unshallow origin main" in run
    assert run.index("--unshallow") < run.index("merge-base --is-ancestor")


def test_python_in_jedem_lauf():  # AC-1, AC-2: umgestellt wird auch ohne neuen Software-Stand
    python = next(s for s in schritte() if str(s.get("uses", "")).startswith("actions/setup-python"))
    pakete = schritt("Python-Pakete")
    assert "if" not in python and "if" not in pakete
    assert "frieda/engine/requirements.txt" in pakete["run"]


def test_vorlage_ruft_das_skript_mit_dem_stand():  # AC-1
    s = aufruf_schritt()
    env = s.get("env", {})
    assert "steps.stand.outputs.alt" in env.get("ALT", "")
    assert "steps.stand.outputs.neu }}" in env.get("NEU", "").replace("neu}}", "neu }}")
    assert "steps.stand.outputs.neu_da" in env.get("NEU_DA", "")
    assert "github.token" in env.get("GH_TOKEN", "")
    assert "${{" not in s["run"]                     # Werte nur über env, der Aufruf ist reines Shell
    assert "if" not in s                             # in jedem Lauf, auch ohne neuen Stand
    # Der Ablauf liegt im Skript, nicht mehr in der Vorlage
    text = VORLAGE.read_text(encoding="utf-8")
    assert "gh issue create" not in text and "git push" not in text and "bauen.py" not in text


def test_vorlage_skript_fehlt_lauf_rot_mit_hinweis(tmp_path):  # AC-1
    """Ist das Submodul älter als #250, fehlt das Skript: Der Lauf endet rot mit einem Hinweis im Protokoll."""
    (tmp_path / "frieda" / "betrieb").mkdir(parents=True)
    r = subprocess.run(["bash", "-e", "-c", aufruf_schritt()["run"]], cwd=tmp_path, capture_output=True, text=True,
                       env={**SAUBER, "ALT": "a" * 40, "NEU": "b" * 40, "NEU_DA": "ja"})
    assert r.returncode != 0
    assert "software-nachziehen.sh" in r.stdout + r.stderr


def test_nichts_einer_instanz():  # #161 AC-4, auch für das Skript
    for datei in (VORLAGE, SKRIPT):
        text = datei.read_text(encoding="utf-8")
        assert "/srv/" not in text and "/home/" not in text, datei.name
        assert "henemm" not in text and "frieda-reisen" not in text, datei.name
        domains = set(re.findall(r"[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:com|de|org|net|io)\b", text))
        assert domains <= {"users.noreply.github.com", "github.com"}, (datei.name, domains)


def test_skript_erzwingt_nie():  # AC-4
    text = SKRIPT.read_text(encoding="utf-8")
    assert "--force" not in text and not re.search(r"push\s+(-\w*f|\S+\s+-f\b)", text)
    assert os.access(SKRIPT, os.X_OK)


# ---------- Doku (AC-8) ----------

def test_doku_einrichten_und_ueberwachung():  # #161 AC-5, #250 AC-8
    doku = BETRIEB_MD.read_text(encoding="utf-8")
    einrichten = doku.split("## Neue Instanz einrichten", 1)[1].split("\n## ", 1)[0]
    assert "betrieb/software-nachziehen.yml" in einrichten and ".github/workflows/" in einrichten
    assert "contents: write" in einrichten and "issues: write" in einrichten
    assert "nur bei grünen Tests" not in einrichten and "Bau jeder Reise" in einrichten   # #168 AC-5
    konvention = doku.split("Konvention für `tests/`", 1)[1].split("\n\n", 1)[0]
    assert "Software nachziehen" in konvention
    ueberwachung = doku.split("## Überwachung", 1)[1].split("\n## ", 1)[0]
    assert "Rückstand" in ueberwachung and "main" in ueberwachung


def test_doku_ablauf_anstoss_und_regel():  # AC-8
    doku = BETRIEB_MD.read_text(encoding="utf-8")
    assert "betrieb/software-nachziehen.sh" in doku and "neu.py nachziehen" in doku
    assert "FR_NACHZIEHEN_WIEDERHOLEN_STUNDEN" in doku and "nachziehen-angestossen" in doku
    regel = [z for z in (WURZEL / "CLAUDE.md").read_text(encoding="utf-8").splitlines()
             if "neu.py nachziehen" in z and "Format" in z]
    assert regel and "Test" in regel[0], "Regel: Formatänderung bringt ihre Umstellung mit, mit Test"
    for datei in [BETRIEB_MD, WURZEL / "CLAUDE.md", *sorted((WURZEL / "betrieb").glob("*"))]:
        if datei.is_file():
            assert "von Hand übernommen" not in datei.read_text(encoding="utf-8"), datei.name


# ---------- Skript gegen echte Repos (AC-2 bis AC-4) ----------

def git(ordner, *args, ok=True):
    r = subprocess.run(["git", "-C", str(ordner), *args], capture_output=True, text=True, env={**SAUBER, **GIT})
    if ok and r.returncode:
        raise AssertionError(f"git {' '.join(args)}: {r.stderr}")
    return r.stdout.strip()


def ausfuehrbar(pfad, text):
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(text, encoding="utf-8")
    pfad.chmod(0o755)
    return pfad


def ausgefuellt(sprache, datei):
    """Die frühere Vorlage, ausgefüllt wie neu.py sie bis #217 schrieb (jeder Platzhalter durch Text ersetzt)."""
    text = (VORLAGE_ALT / sprache / datei).read_text(encoding="utf-8")
    return re.sub(r"\$[a-z_]+", "Probe", text)


VON, BIS = datetime.date(2027, 2, 6), datetime.date(2027, 2, 13)
PERSONEN = {"ida": {"name": "Ida", "rolle": "organisator"}, "karl": {"name": "Karl", "rolle": "mitwirkend"}}

GH_ATTRAPPE = r'''#!{python}
"""gh-Attrappe: Issues in {zustand}, jeder Aufruf als JSON-Zeile in {log}. --jq über das echte jq."""
import json, subprocess, sys
zustand, log = {zustand!r}, {log!r}
a = sys.argv[1:]
with open(log, "a") as f:
    f.write(json.dumps(a) + "\n")
try:
    d = json.load(open(zustand))
except FileNotFoundError:
    d = {{"issues": []}}
def wert(name):
    for i, x in enumerate(a):
        if x == name and i + 1 < len(a):
            return a[i + 1]
        if x.startswith(name + "="):
            return x.split("=", 1)[1]
    return None
def ausgabe(obj):
    felder = wert("--json")
    if felder:
        f = felder.split(",")
        obj = [{{k: v for k, v in o.items() if k in f}} for o in obj] if isinstance(obj, list) else {{k: v for k, v in obj.items() if k in f}}
        text = json.dumps(obj)
        jq = wert("--jq") or wert("-q")
        if jq:
            text = subprocess.run(["jq", "-r", jq], input=text, capture_output=True, text=True, check=True).stdout
        print(text.rstrip("\n"))
    else:
        for o in (obj if isinstance(obj, list) else [obj]):
            print(f"{{o['number']}}\tOPEN\t{{o['title']}}")
def sichtbar(o):
    lab = wert("--label") or wert("-l")
    st = (wert("--state") or wert("-s") or "open").upper()
    return (not lab or lab in [x["name"] for x in o["labels"]]) and (st == "ALL" or o["state"] == st)
if a[:2] == ["issue", "list"]:
    ausgabe([o for o in d["issues"] if sichtbar(o)])
elif a[:2] == ["issue", "view"]:
    ausgabe(next(o for o in d["issues"] if str(o["number"]) == a[2].lstrip("#")))
elif a[:2] == ["issue", "create"]:
    body = wert("--body") or wert("-b") or ""
    if wert("--body-file") or wert("-F"):
        body = open(wert("--body-file") or wert("-F")).read()
    lab = wert("--label") or wert("-l")
    n = len(d["issues"]) + 1
    d["issues"].append({{"number": n, "title": wert("--title") or wert("-t"), "body": body, "state": "OPEN",
                        "labels": [{{"name": lab}}] if lab else [], "comments": []}})
    print(f"https://github.com/probe/reisen/issues/{{n}}")
elif a[:2] == ["issue", "comment"]:
    body = wert("--body") or wert("-b") or ""
    if wert("--body-file") or wert("-F"):
        body = open(wert("--body-file") or wert("-F")).read()
    o = next(o for o in d["issues"] if str(o["number"]) == a[2].lstrip("#"))
    o["comments"].append({{"body": body}})
json.dump(d, open(zustand, "w"))
'''

PYTHON_ATTRAPPE = r'''#!/bin/sh
# Attrappe für python/python3: Tests der Software (rot-software), Tests des Reisen-Repos (rot-inhalt) und der Bau einer
# Reise (kaputt-<reise>; beim-bau läuft vor dem ersten Bau). Alles andere (neu.py nachziehen) läuft echt.
case "$*" in
  *"-m pytest"*engine/tests*) echo software >> {t}/tor.log; [ ! -e {t}/rot-software ]; exit ;;
  *"-m pytest"*) echo inhalt >> {t}/tor.log; [ ! -e {t}/rot-inhalt ]; exit ;;
  *bauen.py*)
    for a; do r="$a"; done
    echo "bau $r" >> {t}/tor.log
    if [ -x {t}/beim-bau ]; then {t}/beim-bau; rm -f {t}/beim-bau; fi
    [ ! -e {t}/kaputt-"$r" ]; exit ;;
esac
exec {python} "$@"
'''


@pytest.fixture(scope="module")
def software(tmp_path_factory):
    """Die Software als eigenes Repo: Stand A (Kopie des Arbeitsbaums) und Stand B (ein Commit mehr), als Bare-Remote."""
    t = tmp_path_factory.mktemp("software")
    sw = t / "sw"
    sw.mkdir()
    weg = shutil.ignore_patterns(".venv", "tests", "__pycache__", "node_modules", "*.pyc")
    shutil.copytree(WURZEL / "engine", sw / "engine", ignore=weg)
    shutil.copytree(WURZEL / "betrieb", sw / "betrieb", ignore=weg)
    git(sw, "init", "-q", "-b", "main")
    git(sw, "add", ".")
    git(sw, "commit", "-qm", "Stand A")
    a = git(sw, "rev-parse", "HEAD")
    (sw / "engine" / "neues.txt").write_text("B\n", encoding="utf-8")
    git(sw, "add", ".")
    git(sw, "commit", "-qm", "Neues aus der Software")
    b = git(sw, "rev-parse", "HEAD")
    subprocess.run(["git", "clone", "-q", "--bare", str(sw), str(t / "sw.git")], check=True, env={**SAUBER, **GIT})
    return {"bare": t / "sw.git", "a": a, "b": b, "a7": a[:7], "b7": b[:7], "ordner": t}


@pytest.fixture
def sn(tmp_path, software):
    """Reisen-Repo mit Submodul frieda/ auf Stand A, zwei Reisen, tests/ und Bare-Remote; Attrappen; lauf() klont wie
    der Runner, setzt das Submodul (wie die Schritte „Neuer Stand?“ und „Submodul setzen“) und ruft das Skript."""
    t = tmp_path
    rq = t / "rq"
    rq.mkdir()
    git(rq, "init", "-q", "-b", "main")
    git(rq, "submodule", "add", "-q", str(software["bare"]), "frieda")
    git(rq / "frieda", "checkout", "-q", software["a"])
    ski = neu.anlegen(rq / "reisen", titel="Skiurlaub im Tal", von=VON, bis=BIS, personen=PERSONEN, wer="Ida",
                      ziel="Oberstdorf", heute=datetime.date(2026, 10, 27))
    wanderung = neu.anlegen(rq / "reisen", titel="Wanderung am See", von=VON, bis=BIS, personen=PERSONEN, wer="Ida",
                            ziel="Bodensee", heute=datetime.date(2026, 10, 27), sprache="en")
    (rq / "tests").mkdir()
    (rq / "tests" / "test_inhalt.py").write_text("def test_inhalt():\n    pass\n", encoding="utf-8")
    git(rq, "add", ".")
    git(rq, "commit", "-qm", "Start")
    remote = t / "reisen.git"
    subprocess.run(["git", "clone", "-q", "--bare", str(rq), str(remote)], check=True, env={**SAUBER, **GIT})
    git(rq, "remote", "add", "origin", str(remote), ok=False)
    git(rq, "remote", "set-url", "origin", str(remote))
    git(rq, "fetch", "-q", "origin")
    git(rq, "branch", "-q", "--set-upstream-to=origin/main", "main")

    python = sys.executable
    ausfuehrbar(t / "bin" / "gh", GH_ATTRAPPE.format(python=python, zustand=str(t / "gh.json"), log=str(t / "gh.log")))
    for name in ("python", "python3"):
        ausfuehrbar(t / "bin" / name, PYTHON_ATTRAPPE.format(t=t, python=python))
    (t / "runner").mkdir()

    zaehler = {"n": 0}

    def lauf(neu_da="ja", alt=None, neu_=None):
        """Ein Lauf des Workflows in einem frischen Klon. Gibt (Ergebnis, Klon) zurück."""
        zaehler["n"] += 1
        klon = t / f"lauf{zaehler['n']}"
        subprocess.run(["git", "clone", "-q", "--recurse-submodules", str(remote), str(klon)], check=True,
                       env={**SAUBER, **GIT}, capture_output=True)
        alt = alt or git(klon / "frieda", "rev-parse", "HEAD")
        neu_ = neu_ or (software["b"] if neu_da == "ja" else alt)
        git(klon / "frieda", "fetch", "-q", "origin", "main")
        if neu_da == "ja":
            git(klon / "frieda", "checkout", "-q", neu_)
        env = {**SAUBER, **GIT_ERLAUBT, "PATH": f"{t / 'bin'}:{os.environ['PATH']}", "ALT": alt, "NEU": neu_,
               "NEU_DA": neu_da, "GH_TOKEN": "probe", "GITHUB_SERVER_URL": "https://github.com",
               "GITHUB_REPOSITORY": "probe/reisen", "GITHUB_RUN_ID": "42", "RUNNER_TEMP": str(t / "runner"),
               "SN_PAUSE": "0", "HOME": str(t)}
        r = subprocess.run([str(klon / "frieda" / "betrieb" / "software-nachziehen.sh")], cwd=klon, env=env,
                           capture_output=True, text=True, timeout=300)
        return r, klon

    def kopf():
        return git(remote, "rev-parse", "main")

    def schreiben(pfad, text, nachricht="Schreibweg: Änderung"):
        """Ein Commit auf origin/main, wie der Schreibweg ihn macht."""
        ziel = rq / pfad
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text(text, encoding="utf-8")
        git(rq, "pull", "-q", "--rebase", "origin", "main")
        git(rq, "add", ".")
        git(rq, "commit", "-qm", nachricht)
        git(rq, "push", "-q", "origin", "HEAD:main")

    def tor():
        datei = t / "tor.log"
        z = datei.read_text().splitlines() if datei.exists() else []
        datei.unlink(missing_ok=True)
        return z

    def gh_aufrufe():
        datei = t / "gh.log"
        return [json.loads(z) for z in datei.read_text().splitlines()] if datei.exists() else []

    def issues():
        datei = t / "gh.json"
        return json.loads(datei.read_text())["issues"] if datei.exists() else []

    def issue_vorab(titel):
        (t / "gh.json").write_text(json.dumps({"issues": [
            {"number": 1, "title": titel, "body": "Früherer Lauf", "state": "OPEN",
             "labels": [{"name": "software-nachziehen"}], "comments": []}]}))

    def reste(reise):
        """Reste der früheren Vorlage in einer Reise (Commit auf origin/main)."""
        sprache = "de" if reise == ski.name else "en"
        schreiben(f"reisen/{reise}/CLAUDE.md", ausgefuellt(sprache, "CLAUDE.md"), f"{reise}: Rest der Vorlage")

    return {"lauf": lauf, "kopf": kopf, "schreiben": schreiben, "tor": tor,
            "gh": gh_aufrufe, "issues": issues, "issue_vorab": issue_vorab, "reste": reste, "remote": remote,
            "ski": ski.name, "wanderung": wanderung.name, "tmp": t, "sw": software}


def auf_main(sn, pfad):
    return subprocess.run(["git", "-C", str(sn["remote"]), "cat-file", "-e", f"main:{pfad}"],
                          capture_output=True).returncode == 0


def test_neuer_stand_ein_commit_mit_submodul_und_umgestellten_reisen(sn):  # AC-2
    sn["reste"](sn["ski"])
    vorher = sn["kopf"]()
    r, _ = sn["lauf"]("ja")
    assert r.returncode == 0, r.stdout + r.stderr
    assert git(sn["remote"], "rev-list", "--count", f"{vorher}..main") == "1"     # genau ein Commit
    assert git(sn["remote"], "rev-parse", "main:frieda") == sn["sw"]["b"]
    assert not auf_main(sn, f"reisen/{sn['ski']}/CLAUDE.md")                    # im selben Commit umgestellt
    nachricht = git(sn["remote"], "log", "-1", "--format=%B", "main")
    assert nachricht.splitlines()[0] == f"Software auf Stand {sn['sw']['b7']} (automatisch)"
    assert "Neues aus der Software" in nachricht                                 # Liste der Commits
    assert sn["ski"] in nachricht and "CLAUDE.md" in nachricht                   # Meldungen der Umstellung je Reise
    assert git(sn["remote"], "log", "-1", "--format=%an", "main") == "github-actions[bot]"
    assert re.search(r"@users\.noreply\.github\.com$", git(sn["remote"], "log", "-1", "--format=%ae", "main"))
    t = sn["tor"]()
    assert "software" in t and f"bau {sn['ski']}" in t and f"bau {sn['wanderung']}" in t and "inhalt" in t

    # Ein zweiter Lauf direkt danach ändert nichts (AC-2), auch ohne Tor
    nachher = sn["kopf"]()
    r, _ = sn["lauf"]("nein")
    assert r.returncode == 0, r.stdout + r.stderr
    assert sn["kopf"]() == nachher and sn["tor"]() == []
    assert not any(a[:2] == ["issue", "create"] for a in sn["gh"]())


def test_ohne_neuen_stand_werden_reisen_umgestellt(sn):  # AC-2
    sn["reste"](sn["wanderung"])
    vorher = sn["kopf"]()
    r, _ = sn["lauf"]("nein")
    assert r.returncode == 0, r.stdout + r.stderr
    assert git(sn["remote"], "rev-list", "--count", f"{vorher}..main") == "1"
    assert git(sn["remote"], "rev-parse", "main:frieda") == sn["sw"]["a"]          # Submodul bleibt
    assert not auf_main(sn, f"reisen/{sn['wanderung']}/CLAUDE.md")
    nachricht = git(sn["remote"], "log", "-1", "--format=%B", "main")
    assert nachricht.splitlines()[0] == "Reisen auf den Stand der Software umgestellt (automatisch)"
    assert sn["wanderung"] in nachricht
    t = sn["tor"]()
    assert "software" not in t                                                    # engine/tests nur bei neuem Stand
    assert f"bau {sn['ski']}" in t and f"bau {sn['wanderung']}" in t               # Bau in jedem Lauf mit Änderung


def test_ohne_aenderung_kein_commit(sn):  # AC-2
    vorher = sn["kopf"]()
    r, _ = sn["lauf"]("nein")
    assert r.returncode == 0, r.stdout + r.stderr
    assert sn["kopf"]() == vorher and sn["tor"]() == [] and sn["issues"]() == []


def test_rote_reisetests_warnen_nur(sn):  # AC-3
    (sn["tmp"] / "rot-inhalt").touch()
    vorher = sn["kopf"]()
    r, _ = sn["lauf"]("ja")
    assert r.returncode == 0, r.stdout + r.stderr
    assert sn["kopf"]() != vorher and git(sn["remote"], "rev-parse", "main:frieda") == sn["sw"]["b"]
    assert "::warning::" in r.stdout and sn["issues"]() == []


@pytest.mark.parametrize("rot", ["rot-software", "kaputt-SKI"])
def test_tor_rot_ohne_offenes_issue(sn, rot):  # AC-3
    (sn["tmp"] / rot.replace("SKI", sn["ski"])).touch()
    vorher = sn["kopf"]()
    r, _ = sn["lauf"]("ja")
    assert r.returncode == 1, r.stdout + r.stderr
    assert sn["kopf"]() == vorher                                                 # nichts übernommen
    i = sn["issues"]()
    assert len(i) == 1 and i[0]["labels"] == [{"name": "software-nachziehen"}]
    assert sn["sw"]["b7"] in i[0]["title"]


def test_tor_rot_mit_offenem_issue_kommentiert_den_neuen_stand_einmal(sn):  # AC-3
    sn["issue_vorab"]("Software-Stand 0000000 lässt sich nicht automatisch übernehmen")
    (sn["tmp"] / "rot-software").touch()
    vorher = sn["kopf"]()
    r, _ = sn["lauf"]("ja")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "::warning::" in r.stdout and sn["kopf"]() == vorher
    i = sn["issues"]()
    assert len(i) == 1 and len(i[0]["comments"]) == 1
    assert sn["sw"]["b7"] in i[0]["comments"][0]["body"] and "/actions/runs/42" in i[0]["comments"][0]["body"]

    r, _ = sn["lauf"]("ja")                                                       # derselbe Stand: kein Kommentar mehr
    assert r.returncode == 0 and len(sn["issues"]()[0]["comments"]) == 1 and len(sn["issues"]()) == 1


def test_tor_rot_issue_nennt_den_stand_schon(sn):  # AC-3
    sn["issue_vorab"](f"Software-Stand {sn['sw']['b7']} lässt sich nicht automatisch übernehmen")
    (sn["tmp"] / "rot-software").touch()
    r, _ = sn["lauf"]("ja")
    assert r.returncode == 0, r.stdout + r.stderr
    assert sn["issues"]()[0]["comments"] == [] and len(sn["issues"]()) == 1


def test_tor_rot_ohne_neuen_stand(sn):  # AC-3: eine umgestellte Reise baut nicht
    sn["reste"](sn["ski"])
    (sn["tmp"] / f"kaputt-{sn['ski']}").touch()
    vorher = sn["kopf"]()
    r, _ = sn["lauf"]("nein")
    assert r.returncode == 1, r.stdout + r.stderr
    assert sn["kopf"]() == vorher
    i = sn["issues"]()
    assert len(i) == 1 and sn["sw"]["a7"] in i[0]["title"]


def test_wettlauf_mit_dem_schreibweg_stellt_neu_um(sn):  # AC-4
    """Zwischen Umstellen und Push schreibt der Schreibweg auf main (mit einem Rest der Vorlage): Das Skript setzt auf
    origin/main zurück, stellt neu um und übernimmt; der Commit des Schreibwegs bleibt, nichts wird erzwungen."""
    sn["reste"](sn["ski"])
    t = sn["tmp"]
    rest = ausgefuellt("en", "CLAUDE.md").replace("'", "'\\''")
    ausfuehrbar(t / "beim-bau", f"""#!/bin/sh
set -e
k={t}/schreiber
git clone -q {sn['remote']} "$k"
printf '%s' '{rest}' > "$k/reisen/{sn['wanderung']}/CLAUDE.md"
git -C "$k" add .
git -C "$k" -c user.name=s -c user.email=s@s commit -qm "Schreibweg: Wanderung"
git -C "$k" push -q origin HEAD:main
""")
    r, _ = sn["lauf"]("ja")
    assert r.returncode == 0, r.stdout + r.stderr
    schreibweg = git(sn["remote"], "log", "--format=%H", "--grep=Schreibweg: Wanderung", "main")
    assert schreibweg and git(sn["remote"], "rev-list", "--count", f"{schreibweg}..main") == "1"
    assert git(sn["remote"], "log", "-1", "--format=%an", "main") == "github-actions[bot]"
    assert git(sn["remote"], "rev-parse", "main:frieda") == sn["sw"]["b"]
    assert not auf_main(sn, f"reisen/{sn['ski']}/CLAUDE.md")
    assert not auf_main(sn, f"reisen/{sn['wanderung']}/CLAUDE.md")               # neu umgestellt
    assert sn["tor"]().count("software") >= 1


def test_drei_gescheiterte_pushes_rot_ohne_issue(sn):  # AC-4
    sn["reste"](sn["ski"])
    vorher = sn["kopf"]()
    ausfuehrbar(sn["remote"] / "hooks" / "pre-receive", f"#!/bin/sh\necho versuch >> {sn['tmp']}/push.log\nexit 1\n")
    r, _ = sn["lauf"]("ja")
    assert r.returncode == 1, r.stdout + r.stderr
    assert (sn["tmp"] / "push.log").read_text().split() == ["versuch"] * 3
    assert sn["kopf"]() == vorher
    assert not any(a[:2] == ["issue", "create"] for a in sn["gh"]()) and sn["issues"]() == []


def test_tor_rot_issue_abfrage_scheitert_rot_ohne_neues_issue(sn):  # AC-3, Gegenprüfung F002
    """Scheitert `gh issue list`, ist unbekannt, ob schon ein Issue offen ist: kein Issue anlegen (kein Doppel), kein
    Commit, der Lauf endet rot mit Hinweis, damit GitHub mailt."""
    t = sn["tmp"]
    echt = t / "bin" / "gh-echt"
    (t / "bin" / "gh").rename(echt)
    ausfuehrbar(t / "bin" / "gh", f'#!/bin/sh\nif [ "$1 $2" = "issue list" ]; then echo "$@" >> {t}/gh-list.log; exit 1; fi\n'
                                  f'exec {echt} "$@"\n')
    (t / "rot-software").touch()
    vorher = sn["kopf"]()
    r, _ = sn["lauf"]("ja")
    assert r.returncode == 1, r.stdout + r.stderr
    assert (t / "gh-list.log").exists() and "::error::" in r.stdout
    assert sn["kopf"]() == vorher
    assert not any(a[:2] == ["issue", "create"] for a in sn["gh"]()) and sn["issues"]() == []
