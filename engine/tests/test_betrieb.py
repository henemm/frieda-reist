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
from conftest import meldet  # noqa: E402

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
             "KN_SEITEN", "KN_ZUGAENGE", "FR_KONNEKTOR", "KN_BASIS", "FR_ADRESSE", "FR_UMZUG_NACH"]
    skript = f'. "{BETRIEB}/gemeinsam.sh"; ' + "; ".join(f'echo "{n}=${{{n}:-}}"' for n in namen)
    r = subprocess.run(["bash", "-c", skript], capture_output=True, text=True,
                       env={**SAUBER, "FR_WURZEL": str(tmp_path), **umgebung})
    return r, dict(z.split("=", 1) for z in r.stdout.splitlines() if "=" in z)


def test_einstellungen_aus_datei_mit_vorgaben(tmp_path):
    r, w = einstellungen(tmp_path, "# Kommentar\nFR_INSTANZ=probe\nFR_ADRESSE=\"https://reisen.example.org\"\n"
                                   "FR_TITEL=$(touch boese)\n")
    assert r.returncode == 0, r.stderr
    assert w["FR_INSTANZ"] == "probe" and w["FR_SEITEN"] == "/srv/probe" and w["FR_ABLAGE"] == "/srv/probe/_rueckmeldungen"
    assert w["RM_ABLAGE"] == "/srv/probe/_rueckmeldungen" and w["FR_KONNEKTOR"] == "/srv/probe/_konnektor"
    assert w["KN_ZUGAENGE"] == ""        # die Datei der alten Links gibt es nicht mehr (#421)
    assert w["FR_KN_ADRESSE"] == w["KN_BASIS"] == "https://reisen.example.org"   # Konnektor an der Wurzel (#163)
    assert w["FR_PYTHON"] == f"{tmp_path}/engine/.venv/bin/python"
    assert w["FR_UMZUG_NACH"] == ""
    r2, w2 = einstellungen(tmp_path, "FR_UMZUG_NACH=https://neu.example.org\n")   # wird an bauen.py weitergereicht (exportiert)
    assert w2["FR_UMZUG_NACH"] == "https://neu.example.org"
    # keine Shell-Auswertung: der Wert bleibt Text, es wird nichts ausgeführt
    assert w["FR_TITEL"] == "$(touch boese)" and not (Path.cwd() / "boese").exists()


def gemeinsam_laden(tmp_path):
    return subprocess.run(["bash", "-c", f'. "{BETRIEB}/gemeinsam.sh"; echo erreicht'], capture_output=True, text=True,
                          env={**SAUBER, "FR_WURZEL": str(tmp_path)})


def test_fr_einlesen_unlesbare_datei_bricht_ab(tmp_path):
    """#361 (AC-11): Eine vorhandene, aber nicht lesbare Einstellungsdatei darf nicht still übersprungen werden, sonst
    baut das Veröffentlichen eine Speicher-Reise aus Git. (Verzeichnis statt Datei: gilt auch unter root.)"""
    (tmp_path / "betrieb" / "einstellungen.env").mkdir(parents=True)
    r = gemeinsam_laden(tmp_path)
    assert r.returncode != 0 and "erreicht" not in r.stdout
    assert "exists but cannot be read" in r.stderr and "einstellungen.env" in r.stderr


def test_fr_einlesen_fehlende_datei_ist_ok(tmp_path):
    (tmp_path / "betrieb").mkdir()
    r = gemeinsam_laden(tmp_path)
    assert r.returncode == 0 and "erreicht" in r.stdout, r.stderr


def nachziehen_weiche(tmp_path, reise, **umgebung):
    """Die beiden Funktionen aus software-nachziehen.sh (Speicher-Reise ja/nein) einzeln laufen lassen, im Ordner tmp_path."""
    text = (BETRIEB / "software-nachziehen.sh").read_text(encoding="utf-8")
    teil = text[text.index("speicherreisen_der_instanz() {"):text.index("umstellen() {")]
    skript = f'{teil}\nif aus_dem_speicher "$1"; then echo SPEICHER; else echo GIT; fi'
    return subprocess.run(["bash", "-c", skript, "x", reise], capture_output=True, text=True, cwd=tmp_path,
                          env={**SAUBER, **umgebung})


def test_nachziehen_weiche_unlesbare_datei_bricht_ab(tmp_path):
    """#361 (Adversary F001): Auch die Weiche des Workflows „Software nachziehen“ darf eine Speicher-Reise bei unlesbarer
    Einstellungsdatei nicht als Git-Reise umstellen."""
    (tmp_path / "betrieb" / "einstellungen.env").mkdir(parents=True)
    r = nachziehen_weiche(tmp_path, "beispielreise")
    assert r.returncode != 0 and "SPEICHER" not in r.stdout and "GIT" not in r.stdout
    assert "exists but cannot be read" in r.stderr


def test_nachziehen_weiche_fehlende_datei_und_umgebung(tmp_path):
    (tmp_path / "betrieb").mkdir()
    r = nachziehen_weiche(tmp_path, "beispielreise")
    assert r.returncode == 0 and r.stdout.strip() == "GIT", r.stderr
    (tmp_path / "betrieb" / "einstellungen.env").write_text("FR_SPEICHERREISEN=beispielreise\n")
    assert nachziehen_weiche(tmp_path, "beispielreise").stdout.strip() == "SPEICHER"
    assert nachziehen_weiche(tmp_path, "stadtwochenende").stdout.strip() == "GIT"


def test_unlesbare_datei_ueber_symlink_schleife_bricht_ab(tmp_path):
    """#361 (Adversary F002): Eine Symlink-Schleife zählt nicht als „fehlt“, sondern als nicht lesbar."""
    (tmp_path / "betrieb").mkdir()
    (tmp_path / "betrieb" / "einstellungen.env").symlink_to("einstellungen.env")
    assert gemeinsam_laden(tmp_path).returncode != 0
    assert nachziehen_weiche(tmp_path, "beispielreise").returncode != 0


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
              "FR_GEPRUEFT", "FR_WEGE_SPAETER", "FR_BIBLIOTHEKEN_NEU"}  # reicht veroeffentlichen.sh an deploy.sh weiter
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
                                                   f'[ -e {tmp_path}/kaputt-$1 ] && {{ cat {tmp_path}/kaputt-$1; exit 2; }}\nexit 0\n')
    # Prüf-Attrappe: aufgerufen mit „engine/tests“ (Software, rot über die Datei rot, Protokoll p) oder „tests“ (Tests des
    # Reisen-Repos, rot über rot-reise, Protokoll r)
    pruefen = ausfuehrbar(tmp_path / "pruefen.sh", f'#!/bin/sh\nif [ "$1" = tests ]; then echo r >> {tmp_path}/pruefen.log; '
                                                   f'[ ! -e {tmp_path}/rot-reise ]; exit; fi\n'
                                                   f'echo p >> {tmp_path}/pruefen.log\n[ ! -e {tmp_path}/rot ]\n')
    # Meldeweg an den Betrieb (FR_MELDEN) und Meldung an Personen (waechter.py rot-melden) als Attrappen
    melden = ausfuehrbar(tmp_path / "melden.sh", f'#!/bin/sh\necho "$1|$2|$3" >> {tmp_path}/melden.log\n'
                                                 f'[ ! -e {tmp_path}/melden-aus ]\n')
    rotmelden = ausfuehrbar(tmp_path / "rotmelden.sh", f'#!/bin/sh\necho "$@" >> {tmp_path}/rotmelden.log\n')
    # curl-Attrappe: protokolliert Heartbeat-Abrufe statt ins Netz zu gehen
    pings = tmp_path / "pings.log"
    ausfuehrbar(tmp_path / "bin/curl", f'#!/bin/sh\necho ping >> {pings}\n')
    frei = ausfuehrbar(tmp_path / "freischalten.sh",
                       f'#!/bin/sh\necho "$1" >> {tmp_path}/frei.log\necho "Seite: https://example.invalid/$1-geheim/"\n')
    # Einheiten-Abgleich (#260) als Attrappe „alles gleich“: der echte Abgleich läse /etc/systemd/system des Testrechners
    units = ausfuehrbar(tmp_path / "units-gleich.sh", "#!/bin/sh\nexit 0\n")
    nginx_gleich = ausfuehrbar(tmp_path / "nginx-gleich.sh", "#!/bin/sh\nexit 0\n")   # Abgleich der nginx-Bausteine (#206), sonst läse er /etc/nginx
    env = {**SAUBER, "FR_WURZEL": str(arbeit), "FR_INSTANZ": "probe", "FR_DIENST": str(tmp_path / "dienst"), "VF_UNITS": str(units),
           "VF_NGINX": str(nginx_gleich),
           "FR_KONNEKTOR": str(tmp_path / "konnektor"), "FR_SPERREN": str(tmp_path), "VF_DEPLOY": str(attrappe), "VF_PRUEFEN": str(pruefen), "VF_FREISCHALTEN": str(frei),
           "FR_HEARTBEAT_VEROEFFENTLICHEN": "https://example.invalid/hb", "PATH": f"{tmp_path / 'bin'}:{os.environ['PATH']}",
           "FR_MELDEN": str(melden), "VF_ROTMELDEN": str(rotmelden), "FR_SUDO": ""}   # Root-Rechte: ohne sudo (#465)

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

    def inhalt(reise, text="neu"):
        """Ein reiner Inhaltsstand: Commit nur in reisen/<reise>/ (wie der Schreibweg)."""
        datei = quelle / "reisen" / reise / "inhalt.md"
        datei.write_text((datei.read_text() if datei.exists() else "") + text + "\n")
        git(quelle, "add", ".")
        git(quelle, "commit", "-qm", f"{reise}: {text}")

    def lauf_stand(reise):
        datei = tmp_path / "dienst" / "reise-stand" / f"{reise}.lauf.json"
        return json.loads(datei.read_text()) if datei.exists() else None

    return {"lauf": lauf, "deploys": deploys, "pings": anzahl_pings, "neuer_commit": neuer_commit, "arbeit": arbeit,
            "tmp": tmp_path, "env": env, "reisetests": reisetests, "rot": rot, "zeilen": zeilen, "kopf": kopf,
            "inhalt": inhalt, "lauf_stand": lauf_stand}


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


def test_veroeffentlichen_inhaltsstand_baut_nur_die_geaenderte_reise(vf):
    """#230: Ein reiner Inhaltsstand (nur reisen/<reise>/ geändert) baut nur diese Reise und überspringt die Prüfungen der
    Software, die für diese Software schon grün waren; ein Software-Wechsel prüft und baut weiter alles."""
    vf["reisetests"]()
    assert vf["lauf"]().returncode == 0 and vf["deploys"]() == ["beispielreise", "zweitreise"]
    assert vf["zeilen"]("pruefen.log") == ["p", "r"]
    vf["inhalt"]("zweitreise")
    r = vf["lauf"]()
    assert r.returncode == 0 and "content only: zweitreise" in r.stdout and "checks skipped" in r.stdout, r.stdout
    assert vf["deploys"]() == ["zweitreise"]
    assert vf["zeilen"]("pruefen.log") == ["p", "r"]                       # weder Software- noch Inhaltstests
    assert (vf["tmp"] / "gepreuft.log").read_text().split()[-1] == vf["kopf"]()   # deploy.sh prüft nicht selbst
    assert (vf["tmp"] / "dienst/veroeffentlicht").read_text().strip() == vf["kopf"]()
    vf["neuer_commit"]()                                                      # außerhalb von reisen/: Software
    assert vf["lauf"]().returncode == 0 and vf["deploys"]() == ["beispielreise", "zweitreise"]
    assert vf["zeilen"]("pruefen.log") == ["p", "r", "p", "r"]
    vf["inhalt"]("beispielreise")
    assert vf["lauf"]("--immer").returncode == 0 and vf["deploys"]() == ["beispielreise", "zweitreise"]   # --immer: alles


def test_veroeffentlichen_heilt_haengendes_baut_ohne_neuen_stand(vf):
    """#397: Ein abgebrochener Lauf lässt eine Reise auf „baut“ stehen. Der nächste Lauf baut sie auch ohne neuen Stand
    (nur sie, nur eine Git-Reise, die es gibt) und setzt den Zustand auf „veröffentlicht“; ohne Hänger tut ein Lauf ohne neuen Stand nichts."""
    assert vf["lauf"]().returncode == 0 and vf["deploys"]() == ["beispielreise", "zweitreise"]
    assert vf["lauf"]().returncode == 0 and vf["deploys"]() == []
    stand = vf["tmp"] / "dienst/reise-stand"
    hing = stand / "zweitreise.lauf.json"
    hing.write_text(hing.read_text().replace('"veroeffentlicht"', '"baut"'))
    (stand / "gibt-es-nicht.lauf.json").write_text('{"zustand": "baut", "nummer": 1}\n')   # eine Reise, die es nicht gibt
    assert vf["lauf_stand"]("zweitreise")["zustand"] == "baut"
    r = vf["lauf"]()
    assert r.returncode == 0, r.stdout
    assert vf["deploys"]() == ["zweitreise"]
    assert vf["lauf_stand"]("zweitreise")["zustand"] == "veroeffentlicht"
    assert vf["lauf"]().returncode == 0 and vf["deploys"]() == []


def test_veroeffentlichen_schreibt_den_zustand_je_reise(vf):
    """#228: Je gebauter Reise steht ihr Zustand mit Reise-Stand in <FR_DIENST>/reise-stand/<reise>.lauf.json: veröffentlicht mit
    Dauer seit dem Sichern (auch im Protokoll), fehlgeschlagen mit dem Grund aus der Ausgabe des Baus."""
    assert vf["lauf"]().returncode == 0 and vf["deploys"]() == ["beispielreise", "zweitreise"]
    st = vf["lauf_stand"]("zweitreise")
    assert st["zustand"] == "veroeffentlicht" and st["nummer"] == 1 and isinstance(st["dauer"], int)
    assert st["gesichert"].endswith("Z") and st["seit"].endswith("Z")
    vf["inhalt"]("zweitreise")
    vf["inhalt"]("zweitreise", "noch mehr")
    (vf["tmp"] / "kaputt-zweitreise").write_text('Die Seite wurde NICHT gebaut. Das muss zuerst behoben werden:\n'
                                                 ' - plan/routen.yaml: U-09 gibt es nicht ("Hütte")\n')
    r = vf["lauf"]()
    assert r.returncode == 1 and vf["deploys"]() == ["zweitreise"]
    st = vf["lauf_stand"]("zweitreise")
    assert st["zustand"] == "fehlgeschlagen" and st["nummer"] == 3
    assert st["grund"] == "plan/routen.yaml: U-09 gibt es nicht ('Hütte')"
    assert vf["lauf_stand"]("beispielreise")["nummer"] == 1               # nicht angefasst
    # Die rote Reise bleibt in jedem Inhaltslauf dabei (ihr Rot gilt weiter), bis ihr Bau gelingt
    vf["inhalt"]("beispielreise")
    r = vf["lauf"]()
    assert r.returncode == 1 and vf["deploys"]() == ["beispielreise", "zweitreise"] and vf["rot"]()["reisen"] == "zweitreise"
    (vf["tmp"] / "kaputt-zweitreise").unlink()
    vf["inhalt"]("beispielreise", "wieder")
    r = vf["lauf"]()
    assert r.returncode == 0 and vf["deploys"]() == ["beispielreise", "zweitreise"] and vf["rot"]() is None
    assert "Published zweitreise state 3, " in r.stdout and vf["lauf_stand"]("zweitreise")["zustand"] == "veroeffentlicht"
    # Die Zeit des Schreibwegs gilt für die Dauer, wenn er diesen Stand gesichert hat
    (vf["tmp"] / "dienst/reise-stand/beispielreise.gesichert.json").write_text('{"nummer": 4, "commit": "x", "zeit": "%s"}' % iso(T0))
    vf["inhalt"]("beispielreise", "vierter")
    r = vf["lauf"](VF_JETZT=str(T0 + 300))
    assert vf["lauf_stand"]("beispielreise")["dauer"] == 300 and vf["lauf_stand"]("beispielreise")["gesichert"] == iso(T0)
    assert "Warning: beispielreise state 4 published 300 s after saving, longer than the target of 120 s." in r.stdout
    # Ein Neubau desselben Stands (--immer, Software-Wechsel, Umschaltung auf den Speicher) ist keine Wartezeit: Der
    # Stand war schon auf der Seite, gemessen wird nicht, und publish_status zeigt keine falsche Dauer (#465)
    r = vf["lauf"]("--immer", VF_JETZT=str(T0 + 50000))
    assert r.returncode == 0, r.stdout
    assert "longer than the target" not in r.stdout and "Published beispielreise state 4 again" in r.stdout
    st = vf["lauf_stand"]("beispielreise")
    assert st["zustand"] == "veroeffentlicht" and st["nummer"] == 4 and st["dauer"] is None


def test_veroeffentlichen_holt_einen_waehrend_des_laufs_angestossenen_stand_gleich_nach(vf):
    """#230: Findet ein Lauf die Sperre belegt (Schreibweg während eines Timer-Laufs), merkt er das; der laufende Lauf
    veröffentlicht danach gleich noch einmal, statt den neuen Stand bis zum Timer warten zu lassen."""
    import fcntl
    assert vf["lauf"]().returncode == 0 and vf["deploys"]() == ["beispielreise", "zweitreise"]
    sperre = vf["tmp"] / "dienst" / "veroeffentlichen.lock"
    nochmal = vf["tmp"] / "dienst" / "veroeffentlichen-nochmal"
    with open(sperre, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        r = vf["lauf"]()
    assert "Already running" in r.stdout and nochmal.exists()
    # Der laufende Lauf, nachgestellt: sein Deploy kündigt währenddessen einen neuen Stand an (wie ein übersprungener Lauf)
    nochmal.unlink()
    vf["inhalt"]("zweitreise")
    kuendigen = ausfuehrbar(vf["tmp"] / "deploy2.sh", f'#!/bin/sh\necho "$1" >> {vf["tmp"]}/deploy.log\n'
                                                     f'[ -e {vf["tmp"]}/einmal ] || touch {vf["tmp"]}/einmal {nochmal}\nexit 0\n')
    r = vf["lauf"](VF_DEPLOY=str(kuendigen))
    assert r.returncode == 0 and "A new state arrived during the run, publishing again." in r.stdout, r.stdout + r.stderr
    assert r.stdout.count("Publishing ") == 1 and vf["deploys"]() == ["zweitreise"]   # der zweite Lauf findet nichts Neues
    assert not nochmal.exists()


# ---------- Veröffentlichen: geänderte Einstellungen wirken im selben Lauf (#242) ----------

def einstellungen_setup(vf):
    """Origin und Bauordner haben schon eine Einstellungsdatei (alte Adresse); die Deploy-Attrappe protokolliert die
    Adressen, die sie sieht. Gibt Funktionen zum Ändern der Datei im Origin und das Adressprotokoll zurück."""
    quelle = vf["tmp"] / "quelle"
    datei = quelle / "betrieb" / "einstellungen.env"

    def setzen(text, meldung="einstellungen"):
        datei.parent.mkdir(exist_ok=True)
        datei.write_text(text)
        git(quelle, "add", ".")
        git(quelle, "commit", "-qm", meldung)

    def entfernen():
        git(quelle, "rm", "-q", "betrieb/einstellungen.env")
        git(quelle, "commit", "-qm", "ohne einstellungen")

    setzen("FR_ADRESSE=https://alt.example.invalid\n", "alt")
    git(vf["arbeit"], "pull", "-q", "--ff-only")
    adressen = vf["tmp"] / "adressen.log"
    attrappe = ausfuehrbar(vf["tmp"] / "deploy-adressen.sh",
                           f'#!/bin/sh\necho "$1 $FR_ADRESSE $FR_KN_ADRESSE $KN_BASIS" >> {adressen}\nexit 0\n')

    def gesehen():
        z = adressen.read_text().splitlines() if adressen.exists() else []
        adressen.unlink(missing_ok=True)
        return z

    return setzen, entfernen, gesehen, {"VF_DEPLOY": str(attrappe)}


def neustarts(r):
    return len(re.findall(r"restart", r.stdout, re.I))


def test_veroeffentlichen_uebernimmt_geaenderte_einstellungen_im_selben_lauf(vf):
    """#242: Bringt das Vorspulen eine geänderte Einstellungsdatei, startet sich der Lauf neu und baut mit den neuen Werten,
    auch den abgeleiteten (FR_KN_ADRESSE)."""
    setzen, _, gesehen, extra = einstellungen_setup(vf)
    setzen("FR_ADRESSE=https://neu.example.invalid\n", "neu")
    r = vf["lauf"](**extra)
    assert r.returncode == 0, r.stdout + r.stderr
    assert neustarts(r) == 1, r.stdout
    zeilen = gesehen()
    assert zeilen and all("https://neu.example.invalid https://neu.example.invalid" in z for z in zeilen), zeilen


def test_veroeffentlichen_wert_aus_dem_aufruf_gewinnt_auch_nach_dem_neustart(vf):
    setzen, _, gesehen, extra = einstellungen_setup(vf)
    setzen("FR_ADRESSE=https://neu.example.invalid\n", "neu")
    r = vf["lauf"](FR_ADRESSE="https://aufruf.example.invalid", **extra)
    assert r.returncode == 0, r.stdout + r.stderr
    assert neustarts(r) == 1, r.stdout     # die Datei hat sich trotzdem geändert
    zeilen = gesehen()
    assert zeilen and all("https://aufruf.example.invalid https://aufruf.example.invalid" in z for z in zeilen), zeilen


def test_veroeffentlichen_unveraenderte_einstellungen_starten_nicht_neu(vf):
    """Regressionsschutz: kein Neustart ohne Änderung der Datei."""
    setzen, _, gesehen, extra = einstellungen_setup(vf)
    vf["neuer_commit"]()
    r = vf["lauf"](**extra)
    assert r.returncode == 0 and neustarts(r) == 0, r.stdout
    assert r.stdout.count("Publishing ") == 1 and gesehen()


def test_veroeffentlichen_geerbte_merker_eines_aeusseren_laufs_stoeren_den_neustart_nicht(vf):
    """#242, Störung auf dem Server: Die Tests laufen dort unter einem echten Lauf von veroeffentlichen.sh und erben dessen
    Merker (Namen der Aufruf-Werte, Neustart). Die Merker gelten nur für den Prozess, der sie gesetzt hat (exec behält die PID)."""
    setzen, _, gesehen, extra = einstellungen_setup(vf)
    setzen("FR_ADRESSE=https://neu.example.invalid\n", "neu")
    geerbt = {"_aufruf_namen": " FR_WURZEL_DER_ECHTEN_INSTANZ ", "_aufruf_pid": "1", "_neugestartet": "1"}
    r = vf["lauf"](**geerbt, **extra)
    assert r.returncode == 0, r.stdout + r.stderr
    assert neustarts(r) == 1, r.stdout
    zeilen = gesehen()
    assert zeilen and all("https://neu.example.invalid" in z for z in zeilen), zeilen


def test_veroeffentlichen_startet_hoechstens_einmal_neu(vf):
    """Regressionsschutz: keine Endlosschleife."""
    setzen, _, gesehen, extra = einstellungen_setup(vf)
    setzen("FR_ADRESSE=https://neu.example.invalid\n", "neu")
    r = subprocess.run([str(BETRIEB / "veroeffentlichen.sh")], env={**vf["env"], **extra}, capture_output=True, text=True,
                       timeout=60)
    assert r.returncode == 0 and neustarts(r) == 1 and r.stdout.count("Publishing ") == 1, r.stdout
    assert vf["lauf"](**extra).stdout.count("Publishing ") == 0     # ein weiterer Lauf: nichts mehr zu tun


def test_veroeffentlichen_neustart_behaelt_immer(vf):
    """Regressionsschutz: --immer übersteht den Neustart (alles wird gebaut)."""
    setzen, _, gesehen, extra = einstellungen_setup(vf)
    assert vf["lauf"](**extra).returncode == 0
    gesehen()
    setzen("FR_ADRESSE=https://neu.example.invalid\n", "neu")
    r = vf["lauf"]("--immer", **extra)
    assert r.returncode == 0 and neustarts(r) == 1, r.stdout
    assert sorted(z.split()[0] for z in gesehen()) == ["beispielreise", "zweitreise"]


def test_veroeffentlichen_einstellungen_ausserhalb_des_repos_starten_nicht_neu(vf):
    """Regressionsschutz: FR_EINSTELLUNGEN außerhalb des Repos, das Vorspulen ändert sie nicht."""
    setzen, _, gesehen, extra = einstellungen_setup(vf)
    aussen = vf["tmp"] / "aussen.env"
    aussen.write_text("FR_ADRESSE=https://aussen.example.invalid\n")
    vf["neuer_commit"]()
    r = vf["lauf"](FR_EINSTELLUNGEN=str(aussen), **extra)
    assert r.returncode == 0 and neustarts(r) == 0, r.stdout
    assert all("https://aussen.example.invalid" in z for z in gesehen())


@pytest.mark.parametrize("fall", ["neu", "entfernt"])
def test_veroeffentlichen_neue_oder_entfernte_einstellungsdatei_ist_eine_aenderung(vf, fall):
    if fall == "neu":
        quelle = vf["tmp"] / "quelle"
        (quelle / "betrieb").mkdir()
        (quelle / "betrieb" / "einstellungen.env").write_text("FR_ADRESSE=https://neu.example.invalid\n")
        git(quelle, "add", ".")
        git(quelle, "commit", "-qm", "neu angelegt")
        attrappe = ausfuehrbar(vf["tmp"] / "deploy-adressen.sh",
                               f'#!/bin/sh\necho "$1 $FR_ADRESSE" >> {vf["tmp"]}/adressen.log\n')
        extra = {"VF_DEPLOY": str(attrappe)}
        erwartet = "https://neu.example.invalid"
    else:
        _, entfernen, _, extra = einstellungen_setup(vf)
        entfernen()
        erwartet = ""
    r = vf["lauf"](**extra)
    assert r.returncode == 0 and neustarts(r) == 1, r.stdout + r.stderr
    zeilen = (vf["tmp"] / "adressen.log").read_text().splitlines()
    assert zeilen and all(z.split(" ", 1)[1].split(" ")[0].strip() == erwartet for z in zeilen), zeilen


def test_interne_merker_haben_kein_fr_praefix():
    """Die neuen Merker (Namen der Aufruf-Werte, Neustart) tragen kein FR_-Präfix: Die Aufräum-Schleife und die
    Einstellungsvorlage erfassen sie nicht."""
    gemeinsam = (BETRIEB / "gemeinsam.sh").read_text(encoding="utf-8")
    ver = (BETRIEB / "veroeffentlichen.sh").read_text(encoding="utf-8")
    assert "_aufruf_namen" in gemeinsam, "Merker der Aufruf-Namen fehlt"
    assert 'exec "$0" "$@"' in ver and "sha256sum" in ver
    assert not re.search(r"\bFR_[A-Z_]*(AUFRUF|NEUSTART)", gemeinsam + ver)


def test_anstoss_von_der_seite_startet_den_workflow(vf):
    """Organisator:innen stoßen auf der Seite das Veröffentlichen an (api/aktualisieren): der nächste Lauf startet den
    Workflow „Software nachziehen“ und legt das Ergebnis für die Seite ab; gescheitert geht eine Nachricht an den Betrieb."""
    t = vf["tmp"]
    ablage = t / "ablage"
    ablage.mkdir()
    nachziehen = ausfuehrbar(t / "nachziehen.sh", f'#!/bin/sh\necho los >> {t}/nachziehen.log\n[ ! -e {t}/gh-kaputt ]\n')
    extra = {"FR_ABLAGE": str(ablage), "VF_NACHZIEHEN": str(nachziehen)}
    assert vf["lauf"](**extra).returncode == 0 and vf["zeilen"]("nachziehen.log") == []       # ohne Anstoß nichts
    (ablage / "_anstoss.json").write_text('{"zeit": "2026-11-01T12:00:00+00:00", "reise": "beispielreise", "von": "Ida"}\n')
    r = vf["lauf"](**extra)
    assert r.returncode == 0 and "workflow software-nachziehen.yml started" in r.stdout
    assert vf["zeilen"]("nachziehen.log") == ["los"] and not (ablage / "_anstoss.json").exists()
    assert json.loads((ablage / "_anstoss-ergebnis.json").read_text())["ok"] is True
    vf["lauf"](**extra)
    assert vf["zeilen"]("nachziehen.log") == ["los"]                                              # nur einmal
    (t / "gh-kaputt").touch()
    (ablage / "_anstoss.json").write_text('{"zeit": "2026-11-01T13:00:00+00:00", "reise": "beispielreise", "von": "Ida"}\n')
    r = vf["lauf"](**extra)
    assert r.returncode == 0 and "could not be started" in r.stdout
    assert json.loads((ablage / "_anstoss-ergebnis.json").read_text())["ok"] is False
    assert any("Publish request failed" in z for z in vf["zeilen"]("melden.log"))


# ---------- Anstoß vom Server: neuer Software-Stand startet „Software nachziehen“ (#250, AC-5) ----------

GIT_ERLAUBT = {"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "protocol.file.allow", "GIT_CONFIG_VALUE_0": "always"}
STUNDE = 3600


@pytest.fixture
def an(vf):
    """vf mit echtem Submodul frieda/ (Software-Repo, Stand A) im Reisen-Repo. VF_LSREMOTE ersetzt `git ls-remote`
    (Aufrufe in lsremote.log, Antwort im Format von ls-remote aus der Datei remote-stand, rot über lsremote-kaputt),
    VF_NACHZIEHEN ersetzt `gh workflow run` (Aufrufe in nachziehen.log, rot über gh-kaputt)."""
    t = vf["tmp"]
    sw = t / "software"
    sw.mkdir()
    (sw / "LIESMICH").write_text("Software\n")
    git(sw, "init", "-q", "-b", "main")
    git(sw, "add", ".")
    git(sw, "commit", "-qm", "A")
    a = git(sw, "rev-parse", "HEAD").strip()
    quelle = t / "quelle"
    subprocess.run(["git", "-C", str(quelle), "submodule", "add", "-q", str(sw), "frieda"], check=True,
                   capture_output=True, env={**os.environ, **GIT, **GIT_ERLAUBT})
    git(quelle, "commit", "-qm", "Software eingebunden")
    lsremote = ausfuehrbar(t / "lsremote.sh", f'#!/bin/sh\necho "$@" >> {t}/lsremote.log\n[ ! -e {t}/lsremote-kaputt ] || exit 128\n'
                                              f'printf "%s\\trefs/heads/main\\n" "$(cat {t}/remote-stand)"\n')
    nachziehen = ausfuehrbar(t / "nachziehen.sh", f'#!/bin/sh\necho los >> {t}/nachziehen.log\n[ ! -e {t}/gh-kaputt ]\n')
    (t / "remote-stand").write_text(a + "\n")
    extra = {**GIT_ERLAUBT, "VF_LSREMOTE": str(lsremote), "VF_NACHZIEHEN": str(nachziehen), "FR_ABLAGE": str(t / "ablage")}

    def lauf(jetzt, **mehr):
        return vf["lauf"](VF_JETZT=str(jetzt), **{**extra, **mehr})

    def remote(stand):
        (t / "remote-stand").write_text(stand + "\n")

    def merk():
        datei = t / "dienst" / "nachziehen-angestossen"
        return datei.read_text().split() if datei.exists() else None

    def starts():
        n = len(vf["zeilen"]("nachziehen.log"))
        (t / "nachziehen.log").unlink(missing_ok=True)
        return n

    return {**vf, "lauf_an": lauf, "remote": remote, "merk": merk, "starts": starts, "a": a, "sw": sw}


def test_anstoss_einmal_je_neuem_software_stand(an):
    r = an["lauf_an"](T0)
    assert r.returncode == 0, r.stdout + r.stderr
    assert an["starts"]() == 0 and an["merk"]() is None                 # eingebunden == main der Software: nichts
    assert an["deploys"]() == ["beispielreise", "zweitreise"]
    assert str(an["sw"]) in an["zeilen"]("lsremote.log")[0]           # URL aus .gitmodules

    b = "b" * 40
    an["remote"](b)
    r = an["lauf_an"](T0 + 60)
    assert r.returncode == 0 and an["starts"]() == 1
    assert an["merk"]() == [b, str(T0 + 60)]                           # „SHA Epoche“
    for dt in (120, 6 * STUNDE + 59):                                  # derselbe Stand: nicht vor Ablauf der Wartezeit
        assert an["lauf_an"](T0 + dt).returncode == 0 and an["starts"]() == 0
    assert an["lauf_an"](T0 + 60 + 6 * STUNDE).returncode == 0 and an["starts"]() == 1
    assert an["merk"]() == [b, str(T0 + 60 + 6 * STUNDE)]

    c = "c" * 40                                                       # ein weiterer Stand startet sofort
    an["remote"](c)
    assert an["lauf_an"](T0 + 60 + 6 * STUNDE + 1).returncode == 0 and an["starts"]() == 1
    assert an["merk"]()[0] == c


def test_anstoss_wartezeit_ist_einstellbar(an):
    an["remote"]("b" * 40)
    an["lauf_an"](T0, FR_NACHZIEHEN_WIEDERHOLEN_STUNDEN="1")
    assert an["starts"]() == 1
    an["lauf_an"](T0 + STUNDE - 1, FR_NACHZIEHEN_WIEDERHOLEN_STUNDEN="1")
    assert an["starts"]() == 0
    an["lauf_an"](T0 + STUNDE, FR_NACHZIEHEN_WIEDERHOLEN_STUNDEN="1")
    assert an["starts"]() == 1


def test_anstoss_merkdatei_nur_nach_erfolg_und_veroeffentlichen_laeuft_weiter(an):
    an["remote"]("b" * 40)
    (an["tmp"] / "gh-kaputt").touch()
    r = an["lauf_an"](T0)
    assert r.returncode == 0, r.stdout + r.stderr
    assert an["starts"]() == 1 and an["merk"]() is None
    assert "warning" in r.stdout.lower()
    assert an["deploys"]() == ["beispielreise", "zweitreise"]          # das Veröffentlichen läuft trotzdem
    (an["tmp"] / "gh-kaputt").unlink()
    an["lauf_an"](T0 + 60)                                             # nächster Lauf versucht es wieder
    assert an["starts"]() == 1 and an["merk"]() == ["b" * 40, str(T0 + 60)]


def test_anstoss_ls_remote_rot_ist_nur_eine_warnung(an):
    (an["tmp"] / "lsremote-kaputt").touch()
    r = an["lauf_an"](T0)
    assert r.returncode == 0, r.stdout + r.stderr
    assert an["zeilen"]("lsremote.log") and an["starts"]() == 0 and an["merk"]() is None
    assert "warning" in r.stdout.lower()
    assert an["deploys"]() == ["beispielreise", "zweitreise"]


def test_anstoss_wartezeit_mit_fuehrender_null(an):
    """Gegenprüfung F001/F005: Wartezeit „08“ und eine gemerkte Zeit mit führender Null gelten dezimal (keine Oktalzahl,
    die die Arithmetik abbricht); das Veröffentlichen läuft durch. Ohne Merkdatei keine Fehlermeldung beim Lesen."""
    b = "b" * 40
    an["remote"](b)
    r = an["lauf_an"](T0, FR_NACHZIEHEN_WIEDERHOLEN_STUNDEN="08")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "No such file" not in r.stdout + r.stderr
    assert an["starts"]() == 1 and an["deploys"]() == ["beispielreise", "zweitreise"]
    (an["tmp"] / "dienst" / "nachziehen-angestossen").write_text(f"{b} 0{T0}\n")
    r = an["lauf_an"](T0 + 8 * STUNDE - 1, FR_NACHZIEHEN_WIEDERHOLEN_STUNDEN="08")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "value too great" not in r.stdout + r.stderr and an["starts"]() == 0
    an["lauf_an"](T0 + 8 * STUNDE, FR_NACHZIEHEN_WIEDERHOLEN_STUNDEN="09")
    assert an["starts"]() == 0
    an["lauf_an"](T0 + 9 * STUNDE, FR_NACHZIEHEN_WIEDERHOLEN_STUNDEN="09")
    assert an["starts"]() == 1


def test_wartezeit_vorgabe_sechs_stunden(tmp_path):
    r = subprocess.run(["bash", "-c", f'. "{BETRIEB}/gemeinsam.sh"; echo "$FR_NACHZIEHEN_WIEDERHOLEN_STUNDEN"'],
                       capture_output=True, text=True, env={**SAUBER, "FR_WURZEL": str(tmp_path)})
    assert r.stdout.strip() == "6"


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
    """Zwei Instanzen auf einem Server stören sich nicht: die Sperre liegt im Dienstordner der Instanz (#211)."""
    import fcntl
    (vf["tmp"] / "andere-dienst").mkdir()
    with open(vf["tmp"] / "andere-dienst" / "veroeffentlichen.lock", "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        assert "Already running" not in vf["lauf"]().stdout
    (vf["tmp"] / "dienst").mkdir(exist_ok=True)
    with open(vf["tmp"] / "dienst" / "veroeffentlichen.lock", "w") as f:
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


def test_veroeffentlichen_ohne_root_rechte_merkt_vor_und_der_naechste_lauf_schaltet_frei(vf):
    """Der Schreibweg stößt das Veröffentlichen aus einem Dienst mit NoNewPrivileges an, darin geht kein sudo (#465).
    Dann wird nicht freigeschaltet (freischalten.sh hielte sonst den Baustein für fehlend) und nicht zugestellt; die
    Reisen werden vorgemerkt, und der nächste Lauf mit Root-Rechten schaltet sie frei, auch ohne neuen Stand."""
    py = ausfuehrbar(vf["tmp"] / "python.sh", f'#!/bin/sh\necho "$@" >> {vf["tmp"]}/zustellen.log\n')
    (vf["tmp"] / "konnektor").mkdir(exist_ok=True)
    (vf["tmp"] / "konnektor/neue-reisen-ausstehend.jsonl").write_text('{"ordner": "neu"}\n')
    r = vf["lauf"](FR_SUDO="false", FR_PYTHON=str(py))
    assert r.returncode == 0, r.stdout + r.stderr
    zl = vf["tmp"] / "zustellen.log"   # FR_PYTHON läuft auch für anderes: nur zustellen.py zählt
    assert not (vf["tmp"] / "frei.log").exists() and "zustellen.py" not in (zl.read_text() if zl.exists() else "")
    assert "Note: beispielreise not released in this run" in r.stdout and "next timer run" in r.stdout
    vorgemerkt = vf["tmp"] / "dienst/freischalten-ausstehend"
    assert vorgemerkt.read_text().split() == ["beispielreise", "zweitreise"]
    # Ein weiterer Lauf ohne Rechte merkt nichts doppelt vor
    r = vf["lauf"]("--immer", FR_SUDO="false", FR_PYTHON=str(py))
    assert r.returncode == 0 and vorgemerkt.read_text().split() == ["beispielreise", "zweitreise"], r.stdout
    # Der Timer (mit Root-Rechten, nichts Neues auf main) schaltet die vorgemerkten frei und stellt zu
    r = vf["lauf"](FR_PYTHON=str(py))
    assert r.returncode == 0, r.stdout + r.stderr
    assert (vf["tmp"] / "frei.log").read_text().split() == ["beispielreise", "zweitreise"]
    assert not vorgemerkt.exists() and "zustellen.py" in zl.read_text()
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


def test_deploy_startprobe_findet_playwright_der_instanz_ohne_umgebungswert(tmp_path):
    """#387: Reisen aus dem Reisespeicher baut veroeffentlichen.sh vor abhaengigkeiten(), also ohne PLAYWRIGHT_MODUL. Die
    Startprobe wurde darum auf dem Server übersprungen. deploy.sh nimmt dann die Kopie in <FR_DIENST>/playwright. Hier ist
    sie eine Attrappe, die beim Start des Browsers scheitert: Wird sie benutzt, endet deploy.sh mit 2 und nennt die Probe."""
    wurzel = tmp_path / "instanz"
    shutil.copytree(BEISPIEL, wurzel / "reisen" / "beispielreise")
    (wurzel / "engine").symlink_to(ENGINE)
    (wurzel / ".gitignore").write_text("dist/\n__pycache__/\n")
    git(wurzel, "init", "-q", "-b", "main")
    git(wurzel, "add", ".")
    git(wurzel, "commit", "-qm", "start")
    (tmp_path / "seiten").mkdir()
    modul = tmp_path / "dienst" / "playwright" / "node_modules" / "playwright" / "index.mjs"
    modul.parent.mkdir(parents=True)
    modul.write_text('export const chromium = {launch: async () => { throw new Error("Attrappe der Instanz benutzt"); }};\n')
    env = {k: v for k, v in SAUBER.items() if k != "PLAYWRIGHT_MODUL"}
    env.update({"FR_WURZEL": str(wurzel), "FR_INSTANZ": "probe", "FR_SEITEN": str(tmp_path / "seiten"),
                "FR_DIENST": str(tmp_path / "dienst"), "FR_PYTHON": sys.executable,
                "FR_GEPRUEFT": git(wurzel, "rev-parse", "HEAD").strip(), "FR_RM_PORT": "1", "FR_SUDO": "false"})
    if not shutil.which("node"):
        pytest.skip("node fehlt")
    r = subprocess.run([str(BETRIEB / "deploy.sh"), "beispielreise"], env=env, capture_output=True, text=True)
    assert r.returncode == 2, r.stdout + r.stderr
    assert "Attrappe der Instanz benutzt" in r.stdout + r.stderr
    assert not (tmp_path / "seiten" / "beispielreise").exists()


def test_deploy_prueft_die_wege_zum_konnektor_von_aussen(tmp_path):
    """Nach dem Deploy fragt deploy.sh jede Art Pfad des Konnektors über die öffentliche Adresse ab. Kommt ein Weg bei
    nginx statt beim Konnektor an (kein Kopf X-Frieda), warnt es im Protokoll (ohne Meldung, #445); die Seite wird trotzdem
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
        assert not meldungen.exists(), meldungen.read_text()   # #445: ein fehlender Ort ist kein Ausfall, keine Meldung
        assert (tmp_path / "seiten" / "beispielreise" / "index.html").exists()
        # Vom Veröffentlichen aufgerufen (FR_WEGE_SPAETER): keine Abfrage je Reise, das macht der Lauf einmal danach
        r = subprocess.run([str(BETRIEB / "deploy.sh"), "beispielreise"], env={**env, "FR_WEGE_SPAETER": "1"},
                           capture_output=True, text=True)
        assert r.returncode == 0 and "Warning: these paths" not in r.stdout and not meldungen.exists(), r.stdout + r.stderr
        fehlt.clear()
        r = subprocess.run([str(BETRIEB / "deploy.sh"), "beispielreise"], env=env, capture_output=True, text=True)
        assert r.returncode == 0 and "Warning: these paths" not in r.stdout and not meldungen.exists(), r.stdout + r.stderr
    finally:
        server.shutdown()


def test_veroeffentlichen_prueft_die_wege_einmal_nach_dem_freischalten(vf):
    """Die Wege zum Konnektor fragt das Veröffentlichen einmal je Lauf ab, nach dem Freischalten aller Reisen, nicht je
    Reise davor. Die Abrufe kommen vom Server selbst und zählen in nginx in dieselbe Begrenzung wie die Prüfung von
    freischalten.sh; je Reise abgefragt bekamen die letzten Reisen 429 (frieda-reist#163)."""
    ablauf = vf["tmp"] / "frei.log"
    ausfuehrbar(vf["tmp"] / "bin" / "curl", f'#!/bin/sh\nfor a; do u="$a"; done\necho "curl $u" >> {ablauf}\necho "X-Frieda: konnektor"\n')
    ausfuehrbar(vf["tmp"] / "bin" / "systemctl", '#!/bin/sh\ncase "$*" in *konnektor*) exit 0;; esac\nexit 1\n')
    r = vf["lauf"](FR_KN_ADRESSE="https://reisen.example.invalid", FR_HEARTBEAT_VEROEFFENTLICHEN="")
    assert r.returncode == 0, r.stdout + r.stderr
    assert vf["deploys"]() == ["beispielreise", "zweitreise"]
    zeilen = ablauf.read_text().split("\n")[:-1]
    assert zeilen[:2] == ["beispielreise", "zweitreise"], zeilen
    wege = [z.removeprefix("curl https://reisen.example.invalid") for z in zeilen[2:]]
    assert wege == ["/gesund", "/anmelden", "/kalender/" + "0" * 40 + ".ics", "/schrift/pruefung.woff2", "/favicon.svg",
                    "/manifest.webmanifest", "/sw.js", "/konto.js", "/info/pruefung.webp"], zeilen
    assert "Warning: these paths" not in r.stdout


def test_wegepruefung_wartet_bei_429_und_meldet_keinen_fehlenden_ort(tmp_path):
    """Ein fehlender Ort ist kein Ausfall und löst keine Meldung über FR_MELDEN aus (#445). 429 kommt von der Anfragebegrenzung in nginx (5/min auf /anmelden), nicht von einem fehlenden Ort: die Prüfung
    wartet und fragt erneut. Erst ein Weg ohne Kopf X-Frieda nach allen Versuchen gilt als fehlend (#279)."""
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    ausfuehrbar(bin_ / "systemctl", "#!/bin/sh\nexit 0\n")
    zaehler = tmp_path / "zaehler"
    meldungen = tmp_path / "meldungen.log"
    melden = ausfuehrbar(tmp_path / "melden.sh", f'#!/bin/sh\necho "$1|$2|$3" >> {meldungen}\n')

    def lauf(curl_text):
        zaehler.write_text("")
        ausfuehrbar(bin_ / "curl", curl_text)
        env = {**SAUBER, "PATH": f"{bin_}:{SAUBER.get('PATH', os.environ['PATH'])}", "FR_WURZEL": str(tmp_path),
               "FR_INSTANZ": "probe", "FR_KN_ADRESSE": "https://reisen.example.invalid", "FR_MELDEN": str(melden),
               "FR_WEGE_429_WARTEN": "0"}
        return subprocess.run(["bash", "-c", f'. "{BETRIEB}/gemeinsam.sh"; wege_pruefen'], env=env, capture_output=True, text=True)

    # /anmelden: dreimal 429, dann 200 mit Kopf: kein Alarm
    r = lauf(f'#!/bin/sh\nfor a; do u="$a"; done\ncase "$u" in */anmelden) echo x >> {zaehler}\n'
             f'[ $(wc -l < {zaehler}) -le 3 ] && {{ echo "HTTP/1.1 429 Too Many Requests"; exit 0; }};; esac\n'
             'echo "HTTP/1.1 200 OK"\necho "X-Frieda: konnektor"\n')
    assert r.returncode == 0 and "Warning" not in r.stdout and not meldungen.exists(), r.stdout + r.stderr
    assert len(zaehler.read_text().split()) == 4
    # Bleibt es bei 429, wird nach vier Versuchen gemeldet; ein Weg ohne Kopf und ohne 429 wird nicht wiederholt
    r = lauf(f'#!/bin/sh\nfor a; do u="$a"; done\ncase "$u" in */anmelden) echo x >> {zaehler}\n'
             'echo "HTTP/1.1 429 Too Many Requests"; exit 0;;\n'
             '*/sw.js) echo "HTTP/1.1 404 Not Found"; exit 0;; esac\necho "X-Frieda: konnektor"\n')
    assert "Warning: these paths do not reach the connector" in r.stdout and "/anmelden" in r.stdout and "/sw.js" in r.stdout
    assert len(zaehler.read_text().split()) == 4
    # Kein Ausfall: Die Warnzeile im Protokoll bleibt, Telegram/MQ bekommt nichts (#445, Meldeweg nur für Ausfälle).
    # Die Abweichung meldet nginx_abgleichen einmal als Issue, der Monitor der Instanz prüft sie als Warnung.
    assert not meldungen.exists(), meldungen.read_text()
    assert r.returncode == 0, r.stdout + r.stderr


def test_veroeffentlichen_installiert_neue_bibliotheken_vor_den_pruefungen(vf):
    """Ändert sich engine/requirements.txt, installiert das Veröffentlichen die Bibliotheken vor den Prüfungen, sonst
    nicht. Scheitert die Installation, endet der Lauf mit 1 ohne Prüfung und Bau; der nächste versucht es wieder (rot
    1.11.2026: eine neue Bibliothek fehlte nur auf dem Server)."""
    tmp, quelle = vf["tmp"], vf["tmp"] / "quelle"
    pip_log = tmp / "pip.log"
    pip = ausfuehrbar(tmp / "pip.sh", f'#!/bin/sh\ncat "$2" >> {pip_log}\n[ ! -e {tmp}/pip-kaputt ]\n')

    def liste(text):
        (quelle / "engine").mkdir(exist_ok=True)
        (quelle / "engine" / "requirements.txt").write_text(text)
        git(quelle, "add", ".")
        git(quelle, "commit", "-qm", "Bibliotheken")

    def pips():
        n = pip_log.read_text().split() if pip_log.exists() else []
        pip_log.unlink(missing_ok=True)
        return n

    liste("PyYAML\n")
    r = vf["lauf"](VF_PIP=str(pip))
    assert r.returncode == 0, r.stdout + r.stderr
    assert pips() == ["PyYAML"] and vf["deploys"]() == ["beispielreise", "zweitreise"]
    # Gleiche Liste: keine Installation
    r = vf["lauf"]("--immer", VF_PIP=str(pip))
    assert r.returncode == 0 and pips() == [], r.stdout + r.stderr
    # Neue Bibliothek, Installation scheitert: kein Test, kein Bau; der nächste Lauf versucht es wieder
    (tmp / "pruefen.log").unlink(missing_ok=True)
    vf["deploys"]()
    (tmp / "pip-kaputt").touch()
    liste("PyYAML\nneu-bibliothek\n")
    r = vf["lauf"](VF_PIP=str(pip))
    assert r.returncode == 1 and "cannot be installed" in r.stdout, r.stdout + r.stderr
    assert pips() == ["PyYAML", "neu-bibliothek"] and vf["deploys"]() == [] and not (tmp / "pruefen.log").exists()
    (tmp / "pip-kaputt").unlink()
    r = vf["lauf"](VF_PIP=str(pip))
    assert r.returncode == 0 and pips() == ["PyYAML", "neu-bibliothek"], r.stdout + r.stderr
    assert vf["deploys"]() == ["beispielreise", "zweitreise"]


def test_veroeffentlichen_installiert_playwright_fest_und_startet_dienste_einmal_neu(vf):
    """Playwright kommt in fester Version aus engine/tests/playwright in eine eigene Kopie unter FR_DIENST, nur wenn sich die
    Sperrdatei geändert hat; die Prüfungen bekommen PLAYWRIGHT_MODUL. Nach neuen Bibliotheken bekommt nur der erste
    Deploy des Laufs FR_BIBLIOTHEKEN_NEU (Dienste mit FR_PYTHON einmal neu starten), #202."""
    tmp, quelle, arbeit = vf["tmp"], vf["tmp"] / "quelle", vf["arbeit"]
    npm_log = tmp / "npm.log"
    npm = ausfuehrbar(tmp / "npm.sh", f'#!/bin/sh\necho "$PWD|$*" >> {npm_log}\n[ "$1" = ci ] && mkdir -p node_modules/playwright '
                                      f'&& touch node_modules/playwright/index.mjs\nexit 0\n')
    pip = ausfuehrbar(tmp / "pip.sh", "#!/bin/sh\nexit 0\n")
    # Deploy-Attrappe, die festhält, was sie mitbekommt
    seen = tmp / "seen.log"
    deploy = ausfuehrbar(tmp / "deploy-seen.sh", f'#!/bin/sh\necho "$1|${{FR_BIBLIOTHEKEN_NEU:-}}" >> {seen}\nexit 0\n')
    pruefen = ausfuehrbar(tmp / "pruefen-pw.sh", f'#!/bin/sh\necho "$1|${{PLAYWRIGHT_MODUL:-}}" >> {tmp}/pw.log\nexit 0\n')
    (quelle / "engine/tests/playwright").mkdir(parents=True)
    (quelle / "engine/tests/playwright/package.json").write_text('{"dependencies": {"playwright": "1.0.0"}}')
    (quelle / "engine/tests/playwright/package-lock.json").write_text("{}")
    (quelle / "engine/requirements.txt").write_text("PyYAML==6.0\n")
    git(quelle, "add", ".")
    git(quelle, "commit", "-qm", "Versionen")
    extra = dict(VF_NPM=str(npm), VF_PIP=str(pip), VF_DEPLOY=str(deploy), VF_PRUEFEN=str(pruefen))
    r = vf["lauf"](**extra)
    assert r.returncode == 0, r.stdout + r.stderr
    ziel = tmp / "dienst" / "playwright"
    aufrufe = npm_log.read_text().splitlines()
    assert [a.split("|")[1].split()[0] for a in aufrufe] == ["ci", "exec"] and all(a.split("|")[0] == str(ziel) for a in aufrufe), aufrufe
    assert "playwright install chromium webkit" in aufrufe[1]
    assert (ziel / "package-lock.json").exists() and (ziel / ".stand").exists()
    assert all(z.endswith(f"|{ziel}/node_modules/playwright/index.mjs") for z in (tmp / "pw.log").read_text().splitlines())
    assert seen.read_text().splitlines() == ["beispielreise|1", "zweitreise|"]
    # Nichts geändert: keine Installation, kein Neustart-Hinweis, PLAYWRIGHT_MODUL trotzdem gesetzt
    npm_log.unlink(); seen.unlink(); (tmp / "pw.log").unlink()
    r = vf["lauf"]("--immer", **extra)
    assert r.returncode == 0 and not npm_log.exists(), r.stdout + r.stderr
    assert seen.read_text().splitlines() == ["beispielreise|", "zweitreise|"]
    assert f"{ziel}/node_modules/playwright/index.mjs" in (tmp / "pw.log").read_text()
    # Ohne npm: Hinweis, kein Abbruch
    r = vf["lauf"]("--immer", **{**extra, "VF_NPM": str(tmp / "gibt-es-nicht")})
    assert r.returncode == 0 and "npm missing" in r.stdout, r.stdout + r.stderr
    assert git(arbeit, "status", "--porcelain").strip() == ""   # nichts im Bauordner


def test_veroeffentlichen_sperre_liegt_im_dienstordner(vf):
    """Die Sperre des Veröffentlichens liegt in FR_DIENST, nicht in FR_SPERREN: Der Schreibweg startet den Lauf aus einem
    Dienst mit privatem /tmp, eine Sperre dort sähe der Timer nicht (#211). Hält ein anderer Lauf sie, wird übersprungen."""
    import fcntl
    sperre = vf["tmp"] / "dienst" / "veroeffentlichen.lock"
    sperre.parent.mkdir(parents=True, exist_ok=True)
    with open(sperre, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        r = vf["lauf"](FR_SPERREN=str(vf["tmp"] / "anderes-tmp"))
    assert r.returncode == 0 and "Already running" in r.stdout, r.stdout + r.stderr
    assert vf["deploys"]() == []
    r = vf["lauf"](FR_SPERREN=str(vf["tmp"] / "anderes-tmp"))
    assert r.returncode == 0 and vf["deploys"]() == ["beispielreise", "zweitreise"]


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
    # Naht zu publish_status (#223): veroeffentlichen.sh holt den Grund aus den Zeilen „ - …“ dieser echten Ausgabe
    # (baugrund); ohne sie bliebe „fehlgeschlagen“ ohne Grund
    assert re.search(r"(?m)^ +- \S", r.stdout), r.stdout
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


def test_veroeffentlichen_roter_stand_heilt_sich_selbst(vf):
    """Ein bekannter roter Stand wird erneut geprüft, wenn sich die Umgebung geändert hat (alle Arten) oder rote Software
    seit mehr als FR_ROT_NEU_PRUEFEN_MINUTEN nicht geprüft wurde; seit und gemeldet bleiben. Eine alte Rot-Datei ohne
    Fingerabdruck wird einmal geprüft. Die Meldung nennt die roten Tests (#203)."""
    tmp = vf["tmp"]
    # Prüf-Attrappe, die wie pytest rote Tests ausgibt
    pruefen = ausfuehrbar(tmp / "pruefen-rot.sh", f'#!/bin/sh\necho p >> {tmp}/pruefen.log\n[ -e {tmp}/rot ] || exit 0\n'
                                                  'echo "E       ModuleNotFoundError: No module named neu"\n'
                                                  'echo "FAILED engine/tests/test_a.py::test_eins - ModuleNotFoundError"\n'
                                                  'echo "FAILED engine/tests/test_b.py::test_zwei[webkit] - Timeout"\nexit 1\n')
    (tmp / "rot").touch()
    lauf = lambda dt, umgebung="a", *args: vf["lauf"](*args, VF_JETZT=str(T0 + dt * 60), VF_UMGEBUNG=umgebung, VF_PRUEFEN=str(pruefen))
    assert lauf(0).returncode == 1
    rot = vf["rot"]()
    assert rot["art"] == "software" and rot["geprueft"] == str(T0) and rot["umgebung"]
    assert rot["tests"].startswith("engine/tests/test_a.py::test_eins, engine/tests/test_b.py::test_zwei[webkit] (first error: ")
    assert vf["zeilen"]("pruefen.log") == ["p"]
    # Gleiche Umgebung, 59 Minuten: überspringen; 31 Minuten Rot: Alarm mit den roten Tests
    r = lauf(31)
    assert r.returncode == 0 and "skipped" in r.stdout and vf["zeilen"]("pruefen.log") == ["p"]
    alarm = hoch(vf)
    assert len(alarm) == 1 and "test_a.py::test_eins" in alarm[0]
    assert lauf(59).returncode == 0 and vf["zeilen"]("pruefen.log") == ["p"]
    # Umgebung geändert: sofort neu prüfen, seit und gemeldet bleiben, kein zweiter Alarm
    r = lauf(60, "b")
    assert r.returncode == 1 and "checking again (environment changed)" in r.stdout, r.stdout
    assert vf["zeilen"]("pruefen.log") == ["p", "p"]
    rot = vf["rot"]()
    assert rot["seit"] == iso(T0) and rot["gemeldet"] == "1" and rot["geprueft"] == str(T0 + 3600) and len(hoch(vf)) == 1
    # Mehr als 60 Minuten seit der letzten Prüfung: neu prüfen; genau 60: noch nicht
    assert lauf(120, "b").returncode == 0 and vf["zeilen"]("pruefen.log") == ["p", "p"]
    r = lauf(121, "b")
    assert r.returncode == 1 and "more than 60 minutes" in r.stdout and vf["zeilen"]("pruefen.log") == ["p", "p", "p"]
    # Ursache in der Umgebung behoben, Umgebung geändert: grün, Rot-Datei weg
    (tmp / "rot").unlink()
    vf["deploys"]()
    assert lauf(125, "c").returncode == 0 and vf["rot"]() is None
    assert vf["deploys"]() == ["beispielreise", "zweitreise"]


def test_veroeffentlichen_rote_reise_nur_bei_neuer_umgebung_erneut(vf):
    """Eine rote Reise (Inhalt) wird nicht nach Zeit erneut geprüft, nur bei geänderter Umgebung; eine Rot-Datei von vor
    #203 (ohne Fingerabdruck) wird einmal geprüft, dann übersprungen."""
    tmp = vf["tmp"]
    (tmp / "kaputt-beispielreise").touch()
    lauf = lambda dt, umgebung="a": vf["lauf"](VF_JETZT=str(T0 + dt * 60), VF_UMGEBUNG=umgebung)
    assert lauf(0).returncode == 1
    vf["deploys"]()
    assert lauf(300).returncode == 0 and vf["deploys"]() == []
    assert lauf(301, "b").returncode == 1 and vf["deploys"]() == ["beispielreise", "zweitreise"]
    # Alte Rot-Datei: ohne umgebung und geprueft
    datei = tmp / "dienst" / "veroeffentlichen-rot"
    alt = "".join(z + "\n" for z in datei.read_text().splitlines() if not z.startswith(("umgebung=", "geprueft=", "tests=")))
    datei.write_text(alt)
    assert lauf(302, "b").returncode == 1 and vf["deploys"]() == ["beispielreise", "zweitreise"]
    assert lauf(303, "b").returncode == 0 and vf["deploys"]() == []


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


def test_sb_module_deckt_die_importe_des_schreibwegs():
    """Stufe 2 (#347, AC-22): Der Unterprozess `anwenden` läuft mit dem Code aus <FR_DIENST>, nicht mehr mit dem einer
    Git-Arbeitskopie. Deshalb muss SB_MODULE jedes eigene Modul enthalten, das schreiben.py lädt, auch in Funktionen
    (Probebau: bauen, routen …; Werkzeuge: neu, schnittstelle …), samt reisespeicher.py und den Modulen des Git-Wegs."""
    kopiert = _deploy_liste("SB_MODULE")
    offen, gesehen = ["schreiben.py"], set()
    while offen:
        d = offen.pop()
        gesehen.add(d)
        offen += [m for m in _eigene_importe(d) if m not in gesehen]
    assert {"reisespeicher.py", "bauen.py", "routen.py", "schreiben_git.py", "stand_git.py"} <= gesehen
    fehlt = gesehen - kopiert
    assert not fehlt, f"deploy.sh SB_MODULE kopiert nicht: {sorted(fehlt)}"
    assert (ENGINE / "stand_git.py").exists() and "stand_git.py" in kopiert


def test_deploy_kopiert_friedas_symbol():
    deploy = (BETRIEB / "deploy.sh").read_text(encoding="utf-8")
    assert '"$WURZEL/engine/marke/" "$DIENST/marke/"' in deploy
    assert '"$WURZEL/engine/app/" "$DIENST/app/"' in deploy      # Frieda-App (#21)


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
           "FS_WARTEN": "0", "FS_429_WARTEN": "0"}

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


def test_freischalten_wartet_bei_429_auf_die_anfragebegrenzung(fs):
    """429 kommt von der Begrenzung in nginx, nicht von der Reise: warten und erneut fragen, auch beim bestehenden
    Link (#198, beim Veröffentlichen am 1. und 2.11.2026 blieben dadurch neue Reisen unverknüpft)."""
    zaehler = fs["tmp"] / "zaehler"
    fs["env"]["FS_ABRUF"] = str(ausfuehrbar(fs["tmp"] / "abruf-429.sh",
        f'#!/bin/sh\necho x >> {zaehler}\n[ $(wc -l < {zaehler}) -le 3 ] && echo 429 || echo 200\n'))
    assert fs["lauf"]("beispielreise").returncode == 0
    zaehler.unlink()
    r = fs["lauf"]("beispielreise")                      # bestehender Link: nur ein Versuch, 429 zählt nicht
    assert r.returncode == 0, r.stdout
    assert len(zaehler.read_text().split()) == 5        # dreimal 429, dann Seite und Rückmeldedienst
    # Bleibt es bei 429, ist es nach den Wartezeiten ein Fehler mit dem Code
    zaehler.unlink()
    fs["env"]["FS_ABRUF"] = str(ausfuehrbar(fs["tmp"] / "abruf-immer-429.sh", f'#!/bin/sh\necho x >> {zaehler}\necho 429\n'))
    r = fs["lauf"]("beispielreise")
    assert r.returncode == 1 and "answers with 429" in r.stdout
    assert len(zaehler.read_text().split()) == 7         # ein Versuch und sechs Wiederholungen


def test_freischalten_kennt_keine_links_fuer_die_claude_app(fs):
    """Links je Person für die Claude-App sind abgeschafft (#421): --person lehnt das Skript ab, ohne etwas zu tun."""
    r = fs["lauf"]("beispielreise", "--person", "ida")
    assert r.returncode == 1 and "no longer exist" in r.stdout and "Claude-App" not in r.stdout
    assert not (fs["tmp"] / "konnektor/zugaenge.json").exists()


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


def test_freischalten_unerwarteter_abbruch_nennt_die_stelle(fs):
    """Scheitert ein Befehl ohne eigene Meldung (set -e), steht trotzdem eine ERROR-Zeile mit Zeile und Befehl im
    Protokoll: veroeffentlichen.sh zeigt nur ERROR-Zeilen, sonst stand dort „not released“ ohne Grund (#465). Ohne Link."""
    (fs["tmp"] / "konnektor").write_text("kein Ordner")     # seiten.json lässt sich nicht schreiben
    r = fs["lauf"]("beispielreise")
    assert r.returncode != 0
    fehler = [z for z in r.stdout.splitlines() if z.startswith("ERROR:")]
    assert len(fehler) == 1 and re.search(r"line \d+", fehler[0]) and "python3" in fehler[0], r.stdout
    token = (fs["snippets"] / "probe-beispielreise.conf").read_text().split("beispielreise-", 1)[1][:24]
    assert token not in r.stdout and "Seite:" not in r.stdout


def test_freischalten_ohne_root_rechte_bricht_ab_statt_einen_neuen_link_anzulegen(fs):
    """Geht sudo nicht (NoNewPrivileges im Schreibweg, #465), scheiterte schon „sudo test -e“; das las sich als „Baustein
    fehlt“, und die Reise bekam beinahe einen neuen geheimen Link. Jetzt: eigene ERROR-Zeile, nichts geändert."""
    assert fs["lauf"]("beispielreise").returncode == 0
    sn = fs["snippets"] / "probe-beispielreise.conf"
    vorher = sn.read_text()
    (fs["tmp"] / "nginx.log").unlink()
    r = subprocess.run([str(BETRIEB / "freischalten.sh"), "beispielreise"], capture_output=True, text=True,
                       env={**fs["env"], "FR_SUDO": "false"})
    assert r.returncode == 1 and "ERROR: no root rights here" in r.stdout and "Seite:" not in r.stdout, r.stdout
    assert sn.read_text() == vorher and list(fs["snippets"].iterdir()) == [sn]
    assert not (fs["tmp"] / "nginx.log").exists()


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
    monkeypatch.setenv("KN_BASIS", "https://example.invalid/mcp")


def test_ausstehende_links_zustellen(fs, monkeypatch, capsys):
    """Eine neue Reise wird zugestellt, sobald ihre Seite veröffentlicht ist; Unveröffentlichtes wartet. Eine ältere Anfrage
    ohne Konto (aus der Zeit der Links) wird nur freigeschaltet und gemeldet, ohne Link für die Claude-App (#421)."""
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
    assert "Seite: https://example.invalid/beispielreise-" in m["text"] and "https://example.invalid/mcp/" not in m["text"]
    assert m["t"] == [["konto.meldungen.text.neue_reise", {"titel": "Beispielreise – Malerweg in vier Tagen"}]]   # #407: ohne Adresse
    assert not (fs["tmp"] / "konnektor/zugaenge.json").exists()      # eine Anfrage ohne Konto bekommt keinen App-Link (#421)
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
    assert rm.meldungen(rm.ordner_neu(), "Ida") == []        # nie an den Namen: den wählt jedes Konto frei
    m = rm.meldungen(rm.ordner_neu(), ida["id"])[-1]
    assert meldet(m["text"], "dienst.zustellen.konto") and "Einladung per Mail an 1 Person" in m["text"]
    assert "https://example.invalid/mcp/" not in m["text"]                  # kein App-Link
    assert m["t"] == [["konto.meldungen.text.neue_reise", {"titel": "Beispielreise – Malerweg in vier Tagen"}],
                      ["konto.meldungen.text.einladungen", {"n": 1}]]


# ---------- Wächter-Lauf ----------

@pytest.fixture
def wa(tmp_path):
    """Attrappe für Python (schreibt den Bericht, wenn WA_BERICHT gesetzt ist) und für den Meldeweg."""
    ausfuehrbar(tmp_path / "python", f'''#!/bin/sh
# Aufruf: python engine/waechter.py lauf --bericht DATEI, danach python engine/konten.py sichern und
# python engine/reisespeicher.py sichern; WA_SICHERN_FEHLER nennt die Module, deren Sicherung scheitert
if [ "$2" = sichern ]; then
  echo "${{1##*/}}" >> {tmp_path}/gesichert
  case " $WA_SICHERN_FEHLER " in *" ${{1##*/}} "*) exit 2;; esac
  exit 0
fi
[ -z "$WA_FEHLER" ] || exit 3
[ -z "$WA_BERICHT" ] || printf '%s\\n' "$WA_BERICHT" > "$4"
exit 0
''')
    ausfuehrbar(tmp_path / "melden.sh", f'#!/bin/sh\nprintf "%s|%s|%s|%s\\n" "$1" "$2" "$3" "$4" >> {tmp_path}/nachrichten\n')
    (tmp_path / "quelle").mkdir()

    def lauf(**umgebung):
        env = {**SAUBER, "FR_WURZEL": str(tmp_path / "quelle"), "FR_PYTHON": str(tmp_path / "python"),
               "FR_DIENST": str(tmp_path / "dienst"), "FR_MELDEN": str(tmp_path / "melden.sh"), "FR_TITEL": "Probe",
               "WA_BERICHT": "", "WA_FEHLER": "", "WA_SICHERN_FEHLER": "", **umgebung}
        r = subprocess.run([str(BETRIEB / "waechter.sh")], capture_output=True, text=True, env=env)
        nachrichten = tmp_path / "nachrichten"
        return r, nachrichten.read_text().splitlines() if nachrichten.exists() else []
    lauf.stempel = tmp_path / "dienst" / "waechter-erfolg"
    lauf.gesichert = tmp_path / "gesichert"
    return lauf


def test_waechter_ohne_neues_keine_nachricht(wa):
    r, nachrichten = wa()
    assert r.returncode == 0 and nachrichten == [] and wa.stempel.exists()
    # täglicher Schnappschuss der Konten (#72) und des Reisespeichers (#346); die Reihenfolge ist nicht festgelegt
    assert sorted(wa.gesichert.read_text().split()) == ["konten.py", "reisespeicher.py"]


def test_waechter_sicherung_fehlgeschlagen_meldet_sich(wa):
    r, nachrichten = wa(WA_SICHERN_FEHLER="konten.py")
    assert r.returncode == 1 and not wa.stempel.exists()
    assert len(nachrichten) == 1 and nachrichten[0].startswith("high|") and "Account backup" in nachrichten[0]
    assert "reisespeicher.py" in wa.gesichert.read_text().split()      # die andere Sicherung läuft trotzdem


def test_waechter_reisen_sicherung_fehlgeschlagen_meldet_sich(wa):
    """#346: Scheitert die Sicherung des Reisespeichers, meldet der Wächter dringend; die Konten werden trotzdem gesichert."""
    r, nachrichten = wa(WA_SICHERN_FEHLER="reisespeicher.py")
    assert r.returncode == 1 and not wa.stempel.exists()
    assert len(nachrichten) == 1 and nachrichten[0].startswith("high|")
    assert "konten.db" not in nachrichten[0] and "reisen.db" in nachrichten[0]
    assert sorted(wa.gesichert.read_text().split()) == ["konten.py", "reisespeicher.py"]


def test_waechter_beide_sicherungen_fehlgeschlagen(wa):
    r, nachrichten = wa(WA_SICHERN_FEHLER="konten.py reisespeicher.py")
    assert r.returncode == 1 and len(nachrichten) == 2 and all(n.startswith("high|") for n in nachrichten)


def test_waechter_fehler_sichert_trotzdem(wa):
    r, _ = wa(WA_FEHLER="1")
    assert r.returncode == 1 and wa.gesichert.exists()


def test_waechter_bericht_geht_als_sammelnachricht_und_ist_erledigt(wa):
    r, nachrichten = wa(WA_BERICHT="Beispiel: Karl: Frist morgen.")
    assert r.returncode == 0 and len(nachrichten) == 1
    prio, betreff, text, erledigt = nachrichten[0].split("|", 3)
    assert (prio, erledigt) == ("normal", "erledigt") and betreff == "Probe: Watchdog and reminders"
    assert "Karl: Frist morgen." in text


def test_waechter_ohne_meldeweg_keine_nachricht(wa):
    r, nachrichten = wa(WA_BERICHT="Beispiel: Karl: Frist morgen.", FR_MELDEN="")
    assert r.returncode == 0 and nachrichten == []


@pytest.mark.parametrize("scheitert, rc", [("", 0), ("konten.py", 1), ("reisespeicher.py", 1),
                                           ("konten.py reisespeicher.py", 1)])
def test_sichern_fuer_das_backup(wa, tmp_path, scheitert, rc):
    """#506: betrieb/sichern.sh schreibt beide Schnappschüsse frisch, unmittelbar vor dem Server-Backup; es versucht
    immer beide, meldet einen Fehler nur über den Exit (das Backup pingt dann keinen Heartbeat), nie über den Meldeweg."""
    env = {**SAUBER, "FR_WURZEL": str(tmp_path / "quelle"), "FR_PYTHON": str(tmp_path / "python"),
           "FR_DIENST": str(tmp_path / "dienst"), "FR_MELDEN": str(tmp_path / "melden.sh"), "WA_SICHERN_FEHLER": scheitert}
    r = subprocess.run([str(BETRIEB / "sichern.sh")], capture_output=True, text=True, env=env)
    assert r.returncode == rc, r.stderr
    assert sorted(wa.gesichert.read_text().split()) == ["konten.py", "reisespeicher.py"]
    assert not (tmp_path / "nachrichten").exists() and not wa.stempel.exists()
    assert ("failed" in r.stderr) == bool(scheitert)


def test_waechter_fehler_meldet_sich_und_laesst_den_stempel_aus(wa):
    r, nachrichten = wa(WA_FEHLER="1")
    assert r.returncode == 1 and not wa.stempel.exists()
    assert len(nachrichten) == 1 and nachrichten[0].split("|")[0] == "high" and "failed" in nachrichten[0]
    assert nachrichten[0].endswith("|")    # Fehler bleiben offen


# ---------- Meldeweg nur für Ausfälle (#446) ----------

# Jede Stelle, die einen Alarm der Stufe high auslöst (Telegram beim Betreiber), mit Begründung, warum sie ein Ausfall ist, bei
# dem jemand jetzt handeln muss und kann. Eine neue Stelle kommt nur mit Begründung hierher; sonst normal (Issue), Warnzeile im
# Protokoll oder Teil-Check in monitor.sh der Infrastruktur (CLAUDE.md, docs/betrieb.md „Meldeweg“).
ALARMSTELLEN = {
    ("waechter.sh", "Watchdog failed"): "keine neuen Meldungen an Personen, abgelaufene Reisen bleiben liegen",
    ("waechter.sh", "Account backup failed"): "Sicherung der Konten veraltet, Datenverlust beim nächsten Schaden",
    ("waechter.sh", "Trip store backup failed"): "Sicherung des Reisespeichers veraltet, Datenverlust beim nächsten Schaden",
    ("veroeffentlichen.sh", "Publishing red for $minuten minutes"): "Reiseseiten bleiben seit mindestens 30 Minuten alt",
}
# Nur diese Funktionen rufen FR_MELDEN direkt auf; alle anderen Stellen gehen über sie.
SENDER = {("gemeinsam.sh", "fr_melden"), ("gemeinsam.sh", "fr_alarm"), ("veroeffentlichen.sh", "alarm_senden")}


def _meldestellen():
    """-> (alarme {(datei, betreff)}, direkte {(datei, funktion)}, stufen [(datei, zeile)] ohne feste Stufe)."""
    alarme, direkte, ohne_stufe = set(), set(), []
    for pfad in sorted(BETRIEB.rglob("*")):
        if not pfad.is_file() or pfad.suffix not in ("", ".sh", ".py", ".inc", ".env", ".beispiel"):
            continue
        funktion = None
        for zeile in pfad.read_text(encoding="utf-8", errors="replace").splitlines():
            code = zeile.split(" #", 1)[0] if not zeile.lstrip().startswith("#") else ""
            if m := re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)\(\)\s*\{", code):
                funktion = m.group(1)
                continue
            if m := re.search(r'\bfr_melden\s+(\S+)\s+"([^"]*)"', code):
                if m.group(1) not in ("normal", "high"):
                    ohne_stufe.append((pfad.name, zeile.strip()))
                elif m.group(1) == "high":
                    alarme.add((pfad.name, m.group(2)))
            if m := re.search(r'\bfr_alarm\s+\S+\s+"([^"]*)"', code):
                alarme.add((pfad.name, m.group(1)))
            if m := re.search(r'\balarm_senden\s+"([^"]*)"', code):
                alarme.add((pfad.name, m.group(1)))
            if re.search(r'(^\s*|\b(if|then|else|do|exec|timeout\s+\d+)\s+|[;&|]\s*|\$\(\s*)"\$FR_MELDEN"\s', code):
                direkte.add((pfad.name, funktion))
    return alarme, direkte, ohne_stufe


def test_alarmstellen_sind_begruendet():
    """#446: Jede high-Stelle in betrieb/ steht mit Begründung in ALARMSTELLEN; eine neue macht diesen Test rot."""
    alarme, _, ohne_stufe = _meldestellen()
    assert alarme == set(ALARMSTELLEN), (
        f"neu, ohne Begründung: {sorted(alarme - set(ALARMSTELLEN))}; nicht mehr da: {sorted(set(ALARMSTELLEN) - alarme)}")
    assert ohne_stufe == [], f"fr_melden ohne feste Stufe normal|high: {ohne_stufe}"


def test_fr_melden_nur_ueber_die_senderfunktionen():
    """#446: FR_MELDEN wird nur in fr_melden, fr_alarm und alarm_senden aufgerufen; engine/ und werkzeuge/ nie."""
    _, direkte, _ = _meldestellen()
    assert direkte == SENDER
    for ordner in ("engine", "werkzeuge"):
        for pfad in (WURZEL / ordner).rglob("*.py"):
            if "tests" in pfad.parts or ".venv" in pfad.parts or "vendor" in pfad.parts:
                continue
            assert "FR_MELDEN" not in pfad.read_text(encoding="utf-8", errors="replace"), pfad


def test_alarmstellen_test_erkennt_neue_stelle(tmp_path, monkeypatch):
    """#446: Der Bestandstest schlägt an, wenn eine neue high-Stelle oder ein direkter Aufruf dazukommt."""
    kopie = tmp_path / "betrieb"
    shutil.copytree(BETRIEB, kopie, ignore=shutil.ignore_patterns("__pycache__"))
    (kopie / "neu.sh").write_text('#!/bin/sh\nprobe() {\n  fr_melden high "Something odd" "x"\n  "$FR_MELDEN" high a b\n}\n')
    monkeypatch.setitem(globals(), "BETRIEB", kopie)
    alarme, direkte, _ = _meldestellen()
    assert ("neu.sh", "Something odd") in alarme and ("neu.sh", "probe") in direkte


def test_waechter_alarm_einmal_je_stoerung(wa):
    """#446 AC-2/AC-3: Dieselbe gescheiterte Sicherung meldet in zwei Läufen nur einmal; nach Erfolg meldet eine neue
    Störung wieder."""
    _, n1 = wa(WA_SICHERN_FEHLER="konten.py")
    r, n2 = wa(WA_SICHERN_FEHLER="konten.py")
    assert r.returncode == 1 and len(n1) == 1 and n2 == n1     # zweiter Lauf: kein neuer Alarm
    r, n3 = wa()
    assert r.returncode == 0 and n3 == n1 and wa.stempel.exists()
    _, n4 = wa(WA_SICHERN_FEHLER="konten.py")
    assert len(n4) == 2 and n4[1].startswith("high|") and "Account backup" in n4[1]


def test_waechter_alarm_ohne_zustellung_wird_wiederholt(wa, tmp_path):
    """#446 AC-4: Scheitert der Meldeweg, bleibt kein Merker; der nächste Lauf versucht es wieder."""
    ausfuehrbar(tmp_path / "scheitert.sh", "#!/bin/sh\nexit 1\n")
    wa(WA_SICHERN_FEHLER="konten.py", FR_MELDEN=str(tmp_path / "scheitert.sh"))
    assert not list((tmp_path / "dienst").glob("alarm-*"))
    _, nachrichten = wa(WA_SICHERN_FEHLER="konten.py")
    assert len(nachrichten) == 1 and "Account backup" in nachrichten[0]


def test_waechter_alarm_ohne_meldeweg_kein_merker(wa, tmp_path):
    """#446 AC-5: Ohne Meldeweg nichts senden und keinen Merker anlegen."""
    r, nachrichten = wa(WA_FEHLER="1", FR_MELDEN="")
    assert r.returncode == 1 and nachrichten == [] and not list((tmp_path / "dienst").glob("alarm-*"))


def test_waechter_alarme_je_teil_unabhaengig(wa):
    """#446 AC-6: Die Merker der drei Teile sind getrennt."""
    _, n1 = wa(WA_SICHERN_FEHLER="konten.py")
    _, n2 = wa(WA_SICHERN_FEHLER="konten.py", WA_FEHLER="1")
    assert len(n2) == 2 and "Watchdog failed" in n2[1]
    _, n3 = wa(WA_SICHERN_FEHLER="konten.py reisespeicher.py", WA_FEHLER="1")
    assert len(n3) == 3 and "Trip store backup" in n3[2]


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
    assert namen == ["probe-konnektor.service", "probe-push.service", "probe-rueckmeldungen.service", "probe-schreiben.service",
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
    # Tests der Software (CI 16 bis 19 min, Server mit Nice=10 und Last länger), Bau und Deploy in einem Lauf (#258)
    grenze = re.search(r"^TimeoutStartSec=(\d+)min$", einh["probe-veroeffentlichen.service"], re.M)
    assert grenze and int(grenze.group(1)) >= 45, "TimeoutStartSec des Veröffentlichens zu knapp"
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
    nginx = (aus / "nginx/probe-konnektor-orte.inc").read_text()
    inc = (aus / "nginx/probe-konnektor.inc").read_text()
    # Konnektor an der Wurzel (#163): /mcp, Anmeldung, OAuth; der alte Pfad bleibt für Links aus der Zeit vor den Konten
    assert "location = /mcp" in nginx and "location = /anmelden" in nginx and "location = /token" in nginx
    assert "location ~ ^/(?:konto|abmelden|authorize|gesund)?$" in nginx    # /info/ (Infoseite, #440) über den Ort der Bilder
    assert "location ^~ /.well-known/oauth-" in nginx and "location ^~ /schrift/" in nginx and "location ^~ /info/" in nginx and "location = /favicon.ico" in nginx
    assert "zone=probe_konto" in nginx
    # die Links aus der Zeit vor den Konten sind auf dem Server abgeschaltet: die Vorlage öffnet sie nicht wieder (#206)
    assert "probe-mcp" not in nginx and "A-Za-z0-9_-" not in nginx
    assert "include /etc/nginx/snippets/probe-konnektor.inc;" in nginx
    assert "proxy_pass http://127.0.0.1:8772;" in inc
    # Der Dienst setzt Referrer-Policy „same-origin“; „no-referrer“ von nginx ließe Browser „Origin: null“ schicken
    assert "add_header Referrer-Policy" not in nginx + inc
    assert "zone=probe_konto:1m" in (aus / "nginx/probe-zone.conf").read_text()
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
    for n in ("probe-konnektor-orte.inc", "probe-konnektor.inc"):
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
    include {snippets}/probe-konnektor-orte.inc;
    include {snippets}/probe-*.conf;   # Reise-Bausteine; der Konnektor-Baustein endet auf .inc und fehlt hier bewusst
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
                     "/icon-192.png", "/manifest.webmanifest", "/sw.js", "/konto.js", "/", "/info/reise-de.webp"):
            assert hol(pfad)[:2] == (200, pfad), pfad
        # Links aus der Zeit vor den Konten bleiben abgeschaltet, wie auf dem Server (#206)
        assert hol("/probe-mcp/" + "t" * 32)[0] == 404 and hol("/" + "t" * 32)[0] == 404
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
    # FR_BETREIBER war der Betreiber des KI-Laufs; FR_BETREIBER_NAME/_ANSCHRIFT/_KONTAKT sind die Angaben fürs Impressum (#383)
    assert "FR_CLAUDE" not in beispiel and not re.search(r"^#?FR_BETREIBER=", beispiel, re.M)


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
    assert instanz.konnektor() == Path("/srv/frieda/_konnektor") and "frieda-reist" in instanz.kennung()
    monkeypatch.setenv("KN_ZUGAENGE", "/srv/alt/_konnektor/zugaenge.json")      # ältere Unit: ihr Ordner gilt (#421)
    assert instanz.konnektor() == Path("/srv/alt/_konnektor")
    monkeypatch.setenv("FR_KONNEKTOR", "/srv/neu/_konnektor")
    assert instanz.konnektor() == Path("/srv/neu/_konnektor")
    monkeypatch.delenv("KN_ZUGAENGE")
    monkeypatch.delenv("FR_KONNEKTOR")
    # Einstellungen der Instanz im aktuellen Ordner (Aufruf von Hand im Reisen-Repo)
    (tmp_path / "betrieb").mkdir()
    (tmp_path / "betrieb/einstellungen.env").write_text("# x\nFR_INSTANZ=probe\nFR_KENNUNG=\"Probe/1 (ida@example.org)\"\n")
    assert instanz.seiten() == Path("/srv/probe") and instanz.ablage() == Path("/srv/probe/_rueckmeldungen")
    assert instanz.kennung() == "Probe/1 (ida@example.org)"
    # ein Dienst, der nur die Ablage kennt, findet die Seiten daneben
    monkeypatch.chdir("/")
    monkeypatch.setenv("RM_ABLAGE", "/srv/andere/_rueckmeldungen")
    assert instanz.seiten() == Path("/srv/andere") and instanz.konnektor() == Path("/srv/andere/_konnektor")
    # ausdrücklich gesetzte Werte gelten
    monkeypatch.setenv("KN_SEITEN", "/x/seiten")
    monkeypatch.setenv("FR_KONNEKTOR", "/x/k")
    assert instanz.seiten() == Path("/x/seiten") and instanz.konnektor() == Path("/x/k")
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


# ---------- Einheiten abgleichen beim Veröffentlichen (#260, test_units.py prüft den Abgleich selbst) ----------

def test_veroeffentlichen_meldet_unit_abweichung_einmal_je_fingerabdruck_und_bleibt_gruen(vf):
    stub = ausfuehrbar(vf["tmp"] / "units.sh", '#!/bin/sh\necho "probe-konnektor.service: allowed, add [Service] Environment=FR_ZEITZONE=UTC"\nexit 3\n')
    assert vf["lauf"](VF_UNITS=str(stub)).returncode == 0
    meldungen = [z for z in vf["zeilen"]("melden.log") if z.startswith("normal|")]
    assert len(meldungen) == 1 and "FR_ZEITZONE" in meldungen[0]
    vf["neuer_commit"]()
    assert vf["lauf"](VF_UNITS=str(stub)).returncode == 0
    assert len([z for z in vf["zeilen"]("melden.log") if z.startswith("normal|")]) == 1   # gleiche Abweichung: keine zweite Meldung


def _units_attrappe(vf, nach_installieren):
    """Attrappe für units.py: pruefen endet mit 3, nach installieren mit nach_installieren (Zahl, Ausgabe wie ein echter Rest)."""
    marker = vf["tmp"] / "installiert"
    protokoll = vf["tmp"] / "units-aufrufe.log"
    return ausfuehrbar(vf["tmp"] / "units-install.sh",
                       f'#!/bin/sh\necho "$1" >> {protokoll}\n'
                       f'if [ "$1" = installieren ]; then touch {marker}; exit 0; fi\n'
                       f'if [ -e {marker} ]; then [ {nach_installieren} -ne 0 ] && echo "probe-waechter.service: BLOCKED, rest"; exit {nach_installieren}; fi\n'
                       f'echo "probe-konnektor.service: allowed, add [Service] Environment=FR_ZEITZONE=UTC"\nexit 3\n'), protokoll


def test_veroeffentlichen_installiert_erlaubte_abweichungen_und_meldet_nichts(vf):
    stub, protokoll = _units_attrappe(vf, 0)
    assert vf["lauf"](VF_UNITS=str(stub)).returncode == 0
    assert protokoll.read_text().split() == ["pruefen", "installieren", "pruefen"]
    assert not [z for z in vf["zeilen"]("melden.log") if z.startswith("normal|")]


def test_veroeffentlichen_meldet_nur_den_rest_nach_dem_installieren(vf):
    stub, protokoll = _units_attrappe(vf, 4)
    assert vf["lauf"](VF_UNITS=str(stub)).returncode == 0
    meldungen = [z for z in vf["zeilen"]("melden.log") if z.startswith("normal|")]
    assert len(meldungen) == 1 and "BLOCKED" in meldungen[0] and "FR_ZEITZONE" not in meldungen[0]


def test_veroeffentlichen_unit_abgleich_fehler_stoppt_nichts(vf):
    stub = ausfuehrbar(vf["tmp"] / "units.sh", "#!/bin/sh\necho boom >&2\nexit 1\n")
    assert vf["lauf"](VF_UNITS=str(stub)).returncode == 0
    assert vf["pings"]() == 1
    assert not hoch(vf)


# ---------- nginx-Bausteine abgleichen beim Veröffentlichen (#206, test_nginx.py prüft den Abgleich selbst) ----------

def test_veroeffentlichen_meldet_nginx_abweichung_einmal_je_fingerabdruck_nach_installationsversuch(vf):
    """#445, Teil 3: erst Installationsversuch (nginx.py installieren), dann erneut prüfen; der Rest wird einmal gemeldet."""
    protokoll = vf["tmp"] / "nginx-aufrufe.log"
    stub = ausfuehrbar(vf["tmp"] / "nginx.sh", f'#!/bin/sh\necho "$@" >> {protokoll}\n'
                       'echo "probe-zone.conf differs"\necho "sudo install -m 644 x /etc/nginx/conf.d/"\nexit 3\n')
    assert vf["lauf"](VF_NGINX=str(stub)).returncode == 0
    log = vf["zeilen"]("melden.log")       # der Text der Meldung ist mehrzeilig
    assert len([z for z in log if z.startswith("normal|")]) == 1
    assert "probe-zone.conf differs" in "\n".join(log) and any(z.startswith("sudo install") for z in log)
    assert any(z.startswith("Install attempt:") for z in log)
    assert protokoll.read_text().split() == ["pruefen", "installieren", "pruefen"]
    vf["neuer_commit"]()
    assert vf["lauf"](VF_NGINX=str(stub)).returncode == 0
    assert len([z for z in vf["zeilen"]("melden.log") if z.startswith("normal|")]) == 1
    assert not hoch(vf)


def _nginx_attrappe(vf, nach_installieren, installieren_text="installed"):
    """Attrappe für nginx.py: pruefen endet mit 3; installieren gibt installieren_text aus (mit $$, also je Lauf anders, wenn
    gewünscht) und endet mit 0 oder 5; danach endet pruefen mit nach_installieren."""
    marker = vf["tmp"] / "nginx-installiert"
    protokoll = vf["tmp"] / "nginx-aufrufe.log"
    return ausfuehrbar(vf["tmp"] / "nginx-install.sh",
                       f'#!/bin/sh\necho "$1" >> {protokoll}\n'
                       f'if [ "$1" = installieren ]; then touch {marker}; echo "{installieren_text}"; '
                       f'[ {nach_installieren} -eq 0 ] && exit 0; exit 5; fi\n'
                       f'if [ -e {marker} ] && [ {nach_installieren} -eq 0 ]; then exit 0; fi\n'
                       f'echo "probe-konnektor-orte.inc: differs from the template"\nexit 3\n'), protokoll


def test_veroeffentlichen_installiert_nginx_orte_und_meldet_nichts(vf):
    """AC-16: Erfolg des Versuchs: nur eine Protokollzeile, keine Meldung, Merker gelöscht."""
    merker = vf["tmp"] / "dienst" / "nginx-gemeldet"
    merker.parent.mkdir(parents=True, exist_ok=True)
    merker.write_text("alter-fingerabdruck\n")
    stub, protokoll = _nginx_attrappe(vf, 0)
    r = vf["lauf"](VF_NGINX=str(stub))
    assert r.returncode == 0, r.stdout + r.stderr
    assert protokoll.read_text().split() == ["pruefen", "installieren", "pruefen"]
    assert not [z for z in vf["zeilen"]("melden.log") if z.startswith(("normal|", "high|"))]
    assert not merker.exists()


def test_veroeffentlichen_nginx_versuch_scheitert_eine_meldung_je_fingerabdruck(vf):
    """AC-17: Der Fingerabdruck kommt nur aus der zweiten Prüfung; ein je Lauf anderes Versuchsergebnis meldet nicht erneut."""
    stub, _ = _nginx_attrappe(vf, 3, installieren_text="helper exit 4 at $$")
    assert vf["lauf"](VF_NGINX=str(stub)).returncode == 0
    log = vf["zeilen"]("melden.log")
    assert len([z for z in log if z.startswith("normal|")]) == 1
    assert any(z.startswith("Install attempt: helper exit 4 at") for z in log)
    vf["neuer_commit"]()
    assert vf["lauf"](VF_NGINX=str(stub)).returncode == 0
    assert len([z for z in vf["zeilen"]("melden.log") if z.startswith("normal|")]) == 1
    assert not hoch(vf)


def test_veroeffentlichen_nginx_ohne_hilfsprogramm_meldet_einmal(vf):
    """AC-18: Ohne Hilfsprogramm enthält die eine Meldung die Zeile „Install attempt: helper missing (<Pfad>)“."""
    stub, _ = _nginx_attrappe(vf, 3, installieren_text="helper missing (/usr/local/sbin/probe-nginx-orte-installieren)")
    assert vf["lauf"](VF_NGINX=str(stub)).returncode == 0
    log = vf["zeilen"]("melden.log")
    assert len([z for z in log if z.startswith("normal|")]) == 1
    assert "Install attempt: helper missing (/usr/local/sbin/probe-nginx-orte-installieren)" in log
    assert "probe-konnektor-orte.inc: differs from the template" in "\n".join(log)
    vf["neuer_commit"]()
    assert vf["lauf"](VF_NGINX=str(stub)).returncode == 0
    assert len([z for z in vf["zeilen"]("melden.log") if z.startswith("normal|")]) == 1
    assert not hoch(vf)


def test_veroeffentlichen_nginx_installiert_aber_reload_gescheitert_meldet_einmal(vf):
    """Gegenprüfung F001: installieren endet mit 5 (Datei installiert, Neuladen gescheitert), die zweite Prüfung ist gleich:
    trotzdem genau eine normale Meldung mit „Install attempt“, beim nächsten Lauf mit gleichem Zustand keine weitere."""
    marker = vf["tmp"] / "nginx-versucht"
    stub = ausfuehrbar(vf["tmp"] / "nginx-reload.sh",
                       f'#!/bin/sh\nif [ "$1" = installieren ]; then touch {marker}; '
                       'echo "helper probe-nginx-orte-installieren failed (exit 5, installed and tested, but nginx reload failed): x"; exit 5; fi\n'
                       f'if [ -e {marker} ]; then rm -f {marker}; exit 0; fi\n'
                       'echo "probe-konnektor-orte.inc: differs from the template"\nexit 3\n')
    r = vf["lauf"](VF_NGINX=str(stub))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "installed from the template" not in r.stdout + r.stderr
    log = vf["zeilen"]("melden.log")
    assert len([z for z in log if z.startswith("normal|")]) == 1
    assert any(z.startswith("Install attempt: helper probe-nginx-orte-installieren failed (exit 5") for z in log), log
    assert (vf["tmp"] / "dienst" / "nginx-gemeldet").exists()
    vf["neuer_commit"]()
    assert vf["lauf"](VF_NGINX=str(stub)).returncode == 0
    assert len([z for z in vf["zeilen"]("melden.log") if z.startswith("normal|")]) == 1
    assert not hoch(vf)


def test_veroeffentlichen_nginx_install_attempt_wiederholt_die_liste_nicht(vf):
    """Gegenprüfung F006: Übersprungener Versuch (andere Dateien weichen ab): „Install attempt:“ nennt nur die letzte Zeile."""
    stub = ausfuehrbar(vf["tmp"] / "nginx-anders.sh",
                       '#!/bin/sh\necho "probe-zone.conf: differs from the template"\n'
                       '[ "$1" = installieren ] && echo "install skipped: other files differ"\nexit 3\n')
    assert vf["lauf"](VF_NGINX=str(stub)).returncode == 0
    log = vf["zeilen"]("melden.log")
    assert "Install attempt: install skipped: other files differ" in log
    assert "\n".join(log).count("probe-zone.conf: differs") == 1


def test_einrichten_erzeugt_nginx_orte_hilfsprogramm_und_nennt_einmalschritt(tmp_path):
    """AC-19: --erzeugen legt das Hilfsprogramm ohne Platzhalter an; die Ausgabe der Einrichtung nennt Installation und sudoers."""
    ziel = tmp_path / "soll"
    env = {**SAUBER, "FR_WURZEL": str(tmp_path), "FR_INSTANZ": "probe", "FR_TITEL": "Probe", "FR_BENUTZER": "hans", "EI_ZIEL": str(ziel)}
    r = subprocess.run(["bash", str(BETRIEB / "einrichten.sh"), "--erzeugen"], env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    helfer = ziel / "sbin" / "probe-nginx-orte-installieren"
    text = helfer.read_text(encoding="utf-8")
    assert text.startswith("#!/usr/bin/python3 -I\n") and not re.search(r"__[A-Z_]+__", text)
    r = subprocess.run(["bash", str(BETRIEB / "einrichten.sh")], env=env, capture_output=True, text=True)
    aus = r.stdout + r.stderr
    assert f"sudo install -m 755 -o root -g root {helfer} /usr/local/sbin/" in aus, aus
    assert "NOPASSWD: /usr/local/sbin/probe-nginx-orte-installieren" in aus


def test_beispiel_einstellungen_nennen_die_hilfsprogramme():
    """AC-19: FR_NGINX_HELFER (neu) und FR_UNITS_HELFER (Lücke aus #260) liest Python, nicht die Shell; trotzdem erklärt."""
    beispiel = (BETRIEB / "einstellungen.beispiel").read_text(encoding="utf-8")
    erklaert = set(re.findall(r"^#?(FR_[A-Z0-9_]+)=", beispiel, re.M))
    assert {"FR_NGINX_HELFER", "FR_UNITS_HELFER"} <= erklaert


def test_veroeffentlichen_nginx_abgleich_fehler_stoppt_nichts(vf):
    stub = ausfuehrbar(vf["tmp"] / "nginx.sh", "#!/bin/sh\necho boom >&2\nexit 1\n")
    assert vf["lauf"](VF_NGINX=str(stub)).returncode == 0
    assert vf["pings"]() == 1
    assert not hoch(vf)


# ---------- Stufe 3 des Reisespeichers (#348, Spec docs/specs/betrieb/speicher-348-stufe3.md) ----------
# RED: Der Speicher-Teil von veroeffentlichen.sh, betrieb/vergleichslauf.sh und die Liste FR_SPEICHERREISEN in der Shell
# gibt es noch nicht. Nicht in diesem Block (brauchen ein Submodul im Bauordner): AC-17, AC-25, AC-26, AC-28, AC-30.

SPEICHER_REISEN = ["beispielreise", "stadtwochenende"]


@pytest.fixture
def sp(vf):
    """Speicher-Aufbau über vf: FR_SPEICHER im tmp, echtes Python, Deploy-Attrappe, die den materialisierten Ordner prüft
    und wie der echte Bau daten.json mit reise_stand.nummer in die Seite schreibt."""
    tmp = vf["tmp"]
    speicher, seiten = tmp / "_speicher", tmp / "seiten"
    deploy = ausfuehrbar(tmp / "deploy-speicher.sh", f"""#!/bin/sh
echo "$1" >> {tmp}/deploy.log
[ -e {tmp}/infra-$1 ] && exit 1
[ -e {tmp}/kaputt-$1 ] && {{ cat {tmp}/kaputt-$1; exit 2; }}
ordner="$FR_DIENST/bau/reisen/$1"
if [ -d "$ordner" ]; then
  nummer=$(cat "$ordner.stand")
  mkdir -p "{seiten}/$1"
  for d in index.html sw.js manifest.json; do : > "{seiten}/$1/$d"; done
  printf '{{"reise_stand": {{"nummer": %s}}}}' "$nummer" > "{seiten}/$1/daten.json"
fi
exit 0
""")
    vf["env"].update({"FR_SPEICHER": str(speicher), "FR_SEITEN": str(seiten), "FR_PYTHON": sys.executable,
                      "VF_DEPLOY": str(deploy), "FR_SPEICHERREISEN": ",".join(SPEICHER_REISEN)})
    sys.path.insert(0, str(ENGINE))
    os.environ["FR_SPEICHER"] = str(speicher)
    import reisespeicher
    for r in SPEICHER_REISEN:
        reisespeicher.importieren(WURZEL / "beispiel" / "reisen" / r, r, "Test", grund="Anfang")
    vf["speicher"] = reisespeicher
    vf["seiten"] = seiten
    freigeben(vf, "beispielreise")        # liegt im Test-Bauordner in Git: zur Umschaltung freigegeben (Stufe 5, #350, AC-23)
    yield vf
    os.environ.pop("FR_SPEICHER", None)


def freigeben(sp, reise):
    """Stempel „gleich“ des Vergleichslaufs im dokumentierten Format (Stufe 5, #350): stand = jetzige Stand-Nummer, baum =
    Git-Baum von reisen/<reise> im HEAD des Bauordners. Gilt auch nach späteren Vorgängen im Speicher (Spec, Entscheidung 3)."""
    datei = sp["tmp"] / "dienst" / "vergleich" / f"{reise}.json"
    datei.parent.mkdir(parents=True, exist_ok=True)
    datei.write_text(json.dumps({"zeit": "2026-11-09T10:00:00Z", "ergebnis": "gleich",
                                 "stand": sp["speicher"].stand_nummer(reise), "git": sp["kopf"](), "unterschiede": 0,
                                 "baum": git(sp["arbeit"], "rev-parse", f"HEAD:reisen/{reise}").strip()}))


def _nummer_der_seite(sp, reise):
    return json.loads((sp["seiten"] / reise / "daten.json").read_text())["reise_stand"]["nummer"]


@pytest.mark.parametrize("reise", SPEICHER_REISEN)
def test_veroeffentlichen_baut_speicher_reise_bis_zur_seite(sp, reise):
    sp["speicher"].vorgang_schreiben(reise, {"nachtrag.md": b"Frage"}, "Test", "test", "Frage anlegen")
    r = sp["lauf"]()
    assert reise in sp["deploys"](), r.stdout + r.stderr
    assert _nummer_der_seite(sp, reise) == sp["speicher"].stand_nummer(reise)
    for d in ("index.html", "sw.js", "manifest.json"):
        assert (sp["seiten"] / reise / d).exists()
    assert sp["lauf_stand"](reise)["zustand"] == "veroeffentlicht"


def test_veroeffentlichen_baut_speicher_reise_nur_bei_neuer_nummer(sp):
    sp["lauf"]()
    sp["deploys"]()
    sp["lauf"]()
    assert [r for r in sp["deploys"]() if r in SPEICHER_REISEN] == []
    sp["speicher"].vorgang_schreiben("stadtwochenende", {"x.md": b"1"}, "Test", "test", "x")
    sp["lauf"]()
    assert [r for r in sp["deploys"]() if r in SPEICHER_REISEN] == ["stadtwochenende"]


def test_gemischter_betrieb_baut_beide_quellen_unabhaengig(sp):
    """Git-Reise `zweitreise` (A) und Speicher-Reise `stadtwochenende` (B); scheitert eine, wird die andere trotzdem gebaut."""
    sp["env"]["FR_SPEICHERREISEN"] = "stadtwochenende"
    (sp["tmp"] / "kaputt-zweitreise").write_text("Bau gescheitert")
    sp["lauf"]()
    assert "stadtwochenende" in sp["deploys"]()
    assert sp["rot"]()["art"] == "reise" and "zweitreise" in sp["rot"]()["reisen"]
    (sp["tmp"] / "kaputt-zweitreise").unlink()
    (sp["tmp"] / "kaputt-stadtwochenende").write_text("Bau gescheitert")
    sp["speicher"].vorgang_schreiben("stadtwochenende", {"y.md": b"1"}, "Test", "test", "y")
    sp["lauf"]("--immer")
    assert "zweitreise" in sp["deploys"]() and "stadtwochenende" in sp["rot"]()["reisen"]


def test_ohne_speicherreisen_bleibt_alles_wie_vorher(sp):
    py = ausfuehrbar(sp["tmp"] / "python-falle", f'#!/bin/sh\necho "$@" >> {sp["tmp"]}/py.log\nexec {sys.executable} "$@"\n')
    sp["env"].update({"FR_SPEICHERREISEN": "", "FR_PYTHON": str(py)})
    sp["lauf"]()
    assert "reisespeicher" not in " ".join(sp["zeilen"]("py.log"))
    assert sp["deploys"]() == ["beispielreise", "zweitreise"]


def test_speicher_reise_wird_ohne_github_veroeffentlicht(sp):
    sp["speicher"].vorgang_schreiben("stadtwochenende", {"z.md": b"1"}, "Test", "test", "z")
    git(sp["arbeit"], "remote", "set-url", "origin", str(sp["tmp"] / "gibtes-nicht"))
    ausfuehrbar(sp["tmp"] / "bin/gh", f'#!/bin/sh\ntouch {sp["tmp"]}/gh-gerufen\nexit 1\n')
    ausfuehrbar(sp["tmp"] / "ls-remote.sh", "#!/bin/sh\nexit 1\n")
    r = sp["lauf"](VF_LSREMOTE=str(sp["tmp"] / "ls-remote.sh"))
    assert r.returncode == 0, r.stdout + r.stderr                     # Stufe 5: kein Fehler des Laufs (zweitreise bleibt in Git)
    assert _nummer_der_seite(sp, "stadtwochenende") == sp["speicher"].stand_nummer("stadtwochenende")
    assert not (sp["tmp"] / "gh-gerufen").exists()
    assert not (sp["tmp"] / "dienst/veroeffentlichen-erfolg").exists() and sp["pings"]() == 0


def test_speicher_teil_laeuft_vor_git_fetch(sp):
    ausfuehrbar(sp["tmp"] / "bin/git", f"""#!/bin/sh
case "$*" in *fetch*) [ -e {sp["seiten"]}/stadtwochenende/daten.json ] && echo vorher >> {sp["tmp"]}/ablauf.log || echo nachher >> {sp["tmp"]}/ablauf.log; exit 1;; esac
exec /usr/bin/git "$@"
""")
    sp["lauf"]()
    assert sp["zeilen"]("ablauf.log") == ["vorher"]


def test_speicher_reise_rot_haelt_die_anderen_nicht_auf(sp):
    (sp["tmp"] / "kaputt-beispielreise").write_text("Bau gescheitert: Grund X")
    sp["lauf"]()
    assert "stadtwochenende" in sp["zeilen"]("deploy.log")
    assert sp["rot"]()["art"] == "reise" and "beispielreise" in sp["rot"]()["reisen"]
    lauf = sp["lauf_stand"]("beispielreise")
    assert lauf["zustand"] == "fehlgeschlagen" and "Grund X" in json.dumps(lauf)
    assert not (sp["tmp"] / "dienst/veroeffentlichen-erfolg").exists() and sp["pings"]() == 0
    (sp["tmp"] / "kaputt-beispielreise").unlink()
    (sp["tmp"] / "infra-beispielreise").write_text("")                # Infrastruktur-Störung: Exit 1
    sp["speicher"].vorgang_schreiben("beispielreise", {"q.md": b"1"}, "Test", "test", "q")
    assert sp["lauf"]().returncode == 1
    assert not (sp["tmp"] / "dienst/reise-stand/beispielreise.gebaut").exists()


def test_speicher_rot_meldet_ohne_gh(sp):
    sp["env"]["FR_SPEICHERREISEN"] = "stadtwochenende"                 # nur im Speicher, nicht in Git
    ausfuehrbar(sp["tmp"] / "bin/gh", f'#!/bin/sh\ntouch {sp["tmp"]}/gh-gerufen\n')
    (sp["tmp"] / "kaputt-stadtwochenende").write_text("Bau gescheitert")
    sp["speicher"].vorgang_schreiben("stadtwochenende", {"r.md": b"1"}, "Test", "test", "r")
    sp["lauf"](VF_JETZT=str(T0))
    assert "stadtwochenende" in sp["rot"]()["reisen"]
    sp["lauf"](VF_JETZT=str(T0 + 7200))                               # über der Schwelle
    assert hoch(sp) and sp["zeilen"]("rotmelden.log")
    assert not (sp["tmp"] / "gh-gerufen").exists()


def test_speicher_teil_uebergeht_reise_ohne_eintrag(sp):
    sp["env"]["FR_SPEICHERREISEN"] = "stadtwochenende,gibtesnicht"
    r = sp["lauf"]()
    assert "gibtesnicht" not in sp["zeilen"]("deploy.log") and "gibtesnicht" in r.stdout
    assert "stadtwochenende" in sp["zeilen"]("deploy.log")


def test_stempel_gebaut_nur_nach_gelungenem_deploy(sp):
    sp["lauf"]()
    gebaut = sp["tmp"] / "dienst/reise-stand/stadtwochenende.gebaut"
    assert gebaut.read_text().split()[0] == str(sp["speicher"].stand_nummer("stadtwochenende"))
    vorher = gebaut.read_text()
    (sp["tmp"] / "kaputt-stadtwochenende").write_text("Bau gescheitert")
    sp["speicher"].vorgang_schreiben("stadtwochenende", {"w.md": b"1"}, "Test", "test", "w")
    sp["lauf"]()
    assert gebaut.read_text() == vorher


def test_vergleichslauf_schreibt_stempel_und_exit_codes(sp):
    """Git-Reise `beispielreise` im Bauordner (aus der Beispielreise) und dieselbe im Speicher."""
    ziel = sp["arbeit"] / "reisen" / "beispielreise"
    shutil.rmtree(ziel)
    shutil.copytree(BEISPIEL, ziel)
    git(sp["arbeit"], "add", ".")
    git(sp["arbeit"], "commit", "-qm", "beispielreise")
    skript = BETRIEB / "vergleichslauf.sh"

    def lauf(*a, **e):
        return subprocess.run([str(skript), *a], env={**sp["env"], **e}, capture_output=True, text=True)
    stempel = sp["tmp"] / "dienst/vergleich/beispielreise.json"
    r = lauf("beispielreise")
    assert r.returncode == 0, r.stdout + r.stderr
    s = json.loads(stempel.read_text())
    assert s["ergebnis"] == "gleich" and s["git"] == git(sp["arbeit"], "rev-parse", "HEAD").strip()
    assert {"zeit", "stand", "git", "unterschiede"} <= set(s)
    sp["speicher"].vorgang_schreiben("beispielreise", {"extra.md": b"1"}, "Test", "test", "extra")
    assert lauf("beispielreise").returncode == 1
    assert json.loads(stempel.read_text())["ergebnis"] == "unterschied"
    assert lauf("beispielreise", FR_SPEICHER=str(sp["tmp"] / "kein-speicher")).returncode == 2
    assert git(sp["arbeit"], "status", "--porcelain").strip() == ""


# ---------- Stufe 3, Teil 3: Software-Wechsel auf dem Server (AC-25, AC-26, AC-30) ----------
# Im Test ohne Submodul: Software-Kennung = `git rev-parse HEAD` (Spec, Entscheidung 5); ein Commit außerhalb von reisen/
# ist ein Software-Wechsel.

def _py_protokoll(sp):
    py = ausfuehrbar(sp["tmp"] / "python-protokoll", f'#!/bin/sh\necho "$@" >> {sp["tmp"]}/py.log\nexec {sys.executable} "$@"\n')
    sp["env"]["FR_PYTHON"] = str(py)


def test_software_wechsel_stellt_speicher_reisen_auf_dem_server_um(sp):
    _py_protokoll(sp)
    sp["env"]["FR_SPEICHERREISEN"] = "stadtwochenende"
    sp["lauf"]()
    gebaut = sp["tmp"] / "dienst/reise-stand/stadtwochenende.gebaut"
    alt = gebaut.read_text().split()[1]
    assert "nachziehen-speicher" not in " ".join(sp["zeilen"]("py.log"))    # ohne Wechsel kein Aufruf
    sp["neuer_commit"]()                                                      # Software-Wechsel
    sp["deploys"]()
    sp["lauf"]()
    assert any("nachziehen-speicher" in z and "stadtwochenende" in z for z in sp["zeilen"]("py.log"))
    assert "stadtwochenende" in sp["deploys"]()
    assert gebaut.read_text().split()[1] == sp["kopf"]() != alt


def test_software_wechsel_braucht_keinen_handschritt(sp):
    """Die Reise im alten Format wird vom Lauf umgestellt, ohne dass jemand neu.py aufruft."""
    sp["env"]["FR_SPEICHERREISEN"] = "stadtwochenende"
    sp["lauf"]()
    alt = {p: b for p, b in sp["speicher"].aktueller_stand("stadtwochenende").items()}
    text = alt["reise.yaml"].decode().splitlines()
    sp["speicher"].vorgang_schreiben("stadtwochenende",
                                     {"reise.yaml": ("\n".join(z for z in text if not z.startswith("sprache:")) + "\n").encode()},
                                     "Test", "test", "altes Format")
    sp["neuer_commit"]()
    sp["lauf"]()
    assert b"sprache:" in sp["speicher"].aktueller_stand("stadtwochenende")["reise.yaml"]
    assert sp["speicher"].verlauf("stadtwochenende", 1)[0]["wer"] == "Software-Nachziehen"


def test_rotes_software_tor_haelt_speicher_reisen_auf_altem_stand(sp):
    _py_protokoll(sp)
    sp["env"]["FR_SPEICHERREISEN"] = "stadtwochenende"
    sp["lauf"]()
    gebaut = sp["tmp"] / "dienst/reise-stand/stadtwochenende.gebaut"
    vorher = gebaut.read_text()
    sp["deploys"]()
    sp["neuer_commit"]()
    (sp["tmp"] / "rot").write_text("")                                        # Tests der Software rot (pruefen.sh)
    # Zwischenlauf: Der Speicher-Teil läuft vor git fetch und sieht den neuen Stand noch nicht; erst dieser Lauf spult vor,
    # das Tor ist rot. Danach trägt der Bauordner die neue, ungeprüfte Software (Spec, Entscheidung 7).
    sp["lauf"]()
    sp["deploys"]()
    sp["speicher"].vorgang_schreiben("stadtwochenende", {"t.md": b"1"}, "Test", "test", "t")   # auch kein Inhaltsbau
    sp["lauf"]()
    assert gebaut.read_text() == vorher
    assert "stadtwochenende" not in sp["deploys"]()
    assert "nachziehen-speicher" not in " ".join(sp["zeilen"]("py.log"))
    assert sp["rot"]()["art"] == "software"


# ---------- Nachträge aus der Prüfung (Adversary, F001, F002) ----------

def test_kaputte_speicher_reise_beim_nachziehen_haelt_die_anderen_nicht_auf(sp):
    """F001: Scheitert das Umstellen einer Reise (kaputte reise.yaml im Speicher), ist nur sie rot; die andere
    Speicher-Reise wird umgestellt und gebaut, der Lauf ist keine Störung."""
    sp["env"]["FR_SPEICHERREISEN"] = "stadtwochenende,beispielreise"          # die kaputte zuerst
    sp["lauf"]()
    sp["speicher"].vorgang_schreiben("stadtwochenende", {"reise.yaml": b"titel: [kaputt\n  sprache: :\n"},
                                     "Test", "test", "kaputt")
    sp["neuer_commit"]()
    r = sp["lauf"]()
    assert "cannot be read from the trip store" not in r.stdout, r.stdout
    assert (sp["tmp"] / "dienst/reise-stand/beispielreise.gebaut").read_text().split()[1] == sp["kopf"]()
    assert "stadtwochenende" in sp["rot"]()["reisen"]
    assert sp["lauf_stand"]("stadtwochenende")["zustand"] == "fehlgeschlagen"


def test_vergleichslauf_ohne_liste_meldet_unlesbaren_speicher(sp):
    """F002: Ohne Reiseliste und mit nicht lesbarer Datenbank ist das ein Fehler (Exit 2), kein stilles Überspringen."""
    db = sp["tmp"] / "_speicher" / "reisen.db"
    for rest in ("-wal", "-shm"):
        Path(f"{db}{rest}").unlink(missing_ok=True)
    db.write_bytes(b"kein sqlite" * 100)
    r = subprocess.run([str(BETRIEB / "vergleichslauf.sh")], env=sp["env"], capture_output=True, text=True)
    assert r.returncode == 2, r.stdout + r.stderr
    assert "ERROR" in r.stdout


# ---------- Stufe 4 des Reisespeichers (#349, Spec docs/specs/betrieb/speicher-349-stufe4.md): Ablage der Medien ----------

STUFE3_SCHEMA = """
CREATE TABLE vorgaenge (
  nummer INTEGER PRIMARY KEY AUTOINCREMENT, reise TEXT NOT NULL, stand INTEGER NOT NULL, wann TEXT NOT NULL,
  wer TEXT NOT NULL, rolle TEXT NOT NULL DEFAULT '', werkzeug TEXT NOT NULL, titel TEXT NOT NULL,
  grund TEXT NOT NULL DEFAULT '', kennung TEXT UNIQUE, herkunft TEXT NOT NULL DEFAULT '',
  UNIQUE (reise, stand), UNIQUE (nummer, reise));
CREATE TABLE versionen (
  vorgang INTEGER NOT NULL, reise TEXT NOT NULL, pfad TEXT NOT NULL, inhalt BLOB, pruefsumme TEXT,
  PRIMARY KEY (vorgang, pfad), FOREIGN KEY (vorgang, reise) REFERENCES vorgaenge (nummer, reise));
"""


def _ausgelagert(db, muster):
    import sqlite3
    from contextlib import closing
    with closing(sqlite3.connect(db)) as v:
        return v.execute("SELECT pfad, pruefsumme, ausgelagert FROM versionen WHERE pfad LIKE ? ORDER BY vorgang DESC",
                         (muster,)).fetchall()


def test_software_wechsel_lagert_medien_ohne_handschritt_aus(sp):
    """AC-23: Ein Speicher im Format der Stufe 3 (Medien als BLOB) wird von den Läufen von veroeffentlichen.sh umgestellt,
    ohne dass jemand neu.py oder reisespeicher.py aufruft."""
    import hashlib
    import sqlite3
    from contextlib import closing
    alt = sp["tmp"] / "_speicher3"
    alt.mkdir(mode=0o700)
    sp["env"].update({"FR_SPEICHER": str(alt), "FR_SPEICHERREISEN": "beispielreise"})
    os.environ["FR_SPEICHER"] = str(alt)
    with closing(sqlite3.connect(alt / "reisen.db")) as v:
        v.executescript(STUFE3_SCHEMA)
        v.execute("INSERT INTO vorgaenge (nummer, reise, stand, wann, wer, werkzeug, titel) "
                  "VALUES (1, 'beispielreise', 1, '2026-11-01T10:00:00+00:00', 'Test', 'test', 'Anfang')")
        for f in sorted(BEISPIEL.rglob("*")):
            if f.is_file() and ".git" not in f.relative_to(BEISPIEL).parts:
                b = f.read_bytes()
                v.execute("INSERT INTO versionen VALUES (1, 'beispielreise', ?, ?, ?)",
                          (f.relative_to(BEISPIEL).as_posix(), b, hashlib.sha256(b).hexdigest()))
        v.execute("PRAGMA user_version = 1")
        v.commit()
    rs = sp["speicher"]
    assert sp["lauf"]().returncode == 0
    assert _ausgelagert(alt / "reisen.db", "medien/%.gpx")[0][2] == 0   # gehoben, aber noch nicht umgestellt
    sp["neuer_commit"]()
    r = sp["lauf"]()
    assert r.returncode == 0, r.stdout + r.stderr
    assert any(e["was"] == "ablage-umstellung" and e["wer"] == "Software-Nachziehen" for e in rs.verlauf("beispielreise"))
    medien = _ausgelagert(alt / "reisen.db", "medien/%.gpx")
    assert medien[0][2] == 1 and rs.ablage_pfad(medien[0][1]).is_file()
    assert not rs.vergleichen("beispielreise", sp["tmp"] / "dienst" / "bau" / "reisen" / "beispielreise")


@pytest.mark.parametrize("art", ["fehlt", "beschaedigt"])
def test_fehlende_ablagedatei_macht_die_speicher_reise_rot(sp, art):
    """AC-10/AC-11, Fehlerfälle der Spec 349: Fehlt eine Ablagedatei oder ist sie beschädigt, ist die Reise rot (Grund =
    Katalogtext), kein Stempel, keine Störung; die andere Speicher-Reise wird trotzdem gebaut."""
    rs = sp["speicher"]
    assert sp["lauf"]().returncode == 0
    gebaut = sp["tmp"] / "dienst/reise-stand/beispielreise.gebaut"
    vorher = gebaut.read_text()
    erfolg = sp["tmp"] / "dienst/veroeffentlichen-erfolg"
    erfolg.unlink(missing_ok=True)
    sp["pings"]()                                                        # zählt ab hier
    sp["deploys"]()
    summe = _ausgelagert(sp["tmp"] / "_speicher" / "reisen.db", "medien/%.png")[0][1]
    f = rs.ablage_pfad(summe)
    os.chmod(f.parent, 0o700)
    if art == "fehlt":
        f.unlink()
    else:
        os.chmod(f, 0o600)
        f.write_bytes(b"kaputt")
    r = sp["lauf"]("--immer")
    assert "cannot be read from the trip store" not in r.stdout, r.stdout + r.stderr
    assert "beispielreise" in sp["rot"]()["reisen"] and "stadtwochenende" in sp["deploys"]()
    lauf = sp["lauf_stand"]("beispielreise")
    assert lauf["zustand"] == "fehlgeschlagen" and "medien/" in json.dumps(lauf, ensure_ascii=False)
    assert gebaut.read_text() == vorher                                   # kein neuer Stempel
    assert not erfolg.exists() and sp["pings"]() == 0, r.stdout          # kein Erfolg, kein Heartbeat


def test_doku_nennt_keinen_handschritt_fuer_die_ablage():
    """AC-23: docs/betrieb.md beschreibt die Umstellung auf die Ablage ohne Handschritt; der Neuaufbau ist freiwillig."""
    text = (WURZEL / "docs" / "betrieb.md").read_text(encoding="utf-8")
    absatz = next(z for z in text.splitlines() if z.startswith("**Ablage der Medien"))
    assert "Kein Handschritt" in absatz and "nachziehen-speicher" in absatz
    assert "ablage-umstellen" in absatz and "freiwillig" in absatz
    assert "ablage/" in absatz and "Wiederherstellung" in absatz


def _dist(ordner):
    aus = {}
    for p in sorted(Path(ordner).rglob("*")):
        if p.is_file():
            rel = p.relative_to(ordner).as_posix()
            if rel == "daten.json":
                d = json.loads(p.read_text(encoding="utf-8"))
                d.pop("reise_stand", None)
                aus[rel] = d
            else:
                aus[rel] = p.read_bytes()
    return aus


@pytest.mark.parametrize("reise", SPEICHER_REISEN)
def test_speicher_reise_mit_ablage_baut_wie_aus_dem_ordner(sp, reise):
    """AC-24: Eine Speicher-Reise mit ausgelagerten Medien, veröffentlicht über veroeffentlichen.sh (Stufe-3-Weg), baut
    dieselbe Seite wie die Reise aus ihrem Ordner (bis auf reise_stand in daten.json)."""
    if reise == "beispielreise":
        assert _ausgelagert(sp["tmp"] / "_speicher" / "reisen.db", "medien/%.png")[0][2] == 1
    assert sp["lauf"]().returncode == 0
    ordner = sp["tmp"] / "dienst" / "bau" / "reisen" / reise
    quelle = sp["tmp"] / "ordner" / reise
    shutil.copytree(WURZEL / "beispiel" / "reisen" / reise, quelle, ignore=shutil.ignore_patterns(".git"))
    bauen.bauen(ordner, sp["tmp"] / "dist-speicher" / reise)
    daten = bauen.bauen(quelle, sp["tmp"] / "dist-ordner" / reise)
    a, b = _dist(sp["tmp"] / "dist-speicher" / reise), _dist(sp["tmp"] / "dist-ordner" / reise)
    assert sorted(set(a) ^ set(b)) == [] and a == b
    assert "sw.js" in a and "manifest.json" in a
    if reise == "beispielreise":
        assert (daten.get("route") or {}).get("strecken")


# ---------- #444: eigener Kartendienst (Spec docs/specs/betrieb/eigener-kartendienst-444.md) ----------
#
# Schnittstelle (Entscheidung in der RED-Phase): Die Einheiten des Kartendienstes entstehen nur mit FR_KARTENDIENST_REGIONEN,
# und zwar in <EI_ZIEL>/kartendienst/ (nicht in <EI_ZIEL>/systemd/, das der Einheiten-Abgleich #260 liest):
#   <instanz>-kartendienst.socket, <instanz>-kartendienst-proxy.service, <instanz>-kartendienst.service,
#   <instanz>-kartendienst-aktualisieren.service, <instanz>-kartendienst-aktualisieren.timer

KD_EINHEITEN = ("kartendienst.socket", "kartendienst-proxy.service", "kartendienst.service",
                "kartendienst-aktualisieren.service", "kartendienst-aktualisieren.timer")
KD_REGIONEN = {"FR_KARTENDIENST_REGIONEN": "europe/andorra", "FR_KARTENDIENST_ORDNER": "/srv/probe/kartendienst"}


def kd_einrichten(tmp_path, *argv, **extra):
    ziel = tmp_path / "soll"
    env = {**{k: v for k, v in SAUBER.items() if not k.startswith("EI_")}, "FR_WURZEL": str(tmp_path), "FR_INSTANZ": "probe",
           "FR_TITEL": "Probe", "EI_ZIEL": str(ziel), "EI_SYSTEMD": str(tmp_path / "systemd"),
           "FR_NGINX_SNIPPETS": str(tmp_path / "snippets"), **extra}
    r = subprocess.run(["bash", str(BETRIEB / "einrichten.sh"), *argv], env=env, capture_output=True, text=True, timeout=120)
    return r, ziel


def test_einrichten_kartendienst_nur_mit_regionen(tmp_path):
    """AC-13: Ohne Regionen keine Einheiten und keine Befehle des Kartendienstes; mit Regionen alle fünf, Platzhalter ersetzt,
    Image per Digest, StopWhenUnneeded, --exit-idle-time, Socket nur auf 127.0.0.1, und die einmaligen Befehle in der Ausgabe."""
    r, ziel = kd_einrichten(tmp_path, "--erzeugen")
    assert r.returncode == 0, (r.stdout, r.stderr)
    assert not [p for p in ziel.rglob("*") if "kartendienst" in p.name]
    r, _ = kd_einrichten(tmp_path)
    assert "kartendienst" not in r.stdout.replace(str(tmp_path), "<tmp>").lower(), r.stdout   # der Testordner trägt den Testnamen
    r, ziel = kd_einrichten(tmp_path, "--erzeugen", **KD_REGIONEN)
    assert r.returncode == 0, (r.stdout, r.stderr)
    ordner = ziel / "kartendienst"
    texte_ = {n: (ordner / f"probe-{n}").read_text(encoding="utf-8") for n in KD_EINHEITEN}
    for name, text in texte_.items():
        assert not re.search(r"__[A-Z_]+__", text), (name, text)
    assert not [p for p in (ziel / "systemd").iterdir() if "kartendienst" in p.name]
    assert re.search(r"ListenStream=127\.0\.0\.1:12345\b", texte_["kartendienst.socket"]), texte_["kartendienst.socket"]
    assert "--exit-idle-time=15min" in texte_["kartendienst-proxy.service"]
    assert "BindsTo=probe-kartendienst.service" in texte_["kartendienst-proxy.service"]
    dienst = texte_["kartendienst.service"]
    assert re.search(r"wiktorn/overpass-api(:[\w.-]+)?@sha256:[0-9a-f]{64}", dienst), dienst
    assert "StopWhenUnneeded=yes" in dienst and "2g" in dienst and "/srv/probe/kartendienst" in dienst
    assert "ExecStartPost=" in dienst and "/api/status" not in dienst
    assert "OnCalendar=" in texte_["kartendienst-aktualisieren.timer"]
    assert "kartendienst.sh aktualisieren" in texte_["kartendienst-aktualisieren.service"]
    r, ziel = kd_einrichten(tmp_path, **KD_REGIONEN, FR_KARTENDIENST_PORT="23456", FR_KARTENDIENST_RUHE="5min",
                            FR_KARTENDIENST_SPEICHER="3g")
    assert re.search(r"755 .*/srv/probe/kartendienst|/srv/probe/kartendienst.*755", r.stdout), r.stdout
    assert "enable --now probe-kartendienst.socket" in r.stdout and "kartendienst.sh einspielen" in r.stdout, r.stdout
    assert "enable --now probe-kartendienst-aktualisieren.timer" in r.stdout, r.stdout
    texte_ = {n: (ziel / "kartendienst" / f"probe-{n}").read_text(encoding="utf-8") for n in KD_EINHEITEN}
    assert "127.0.0.1:23456" in texte_["kartendienst.socket"] and "--exit-idle-time=5min" in texte_["kartendienst-proxy.service"]
    assert "3g" in texte_["kartendienst.service"]


def test_einheitenabgleich_ohne_kartendienst_laerm(tmp_path):
    """AC-14: Der Abgleich (#260) sieht die Einheiten des Kartendienstes nicht; die feste Menge der Arten bleibt bei sechs."""
    import importlib.util
    r, ziel = kd_einrichten(tmp_path, "--erzeugen", **KD_REGIONEN)
    assert r.returncode == 0, (r.stdout, r.stderr)
    assert (ziel / "kartendienst" / "probe-kartendienst.service").exists()
    spec = importlib.util.spec_from_file_location("units_kd", BETRIEB / "units.py")
    units = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(units)
    systemd = tmp_path / "systemd"
    systemd.mkdir(exist_ok=True)
    for p in (ziel / "systemd").iterdir():
        shutil.copy(p, systemd / p.name)
    assert units.pruefen(str(ziel), str(systemd)) == {}
    helfer = (BETRIEB / "vorlagen" / "units-installieren.py").read_text(encoding="utf-8")
    assert re.search(r'^ARTEN = \("konnektor", "push", "rueckmeldungen", "schreiben", "veroeffentlichen", "waechter"\)$', helfer, re.M)


def test_kartendienst_in_der_modulliste_des_schreibwegs():
    """AC-18"""
    assert (ENGINE / "kartendienst.py").exists()
    assert "kartendienst.py" in _deploy_liste("SB_MODULE")


def test_kartendienst_lizenzhinweis_in_doku():
    """AC-19: docs/betrieb.md und THIRD_PARTY.md nennen Overpass (AGPL), das Image per Digest (nicht mitgeliefert) und die Daten
    (ODbL, OpenStreetMap)."""
    for datei in (WURZEL / "docs" / "betrieb.md", WURZEL / "THIRD_PARTY.md"):
        text = datei.read_text(encoding="utf-8")
        abschnitt = text[text.lower().index("kartendienst"):] if "kartendienst" in text.lower() else ""
        assert abschnitt, datei.name
        for wort in ("Overpass", "AGPL", "wiktorn/overpass-api", "Digest", "ODbL", "OpenStreetMap"):
            assert wort in abschnitt, (datei.name, wort)


def test_einstellungen_des_kartendienstes_dokumentiert():
    """Spec, Einstellungen der Instanz: alle neuen Werte stehen in einstellungen.beispiel und docs/betrieb.md."""
    beispiel = (BETRIEB / "einstellungen.beispiel").read_text(encoding="utf-8")
    doku = (WURZEL / "docs" / "betrieb.md").read_text(encoding="utf-8")
    for name in ("FR_OVERPASS", "FR_KARTENDIENST", "FR_KARTENDIENST_ORDNER", "FR_KARTENDIENST_REGIONEN", "FR_KARTENDIENST_PORT",
                 "FR_KARTENDIENST_SPEICHER", "FR_KARTENDIENST_RUHE"):
        assert re.search(rf"\b{name}=", beispiel), name
        assert name in doku, name


def test_ci_nachweis_ersetzt_die_serverpruefung_der_software(an):
    """#403: Sind die Pflichtprüfungen der eingebundenen Software-Version auf GitHub grün, läuft engine/tests nicht noch
    einmal auf dem Server; ohne Nachweis (nicht grün oder abgeschaltet) laufen sie wie bisher."""
    t = an["tmp"]
    nachweis = ausfuehrbar(t / "ci.sh", f'#!/bin/sh\necho "$@" >> {t}/ci.log\n[ ! -e {t}/ci-rot ] && echo true || echo false\n')
    r = an["lauf_an"](T0, VF_CINACHWEIS=str(nachweis))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "server tests skipped (#403)" in r.stdout
    assert "p" not in an["zeilen"]("pruefen.log")                       # keine Serverprüfung der Software
    assert an["a"] in an["zeilen"]("ci.log")[0]                         # Nachweis für genau die eingebundene Version


def test_ohne_ci_nachweis_laeuft_die_serverpruefung(an):
    t = an["tmp"]
    nachweis = ausfuehrbar(t / "ci.sh", f'#!/bin/sh\necho false\n')
    r = an["lauf_an"](T0, VF_CINACHWEIS=str(nachweis))
    assert r.returncode == 0 and "skipped (#403)" not in r.stdout
    assert "p" in an["zeilen"]("pruefen.log")


def test_ci_nachweis_abgeschaltet_laeuft_die_serverpruefung(an):
    t = an["tmp"]
    nachweis = ausfuehrbar(t / "ci.sh", "#!/bin/sh\necho true\n")
    r = an["lauf_an"](T0, VF_CINACHWEIS=str(nachweis), FR_CI_NACHWEIS="0")
    assert r.returncode == 0 and "skipped (#403)" not in r.stdout
    assert "p" in an["zeilen"]("pruefen.log")


def _ersetzen(ziel, *dateien):
    return subprocess.run([str(BETRIEB / "ersetzen.sh"), str(ziel), *map(str, dateien)], capture_output=True, text=True)


def test_ersetzen_laesst_unveraenderte_dateien_stehen(tmp_path):
    """#489: deploy.sh ersetzte jedes Modul in <FR_DIENST> mit install, auch unveränderte. install löscht die Zieldatei
    und schreibt sie neu; ein gleichzeitiger Schreibvorgang fand texte_de.py kurz nicht und meldete „Fehler im Dienst“.
    Unveränderte Dateien bleiben deshalb unberührt (gleicher Inode)."""
    quelle, ziel = tmp_path / "quelle", tmp_path / "ziel"
    quelle.mkdir()
    (quelle / "a.py").write_text("A = 1\n")
    assert _ersetzen(ziel, quelle / "a.py").returncode == 0
    inode = (ziel / "a.py").stat().st_ino
    r = _ersetzen(ziel, quelle / "a.py")
    assert r.returncode == 0, r.stderr
    assert (ziel / "a.py").stat().st_ino == inode


def test_ersetzen_tauscht_geaenderte_dateien_atomar(tmp_path):
    """Eine geänderte Datei kommt per Umbenennen an ihren Platz (neuer Inode, nie fehlend oder halb geschrieben):
    Wer die alte Datei offen hat, liest sie ganz zu Ende; Rechte 644; keine Reste im Zielordner."""
    quelle, ziel = tmp_path / "quelle", tmp_path / "ziel"
    quelle.mkdir()
    (quelle / "a.py").write_text("A = 1\n")
    (quelle / "b.html").write_text("<p>alt</p>\n")
    assert _ersetzen(ziel, quelle / "a.py", quelle / "b.html").returncode == 0
    alt = open(ziel / "a.py")
    inode = (ziel / "a.py").stat().st_ino
    (quelle / "a.py").write_text("A = 2\n")
    r = _ersetzen(ziel, quelle / "a.py", quelle / "b.html")
    assert r.returncode == 0, r.stderr
    assert (ziel / "a.py").read_text() == "A = 2\n" and (ziel / "a.py").stat().st_ino != inode
    assert alt.read() == "A = 1\n"
    alt.close()
    assert stat.S_IMODE((ziel / "a.py").stat().st_mode) == 0o644
    assert sorted(p.name for p in ziel.iterdir()) == ["a.py", "b.html"]


def test_ersetzen_bricht_bei_fehlender_quelle_ab(tmp_path):
    (tmp_path / "ziel").mkdir()
    r = _ersetzen(tmp_path / "ziel", tmp_path / "fehlt.py")
    assert r.returncode != 0 and list((tmp_path / "ziel").iterdir()) == []


def test_deploy_ersetzt_dateien_im_dienst_nur_ueber_ersetzen():
    """Kein install mehr nach <FR_DIENST> (#489): Module, Vorlage und Service-Worker gehen über ersetzen.sh, Ordner über
    rsync (das schreibt ohnehin in eine Temp-Datei und benennt um)."""
    deploy = (BETRIEB / "deploy.sh").read_text(encoding="utf-8")
    assert not re.search(r'install [^\n]*"\$DIENST/?"', deploy)
    assert '"$FR_BETRIEB/ersetzen.sh" "$DIENST"' in deploy
    assert "--inplace" not in deploy



# ---------- Neustarts eines Laufs ohne Root-Rechte (#494) ----------

def test_deploy_ohne_root_rechte_merkt_die_neustarts_vor(tmp_path):
    """Der Schreibweg stößt das Veröffentlichen aus einem Dienst mit NoNewPrivileges an; spult dieser Lauf die Software
    vor, scheitert in deploy.sh jedes sudo. Die fälligen Neustarts werden dann in <FR_DIENST>/neustart-ausstehend
    vorgemerkt (einmal je Dienst), statt nur „please run“ ins Protokoll zu schreiben (#494)."""
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
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    ausfuehrbar(bin_ / "systemctl", '#!/bin/sh\ncase "$1" in is-enabled) exit 0;; esac\nexit 1\n')   # alle Dienste eingerichtet

    class Gesund(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")

        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), Gesund)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    env = {**SAUBER, "PATH": f"{bin_}:{SAUBER.get('PATH', os.environ['PATH'])}", "FR_WURZEL": str(wurzel), "FR_INSTANZ": "probe",
           "FR_SEITEN": str(tmp_path / "seiten"), "FR_DIENST": str(tmp_path / "dienst"), "FR_PYTHON": sys.executable,
           "FR_GEPRUEFT": git(wurzel, "rev-parse", "HEAD").strip(), "FR_RM_PORT": str(server.server_address[1]), "FR_SUDO": "false",
           # Konnektor ebenfalls gegen den Probe-Server, nie gegen einen echten Dienst auf dem Rechner; Wege von außen
           # prüft hier niemand
           "FR_KN_PORT": str(server.server_address[1]), "FR_WEGE_SPAETER": "1"}
    vorgemerkt = tmp_path / "dienst" / "neustart-ausstehend"
    try:
        r = subprocess.run([str(BETRIEB / "deploy.sh"), "beispielreise"], env=env, capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr
        assert vorgemerkt.read_text().split() == ["probe-rueckmeldungen", "probe-konnektor", "probe-schreiben", "probe-push"]
        assert "please run" not in r.stdout and "the next timer run restarts probe-konnektor" in r.stdout
        # Ein Dienst ändert sich wieder, bevor der Timer lief: nichts doppelt vorgemerkt
        (tmp_path / "dienst" / "konnektor.py").write_text("alt\n")
        r = subprocess.run([str(BETRIEB / "deploy.sh"), "beispielreise"], env=env, capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr
        assert sorted(vorgemerkt.read_text().split()) == ["probe-konnektor", "probe-push", "probe-rueckmeldungen", "probe-schreiben"]
    finally:
        server.shutdown()


def test_veroeffentlichen_holt_vorgemerkte_neustarts_mit_root_rechten_nach(vf):
    """Der nächste Lauf mit Root-Rechten (Timer) startet die vorgemerkten Dienste neu, auch ohne neuen Stand und vor dem
    Abruf von GitHub; ein Lauf ohne Root-Rechte lässt die Vormerkung liegen. Scheitert ein Neustart, bleibt nur dieser
    vorgemerkt (#494)."""
    neustarts = vf["tmp"] / "neustarts.log"
    ausfuehrbar(vf["tmp"] / "bin" / "systemctl",
                f'#!/bin/sh\n[ "$1" = restart ] || exit 1\ncase "$2" in *kaputt*) exit 1;; esac\necho "$2" >> {neustarts}\n')
    vorgemerkt = vf["tmp"] / "dienst" / "neustart-ausstehend"
    vorgemerkt.parent.mkdir(exist_ok=True)
    vorgemerkt.write_text("probe-konnektor\nprobe-kaputt\nprobe-schreiben\nprobe-konnektor\nboese; rm -rf /\n")
    r = vf["lauf"](FR_SUDO="false")
    assert r.returncode == 0, r.stdout + r.stderr
    assert not neustarts.exists() and len(vorgemerkt.read_text().split("\n")) == 6
    r = vf["lauf"]()
    assert r.returncode == 0, r.stdout + r.stderr
    assert neustarts.read_text().split() == ["probe-konnektor", "probe-schreiben"]
    assert "probe-konnektor restarted (pending from a run without root rights)." in r.stdout
    assert "Warning: restart of probe-kaputt failed" in r.stdout
    assert vorgemerkt.read_text().split() == ["probe-kaputt"]
    vorgemerkt.write_text("probe-push\n")
    neustarts.unlink()
    r = vf["lauf"]()
    assert r.returncode == 0 and neustarts.read_text().split() == ["probe-push"] and not vorgemerkt.exists(), r.stdout


# ---------- #552: Rechte des Dienstbenutzers (Spec docs/specs/betrieb/dienstrechte-552.md) ----------

def _unit_zeilen(name):
    return [z.strip() for z in (BETRIEB / "vorlagen" / name).read_text(encoding="utf-8").splitlines()
            if z.strip() and not z.strip().startswith("#")]


def test_netzdienste_ohne_docker_und_sudo():
    """AC-1: Die drei aus dem Netz erreichbaren Dienste kommen weder über sudo noch über den Docker-Socket an Root-Rechte."""
    for name in ("konnektor.service", "rueckmeldungen.service", "push.service"):
        zeilen = _unit_zeilen(name)
        assert "NoNewPrivileges=yes" in zeilen, name
        assert "InaccessiblePaths=-/run/docker.sock" in zeilen, name
    # Der Rückmeldedienst fragt die Rolle beim Schreibweg ab (AC-17): er kennt dessen Adresse
    assert "Environment=KN_SCHREIBDIENST=http://127.0.0.1:__SB_PORT__" in _unit_zeilen("rueckmeldungen.service")


def _readwritepaths(zeilen):
    return [p for z in zeilen if z.startswith("ReadWritePaths=") for p in z.split("=", 1)[1].split()]


def test_schreiben_unit_sandbox():
    """AC-2: Der Schreibweg kann keine Dateien im Home ändern, die später mit höheren Rechten laufen."""
    zeilen = _unit_zeilen("schreiben.service")
    for soll in ("ProtectSystem=strict", "ProtectHome=read-only", "InaccessiblePaths=-/run/docker.sock", "NoNewPrivileges=yes"):
        assert soll in zeilen, soll
    assert not [z for z in zeilen if z in ("ProtectSystem=no", "ProtectHome=no")]
    ziele = _readwritepaths(zeilen)
    assert ziele and len(ziele) == len(set(ziele))
    for platzhalter in ("__DIENST__", "__KONTEN__"):
        assert any(p.lstrip("-").startswith(platzhalter) for p in ziele), (platzhalter, ziele)
    # Kein Ziel öffnet das ganze Home oder die Wurzel des Systems
    assert not [p for p in ziele if p.lstrip("-") in ("/", "/home", "/root", "/etc", "/usr", "__HOME__")]
    # Jedes Ziel steht mit Begründung als Kommentar in der Vorlage
    text = (BETRIEB / "vorlagen" / "schreiben.service").read_text(encoding="utf-8")
    kommentare = "\n".join(z for z in text.splitlines() if z.lstrip().startswith("#"))
    for p in ziele:
        assert p.lstrip("-") in kommentare, p


def test_messlauf_deckt_readwritepaths():
    """AC-3: Die Schreibziele, die messlauf-schreibweg.py unter der Sandbox prüft, sind genau die ReadWritePaths der Vorlage."""
    import importlib.machinery
    import importlib.util
    datei = BETRIEB / "messlauf-schreibweg.py"
    spec = importlib.util.spec_from_file_location("messlauf_schreibweg", datei,
                                                  loader=importlib.machinery.SourceFileLoader("messlauf_schreibweg", str(datei)))
    messlauf = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(messlauf)
    assert sorted(messlauf.SCHREIBZIELE) == sorted(_readwritepaths(_unit_zeilen("schreiben.service")))


ROOT_BEFEHLE = re.compile(r"(?:\$\{?(?:SUDO|FR_SUDO)\b[^ ]*|\bsudo(?:\s+-n)?)\s+(?:install|test|cat|rm|nginx|systemctl\s+reload)\b")


def test_nur_helfer_mit_sudo():
    """AC-8: In den Skripten des Betriebs (außer den Anleitungen von einrichten.sh) und in nginx.py ruft sudo nur die Helfer
    oder „systemctl restart“ der eigenen Dienste auf; freischalten.sh nutzt den Reise-Helfer."""
    for datei in sorted(BETRIEB.glob("*.sh")):
        if datei.name == "einrichten.sh":
            continue
        code = "\n".join(z for z in datei.read_text(encoding="utf-8").splitlines() if not z.lstrip().startswith("#"))
        treffer = ROOT_BEFEHLE.search(code)
        assert not treffer, (datei.name, treffer and treffer.group(0))
        assert "NGINX_TEST" not in code and "NGINX_LADEN" not in code, datei.name
    nginx_py = (BETRIEB / "nginx.py").read_text(encoding="utf-8")
    for verboten in ('sudo + ["cat"', 'sudo + ["install"', 'sudo + ["rm"'):
        assert verboten not in nginx_py, verboten
    frei = (BETRIEB / "freischalten.sh").read_text(encoding="utf-8")
    assert "nginx-reise-installieren" in frei and "FR_NGINX_REISE_HELFER" in frei


def _ei_env(tmp_path, **extra):
    return {**{k: v for k, v in SAUBER.items() if not k.startswith("EI_")}, "FR_WURZEL": str(tmp_path), "FR_INSTANZ": "probe",
            "FR_TITEL": "Probe", "FR_BENUTZER": "hans", "FR_GRUPPE": "hans", "FR_HOME": "/home/hans",
            "EI_ZIEL": str(tmp_path / "soll"), "EI_SYSTEMD": str(tmp_path / "systemd"),
            "FR_NGINX_SNIPPETS": str(tmp_path / "snippets"), "FR_KARTENDIENST_REGIONEN": "europe/andorra",
            "FR_KARTENDIENST_ORDNER": "/srv/probe/kartendienst", **extra}


NUR_HELFER = re.compile(r"NOPASSWD: (?:/usr/local/sbin/probe-[a-z-]+|/usr/bin/systemctl restart [a-z0-9 -]+)$")


def test_einrichten_helfer_und_karte(tmp_path):
    """AC-9: Helfer und Karte-Skript ohne offene Platzhalter; sudoers nur für Helfer; kein Docker für den Dienstbenutzer,
    aber ein eigener Benutzer probe-karte mit Gruppe docker."""
    env = _ei_env(tmp_path)
    r = subprocess.run(["bash", str(BETRIEB / "einrichten.sh"), "--erzeugen"], env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    sbin = tmp_path / "soll" / "sbin"
    for name in ("probe-nginx-reise-installieren", "probe-kartendienst"):
        assert (sbin / name).is_file(), name
        assert not re.search(r"__[A-Z_]+__", (sbin / name).read_text(encoding="utf-8")), name
    karte = (sbin / "probe-kartendienst").read_text(encoding="utf-8")
    # Das Karte-Skript liest weder betrieb.env noch etwas aus Ordnern des Dienstbenutzers oder dem Repo
    assert "betrieb.env" not in karte and str(tmp_path) not in karte and "/home/hans" not in karte
    r = subprocess.run(["bash", str(BETRIEB / "einrichten.sh")], env=env, capture_output=True, text=True)
    aus = r.stdout + r.stderr
    assert "NOPASSWD: /usr/local/sbin/probe-nginx-reise-installieren" in aus, aus
    assert f"sudo install -m 755 -o root -g root {sbin}/probe-nginx-reise-installieren /usr/local/sbin/" in aus
    assert f"{sbin}/probe-kartendienst" in aus
    assert not re.search(r"usermod -aG docker hans\b", aus), aus
    assert re.search(r"useradd\b.*probe-karte", aus), aus
    assert not re.search(r"sudo -n nginx -t|install/test/cat/rm", aus), aus
    for zeile in (z.strip() for z in aus.splitlines() if "NOPASSWD" in z):
        assert NUR_HELFER.search(zeile), zeile


def test_sperren_nicht_in_tmp(tmp_path):
    """AC-12: Ohne Einstellung liegen die Sperren in FR_DIENST, nie im gemeinsamen /tmp."""
    dienst = tmp_path / "dienst"
    r = subprocess.run(["bash", "-c", f'. "{BETRIEB}/gemeinsam.sh"; echo "$FR_SPERREN"'], capture_output=True, text=True,
                       env={**SAUBER, "FR_WURZEL": str(tmp_path), "FR_DIENST": str(dienst)})
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == str(dienst)
    for datei in ("gemeinsam.sh", "kartendienst.sh"):
        assert not re.search(r"SPERREN[^\n]*/tmp", (BETRIEB / datei).read_text(encoding="utf-8")), datei
    assert not re.search(r'"FR_SPERREN",\s*"/tmp"', (ENGINE / "schreiben.py").read_text(encoding="utf-8"))
    # Der Kartendienst öffnet die Sperre des Veröffentlichens nur lesend (er läuft unter eigenem Benutzer)
    karte = (BETRIEB / "kartendienst.sh").read_text(encoding="utf-8")
    assert re.search(r'exec 9<\s*"\$FR_DIENST/veroeffentlichen\.lock"', karte), "veroeffentlichen.lock nur lesend öffnen"


def test_doku_beschreibt_dienstrechte():
    """AC-19: docs/betrieb.md beschreibt Reise-Helfer, Kartendienst-Benutzer, Sandbox, Einmalschritt und die Warnung zum
    Admin-Benutzer und empfiehlt keine sudoers-Zeile für install, cat, rm oder nginx."""
    doku = (WURZEL / "docs" / "betrieb.md").read_text(encoding="utf-8")
    for soll in ("nginx-reise-installieren", "<instanz>-karte", "InaccessiblePaths", "ProtectHome=read-only",
                 "einrichten.sh --installieren"):
        assert soll in doku, soll
    for zeile in (z for z in doku.splitlines() if "NOPASSWD" in z):
        rest = zeile.split("NOPASSWD", 1)[1].replace("nginx-orte-installieren", "").replace("nginx-reise-installieren", "")
        assert not re.search(r"\b(?:install|cat|rm|nginx|test)\b", rest), zeile
    assert re.search(r"[Aa]dmin", doku)


def test_einrichten_installieren_attrappe(tmp_path):
    """AC-20 (Installationsweg): --installieren gegen eine sudo-Attrappe installiert Reise-Helfer, Units und eine sudoers-Datei
    nur mit Helfern; kein usermod -aG docker für den Dienstbenutzer."""
    repo = tmp_path / "repo"
    (repo / "betrieb").mkdir(parents=True)
    (repo / "betrieb/einstellungen.env").write_text("FR_INSTANZ=probe\nFR_TITEL=Probe\nFR_ADRESSE=https://example.invalid\n")
    (repo / "engine").symlink_to(ENGINE)
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", str(origin)], check=True)
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "remote", "add", "origin", str(origin)], check=True)
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    log = tmp_path / "sudo.log"
    ausfuehrbar(bin_ / "sudo", f'#!/bin/sh\nprintf "%s\\n" "$*" >> {log}\nexit 0\n')
    ausfuehrbar(bin_ / "gh", "#!/bin/sh\nexit 0\n")
    for name in ("rsync", "flock"):
        if not shutil.which(name):
            ausfuehrbar(bin_ / name, "#!/bin/sh\nexit 0\n")
    env = {**{k: v for k, v in SAUBER.items() if not k.startswith("EI_")}, "PATH": f"{bin_}:{SAUBER.get('PATH', '/usr/bin:/bin')}",
           "FR_WURZEL": str(repo), "FR_SEITEN": str(tmp_path / "srv/probe"), "EI_ZIEL": str(tmp_path / "aus"),
           "EI_SYSTEMD": str(tmp_path / "systemd"), "FR_BENUTZER": "reisen", "FR_GRUPPE": "reisen", "FR_HOME": "/home/reisen",
           "FR_PFAD": f"{bin_}:/usr/bin:/bin", "FR_PYTHON": sys.executable, "FR_NGINX_SNIPPETS": str(tmp_path / "snippets")}
    r = subprocess.run(["bash", str(BETRIEB / "einrichten.sh"), "--installieren"], input="ja\n", env=env, capture_output=True,
                       text=True, timeout=120)
    assert r.returncode == 0 and "Installed." in r.stdout, r.stdout + r.stderr
    befehle = log.read_text().splitlines()
    aus = tmp_path / "aus"
    assert f"install -m 755 -o root -g root {aus}/sbin/probe-nginx-reise-installieren /usr/local/sbin/" in befehle, befehle
    assert any(b.startswith("install -m 644") and str(tmp_path / "systemd") in b for b in befehle), befehle
    assert not [b for b in befehle if re.search(r"usermod -aG docker reisen\b", b)], befehle
    sudoers = next((Path(b.split()[-2]) for b in befehle if b.startswith("install") and "/etc/sudoers.d/" in b), None)
    assert sudoers is not None and sudoers.is_file(), befehle
    text = sudoers.read_text()
    assert "probe-nginx-reise-installieren" in text
    for zeile in (z.strip() for z in text.splitlines() if "NOPASSWD" in z):
        assert NUR_HELFER.search(zeile), zeile
