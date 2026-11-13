"""Tests für das Hilfsprogramm mit Root-Rechten, das den nginx-Baustein einer Reise anlegt, erneuert, nennt oder entfernt
(#552, betrieb/vorlagen/nginx-reise-installieren.py, Spec docs/specs/betrieb/dienstrechte-552.md, AC-4 bis AC-7).

Muster: test_nginx_helfer.py (Orte-Helfer, #445). Das Hilfsprogramm entsteht wie auf dem Server mit
`einrichten.sh --erzeugen` (erfundene Instanz „probe“, Seiten /srv/probe/seiten, Port 8781, Zone probe_api) und läuft hier
direkt mit Parametern in einem Testordner, ohne root. Unter /etc wird nichts gelesen oder geschrieben.

Schnittstelle des Hilfsprogramms, die diese Tests festlegen (RED-Phase, #552):
- Konstanten INSTANZ, SNIPPETS, SICHERUNG="/var/lib/<instanz>-nginx-sicherung", NGINX="/usr/sbin/nginx",
  SYSTEMCTL="/usr/bin/systemctl", UMGEBUNG (feste Umgebung der Unterprozesse), MUSTER (Reisename).
- Ausnahme Abgelehnt (Ausgang 3).
- installieren(reise: str, snippets=…, sicherung=…, sperre=…, nginx=…, testen=…, neu_laden=…) -> (ausgang, pfad):
  ausgang 0 (angelegt oder erneuert und geladen), 2 (nichts zu tun), 4, 5, 6 wie beim Orte-Helfer; pfad ist das erste Glied
  des geheimen Links („<reise>-<token>“, bei von Hand angelegten Bausteinen der vorhandene Pfad). Abgelehnt bei Ausgang 3.
- pfad_lesen(reise, snippets=…) -> Pfad des vorhandenen Bausteins oder None (Lesemodus, ersetzt „sudo cat“).
- entfernen(reise, snippets=…, sicherung=…, sperre=…, nginx=…, testen=…, neu_laden=…) -> 0, 2, 4, 5, 6.
- main(argv, daten=None, **kw) -> Ausgang. argv ist ["helfer"] (installieren), ["helfer", "--pfad"] (Lesemodus) oder
  ["helfer", "--entfernen"]; daten ist der Reisename (bytes, stdin). Ausgabe auf stdout nur der Pfad (bei 0 und 2 des
  Installierens und beim Lesemodus), nie der Inhalt des Bausteins. Kein Pfad endet mit einem Traceback.
"""
import fcntl
import importlib.machinery
import importlib.util
import os
import re
import stat
import subprocess
from pathlib import Path

import pytest

BETRIEB = Path(__file__).resolve().parents[2] / "betrieb"
VORLAGE = BETRIEB / "vorlagen" / "nginx-reise-installieren.py"
REISE_VORLAGE = BETRIEB / "vorlagen" / "nginx-reise.conf"
SAUBER = {k: v for k, v in os.environ.items() if not k.startswith(("FR_", "RM_", "KN_", "EA_", "VF_", "FS_", "WA_", "EI_"))}
SEITEN = "/srv/probe/seiten"


def lade(datei, name):
    spec = importlib.util.spec_from_file_location(name, datei, loader=importlib.machinery.SourceFileLoader(name, str(datei)))
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def soll_baustein(reise, pfad):
    """Der Baustein, wie ihn bisher freischalten.sh aus der Vorlage erzeugte (Beispielwerte der Instanz probe)."""
    text = REISE_VORLAGE.read_text(encoding="utf-8")
    return (text.replace("__REISE__-__TOKEN__", pfad).replace("__TOKEN__", pfad.rsplit("-", 1)[1]).replace("__REISE__", reise)
            .replace("__SEITEN__", SEITEN).replace("__RM_PORT__", "8781").replace("__ZONE__", "probe_api")
            .replace("__INSTANZ__", "probe"))


@pytest.fixture
def erzeugt(tmp_path):
    ziel = tmp_path / "soll"
    env = {**SAUBER, "FR_WURZEL": str(tmp_path), "FR_INSTANZ": "probe", "FR_TITEL": "Probe", "FR_BENUTZER": "hans",
           "FR_SEITEN": SEITEN, "FR_RM_PORT": "8781", "EI_ZIEL": str(ziel)}
    r = subprocess.run(["bash", str(BETRIEB / "einrichten.sh"), "--erzeugen"], env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return ziel / "sbin" / "probe-nginx-reise-installieren"


@pytest.fixture
def h(tmp_path, erzeugt):
    modul = lade(erzeugt, "nginx_reise_helfer")
    snippets = tmp_path / "snippets"
    snippets.mkdir()
    nginx = tmp_path / "nginx"
    nginx.write_text("#!/bin/sh\n")
    nginx.chmod(0o755)
    zustand = {"tests": [], "laden": [], "test_ergebnisse": [], "laden_ok": True}

    def testen():
        zustand["tests"].append(sorted(p.name for p in snippets.iterdir()))
        return zustand["test_ergebnisse"].pop(0) if zustand["test_ergebnisse"] else True

    def neu_laden():
        zustand["laden"].append(1)
        return zustand["laden_ok"]

    kw = {"snippets": str(snippets), "sicherung": str(tmp_path / "sicherung"), "sperre": str(tmp_path / "sperre"),
          "nginx": str(nginx), "testen": testen, "neu_laden": neu_laden}

    def main(daten, *argv):
        if isinstance(daten, str):
            daten = daten.encode("utf-8")
        return modul.main(["helfer", *argv], daten, **kw)

    return {"m": modul, "kw": kw, "main": main, "snippets": snippets, "z": zustand, "tmp": tmp_path,
            "ziel": snippets / "probe-beispielreise.conf", "sicherung": tmp_path / "sicherung", "datei": erzeugt}


def test_erzeugt_ohne_platzhalter_mit_festem_start(erzeugt):
    text = erzeugt.read_text(encoding="utf-8")
    assert text.startswith("#!/usr/bin/python3 -I\n")
    assert not re.search(r"__[A-Z_]+__", text)
    # Vorlage und Werte sind eingebacken: keine Umgebung, kein Pfad ins Repo der Instanz
    assert "os.environ" not in text and "getenv" not in text
    assert "proxy_pass http://127.0.0.1:8781/" in text and SEITEN in text


# ---------- AC-4: Grammatik der Eingabe ----------

@pytest.mark.parametrize("eingabe", [b"", b"Beispielreise", b"../beispielreise", b"beispiel/reise", b"beispiel reise",
                                     b"a", b"x" * 41, b"beispielreise\nzweite", b"-beispielreise", b"beispiel\x00reise",
                                     "beispielreisé".encode("utf-8"), b"beispielreise;", b"beispielreise.conf"])
def test_eingabe_grammatik(h, eingabe):
    assert h["main"](eingabe) == 3
    assert h["main"](eingabe, "--pfad") == 3
    assert h["main"](eingabe, "--entfernen") == 3
    assert list(h["snippets"].iterdir()) == []
    assert not h["z"]["tests"] and not h["z"]["laden"]


@pytest.mark.parametrize("argv", [("--andere",), ("--pfad", "x"), ("beispielreise",), ("--pfad", "--entfernen")])
def test_argumente_ausser_den_modi_werden_abgelehnt(h, argv):
    assert h["main"](b"beispielreise", *argv) == 3
    assert list(h["snippets"].iterdir()) == []


# ---------- AC-5: Token und Ersetzen ----------

def test_token_bleibt(h, capsys):
    assert h["main"](b"beispielreise") == 0
    pfad = capsys.readouterr().out.strip()
    assert re.fullmatch(r"beispielreise-[A-Za-z0-9_-]{16,}", pfad), pfad
    inhalt = h["ziel"].read_text(encoding="utf-8")
    assert inhalt == soll_baustein("beispielreise", pfad)
    assert stat.S_IMODE(h["ziel"].stat().st_mode) == 0o640
    assert len(h["z"]["tests"]) == 1 and len(h["z"]["laden"]) == 1
    # Zweiter Lauf: alles gleich -> 2, derselbe Pfad, kein nginx
    assert h["main"](b"beispielreise") == 2
    assert capsys.readouterr().out.strip() == pfad
    assert h["ziel"].read_text(encoding="utf-8") == inhalt and len(h["z"]["laden"]) == 1
    # Vorlage geändert (hier: Baustein veraltet) -> Erneuerung mit demselben Token
    h["ziel"].write_text(inhalt.replace("client_max_body_size 11m;", "client_max_body_size 1m;"), encoding="utf-8")
    assert h["main"](b"beispielreise") == 0
    assert capsys.readouterr().out.strip() == pfad
    assert h["ziel"].read_text(encoding="utf-8") == inhalt
    assert len(list(h["sicherung"].iterdir())) == 1


def test_zwei_reisen_bekommen_verschiedene_token(h, capsys):
    assert h["main"](b"beispielreise") == 0
    a = capsys.readouterr().out.strip()
    assert h["main"](b"stadtwochenende") == 0
    b = capsys.readouterr().out.strip()
    assert a.rsplit("-", 1)[1] != b.rsplit("-", 1)[1]


def test_von_hand_angelegter_pfad_bleibt(h, capsys):
    """Ein von Hand angelegter Baustein trägt einen anderen Namen als den Ordner der Reise: der Link bleibt."""
    alt = soll_baustein("beispielreise", "rundreise-abc123def456")
    h["ziel"].write_text(alt.replace("no-cache", "no-store"), encoding="utf-8")
    assert h["main"](b"beispielreise") == 0
    assert capsys.readouterr().out.strip() == "rundreise-abc123def456"
    assert h["ziel"].read_text(encoding="utf-8") == alt


def test_symlink_statt_baustein_wird_abgelehnt(h):
    fremd = h["tmp"] / "fremd.conf"
    fremd.write_text("geheim\n")
    h["ziel"].symlink_to(fremd)
    assert h["main"](b"beispielreise") == 3
    assert fremd.read_text() == "geheim\n" and h["ziel"].is_symlink()
    assert not h["z"]["tests"]


def test_belegte_sperre(h):
    fd = os.open(h["kw"]["sperre"], os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert h["main"](b"beispielreise") == 3
        assert list(h["snippets"].iterdir()) == []
    finally:
        os.close(fd)


# ---------- AC-6: Rückweg und Ausgänge ----------

def test_rueckweg_und_ausgaenge(h, capsys):
    # neuer Baustein, nginx -t scheitert: Baustein wieder weg, kein Reload, 4
    h["z"]["test_ergebnisse"] = [False, True]
    assert h["main"](b"beispielreise") == 4
    assert not h["ziel"].exists() and not h["z"]["laden"]
    assert capsys.readouterr().out == ""
    # angelegt; dann Erneuerung, nginx -t scheitert: alter Stand zurück, 4
    assert h["main"](b"beispielreise") == 0
    pfad = capsys.readouterr().out.strip()
    gut = h["ziel"].read_text(encoding="utf-8")
    veraltet = gut.replace("no-cache", "no-store")
    h["ziel"].write_text(veraltet, encoding="utf-8")
    laden = len(h["z"]["laden"])
    h["z"]["test_ergebnisse"] = [False, True]
    assert h["main"](b"beispielreise") == 4
    assert h["ziel"].read_text(encoding="utf-8") == veraltet and len(h["z"]["laden"]) == laden
    # auch der zweite nginx -t scheitert: 6, Sicherung bleibt
    h["z"]["test_ergebnisse"] = [False, False]
    assert h["main"](b"beispielreise") == 6
    assert any(p.read_text(encoding="utf-8") == veraltet for p in h["sicherung"].iterdir())
    assert len(h["z"]["laden"]) == laden
    # Reload scheitert: 5, neuer Stand installiert und getestet
    h["ziel"].write_text(veraltet, encoding="utf-8")
    h["z"]["test_ergebnisse"] = []
    h["z"]["laden_ok"] = False
    assert h["main"](b"beispielreise") == 5
    assert h["ziel"].read_text(encoding="utf-8") == gut
    assert pfad.startswith("beispielreise-")


def test_entfernen(h, capsys):
    assert h["main"](b"beispielreise", "--entfernen") == 2
    assert h["main"](b"beispielreise") == 0
    capsys.readouterr()
    inhalt = h["ziel"].read_text(encoding="utf-8")
    assert h["main"](b"beispielreise", "--entfernen") == 0
    assert not h["ziel"].exists()
    assert any(p.read_text(encoding="utf-8") == inhalt for p in h["sicherung"].iterdir())
    # nginx -t scheitert nach dem Entfernen: Baustein zurück, 4
    assert h["main"](b"beispielreise") == 0
    capsys.readouterr()
    h["z"]["test_ergebnisse"] = [False, True]
    assert h["main"](b"beispielreise", "--entfernen") == 4
    assert h["ziel"].exists()


# ---------- AC-7: feste Umgebung, Lesemodus ----------

def test_umgebung_fest(h, monkeypatch, capsys):
    m = h["m"]
    assert m.NGINX == "/usr/sbin/nginx" and m.SYSTEMCTL == "/usr/bin/systemctl"
    assert m.SICHERUNG == "/var/lib/probe-nginx-sicherung" and m.INSTANZ == "probe"
    assert set(m.UMGEBUNG) == {"PATH"} and m.UMGEBUNG["PATH"].startswith("/usr/sbin:")
    falle = h["tmp"] / "falle"
    falle.mkdir()
    monkeypatch.setenv("PATH", str(falle))
    monkeypatch.setenv("PYTHONPATH", str(falle))
    monkeypatch.setenv("FR_SEITEN", str(falle))
    monkeypatch.setenv("FR_NGINX_SNIPPETS", str(falle))
    assert h["main"](b"beispielreise") == 0
    pfad = capsys.readouterr().out.strip()
    assert list(falle.iterdir()) == []
    assert h["ziel"].read_text(encoding="utf-8") == soll_baustein("beispielreise", pfad)


def test_lesemodus(h, capsys):
    assert h["main"](b"beispielreise", "--pfad") == 2
    assert capsys.readouterr().out == ""
    assert h["main"](b"beispielreise") == 0
    pfad = capsys.readouterr().out.strip()
    tests = len(h["z"]["tests"])
    assert h["main"](b"beispielreise", "--pfad") == 0
    aus = capsys.readouterr().out
    assert aus == pfad + "\n"
    assert "alias" not in aus and "location" not in aus
    assert len(h["z"]["tests"]) == tests and h["m"].pfad_lesen("beispielreise", snippets=h["kw"]["snippets"]) == pfad


# ---------- #552, Entscheidung 9: Bausteine lesbar für die Gruppe des Dienstbenutzers ----------

def test_baustein_mit_gruppe_der_instanz(tmp_path, monkeypatch):
    """Der Reise-Helfer installiert mit 0640 root:<FR_GRUPPE>; die Gruppe ist eingebacken, kein Argument nennt sie."""
    ziel = tmp_path / "soll"
    env = {**SAUBER, "FR_WURZEL": str(tmp_path), "FR_INSTANZ": "probe", "FR_TITEL": "Probe", "FR_BENUTZER": "hans",
           "FR_GRUPPE": "reisegruppe", "FR_SEITEN": SEITEN, "FR_RM_PORT": "8781", "EI_ZIEL": str(ziel)}
    r = subprocess.run(["bash", str(BETRIEB / "einrichten.sh"), "--erzeugen"], env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    m = lade(ziel / "sbin" / "probe-nginx-reise-installieren", "nginx_reise_helfer_gruppe")
    assert m.GRUPPE == "reisegruppe"
    assert m.main(["helfer", "--gruppe"], b"beispielreise") == 3
    aufrufe = []
    monkeypatch.setattr(m.os, "geteuid", lambda: 0)
    monkeypatch.setattr(m.os, "fchown", lambda fd, uid, gid: aufrufe.append((uid, gid)))
    monkeypatch.setattr(m.grp, "getgrnam", lambda n: type("G", (), {"gr_gid": 4711})() if n == "reisegruppe" else None)
    snippets = tmp_path / "snippets"
    snippets.mkdir()
    m.ersetzen(b"x\n", str(snippets), str(snippets / "probe-beispielreise.conf"))
    assert aufrufe == [(0, 4711)]
    assert stat.S_IMODE((snippets / "probe-beispielreise.conf").stat().st_mode) == 0o640
