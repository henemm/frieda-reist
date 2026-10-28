"""Tests für betrieb/einarbeiten.sh und betrieb/einarbeiten_hilfe.py (docs/betrieb.md, Einarbeiten): Eingang, Sammelzeit,
ein Lauf zur Zeit, ein KI-Lauf je Reise mit eingegrenzten Rechten, Veröffentlichen am Ende, Fehlerfälle.
Die Instanz ist ein Wegwerf-Repo mit zwei erfundenen Reisen; KI, gh, Meldeweg und Veröffentlichen sind Attrappen."""
import datetime
import fcntl
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest
import yaml

WURZEL = Path(__file__).resolve().parents[2]
ENGINE = WURZEL / "engine"
BETRIEB = WURZEL / "betrieb"
BEISPIEL = WURZEL / "beispiel" / "reisen" / "beispielreise"
sys.path.insert(0, str(BETRIEB))
sys.path.insert(0, str(ENGINE))
import einarbeiten_hilfe as hilfe  # noqa: E402

GIT = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}


def git(ordner, *args):
    return subprocess.run(["git", "-C", str(ordner), *args], check=True, capture_output=True, text=True,
                          env={**os.environ, **GIT}).stdout.strip()


def jetzt(sekunden=0):
    return (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=sekunden)).isoformat(timespec="seconds")


def schreibe(pfad, text, ausfuehrbar=False):
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(text)
    if ausfuehrbar:
        pfad.chmod(0o755)


@pytest.fixture
def u(tmp_path):
    """Origin (bare), Veröffentlichungsordner „quelle“ mit den Reisen beispiel und zweite, Rückmelde-Ablage, Attrappen."""
    if not shutil.which("flock"):
        pytest.skip("flock fehlt")
    roh = tmp_path / "roh"
    for reise in ("beispiel", "zweite"):
        schreibe(roh / f"reisen/{reise}/reise.json", "{}")
        schreibe(roh / f"reisen/{reise}/reise.yaml", "regeln:\n  sammelzeit_minuten: 4\n")
        schreibe(roh / f"reisen/{reise}/notizen.md", "start\n")
    (roh / "engine").symlink_to(ENGINE)   # die Software, wie im Reisen-Repo über das Submodul
    git(roh, "init", "-q", "-b", "main")
    git(roh, "add", "-A")
    git(roh, "commit", "-qm", "start")
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "clone", "-q", "--bare", str(roh), str(origin)], check=True)
    quelle = tmp_path / "quelle"
    subprocess.run(["git", "clone", "-q", str(origin), str(quelle)], check=True)

    ablage = tmp_path / "ablage"
    for reise in ("beispiel", "zweite"):
        (ablage / reise).mkdir(parents=True)
    dienst = tmp_path / "dienst"
    dienst.mkdir()
    bin_ = tmp_path / "bin"
    # gh: PR anlegen/zusammenführen = Branch in origin/main vorspulen
    schreibe(bin_ / "gh", f'''#!/bin/sh
case "$1 $2" in
  "pr create") while [ $# -gt 0 ]; do [ "$1" = --head ] && echo "$2" > {tmp_path}/pr-branch; shift; done; echo https://example.invalid/pr/1;;
  "pr merge") t=$(mktemp -d); git clone -q {origin} $t; cd $t; b=origin/$(cat {tmp_path}/pr-branch)
    git merge -q --ff-only $b && git push -q origin HEAD:main;;
  "pr view") case "$*" in *mergeCommit*) git -C {origin} rev-parse main;; *) echo MERGED;; esac;;
esac
''', True)
    # Python: Bauen gelingt, Tests nach Wunsch rot, alles andere echt (Hilfen, Rückmeldedienst)
    schreibe(tmp_path / "python", f'''#!/bin/sh
case "$1 $2" in "-m pytest") [ -e {tmp_path}/rot ] && exit 1; exit 0;; esac
case "$1" in */bauen.py|engine/bauen.py) exit 0;; esac
exec {sys.executable} "$@"
''', True)
    schreibe(tmp_path / "claude", f'''#!/bin/sh
# Attrappe: zählt Aufrufe, merkt Auftrag und Schalter, schreibt Status und Bericht, ändert eine Datei der Reise
echo run >> {tmp_path}/claude-laeufe
n=$(wc -l < {tmp_path}/claude-laeufe)
printf '%s\\n' "$@" > {tmp_path}/args-$n
printf '%s' "$2" > {tmp_path}/prompt-$n
aus=$(printf '%s' "$2" | grep -o '/[^ ]*[.]einarbeiten/[a-z0-9-]*' | head -1)
reise=$(basename "$aus")
echo "$reise" > {tmp_path}/reise-$n
if [ -e {tmp_path}/claude-kaputt ] || [ -e {tmp_path}/claude-kaputt-$reise ]; then echo "halb" >> reisen/$reise/notizen.md; exit 1; fi
if [ -e {tmp_path}/nachzuegler ]; then cat {tmp_path}/nachzuegler >> {ablage}/beispiel/eingang.jsonl; rm {tmp_path}/nachzuegler; fi
echo "$(date +%s)" >> reisen/$reise/notizen.md
if [ -e {tmp_path}/uebergriff ]; then echo boese >> reisen/zweite/notizen.md; echo boese > ausserhalb.txt; fi
grep "^$reise	" {tmp_path}/status.tsv > "$aus/status.tsv" || true
printf 'Test eingearbeitet\\n\\n- etwas in %s\\n' "$reise" > "$aus/bericht.md"
echo 'Warnung auf stderr' >&2
echo '{{"total_cost_usd":0.5,"is_error":false}}'
''', True)
    schreibe(tmp_path / "melden.sh", f'#!/bin/sh\nprintf "%s|%s|%s|%s\\n" "$1" "$2" "$(printf %s "$3" | tr "\\n" " ")" "$4" >> {tmp_path}/mq.log\n', True)
    schreibe(tmp_path / "veroeffentlichen.sh",
             f'#!/bin/sh\n[ -e {tmp_path}/belegt ] && {{ echo "Läuft schon, übersprungen."; exit 0; }}\n'
             f'git -C {quelle} pull -q --ff-only origin main\ngit -C {quelle} rev-parse HEAD > {dienst}/veroeffentlicht\n', True)
    env = {**os.environ, **GIT, "PATH": f"{bin_}:{os.environ['PATH']}",
           "FR_WURZEL": str(quelle), "FR_EINSTELLUNGEN": str(tmp_path / "keine.env"), "FR_INSTANZ": "probe",
           "FR_TITEL": "Probe", "FR_SEITEN": str(tmp_path / "seiten"), "FR_ABLAGE": str(ablage), "FR_DIENST": str(dienst),
           "RM_ABLAGE": str(ablage), "FR_PYTHON": str(tmp_path / "python"), "FR_CLAUDE": str(tmp_path / "claude"),
           "FR_MELDEN": str(tmp_path / "melden.sh"), "FR_BETREIBER": "Ida", "FR_SPERREN": str(tmp_path),
           "FR_MAX_WARTEN_MIN": "12", "EA_SEKUNDEN_JE_MINUTE": "1",
           "EA_ARBEIT": str(tmp_path / "auto"), "EA_VEROEFFENTLICHEN": str(tmp_path / "veroeffentlichen.sh"),
           "VF_STAND": str(dienst / "veroeffentlicht"), "EA_AUSSTEHEND": str(dienst / "ausstehend.jsonl")}
    for k in ("KN_SEITEN", "KN_ZUGAENGE", "KN_BASIS", "RM_LAEUFE"):
        env.pop(k, None)

    def eingabe(rid, erstellt=None, art="Kommentar"):
        e = {"id": rid, "erstellt": erstellt or jetzt(), "name": "Ida", "art": art, "ziel": "T-01", "text": "Hallo", "quelle": ""}
        return json.dumps(e, ensure_ascii=False) + "\n"

    def lege_ein(rid, reise="beispiel", **kw):
        with (ablage / reise / "eingang.jsonl").open("a") as f:
            f.write(eingabe(rid, **kw))

    def lauf(**extra):
        return subprocess.run([str(BETRIEB / "einarbeiten.sh")], env={**env, **{k: str(v) for k, v in extra.items()}},
                              capture_output=True, text=True, timeout=120)

    def status(rid, reise="beispiel"):
        p = ablage / reise / "status.json"
        return json.loads(p.read_text()).get(rid, {}) if p.exists() else {}

    def zeilen(name):
        p = tmp_path / name
        return p.read_text().splitlines() if p.exists() else []

    schreibe(tmp_path / "status.tsv", "beispiel\tR-1\tuebernommen\tSteht jetzt in den Notizen.\nbeispiel\tR-2\tverworfen\tPasst nicht.\n")
    return {"lauf": lauf, "lege_ein": lege_ein, "eingabe": eingabe, "status": status, "tmp": tmp_path, "ablage": ablage,
            "dienst": dienst, "quelle": quelle, "origin": origin, "zeilen": zeilen, "env": env}


def laeufe(u):
    p = u["dienst"] / "einarbeiten-laeufe.jsonl"
    return [json.loads(z) for z in p.read_text().splitlines()] if p.exists() else []


def test_nichts_neues_startet_keine_ki(u):
    r = u["lauf"]()
    assert r.returncode == 0 and "Nichts Neues" in r.stdout
    assert u["zeilen"]("claude-laeufe") == [] and (u["dienst"] / "einarbeiten-erfolg").exists()


def test_eingang_bis_online_und_status(u):
    u["lege_ein"]("R-1", erstellt=jetzt(-30))
    r = u["lauf"]()
    assert r.returncode == 0, r.stdout + r.stderr
    assert len(u["zeilen"]("claude-laeufe")) == 1
    # eingearbeitet, zusammengeführt, veröffentlicht: der Stand enthält den Merge von origin
    assert (u["dienst"] / "veroeffentlicht").read_text().strip() == git(u["origin"], "rev-parse", "main")
    assert git(u["origin"], "log", "-1", "--format=%s") == "Test eingearbeitet"
    # Status mit Kommentar steht beim Absender (Rückmeldedienst liest status.json)
    assert u["status"]("R-1")["status"] == "uebernommen" and u["status"]("R-1")["kommentar"]
    z = laeufe(u)
    assert len(z) == 1 and z[0]["ergebnis"] == "ok" and z[0]["kosten_usd"] == 0.5 and z[0]["online"] == "ja"
    assert z[0]["anzahl"] == 1 and z[0]["eingabe_bis_ende_s"] >= 30
    bericht = [x for x in u["zeilen"]("mq.log") if x.startswith("normal|")]
    assert len(bericht) == 1 and "Probe: 1 Einträge bearbeitet" in bericht[0] and bericht[0].endswith("|erledigt")
    assert "Online." in bericht[0]
    # beim zweiten Mal ist nichts mehr neu
    assert "Nichts Neues" in u["lauf"]().stdout and len(u["zeilen"]("claude-laeufe")) == 1


def test_ki_lauf_je_reise_mit_eingegrenzten_rechten(u):
    """Je Reise ein eigener KI-Lauf: Auftrag nur mit deren IDs, Schreiben nur in deren Ordner, die andere Reise und die
    Ablage sind nicht lesbar, Befehle nur für diese Reise. Ein Commit und ein PR für beide."""
    u["lege_ein"]("R-1", erstellt=jetzt(-60))
    u["lege_ein"]("R-7", reise="zweite", erstellt=jetzt(-60))
    schreibe(u["tmp"] / "status.tsv", "beispiel\tR-1\tuebernommen\tok\nzweite\tR-7\tverworfen\tPasst nicht.\n"
                                      "zweite\tR-1\tverworfen\tfalsche Reise\n")
    r = u["lauf"]()
    assert r.returncode == 0, r.stdout + r.stderr
    assert u["zeilen"]("claude-laeufe") == ["run", "run"]
    for n in (1, 2):
        reise = u["zeilen"](f"reise-{n}")[0]
        andere = {"beispiel": "zweite", "zweite": "beispiel"}[reise]
        prompt = (u["tmp"] / f"prompt-{n}").read_text()
        args = u["zeilen"](f"args-{n}")
        assert f"Reise {reise} einarbeiten" in prompt and "__" not in prompt
        assert ("R-1" in prompt) == (reise == "beispiel") and ("R-7" in prompt) == (reise == "zweite")
        erlaubt = args[args.index("--allowedTools") + 1:args.index("--disallowedTools")]
        verboten = args[args.index("--disallowedTools") + 1:]
        assert f"Edit(/{u['tmp']}/auto/reisen/{reise}/**)" in erlaubt
        assert not [a for a in erlaubt if a.startswith("Edit(") and "/reisen/" in a and f"/reisen/{reise}/" not in a]
        assert f"Bash(python3 engine/rueckmeldungen.py liste {reise})" in erlaubt
        assert not [a for a in erlaubt if a.startswith("Bash(") and not a.endswith(f" {reise})")]
        assert f"Read(/{u['tmp']}/auto/reisen/{andere}/**)" in verboten
        assert f"Read(/{u['tmp']}/quelle/reisen/{andere}/**)" in verboten
        assert f"Read(/{u['ablage']}/**)" in verboten and not [v for v in verboten if f"/reisen/{reise}/" in v]
    # ein Commit für beide Reisen, Status nur aus der eigenen Reise
    assert git(u["origin"], "log", "-1", "--format=%s") == "Rückmeldungen eingearbeitet: beispiel, zweite"
    assert git(u["origin"], "rev-list", "--count", "main") == "2"
    assert u["status"]("R-1")["status"] == "uebernommen" and u["status"]("R-7", "zweite")["status"] == "verworfen"
    assert u["status"]("R-1", "zweite") == {} and "Übersprungen (nicht in diesem Lauf von zweite): zweite R-1" in r.stdout
    assert laeufe(u)[0]["kosten_usd"] == 1.0 and laeufe(u)[0]["reisen"] == "beispiel zweite"


def test_aenderungen_ausserhalb_der_reise_werden_verworfen(u):
    u["lege_ein"]("R-1", erstellt=jetzt(-60))
    schreibe(u["tmp"] / "uebergriff", "")
    r = u["lauf"]()
    assert r.returncode == 0, r.stdout + r.stderr
    assert "Verworfen (außerhalb von reisen/beispiel/): ausserhalb.txt reisen/zweite/notizen.md" in r.stdout
    git(u["quelle"], "pull", "-q")
    assert (u["quelle"] / "reisen/zweite/notizen.md").read_text() == "start\n"
    assert not (u["quelle"] / "ausserhalb.txt").exists()
    assert (u["quelle"] / "reisen/beispiel/notizen.md").read_text() != "start\n"
    assert any("außerhalb der Reise verworfen" in x for x in u["zeilen"]("mq.log"))


def test_sammelzeit_buendelt_eingaben_in_einen_lauf(u):
    # Reichlich Luft (Sammelzeit 4 s, zweite Eingabe nach 1 s), damit ein langsamer Rechner den Test nicht kippt
    u["lege_ein"]("R-1")
    threading.Timer(1.0, u["lege_ein"], args=("R-2",)).start()
    t0 = time.time()
    r = u["lauf"]()
    assert r.returncode == 0, r.stdout + r.stderr
    assert time.time() - t0 >= 4.5  # 1 s + 4 s Sammelzeit nach der letzten Eingabe
    assert len(u["zeilen"]("claude-laeufe")) == 1 and "Sammelzeit" in r.stdout
    assert u["status"]("R-1")["status"] == "uebernommen" and u["status"]("R-2")["status"] == "verworfen"
    assert laeufe(u)[0]["anzahl"] == 2


def test_eingabe_waehrend_des_laufs_kommt_in_den_naechsten_durchgang(u):
    u["lege_ein"]("R-1", erstellt=jetzt(-60))
    schreibe(u["tmp"] / "nachzuegler", u["eingabe"]("R-2", erstellt=jetzt(-60)))
    schreibe(u["tmp"] / "status.tsv", "beispiel\tR-1\tuebernommen\tok\nbeispiel\tR-2\tuebernommen\tauch ok\n")
    r = u["lauf"]()
    assert r.returncode == 0, r.stdout + r.stderr
    assert len(u["zeilen"]("claude-laeufe")) == 2   # zwei Durchgänge, nie gleichzeitig
    assert u["status"]("R-1")["status"] == "uebernommen" and u["status"]("R-2")["status"] == "uebernommen"
    assert [z["anzahl"] for z in laeufe(u)] == [1, 1]


def test_ein_lauf_zur_zeit(u):
    u["lege_ein"]("R-1", erstellt=jetzt(-60))
    with open(u["tmp"] / "probe-einarbeiten.lock", "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        r = u["lauf"]()
    assert r.returncode == 0 and "Läuft schon" in r.stdout
    assert u["zeilen"]("claude-laeufe") == [] and u["status"]("R-1") == {}


def test_ki_scheitert_wird_gemeldet_und_nach_drei_versuchen_aufgegeben(u):
    u["lege_ein"]("R-1", erstellt=jetzt(-60))
    schreibe(u["tmp"] / "claude-kaputt", "")
    for _ in range(2):
        r = u["lauf"]()
        assert r.returncode != 0 and "KI-Lauf abgebrochen" in r.stdout
    assert any(x.startswith("high|") and "fehlgeschlagen" in x for x in u["zeilen"]("mq.log"))
    assert [z["ergebnis"] for z in laeufe(u)] == ["fehler", "fehler"]
    r = u["lauf"]()                       # dritter Fehlversuch: aufgegeben
    assert r.returncode != 0 and any("aufgegeben" in x for x in u["zeilen"]("mq.log"))
    r = u["lauf"]()                       # blockiert spätere Läufe nicht
    assert r.returncode == 0 and "Nichts Neues" in r.stdout
    u["lege_ein"]("R-3")
    (u["tmp"] / "claude-kaputt").unlink()
    schreibe(u["tmp"] / "status.tsv", "beispiel\tR-3\tuebernommen\tok\n")
    assert u["lauf"]().returncode == 0 and u["status"]("R-3")["status"] == "uebernommen"
    # R-1 ist aufgegeben: Rückfrage mit Hinweis statt „neu“, und kein späterer KI-Lauf bekommt sie je zu sehen
    assert u["status"]("R-1")["status"] == "rueckfrage"
    assert "Ida schaut es sich in der nächsten Sitzung an" in u["status"]("R-1")["kommentar"]
    letzter = (u["tmp"] / f"prompt-{len(u['zeilen']('claude-laeufe'))}").read_text()
    assert "R-3" in letzter and "R-1" not in letzter


def test_scheitert_eine_reise_laufen_die_anderen_weiter(u):
    """Der Versuch zählt nur für die Einträge der gescheiterten Reise; die andere geht online, halbe Änderungen nicht."""
    u["lege_ein"]("R-1", erstellt=jetzt(-60))
    u["lege_ein"]("R-7", reise="zweite", erstellt=jetzt(-60))
    schreibe(u["tmp"] / "claude-kaputt-zweite", "")
    schreibe(u["tmp"] / "status.tsv", "beispiel\tR-1\tuebernommen\tok\n")
    r = u["lauf"]()
    assert r.returncode != 0 and "KI-Lauf abgebrochen (zweite); die übrigen Reisen sind eingearbeitet." in r.stdout
    assert u["status"]("R-1")["status"] == "uebernommen" and u["status"]("R-7", "zweite") == {}
    git(u["quelle"], "pull", "-q")
    assert (u["quelle"] / "reisen/zweite/notizen.md").read_text() == "start\n"
    assert git(u["origin"], "log", "-1", "--format=%s") == "Test eingearbeitet"
    assert (u["dienst"] / "einarbeiten-versuche").read_text() == "R-7 1\n"
    assert laeufe(u)[-1]["ergebnis"] == "teilweise"
    # nächster Lauf: nur noch R-7, sobald die KI wieder geht
    (u["tmp"] / "claude-kaputt-zweite").unlink()
    schreibe(u["tmp"] / "status.tsv", "zweite\tR-7\tuebernommen\tok\n")
    assert u["lauf"]().returncode == 0 and u["status"]("R-7", "zweite")["status"] == "uebernommen"


def test_ki_bekommt_nur_die_ids_des_eigenen_laufs(u):
    """Frühere, noch „neue“ Einträge (z. B. nach roten Tests) stehen weiter in der Liste, gehören aber nicht zum Lauf."""
    u["lege_ein"]("R-1", erstellt=jetzt(-60))
    schreibe(u["tmp"] / "rot", "")
    assert u["lauf"]().returncode != 0           # Tests rot: R-1 gesehen, aber noch „neu“
    (u["tmp"] / "rot").unlink()
    u["lege_ein"]("R-2", erstellt=jetzt(-60))
    schreibe(u["tmp"] / "status.tsv", "beispiel\tR-2\tuebernommen\tok\n")
    assert u["lauf"]().returncode == 0
    prompt = (u["tmp"] / "prompt-2").read_text()
    assert "NUR diese Einträge: R-2." in prompt and "R-1" not in prompt and "__IDS__" not in prompt


def test_rote_tests_nichts_online_status_bleibt_neu(u):
    u["lege_ein"]("R-1", erstellt=jetzt(-60))
    schreibe(u["tmp"] / "rot", "")
    r = u["lauf"]()
    assert r.returncode != 0 and "Tests rot" in r.stdout
    assert not (u["dienst"] / "veroeffentlicht").exists() and u["status"]("R-1") == {}
    assert laeufe(u)[-1]["ergebnis"] == "fehler"
    assert "Nichts Neues" in u["lauf"]().stdout   # nicht jedes Mal neu versuchen


def test_veroeffentlichen_belegt_wird_ehrlich_gemeldet(u):
    u["lege_ein"]("R-1", erstellt=jetzt(-60))
    schreibe(u["tmp"] / "belegt", "")
    r = u["lauf"]()
    assert r.returncode == 0, r.stdout + r.stderr
    assert laeufe(u)[0]["online"] == "nein"
    assert any("Online in wenigen Minuten" in x for x in u["zeilen"]("mq.log"))
    assert u["status"]("R-1")["status"] == "uebernommen"


def test_ergaenzung_der_instanz_kommt_in_den_auftrag(u):
    schreibe(u["quelle"] / "betrieb/einarbeiten-ergaenzung.md", "Herkunft immer mit Kürzel notieren.\n")
    u["lege_ein"]("R-1", erstellt=jetzt(-60))
    assert u["lauf"]().returncode == 0
    prompt = (u["tmp"] / "prompt-1").read_text()
    assert prompt.rstrip().endswith("Ergänzung dieser Instanz:\nHerkunft immer mit Kürzel notieren.")


def test_wartezeit_rechnet_ab_letzter_eingabe(u, monkeypatch):
    monkeypatch.setenv("RM_ABLAGE", str(u["ablage"]))
    monkeypatch.setenv("EA_SEKUNDEN_JE_MINUTE", "60")
    monkeypatch.setenv("FR_MAX_WARTEN_MIN", "20")
    gesehen = u["dienst"] / "gesehen"
    assert hilfe.wartezeit(u["quelle"], gesehen) == 0           # nichts da
    u["lege_ein"]("R-1", erstellt=jetzt(-300))
    assert hilfe.wartezeit(u["quelle"], gesehen) == 0           # 5 min her, Sammelzeit 4 min
    u["lege_ein"]("R-2", erstellt=jetzt(-20))
    assert 218 <= hilfe.wartezeit(u["quelle"], gesehen) <= 221   # 240 s nach der letzten
    gesehen.write_text("R-2\n")
    assert hilfe.wartezeit(u["quelle"], gesehen) == 0           # R-2 schon gesehen, R-1 ist alt genug
    u["lege_ein"]("R-3", erstellt=jetzt(-5))
    assert 233 <= hilfe.wartezeit(u["quelle"], gesehen) <= 236


def test_wartezeit_hat_eine_obergrenze(u, monkeypatch):
    monkeypatch.setenv("RM_ABLAGE", str(u["ablage"]))
    monkeypatch.setenv("EA_SEKUNDEN_JE_MINUTE", "60")
    monkeypatch.setenv("FR_MAX_WARTEN_MIN", "2")
    gesehen = u["dienst"] / "gesehen"
    u["lege_ein"]("R-1", erstellt=jetzt(-100))   # älteste: Obergrenze 2 min -> noch ~20 s
    u["lege_ein"]("R-2", erstellt=jetzt(-1))     # neueste: Sammelzeit würde 59 s verlangen
    assert 18 <= hilfe.wartezeit(u["quelle"], gesehen) <= 21


def test_versuche_zaehlen_und_kosten_lesen(tmp_path):
    d = tmp_path / "v"
    assert hilfe.versuch(d, 3, ["A", "B"]) == []
    assert hilfe.versuch(d, 3, ["A"]) == []
    assert hilfe.versuch(d, 3, ["A", "B"]) == ["A"]
    log = tmp_path / "c.json"
    log.write_text('{"total_cost_usd": 1.25, "is_error": false}')
    assert hilfe.kosten(log) == (1.25, False)
    log.write_text('{"is_error": true}')
    assert hilfe.kosten(log) == (None, True)
    log.write_text("kein json")
    assert hilfe.kosten(log) == (None, False)


# ---------- Regeln nach dem Lauf: Konflikt wird offene Frage, Prüfauftrag ändert keinen Wert ----------

def regel_ablage(tmp_path, monkeypatch, auftrag, status):
    ablage = tmp_path / "ablage"
    (ablage / "x").mkdir(parents=True)
    (ablage / "x/auftraege.jsonl").write_text(json.dumps(auftrag, ensure_ascii=False) + "\n")
    (ablage / "x/status.json").write_text(json.dumps({auftrag["id"]: {"status": status}}))
    monkeypatch.setenv("RM_ABLAGE", str(ablage))
    arbeit = tmp_path / "arbeit"
    (arbeit / "reisen/x/plan").mkdir(parents=True)
    return arbeit


def test_regel_konflikt_braucht_neue_offene_frage(tmp_path, monkeypatch):
    aid = "A-20261027-100000-abcd"
    arbeit = regel_ablage(tmp_path, monkeypatch, {"id": aid, "erstellt": jetzt(), "name": "Ida", "text": "KONFLIKT"}, "konflikt")
    alt = "| ID | Frage |\n|---|---|\n| F-01 | Alt |\n"
    vorher = {"reisen/x/offene-fragen.md": alt}.get
    datei = arbeit / "reisen/x/offene-fragen.md"
    datei.write_text(alt)
    assert hilfe.regeln(WURZEL, arbeit, [("x", aid)], alt=vorher) == [f"x {aid}: Konflikt ohne neue offene Frage, die {aid} nennt."]
    datei.write_text(alt + "| F-02 | Hotel: Ida wählt A, Karl wählt B |\n")   # neue Frage, aber ohne Auftrags-ID
    assert hilfe.regeln(WURZEL, arbeit, [("x", aid)], alt=vorher)
    datei.write_text(alt + f"| F-02 | Hotel: Ida wählt A ({aid}), Karl wählt B |\n")
    assert hilfe.regeln(WURZEL, arbeit, [("x", aid)], alt=vorher) == []
    # Ein Auftrag ohne Konflikt wird nicht geprüft
    arbeit2 = regel_ablage(tmp_path / "b", monkeypatch, {"id": aid, "erstellt": jetzt(), "name": "Ida", "text": "x"}, "neu")
    assert hilfe.regeln(WURZEL, arbeit2, [("x", aid)], alt=lambda p: "") == []


def test_regel_pruefauftrag_aendert_keinen_wert(tmp_path, monkeypatch):
    aid = "A-20261027-071300-beef"
    auftrag = {"id": aid, "erstellt": jetzt(), "name": "Wächter", "art": "Prüfung", "text": "Prüfauftrag",
               "daten": {"pruefung": [{"bezug": "U-01", "merkmal": "preis", "wert": "120 €"},
                                      {"bezug": "V-01.b", "merkmal": "dauer", "wert": "2 h"}]}}
    arbeit = regel_ablage(tmp_path, monkeypatch, auftrag, "neu")
    alt = ("unterkuenfte:\n  U-01:\n    name: Haus\n    merkmale:\n      preis: {wert: 120 €}\n"
           "wahlstellen:\n  - id: V-01\n    optionen:\n      - id: V-01.b\n        merkmale:\n"
           "          dauer: [{wert: 2 h}, {wert: 3 h, gilt: 2027-05-15}]\n")
    vorher = {"reisen/x/plan/routen.yaml": alt}.get
    datei = arbeit / "reisen/x/plan/routen.yaml"
    # Bestätigt: Prüfdatum und Quelle kommen dazu, Werte bleiben
    datei.write_text(alt.replace("{wert: 120 €}", "{wert: 120 €, geprueft: 2026-10-27, quelle: https://example.org}"))
    assert hilfe.regeln(WURZEL, arbeit, [("x", aid)], alt=vorher) == []
    # Still geändert: Verstoß, auch bei einem Wert je Datum
    datei.write_text(alt.replace("{wert: 120 €}", "{wert: 135 €}").replace("{wert: 3 h", "{wert: 4 h"))
    v = hilfe.regeln(WURZEL, arbeit, [("x", aid)], alt=vorher)
    assert len(v) == 2 and "U-01 preis wurde geändert (['120 €'] → ['135 €'])" in v[0] and "V-01.b dauer" in v[1]


def test_konflikt_ohne_offene_frage_geht_nicht_online(u):
    """Die Attrappe legt keine offene Frage an; der Lauf hält an wie bei roten Tests, nichts wird gesetzt."""
    aid = "A-20261027-100000-abcd"
    with (u["ablage"] / "beispiel/auftraege.jsonl").open("a") as f:
        f.write(json.dumps({"id": aid, "erstellt": jetzt(-600), "name": "Ida", "art": "Auftrag", "ziel": "V-01.a",
                            "text": "KONFLIKT", "quelle": ""}) + "\n")
    (u["ablage"] / "beispiel/status.json").write_text(json.dumps({aid: {"status": "konflikt"}}))
    r = u["lauf"]()
    assert r.returncode != 0 and "Regel verletzt" in r.stdout and f"Konflikt ohne neue offene Frage, die {aid} nennt" in r.stdout
    assert u["status"](aid)["status"] == "konflikt"          # bleibt, nichts eingearbeitet
    assert git(u["origin"], "rev-list", "--count", "main") == "1"   # nichts zusammengeführt


def test_regel_pruefauftrag_findet_alle_ziele_der_beispielreise(tmp_path, monkeypatch):
    """Die Prüfung greift bei jeder veränderlichen Angabe, auch an Optionen, deren Wert an der verknüpften Unterkunft
    oder Strecke steht. Sonst ergäbe sie vorher und nachher „nichts“ und wäre stumm."""
    import bauen
    import waechter
    d = bauen.Bauer(BEISPIEL, tmp_path / "dist").daten()
    ziele = waechter.zu_pruefen(d, datetime.date(2100, 1, 1), 0)
    text = (BEISPIEL / "plan/routen.yaml").read_text(encoding="utf-8")
    routen = yaml.safe_load(text)
    assert ziele and [(t["bezug"], t["merkmal"]) for t in ziele if hilfe._werte(routen, t["bezug"], t["merkmal"]) == [None]] == []
    # Eine Änderung am Wert wird gemeldet
    t = ziele[0]
    alt = hilfe._werte(routen, t["bezug"], t["merkmal"])[0]
    aid = "A-20261027-071300-beef"
    arbeit = regel_ablage(tmp_path / "r", monkeypatch, {"id": aid, "erstellt": jetzt(), "name": "Wächter", "text": "x",
                                                         "daten": {"pruefung": [t]}}, "neu")
    (arbeit / "reisen/x/plan/routen.yaml").write_text(text.replace(str(alt), str(alt) + " GEÄNDERT", 1), encoding="utf-8")
    assert hilfe.regeln(WURZEL, arbeit, [("x", aid)], alt=lambda p: text)


def test_neue_reise_aus_der_claude_app(u):
    """Anfragen aus dem Konto-Link (Ablage _neu) legt das Skript ohne KI an, baut, testet, führt zusammen und merkt die
    Links zum Zustellen vor; eine Anfrage, die nicht geht, wird eine Rückfrage."""
    from reise import neue_reise_pruefen
    o = u["ablage"] / "_neu"
    o.mkdir()
    zeilen = []
    for aid, titel, pfad in (("A-20261027-100000-0001", "Winterwoche im Tal", None),
                             ("A-20261027-100000-0002", "Doppelt", "beispiel")):
        daten, f = neue_reise_pruefen({"titel": titel, "von": "2027-02-06", "bis": "2027-02-13", "pfad": pfad,
                                       "personen": [{"vorname": "Karl"}], "notiz": "Hütte am Ort."}, "Ida")
        assert f is None
        zeilen.append(json.dumps({"id": aid, "erstellt": jetzt(-600), "name": "Ida", "konto": "ida", "art": "Auftrag",
                                  "ziel": "allgemein", "text": "Neue Reise", "quelle": "Claude-App",
                                  "daten": {"neue_reise": daten}}) + "\n")
    (o / "auftraege.jsonl").write_text("".join(zeilen))
    r = u["lauf"]()
    assert r.returncode == 0, r.stdout + r.stderr
    assert "Neue Reise angelegt: winterwoche-im-tal-2027" in r.stdout and "Neue Reise nicht angelegt: A-20261027-100000-0002" in r.stdout
    assert u["zeilen"]("claude-laeufe") == []                  # keine Rückmeldung in einer Reise: keine KI
    git(u["quelle"], "pull", "-q")
    neu = u["quelle"] / "reisen/winterwoche-im-tal-2027"
    assert (neu / "reise.yaml").exists() and "Notiz von Ida aus der Claude-App" in (neu / "inhalt/wissen.md").read_text()
    assert git(u["quelle"], "log", "-1", "--format=%s") == "Neue Reise angelegt: winterwoche-im-tal-2027"
    st = json.loads((o / "status.json").read_text())
    assert st["A-20261027-100000-0001"]["status"] == "uebernommen" and "meine_reisen" in st["A-20261027-100000-0001"]["kommentar"]
    assert st["A-20261027-100000-0002"]["status"] == "rueckfrage" and "gibt es schon" in st["A-20261027-100000-0002"]["kommentar"]
    aus = [json.loads(z) for z in (u["dienst"] / "ausstehend.jsonl").read_text().splitlines()]
    assert aus == [{"ordner": "winterwoche-im-tal-2027", "aid": "A-20261027-100000-0001", "name": "Ida", "person": "ida"}]
    assert {"A-20261027-100000-0001", "A-20261027-100000-0002"} <= set((u["dienst"] / "einarbeiten-gesehen").read_text().split())
    # nächster Lauf: nichts Neues
    assert "Nichts Neues" in u["lauf"]().stdout
