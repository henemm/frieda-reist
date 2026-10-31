"""Vorlage des Workflows „Software nachziehen“ (#161): Ein Reisen-Repo zieht das Submodul frieda/ selbst nach,
nur bei grünen Tests; bei Rot entsteht ein Issue. Die Vorlage ist allgemein (nichts einer Instanz)."""
import re
from pathlib import Path

import yaml

WURZEL = Path(__file__).resolve().parents[2]
VORLAGE = WURZEL / "betrieb" / "software-nachziehen.yml"
BETRIEB_MD = WURZEL / "docs" / "betrieb.md"


def lade():
    return yaml.safe_load(VORLAGE.read_text(encoding="utf-8"))


def schritte():
    return lade()["jobs"]["nachziehen"]["steps"]


def schritt(name):
    return next(s for s in schritte() if s.get("name") == name)


def test_ausloeser_rechte_und_ein_lauf_gleichzeitig():  # AC-1
    w = lade()
    ausloeser = w.get("on", w.get(True))  # PyYAML liest den Schlüssel `on` als True
    assert "schedule" in ausloeser and "workflow_dispatch" in ausloeser
    assert w["permissions"] == {"contents": "write", "issues": "write"}
    assert w["concurrency"]["cancel-in-progress"] is False


def test_rote_tests_fuehren_zum_issue():  # AC-2, #224
    tests = next(s for s in schritte() if s.get("id") == "tests")
    assert tests.get("continue-on-error") is True
    assert "steps.tests.outcome == 'success'" in schritt("Nach main übernehmen")["if"]
    issue = schritt("Issue bei Testfehler")
    assert "steps.tests.outcome == 'failure'" in issue["if"]
    assert issue["run"].rstrip().endswith("exit 1")


def test_volle_historie_fuer_vorwaerts_pruefung():
    """actions/checkout holt Submodule flach; ohne volle Historie scheitert merge-base --is-ancestor immer."""
    run = schritt("Neuer Stand?")["run"]
    assert "fetch -q --unshallow origin main" in run
    assert run.index("--unshallow") < run.index("merge-base --is-ancestor")


def test_commit_als_bot_mit_liste_und_ohne_erzwingen():  # AC-3
    run = schritt("Nach main übernehmen")["run"]
    assert 'user.name "github-actions[bot]"' in run
    assert re.search(r'user\.email "[^"]+@users\.noreply\.github\.com"', run)
    assert re.search(r"git -C frieda log [^\n]*\$alt\.\.\$neu", run)
    assert "git rebase --abort" in run and "for versuch in 1 2 3" in run
    assert "--force" not in VORLAGE.read_text(encoding="utf-8")


def test_nichts_einer_instanz():  # AC-4
    text = VORLAGE.read_text(encoding="utf-8")
    assert "/srv/" not in text and "/home/" not in text
    assert "henemm" not in text and "frieda-reisen" not in text
    domains = set(re.findall(r"[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:com|de|org|net|io)\b", text))
    assert domains <= {"users.noreply.github.com", "github.com"}, domains


def test_doku_einrichten_und_ueberwachung():  # AC-5
    doku = BETRIEB_MD.read_text(encoding="utf-8")
    einrichten = doku.split("## Neue Instanz einrichten", 1)[1].split("\n## ", 1)[0]
    assert "betrieb/software-nachziehen.yml" in einrichten and ".github/workflows/" in einrichten
    assert "contents: write" in einrichten and "issues: write" in einrichten
    ueberwachung = doku.split("## Überwachung", 1)[1].split("\n## ", 1)[0]
    assert "Rückstand" in ueberwachung and "main" in ueberwachung
