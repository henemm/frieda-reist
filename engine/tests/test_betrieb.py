"""Tests für den Betrieb (betrieb/, docs/betrieb.md): Einstellungen, Veröffentlichen, Deploy, Freischalten, Wächter-Lauf,
Einrichten. nginx, sudo, curl, Python und der Meldeweg sind Attrappen, wo sie das System berühren würden; der Konnektor
ist echt. Alles mit der Beispielreise oder erfundenen Reisen."""
import json
import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parents[2]
ENGINE = WURZEL / "engine"
BETRIEB = WURZEL / "betrieb"
BEISPIEL = WURZEL / "beispiel" / "reisen" / "beispielreise"
sys.path.insert(0, str(BETRIEB))
sys.path.insert(0, str(ENGINE))
import bauen  # noqa: E402
import rueckmeldungen as rm  # noqa: E402
import zustellen  # noqa: E402

GIT = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
# Umgebung ohne Werte einer echten Instanz, die die Prüfung verfälschen könnten
SAUBER = {k: v for k, v in os.environ.items() if not k.startswith(("FR_", "RM_", "KN_", "EA_", "VF_", "FS_", "WA_"))}


def git(ordner, *args):
    return subprocess.run(["git", "-C", str(ordner), *args], check=True, capture_output=True, text=True,
                          env={**os.environ, **GIT}).stdout


def ausfuehrbar(pfad, text):
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(text)
    pfad.chmod(0o755)
    return pfad


# ---------- Einstellungen (gemeinsam.sh) ----------

def einstellungen(tmp_path, datei_text, **umgebung):
    """Liest gemeinsam.sh mit einer Einstellungsdatei und gibt die Werte zurück, die die Skripte sehen."""
    (tmp_path / "betrieb").mkdir(exist_ok=True)
    (tmp_path / "betrieb/einstellungen.env").write_text(datei_text)
    namen = ["FR_INSTANZ", "FR_TITEL", "FR_SEITEN", "FR_ABLAGE", "FR_DIENST", "FR_KN_ADRESSE", "FR_PYTHON", "RM_ABLAGE",
             "KN_SEITEN", "KN_ZUGAENGE", "KN_BASIS", "FR_ADRESSE", "FR_UMZUG_NACH"]
    skript = f'. "{BETRIEB}/gemeinsam.sh"; ' + "; ".join(f'echo "{n}=${{{n}:-}}"' for n in namen)
    r = subprocess.run(["bash", "-c", skript], capture_output=True, text=True,
                       env={**SAUBER, "FR_WURZEL": str(tmp_path), **umgebung})
    return r, dict(z.split("=", 1) for z in r.stdout.splitlines() if "=" in z)


def test_einstellungen_aus_datei_mit_vorgaben(tmp_path):
    r, w = einstellungen(tmp_path, "# Kommentar\nFR_INSTANZ=probe\nFR_ADRESSE=\"https://reisen.example.org\"\n"
                                   "FR_TITEL=$(touch boese)\n")
    assert r.returncode == 0, r.stderr
    assert w["FR_INSTANZ"] == "probe" and w["FR_SEITEN"] == "/srv/probe" and w["FR_ABLAGE"] == "/srv/probe/_rueckmeldungen"
    assert w["RM_ABLAGE"] == "/srv/probe/_rueckmeldungen" and w["KN_ZUGAENGE"] == "/srv/probe/_konnektor/zugaenge.json"
    assert w["FR_KN_ADRESSE"] == w["KN_BASIS"] == "https://reisen.example.org"   # Konnektor an der Wurzel (#163)
    assert w["FR_PYTHON"] == f"{tmp_path}/engine/.venv/bin/python"
    assert w["FR_UMZUG_NACH"] == ""
    r2, w2 = einstellungen(tmp_path, "FR_UMZUG_NACH=https://neu.example.org\n")   # wird an bauen.py weitergereicht (exportiert)
    assert w2["FR_UMZUG_NACH"] == "https://neu.example.org"
    # keine Shell-Auswertung: der Wert bleibt Text, es wird nichts ausgeführt
    assert w["FR_TITEL"] == "$(touch boese)" and not (Path.cwd() / "boese").exists()


def test_umgebung_gilt_vor_der_datei_und_fremdes_wird_ignoriert(tmp_path):
    r, w = einstellungen(tmp_path, "FR_INSTANZ=probe\nPATH=/nirgends\nRM_ABLAGE=/falsch\nFR_SEITEN=/srv/datei\n",
                         FR_SEITEN="/srv/umgebung")
    assert r.returncode == 0 and w["FR_SEITEN"] == "/srv/umgebung" and w["RM_ABLAGE"] == "/srv/umgebung/_rueckmeldungen"
    assert "line ignored" in r.stderr and "PATH" in r.stderr


def test_geheime_werte_aus_dem_dienstordner(tmp_path):
    (tmp_path / "dienst").mkdir()
    (tmp_path / "dienst/betrieb.env").write_text("FR_MELDEN=/pfad/melden.sh\n")
    r = subprocess.run(["bash", "-c", f'. "{BETRIEB}/gemeinsam.sh"; echo "$FR_MELDEN"'], capture_output=True, text=True,
                       env={**SAUBER, "FR_WURZEL": str(tmp_path), "FR_DIENST": str(tmp_path / "dienst")})
    assert r.stdout.strip() == "/pfad/melden.sh"
    (tmp_path / "dienst/betrieb.env").write_text("FR_MELDEN=betrieb/melden.sh\n")
    r = subprocess.run(["bash", "-c", f'. "{BETRIEB}/gemeinsam.sh"; echo "$FR_MELDEN"'], capture_output=True, text=True,
                       env={**SAUBER, "FR_WURZEL": str(tmp_path), "FR_DIENST": str(tmp_path / "dienst")})
    assert r.stdout.strip() == f"{tmp_path}/betrieb/melden.sh"


def test_ungueltiger_instanzname(tmp_path):
    r, _ = einstellungen(tmp_path, "FR_INSTANZ=Böse Instanz\n")
    assert r.returncode != 0 and "FR_INSTANZ" in r.stderr


def test_ohne_wurzel_bricht_ab(tmp_path):
    """Außerhalb eines Reisen-Repos (Software nicht als Submodul eingebunden) weiß der Betrieb nicht, wo er ist.
    Geprüft an einer Kopie außerhalb jedes Repos, weil die Software in einer Instanz selbst Submodul ist."""
    shutil.copy(BETRIEB / "gemeinsam.sh", tmp_path / "gemeinsam.sh")
    r = subprocess.run(["bash", "-c", f'. "{tmp_path}/gemeinsam.sh"'], capture_output=True, text=True,
                       env={**SAUBER, "GIT_CEILING_DIRECTORIES": str(tmp_path.parent)})
    assert r.returncode != 0 and "root of the instance" in r.stderr


def test_beispiel_einstellungen_sind_vollstaendig():
    """Jede FR_-Einstellung, die ein Skript liest, ist in einstellungen.beispiel erklärt."""
    beispiel = (BETRIEB / "einstellungen.beispiel").read_text(encoding="utf-8")
    erklaert = set(re.findall(r"^#?(FR_[A-Z0-9_]+)=", beispiel, re.M))
    gelesen = set()
    for f in BETRIEB.glob("*.sh"):
        gelesen |= set(re.findall(r"\$\{?(FR_[A-Z0-9_]+)", f.read_text(encoding="utf-8")))
    intern = {"FR_WURZEL", "FR_BETRIEB", "FR_EINSTELLUNGEN", "FR_PFAD", "FR_GRUPPE", "FR_HEARTBEAT_VEROEFFENTLICHEN",
              "FR_GEPRUEFT"}  # FR_GEPRUEFT reicht veroeffentlichen.sh an deploy.sh weiter
    assert gelesen - intern - erklaert == set()


# ---------- Veröffentlichen ----------

@pytest.fixture
def vf(tmp_path):
    """Origin mit main, Bauordner als Klon, Deploy-Attrappe, die jede Reise protokolliert."""
    if not shutil.which("flock"):
        pytest.skip("flock fehlt")
    quelle = tmp_path / "quelle"
    for reise in ("beispielreise", "zweitreise"):
        (quelle / "reisen" / reise).mkdir(parents=True)
        (quelle / "reisen" / reise / "reise.json").write_text("{}")
    git(quelle, "init", "-q", "-b", "main")
    git(quelle, "add", ".")
    git(quelle, "commit", "-qm", "start")
    arbeit = tmp_path / "arbeit"
    subprocess.run(["git", "clone", "-q", str(quelle), str(arbeit)], check=True)
    protokoll = tmp_path / "deploy.log"
    # Deploy-Attrappe (#142): kaputt-<reise> = Bau dieser Reise gescheitert (Exit 2), kaputt oder infra-<reise> =
    # Infrastrukturfehler (Exit 1)
    attrappe = ausfuehrbar(tmp_path / "deploy.sh", f'#!/bin/sh\necho "$1" >> {protokoll}\necho "$FR_GEPRUEFT" >> {tmp_path}/gepreuft.log\n'
                                                   f'[ -e {tmp_path}/kaputt ] && exit 1\n[ -e {tmp_path}/infra-$1 ] && exit 1\n'
                                                   f'[ -e {tmp_path}/kaputt-$1 ] && exit 2\nexit 0\n')
    # Prüf-Attrappe: aufgerufen mit „engine/tests“ (Software, rot über die Datei rot, Protokoll p) oder „tests“ (Tests des
    # Reisen-Repos, rot über rot-reise, Protokoll r)
    pruefen = ausfuehrbar(tmp_path / "pruefen.sh", f'#!/bin/sh\nif [ "$1" = tests ]; then echo r >> {tmp_path}/pruefen.log; '
                                                   f'[ ! -e {tmp_path}/rot-reise ]; exit; fi\n'
                                                   f'echo p >> {tmp_path}/pruefen.log\n[ ! -e {tmp_path}/rot ]\n')
    # Meldeweg an den Betrieb (FR_MELDEN) und Meldung an Personen (waechter.py rot-melden) als Attrappen
    melden = ausfuehrbar(tmp_path / "melden.sh", f'#!/bin/sh\necho "$1|$2" >> {tmp_path}/melden.log\n'
                                                 f'[ ! -e {tmp_path}/melden-aus ]\n')
    rotmelden = ausfuehrbar(tmp_path / "rotmelden.sh", f'#!/bin/sh\necho "$@" >> {tmp_path}/rotmelden.log\n')
    # curl-Attrappe: protokolliert Heartbeat-Abrufe statt ins Netz zu gehen
    pings = tmp_path / "pings.log"
    ausfuehrbar(tmp_path / "bin/curl", f'#!/bin/sh\necho ping >> {pings}\n')
    frei = ausfuehrbar(tmp_path / "freischalten.sh",
                       f'#!/bin/sh\necho "$1" >> {tmp_path}/frei.log\necho "Seite: https://example.invalid/$1-geheim/"\n')
    env = {**SAUBER, "FR_WURZEL": str(arbeit), "FR_INSTANZ": "probe", "FR_DIENST": str(tmp_path / "dienst"),
           "FR_KONNEKTOR": str(tmp_path / "konnektor"), "FR_SPERREN": str(tmp_path), "VF_DEPLOY": str(attrappe), "VF_PRUEFEN": str(pruefen), "VF_FREISCHALTEN": str(frei),
           "FR_HEARTBEAT_VEROEFFENTLICHEN": "https://example.invalid/hb", "PATH": f"{tmp_path / 'bin'}:{os.environ['PATH']}",
           "FR_MELDEN": str(melden), "VF_ROTMELDEN": str(rotmelden)}

    def lauf(*args, **extra):
        return subprocess.run([str(BETRIEB / "veroeffentlichen.sh"), *args], env={**env, **extra}, capture_output=True, text=True)

    def deploys():
        inhalt = protokoll.read_text().split() if protokoll.exists() else []
        protokoll.unlink(missing_ok=True)
        return inhalt

    def neuer_commit():
        (quelle / "neu.txt").write_text(str(len(git(quelle, "log", "--oneline"))))
        git(quelle, "add", ".")
        git(quelle, "commit", "-qm", "neu")

    def anzahl_pings():
        n = len(pings.read_text().split()) if pings.exists() else 0
        pings.unlink(missing_ok=True)
        return n

    def reisetests():
        """Das Reisen-Repo bekommt einen eigenen Testordner tests/ (wie eine echte Instanz)."""
        (quelle / "tests").mkdir(exist_ok=True)
        (quelle / "tests" / "test_inhalt.py").write_text("def test_inhalt():\n    pass\n")
        git(quelle, "add", ".")
        git(quelle, "commit", "-qm", "tests")

    def rot():
        """Inhalt der Rot-Datei <FR_DIENST>/veroeffentlichen-rot als dict, None wenn es sie nicht gibt."""
        datei = tmp_path / "dienst" / "veroeffentlichen-rot"
        if not datei.exists():
            return None
        return dict(z.split("=", 1) for z in datei.read_text(encoding="utf-8").splitlines() if "=" in z)

    def zeilen(name):
        datei = tmp_path / name
        return datei.read_text(encoding="utf-8").splitlines() if datei.exists() else []

    def kopf():
        return git(quelle, "rev-parse", "HEAD").strip()

    return {"lauf": lauf, "deploys": deploys, "pings": anzahl_pings, "neuer_commit": neuer_commit, "arbeit": arbeit,
            "tmp": tmp_path, "env": env, "reisetests": reisetests, "rot": rot, "zeilen": zeilen, "kopf": kopf}


T0 = 1_800_000_000   # erfundener Zeitpunkt für VF_JETZT (Sekunden seit 1970)


def iso(sekunden):
    import datetime
    return datetime.datetime.fromtimestamp(sekunden, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def hoch(vf):
    """Nachrichten an den Betrieb mit Priorität high."""
    return [z for z in vf["zeilen"]("melden.log") if z.startswith("high|")]


def test_veroeffentlichen_nur_bei_neuem_stand(vf):
    assert vf["lauf"]().returncode == 0
    assert vf["deploys"]() == ["beispielreise", "zweitreise"]
    assert (vf["tmp"] / "dienst/veroeffentlicht").read_text().strip() == git(vf["arbeit"], "rev-parse", "HEAD").strip()
    assert vf["lauf"]().returncode == 0
    assert vf["deploys"]() == []
    vf["neuer_commit"]()
    assert vf["lauf"]().returncode == 0
    assert vf["deploys"]() == ["beispielreise", "zweitreise"]
    assert (vf["arbeit"] / "neu.txt").exists()
    assert vf["lauf"]("--immer").returncode == 0
    assert vf["deploys"]() == ["beispielreise", "zweitreise"]


def test_veroeffentlichen_fehlschlag_wird_wiederholt(vf):
    """Ein Infrastrukturfehler (Exit 1 aus deploy.sh) beendet den Lauf sofort, wird nicht gemerkt und beim nächsten Lauf
    auf demselben Stand wiederholt (#142, AC-18)."""
    (vf["tmp"] / "kaputt").touch()
    assert vf["lauf"]().returncode == 1
    assert vf["deploys"]() == ["beispielreise"]
    assert vf["rot"]() is None
    assert vf["lauf"]().returncode == 1
    assert vf["deploys"]() == ["beispielreise"]                  # wiederholt, nicht übersprungen
    (vf["tmp"] / "kaputt").unlink()
    assert vf["lauf"]().returncode == 0
    assert vf["deploys"]() == ["beispielreise", "zweitreise"]


def test_veroeffentlichen_prueft_einmal_fuer_alle_reisen(vf):
    """Die Prüfungen laufen einmal je Lauf, nicht je Reise; deploy.sh bekommt den geprüften Stand und prüft nicht nochmal.
    Rote Software-Tests: keine Reise wird angefasst, der Stand bleibt ungemerkt, die Rot-Datei merkt den Stand (art=software);
    derselbe Stand wird erst mit --immer oder einem neuen Commit wieder geprüft (#142, AC-3, AC-15)."""
    (vf["tmp"] / "rot").touch()
    r = vf["lauf"](VF_JETZT=str(T0))
    assert r.returncode == 1 and "checks red" in r.stdout and vf["deploys"]() == []
    assert not (vf["tmp"] / "dienst/veroeffentlicht").exists()
    assert not (vf["tmp"] / "dienst/veroeffentlichen-erfolg").exists() and vf["pings"]() == 0
    rot = vf["rot"]()
    assert rot["commit"] == vf["kopf"]() and rot["art"] == "software" and rot["reisen"] == ""
    assert rot["seit"] == iso(T0) and rot["gemeldet"] == "0"
    (vf["tmp"] / "rot").unlink()
    r = vf["lauf"]()
    assert r.returncode == 0 and "Known red state" in r.stdout and vf["deploys"]() == []
    assert vf["zeilen"]("pruefen.log") == ["p"]
    assert vf["lauf"]("--immer").returncode == 0
    assert vf["deploys"]() == ["beispielreise", "zweitreise"]
    assert vf["zeilen"]("pruefen.log") == ["p", "p"]
    kopf = git(vf["arbeit"], "rev-parse", "HEAD").strip()
    assert (vf["tmp"] / "gepreuft.log").read_text().split() == [kopf, kopf]
    deploy = (BETRIEB / "deploy.sh").read_text(encoding="utf-8")
    assert 'if [ "${FR_GEPRUEFT:-}" != "$(git -C "$WURZEL" rev-parse HEAD)" ]; then' in deploy


def test_veroeffentlichen_laesst_laufende_arbeit_in_ruhe(vf):
    (vf["arbeit"] / "entwurf.md").write_text("halb fertig")
    erg = vf["lauf"]()
    assert erg.returncode == 0 and "Uncommitted" in erg.stdout
    assert vf["deploys"]() == []
    (vf["arbeit"] / "entwurf.md").unlink()
    git(vf["arbeit"], "checkout", "-qb", "baustelle")
    erg = vf["lauf"]()
    assert erg.returncode == 0 and "not on main" in erg.stdout
    assert vf["deploys"]() == []


def test_veroeffentlichen_heartbeat_nur_bei_erfolg(vf):
    (vf["tmp"] / "kaputt-beispielreise").touch()
    assert vf["lauf"]().returncode == 1
    assert vf["pings"]() == 0                                  # Bau einer Reise gescheitert (Teil-Erfolg ist kein Erfolg)
    assert vf["lauf"]().returncode == 0
    assert vf["pings"]() == 0                                  # bekannter roter Stand übersprungen
    (vf["tmp"] / "kaputt-beispielreise").unlink()
    vf["neuer_commit"]()
    assert vf["lauf"]().returncode == 0
    assert vf["pings"]() == 1                                  # repariert und veröffentlicht
    assert vf["lauf"]().returncode == 0
    assert vf["pings"]() == 1                                  # nichts Neues, Abruf gelungen
    (vf["arbeit"] / "entwurf.md").write_text("halb fertig")
    assert vf["lauf"]().returncode == 0
    assert vf["pings"]() == 0                                  # übersprungen


def test_veroeffentlichen_stempel_nur_bei_erfolg(vf):
    stempel = vf["tmp"] / "dienst" / "veroeffentlichen-erfolg"
    (vf["tmp"] / "kaputt-beispielreise").touch()
    assert vf["lauf"]().returncode == 1
    assert not stempel.exists()                                # Bau einer Reise gescheitert
    assert vf["lauf"]().returncode == 0
    assert not stempel.exists()                                # bekannter roter Stand übersprungen
    (vf["tmp"] / "kaputt-beispielreise").unlink()
    assert vf["lauf"]("--immer").returncode == 0
    assert stempel.exists()                                    # repariert und veröffentlicht
    stempel.unlink()
    (vf["arbeit"] / "entwurf.md").write_text("halb fertig")
    assert vf["lauf"]().returncode == 0
    assert not stempel.exists()                                # übersprungen
    (vf["arbeit"] / "entwurf.md").unlink()
    assert vf["lauf"]().returncode == 0
    assert stempel.exists()                                    # nichts Neues, Abruf gelungen


def test_veroeffentlichen_sperre_je_instanz(vf):
    """Zwei Instanzen auf einem Server stören sich nicht: die Sperre trägt den Namen der Instanz."""
    import fcntl
    with open(vf["tmp"] / "andere-veroeffentlichen.lock", "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        assert "Already running" not in vf["lauf"]().stdout
    with open(vf["tmp"] / "probe-veroeffentlichen.lock", "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        assert "Already running" in vf["lauf"]().stdout


def test_veroeffentlichen_freischalten_je_reise_ohne_links_im_protokoll(vf):
    """Nach dem Veröffentlichen wird jede Reise freigeschaltet (neue bekommen ihren Link); die Links stehen nie im
    Protokoll. Ausstehende Links neuer Reisen werden auch ohne neuen Stand zugestellt."""
    r = vf["lauf"]()
    assert r.returncode == 0
    assert (vf["tmp"] / "frei.log").read_text().split() == ["beispielreise", "zweitreise"]
    assert "geheim" not in r.stdout + r.stderr
    py = ausfuehrbar(vf["tmp"] / "python.sh", f'#!/bin/sh\necho "$@" >> {vf["tmp"]}/zustellen.log\n')
    (vf["tmp"] / "konnektor").mkdir(exist_ok=True)
    (vf["tmp"] / "konnektor/neue-reisen-ausstehend.jsonl").write_text('{"ordner": "neu"}\n')
    r = vf["lauf"](FR_PYTHON=str(py))
    assert r.returncode == 0, r.stdout + r.stderr
    assert f"{BETRIEB}/zustellen.py" in (vf["tmp"] / "zustellen.log").read_text()


def test_veroeffentlichen_nennt_erneuerte_bausteine_und_den_grund_eines_fehlschlags(vf):
    """„Baustein erneuert“ steht im Protokoll; schlägt freischalten.sh fehl, steht sein FEHLER-Grund darunter, Links nie."""
    frei = ausfuehrbar(vf["tmp"] / "freischalten2.sh",
                       '#!/bin/sh\necho "Seite: https://example.invalid/$1-geheim/"\n'
                       '[ "$1" = beispielreise ] && echo "Block renewed: $1"\n'
                       '[ "$1" = zweitreise ] && { echo "ERROR: no path in the block."; exit 1; }\nexit 0\n')
    r = vf["lauf"](VF_FREISCHALTEN=str(frei))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "Block renewed: beispielreise" in r.stdout
    assert "Warning: zweitreise not released" in r.stdout and "ERROR: no path in the block." in r.stdout
    assert "geheim" not in r.stdout + r.stderr


def test_veroeffentlichen_und_deploy_pruefen_in_eigenem_testordner():
    """pytest räumt in /tmp/pytest-of-<user> die Ordner älterer Läufe weg, auch die eines noch laufenden; die Prüfungen
    des Betriebs laufen deshalb in einem eigenen Ordner (--basetemp), der danach verschwindet."""
    for datei in ("veroeffentlichen.sh", "deploy.sh"):
        text = (BETRIEB / datei).read_text(encoding="utf-8")
        assert re.search(r'pytest .*--basetemp "\$pruef_tmp"', text), datei
        assert 'rm -rf "$pruef_tmp"' in text, datei


# ---------- Veröffentlichen: Tor, Rot-Datei und Alarm (#142) ----------

def test_veroeffentlichen_rote_reisetests_sperren_nicht(vf):
    """Die Tests des Reisen-Repos (tests/) prüfen Inhalt, nicht Software: rot sperrt nie, der Betrieb bekommt eine
    Nachricht (AC-1)."""
    vf["reisetests"]()
    (vf["tmp"] / "rot-reise").touch()
    r = vf["lauf"]()
    assert r.returncode == 0, r.stdout + r.stderr
    assert "tests of the trips repo red (they do not block)" in r.stdout
    assert vf["zeilen"]("pruefen.log") == ["p", "r"]
    assert vf["deploys"]() == ["beispielreise", "zweitreise"]
    assert vf["zeilen"]("frei.log") == ["beispielreise", "zweitreise"]
    assert (vf["tmp"] / "dienst/veroeffentlicht").read_text().strip() == vf["kopf"]()
    assert (vf["tmp"] / "dienst/veroeffentlichen-erfolg").exists() and vf["pings"]() == 1
    assert len([z for z in vf["zeilen"]("melden.log") if z.startswith("normal|")]) == 1
    assert vf["rot"]() is None


def test_veroeffentlichen_warnung_der_reisetests_einmal_je_commit(vf):
    """Die Nachricht über rote Tests des Reisen-Repos kommt je Commit einmal, auch bei --immer (AC-2)."""
    vf["reisetests"]()
    (vf["tmp"] / "rot-reise").touch()
    normal = lambda: [z for z in vf["zeilen"]("melden.log") if z.startswith("normal|")]   # noqa: E731
    assert vf["lauf"]().returncode == 0
    assert vf["lauf"]("--immer").returncode == 0
    assert len(normal()) == 1
    assert (vf["tmp"] / "dienst/veroeffentlichen-warnung").read_text().strip() == vf["kopf"]()
    vf["neuer_commit"]()
    assert vf["lauf"]().returncode == 0
    assert len(normal()) == 2


def test_deploy_prueft_nur_die_tests_der_software():
    """deploy.sh und das Tor prüfen mit pytest nur engine/tests; tests/ des Reisen-Repos läuft im Tor getrennt und sperrt
    nicht (AC-4)."""
    deploy = (BETRIEB / "deploy.sh").read_text(encoding="utf-8")
    pytest_zeilen = [z for z in deploy.splitlines() if "pytest" in z and not z.lstrip().startswith("#")]
    assert pytest_zeilen and all('"$WURZEL/engine/tests"' in z for z in pytest_zeilen)
    assert not any("$WURZEL/tests" in z for z in pytest_zeilen)
    assert 'if [ "${FR_GEPRUEFT:-}" != "$(git -C "$WURZEL" rev-parse HEAD)" ]; then' in deploy
    tor = (BETRIEB / "veroeffentlichen.sh").read_text(encoding="utf-8")
    assert not any("engine/tests" in z and "[ -d tests ]" in z for z in tor.splitlines())


def test_bau_mit_warnung_sperrt_nicht(tmp_path):
    """Eine Warnung im Plan (hier: Plan endet an einem anderen Tag als die Reise) sperrt den Bau nie: bauen.py endet mit 0
    und legt die Seite an (AC-5). Regressionsschutz: das galt schon vor #142."""
    reise = tmp_path / "reisen" / "beispielreise"
    shutil.copytree(BEISPIEL, reise)
    routen = reise / "plan" / "routen.yaml"
    text = routen.read_text(encoding="utf-8")
    assert "ende: {datum: 2027-05-16, ort: O-01}" in text
    routen.write_text(text.replace("ende: {datum: 2027-05-16, ort: O-01}", "ende: {datum: 2027-05-20, ort: O-01}"), encoding="utf-8")
    daten = bauen.Bauer(reise, tmp_path / "probe").daten()
    assert any("endet am" in w["text"] for w in daten["route"]["warnungen"])
    r = subprocess.run([sys.executable, str(ENGINE / "bauen.py"), "--reisen", str(tmp_path / "reisen"), "--ziel",
                        str(tmp_path / "dist"), "beispielreise"], capture_output=True, text=True, env=SAUBER)
    assert r.returncode == 0, r.stdout + r.stderr
    assert (tmp_path / "dist" / "beispielreise" / "index.html").exists()


def test_deploy_mit_warnung_im_plan_legt_die_seite_ab(tmp_path):
    """deploy.sh selbst (nicht nur bauen.py) endet bei einer Warnung im Plan mit 0 und legt die Seite im Zielordner
    FR_SEITEN ab (AC-5)."""
    wurzel = tmp_path / "instanz"
    reise = wurzel / "reisen" / "beispielreise"
    shutil.copytree(BEISPIEL, reise)
    routen = reise / "plan" / "routen.yaml"
    text = routen.read_text(encoding="utf-8")
    assert "ende: {datum: 2027-05-16, ort: O-01}" in text
    routen.write_text(text.replace("ende: {datum: 2027-05-16, ort: O-01}", "ende: {datum: 2027-05-20, ort: O-01}"), encoding="utf-8")
    (wurzel / "engine").symlink_to(ENGINE)
    (wurzel / ".gitignore").write_text("dist/\n__pycache__/\n")
    git(wurzel, "init", "-q", "-b", "main")
    git(wurzel, "add", ".")
    git(wurzel, "commit", "-qm", "start")
    (tmp_path / "seiten").mkdir()
    # Rückmeldedienst-Attrappe: antwortet auf …/gesund, damit die Bereitschaftsprüfung am Ende von deploy.sh besteht
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    class Gesund(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")

        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), Gesund)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    env = {**SAUBER, "FR_WURZEL": str(wurzel), "FR_INSTANZ": "probe", "FR_SEITEN": str(tmp_path / "seiten"),
           "FR_DIENST": str(tmp_path / "dienst"), "FR_PYTHON": sys.executable, "FR_GEPRUEFT": git(wurzel, "rev-parse", "HEAD").strip(),
           "FR_RM_PORT": str(server.server_address[1]), "FR_SUDO": "false"}
    try:
        r = subprocess.run([str(BETRIEB / "deploy.sh"), "beispielreise"], env=env, capture_output=True, text=True)
    finally:
        server.shutdown()
    assert r.returncode == 0, r.stdout + r.stderr
    assert (tmp_path / "seiten" / "beispielreise" / "index.html").exists()


def test_deploy_prueft_die_wege_zum_konnektor_von_aussen(tmp_path):
    """Nach dem Deploy fragt deploy.sh jede Art Pfad des Konnektors über die öffentliche Adresse ab. Kommt ein Weg bei
    nginx statt beim Konnektor an (kein Kopf X-Frieda), warnt es und meldet es dem Betreiber; die Seite wird trotzdem
    abgelegt. So lief das Kalender-Abo ins Leere: nginx kannte /kalender/ nicht (1.11.2026)."""
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    wurzel = tmp_path / "instanz"
    shutil.copytree(BEISPIEL, wurzel / "reisen" / "beispielreise")
    (wurzel / "engine").symlink_to(ENGINE)
    (wurzel / ".gitignore").write_text("dist/\n__pycache__/\n")
    git(wurzel, "init", "-q", "-b", "main")
    git(wurzel, "add", ".")
    git(wurzel, "commit", "-qm", "start")
    (tmp_path / "seiten").mkdir()
    fehlt = {"/kalender/"}

    class Dienste(BaseHTTPRequestHandler):
        """Rückmeldedienst, Konnektor und nginx davor in einem: X-Frieda nur, wo nginx zum Konnektor weiterleitet."""
        def do_GET(self):
            nginx_404 = any(self.path.startswith(f) for f in fehlt)
            self.send_response(404 if nginx_404 else 200)
            if not nginx_404:
                self.send_header("X-Frieda", "konnektor")
            self.send_header("Content-Length", "0")
            self.end_headers()
        do_HEAD = do_GET

        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), Dienste)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    port = str(server.server_address[1])
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    ausfuehrbar(bin_ / "systemctl", '#!/bin/sh\ncase "$*" in *konnektor*) exit 0;; esac\nexit 1\n')
    meldungen = tmp_path / "meldungen.log"
    melden = ausfuehrbar(tmp_path / "melden.sh", f'#!/bin/sh\necho "$1|$2|$3" >> {meldungen}\n')
    env = {**SAUBER, "PATH": f"{bin_}:{SAUBER.get('PATH', os.environ['PATH'])}", "FR_WURZEL": str(wurzel), "FR_INSTANZ": "probe",
           "FR_SEITEN": str(tmp_path / "seiten"), "FR_DIENST": str(tmp_path / "dienst"), "FR_KONNEKTOR": str(tmp_path / "kn"),
           "FR_KONTEN": str(tmp_path / "konten"), "FR_PYTHON": sys.executable, "FR_GEPRUEFT": git(wurzel, "rev-parse", "HEAD").strip(),
           "FR_RM_PORT": port, "FR_KN_PORT": port, "FR_KN_ADRESSE": f"http://127.0.0.1:{port}", "FR_SUDO": "false",
           "FR_MELDEN": str(melden)}
    try:
        r = subprocess.run([str(BETRIEB / "deploy.sh"), "beispielreise"], env=env, capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr
        assert "Warning: these paths do not reach the connector" in r.stdout and "/kalender/" in r.stdout and "/gesund" not in r.stdout.split("Warning")[1]
        assert "nginx: paths to the connector missing" in meldungen.read_text() and "/kalender/" in meldungen.read_text()
        assert (tmp_path / "seiten" / "beispielreise" / "index.html").exists()
        fehlt.clear()
        meldungen.unlink()
        r = subprocess.run([str(BETRIEB / "deploy.sh"), "beispielreise"], env=env, capture_output=True, text=True)
        assert r.returncode == 0 and "Warning: these paths" not in r.stdout and not meldungen.exists(), r.stdout + r.stderr
    finally:
        server.shutdown()


def test_veroeffentlichen_merge_und_submodulfehler_werden_nicht_gemerkt(vf):
    """Scheitert das Vorspulen (lokaler Commit im Bauordner) oder das Holen des Submoduls, endet der Lauf mit 1,
    es wird nichts gebaut, kein Stand geschrieben und die Rot-Datei weder angelegt noch verändert (AC-18)."""
    stand = vf["tmp"] / "dienst" / "veroeffentlicht"
    rot_datei = vf["tmp"] / "dienst" / "veroeffentlichen-rot"
    arbeit, quelle = vf["arbeit"], vf["tmp"] / "quelle"
    # Merge-Fehler: lokaler Commit im Bauordner, origin/main läuft davon
    git(arbeit, "config", "user.email", "test@example.invalid")
    git(arbeit, "config", "user.name", "Test")
    (arbeit / "lokal.txt").write_text("lokal")
    git(arbeit, "add", ".")
    git(arbeit, "commit", "-qm", "lokal")
    vf["neuer_commit"]()
    r = vf["lauf"]()
    assert r.returncode == 1 and "cannot be fast-forwarded" in r.stdout, r.stdout + r.stderr
    assert vf["deploys"]() == [] and not stand.exists() and vf["rot"]() is None
    # Submodul-Fehler: .gitmodules verweist auf ein Ziel, das es nicht gibt
    git(arbeit, "fetch", "-q", "origin", "main")
    git(arbeit, "reset", "-q", "--hard", "origin/main")
    (quelle / ".gitmodules").write_text('[submodule "frieda"]\n\tpath = frieda\n\turl = %s\n' % (vf["tmp"] / "fehlt.git"))
    git(quelle, "update-index", "--add", "--cacheinfo", "160000," + git(quelle, "rev-parse", "HEAD").strip() + ",frieda")
    git(quelle, "add", ".gitmodules")
    git(quelle, "commit", "-qm", "Submodul ohne Ziel")
    alt = "commit=" + "0" * 40 + "\nart=reise\nreisen=zweitreise\nseit=1\ngemeldet=0\n"
    rot_datei.parent.mkdir(exist_ok=True)
    rot_datei.write_text(alt, encoding="utf-8")
    r = vf["lauf"]()
    assert r.returncode == 1 and "submodule" in r.stdout, r.stdout + r.stderr
    assert vf["deploys"]() == [] and not stand.exists() and rot_datei.read_text(encoding="utf-8") == alt


def test_veroeffentlichen_eine_rote_reise_haelt_die_anderen_nicht_auf(vf):
    """Scheitert der Bau einer Reise (Exit 2), werden die anderen trotzdem veröffentlicht und freigeschaltet; der Lauf ist
    rot, der Stand bleibt ungemerkt, die Rot-Datei nennt die Reise (AC-6)."""
    (vf["tmp"] / "kaputt-beispielreise").touch()
    r = vf["lauf"](VF_JETZT=str(T0))
    assert r.returncode == 1
    assert vf["deploys"]() == ["beispielreise", "zweitreise"]
    assert vf["zeilen"]("frei.log") == ["zweitreise"]
    rot = vf["rot"]()
    assert rot["art"] == "reise" and rot["reisen"] == "beispielreise" and rot["commit"] == vf["kopf"]()
    assert rot["seit"] == iso(T0) and rot["gemeldet"] == "0"
    assert not (vf["tmp"] / "dienst/veroeffentlicht").exists()
    assert not (vf["tmp"] / "dienst/veroeffentlichen-erfolg").exists() and vf["pings"]() == 0


def test_deploy_exit_2_bei_baufehler_sonst_1(tmp_path):
    """deploy.sh endet mit 2, wenn der Bau der Reise scheitert (deterministisch, nur diese Reise), sonst bei Fehlern mit 1
    (AC-7)."""
    wurzel = tmp_path / "instanz"
    (wurzel / "reisen" / "kaputtreise").mkdir(parents=True)
    (wurzel / "engine").symlink_to(ENGINE)
    (wurzel / "reisen" / "kaputtreise" / "reise.json").write_text("{}")
    (wurzel / "reisen" / "kaputtreise" / "reise.yaml").write_text("titel: [kein gültiges YAML\n")
    (wurzel / ".gitignore").write_text("dist/\n")
    git(wurzel, "init", "-q", "-b", "main")
    git(wurzel, "add", ".")
    git(wurzel, "commit", "-qm", "start")
    (tmp_path / "seiten").mkdir()
    env = {**SAUBER, "FR_WURZEL": str(wurzel), "FR_INSTANZ": "probe", "FR_SEITEN": str(tmp_path / "seiten"),
           "FR_DIENST": str(tmp_path / "dienst"), "FR_PYTHON": sys.executable}
    r = subprocess.run([str(BETRIEB / "deploy.sh"), "kaputtreise"], env=env, capture_output=True, text=True)
    assert r.returncode == 2, r.stdout + r.stderr
    assert not (tmp_path / "seiten" / "kaputtreise").exists()
    r = subprocess.run([str(BETRIEB / "deploy.sh"), "kaputtreise"], env={**env, "FR_SEITEN": str(tmp_path / "fehlt")},
                       capture_output=True, text=True)
    assert r.returncode == 1, r.stdout + r.stderr
    r = subprocess.run([str(BETRIEB / "deploy.sh"), "gibtsnicht"], env=env, capture_output=True, text=True)
    assert r.returncode == 1, r.stdout + r.stderr


def test_veroeffentlichen_infrastrukturfehler_wird_nicht_gemerkt_und_wiederholt(vf):
    """Ein Infrastrukturfehler (Exit 1) bei der ersten Reise beendet die Schleife; die zweite Reise wird nicht angefasst,
    die Rot-Datei weder angelegt noch verändert (AC-8)."""
    (vf["tmp"] / "infra-beispielreise").touch()
    assert vf["lauf"]().returncode == 1
    assert vf["deploys"]() == ["beispielreise"]
    assert vf["rot"]() is None and vf["zeilen"]("frei.log") == []
    rot_datei = vf["tmp"] / "dienst" / "veroeffentlichen-rot"
    alt = f"commit={'0' * 40}\nart=reise\nreisen=zweitreise\nseit={iso(T0)}\ngemeldet=0\n"
    rot_datei.write_text(alt, encoding="utf-8")
    assert vf["lauf"](VF_JETZT=str(T0 + 60)).returncode == 1
    assert vf["deploys"]() == ["beispielreise"]
    assert rot_datei.read_text(encoding="utf-8") == alt


def test_veroeffentlichen_roter_stand_wird_nicht_erneut_geprueft(vf):
    """Ein Stand mit gescheitertem Bau wird beim nächsten Lauf ohne --immer nicht noch einmal geprüft und gebaut (AC-15)."""
    (vf["tmp"] / "kaputt-beispielreise").touch()
    assert vf["lauf"]().returncode == 1
    assert vf["deploys"]() == ["beispielreise", "zweitreise"]
    assert vf["zeilen"]("pruefen.log") == ["p"]
    r = vf["lauf"]()
    assert r.returncode == 0 and "Known red state" in r.stdout
    assert vf["deploys"]() == [] and vf["zeilen"]("pruefen.log") == ["p"]


def test_veroeffentlichen_ueberspringen_ohne_stempel_und_heartbeat(vf):
    """Das Überspringen eines bekannten roten Stands ist kein fachlicher Erfolg: kein Stempel, kein Heartbeat (AC-16)."""
    stempel = vf["tmp"] / "dienst" / "veroeffentlichen-erfolg"
    (vf["tmp"] / "kaputt-beispielreise").touch()
    assert vf["lauf"]().returncode == 1
    assert vf["lauf"]().returncode == 0
    assert not stempel.exists() and vf["pings"]() == 0
    (vf["tmp"] / "kaputt-beispielreise").unlink()
    (vf["tmp"] / "rot").touch()
    vf["neuer_commit"]()
    assert vf["lauf"]().returncode == 1                        # Software rot
    assert vf["lauf"]().returncode == 0
    assert not stempel.exists() and vf["pings"]() == 0


def test_veroeffentlichen_gruen_raeumt_die_rot_datei_auf(vf):
    """Nach einem roten Stand prüfen --immer und ein neuer Commit wieder; ist alles grün, verschwindet die Rot-Datei und
    der Stand wird gemerkt (AC-17)."""
    (vf["tmp"] / "kaputt-beispielreise").touch()
    assert vf["lauf"]().returncode == 1 and vf["rot"]() is not None
    (vf["tmp"] / "kaputt-beispielreise").unlink()
    vf["deploys"]()
    assert vf["lauf"]("--immer").returncode == 0
    assert vf["deploys"]() == ["beispielreise", "zweitreise"]
    assert vf["rot"]() is None and vf["pings"]() == 1
    assert (vf["tmp"] / "dienst/veroeffentlicht").read_text().strip() == vf["kopf"]()
    (vf["tmp"] / "kaputt-zweitreise").touch()
    vf["neuer_commit"]()
    assert vf["lauf"]().returncode == 1 and vf["rot"]()["reisen"] == "zweitreise"
    (vf["tmp"] / "kaputt-zweitreise").unlink()
    vf["neuer_commit"]()
    vf["deploys"]()
    assert vf["lauf"]().returncode == 0
    assert vf["deploys"]() == ["beispielreise", "zweitreise"] and vf["rot"]() is None


def test_veroeffentlichen_kein_alarm_vor_der_schwelle(vf):
    """Vor 30 Minuten Rot geht kein Alarm hinaus (AC-20)."""
    (vf["tmp"] / "kaputt-beispielreise").touch()
    assert vf["lauf"](VF_JETZT=str(T0)).returncode == 1
    assert vf["lauf"](VF_JETZT=str(T0 + 29 * 60)).returncode == 0
    assert hoch(vf) == [] and vf["zeilen"]("rotmelden.log") == []
    assert vf["rot"]()["gemeldet"] == "0"


def test_veroeffentlichen_alarm_genau_einmal(vf):
    """Ab 30 Minuten Rot geht genau ein Alarm an den Betrieb, auch beim Überspringen; weitere Läufe und neue rote Commits
    derselben Rot-Phase alarmieren nicht erneut (AC-21)."""
    (vf["tmp"] / "kaputt-beispielreise").touch()
    assert vf["lauf"](VF_JETZT=str(T0)).returncode == 1
    r = vf["lauf"](VF_JETZT=str(T0 + 30 * 60))
    assert r.returncode == 0 and "Known red state" in r.stdout
    assert len(hoch(vf)) == 1 and "red" in hoch(vf)[0]
    assert vf["rot"]()["gemeldet"] == "1"
    assert vf["lauf"](VF_JETZT=str(T0 + 60 * 60)).returncode == 0
    vf["neuer_commit"]()
    assert vf["lauf"](VF_JETZT=str(T0 + 70 * 60)).returncode == 1
    assert len(hoch(vf)) == 1
    assert vf["rot"]()["seit"] == iso(T0)


def test_veroeffentlichen_alarm_art_software_nur_an_den_betrieb(vf):
    """Bei einer roten Reise gehen Meldungen an deren Organisator:innen (waechter.py rot-melden), bei roter Software nur
    der Alarm an den Betrieb (AC-22)."""
    (vf["tmp"] / "kaputt-beispielreise").touch()
    assert vf["lauf"](VF_JETZT=str(T0)).returncode == 1
    assert vf["lauf"](VF_JETZT=str(T0 + 31 * 60)).returncode == 0
    aufrufe = vf["zeilen"]("rotmelden.log")
    assert aufrufe and all(a.split() == ["--reisen", "beispielreise", "--seit", iso(T0)] for a in aufrufe)
    # grün: neue Rot-Phase mit roter Software
    (vf["tmp"] / "kaputt-beispielreise").unlink()
    assert vf["lauf"]("--immer", VF_JETZT=str(T0 + 40 * 60)).returncode == 0 and vf["rot"]() is None
    (vf["tmp"] / "rot").touch()
    vf["neuer_commit"]()
    t1 = T0 + 50 * 60
    assert vf["lauf"](VF_JETZT=str(t1)).returncode == 1
    assert vf["rot"]()["seit"] == iso(t1) and vf["rot"]()["art"] == "software"
    assert vf["lauf"](VF_JETZT=str(t1 + 31 * 60)).returncode == 0
    assert len(hoch(vf)) == 2                                  # je Rot-Phase ein Alarm
    assert vf["zeilen"]("rotmelden.log") == aufrufe            # keine Meldung an Personen


def test_veroeffentlichen_alarm_wiederholt_bei_ausfall_des_meldewegs(vf):
    """Kommt der Alarm nicht an (FR_MELDEN scheitert), bleibt gemeldet=0 und der nächste Lauf versucht es wieder (AC-24)."""
    (vf["tmp"] / "kaputt-beispielreise").touch()
    (vf["tmp"] / "melden-aus").touch()
    assert vf["lauf"](VF_JETZT=str(T0)).returncode == 1
    assert vf["lauf"](VF_JETZT=str(T0 + 31 * 60)).returncode == 0
    assert len(hoch(vf)) == 1 and vf["rot"]()["gemeldet"] == "0"
    (vf["tmp"] / "melden-aus").unlink()
    assert vf["lauf"](VF_JETZT=str(T0 + 36 * 60)).returncode == 0
    assert len(hoch(vf)) == 2 and vf["rot"]()["gemeldet"] == "1"


def test_veroeffentlichen_schwelle_ist_einstellbar(vf):
    """Die Schwelle kommt aus FR_ROT_MELDEN_NACH_MINUTEN (Vorgabe 30, erklärt in einstellungen.beispiel) (AC-25)."""
    (vf["tmp"] / "kaputt-beispielreise").touch()
    assert vf["lauf"](VF_JETZT=str(T0), FR_ROT_MELDEN_NACH_MINUTEN="10").returncode == 1
    assert vf["lauf"](VF_JETZT=str(T0 + 9 * 60), FR_ROT_MELDEN_NACH_MINUTEN="10").returncode == 0
    assert hoch(vf) == []
    assert vf["lauf"](VF_JETZT=str(T0 + 11 * 60), FR_ROT_MELDEN_NACH_MINUTEN="10").returncode == 0
    assert len(hoch(vf)) == 1
    beispiel = (BETRIEB / "einstellungen.beispiel").read_text(encoding="utf-8")
    assert re.search(r"^#?FR_ROT_MELDEN_NACH_MINUTEN=30\s*$", beispiel, re.M)


def test_veroeffentlichen_seit_bleibt_ueber_neue_rote_commits(vf):
    """Ein neuer roter Commit in derselben Rot-Phase ersetzt commit, art und reisen; seit und gemeldet bleiben (AC-26)."""
    (vf["tmp"] / "kaputt-beispielreise").touch()
    assert vf["lauf"](VF_JETZT=str(T0)).returncode == 1
    erster = vf["kopf"]()
    (vf["tmp"] / "kaputt-beispielreise").unlink()
    (vf["tmp"] / "kaputt-zweitreise").touch()
    vf["neuer_commit"]()
    assert vf["lauf"](VF_JETZT=str(T0 + 5 * 60)).returncode == 1
    rot = vf["rot"]()
    assert rot["commit"] == vf["kopf"]() != erster and rot["reisen"] == "zweitreise"
    assert rot["seit"] == iso(T0) and rot["gemeldet"] == "0"
    assert vf["lauf"](VF_JETZT=str(T0 + 31 * 60)).returncode == 0 and vf["rot"]()["gemeldet"] == "1"
    vf["neuer_commit"]()
    assert vf["lauf"](VF_JETZT=str(T0 + 40 * 60)).returncode == 1
    rot = vf["rot"]()
    assert rot["commit"] == vf["kopf"]() and rot["seit"] == iso(T0) and rot["gemeldet"] == "1"


def test_betrieb_md_nennt_rot_datei_alarm_und_konvention():
    """docs/betrieb.md beschreibt Tor, Exit-Codes, Rot-Datei, Überspringen, Alarm mit Schwelle und die Konvention für die
    Tests des Reisen-Repos (AC-33)."""
    text = (WURZEL / "docs" / "betrieb.md").read_text(encoding="utf-8")
    for teil in ("veroeffentlichen-rot", "FR_ROT_MELDEN_NACH_MINUTEN", "Exit 2", "Known red state",
                 "rot-melden", "sperren nicht"):
        assert teil in text, teil


# ---------- Deploy ----------

def _deploy_liste(name):
    deploy = (BETRIEB / "deploy.sh").read_text(encoding="utf-8")
    liste = re.search(rf'^{name}="([^"]*)"', deploy, re.M).group(1).split()
    sprachen = sorted(p.name for p in ENGINE.glob("texte_??.py")) + sorted(p.name for p in ENGINE.glob("texte_???.py"))
    return {m for x in liste for m in (sprachen if x == "$SPRACHDATEIEN" else [x])}   # die Sprachdateien nimmt deploy.sh per ls mit


def _eigene_importe(datei):
    return {f"{n}.py" for n in re.findall(r"^\s*(?:from|import)\s+(\w+)", (ENGINE / datei).read_text(encoding="utf-8"), re.M)
            if (ENGINE / f"{n}.py").exists()}


def test_deploy_kopiert_alle_module_der_dienste():
    """Rückmeldedienst und Konnektor laufen aus <FR_DIENST>; jedes eigene Modul, das sie (auch mittelbar) importieren,
    muss deploy.sh dorthin kopieren. Ein fehlendes Modul ließ den Konnektor einmal nicht starten."""
    kopiert = _deploy_liste("RM_MODULE") | _deploy_liste("KN_MODULE")
    offen, gesehen = ["konnektor.py", "rueckmeldungen.py"], set()
    while offen:
        datei = offen.pop()
        gesehen.add(datei)
        assert datei in kopiert, f"deploy.sh kopiert {datei} nicht"
        offen += [m for m in _eigene_importe(datei) if m not in gesehen]


def test_deploy_startet_dienste_bei_geaenderten_modulen_neu():
    """Ändert sich ein Modul, das der Rückmeldedienst lädt, startet er neu; der Konnektor lädt alles, was der
    Rückmeldedienst lädt, und startet dann auch neu."""
    def huelle(datei):
        offen, gesehen = [datei], set()
        while offen:
            d = offen.pop()
            gesehen.add(d)
            offen += [m for m in _eigene_importe(d) if m not in gesehen]
        return gesehen
    assert huelle("rueckmeldungen.py") <= _deploy_liste("RM_MODULE")
    assert huelle("konnektor.py") <= _deploy_liste("KN_MODULE") | _deploy_liste("RM_MODULE")
    deploy = (BETRIEB / "deploy.sh").read_text(encoding="utf-8")
    assert '[ -n "$NEU_RM$NEU_KN" ] && neustart "$FR_INSTANZ-konnektor"' in deploy


def test_deploy_kopiert_module_des_schreibwegs():
    """Der Schreibweg (schreiben.py dienst) läuft aus <FR_DIENST> und lädt beim Start nur seine eigenen Module; den
    Schreibvorgang führt er mit dem Code der Arbeitskopie aus (dort liegt die ganze Engine). Deshalb zählen hier nur die
    Importe auf oberster Ebene; die Importe in den Funktionen (bauen, routen, reise) gehören zur Arbeitskopie."""
    kopiert = _deploy_liste("SB_MODULE")
    oben = {f"{n}.py" for n in re.findall(r"^(?:from|import)\s+(\w+)", (ENGINE / "schreiben.py").read_text(encoding="utf-8"), re.M)
            if (ENGINE / f"{n}.py").exists()}
    offen, gesehen = ["schreiben.py"], set()
    while offen:
        datei = offen.pop()
        gesehen.add(datei)
        assert datei in kopiert, f"deploy.sh kopiert {datei} nicht (SB_MODULE)"
        offen += [m for m in (oben if datei == "schreiben.py" else _eigene_importe(datei)) if m not in gesehen]
    deploy = (BETRIEB / "deploy.sh").read_text(encoding="utf-8")
    assert 'neustart "$FR_INSTANZ-schreiben"' in deploy and 'is-enabled --quiet "$FR_INSTANZ-schreiben"' in deploy


def test_deploy_kopiert_friedas_symbol():
    deploy = (BETRIEB / "deploy.sh").read_text(encoding="utf-8")
    assert '"$WURZEL/engine/marke/" "$DIENST/marke/"' in deploy


# ---------- Nur aus dem Bauordner (#137) ----------

@pytest.fixture
def instanz(tmp_path):
    """Reisen-Repo auf main, das die Software (Kopie von betrieb/) als Submodul frieda/ einbindet, mit der Beispielreise.
    So findet gemeinsam.sh die Wurzel auch ohne FR_WURZEL, wie bei einem Aufruf von Hand in einem Arbeitsordner."""
    wurzel = tmp_path / "instanz"
    shutil.copytree(BEISPIEL, wurzel / "reisen" / "beispielreise")
    shutil.copytree(BETRIEB, wurzel / "frieda" / "betrieb", ignore=shutil.ignore_patterns("__pycache__"))
    git(wurzel / "frieda", "init", "-q", "-b", "main")
    git(wurzel / "frieda", "add", ".")
    git(wurzel / "frieda", "commit", "-qm", "software")
    (wurzel / "engine").symlink_to(ENGINE)
    (wurzel / ".gitignore").write_text("dist/\n__pycache__/\n")
    git(wurzel, "init", "-q", "-b", "main")
    git(wurzel, "add", ".")
    git(wurzel, "commit", "-qm", "start")
    assert git(wurzel / "frieda", "rev-parse", "--show-superproject-working-tree").strip() == str(wurzel)
    (tmp_path / "seiten").mkdir()
    # FR_GEPRUEFT: deploy.sh soll hier nicht die ganzen Tests der Software noch einmal laufen lassen
    env = {**SAUBER, "FR_INSTANZ": "probe", "FR_SEITEN": str(tmp_path / "seiten"), "FR_DIENST": str(tmp_path / "dienst"),
           "FR_SPERREN": str(tmp_path), "FR_PYTHON": sys.executable, "FR_SUDO": "false", "FR_RM_PORT": "9",
           "FR_GEPRUEFT": git(wurzel, "rev-parse", "HEAD").strip(),
           "VF_DEPLOY": str(ausfuehrbar(tmp_path / "deploy.sh", f'#!/bin/sh\necho "$1" >> {tmp_path}/deploy.log\n'))}
    return {"wurzel": wurzel, "tmp": tmp_path, "env": env,
            "deploy": wurzel / "frieda" / "betrieb" / "deploy.sh",
            "veroeffentlichen": wurzel / "frieda" / "betrieb" / "veroeffentlichen.sh"}


def test_deploy_ohne_fr_wurzel_verweigert(instanz):
    """AC-1: Ohne FR_WURZEL baut deploy.sh nicht aus dem Ordner, in dem es zufällig liegt."""
    r = subprocess.run([str(instanz["deploy"]), "beispielreise"], env=instanz["env"], capture_output=True, text=True)
    assert r.returncode == 1 and "FR_WURZEL" in r.stderr, r.stdout + r.stderr
    assert not (instanz["tmp"] / "seiten" / "beispielreise").exists()
    assert not (instanz["wurzel"] / "dist").exists()


def test_veroeffentlichen_ohne_fr_wurzel_verweigert(instanz):
    """AC-2: Ohne FR_WURZEL veröffentlicht veroeffentlichen.sh nichts und merkt sich nichts."""
    r = subprocess.run([str(instanz["veroeffentlichen"]), "--immer"], env=instanz["env"], capture_output=True, text=True)
    assert r.returncode == 1 and "FR_WURZEL" in r.stderr, r.stdout + r.stderr
    assert not (instanz["tmp"] / "deploy.log").exists()
    assert not (instanz["tmp"] / "dienst" / "veroeffentlicht").exists()
    assert not (instanz["tmp"] / "dienst" / "veroeffentlichen-erfolg").exists()


@pytest.mark.parametrize("wechsel", [("checkout", "-qb", "baustelle"), ("checkout", "-q", "--detach")])
def test_deploy_nur_auf_main(instanz, wechsel):
    """AC-3: Steht der Ordner nicht auf main (anderer Branch oder losgelöster HEAD), baut deploy.sh nicht."""
    git(instanz["wurzel"], *wechsel)
    r = subprocess.run([str(instanz["deploy"]), "beispielreise"], env={**instanz["env"], "FR_WURZEL": str(instanz["wurzel"])},
                       capture_output=True, text=True)
    assert r.returncode == 1 and "main" in r.stderr, r.stdout + r.stderr
    assert not (instanz["tmp"] / "seiten" / "beispielreise").exists()
    assert not (instanz["wurzel"] / "dist").exists()


def _texte_ohne_geschichte():
    """Doku, Skripte und Code, ohne die Protokolle früherer Vorhaben (docs/artifacts, docs/specs, docs/context)."""
    for ordner in ("docs", "betrieb", "werkzeuge", "engine"):
        for pfad in (WURZEL / ordner).rglob("*"):
            teile = pfad.relative_to(WURZEL).parts
            if not pfad.is_file() or pfad.suffix not in {".md", ".sh", ".py", ".yml", ".service", ".timer", ".conf", ".beispiel"}:
                continue
            if teile[:2] in {("docs", "artifacts"), ("docs", "specs"), ("docs", "context")} or ".venv" in teile \
                    or teile[:2] == ("engine", "vendor") or pfad.name == "test_betrieb.py":
                continue
            yield pfad, pfad.read_text(encoding="utf-8")


def test_arbeitskopie_sh_entfaellt():
    """AC-5: Arbeitskopien gibt es nicht mehr; gearbeitet wird in einem eigenen Arbeitsordner."""
    assert not (BETRIEB / "arbeitskopie.sh").exists()
    for pfad, text in _texte_ohne_geschichte():
        assert "arbeitskopie.sh" not in text, pfad


def test_handaufrufe_nennen_den_bauordner():
    """AC-6: Jede dokumentierte Handzeile, die deploy.sh oder veroeffentlichen.sh aufruft, setzt FR_WURZEL."""
    aufruf = re.compile(r"(?:frieda/)?betrieb/(?:deploy|veroeffentlichen)\.sh(?: --immer| <[^>]+>| \$\w+)")
    quellen = [*(WURZEL / "docs").glob("*.md"), BETRIEB / "einrichten.sh", WURZEL / "werkzeuge" / "karte-holen.sh"]
    gefunden = 0
    for pfad in quellen:
        for zeile in pfad.read_text(encoding="utf-8").splitlines():
            for m in aufruf.finditer(zeile):
                gefunden += 1
                davor = zeile[:m.start()]
                assert re.search(r"FR_WURZEL=\S*\s*$", davor), f"{pfad.name}: {zeile.strip()}"
    assert gefunden >= 4


def test_betrieb_md_bauordner_und_zurueckrollen():
    """AC-7: Bauordner und Arbeitsordner in der Tabelle der Instanz, Zurückrollen per git revert auf main."""
    text = (WURZEL / "docs" / "betrieb.md").read_text(encoding="utf-8")
    assert "| Bauordner |" in text and "| Arbeitsordner |" in text
    assert "Veröffentlichungsordner" not in text
    zurueck = text.split("## Zurückrollen", 1)[1].split("\n## ", 1)[0]
    assert "git revert" in zurueck and "git checkout" not in zurueck


# ---------- Freischalten ----------

@pytest.fixture
def fs(tmp_path):
    seiten = tmp_path / "seiten"
    bauen.bauen(BEISPIEL, seiten / "beispielreise")
    snippets = tmp_path / "snippets"
    snippets.mkdir()
    abrufe = tmp_path / "abrufe.log"
    code = tmp_path / "code"
    code.write_text("200")
    abruf = ausfuehrbar(tmp_path / "abruf.sh", f'#!/bin/sh\necho "$1" >> {abrufe}\ncat {code}\n')
    nginx = ausfuehrbar(tmp_path / "nginx.sh",
                        f'#!/bin/sh\necho "$@" >> {tmp_path}/nginx.log\n[ -e {tmp_path}/nginx-kaputt ] && exit 1\nexit 0\n')
    # Ein Reisen-Repo mit der Reise „beispielreise“: freischalten.sh prüft nur, dass es den Ordner gibt
    repo = tmp_path / "repo"
    (repo / "reisen/beispielreise").mkdir(parents=True)
    (repo / "reisen/beispielreise/reise.yaml").write_text("titel: x\n")
    (repo / "engine").symlink_to(ENGINE)
    env = {**SAUBER, "FR_WURZEL": str(repo), "FR_INSTANZ": "probe", "FR_SEITEN": str(seiten),
           "FR_ABLAGE": str(tmp_path / "ablage"), "FR_KONNEKTOR": str(tmp_path / "konnektor"), "FR_RM_PORT": "8871",
           "FR_ADRESSE": "https://example.invalid", "FR_KN_ADRESSE": "https://example.invalid/mcp",
           "FR_NGINX_SNIPPETS": str(snippets), "FR_SUDO": "",
           "FS_NGINX_TEST": f"{nginx} -t", "FS_NGINX_LADEN": f"{nginx} reload", "FS_ABRUF": str(abruf),
           "FS_WARTEN": "0"}

    def lauf(*args):
        return subprocess.run([str(BETRIEB / "freischalten.sh"), *args], env=env, capture_output=True, text=True)

    return {"lauf": lauf, "tmp": tmp_path, "snippets": snippets, "abrufe": abrufe, "code": code, "env": env,
            "repo": repo, "seiten": seiten}


def test_freischalten_neue_reise_bekommt_link_einmal(fs):
    r = fs["lauf"]("beispielreise")
    assert r.returncode == 0, r.stdout + r.stderr
    sn = fs["snippets"] / "probe-beispielreise.conf"
    inhalt = sn.read_text()
    pfad = inhalt.split("location ^~ /", 1)[1].split("/", 1)[0]
    assert pfad.startswith("beispielreise-") and len(pfad.split("-")[-1]) == 24 and not re.search(r"__[A-Z_]+__", inhalt)
    assert f"alias {fs['seiten']}/beispielreise/;" in inhalt and "proxy_pass http://127.0.0.1:8871/beispielreise/;" in inhalt
    assert "limit_req zone=probe_api " in inhalt
    assert stat.S_IMODE(sn.stat().st_mode) == 0o640
    assert "Released: beispielreise" in r.stdout and f"Seite: https://example.invalid/{pfad}/" in r.stdout
    assert fs["abrufe"].read_text().split() == [f"https://example.invalid/{pfad}/", f"https://example.invalid/{pfad}/api/gesund"]
    assert (fs["tmp"] / "nginx.log").read_text().split("\n")[:2] == ["-t", "reload"]
    links = fs["tmp"] / "konnektor/seiten.json"
    assert json.loads(links.read_text()) == {"beispielreise": f"https://example.invalid/{pfad}/"}
    assert stat.S_IMODE(links.stat().st_mode) == 0o600
    # zweiter Aufruf: derselbe Link, kein neues Laden von nginx
    r = fs["lauf"]("beispielreise")
    assert r.returncode == 0 and "Released" not in r.stdout and sn.read_text() == inhalt
    assert (fs["tmp"] / "nginx.log").read_text().count("reload") == 1


def test_freischalten_wartet_auf_das_neuladen_von_nginx(fs):
    """Gleich nach dem Neuladen kennt nginx den neuen Pfad noch nicht (404); ein neuer Link wird mehrmals versucht."""
    zaehler = fs["tmp"] / "zaehler"
    fs["env"]["FS_ABRUF"] = str(ausfuehrbar(fs["tmp"] / "abruf-langsam.sh",
        f'#!/bin/sh\necho x >> {zaehler}\n[ $(wc -l < {zaehler}) -le 2 ] && echo 404 || echo 200\n'))
    r = fs["lauf"]("beispielreise")
    assert r.returncode == 0 and "Released: beispielreise" in r.stdout, r.stdout
    assert len(zaehler.read_text().split()) == 4        # zweimal 404, dann Seite und Rückmeldedienst
    # Bestehender Link: kein Warten, ein Fehler ist sofort ein Fehler
    zaehler.unlink()
    fs["env"]["FS_ABRUF"] = str(ausfuehrbar(fs["tmp"] / "abruf-404.sh", f'#!/bin/sh\necho x >> {zaehler}\necho 404\n'))
    assert fs["lauf"]("beispielreise").returncode == 1 and len(zaehler.read_text().split()) == 1


def test_freischalten_link_fuer_die_claude_app(fs):
    r = fs["lauf"]("beispielreise", "--person", "ida")
    assert r.returncode == 0, r.stdout + r.stderr
    app = next(z for z in r.stdout.splitlines() if z.startswith("Claude-App: ")).split(": ", 1)[1]
    token = app.rsplit("/", 1)[1]
    assert app.startswith("https://example.invalid/mcp/")
    assert json.loads((fs["tmp"] / "konnektor/zugaenge.json").read_text())[token]["person"] == "ida"
    assert fs["lauf"]("beispielreise", "--person", "niemand").returncode != 0


def test_freischalten_nginx_lehnt_ab_alles_zurueck(fs):
    (fs["tmp"] / "nginx-kaputt").touch()
    r = fs["lauf"]("beispielreise")
    assert r.returncode == 1 and "nginx rejects the configuration" in r.stdout
    assert not list(fs["snippets"].iterdir()) and "reload" not in (fs["tmp"] / "nginx.log").read_text()


def test_freischalten_seite_nicht_erreichbar_ist_fehler_ohne_link_im_protokoll(fs):
    fs["code"].write_text("404")
    r = fs["lauf"]("beispielreise")
    assert r.returncode == 1 and "page of beispielreise answers with 404" in r.stdout and "include missing" in r.stdout
    token = (fs["snippets"] / "probe-beispielreise.conf").read_text().split("beispielreise-", 1)[1][:24]
    assert token not in r.stdout + r.stderr


def test_freischalten_unbekannte_reise_und_fehlende_adresse(fs):
    assert "does not exist" in fs["lauf"]("gibts-nicht").stdout
    assert "lowercase letters" in fs["lauf"]("Böse;rm").stdout
    r = subprocess.run([str(BETRIEB / "freischalten.sh"), "beispielreise"], capture_output=True, text=True,
                       env={**fs["env"], "FR_ADRESSE": "", "FR_KN_ADRESSE": ""})
    assert r.returncode == 1 and "FR_ADRESSE is not set" in r.stdout


def _zustellen_umgebung(fs, monkeypatch):
    for k in ("FR_WURZEL", "FR_INSTANZ", "FR_SEITEN", "FR_KONNEKTOR", "FR_ADRESSE", "FR_KN_ADRESSE", "FR_NGINX_SNIPPETS",
              "FR_SUDO", "FR_RM_PORT", "FS_NGINX_TEST", "FS_NGINX_LADEN", "FS_ABRUF", "FS_WARTEN"):
        monkeypatch.setenv(k, fs["env"][k])
    monkeypatch.setenv("RM_ABLAGE", fs["env"]["FR_ABLAGE"])
    monkeypatch.setenv("KN_SEITEN", str(fs["seiten"]))
    monkeypatch.setenv("KN_ZUGAENGE", str(fs["tmp"] / "konnektor/zugaenge.json"))
    monkeypatch.setenv("KN_BASIS", "https://example.invalid/mcp")


def test_ausstehende_links_zustellen(fs, monkeypatch, capsys):
    """Links einer neuen Reise gehen an die Person, sobald ihre Seite veröffentlicht ist; Unveröffentlichtes wartet."""
    _zustellen_umgebung(fs, monkeypatch)
    datei = fs["tmp"] / "ausstehend.jsonl"
    datei.write_text(json.dumps({"ordner": "beispielreise", "aid": "A-1", "name": "Ida", "person": "ida"}) + "\n"
                     + json.dumps({"ordner": "spaeter", "aid": "A-2", "name": "Ida", "person": "ida"}) + "\n")
    assert zustellen.ausstehend(fs["repo"], datei) == 0
    out = capsys.readouterr().out
    assert "Delivered: beispielreise to Ida" in out and "https://" not in out      # Links nie ins Protokoll
    assert [json.loads(z)["ordner"] for z in datei.read_text().splitlines()] == ["spaeter"]
    m = rm.meldungen(rm.ordner_neu(), "Ida")[0]
    assert m["art"] == "neue_reise" and m["auftraege"] == ["A-1"]
    assert "„Beispielreise – Malerweg in vier Tagen“ ist angelegt" in m["text"]
    assert "Seite: https://example.invalid/beispielreise-" in m["text"] and "https://example.invalid/mcp/" in m["text"]
    # Freischalten scheitert: Eintrag bleibt, Fehlerzeile ohne Links
    (fs["seiten"] / "spaeter").mkdir()
    (fs["seiten"] / "spaeter" / "daten.json").write_text("{}")
    assert zustellen.ausstehend(fs["repo"], datei) == 1
    out = capsys.readouterr().out
    assert "ERROR: spaeter not released" in out and "https://" not in out
    assert len(datei.read_text().splitlines()) == 1


def test_neue_reise_aus_dem_konnektor_frieda(fs, monkeypatch, capsys):
    """Auftrag mit konto_id: kein App-Link; das Konto wird mit der Reise verknüpft, Personen mit Adresse bekommen die
    Einladung per Mail. Adressen stehen nie im Protokoll oder in der Zustelldatei."""
    import konten
    _zustellen_umgebung(fs, monkeypatch)
    monkeypatch.setenv("FR_MAIL_DATEI", str(fs["tmp"] / "mails.jsonl"))
    monkeypatch.setenv("FR_BASIS", "https://frieda.example.invalid")
    konten.code_anfordern("ida@example.invalid")
    code = json.loads((fs["tmp"] / "mails.jsonl").read_text().splitlines()[-1])["text"].split(": ", 1)[1][:7]
    _, ida = konten.anmelden("ida@example.invalid", code, name="Ida")
    o = rm.ordner_neu(anlegen=True)
    (o / "auftraege.jsonl").write_text(json.dumps({
        "id": "A-1", "erstellt": "2026-10-27T10:00:00+00:00", "name": "Ida", "konto": "ida", "konto_id": ida["id"],
        "art": "Auftrag", "ziel": "allgemein", "text": "Neue Reise", "quelle": "Claude-App",
        "daten": {"neue_reise": {"titel": "x"}},
        "einladen": [{"schluessel": "karl", "email": "karl@example.invalid", "rolle": "mitwirkend", "name": "Karl"}]}) + "\n")
    datei = fs["tmp"] / "ausstehend.jsonl"
    datei.write_text(json.dumps({"ordner": "beispielreise", "aid": "A-1", "name": "Ida", "person": "ida"}) + "\n")
    assert zustellen.ausstehend(fs["repo"], datei) == 0
    out = capsys.readouterr().out
    assert "Delivered: beispielreise to Ida" in out and "@" not in out
    assert datei.read_text() == ""
    assert konten.mitglied(ida["id"], "beispielreise") == "ida"
    einl = [json.loads(z) for z in (fs["tmp"] / "mails.jsonl").read_text().splitlines() if "karl@" in z]
    assert len(einl) == 1 and "Ida hat dich zur Reise" in einl[0]["text"]
    m = rm.meldungen(rm.ordner_neu(), "Ida")[-1]
    assert "steht in meine_reisen" in m["text"] and "Einladung per Mail an 1 Person" in m["text"]
    assert "https://example.invalid/mcp/" not in m["text"]                  # kein App-Link


# ---------- Wächter-Lauf ----------

@pytest.fixture
def wa(tmp_path):
    """Attrappe für Python (schreibt den Bericht, wenn WA_BERICHT gesetzt ist) und für den Meldeweg."""
    ausfuehrbar(tmp_path / "python", '''#!/bin/sh
# Aufruf: python engine/waechter.py lauf --bericht DATEI
[ -z "$WA_FEHLER" ] || exit 3
[ -z "$WA_BERICHT" ] || printf '%s\\n' "$WA_BERICHT" > "$4"
exit 0
''')
    ausfuehrbar(tmp_path / "melden.sh", f'#!/bin/sh\nprintf "%s|%s|%s|%s\\n" "$1" "$2" "$3" "$4" >> {tmp_path}/nachrichten\n')
    (tmp_path / "quelle").mkdir()

    def lauf(**umgebung):
        env = {**SAUBER, "FR_WURZEL": str(tmp_path / "quelle"), "FR_PYTHON": str(tmp_path / "python"),
               "FR_DIENST": str(tmp_path / "dienst"), "FR_MELDEN": str(tmp_path / "melden.sh"), "FR_TITEL": "Probe",
               "WA_BERICHT": "", "WA_FEHLER": "", **umgebung}
        r = subprocess.run([str(BETRIEB / "waechter.sh")], capture_output=True, text=True, env=env)
        nachrichten = tmp_path / "nachrichten"
        return r, nachrichten.read_text().splitlines() if nachrichten.exists() else []
    lauf.stempel = tmp_path / "dienst" / "waechter-erfolg"
    return lauf


def test_waechter_ohne_neues_keine_nachricht(wa):
    r, nachrichten = wa()
    assert r.returncode == 0 and nachrichten == [] and wa.stempel.exists()


def test_waechter_bericht_geht_als_sammelnachricht_und_ist_erledigt(wa):
    r, nachrichten = wa(WA_BERICHT="Beispiel: Karl: Frist morgen.")
    assert r.returncode == 0 and len(nachrichten) == 1
    prio, betreff, text, erledigt = nachrichten[0].split("|", 3)
    assert (prio, erledigt) == ("normal", "erledigt") and betreff == "Probe: Watchdog and reminders"
    assert "Karl: Frist morgen." in text


def test_waechter_ohne_meldeweg_keine_nachricht(wa):
    r, nachrichten = wa(WA_BERICHT="Beispiel: Karl: Frist morgen.", FR_MELDEN="")
    assert r.returncode == 0 and nachrichten == []


def test_waechter_fehler_meldet_sich_und_laesst_den_stempel_aus(wa):
    r, nachrichten = wa(WA_FEHLER="1")
    assert r.returncode == 1 and not wa.stempel.exists()
    assert len(nachrichten) == 1 and nachrichten[0].split("|")[0] == "high" and "failed" in nachrichten[0]
    assert nachrichten[0].endswith("|")    # Fehler bleiben offen


# ---------- Einrichten und Vorlagen ----------

def einrichten(tmp_path, **umgebung):
    repo = tmp_path / "repo"
    (repo / "betrieb").mkdir(parents=True, exist_ok=True)
    (repo / "betrieb/einstellungen.env").write_text("FR_INSTANZ=probe\nFR_TITEL=Probe\nFR_ADRESSE=https://example.invalid\n")
    env = {**SAUBER, "FR_WURZEL": str(repo), "FR_SEITEN": str(tmp_path / "srv/probe"), "EI_ZIEL": str(tmp_path / "aus"),
           "EI_SYSTEMD": str(tmp_path / "systemd"), "FR_BENUTZER": "reisen", "FR_GRUPPE": "reisen",
           "FR_HOME": "/home/reisen", **umgebung}
    return subprocess.run([str(BETRIEB / "einrichten.sh")], capture_output=True, text=True, env=env, stdin=subprocess.DEVNULL)


def test_einrichten_erzeugt_einheiten_ohne_platzhalter(tmp_path):
    r = einrichten(tmp_path)
    assert r.returncode in (0, 2), r.stdout + r.stderr          # 2: Voraussetzungen fehlen hier (kein Python, kein gh)
    aus = tmp_path / "aus"
    namen = sorted(p.name for p in (aus / "systemd").iterdir())
    # kein Einarbeiten mehr (ADR-0001, O-3): keine Einheit ruft Claude Code auf, kein Pfad-Wächter auf die Ablage
    assert namen == ["probe-konnektor.service", "probe-rueckmeldungen.service", "probe-schreiben.service",
                     "probe-veroeffentlichen.service", "probe-veroeffentlichen.timer", "probe-waechter.service",
                     "probe-waechter.timer"]
    for p in [*(aus / "systemd").iterdir(), *(aus / "nginx").iterdir()]:
        assert not re.search(r"__[A-Z_]+__", p.read_text()), p.name
        assert "einarbeiten" not in p.read_text() and "claude -p" not in p.read_text(), p.name
    srv = tmp_path / "srv/probe"
    einh = {p.name: p.read_text() for p in (aus / "systemd").iterdir()}
    assert f"ExecStart={tmp_path}/repo/frieda/betrieb/veroeffentlichen.sh" in einh["probe-veroeffentlichen.service"]
    assert f"Environment=FR_WURZEL={tmp_path}/repo" in einh["probe-veroeffentlichen.service"]
    assert "User=reisen" in einh["probe-veroeffentlichen.service"] and "/home/reisen/.local/bin" in einh["probe-veroeffentlichen.service"]
    assert "Nice=10" in einh["probe-veroeffentlichen.service"] and "IOSchedulingClass=best-effort" in einh["probe-veroeffentlichen.service"]
    assert "IOSchedulingPriority=7" in einh["probe-veroeffentlichen.service"]
    assert "Environment=KN_PORT=8772" in einh["probe-konnektor.service"]
    assert "Environment=KN_BASIS=https://example.invalid" in einh["probe-konnektor.service"]
    assert f"ExecStart=/usr/bin/python3 {srv}/_dienst/konnektor.py dienst" in einh["probe-konnektor.service"]
    # Schreibweg (O-3): Konnektor kennt die Adresse, der Dienst läuft mit dem Python der Software aus dem Dienstordner
    assert "Environment=KN_SCHREIBDIENST=http://127.0.0.1:8773" in einh["probe-konnektor.service"]
    assert "Environment=FR_SB_PORT=8773" in einh["probe-schreiben.service"]
    assert f"ExecStart={tmp_path}/repo/engine/.venv/bin/python {srv}/_dienst/schreiben.py dienst" in einh["probe-schreiben.service"]
    assert f"Environment=FR_WURZEL={tmp_path}/repo" in einh["probe-schreiben.service"]
    assert "ProtectHome=" not in einh["probe-schreiben.service"]     # schreibt in die Arbeitskopie neben dem Repo
    assert "sudo systemctl enable --now probe-rueckmeldungen probe-konnektor probe-schreiben" in r.stdout
    assert "OnCalendar=" in einh["probe-waechter.timer"] and "Persistent=true" in einh["probe-waechter.timer"]
    nginx = (aus / "nginx/probe-konnektor.conf").read_text()
    inc = (aus / "nginx/probe-konnektor.inc").read_text()
    # Konnektor an der Wurzel (#163): /mcp, Anmeldung, OAuth; der alte Pfad bleibt für Links aus der Zeit vor den Konten
    assert "location ~ ^/(mcp|anmelden|abmelden|konto|authorize|token|register|gesund)$" in nginx
    assert "location ^~ /.well-known/oauth-" in nginx and "location ^~ /schrift/" in nginx and "location = /favicon.ico" in nginx
    assert "location ^~ /probe-mcp/" in nginx and "zone=probe_api" in nginx and "127.0.0.1:8772/" in nginx
    assert "include /etc/nginx/snippets/probe-konnektor.inc;" in nginx
    assert "proxy_pass http://127.0.0.1:8772;" in inc
    # Der Dienst setzt Referrer-Policy „same-origin“; „no-referrer“ von nginx ließe Browser „Origin: null“ schicken
    assert "add_header Referrer-Policy" not in nginx + inc
    assert "zone=probe_api:10m" in (aus / "nginx/probe-zone.conf").read_text()
    assert "sudo systemctl enable --now probe-veroeffentlichen.timer" in r.stdout
    # ohne --installieren wird außerhalb des Ausgabeordners nichts angelegt
    assert not (tmp_path / "srv").exists() and not (tmp_path / "systemd").exists()


def test_konnektor_darf_vorgemerkte_neue_reisen_schreiben(tmp_path, monkeypatch):
    """reise_anlegen merkt die neue Reise in einer Datei vor. Sie muss in einem Ordner liegen, den die Einheit des
    Konnektors beschreiben darf (ReadWritePaths), sonst scheitert das Anlegen im Betrieb mit „Read-only file system“.
    Das Veröffentlichen liest dieselbe Datei."""
    import konnektor as kn
    einrichten(tmp_path)
    einheit = (tmp_path / "aus/systemd/probe-konnektor.service").read_text()
    for z in einheit.splitlines():
        if z.startswith("Environment="):
            k, _, v = z[len("Environment="):].partition("=")
            monkeypatch.setenv(k, v)
    monkeypatch.delenv("KN_AUSSTEHEND", raising=False)
    schreibbar = next(z for z in einheit.splitlines() if z.startswith("ReadWritePaths=")).split("=", 1)[1].split()
    datei = kn.ausstehend_datei()
    assert any(datei.is_relative_to(p) for p in schreibbar), (datei, schreibbar)
    srv = tmp_path / "srv/probe"
    assert datei == srv / "_konnektor/neue-reisen-ausstehend.jsonl"
    assert "$FR_KONNEKTOR/neue-reisen-ausstehend.jsonl" in (BETRIEB / "veroeffentlichen.sh").read_text()


def test_einrichten_verlangt_konnektor_an_der_wurzel(tmp_path):
    """Die Anmeldeseiten verweisen auf /anmelden, OAuth erwartet /.well-known/ an der Wurzel (#163): ein Pfad geht nicht."""
    assert "FR_KN_ADRESSE “https://example.invalid/probe-mcp”" in einrichten(tmp_path, FR_KN_ADRESSE="https://example.invalid/probe-mcp").stdout
    assert "ok      connector at https://example.invalid/mcp" in einrichten(tmp_path).stdout


def _frei():
    import socket
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.mark.skipif(not shutil.which("nginx"), reason="nginx fehlt")
def test_nginx_leitet_konnektor_und_reise_richtig(tmp_path):
    """Die erzeugten Bausteine in einem echten nginx: Konnektor-Pfade an der Wurzel gehen an den Dienst, auch wenn der
    server-Block vorher eine allgemeine Regel für Dateiendungen hat; die Reiseseite kommt aus ihrem Ordner (#163)."""
    import http.server
    import threading
    import urllib.error
    import urllib.request
    kn_port, port = _frei(), _frei()
    snippets = tmp_path / "snippets"
    snippets.mkdir()
    r = einrichten(tmp_path, FR_KN_PORT=str(kn_port), FR_NGINX_SNIPPETS=str(snippets))
    assert r.returncode in (0, 2), r.stdout + r.stderr
    aus = tmp_path / "aus/nginx"
    for n in ("probe-konnektor.conf", "probe-konnektor.inc"):
        shutil.copy(aus / n, snippets / n)
    seiten = tmp_path / "seiten"
    (seiten / "reise").mkdir(parents=True)
    (seiten / "reise/index.html").write_text("Reiseseite")
    reise = (BETRIEB / "vorlagen/nginx-reise.conf").read_text()
    for k, v in {"__INSTANZ__": "probe", "__REISE__": "reise", "__TOKEN__": "geheim", "__SEITEN__": str(seiten),
                 "__ZONE__": "probe_api", "__RM_PORT__": str(_frei())}.items():
        reise = reise.replace(k, v)
    (snippets / "probe-reise.conf").write_text(reise)
    temp = " ".join(f"{n}_temp_path {tmp_path}/{n};" for n in ("client_body", "proxy", "fastcgi", "uwsgi", "scgi"))
    # Als root laufen die Arbeiter sonst als „nobody“ und lesen den Testordner nicht
    benutzer = "user root;" if os.geteuid() == 0 else ""
    (tmp_path / "nginx.conf").write_text(f"""{benutzer} pid {tmp_path}/nginx.pid; error_log {tmp_path}/fehler.log; daemon off;
events {{}}
http {{ access_log off; {temp}
  include {aus}/probe-zone.conf;
  server {{ listen 127.0.0.1:{port};
    location ~* \\.(ico|png|svg|woff2|ics)$ {{ return 418; }}
    include {snippets}/probe-*.conf;
  }}
}}
""")

    class Dienst(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("X-Pfad", self.path)
            self.end_headers()

        do_POST = do_GET

        def log_message(self, *a):
            pass

    s = http.server.ThreadingHTTPServer(("127.0.0.1", kn_port), Dienst)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    pruefung = subprocess.run(["nginx", "-t", "-e", str(tmp_path / "fehler.log"), "-c", str(tmp_path / "nginx.conf"), "-p", str(tmp_path)], capture_output=True, text=True)
    assert pruefung.returncode == 0, pruefung.stderr
    ng = subprocess.Popen(["nginx", "-e", str(tmp_path / "fehler.log"), "-c", str(tmp_path / "nginx.conf"), "-p", str(tmp_path)], stderr=subprocess.PIPE)
    try:
        def hol(pfad):
            import time
            for _ in range(50):
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{port}{pfad}") as a:
                        return a.status, a.headers.get("X-Pfad"), a.read().decode()
                except urllib.error.HTTPError as e:
                    return e.code, None, ""
                except OSError:
                    time.sleep(0.1)
            raise AssertionError("nginx antwortet nicht")
        # Konnektor an der Wurzel: Pfad kommt unverändert an
        for pfad in ("/mcp", "/anmelden?zurueck=/konto", "/konto", "/authorize?x=1", "/token", "/register", "/gesund",
                     "/.well-known/oauth-authorization-server", "/.well-known/oauth-protected-resource/mcp", "/einladung/abc",
                     "/kalender/abc.ics", "/schrift/source-sans-3-latin-wght-normal.woff2", "/favicon.ico", "/favicon.svg",
                     "/icon-192.png", "/" + "t" * 32):
            assert hol(pfad)[:2] == (200, pfad), pfad
        # alter Pfad der Links vor den Konten: Präfix fällt weg
        assert hol("/probe-mcp/" + "t" * 32)[:2] == (200, "/" + "t" * 32)
        # Reiseseite aus ihrem Ordner, Fremdes nicht an den Dienst
        assert hol("/reise-geheim/") == (200, None, "Reiseseite")
        assert hol("/etwas.png")[0] == 418 and hol("/anderes")[0] == 404
    finally:
        ng.terminate()
        ng.wait(timeout=10)
        s.shutdown()


def test_einrichten_erkennt_belegte_ports_einer_anderen_instanz(tmp_path):
    (tmp_path / "systemd").mkdir()
    (tmp_path / "systemd/andere-rueckmeldungen.service").write_text("[Service]\nEnvironment=RM_PORT=8771\n")
    r = einrichten(tmp_path)
    assert r.returncode == 2 and "Port 8771, 8772 or 8773 is already used by andere-rueckmeldungen.service" in r.stdout
    r = einrichten(tmp_path, FR_RM_PORT="8781", FR_KN_PORT="8782")
    assert "is already used by" not in r.stdout
    (tmp_path / "systemd/andere-schreiben.service").write_text("[Service]\nEnvironment=FR_SB_PORT=8773\n")
    assert "is already used by andere-schreiben.service" in einrichten(tmp_path, FR_RM_PORT="8781", FR_KN_PORT="8782").stdout
    (tmp_path / "systemd/andere-schreiben.service").unlink()
    r = einrichten(tmp_path, FR_RM_PORT="8781", FR_KN_PORT="8782", FR_SB_PORT="8783")
    assert "is already used by" not in r.stdout
    # die eigene Instanz zählt nicht als andere
    (tmp_path / "systemd/andere-rueckmeldungen.service").rename(tmp_path / "systemd/probe-rueckmeldungen.service")
    assert "is already used by" not in einrichten(tmp_path).stdout


def test_einrichten_installiert_nur_nach_bestaetigung(tmp_path):
    """Mit --installieren fragt das Skript; ohne „ja“ (oder mit fehlenden Voraussetzungen) ändert es nichts."""
    vorher = einrichten(tmp_path, FR_RM_PORT="8781").returncode
    r = subprocess.run([str(BETRIEB / "einrichten.sh"), "--installieren"], input="nein\n", capture_output=True, text=True,
                       env={**SAUBER, "FR_WURZEL": str(tmp_path / "repo"), "FR_SEITEN": str(tmp_path / "srv/probe"),
                            "EI_ZIEL": str(tmp_path / "aus"), "EI_SYSTEMD": str(tmp_path / "systemd"), "FR_RM_PORT": "8781"})
    if vorher == 2:
        assert r.returncode == 1 and "prerequisite(s) missing" in r.stdout
    else:
        assert r.returncode == 0 and "Nothing installed." in r.stdout
    assert not (tmp_path / "srv").exists() and not (tmp_path / "systemd").exists()


def test_vorlagen_ohne_werte_einer_instanz():
    """Der Betrieb kennt keine Instanz: keine Adressen, Benutzer, Pfade oder Namen einer echten Installation."""
    verboten = re.compile(r"/home/(?!reisen\b)\w+|/srv/(?!probe\b|beispiel\b|<)\w+|\b(?:www\.)?\w+\.(?:com|de|net)\b",
                          re.I)
    for p in sorted(BETRIEB.rglob("*")):
        if p.is_file() and p.suffix not in (".pyc",):
            text = p.read_text(encoding="utf-8")
            # github.com ist keine Adresse einer Instanz (Bot-Adresse im Workflow „Software nachziehen“, #161)
            treffer = [t for t in verboten.findall(text)
                       if "example" not in t and "anthropic" not in t and "claude" not in t and t.lower() != "github.com"]
            assert treffer == [], (p.name, treffer)


def test_betrieb_ohne_ki():
    """ADR-0001: Frieda enthält keine eigene KI. Kein Betriebsskript und keine Vorlage ruft Claude Code auf, und die
    Einstellungen kennen keinen KI-Lauf mehr (seit 29.10.2026, O-3 letzter Schritt)."""
    for p in sorted(BETRIEB.rglob("*")):
        if p.is_file() and p.suffix != ".pyc":
            text = p.read_text(encoding="utf-8")
            assert "claude -p" not in text and "einarbeiten" not in text.lower(), p.name
    assert not (BETRIEB / "einarbeiten.sh").exists() and not (BETRIEB / "einarbeiten-auftrag.md").exists()
    beispiel = (BETRIEB / "einstellungen.beispiel").read_text(encoding="utf-8")
    assert "FR_CLAUDE" not in beispiel and "FR_BETREIBER" not in beispiel


def test_skripte_sind_ausfuehrbar():
    for p in BETRIEB.glob("*.sh"):
        if p.name != "gemeinsam.sh":
            assert os.access(p, os.X_OK), p.name


# ---------- Vorgaben der Software ohne Instanzbezug (engine/instanz.py) ----------

def test_instanz_vorgaben(tmp_path, monkeypatch):
    import instanz
    for k in list(os.environ):
        if k.startswith(("FR_", "RM_", "KN_")):
            monkeypatch.delenv(k)
    monkeypatch.chdir(tmp_path)
    # ohne alles: allgemeine Vorgabe, kein Name einer Instanz
    assert instanz.seiten() == Path("/srv/frieda") and instanz.ablage() == Path("/srv/frieda/_rueckmeldungen")
    assert instanz.zugaenge() == Path("/srv/frieda/_konnektor/zugaenge.json") and "frieda-reist" in instanz.kennung()
    # Einstellungen der Instanz im aktuellen Ordner (Aufruf von Hand im Reisen-Repo)
    (tmp_path / "betrieb").mkdir()
    (tmp_path / "betrieb/einstellungen.env").write_text("# x\nFR_INSTANZ=probe\nFR_KENNUNG=\"Probe/1 (ida@example.org)\"\n")
    assert instanz.seiten() == Path("/srv/probe") and instanz.ablage() == Path("/srv/probe/_rueckmeldungen")
    assert instanz.kennung() == "Probe/1 (ida@example.org)"
    # ein Dienst, der nur die Ablage kennt, findet die Seiten daneben
    monkeypatch.chdir("/")
    monkeypatch.setenv("RM_ABLAGE", "/srv/andere/_rueckmeldungen")
    assert instanz.seiten() == Path("/srv/andere") and instanz.zugaenge() == Path("/srv/andere/_konnektor/zugaenge.json")
    # ausdrücklich gesetzte Werte gelten
    monkeypatch.setenv("KN_SEITEN", "/x/seiten")
    monkeypatch.setenv("KN_ZUGAENGE", "/x/z.json")
    assert instanz.seiten() == Path("/x/seiten") and instanz.zugaenge() == Path("/x/z.json")
    assert instanz.ablage() == Path("/srv/andere/_rueckmeldungen")


def test_software_ohne_pfade_einer_instanz():
    """Keine Ordner oder Adressen einer echten Installation als Vorgabe in der Software (#67)."""
    for p in ENGINE.glob("*.py"):
        assert not re.search(r"/srv/(?!frieda\b)\w+|/home/\w+", p.read_text(encoding="utf-8")), p.name


def test_einrichten_prueft_gh_und_nicht_claude(tmp_path):
    """Der Schreibweg pusht mit gh als Credential-Helfer; Claude Code braucht der Server nicht mehr (ADR-0001, O-3)."""
    bin_ = tmp_path / "bin"
    ausfuehrbar(bin_ / "gh", '#!/bin/sh\n[ "$1 $2" = "auth status" ] && [ "$ANGEMELDET" = true ]\n')
    pfad = f"{bin_}:/usr/bin:/bin"
    aus = einrichten(tmp_path, FR_PFAD=pfad, ANGEMELDET="false").stdout
    assert "MISSING gh is not signed in" in aus and "claude" not in aus.lower()
    assert "ok      gh signed in" in einrichten(tmp_path, FR_PFAD=pfad, ANGEMELDET="true").stdout


def test_freischalten_erneuert_den_baustein_bei_neuer_vorlage(fs):
    """Ändert sich vorlagen/nginx-reise.conf (etwa der Block für Belege, #76), bekommt jede Reise den neuen Baustein mit
    ihrem alten Token; nginx wird geprüft, bei Ablehnung gilt der alte Stand weiter."""
    r = fs["lauf"]("beispielreise")
    assert r.returncode == 0, r.stdout + r.stderr
    sn = fs["snippets"] / "probe-beispielreise.conf"
    inhalt = sn.read_text()
    pfad = inhalt.split("location ^~ /", 1)[1].split("/", 1)[0]
    assert "api/belege/" in inhalt and "client_max_body_size 11m" in inhalt
    # alter Baustein ohne den Belege-Block (wie vor dem 29.10.2026): wird erneuert, Token bleibt
    alt = inhalt.split("# Belege zu Buchungen", 1)[0] + inhalt.split("# Rückmeldedienst.", 1)[1]
    alt = "# Rückmeldedienst." + alt if "# Rückmeldedienst." not in alt else alt
    sn.write_text(inhalt.replace(inhalt[inhalt.index("# Belege zu Buchungen"):inhalt.index("# Rückmeldedienst.")], ""))
    assert "api/belege/" not in sn.read_text()
    r = fs["lauf"]("beispielreise")
    assert r.returncode == 0 and "Block renewed: beispielreise" in r.stdout, r.stdout + r.stderr
    assert sn.read_text() == inhalt and f"/{pfad}/" in sn.read_text()
    assert (fs["tmp"] / "nginx.log").read_text().count("reload") == 2
    # unverändert: nichts passiert
    r = fs["lauf"]("beispielreise")
    assert r.returncode == 0 and "erneuert" not in r.stdout and (fs["tmp"] / "nginx.log").read_text().count("reload") == 2
    # nginx lehnt den neuen Stand ab: der alte bleibt
    kaputt = inhalt.replace("client_max_body_size 11m", "client_max_body_size 9m")
    sn.write_text(kaputt)
    (fs["tmp"] / "nginx-kaputt").touch()
    r = fs["lauf"]("beispielreise")
    assert r.returncode == 1 and "old state stays in force" in r.stdout and sn.read_text() == kaputt


def test_freischalten_erneuert_auch_einen_von_hand_benannten_baustein(fs):
    """Ein von Hand angelegter Baustein kann einen Pfad tragen, der nicht mit dem Ordner der Reise beginnt (eine Reise
    „rundreise-2027“ unter „/rundreise-<token>/“). Die Erneuerung liest den Pfad aus dem Baustein und lässt den Link, wie er ist;
    bis zum 29.10.2026 brach sie hier stumm ab, und die Reise bekam den Belege-Block nie."""
    sn = fs["snippets"] / "probe-beispielreise.conf"
    pfad = "beispiel-0123456789abcdef01234567"
    sn.write_text("# von Hand angelegt\n"
                  f"location ^~ /{pfad}/ {{\n    alias {fs['seiten']}/beispielreise/;\n}}\n"
                  f"location ^~ /{pfad}/api/ {{\n    proxy_pass http://127.0.0.1:8871/beispielreise/;\n}}\n")
    r = fs["lauf"]("beispielreise")
    assert r.returncode == 0 and "Block renewed: beispielreise" in r.stdout, r.stdout + r.stderr
    inhalt = sn.read_text()
    assert f"location ^~ /{pfad}/ {{" in inhalt and f"location ^~ /{pfad}/api/belege/ {{" in inhalt
    assert "beispielreise-" not in inhalt.replace("probe-beispielreise.conf", "")   # kein zweiter Pfad aus Ordner und Token
    assert "proxy_pass http://127.0.0.1:8871/beispielreise/belege/;" in inhalt and not re.search(r"__[A-Z_]+__", inhalt)
    assert f"Seite: https://example.invalid/{pfad}/" in r.stdout
    assert json.loads((fs["tmp"] / "konnektor/seiten.json").read_text()) == {"beispielreise": f"https://example.invalid/{pfad}/"}
    # ohne location-Block: klarer Fehler statt stummem Abbruch
    sn.write_text("# leer\n")
    r = fs["lauf"]("beispielreise")
    assert r.returncode == 1 and "no path in the" in r.stdout
