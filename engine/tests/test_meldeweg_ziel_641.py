"""#641: Meldeweg ohne Reisen-Repo (Rest von #557 AC-36).

Seit #454 und #557 läuft jede Instanz ohne ihr früheres privates Reisen-Repo; es wird archiviert. Ist-Doku, Usage der
Betriebsskripte und sichtbare Texte dürfen es darum nicht mehr als aktuellen Ort nennen (Einstellungen liegen unter
<FR_DIENST>/instanz/, Anleitung und Meldungen der Stufe normal im privaten Repo der Instanz, FR_MELDEN_REPO). Specs,
docs/artifacts/, docs/adr/, docs/context/, docs/briefings/ und docs/abgleich-* sind Historie und bleiben unberührt.
"""
import importlib
import re
import subprocess
import sys
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parents[2]
ENGINE = WURZEL / "engine"
BETRIEB = WURZEL / "betrieb"
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(Path(__file__).resolve().parent))

WORT = "Reisen-Repo"   # deckt auch „Reisen-Repos“ ab

# Fundstellen, die das Reisen-Repo ausdrücklich als früheren oder abwesenden Zustand beschreiben. Die Liste darf nur
# kürzer werden (wie die Ausnahmelisten in test_texte.py); jeder Eintrag muss in seiner Datei noch vorkommen (Test 4).
AUSNAHMEN = {
    ("betrieb/einrichten.sh", "ohne Reisen-Repo, ohne gh"): "neue Instanz kommt ohne das Reisen-Repo aus (Abwesenheit)",
    ("betrieb/veroeffentlichen.sh", "kein Reisen-Repo, keine eingebundene Software"): "seit #557 gibt es es nicht mehr",
    ("betrieb/veroeffentlichen.sh", "(das frühere Reisen-Repo)"): "Aufräumen der alten Arbeitskopie, ausdrücklich früher",
    ("docs/betrieb.md", "| Reisen-Repo (alt) |"): "Tabellenzeile des archivierten Repos, ausdrücklich alt",
    ("docs/betrieb.md", "ohne Anmeldung, ohne Reisen-Repo, ohne `gh`"): "Software direkt (#454), Abwesenheit",
    ("docs/betrieb.md", "ohne Reisen-Repo, ohne `gh` und ohne Anmeldung"): "neue Instanz (#454), Abwesenheit",
    ("docs/betrieb.md", "der alten Anordnung (Reisen-Repo mit eingebundener Software"): "abgeschlossener Umzug #454",
    ("docs/betrieb.md", "das archivierte Reisen-Repo auf GitHub"): "Archiv, nur lesen (AC-36 aus #557)",
}

HISTORIE = re.compile(r"^docs/(specs|artifacts|adr|context|briefings)/|^docs/abgleich-")


def _ist_dateien():
    """Ist-Doku, Usage der Betriebsskripte und sichtbare Texte (Spec #641, Rückfall-Test)."""
    dateien = [WURZEL / "CLAUDE.md", WURZEL / "README.md"]
    dateien += sorted(p for p in (WURZEL / "docs").glob("*.md"))
    dateien += sorted(p for p in BETRIEB.rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    dateien += sorted(ENGINE.glob("texte_*.py")) + [ENGINE / "konten.py"]
    return [p for p in dateien if not HISTORIE.match(str(p.relative_to(WURZEL)))]


def _fundstellen():
    funde = []
    for pfad in _ist_dateien():
        rel = str(pfad.relative_to(WURZEL))
        try:
            text = pfad.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        ausnahmen = [s for (d, s) in AUSNAHMEN if d == rel]
        for nr, zeile in enumerate(text.splitlines(), 1):
            rest = zeile
            for s in ausnahmen:
                rest = rest.replace(s, "")
            if WORT in rest:
                funde.append(f"{rel}:{nr}: {zeile.strip()[:160]}")
    return funde


def test_ist_doku_nennt_reisen_repo_nicht_als_aktuellen_ort():
    """Test 1, AC-10, AC-13: kein Reisen-Repo als aktueller Ort in Ist-Doku, Usage und sichtbaren Texten."""
    funde = _fundstellen()
    assert not funde, "Reisen-Repo als aktueller Ort (privates Repo der Instanz bzw. <FR_DIENST>/instanz/ nennen):\n" + \
        "\n".join(funde)


def test_claude_md_und_readme_nennen_instanz_orte():
    """AC-10: Einstellungen unter <FR_DIENST>/instanz/, Anleitung der Instanz-Tests im privaten Repo der Instanz."""
    claude = (WURZEL / "CLAUDE.md").read_text(encoding="utf-8")
    readme = (WURZEL / "README.md").read_text(encoding="utf-8")
    assert "<FR_DIENST>/instanz/einstellungen.env" in claude
    assert "privaten Repo der Instanz" in claude
    assert "<FR_DIENST>/instanz/" in readme


def test_betrieb_md_meldeweg_nennt_instanz_repo_und_variable():
    """AC-10: Abschnitt Meldeweg nennt FR_MELDEN_REPO und das private Repo der Instanz als Ziel der Stufe normal."""
    betrieb = (WURZEL / "docs/betrieb.md").read_text(encoding="utf-8")
    assert "FR_MELDEN_REPO" in betrieb
    assert "privaten Repo der Instanz" in betrieb


def test_meldung_erledigt_verweist_auf_instanz_repo():
    """Test 2, AC-11: konten.py (Usage, Kommentar) und docs/konten.md nennen das private Repo der Instanz."""
    for datei in ("engine/konten.py", "docs/konten.md"):
        text = (WURZEL / datei).read_text(encoding="utf-8")
        assert WORT not in text, datei
        assert "privaten Repo der Instanz" in text, datei


@pytest.mark.parametrize("katalog", sorted(p.stem for p in ENGINE.glob("texte_*.py")))
def test_ontologie_text_ohne_reisen_repo_in_allen_sprachen(katalog):
    """Test 2, AC-11: konnektor.ontologie_werkzeug.4 nennt in keiner Sprache das Reisen-Repo als Ort einer Sitzung."""
    texte = importlib.import_module(katalog).TEXTE
    wert = texte["konnektor.ontologie_werkzeug.4"]
    assert not re.search(r"reisen-repo|trips? repo", wert, re.IGNORECASE), (katalog, wert)


def test_einstellungen_beispiel_dokumentiert_meldeziel():
    """Test 3, AC-12: FR_MELDEN_REPO steht mit Platzhalter in der Vorlage, das Reisen-Repo nicht als Ort."""
    beispiel = (BETRIEB / "einstellungen.beispiel").read_text(encoding="utf-8")
    assert re.search(r"^#FR_MELDEN_REPO=", beispiel, re.MULTILINE)
    assert "<Instanz-Repo>" in beispiel
    assert WORT not in beispiel


def test_zustellen_usage_ohne_reisen_repo():
    """Test 3, AC-12: Usage von zustellen.py nennt den Software-Klon als Wurzel, nicht das Reisen-Repo."""
    assert WORT not in (BETRIEB / "zustellen.py").read_text(encoding="utf-8")


def test_ausnahmen_gibt_es_noch():
    """Test 4, AC-13: Jede Ausnahme steht noch in ihrer Datei; die Liste wird nur kürzer."""
    fehlend = [(d, s) for (d, s) in AUSNAHMEN if s not in (WURZEL / d).read_text(encoding="utf-8")]
    assert not fehlend, f"Ausnahmen ohne Fundstelle, bitte streichen: {fehlend}"
    assert len(AUSNAHMEN) <= 8


def test_fr_melden_repo_erreicht_das_meldeskript(tmp_path):
    """Test 5, AC-3: FR_MELDEN_REPO aus einstellungen.env der Instanz erreicht melden.sh ohne Änderung der Software."""
    dienst = tmp_path / "dienst"
    (dienst / "instanz").mkdir(parents=True)
    protokoll = tmp_path / "gemeldet"
    stub = dienst / "instanz/melden.sh"
    stub.write_text(f'#!/bin/bash\necho "$1|${{FR_MELDEN_REPO:-}}" > "{protokoll}"\n')
    stub.chmod(0o755)
    (dienst / "instanz/einstellungen.env").write_text("FR_INSTANZ=probe\nFR_MELDEN_REPO=<Instanz-Repo>\n")
    r = subprocess.run(["bash", "-c", f'. "{BETRIEB}/gemeinsam.sh"; fr_melden normal Probe Text'],
                       capture_output=True, text=True,
                       env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path), "FR_WURZEL": str(tmp_path),
                            "FR_DIENST": str(dienst)})
    assert r.returncode == 0, r.stderr
    assert protokoll.read_text().strip() == "normal|<Instanz-Repo>"


def test_alarmstellen_unveraendert():
    """Test 6, AC-17: #641 bringt keine neue high-Stelle; ALARMSTELLEN bleibt, wie sie ist."""
    from test_betrieb import ALARMSTELLEN
    assert set(ALARMSTELLEN) == {
        ("waechter.sh", "Watchdog failed"),
        ("waechter.sh", "Account backup failed"),
        ("waechter.sh", "Trip store backup failed"),
        ("veroeffentlichen.sh", "Publishing red for $minuten minutes"),
    }
