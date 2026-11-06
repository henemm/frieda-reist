#!/usr/bin/env python3
"""Messlauf des Schreibwegs (Stufe 2, #347, docs/specs/betrieb/schreibweg-speicher-347.md): wie lange dauert ein
Schreibvorgang über den Reisespeicher bzw. über Git? Kein Teil der Testläufe; die Werte kommen als Kommentar ins Issue.

    messlauf-schreibweg.py [--weg speicher|git] [--anzahl N] [--parallel P] [--auffuellen MB]

--auffuellen MB legt zusätzlich die erfundene Reise `gross-erfunden` an: eine Kopie der Beispielreise, deren Ordner `medien/`
mit Zufallsdateien (je 1 MB, als `foto-NNN.jpg`) auf MB Megabyte aufgefüllt ist. Ihre Zeiten stehen einzeln in der Ausgabe.

Baut eine temporäre Instanz (alles unter TMPDIR, wird danach gelöscht) mit beiden Beispielreisen und je einer Kopie unter
anderem Namen, und schickt einen Werkzeugmix (Frage anlegen, Art anlegen, Wissen schreiben) über den Eingang des Dienstes
(schreiben.anwenden_extern):
  nacheinander  N Vorgänge, einer nach dem anderen, reihum über die Reisen
  parallel      N Vorgänge mit P Fäden zugleich: mehrere Reisen gleichzeitig und mehrere Vorgänge auf derselben Reise
                (429 = Sperre der Reise belegt, getrennt gezählt)
Ausgabe je Lauf: Anzahl, Mittel, p50, p90, p99, Maximum (Sekunden) und die Zahl der 504, 429 und 5xx; dazu Export- und
Probebauzeit einzeln. Der Git-Weg läuft gegen einen lokalen Origin und ist nur ein Richtwert.

Belastbar ist erst ein Lauf auf dem Server der Instanz mit einer erfundenen Testreise, die mit Fotos auf die Größe der
größten echten Reise aufgefüllt ist (Fotos liegen bis Stufe 4 in der Datenbank und treiben den Export).
"""
import argparse
import concurrent.futures
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
ENGINE = WURZEL / "engine"
BEISPIEL = WURZEL / "beispiel" / "reisen"
REISEN = {"beispielreise": {"person": "ida", "name": "Ida", "rolle": "organisator"},          # Beispielwerte
          "stadtwochenende": {"person": "tom", "name": "Tom", "rolle": "organisator"}}


def befehl(*argv):
    subprocess.run(list(argv), check=True, capture_output=True, text=True)


def umgebung(tmp, wurzel):
    """Die Umgebung einer Instanz unter tmp; Werte der aufrufenden Instanz gelten nicht."""
    for k in list(os.environ):
        if k.startswith(("FR_", "SB_", "KN_", "RM_")):
            del os.environ[k]
    for name, ordner in (("FR_SEITEN", "seiten"), ("FR_DIENST", "dienst"), ("FR_KONTEN", "konten"), ("FR_SPERREN", "sperren"),
                         ("FR_SPEICHER", "speicher")):
        (tmp / ordner).mkdir(parents=True, exist_ok=True)
        os.environ[name] = str(tmp / ordner)
    os.environ["FR_WURZEL"] = str(wurzel)
    os.environ["FR_SCHREIBKOPIE"] = str(tmp / "arbeit")
    os.environ["SB_VEROEFFENTLICHEN"] = str(tmp / "ohne-veroeffentlichen")   # gibt es nicht: kein Veröffentlichen


GROSS = {}   # leer oder {"gross-erfunden": Quellordner}, gesetzt von main() bei --auffuellen
ZEITEN_JE_REISE = {}


def reisen_mit_kopien():
    """Reise -> (Quellordner, Person): die Beispielreisen und je eine Kopie unter anderem Namen (und die aufgefüllte)."""
    reisen = {**{r: (BEISPIEL / r, p) for r, p in REISEN.items()}, **{f"{r}-kopie": (BEISPIEL / r, p) for r, p in REISEN.items()}}
    for name, quelle in GROSS.items():
        reisen[name] = (quelle, REISEN["beispielreise"])
    return reisen


def aufgefuellte_reise(ziel, megabyte):
    """Kopie der Beispielreise mit megabyte MB Zufallsdateien in medien/ (erfunden; Fotos stehen bis Stufe 4 in der Datenbank)."""
    shutil.copytree(BEISPIEL / "beispielreise", ziel)
    (ziel / "medien").mkdir(exist_ok=True)
    for i in range(megabyte):
        (ziel / "medien" / f"foto-{i:03d}.jpg").write_bytes(os.urandom(1024 * 1024))
    return ziel


def instanz_speicher(tmp):
    wurzel = tmp / "instanz"
    wurzel.mkdir()
    umgebung(tmp, wurzel)
    reisen = reisen_mit_kopien()
    os.environ["FR_SPEICHERREISEN"] = ",".join(reisen)
    sys.path.insert(0, str(ENGINE))
    import reisespeicher
    for reise, (quelle, person) in reisen.items():
        reisespeicher.importieren(quelle, reise, wer=person["name"], grund="Messlauf (Beispielwert)")
    return wurzel, reisen


def instanz_git(tmp):
    """Reisen-Repo mit lokalem Origin (wie die Fixture `repo` in engine/tests/test_schreiben.py)."""
    origin, wurzel = tmp / "origin.git", tmp / "instanz"
    befehl("git", "init", "-q", "--bare", "-b", "main", str(origin))
    befehl("git", "clone", "-q", str(origin), str(wurzel))
    befehl("git", "-C", str(wurzel), "config", "user.email", "messlauf@example.invalid")
    befehl("git", "-C", str(wurzel), "config", "user.name", "Messlauf")
    befehl("git", "-C", str(wurzel), "checkout", "-q", "-b", "main")
    reisen = reisen_mit_kopien()
    for reise, (quelle, _) in reisen.items():
        shutil.copytree(quelle, wurzel / "reisen" / reise)
    (wurzel / "engine").symlink_to(ENGINE)
    (wurzel / ".gitignore").write_text("dist/\n__pycache__/\n")
    befehl("git", "-C", str(wurzel), "add", "-A")
    befehl("git", "-C", str(wurzel), "commit", "-q", "-m", "Beispielreisen")
    befehl("git", "-C", str(wurzel), "push", "-q", "-u", "origin", "main")
    umgebung(tmp, wurzel)
    sys.path.insert(0, str(ENGINE))
    return wurzel, reisen


class Zaehler:
    """Laufende Nummer für Werkzeugargumente, die jedes Mal etwas ändern."""

    def __init__(self):
        self.n, self.sperre = 0, threading.Lock()

    def naechste(self):
        with self.sperre:
            self.n += 1
            return self.n


def auftrag(i, n):
    """Werkzeug und Argumente des i-ten Vorgangs (Werkzeugmix, jedes Mal eine Änderung)."""
    art = i % 3
    if art == 0:
        return "frage_anlegen", {"text": f"Messfrage {n}: gibt es dort einen Markt? (Beispielwert)"}
    if art == 1:
        return "art_definieren", {"bezeichnung": f"Messart {n}", "grundform": "aufenthalt"}
    return "wissen_schreiben", {"titel": f"Messnotiz {n}", "text": f"Notiz {n} aus dem Messlauf (Beispielwert).",
                                "quelle": "Messlauf"}


def lauf(sb, wurzel, reisen, anzahl, faeden, zaehler):
    """anzahl Vorgänge mit faeden Fäden -> [(Code, Sekunden)]."""
    namen = sorted(reisen)

    def ein_vorgang(i):
        reise = namen[i % len(namen)] if faeden == 1 else namen[(i // 2) % len(namen)]   # parallel: je zwei auf einer Reise
        werkzeug, args = auftrag(i, zaehler.naechste())
        start = time.monotonic()
        code, _ = sb.anwenden_extern(sb.Schreiber(wurzel), reise, werkzeug, {**reisen[reise][1], "args": args})
        dauer = time.monotonic() - start
        ZEITEN_JE_REISE.setdefault(reise, []).append(dauer)
        return code, dauer

    if faeden == 1:
        return [ein_vorgang(i) for i in range(anzahl)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=faeden) as pool:
        return list(pool.map(ein_vorgang, range(anzahl)))


def quantil(werte, q):
    if not werte:
        return 0.0
    s = sorted(werte)
    return s[min(len(s) - 1, max(0, round(q * (len(s) - 1))))]


def kennzahlen(name, ergebnisse):
    dauer = [d for _, d in ergebnisse]
    codes = [c for c, _ in ergebnisse]
    mittel = statistics.mean(dauer) if dauer else 0.0
    print(f"{name}: Anzahl {len(ergebnisse)}, Mittel {mittel:.2f} s, p50 {quantil(dauer, 0.5):.2f} s, "
          f"p90 {quantil(dauer, 0.9):.2f} s, p99 {quantil(dauer, 0.99):.2f} s, Maximum {max(dauer, default=0.0):.2f} s; "
          f"504: {codes.count(504)}, 429: {codes.count(429)}, 5xx: {sum(1 for c in codes if 500 <= c < 600)}, "
          f"200: {codes.count(200)}, 422: {codes.count(422)}")


def teilzeiten(weg, reisen):
    """Export- und Probebauzeit einzeln (Export nur beim Speicherweg)."""
    import schreiben as sb
    export, probe = [], []
    for reise in sorted(reisen):
        with tempfile.TemporaryDirectory(prefix="frieda-messlauf-") as t:
            ordner = Path(t) / reise
            if weg == "speicher":
                import reisespeicher
                start = time.monotonic()
                reisespeicher.exportieren(reise, ordner)
                export.append(time.monotonic() - start)
            else:
                shutil.copytree(reisen[reise][0], ordner)
            start = time.monotonic()
            sb.warnungen_des_baus(ordner)
            probe.append(time.monotonic() - start)
    if export:
        print(f"Export: Anzahl {len(export)}, Mittel {statistics.mean(export):.3f} s, Maximum {max(export):.3f} s")
    else:
        print("Export: entfällt (Git-Weg: Arbeitskopie über fetch und checkout)")
    print(f"Probebau: Anzahl {len(probe)}, Mittel {statistics.mean(probe):.3f} s, Maximum {max(probe):.3f} s")


def main():
    a = argparse.ArgumentParser(description="Messlauf des Schreibwegs (#347)")
    a.add_argument("--weg", choices=("speicher", "git"), default="speicher")
    a.add_argument("--anzahl", type=int, default=40, help="Vorgänge je Lauf")
    a.add_argument("--parallel", type=int, default=4, help="Fäden im parallelen Lauf")
    a.add_argument("--auffuellen", type=int, default=0, help="zusätzliche Reise gross-erfunden auf MB Megabyte auffüllen")
    o = a.parse_args()
    tmp = Path(tempfile.mkdtemp(prefix="frieda-messlauf-"))
    try:
        if o.auffuellen:
            GROSS["gross-erfunden"] = aufgefuellte_reise(tmp / "quelle-gross", o.auffuellen)
        wurzel, reisen = instanz_speicher(tmp) if o.weg == "speicher" else instanz_git(tmp)
        import schreiben as sb
        zaehler = Zaehler()
        print(f"Messlauf Schreibweg: Weg {o.weg}, Reisen {', '.join(sorted(reisen))}")
        kennzahlen("nacheinander", lauf(sb, wurzel, reisen, o.anzahl, 1, zaehler))
        kennzahlen("parallel", lauf(sb, wurzel, reisen, o.anzahl, max(2, o.parallel), zaehler))
        teilzeiten(o.weg, reisen)
        if "gross-erfunden" in ZEITEN_JE_REISE:
            z = ZEITEN_JE_REISE["gross-erfunden"]
            print(f"gross-erfunden ({o.auffuellen} MB) einzeln: Anzahl {len(z)}, Mittel {statistics.mean(z):.2f} s, "
                  f"p90 {quantil(z, 0.9):.2f} s, Maximum {max(z):.2f} s")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
