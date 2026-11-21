"""Protokolle, Nachweise, Specs und Kontext in docs/artifacts/, docs/specs/ und docs/context/ sind öffentlich: Sie nennen keine absoluten Pfade
eines Rechners oder Servers (Heimatordner, /srv/…, /mnt/…), sondern Pfade relativ zum Repo oder zu ~. Anlass: frieda-reisen#245,
wo kopierte pytest-Ausgaben den Benutzer des Servers verrieten (CLAUDE.md, „Was nie hierher gehört“)."""
import re
import subprocess
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[2]
ABSOLUT = re.compile(r"(?<![\w.~-])/(?:home|Users|srv|mnt|root|var/www)/[\w.-]+")


def test_protokolle_ohne_absolute_pfade():
    dateien = subprocess.run(["git", "-C", str(WURZEL), "ls-files", "docs/artifacts", "docs/specs", "docs/context"], capture_output=True, text=True, check=True).stdout.split()
    funde = []
    for f in dateien:
        p = WURZEL / f
        if not p.is_file() or p.suffix in {".png", ".jpg", ".pdf"}:
            continue
        for n, zeile in enumerate(p.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
            m = ABSOLUT.search(zeile) or PYTEST_TMP.search(zeile)
            if m:
                funde.append(f"{f}:{n}: {m.group(0)}")
    assert funde == [], "Absolute Pfade oder Benutzernamen im pytest-Temp-Ordner in öffentlichen Protokollen (relativ zum Repo oder zu ~ schreiben, Temp-Ordner als pytest-of-<benutzer>):\n" + "\n".join(funde)


def test_muster_erkennt_pfade():
    assert ABSOLUT.search("rootdir: /home/jemand/frieda-reist") and ABSOLUT.search("/srv/instanz/_bau")
    assert not ABSOLUT.search("rootdir: ~/frieda-reist") and not ABSOLUT.search("engine/tests/home/x")


def test_muster_erkennt_pytest_tmp():
    """#602: Der Temp-Ordner von pytest trägt den Benutzernamen, auch ohne Schrägstriche oder gekürzt."""
    for beispiel in ("rootdir: /tmp/pytest-of-jemand/pytest-3/test_bau0", "PosixPath('tmppytest-of-jemandpytest-3')", "/tmp/pytest-of-jem…/pytest-3"):
        assert PYTEST_TMP.search(beispiel), beispiel
    for platzhalter in ("/tmp/pytest-of-<benutzer>/pytest-3", "/tmp/pytest-of-<user>/x", "rm -rf /tmp/pytest-of-*", "/tmp/pytest-of-.../pytest-3"):
        assert not PYTEST_TMP.search(platzhalter), platzhalter
