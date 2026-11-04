"""Protokolle, Nachweise und Specs in docs/artifacts/ und docs/specs/ sind öffentlich: Sie nennen keine absoluten Pfade
eines Rechners oder Servers (Heimatordner, /srv/…, /mnt/…), sondern Pfade relativ zum Repo oder zu ~. Anlass: frieda-reisen#245,
wo kopierte pytest-Ausgaben den Benutzer des Servers verrieten (CLAUDE.md, „Was nie hierher gehört“)."""
import re
import subprocess
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[2]
ABSOLUT = re.compile(r"(?<![\w.~-])/(?:home|Users|srv|mnt|root|var/www)/[\w.-]+")


def test_protokolle_ohne_absolute_pfade():
    dateien = subprocess.run(["git", "-C", str(WURZEL), "ls-files", "docs/artifacts", "docs/specs"], capture_output=True, text=True, check=True).stdout.split()
    funde = []
    for f in dateien:
        p = WURZEL / f
        if not p.is_file() or p.suffix in {".png", ".jpg", ".pdf"}:
            continue
        for n, zeile in enumerate(p.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
            m = ABSOLUT.search(zeile)
            if m:
                funde.append(f"{f}:{n}: {m.group(0)}")
    assert funde == [], "Absolute Pfade in öffentlichen Protokollen (relativ zum Repo oder zu ~ schreiben):\n" + "\n".join(funde)


def test_muster_erkennt_pfade():
    assert ABSOLUT.search("rootdir: /home/jemand/frieda-reist") and ABSOLUT.search("/srv/instanz/_bau")
    assert not ABSOLUT.search("rootdir: ~/frieda-reist") and not ABSOLUT.search("engine/tests/home/x")
