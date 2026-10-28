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
import einarbeiten_hilfe as hilfe  # noqa: E402
import rueckmeldungen as rm  # noqa: E402

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
             "KN_SEITEN", "KN_ZUGAENGE", "KN_BASIS", "FR_ADRESSE", "FR_BETREIBER"]
    skript = f'. "{BETRIEB}/gemeinsam.sh"; ' + "; ".join(f'echo "{n}=${{{n}:-}}"' for n in namen)
    r = subprocess.run(["bash", "-c", skript], capture_output=True, text=True,
                       env={**SAUBER, "FR_WURZEL": str(tmp_path), **umgebung})
    return r, dict(z.split("=", 1) for z in r.stdout.splitlines() if "=" in z)


def test_einstellungen_aus_datei_mit_vorgaben(tmp_path):
    r, w = einstellungen(tmp_path, "# Kommentar\nFR_INSTANZ=probe\nFR_ADRESSE=\"https://reisen.example.org\"\n"
                                   "FR_BETREIBER=Ida und Karl\nFR_TITEL=$(touch boese)\n")
    assert r.returncode == 0, r.stderr
    assert w["FR_INSTANZ"] == "probe" and w["FR_SEITEN"] == "/srv/probe" and w["FR_ABLAGE"] == "/srv/probe/_rueckmeldungen"
    assert w["RM_ABLAGE"] == "/srv/probe/_rueckmeldungen" and w["KN_ZUGAENGE"] == "/srv/probe/_konnektor/zugaenge.json"
    assert w["FR_KN_ADRESSE"] == w["KN_BASIS"] == "https://reisen.example.org/probe-mcp"
    assert w["FR_BETREIBER"] == "Ida und Karl" and w["FR_PYTHON"] == f"{tmp_path}/engine/.venv/bin/python"
    # keine Shell-Auswertung: der Wert bleibt Text, es wird nichts ausgeführt
    assert w["FR_TITEL"] == "$(touch boese)" and not (Path.cwd() / "boese").exists()


def test_umgebung_gilt_vor_der_datei_und_fremdes_wird_ignoriert(tmp_path):
    r, w = einstellungen(tmp_path, "FR_INSTANZ=probe\nPATH=/nirgends\nRM_ABLAGE=/falsch\nFR_SEITEN=/srv/datei\n",
                         FR_SEITEN="/srv/umgebung")
    assert r.returncode == 0 and w["FR_SEITEN"] == "/srv/umgebung" and w["RM_ABLAGE"] == "/srv/umgebung/_rueckmeldungen"
    assert "Zeile ignoriert" in r.stderr and "PATH" in r.stderr


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
    assert r.returncode != 0 and "Wurzel der Instanz" in r.stderr


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
    """Origin mit main, Veröffentlichungsordner als Klon, Deploy-Attrappe, die jede Reise protokolliert."""
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
    attrappe = ausfuehrbar(tmp_path / "deploy.sh", f'#!/bin/sh\necho "$1" >> {protokoll}\necho "$FR_GEPRUEFT" >> {tmp_path}/gepreuft.log\n'
                                                   f'[ -e {tmp_path}/kaputt ] && exit 1\nexit 0\n')
    pruefen = ausfuehrbar(tmp_path / "pruefen.sh", f'#!/bin/sh\necho p >> {tmp_path}/pruefen.log\n[ ! -e {tmp_path}/rot ]\n')
    # curl-Attrappe: protokolliert Heartbeat-Abrufe statt ins Netz zu gehen
    pings = tmp_path / "pings.log"
    ausfuehrbar(tmp_path / "bin/curl", f'#!/bin/sh\necho ping >> {pings}\n')
    frei = ausfuehrbar(tmp_path / "freischalten.sh",
                       f'#!/bin/sh\necho "$1" >> {tmp_path}/frei.log\necho "Seite: https://example.invalid/$1-geheim/"\n')
    env = {**SAUBER, "FR_WURZEL": str(arbeit), "FR_INSTANZ": "probe", "FR_DIENST": str(tmp_path / "dienst"),
           "FR_SPERREN": str(tmp_path), "VF_DEPLOY": str(attrappe), "VF_PRUEFEN": str(pruefen), "VF_FREISCHALTEN": str(frei),
           "FR_HEARTBEAT_VEROEFFENTLICHEN": "https://example.invalid/hb", "PATH": f"{tmp_path / 'bin'}:{os.environ['PATH']}"}

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

    return {"lauf": lauf, "deploys": deploys, "pings": anzahl_pings, "neuer_commit": neuer_commit, "arbeit": arbeit,
            "tmp": tmp_path, "env": env}


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
    (vf["tmp"] / "kaputt").touch()
    assert vf["lauf"]().returncode == 1
    vf["deploys"]()
    (vf["tmp"] / "kaputt").unlink()
    assert vf["lauf"]().returncode == 0
    assert vf["deploys"]() == ["beispielreise", "zweitreise"]


def test_veroeffentlichen_prueft_einmal_fuer_alle_reisen(vf):
    """Die Prüfungen laufen einmal je Lauf, nicht je Reise; deploy.sh bekommt den geprüften Stand und prüft nicht nochmal.
    Rote Prüfungen: keine Reise wird angefasst, der Stand bleibt ungemerkt, der nächste Lauf versucht es wieder."""
    (vf["tmp"] / "rot").touch()
    r = vf["lauf"]()
    assert r.returncode == 1 and "Prüfungen rot" in r.stdout and vf["deploys"]() == []
    assert not (vf["tmp"] / "dienst/veroeffentlicht").exists()
    (vf["tmp"] / "rot").unlink()
    assert vf["lauf"]().returncode == 0
    assert vf["deploys"]() == ["beispielreise", "zweitreise"]
    assert (vf["tmp"] / "pruefen.log").read_text().split() == ["p", "p"]
    kopf = git(vf["arbeit"], "rev-parse", "HEAD").strip()
    assert (vf["tmp"] / "gepreuft.log").read_text().split() == [kopf, kopf]
    deploy = (BETRIEB / "deploy.sh").read_text(encoding="utf-8")
    assert 'if [ "${FR_GEPRUEFT:-}" != "$(git -C "$WURZEL" rev-parse HEAD)" ]; then' in deploy


def test_veroeffentlichen_laesst_laufende_arbeit_in_ruhe(vf):
    (vf["arbeit"] / "entwurf.md").write_text("halb fertig")
    erg = vf["lauf"]()
    assert erg.returncode == 0 and "Ungesicherte" in erg.stdout
    assert vf["deploys"]() == []
    (vf["arbeit"] / "entwurf.md").unlink()
    git(vf["arbeit"], "checkout", "-qb", "baustelle")
    erg = vf["lauf"]()
    assert erg.returncode == 0 and "nicht auf main" in erg.stdout
    assert vf["deploys"]() == []


def test_veroeffentlichen_heartbeat_nur_bei_erfolg(vf):
    (vf["tmp"] / "kaputt").touch()
    assert vf["lauf"]().returncode == 1
    assert vf["pings"]() == 0                                  # Deploy fehlgeschlagen
    (vf["tmp"] / "kaputt").unlink()
    assert vf["lauf"]().returncode == 0
    assert vf["pings"]() == 1                                  # veröffentlicht
    assert vf["lauf"]().returncode == 0
    assert vf["pings"]() == 1                                  # nichts Neues, Abruf gelungen
    (vf["arbeit"] / "entwurf.md").write_text("halb fertig")
    assert vf["lauf"]().returncode == 0
    assert vf["pings"]() == 0                                  # übersprungen


def test_veroeffentlichen_stempel_nur_bei_erfolg(vf):
    stempel = vf["tmp"] / "dienst" / "veroeffentlichen-erfolg"
    (vf["tmp"] / "kaputt").touch()
    assert vf["lauf"]().returncode == 1
    assert not stempel.exists()                                # Deploy fehlgeschlagen
    (vf["tmp"] / "kaputt").unlink()
    assert vf["lauf"]().returncode == 0
    assert stempel.exists()                                    # veröffentlicht
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
        assert "Läuft schon" not in vf["lauf"]().stdout
    with open(vf["tmp"] / "probe-veroeffentlichen.lock", "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        assert "Läuft schon" in vf["lauf"]().stdout


def test_veroeffentlichen_freischalten_je_reise_ohne_links_im_protokoll(vf):
    """Nach dem Veröffentlichen wird jede Reise freigeschaltet (neue bekommen ihren Link); die Links stehen nie im
    Protokoll. Ausstehende Links neuer Reisen werden auch ohne neuen Stand zugestellt."""
    r = vf["lauf"]()
    assert r.returncode == 0
    assert (vf["tmp"] / "frei.log").read_text().split() == ["beispielreise", "zweitreise"]
    assert "geheim" not in r.stdout + r.stderr
    py = ausfuehrbar(vf["tmp"] / "python.sh", f'#!/bin/sh\necho "$@" >> {vf["tmp"]}/zustellen.log\n')
    (vf["tmp"] / "dienst/neue-reisen-ausstehend.jsonl").write_text('{"ordner": "neu"}\n')
    r = vf["lauf"](FR_PYTHON=str(py))
    assert r.returncode == 0, r.stdout + r.stderr
    assert f"{BETRIEB}/einarbeiten_hilfe.py ausstehend" in (vf["tmp"] / "zustellen.log").read_text()


# ---------- Deploy ----------

def _deploy_liste(name):
    deploy = (BETRIEB / "deploy.sh").read_text(encoding="utf-8")
    return set(re.search(rf'^{name}="([^"]*)"', deploy, re.M).group(1).split())


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


def test_deploy_kopiert_friedas_symbol():
    deploy = (BETRIEB / "deploy.sh").read_text(encoding="utf-8")
    assert '"$WURZEL/engine/marke/" "$DIENST/marke/"' in deploy


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
    assert "Freigeschaltet: beispielreise" in r.stdout and f"Seite: https://example.invalid/{pfad}/" in r.stdout
    assert fs["abrufe"].read_text().split() == [f"https://example.invalid/{pfad}/", f"https://example.invalid/{pfad}/api/gesund"]
    assert (fs["tmp"] / "nginx.log").read_text().split("\n")[:2] == ["-t", "reload"]
    links = fs["tmp"] / "konnektor/seiten.json"
    assert json.loads(links.read_text()) == {"beispielreise": f"https://example.invalid/{pfad}/"}
    assert stat.S_IMODE(links.stat().st_mode) == 0o600
    # zweiter Aufruf: derselbe Link, kein neues Laden von nginx
    r = fs["lauf"]("beispielreise")
    assert r.returncode == 0 and "Freigeschaltet" not in r.stdout and sn.read_text() == inhalt
    assert (fs["tmp"] / "nginx.log").read_text().count("reload") == 1


def test_freischalten_wartet_auf_das_neuladen_von_nginx(fs):
    """Gleich nach dem Neuladen kennt nginx den neuen Pfad noch nicht (404); ein neuer Link wird mehrmals versucht."""
    zaehler = fs["tmp"] / "zaehler"
    fs["env"]["FS_ABRUF"] = str(ausfuehrbar(fs["tmp"] / "abruf-langsam.sh",
        f'#!/bin/sh\necho x >> {zaehler}\n[ $(wc -l < {zaehler}) -le 2 ] && echo 404 || echo 200\n'))
    r = fs["lauf"]("beispielreise")
    assert r.returncode == 0 and "Freigeschaltet: beispielreise" in r.stdout, r.stdout
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
    assert r.returncode == 1 and "nginx lehnt die Konfiguration ab" in r.stdout
    assert not list(fs["snippets"].iterdir()) and "reload" not in (fs["tmp"] / "nginx.log").read_text()


def test_freischalten_seite_nicht_erreichbar_ist_fehler_ohne_link_im_protokoll(fs):
    fs["code"].write_text("404")
    r = fs["lauf"]("beispielreise")
    assert r.returncode == 1 and "Seite von beispielreise antwortet mit 404" in r.stdout and "fehlt das include" in r.stdout
    token = (fs["snippets"] / "probe-beispielreise.conf").read_text().split("beispielreise-", 1)[1][:24]
    assert token not in r.stdout + r.stderr


def test_freischalten_unbekannte_reise_und_fehlende_adresse(fs):
    assert "gibt es nicht" in fs["lauf"]("gibts-nicht").stdout
    assert "nur Kleinbuchstaben" in fs["lauf"]("Böse;rm").stdout
    r = subprocess.run([str(BETRIEB / "freischalten.sh"), "beispielreise"], capture_output=True, text=True,
                       env={**fs["env"], "FR_ADRESSE": "", "FR_KN_ADRESSE": ""})
    assert r.returncode == 1 and "FR_ADRESSE ist nicht gesetzt" in r.stdout


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
    assert hilfe.ausstehend(fs["repo"], datei) == 0
    out = capsys.readouterr().out
    assert "Zugestellt: beispielreise an Ida" in out and "https://" not in out      # Links nie ins Protokoll
    assert [json.loads(z)["ordner"] for z in datei.read_text().splitlines()] == ["spaeter"]
    m = rm.meldungen(rm.ordner_neu(), "Ida")[0]
    assert m["art"] == "neue_reise" and m["auftraege"] == ["A-1"]
    assert "„Beispielreise – Malerweg in vier Tagen“ ist angelegt" in m["text"]
    assert "Seite: https://example.invalid/beispielreise-" in m["text"] and "https://example.invalid/mcp/" in m["text"]
    # Freischalten scheitert: Eintrag bleibt, Fehlerzeile ohne Links
    (fs["seiten"] / "spaeter").mkdir()
    (fs["seiten"] / "spaeter" / "daten.json").write_text("{}")
    assert hilfe.ausstehend(fs["repo"], datei) == 1
    out = capsys.readouterr().out
    assert "FEHLER: spaeter nicht freigeschaltet" in out and "https://" not in out
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
        "einladen": [{"schluessel": "karl", "email": "karl@example.invalid", "rolle": "einbringer", "name": "Karl"}]}) + "\n")
    datei = fs["tmp"] / "ausstehend.jsonl"
    datei.write_text(json.dumps({"ordner": "beispielreise", "aid": "A-1", "name": "Ida", "person": "ida"}) + "\n")
    assert hilfe.ausstehend(fs["repo"], datei) == 0
    out = capsys.readouterr().out
    assert "Zugestellt: beispielreise an Ida" in out and "@" not in out
    assert datei.read_text() == ""
    assert konten.mitglied(ida["id"], "beispielreise") == "ida"
    einl = [json.loads(z) for z in (fs["tmp"] / "mails.jsonl").read_text().splitlines() if "karl@" in z]
    assert len(einl) == 1 and "Ida hat dich zur Reise" in einl[0]["text"]
    m = rm.meldungen(rm.ordner_neu(), "Ida")[-1]
    assert "steht in meine_reisen" in m["text"] and "Einladungen per Mail an 1 Person" in m["text"]
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
    assert (prio, erledigt) == ("normal", "erledigt") and betreff == "Probe: Wächter und Erinnerer"
    assert "Karl: Frist morgen." in text


def test_waechter_ohne_meldeweg_keine_nachricht(wa):
    r, nachrichten = wa(WA_BERICHT="Beispiel: Karl: Frist morgen.", FR_MELDEN="")
    assert r.returncode == 0 and nachrichten == []


def test_waechter_fehler_meldet_sich_und_laesst_den_stempel_aus(wa):
    r, nachrichten = wa(WA_FEHLER="1")
    assert r.returncode == 1 and not wa.stempel.exists()
    assert len(nachrichten) == 1 and nachrichten[0].split("|")[0] == "high" and "fehlgeschlagen" in nachrichten[0]
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
    assert namen == ["probe-einarbeiten.path", "probe-einarbeiten.service", "probe-einarbeiten.timer",
                     "probe-konnektor.service", "probe-rueckmeldungen.service", "probe-veroeffentlichen.service",
                     "probe-veroeffentlichen.timer", "probe-waechter.service", "probe-waechter.timer"]
    for p in [*(aus / "systemd").iterdir(), *(aus / "nginx").iterdir()]:
        assert not re.search(r"__[A-Z_]+__", p.read_text()), p.name
    srv = tmp_path / "srv/probe"
    einh = {p.name: p.read_text() for p in (aus / "systemd").iterdir()}
    assert f"PathModified={srv}/_rueckmeldungen/.neu" in einh["probe-einarbeiten.path"]
    assert "Unit=probe-einarbeiten.service" in einh["probe-einarbeiten.path"]
    assert f"ExecStart={tmp_path}/repo/frieda/betrieb/einarbeiten.sh" in einh["probe-einarbeiten.service"]
    assert f"Environment=FR_WURZEL={tmp_path}/repo" in einh["probe-einarbeiten.service"]
    assert "User=reisen" in einh["probe-einarbeiten.service"] and "/home/reisen/.local/bin" in einh["probe-einarbeiten.service"]
    assert "Environment=KN_PORT=8772" in einh["probe-konnektor.service"]
    assert "Environment=KN_BASIS=https://example.invalid/probe-mcp" in einh["probe-konnektor.service"]
    assert f"ExecStart=/usr/bin/python3 {srv}/_dienst/konnektor.py dienst" in einh["probe-konnektor.service"]
    assert "OnCalendar=" in einh["probe-waechter.timer"] and "Persistent=true" in einh["probe-waechter.timer"]
    nginx = (aus / "nginx/probe-konnektor.conf").read_text()
    assert "location ^~ /probe-mcp/" in nginx and "zone=probe_api" in nginx and "127.0.0.1:8772/" in nginx
    assert "zone=probe_api:10m" in (aus / "nginx/probe-zone.conf").read_text()
    assert "sudo systemctl enable --now probe-veroeffentlichen.timer" in r.stdout
    # ohne --installieren wird außerhalb des Ausgabeordners nichts angelegt
    assert not (tmp_path / "srv").exists() and not (tmp_path / "systemd").exists()


def test_einrichten_erkennt_belegte_ports_einer_anderen_instanz(tmp_path):
    (tmp_path / "systemd").mkdir()
    (tmp_path / "systemd/andere-rueckmeldungen.service").write_text("[Service]\nEnvironment=RM_PORT=8771\n")
    r = einrichten(tmp_path)
    assert r.returncode == 2 and "Port 8771 oder 8772 nutzt schon andere-rueckmeldungen.service" in r.stdout
    r = einrichten(tmp_path, FR_RM_PORT="8781", FR_KN_PORT="8782")
    assert "nutzt schon" not in r.stdout
    # die eigene Instanz zählt nicht als andere
    (tmp_path / "systemd/andere-rueckmeldungen.service").rename(tmp_path / "systemd/probe-rueckmeldungen.service")
    assert "nutzt schon" not in einrichten(tmp_path).stdout


def test_einrichten_installiert_nur_nach_bestaetigung(tmp_path):
    """Mit --installieren fragt das Skript; ohne „ja“ (oder mit fehlenden Voraussetzungen) ändert es nichts."""
    vorher = einrichten(tmp_path, FR_RM_PORT="8781").returncode
    r = subprocess.run([str(BETRIEB / "einrichten.sh"), "--installieren"], input="nein\n", capture_output=True, text=True,
                       env={**SAUBER, "FR_WURZEL": str(tmp_path / "repo"), "FR_SEITEN": str(tmp_path / "srv/probe"),
                            "EI_ZIEL": str(tmp_path / "aus"), "EI_SYSTEMD": str(tmp_path / "systemd"), "FR_RM_PORT": "8781"})
    if vorher == 2:
        assert r.returncode == 1 and "Voraussetzung(en) fehlen" in r.stdout
    else:
        assert r.returncode == 0 and "Nichts installiert." in r.stdout
    assert not (tmp_path / "srv").exists() and not (tmp_path / "systemd").exists()


def test_vorlagen_ohne_werte_einer_instanz():
    """Der Betrieb kennt keine Instanz: keine Adressen, Benutzer, Pfade oder Namen einer echten Installation."""
    verboten = re.compile(r"/home/(?!reisen\b)\w+|/srv/(?!probe\b|beispiel\b|<)\w+|\b(?:www\.)?\w+\.(?:com|de|net)\b",
                          re.I)
    for p in sorted(BETRIEB.rglob("*")):
        if p.is_file() and p.suffix not in (".pyc",):
            text = p.read_text(encoding="utf-8")
            treffer = [t for t in verboten.findall(text) if "example" not in t and "anthropic" not in t and "claude" not in t]
            assert treffer == [], (p.name, treffer)


def test_einarbeiten_auftrag_kennt_pruefauftraege_und_grenzen():
    prompt = (BETRIEB / "einarbeiten-auftrag.md").read_text(encoding="utf-8")
    assert "Prüfaufträge:" in prompt and "NICHT" in prompt and "offene Frage" in prompt
    assert "__REISE__" in prompt and "__IDS__" in prompt and "__AUS__" in prompt
    assert "Nur reisen/__REISE__/ ändern" in prompt and "test_reisen" not in prompt


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


def test_einrichten_prueft_anmeldung_von_claude(tmp_path):
    bin_ = tmp_path / "bin"
    ausfuehrbar(bin_ / "claude", '#!/bin/sh\n[ "$1 $2" = "auth status" ] && echo \'{"loggedIn": \'"$ANGEMELDET"\'}\'\n')
    pfad = f"{bin_}:/usr/bin:/bin"
    assert "FEHLT   Claude Code ist nicht angemeldet" in einrichten(tmp_path, FR_PFAD=pfad, ANGEMELDET="false").stdout
    assert "ok      Claude Code angemeldet" in einrichten(tmp_path, FR_PFAD=pfad, ANGEMELDET="true").stdout
