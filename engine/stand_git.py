"""Reise-Stand aus Git (bis Stufe 5, #347, ADR-0009): Nummer und Änderungsliste einer Reise, die noch nicht über den
Reisespeicher geschrieben wird. Verschoben aus engine/stand.py ohne Änderung des Verhaltens; stand.py lädt dieses Modul
nur in seinen Funktionen.

Nummer: die Zahl der Commits, die den Ordner der Reise ändern (git rev-list --count HEAD -- <ordner>). Jeder gesicherte
Schreibvorgang ist ein Commit in reisen/<reise>/ und erhöht sie um 1; ein Software-Update (Submodul frieda/) ändert den
Ordner nicht und lässt sie stehen. main wächst nur (vorspulen, docs/betrieb.md), deshalb steigt die Nummer und Stand 43
enthält alles aus Stand 42. In einem flachen Klon wäre die Zahl falsch und fehlt deshalb; ohne Git fehlt sie auch.
"""
import subprocess
from pathlib import Path

from stand import AENDERUNGEN, PERSON_TRAILER, ohne_kennungen, zeit_iso


def git(ordner, *args):
    """git im Ordner -> Ausgabe ohne Rand oder None (kein Git, Fehler)."""
    try:
        r = subprocess.run(["git", "-C", str(ordner), *args], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def nummer(ordner, rev="HEAD"):
    """Reise-Stand des Ordners auf rev -> int oder None (ohne Git, flacher Klon, nichts eingecheckt)."""
    if not Path(ordner).is_dir() or git(ordner, "rev-parse", "--is-shallow-repository") != "false":
        return None
    n = git(ordner, "rev-list", "--count", rev, "--", ".")
    return int(n) if n and n.isdigit() and int(n) > 0 else None


def _person(nachricht, autor):
    """Wer eine Änderung gemacht hat: die Zeile Frieda-Person des Schreibwegs, sonst der Autor des Commits."""
    for z in reversed(nachricht.splitlines()):
        if z.startswith(PERSON_TRAILER + ":"):
            return z.split(":", 1)[1].strip() or None
    return autor or None


def aenderungen(ordner, namen=None, n=AENDERUNGEN):
    """Die letzten n Änderungen der Reise -> [{nummer, zeit, was, wer}], neueste zuerst. was ist die erste Zeile des Commits
    ohne den Titel der Reise davor, mit Namen statt Kennungen."""
    gesamt = nummer(ordner)
    if not gesamt:
        return []
    roh = git(ordner, "log", f"-{n}", "--format=%ct%x1f%an%x1f%B%x1e", "--", ".")
    if not roh:
        return []
    liste = []
    for i, eintrag in enumerate(x for x in roh.split("\x1e") if x.strip()):
        teile = eintrag.strip("\n").split("\x1f", 2)
        if len(teile) != 3 or not teile[0].strip().isdigit():
            continue
        zeit, autor, nachricht = int(teile[0].strip()), teile[1].strip(), teile[2].strip()
        was = (nachricht.splitlines() or [""])[0]
        if ": " in was:   # „<Titel der Reise>: <was>“ (Schreibweg)
            was = was.split(": ", 1)[1]
        liste.append({"nummer": gesamt - i, "zeit": zeit_iso(zeit), "was": ohne_kennungen(was, namen or {}),
                      "wer": _person(nachricht, autor)})
    return liste


def reise_aus_head(wurzel, reise, ziel):
    """Dateistand von reisen/<reise> im Commit HEAD des Bauordners nach ziel (neuer Ordner), wie betrieb/vergleichslauf.sh:
    git archive, dazu die von Git ignorierten Dateien der Reise aus dem Bauordner (Offline-Grundkarten, #479). Der Bauordner
    bleibt unberührt, ungesicherte, nicht ignorierte Dateien zählen nicht. Symlinks bleiben Symlinks (der Vergleich lehnt sie
    ab). -> Zahl der ignorierten Dateien. Fehler von git: RuntimeError (#454, automatische Umschaltung)."""
    import io
    import shutil
    import tarfile
    ziel = Path(ziel)
    ziel.mkdir(parents=True)
    try:
        r = subprocess.run(["git", "-C", str(wurzel), "archive", "--format=tar", "HEAD", f"reisen/{reise}"],
                           capture_output=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as e:
        raise RuntimeError(f"git archive: {e}") from e
    if r.returncode != 0:
        raise RuntimeError(f"git archive: {r.stderr.decode(errors='replace').strip()[:200]}")
    vorne = f"reisen/{reise}/"
    with tarfile.open(fileobj=io.BytesIO(r.stdout)) as tar:
        for m in tar.getmembers():
            if not m.name.startswith(vorne):
                continue
            m.name = m.name[len(vorne):]
            if m.name:
                tar.extract(m, ziel, filter="tar")
    roh = git(wurzel, "ls-files", "-z", "--others", "--ignored", "--exclude-standard", "--", f"reisen/{reise}")
    if roh is None:
        raise RuntimeError("git ls-files failed")
    ignoriert = [x for x in roh.split("\0") if x]
    for rel in ignoriert:
        quelle = Path(wurzel) / rel
        aus = ziel / rel[len(vorne):]
        aus.parent.mkdir(parents=True, exist_ok=True)
        if quelle.is_symlink():
            aus.symlink_to(Path(quelle).readlink())
        else:
            shutil.copyfile(quelle, aus)
    return len(ignoriert)
