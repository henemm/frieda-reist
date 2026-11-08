"""Git-Weg des Schreibwegs (bis Stufe 5, #347, ADR-0009): jede Reise, die nicht in FR_SPEICHERREISEN steht, schreibt wie
vor Stufe 2 über eine Git-Arbeitskopie, einen Commit und einen Push nach main. Verschoben aus engine/schreiben.py ohne
Änderung des Verhaltens; schreiben.py lädt dieses Modul nur in den Funktionen des Git-Wegs.

Arbeitskopie: <Wurzel>-schreiben-<reise> (FR_SCHREIBKOPIE), ein Git-Worktree des Reisen-Repos ohne eigenen Branch (steht
auf origin/main). Je Anfrage bringt der Dienst sie auf origin/main und startet dort einen Unterprozess `anwenden` mit dem
Code dieser Arbeitskopie, damit Code und Daten denselben Stand haben. Eine Reise aus FR_SPEICHERREISEN lehnt der Git-Weg
ab (kein Doppelschreiben).

Die Zeitgrenzen (ZEIT_GESAMT, ZEIT_SPERRE, ZEIT_PRUEFUNG) gibt es nur in schreiben.py; sie werden zur Laufzeit von dort
gelesen, ebenso alles, was Tests dort ersetzen (Schreiber, vorgang_eingetragen, befehl_mit_frist, sperrdatei).
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import instanz
import schreiben as sb
import stand as reisestand


def git(ordner, *args, fehler=True, frist=None):
    """git-Aufruf -> stdout; mit `frist` (Sekunden) wird er danach samt Unterprozessen beendet (subprocess.TimeoutExpired)."""
    if frist is None:
        r = subprocess.run(["git", "-C", str(ordner), *args], capture_output=True, text=True)
    else:
        r = sb.befehl_mit_frist(["git", "-C", str(ordner), *args], "", frist)
    if fehler and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip() or r.stdout.strip()}")
    return r.stdout.strip()


def vorbereiten(s):
    """Arbeitskopie anlegen oder auf origin/main bringen; eigene Reste verwerfen. Jeder git-Aufruf bekommt den Rest der
    Frist (subprocess.TimeoutExpired, wenn sie abläuft)."""
    git(s.wurzel, "fetch", "-q", "origin", "main", frist=s.rest())
    if not (s.arbeit / ".git").exists():
        s.arbeit.parent.mkdir(parents=True, exist_ok=True)
        git(s.wurzel, "worktree", "prune", frist=s.rest())
        git(s.wurzel, "worktree", "add", "-q", "--detach", str(s.arbeit), "origin/main", frist=s.rest())
    else:
        git(s.arbeit, "reset", "-q", "--hard", frist=s.rest())
        git(s.arbeit, "clean", "-qfd", "--", "reisen", frist=s.rest())
        git(s.arbeit, "checkout", "-q", "--detach", "origin/main", frist=s.rest())
    if (s.arbeit / ".gitmodules").exists():
        git(s.arbeit, "submodule", "update", "--init", "--quiet", frist=s.rest())


def verwerfen(s, reise=None):
    """Nach einer Ablehnung die Arbeitskopie zurücksetzen: eine Reise (checkout, clean) oder alle Reisen (reise_anlegen)."""
    if reise is None:
        git(s.arbeit, "reset", "-q", "--hard")
        git(s.arbeit, "clean", "-qfd", "--", "reisen")
    else:
        git(s.arbeit, "checkout", "-q", "--", f"reisen/{reise}")
        git(s.arbeit, "clean", "-qfd", "--", f"reisen/{reise}")


def schreiben(s, reise, werkzeug, anfrage):
    """Ein Schreibvorgang in der vorbereiteten Arbeitskopie: Werkzeug und Probebau (schreiben.Schreiber), Commit mit Person
    und Werkzeug, nach main -> {"ok": True, "text", "commit", "stand"}; sonst Ablehnung."""
    reise, reise_dir, wer, titel, text, hinweise = s.anwenden_im_ordner(reise, werkzeug, anfrage)
    if not git(s.arbeit, "status", "--porcelain", "--", f"reisen/{reise}"):
        raise sb.Ablehnung("schreiben.schreiben.4")
    kopf, titel_, text_, fuss = s.nachricht(reise_dir, werkzeug, wer, titel, text)
    nachricht = f"{kopf}: {titel_}\n\n{text_}\n\n{fuss}\n"
    # Wer den Eintrag gemacht hat, für die Änderungsliste der Seite (engine/stand.py, #229)
    nachricht += f"\n{reisestand.PERSON_TRAILER}: {' '.join(wer['name'].split())}\n"
    if os.environ.get("FR_VORGANG"):     # Kennung des Vorgangs: nach einem Abbruch findet vorgang_eingetragen den Eintrag
        nachricht += f"Frieda-Vorgang: {os.environ['FR_VORGANG']}\n"
    git(s.arbeit, "add", "-A", "--", f"reisen/{reise}")
    git(s.arbeit, "commit", "-q", "-m", nachricht)
    commit = hochladen(s, reise)
    # Reise-Stand (#226): jeder gesicherte Schreibvorgang ist ein Commit in reisen/<reise>/ und erhöht die Nummer um 1
    nummer = reisestand.nummer(reise_dir)
    reisestand.gesichert_schreiben(reise, nummer, commit)
    s.veroeffentlichen_anstossen()
    return s.antwort(reise, titel, text, hinweise, commit, nummer)


def buchung_im_repo(s, reise, bid):
    """Gibt es die Buchung B-… auf origin/main (auch wenn die Seite noch nicht neu gebaut ist)? -> {"gibt_es", "fuer", "wer"}.
    Liest nur (git show), ohne Sperre und ohne Arbeitskopie; der Konnektor fragt so, bevor er einen Beleg ablegt (Issue #135)."""
    if not sb.buchung_anfrage_gueltig(reise, bid):
        return {"gibt_es": False}
    git(s.wurzel, "fetch", "-q", "origin", "main", frist=sb.ZEIT_PRUEFUNG)
    text = git(s.wurzel, "show", f"origin/main:reisen/{reise}/plan/routen.yaml", fehler=False, frist=sb.ZEIT_PRUEFUNG)
    return sb.buchung_aus_routen(text, bid)


def hochladen(s, reise):
    """Nach main pushen; kam inzwischen etwas anderes an, darauf aufsetzen (höchstens dreimal)."""
    for versuch in range(3):
        r = subprocess.run(["git", "-C", str(s.arbeit), "push", "-q", "origin", "HEAD:main"], capture_output=True, text=True)
        if r.returncode == 0:
            return git(s.arbeit, "rev-parse", "HEAD")
        sys.stderr.write(f"Upload attempt {versuch + 1}: git push failed: {r.stderr.strip()}\n")
        git(s.arbeit, "fetch", "-q", "origin", "main")
        rb = subprocess.run(["git", "-C", str(s.arbeit), "rebase", "-q", "origin/main"], capture_output=True, text=True)
        if rb.returncode != 0:
            sys.stderr.write(f"Upload attempt {versuch + 1}: git rebase failed: {rb.stderr.strip() or rb.stdout.strip()}\n")
            git(s.arbeit, "rebase", "--abort", fehler=False)
            git(s.arbeit, "reset", "-q", "--hard", "origin/main")
            raise sb.Ablehnung("schreiben.hochladen.1", reise=reise)
    git(s.arbeit, "reset", "-q", "--hard", "origin/main")
    raise sb.Ablehnung("schreiben.hochladen.2")


def gesund(s):
    """Git-Teil von /gesund: das Reisen-Repo ist da und lesbar."""
    return (s.wurzel / ".git").exists() and subprocess.run(["git", "-C", str(s.wurzel), "rev-parse", "--git-dir"],
                                                           capture_output=True).returncode == 0


def vorbereiten_aufruf():
    """`schreiben.py vorbereiten`: Arbeitskopie anlegen und ihren Stand nennen."""
    s = sb.Schreiber(sb.wurzel())
    s.vorbereiten()
    print(f"Arbeitskopie {s.arbeit} steht auf {git(s.arbeit, 'rev-parse', '--short', 'HEAD')}.")


def vorgang_eingetragen(s, kennung):
    """Ist der Vorgang mit dieser Kennung auf origin/main angekommen? -> True, False oder None (Prüfung nicht möglich).
    Holen und Suchen zusammen höchstens ZEIT_PRUEFUNG Sekunden; der alte Stand von origin/main gilt nicht als Antwort."""
    import time
    ende = time.monotonic() + sb.ZEIT_PRUEFUNG
    try:
        git(s.wurzel, "fetch", "-q", "origin", "main", frist=ende - time.monotonic())
        return bool(git(s.wurzel, "log", "--format=%H", "--fixed-strings", f"--grep=Frieda-Vorgang: {kennung}", "origin/main",
                        frist=ende - time.monotonic()))
    except (RuntimeError, subprocess.TimeoutExpired):
        return None


def nach_abbruch(s, werkzeug, kennung, reise=None):
    """Antwort, nachdem das Anwenden von der Frist abgebrochen wurde: Ergebnis auf origin/main nachsehen."""
    ergebnis = sb.vorgang_eingetragen(s, kennung)
    if ergebnis:
        # vorgang_eingetragen hat origin/main eben geholt
        nummer = reisestand.nummer(s.wurzel / "reisen" / reise, "origin/main") if reise else None
        return sb.eingetragen_trotz_abbruch(werkzeug, reise, nummer)
    if ergebnis is False:
        return sb.nicht_eingetragen(werkzeug)
    return sb.ungeprueft(werkzeug)


def git_sperren_raeumen(arbeit):
    """Veraltete Sperren von git (index.lock, HEAD.lock …) im eigenen git-Ordner der Arbeitskopie entfernen: Ein nach Fristablauf
    beendetes git kann sie hinterlassen. Nur unter der Sperre der Reise aufrufen; der gemeinsame git-Ordner des Repos bleibt
    unberührt (dort arbeiten andere Reisen und das Veröffentlichen). Die Arbeitskopie ist ein Worktree: .git ist eine Datei
    „gitdir: <Repo>/.git/worktrees/<Name>“."""
    punkt_git = Path(arbeit) / ".git"
    if punkt_git.is_file():
        zeile = punkt_git.read_text(encoding="utf-8").strip()
        if not zeile.startswith("gitdir:"):
            return
        gitdir = Path(arbeit) / zeile[len("gitdir:"):].strip()     # absolut bleibt absolut
    elif punkt_git.is_dir():
        gitdir = punkt_git
    else:
        return
    for f in gitdir.glob("*.lock"):
        f.unlink(missing_ok=True)
        sys.stderr.write(f"Working copy: stale lock {f.name} removed\n")


def vorgang(s, reise, werkzeug, anfrage, start):
    """Ein Schreibvorgang über Git -> (Code, Antwort): Sperre der Reise, Arbeitskopie auf origin/main, `anwenden` mit dem Code
    der Arbeitskopie in der Frist. Eine Reise aus FR_SPEICHERREISEN wird abgelehnt, bevor etwas geholt wird."""
    try:
        im_speicher = reise in instanz.speicherreisen()
    except instanz.EinstellungenNichtLesbar as e:     # #361: Liste unbekannt -> nichts holen, nichts schreiben
        sys.stderr.write(f"Refused {werkzeug} 503: settings not readable: {' '.join(str(e).split())[:sb.LOG_LAENGE]}\n")
        return 503, sb.fehler_antwort("schreiben.dienst.einstellungen_nicht_lesbar")
    if im_speicher:
        sys.stderr.write(f"Refused {werkzeug} 503: trip {reise} is written through the store, not through git\n")
        return 503, sb.fehler_antwort("schreiben.dienst.reise_im_speicher")
    s = sb.Schreiber(s.wurzel, Path(f"{s.arbeit}-{reise}"), s.veroeffentlichen)
    s.ende = start + sb.ZEIT_GESAMT
    with open(sb.sperrdatei(reise), "w") as f:
        if not sb.sperre_nehmen(f):
            sys.stderr.write(f"Locked {werkzeug} 429: lock of the trip still held after {sb.ZEIT_SPERRE} s\n")
            return 429, sb.fehler_antwort("schreiben.dienst.besetzt")
        try:
            git_sperren_raeumen(s.arbeit)     # unter der Sperre der Reise: kein anderes git arbeitet in dieser Kopie
            s.vorbereiten()
        except subprocess.TimeoutExpired:
            return sb.nicht_eingetragen(werkzeug)     # noch nichts angewendet, keine Prüfung nötig
        except RuntimeError as e:
            sys.stderr.write(f"Arbeitskopie: {e}\n")
            return 503, sb.fehler_antwort("schreiben.dienst.repo_nicht_erreichbar_spaeter")
        skript = s.arbeit / "engine" / "schreiben.py"
        if not skript.exists():
            sys.stderr.write(f"Working copy: {skript} missing\n")
            return 503, sb.fehler_antwort("schreiben.dienst.software_alt")
        if s.rest() <= 0:
            return sb.nicht_eingetragen(werkzeug)
        kennung = sb.secrets.token_hex(6)
        try:
            r = sb.befehl_mit_frist([sys.executable, str(skript), "anwenden", reise, werkzeug], json.dumps(anfrage), s.rest(),
                                    env={**os.environ, "FR_WURZEL": str(s.wurzel), "FR_SCHREIBKOPIE": str(s.arbeit),
                                         "FR_VORGANG": kennung})
        except subprocess.TimeoutExpired:
            return nach_abbruch(s, werkzeug, kennung, reise)
        return sb.ausgabe_lesen(r)
