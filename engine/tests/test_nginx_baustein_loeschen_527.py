"""#527: Verwaisten nginx-Baustein einer endgültig entfernten Reise automatisch löschen.

Der Wächter entfernt eine Reise nach der Schonfrist (#381), hat aber keine Root-Rechte (#552). Der nächste Lauf von
betrieb/veroeffentlichen.sh entfernt deshalb den Baustein <FR_NGINX_SNIPPETS>/<instanz>-<reise>.conf jeder Reise des
Löschprotokolls (engine/konten.py entfernt) über das Hilfsprogramm nginx-reise-installieren --entfernen. Reisen in der
Schonfrist behalten ihren Baustein. Spec: docs/specs/betrieb/nginx-baustein-loeschen-527.md.

Alle Reisenamen sind erfunden; das Hilfsprogramm ist eine Attrappe, die ihre Aufrufe protokolliert.
"""
import os
import re
import subprocess
import sys
from contextlib import closing
from pathlib import Path

import pytest

ENGINE = Path(__file__).resolve().parents[1]
WURZEL = ENGINE.parent
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import konten  # noqa: E402
from test_betrieb import ausfuehrbar, vf  # noqa: E402,F401  (vf: Fixture)

ENTFERNT = "stadtwochenende"     # erfunden: steht im Löschprotokoll
SCHONFRIST = "wanderwoche"       # erfunden: zur Löschung vorgemerkt, Frist läuft noch


# ---------- Aufbau ----------

@pytest.fixture
def kdb(tmp_path, monkeypatch):
    """Kontendatenbank mit einem erfundenen Konto."""
    monkeypatch.setenv("FR_KONTEN", str(tmp_path / "konten"))
    monkeypatch.setenv("FR_MAIL_DATEI", str(tmp_path / "mails.jsonl"))
    with closing(konten.db()) as v, v:
        v.execute("INSERT INTO konten (id, email, name, angelegt, sprache) VALUES (?,?,?,?,?)",
                  ("k-ida", "ida@example.invalid", "Ida", "2026-11-01T00:00:00+00:00", "de"))
    return konten


def _entfernt(*reisen):
    for r in reisen:
        konten.loeschung_vormerken(r, "k-ida")
        konten.loeschung_abschliessen(r)


@pytest.fixture
def nb(vf, kdb, tmp_path):
    """Veröffentlichen mit Kontendatenbank, Snippet-Ordner und einer Attrappe des Hilfsprogramms.

    Die Attrappe liest den Reisenamen von stdin und schreibt „<argumente> <reise>“ nach helfer.log. Liegt
    helfer-exit (Inhalt: Ausgang), endet sie damit und schreibt einen Grund nach stderr; sonst löscht sie den Baustein
    und endet mit 0."""
    snippets = tmp_path / "snippets"
    snippets.mkdir()
    seiten = tmp_path / "seiten"
    seiten.mkdir(exist_ok=True)
    log = tmp_path / "helfer.log"
    helfer = ausfuehrbar(tmp_path / "helfer", (
        "#!/bin/sh\n"
        "read -r reise\n"
        f'echo "$* $reise" >> {log}\n'
        f'if [ -e {tmp_path}/helfer-exit ]; then echo "nginx -t lehnt ab (erfunden)" >&2; exit "$(cat {tmp_path}/helfer-exit)"; fi\n'
        f'rm -f "{snippets}/probe-$reise.conf"\n'
        "exit 0\n"))
    extra = {"FR_KONTEN": str(tmp_path / "konten"), "FR_PYTHON": sys.executable, "FR_SEITEN": str(seiten),
             "FR_NGINX_SNIPPETS": str(snippets), "FR_NGINX_REISE_HELFER": str(helfer)}

    def lauf(*args, **mehr):
        return vf["lauf"](*args, **{**extra, **mehr})

    def aufrufe():
        return log.read_text().splitlines() if log.exists() else []

    def baustein(reise):
        p = snippets / f"probe-{reise}.conf"
        p.write_text(f"location /{reise}-geheim/ {{ }}\n")
        return p

    return {**vf, "lauf": lauf, "aufrufe": aufrufe, "baustein": baustein, "snippets": snippets, "helfer": helfer}


# ---------- AC-1: konten.py entfernt ----------

def test_befehl_entfernt_listet_nur_das_loeschprotokoll(kdb):
    _entfernt(ENTFERNT, "altreise")
    konten.loeschung_vormerken(SCHONFRIST, "k-ida")
    r = subprocess.run([sys.executable, str(ENGINE / "konten.py"), "entfernt"], capture_output=True, text=True,
                       env=os.environ)
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.splitlines() == ["altreise", ENTFERNT]


def test_befehl_entfernt_ohne_datenbank_still(tmp_path):
    konten_ordner = tmp_path / "konten"
    env = {**os.environ, "FR_KONTEN": str(konten_ordner)}
    r = subprocess.run([sys.executable, str(ENGINE / "konten.py"), "entfernt"], capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout == ""
    assert not (konten_ordner / "konten.db").exists()


# ---------- AC-2: Baustein der entfernten Reise weg, Schonfrist bleibt ----------

def test_baustein_der_entfernten_reise_wird_entfernt(nb):
    _entfernt(ENTFERNT)
    konten.loeschung_vormerken(SCHONFRIST, "k-ida")
    weg, bleibt = nb["baustein"](ENTFERNT), nb["baustein"](SCHONFRIST)
    r = nb["lauf"]()
    assert r.returncode == 0, r.stdout + r.stderr
    assert nb["aufrufe"]() == [f"--entfernen {ENTFERNT}"]
    assert not weg.exists() and bleibt.exists()
    assert f"Block removed: {ENTFERNT}" in r.stdout
    assert "geheim" not in r.stdout + r.stderr


# ---------- AC-3: ohne Baustein-Datei kein Aufruf ----------

def test_ohne_baustein_kein_aufruf_und_kein_sudo(nb):
    _entfernt(ENTFERNT)
    sudo_log = nb["tmp"] / "sudo.log"
    sudo = ausfuehrbar(nb["tmp"] / "sudo.sh", f'#!/bin/sh\necho "$*" >> {sudo_log}\n[ "$1" = -l ] && exit 0\nexec "$@"\n')
    r = nb["lauf"](FR_SUDO=str(sudo))
    assert r.returncode == 0, r.stdout + r.stderr
    assert nb["aufrufe"]() == []
    sudo_aufrufe = sudo_log.read_text() if sudo_log.exists() else ""
    assert str(nb["helfer"]) not in sudo_aufrufe and "--entfernen" not in sudo_aufrufe
    assert "Block removed" not in r.stdout


# ---------- AC-4: ohne Root-Rechte vormerken, mit Root nachholen ----------

def test_ohne_root_rechte_hinweis_und_der_naechste_lauf_holt_nach(nb):
    _entfernt(ENTFERNT)
    datei = nb["baustein"](ENTFERNT)
    r = nb["lauf"](FR_SUDO="false")
    assert r.returncode == 0, r.stdout + r.stderr
    assert nb["aufrufe"]() == [] and datei.exists()
    assert f"Note: nginx block of {ENTFERNT} not removed in this run (no root rights)" in r.stdout
    r = nb["lauf"]()
    assert r.returncode == 0, r.stdout + r.stderr
    assert nb["aufrufe"]() == [f"--entfernen {ENTFERNT}"] and not datei.exists()
    assert f"Block removed: {ENTFERNT}" in r.stdout


# ---------- AC-5: Fehler des Hilfsprogramms: Warnzeile, kein Alarm, nächster Lauf erneut ----------

@pytest.mark.parametrize("ausgang", [3, 4, 5, 6])
def test_fehler_des_helfers_warnt_ohne_alarm_und_wiederholt(nb, ausgang):
    _entfernt(ENTFERNT)
    datei = nb["baustein"](ENTFERNT)
    (nb["tmp"] / "helfer-exit").write_text(f"{ausgang}\n")
    r = nb["lauf"]()
    assert r.returncode == 0, r.stdout + r.stderr
    assert f"Warning: nginx block of {ENTFERNT} not removed (exit {ausgang}), the next run tries again" in r.stdout
    assert "nginx -t lehnt ab (erfunden)" in r.stdout
    assert datei.exists() and "Block removed" not in r.stdout
    assert not [z for z in nb["zeilen"]("melden.log") if z.startswith("high|")]
    # Der Bau läuft weiter
    assert sorted(nb["deploys"]()) == ["beispielreise", "zweitreise"]
    # Der nächste Lauf versucht es erneut
    r = nb["lauf"]("--immer")
    assert r.returncode == 0, r.stdout + r.stderr
    assert nb["aufrufe"]() == [f"--entfernen {ENTFERNT}"] * 2


def test_ausgang_2_bleibt_still(nb):
    _entfernt(ENTFERNT)
    nb["baustein"](ENTFERNT)
    (nb["tmp"] / "helfer-exit").write_text("2\n")
    r = nb["lauf"]()
    assert r.returncode == 0, r.stdout + r.stderr
    assert nb["aufrufe"]() == [f"--entfernen {ENTFERNT}"]
    assert "Warning: nginx block" not in r.stdout and "Block removed" not in r.stdout


# ---------- AC-6: ungültige Namen ----------

@pytest.mark.parametrize("name", ["Grossreise", "a/b", "..", "x", "a" * 41])
def test_ungueltiger_name_wird_uebersprungen(nb, name):
    with closing(konten.db()) as v, v:   # direkt ins Löschprotokoll: konten.py nimmt nur gültige Namen an
        v.execute("INSERT INTO loeschprotokoll (reise, datum) VALUES (?, ?)", (name, "2026-11-19"))
    if "/" not in name and name != "..":
        (nb["snippets"] / f"probe-{name}.conf").write_text("location /x/ { }\n")
    r = nb["lauf"]()
    assert r.returncode == 0, r.stdout + r.stderr
    assert nb["aufrufe"]() == []


def test_gueltige_grenzen_des_musters(nb):
    """Zwei und 40 Zeichen sind gültig (Muster des Hilfsprogramms)."""
    kurz, lang = "ab", "a" * 40
    _entfernt(kurz, lang)
    nb["baustein"](kurz), nb["baustein"](lang)
    r = nb["lauf"]()
    assert r.returncode == 0, r.stdout + r.stderr
    assert sorted(nb["aufrufe"]()) == sorted([f"--entfernen {kurz}", f"--entfernen {lang}"])


# ---------- AC-7: Liste nicht lesbar ----------

def test_liste_nicht_lesbar_warnt_ohne_abbruch(nb):
    _entfernt(ENTFERNT)
    nb["baustein"](ENTFERNT)
    py = ausfuehrbar(nb["tmp"] / "python.sh",
                     f'#!/bin/sh\ncase "$*" in *konten.py\\ entfernt*) echo kaputt >&2; exit 1;; esac\nexec {sys.executable} "$@"\n')
    r = nb["lauf"](FR_PYTHON=str(py))
    assert r.returncode == 0, r.stdout + r.stderr
    assert nb["aufrufe"]() == []
    assert re.search(r"Warning: .*removed trips.*cannot be read", r.stdout), r.stdout
    assert sorted(nb["deploys"]()) == ["beispielreise", "zweitreise"]


# ---------- AC-8: Aufrufstellen ----------

def test_schritt_steht_an_jeder_stelle_nach_vorgemerkte_entfernen():
    """Der Schritt folgt jedem Aufruf von vorgemerkte_entfernen; seit #557 (nur noch der Lauf aus dem Software-Klon) ist
    das genau eine Stelle."""
    text = (WURZEL / "betrieb" / "veroeffentlichen.sh").read_text(encoding="utf-8")
    assert re.search(r"^entfernte_bausteine\(\) \{", text, re.M)
    stellen = re.findall(r"vorgemerkte_entfernen \|\| return 1\n\s*entfernte_bausteine\b", text)
    assert len(stellen) == 1, stellen
    assert len(re.findall(r"vorgemerkte_entfernen \|\| return 1", text)) == 1


# ---------- AC-9: Doku und Docstring ----------

def test_doku_beschreibt_den_neuen_ablauf():
    waechter = (ENGINE / "waechter.py").read_text(encoding="utf-8")
    betrieb = (WURZEL / "docs" / "betrieb.md").read_text(encoding="utf-8")
    assert "bleibt (Root-Rechte)" not in waechter
    assert "entfernen kann ihn nur der Betreiber" not in betrieb
    assert "konten.py entfernt" in betrieb
    absatz = next(z for z in betrieb.splitlines() if z.startswith("**Löschen von Reisen (#381):**"))
    assert "nginx-Baustein" in absatz and "Veröffentlichen" in absatz and "--entfernen" in absatz
    assert re.search(r"nginx-Baustein[^\"]*Veröffentlichen", waechter)
