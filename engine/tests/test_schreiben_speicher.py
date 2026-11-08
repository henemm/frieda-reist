"""Tests für den Schreibweg über den Reisespeicher (Stufe 2, #347, Epic #345, ADR-0009; Spec
docs/specs/betrieb/schreibweg-speicher-347.md). Nur mit den beiden erfundenen Beispielreisen (beispielreise: Ida, Karl;
stadtwochenende: Tom, Lea) und erfundenen Testdaten, alles unter tmp_path.

Aufbau der Fixture `speicher`: eine Instanz ohne Git (FR_WURZEL ohne .git, keine Arbeitskopie), der Speicher unter
tmp_path mit beiden Beispielreisen (importieren) und FR_SPEICHERREISEN mit beiden Namen. Veröffentlichen ist ein Stummel.

Was diese Tests als Schnittstelle festlegen (die Spec lässt es offen):
  instanz.speicherreisen()      -> list[str] aus FR_SPEICHERREISEN (kommagetrennt, Leerzeichen und leere Teile fallen weg)
  schreiben.anwenden_extern(s, reise, werkzeug, anfrage)   bleibt der Eingang des Dienstes für beide Wege; s =
                                schreiben.Schreiber(wurzel). Der Weg richtet sich nach instanz.speicherreisen().
  schreiben_git.vorgang(s, reise, werkzeug, anfrage, start)   der bisherige Git-Weg (vorher schreiben.vorgang), bis Stufe 5
  Patch-Ziele sind Modulattribute: reisespeicher.exportieren, reisespeicher.vorgang_eingetragen, schreiben.befehl_mit_frist,
                                schreiben.secrets.token_hex, schreiben.ZEIT_GESAMT / ZEIT_SPERRE / ZEIT_PRUEFUNG.
                                Die Zeitgrenzen gibt es nur in schreiben.py; schreiben_git liest sie zur Laufzeit von dort.
  Ablauf im Elternprozess:      Sperre, basis = reisespeicher.stand_nummer(reise), reisespeicher.exportieren(reise, <tmp>,
                                bis=basis), dann der Unterprozess `anwenden` über schreiben.befehl_mit_frist mit FR_VORGANG.
                                Der Unterprozess läuft mit dem Code des laufenden Dienstes (im Betrieb <FR_DIENST>), nicht
                                mit dem einer Git-Arbeitskopie; die Tests geben ihm keinen eigenen Code-Ordner.
  Antwort:                      commit = Vorgangs-Nummer als Text, stand.gesichert = neue Stand-Nummer.
  Temporäre Ordner:             über tempfile (der Test lenkt tempfile.tempdir und TMPDIR in einen eigenen Ordner).

Die neuen Module (schreiben_git, stand_git) und das Messlauf-Skript werden erst in den Tests geladen: Fehlt eines,
scheitert jeder Test einzeln."""
import fcntl
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import types
import urllib.error
import urllib.request
from contextlib import closing
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest
import yaml

ENGINE = Path(__file__).resolve().parents[1]
WURZEL = ENGINE.parent
BEISPIEL = WURZEL / "beispiel" / "reisen"
sys.path.insert(0, str(ENGINE))
import schreiben as sb  # noqa: E402
from conftest import meldet  # noqa: E402
from test_schreiben import repo, git  # noqa: E402,F401  (Fixture des Git-Wegs: Reisen-Repo mit origin)

IDA = {"person": "ida", "name": "Ida", "rolle": "organisator"}
KARL = {"person": "karl", "name": "Karl", "rolle": "mitwirkend"}
TOM = {"person": "tom", "name": "Tom", "rolle": "organisator"}
LEA = {"person": "lea", "name": "Lea", "rolle": "mitwirkend"}
REISEN = {"beispielreise": (IDA, KARL), "stadtwochenende": (TOM, LEA)}
ART = {"bezeichnung": "Refugi", "grundform": "aufenthalt"}            # Beispielwert
DONE = re.compile(r"^Done (\w+) (\d{3}) in \d+\.\d s$", re.M)


@pytest.fixture
def speicher(tmp_path, monkeypatch):
    """Instanz ohne Git mit beiden Beispielreisen im Speicher -> Namespace(rs, wurzel, tmp, stempel, schreiber)."""
    for k in list(os.environ):
        if k.startswith(("FR_", "SB_", "KN_", "RM_")):
            monkeypatch.delenv(k)
    wurzel = tmp_path / "instanz"
    wurzel.mkdir()
    (tmp_path / "sperren").mkdir()
    stempel = tmp_path / "veroeffentlicht"
    stub = tmp_path / "veroeffentlichen.sh"
    stub.write_text(f"#!/bin/sh\necho \"$FR_WURZEL\" >> {stempel}\n")
    stub.chmod(0o755)
    monkeypatch.setenv("FR_WURZEL", str(wurzel))
    monkeypatch.setenv("FR_SCHREIBKOPIE", str(tmp_path / "keine-arbeitskopie"))
    monkeypatch.setenv("SB_VEROEFFENTLICHEN", str(stub))
    monkeypatch.setenv("FR_KONTEN", str(tmp_path / "konten"))
    monkeypatch.setenv("FR_SPERREN", str(tmp_path / "sperren"))
    monkeypatch.setenv("FR_DIENST", str(tmp_path / "_dienst"))
    monkeypatch.setenv("FR_SPEICHER", str(tmp_path / "_speicher"))
    monkeypatch.setenv("FR_SPEICHERREISEN", "beispielreise,stadtwochenende")
    tmp = tmp_path / "tmp"
    tmp.mkdir()
    monkeypatch.setenv("TMPDIR", str(tmp))
    monkeypatch.setattr(tempfile, "tempdir", str(tmp))
    import reisespeicher as rs
    rs.importieren(BEISPIEL / "beispielreise", "beispielreise", wer="Ida", grund="Beispiel")
    rs.importieren(BEISPIEL / "stadtwochenende", "stadtwochenende", wer="Tom", grund="Beispiel")
    return types.SimpleNamespace(rs=rs, wurzel=wurzel, tmp=tmp, stempel=stempel, schreiber=lambda: sb.Schreiber(wurzel))


def schreib(sp, reise, werkzeug, anfrage):
    return sb.anwenden_extern(sp.schreiber(), reise, werkzeug, anfrage)


def zustand(sp, reise):
    return sp.rs.stand_nummer(reise), sp.rs.aktueller_stand(reise)


def kaputter_speicher(tmp_path, monkeypatch):
    """Datenbank nicht lesbar: reisen.db ist keine SQLite-Datei (sqlite3.DatabaseError)."""
    kaputt = tmp_path / "kaputt"
    kaputt.mkdir()
    (kaputt / "reisen.db").write_bytes(b"keine Datenbank " * 64)
    monkeypatch.setenv("FR_SPEICHER", str(kaputt))


class Dienst:
    """Der HTTP-Dienst in einem Thread; get(pfad, geheim=True) -> (code, json)."""

    def __init__(self, schreiber):
        import konten
        self.geheim = konten.dienst_geheimnis()
        sb.Dienst.schreiber = schreiber
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), sb.Dienst)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.basis = f"http://127.0.0.1:{self.server.server_address[1]}"

    def get(self, pfad, geheim=True):
        req = urllib.request.Request(f"{self.basis}/{pfad}", headers={"X-Frieda-Dienst": self.geheim} if geheim else {})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.server.shutdown()
        sb.Dienst.schreiber = None


# ---------- AC-5: Schalter je Reise ----------

def test_schalter_vorgabe_ist_git(repo, monkeypatch, tmp_path):
    import instanz
    import reisespeicher
    monkeypatch.delenv("FR_SPEICHERREISEN", raising=False)
    assert instanz.speicherreisen() == []
    monkeypatch.setenv("FR_SPEICHERREISEN", "")
    assert instanz.speicherreisen() == []
    monkeypatch.setenv("FR_SPEICHERREISEN", " beispielreise, ,stadtwochenende ,")
    assert instanz.speicherreisen() == ["beispielreise", "stadtwochenende"]
    monkeypatch.delenv("FR_SPEICHERREISEN")
    datei = tmp_path / "einstellungen.env"
    datei.write_text("FR_SPEICHERREISEN=stadtwochenende\n", encoding="utf-8")
    monkeypatch.setenv("FR_EINSTELLUNGEN", str(datei))
    assert instanz.speicherreisen() == ["stadtwochenende"]
    monkeypatch.delenv("FR_EINSTELLUNGEN")
    assert "FR_SPEICHERREISEN" in instanz.__doc__
    assert re.search(r"^#?FR_SPEICHERREISEN=", (WURZEL / "betrieb" / "einstellungen.beispiel").read_text(encoding="utf-8"), re.M)
    # ohne Einstellung: jede Reise schreibt über Git wie vor dieser Stufe, der Speicher bleibt unberührt
    wurzel, origin, arbeit, _ = repo
    vorher = git(origin, "rev-parse", "main")
    code, a = sb.anwenden_extern(sb.Schreiber(wurzel, arbeit), "beispielreise", "art_definieren", {**IDA, "args": ART})
    assert code == 200 and a["ok"], a
    assert git(origin, "rev-parse", "main") == a["commit"] != vorher
    assert not reisespeicher.pfad().exists()


# ---------- AC-6: ein Vorgang je Schreibvorgang ----------

@pytest.mark.parametrize("reise", sorted(REISEN))
def test_speicherweg_schreibt_einen_vorgang(speicher, monkeypatch, reise):
    org, _ = REISEN[reise]
    rs = speicher.rs
    monkeypatch.setattr(sb.secrets, "token_hex", lambda n=6: "a1b2c3d4e5f6")
    basis = rs.stand_nummer(reise)
    frage = "Gibt es dort samstags einen Markt? (Beispielwert)"
    code, a = schreib(speicher, reise, "frage_anlegen", {**org, "args": {"text": frage}})
    assert code == 200 and a["ok"], a
    assert rs.stand_nummer(reise) == basis + 1
    e = rs.verlauf(reise, n=1)[0]
    assert a["commit"] == str(e["vorgang"])
    assert a["stand"]["gesichert"] == basis + 1 and "veroeffentlicht" in a["stand"]
    assert e["werkzeug"] == "frage_anlegen" and e["wer"] == org["name"] and e["nummer"] == basis + 1
    titel_der_reise = yaml.safe_load((BEISPIEL / reise / "reise.yaml").read_text(encoding="utf-8")).get("titel") or reise
    assert e["was"] and not e["was"].startswith(f"{titel_der_reise}: ") and "\n" not in e["was"]
    assert org["name"] in e["grund"]                                    # Fuß des Vorgangs in der Sprache der Reise
    with closing(sqlite3.connect(rs.pfad())) as v:
        assert v.execute("SELECT rolle, kennung FROM vorgaenge WHERE nummer = ?", (e["vorgang"],)).fetchone() == \
            ("organisator", "a1b2c3d4e5f6")
    neu = rs.aktueller_stand(reise)
    assert e["dateien"] and all(p in neu for p in e["dateien"])
    assert any(frage.encode() in neu[p] for p in e["dateien"])
    assert not (speicher.wurzel / ".git").exists() and not (speicher.wurzel / "reisen").exists()
    assert not Path(os.environ["FR_SCHREIBKOPIE"]).exists() and not list(speicher.tmp.iterdir())


# ---------- AC-7: Ablehnungen lassen den Stand unverändert ----------

@pytest.mark.parametrize("reise", sorted(REISEN))
def test_abgelehnte_vorgaenge_lassen_den_stand_unveraendert(speicher, monkeypatch, reise):
    org, mit = REISEN[reise]
    code, a = schreib(speicher, reise, "art_definieren", {**org, "args": ART})
    assert code == 200, a
    vorher = zustand(speicher, reise)

    def abgelehnt(code_soll, werkzeug, anfrage):
        code, a = schreib(speicher, reise, werkzeug, anfrage)
        assert code == code_soll and a["ok"] is False and a.get("fehler_code"), (code, a)
        assert zustand(speicher, reise) == vorher
        assert not list(speicher.tmp.iterdir()), "temporärer Ordner nicht gelöscht"
        return a

    abgelehnt(422, "art_definieren", {**mit, "args": {"bezeichnung": "X", "grundform": "aufenthalt"}})   # Rolle
    abgelehnt(422, "art_definieren", {**org, "args": ART})                                             # nichts geändert
    if reise == "beispielreise":                                                                      # Probebau
        a = abgelehnt(422, "merkmal_definieren", {**org, "args": {"art": "pension", "merkmal": "fruehstueck",
                                                                     "werte": ["ja", "nein"]}})
        assert a["fehler_code"].startswith("schreiben.bau.")
    monkeypatch.setattr(sb, "ZEIT_SPERRE", 0.2)
    with open(sb.sperrdatei(reise), "w") as f:                                                        # Sperre belegt
        fcntl.flock(f, fcntl.LOCK_EX)
        a = abgelehnt(429, "art_definieren", {**org, "args": {"bezeichnung": "Finca", "grundform": "aufenthalt"}})
    assert a["fehler_code"] == "schreiben.dienst.besetzt"


# ---------- AC-8: Reise der Liste ohne Eintrag; Speicher nicht erreichbar ----------

def test_reise_der_liste_ohne_eintrag_gibt_503_ohne_wirkung(speicher, monkeypatch, tmp_path):
    rs = speicher.rs
    monkeypatch.setenv("FR_SPEICHERREISEN", "beispielreise,stadtwochenende,dritte-reise")
    code, a = schreib(speicher, "dritte-reise", "art_definieren", {**IDA, "args": ART})
    assert code == 503 and a["ok"] is False and a["fehler_code"] == "schreiben.dienst.reise_nicht_im_speicher", a
    assert rs.reisen() == ["beispielreise", "stadtwochenende"] and rs.stand_nummer("dritte-reise") is None
    assert not (speicher.wurzel / "reisen").exists() and not list(speicher.tmp.iterdir())
    kaputter_speicher(tmp_path, monkeypatch)
    code, a = schreib(speicher, "beispielreise", "art_definieren", {**IDA, "args": ART})
    assert code == 503 and a["fehler_code"] == "schreiben.dienst.speicher_nicht_erreichbar", a


@pytest.mark.parametrize("art", ["fehlt", "beschaedigt"])
def test_ablagefehler_gibt_saubere_antwort_ohne_wirkung(speicher, art):
    """Stufe 4 (#349, F002): Fehlt eine Datei der Ablage oder ist sie beschädigt, antwortet der Schreibweg mit 503 und
    pruefung.bauen.79/.80 (Schlüssel und Werte für den Konnektor), schreibt nichts und hinterlässt keinen Ordner; eine
    andere Reise liest die Datei als „nicht lesbar“ (fremde_datei)."""
    rs = speicher.rs
    with closing(sqlite3.connect(rs.pfad())) as v:
        pfad, summe = v.execute("SELECT pfad, pruefsumme FROM versionen WHERE reise = 'beispielreise' "
                                "AND ausgelagert = 1 ORDER BY pfad LIMIT 1").fetchone()
    f = rs.ablage_pfad(summe)
    os.chmod(f.parent, 0o700)
    if art == "fehlt":
        f.unlink()
    else:
        os.chmod(f, 0o600)
        f.write_bytes(b"kaputt")
    vorher = rs.stand_nummer("beispielreise")
    org, _ = REISEN["beispielreise"]
    code, a = schreib(speicher, "beispielreise", "frage_anlegen", {**org, "args": {"text": "Markt? (Beispielwert)"}})
    schluessel = "pruefung.bauen.79" if art == "fehlt" else "pruefung.bauen.80"
    assert code == 503 and a["ok"] is False and a["fehler_code"] == schluessel, a
    assert a["werte"]["ziel"] == pfad and a["werte"]["w1"] == "beispielreise" and "{" not in a["fehler"]
    assert rs.stand_nummer("beispielreise") == vorher and not list(speicher.tmp.iterdir())
    assert sb.fremde_datei(speicher.wurzel / "reisen" / "stadtwochenende", "beispielreise", pfad) is None


# ---------- AC-9: der Git-Weg lehnt eine Reise der Liste ab ----------

def test_git_weg_lehnt_reise_der_liste_ab(repo, monkeypatch):
    import schreiben_git
    wurzel, origin, arbeit, _ = repo
    monkeypatch.setenv("FR_SPEICHERREISEN", "beispielreise")
    vorher = git(origin, "rev-parse", "main")
    git(wurzel, "remote", "set-url", "origin", str(wurzel / "gibt-es-nicht.git"))   # ein fetch fiele auf (503 Repo)
    s = sb.Schreiber(wurzel, arbeit)
    code, a = schreiben_git.vorgang(s, "beispielreise", "art_definieren", {**IDA, "args": ART}, time.monotonic())
    assert code == 503 and a["fehler_code"] == "schreiben.dienst.reise_im_speicher", (code, a)
    assert not Path(f"{arbeit}-beispielreise").exists()
    git(wurzel, "remote", "set-url", "origin", str(origin))
    assert git(origin, "rev-parse", "main") == vorher
    # über den Eingang des Dienstes: Liste gesetzt, Speicher leer -> Speicherweg, 503, kein Commit
    code, a = sb.anwenden_extern(s, "beispielreise", "art_definieren", {**IDA, "args": ART})
    assert code == 503 and a["fehler_code"] == "schreiben.dienst.reise_nicht_im_speicher", (code, a)
    assert git(origin, "rev-parse", "main") == vorher


# ---------- AC-10: zwischenzeitliche Änderung ----------

def test_zwischenzeitliche_aenderung_gibt_stand_geaendert(speicher, monkeypatch):
    """Ein anderer Vorgang schreibt nach dem Export der Arbeitskopie auf dieselbe Reise: Der erste Vorgang darf ihn nicht
    überschreiben (erwartet=basis), sondern antwortet 503 stand_geaendert."""
    rs = speicher.rs
    original = rs.exportieren
    basis = rs.stand_nummer("beispielreise")

    def export_und_fremder_vorgang(reise, ziel, bis=None):
        original(reise, ziel, bis=bis)
        rs.vorgang_schreiben(reise, {"inhalt/fremd.md": b"Karl war schneller (Beispielwert)\n"}, wer="Karl",
                             werkzeug="knowledge_write", titel="fremder Vorgang")
    monkeypatch.setattr(rs, "exportieren", export_und_fremder_vorgang)
    code, a = schreib(speicher, "beispielreise", "art_definieren", {**IDA, "args": ART})
    assert code == 503 and a["fehler_code"] == "schreiben.dienst.stand_geaendert", (code, a)
    assert rs.stand_nummer("beispielreise") == basis + 1
    jetzt = rs.aktueller_stand("beispielreise")
    assert jetzt["inhalt/fremd.md"].startswith(b"Karl") and b"refugi" not in jetzt["plan/arten.yaml"].lower()
    assert [e["was"] for e in rs.verlauf("beispielreise", n=1)] == ["fremder Vorgang"]
    assert not list(speicher.tmp.iterdir())


# ---------- AC-11: Nachprüfung nach Abbruch, lokal im Speicher ----------

def test_nach_abbruch_prueft_lokal_im_speicher(speicher, monkeypatch, capsys):
    rs = speicher.rs
    monkeypatch.setattr(sb.secrets, "token_hex", lambda n=6: "k0a1b2c3d4e5")
    basis = rs.stand_nummer("beispielreise")
    capsys.readouterr()

    def abbruch(eingetragen):
        def fake(argv, eingabe, frist, env=None):
            if eingetragen:   # der Unterprozess hat eingetragen und wurde danach von der Frist beendet
                rs.vorgang_schreiben("beispielreise", {"inhalt/abbruch.md": b"x\n"}, wer="Ida", werkzeug="art_definieren",
                                     titel="vor dem Abbruch", kennung=(env or {}).get("FR_VORGANG"))
            raise subprocess.TimeoutExpired(argv, frist)
        monkeypatch.setattr(sb, "befehl_mit_frist", fake)
        code, a = schreib(speicher, "beispielreise", "art_definieren", {**IDA, "args": ART})
        return code, a, capsys.readouterr().err

    code, a, err = abbruch(False)                                      # nicht eingetragen
    assert code == 504 and a["ok"] is False and a["fehler_code"] == "schreiben.dienst.zu_lange_nicht", a
    assert "Timeout art_definieren 504: aborted, not saved" in err and DONE.findall(err) == [("art_definieren", "504")]
    assert rs.stand_nummer("beispielreise") == basis

    original = rs.vorgang_eingetragen
    monkeypatch.setattr(rs, "vorgang_eingetragen", lambda *a, **k: (_ for _ in ()).throw(sqlite3.OperationalError("database is locked")))
    code, a, err = abbruch(False)                                      # Datenbank nicht lesbar
    assert code == 504 and a["fehler_code"] == "schreiben.dienst.zu_lange_ungeprueft", a
    assert "Timeout art_definieren 504: aborted, unchecked" in err and DONE.findall(err) == [("art_definieren", "504")]
    monkeypatch.setattr(rs, "vorgang_eingetragen", original)

    code, a, err = abbruch(True)                                       # eingetragen trotz Abbruch
    assert code == 200 and a["ok"] is True and meldet(a["text"], "schreiben.dienst.verzoegert"), a
    assert a["stand"]["gesichert"] == basis + 1 == rs.stand_nummer("beispielreise")
    assert rs.vorgang_eingetragen("k0a1b2c3d4e5").stand == basis + 1
    assert "Timeout art_definieren 504: aborted, saved" in err and DONE.findall(err) == [("art_definieren", "200")]
    assert not list(speicher.tmp.iterdir())


# ---------- AC-12: Fristen ----------

def test_speicherweg_haelt_die_fristen(speicher, monkeypatch, capsys):
    assert (sb.ZEIT_GESAMT, sb.ZEIT_SPERRE, sb.ZEIT_PRUEFUNG) == (25, 3, 3)
    rs = speicher.rs
    vorher = zustand(speicher, "beispielreise")
    capsys.readouterr()
    # Der Export dauert länger als die Frist: noch nichts angewendet, 504 „nicht eingetragen“, kein Unterprozess
    original = rs.exportieren
    gestartet = []
    with monkeypatch.context() as m:
        m.setattr(sb, "ZEIT_GESAMT", 1)
        m.setattr(rs, "exportieren", lambda *a, **k: (time.sleep(1.2), original(*a, **k))[1])
        m.setattr(sb, "befehl_mit_frist", lambda *a, **k: gestartet.append(a))
        start = time.monotonic()
        code, a = schreib(speicher, "beispielreise", "art_definieren", {**IDA, "args": ART})
        assert time.monotonic() - start < 1 + sb.ZEIT_PRUEFUNG + 1
    assert code == 504 and a["fehler_code"] == "schreiben.dienst.zu_lange_nicht" and not gestartet, (code, a, gestartet)
    assert DONE.findall(capsys.readouterr().err) == [("art_definieren", "504")]
    assert zustand(speicher, "beispielreise") == vorher and not list(speicher.tmp.iterdir())
    # Das Eintragen hängt an der Sperre der Datenbank: die Antwort kommt trotzdem in der Frist, ohne Wirkung
    monkeypatch.setattr(sb, "ZEIT_GESAMT", 4)
    halter = sqlite3.connect(rs.pfad(), timeout=0)
    halter.execute("BEGIN IMMEDIATE")
    try:
        start = time.monotonic()
        code, a = schreib(speicher, "beispielreise", "art_definieren", {**IDA, "args": ART})
        dauer = time.monotonic() - start
    finally:
        halter.rollback()
        halter.close()
    assert dauer < 4 + sb.ZEIT_PRUEFUNG + 1, dauer
    assert (code, a.get("fehler_code")) in {(503, "schreiben.dienst.speicher_nicht_erreichbar"),
                                            (504, "schreiben.dienst.zu_lange_nicht")}, (code, a)
    assert DONE.findall(capsys.readouterr().err) == [("art_definieren", str(code))]
    assert zustand(speicher, "beispielreise") == vorher


def test_haengender_export_ueberdauert_die_frist_nicht(speicher, monkeypatch, capsys):
    """Adversary F001 (AC-12): Ein Export, der länger hängt als ZEIT_GESAMT + ZEIT_PRUEFUNG, hält die Antwort nicht auf:
    504 „nicht eingetragen“ in der Frist, ohne Unterprozess, Stand unverändert, temporärer Ordner weg (auch nachdem der
    hängende Export doch noch fertig wird), genau eine Zeile „Done …“."""
    rs = speicher.rs
    vorher = zustand(speicher, "beispielreise")
    original = rs.exportieren
    gestartet = []
    monkeypatch.setattr(sb, "ZEIT_GESAMT", 0.5)
    haengt = 0.5 + sb.ZEIT_PRUEFUNG + 1
    monkeypatch.setattr(rs, "exportieren", lambda *a, **k: (time.sleep(haengt), original(*a, **k))[1])
    monkeypatch.setattr(sb, "befehl_mit_frist", lambda *a, **k: gestartet.append(a))
    capsys.readouterr()
    start = time.monotonic()
    code, a = schreib(speicher, "beispielreise", "art_definieren", {**IDA, "args": ART})
    dauer = time.monotonic() - start
    assert dauer < 0.5 + sb.ZEIT_PRUEFUNG + 0.5, dauer
    assert code == 504 and a["fehler_code"] == "schreiben.dienst.zu_lange_nicht" and not gestartet, (code, a)
    assert DONE.findall(capsys.readouterr().err) == [("art_definieren", "504")]
    assert zustand(speicher, "beispielreise") == vorher and not list(speicher.tmp.iterdir())
    time.sleep(max(0.0, haengt + 1 - dauer))                         # der hängende Export wird fertig und räumt auf
    assert zustand(speicher, "beispielreise") == vorher and not list(speicher.tmp.iterdir())


# ---------- AC-13: Buchung aus dem Speicher ----------

def test_buchung_wird_aus_dem_speicher_gelesen(speicher, monkeypatch, tmp_path):
    rs = speicher.rs
    routen = yaml.safe_load(rs.datei("beispielreise", "plan/routen.yaml"))
    routen["buchungen"]["B-02"] = {"fuer": ["U-01"], "status": "gebucht", "wer": "Karl"}   # Beispielwert
    rs.vorgang_schreiben("beispielreise", {"plan/routen.yaml": yaml.safe_dump(routen, allow_unicode=True).encode()},
                         wer="Karl", werkzeug="booking_create", titel="Buchung B-02")
    with Dienst(speicher.schreiber()) as d:
        assert d.get("beispielreise/buchung/B-01", geheim=False)[0] == 403
        assert d.get("beispielreise/buchung/B-01") == (200, {"gibt_es": True, "fuer": ["U-01"], "wer": "Ida"})
        assert d.get("beispielreise/buchung/B-02") == (200, {"gibt_es": True, "fuer": ["U-01"], "wer": "Karl"})
        code, b = d.get("stadtwochenende/buchung/B-01")
        assert code == 200 and b["gibt_es"] is True and b["fuer"] == ["E-01", "E-02"]
        assert d.get("beispielreise/buchung/B-77") == (200, {"gibt_es": False})
        assert d.get("beispielreise/buchung/U-01") == (200, {"gibt_es": False})
        monkeypatch.setenv("FR_SPEICHERREISEN", "beispielreise,stadtwochenende,dritte-reise")
        assert d.get("dritte-reise/buchung/B-01") == (200, {"gibt_es": False})
        kaputter_speicher(tmp_path, monkeypatch)
        code, b = d.get("beispielreise/buchung/B-01")
        assert code == 503 and b["fehler_code"] == "schreiben.dienst.speicher_nicht_erreichbar", b


# ---------- AC-14: Gesundheit ----------

def test_gesund_prueft_die_datenbank(speicher, monkeypatch, tmp_path):
    with Dienst(speicher.schreiber()) as d:
        assert d.get("gesund", geheim=False) == (200, {"gesund": True})     # ohne .git: der Speicher genügt
        kaputter_speicher(tmp_path, monkeypatch)
        assert d.get("gesund", geheim=False) == (503, {"gesund": False})


def test_gesund_ohne_datenbank_ist_ungesund_und_legt_nichts_an(speicher, monkeypatch, tmp_path):
    """Adversary F002 (AC-14): Fehlt reisen.db (falscher Ort, nicht eingerichtet), ist der Speicher nicht gesund; /gesund
    legt die Datenbank dabei nicht an."""
    leer = tmp_path / "leer"
    leer.mkdir()
    monkeypatch.setenv("FR_SPEICHER", str(leer))
    with Dienst(speicher.schreiber()) as d:
        assert d.get("gesund", geheim=False) == (503, {"gesund": False})
    assert not speicher.rs.pfad().exists() and not list(leer.iterdir())


# ---------- AC-15: neue Reise im Speicher ----------

def _auftrag(pfad):
    return {"id": "A-20261106-120000-abcd", "erstellt": "2026-11-06T12:00:00+00:00", "name": "Ida", "art": "Auftrag",
            "daten": {"neue_reise": {"titel": "Skiwoche im Allgäu", "von": "2027-02-06", "bis": "2027-02-13", "ziel": "Oberstdorf",
                                     "pfad": pfad, "personen": {"ida": {"name": "Ida", "rolle": "organisator"},
                                                                "karl": {"name": "Karl", "rolle": "mitwirkend"}},
                                     "wer": "Ida", "notiz": "Beispielwert"}}}


def test_reise_anlegen_schreibt_den_ersten_vorgang(speicher, monkeypatch):
    rs = speicher.rs
    monkeypatch.setenv("FR_SPEICHERREISEN", "beispielreise,stadtwochenende,skiwoche-allgaeu-2027")
    anfrage = {"person": None, "name": "Ida", "rolle": "organisator"}
    code, a = schreib(speicher, "skiwoche-allgaeu-2027", "reise_anlegen", {**anfrage, "args": {"auftrag": _auftrag("skiwoche-allgaeu-2027")}})
    assert code == 200 and a["ok"], a
    assert rs.stand_nummer("skiwoche-allgaeu-2027") == 1 and a["stand"]["gesichert"] == 1
    assert rs.reisen() == ["beispielreise", "skiwoche-allgaeu-2027", "stadtwochenende"]
    neu = rs.aktueller_stand("skiwoche-allgaeu-2027")
    assert "reise.yaml" in neu and "ids.yaml" in neu
    r = yaml.safe_load(neu["reise.yaml"])
    assert r["status"]["wert"] == "idee" and r["personen"]["karl"]["rolle"] == "mitwirkend"
    e = rs.verlauf("skiwoche-allgaeu-2027")[0]
    assert e["werkzeug"] == "reise_anlegen" and e["wer"] == "Ida" and a["commit"] == str(e["vorgang"])
    assert not (speicher.wurzel / "reisen").exists() and not list(speicher.tmp.iterdir())
    # vorhandener Name (im Speicher) und ungültige Anfrage legen nichts an
    vorher = {r_: zustand(speicher, r_) for r_ in rs.reisen()}
    for reise, args in (("stadtwochenende", {"auftrag": _auftrag("stadtwochenende")}),
                        ("skiwoche-allgaeu-2027", {"auftrag": _auftrag("skiwoche-allgaeu-2027")}),
                        ("skiwoche-allgaeu-2027", {})):
        code, a = schreib(speicher, reise, "reise_anlegen", {**anfrage, "args": args})
        assert code == 422 and a["ok"] is False, (reise, code, a)
    assert {r_: zustand(speicher, r_) for r_ in rs.reisen()} == vorher
    assert not list(speicher.tmp.iterdir())


# ---------- AC-16: Stand-Nachweis ----------

def test_gesichert_json_traegt_stand_und_vorgangsnummer(speicher):
    import stand
    code, a = schreib(speicher, "stadtwochenende", "art_definieren", {**TOM, "args": ART})
    assert code == 200, a
    n = speicher.rs.stand_nummer("stadtwochenende")
    g = json.loads((Path(os.environ["FR_DIENST"]) / "reise-stand" / "stadtwochenende.gesichert.json").read_text(encoding="utf-8"))
    assert g["nummer"] == n == 2 and g["commit"] == a["commit"] == str(speicher.rs.verlauf("stadtwochenende", 1)[0]["vorgang"])
    z = stand.lesen("stadtwochenende")
    assert z["gesichert"]["nummer"] == n and z["zustand"] == "wartet"   # bis Stufe 3 baut niemand aus dem Speicher
    assert stand.enthalten(z, n) is None


# ---------- AC-18 und AC-19: kein git ----------

def _git_aufrufe_im_quelltext(datei):
    import ast
    baum = ast.parse((ENGINE / datei).read_text(encoding="utf-8"))
    funde = []
    for k in ast.walk(baum):
        if isinstance(k, (ast.FunctionDef, ast.AsyncFunctionDef)) and k.name == "git":
            funde.append(f"def git (Z. {k.lineno})")
        if isinstance(k, ast.Call):
            if isinstance(k.func, ast.Name) and k.func.id == "git":
                funde.append(f"git( (Z. {k.lineno})")
            for arg in k.args:
                if isinstance(arg, (ast.List, ast.Tuple)) and any(isinstance(e, ast.Constant) and e.value == "git" for e in arg.elts):
                    funde.append(f'"git" in Argumenten (Z. {k.lineno})')
    for k in baum.body:   # Modulebene: kein Import der Git-Module
        namen = [a.name for a in k.names] if isinstance(k, ast.Import) else [k.module or ""] if isinstance(k, ast.ImportFrom) else []
        funde += [f"import {n} auf Modulebene" for n in namen if n in ("schreiben_git", "stand_git")]
    return funde


def test_schreiben_und_stand_enthalten_kein_git():
    for datei in ("schreiben.py", "stand.py"):
        assert _git_aufrufe_im_quelltext(datei) == [], datei
    quelle = (ENGINE / "stand.py").read_text(encoding="utf-8")
    assert not re.search(r"^\s*(import|from)\s+subprocess\b", quelle, re.M)
    assert re.search(r"^\s+import stand_git\b|^\s+from stand_git import", quelle, re.M)          # nur in Funktionen
    assert re.search(r"^\s+import schreiben_git\b|^\s+from schreiben_git import", (ENGINE / "schreiben.py").read_text(encoding="utf-8"), re.M)
    for datei in ("schreiben_git.py", "stand_git.py"):
        assert (ENGINE / datei).exists(), datei


def test_speicherweg_ruft_nie_git_auf(speicher, monkeypatch, tmp_path):
    import stand
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    marke = tmp_path / "git-gerufen"
    (bin_ / "git").write_text(f"#!/bin/sh\necho \"$@\" >> {marke}\nexit 1\n")
    (bin_ / "git").chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_}{os.pathsep}{os.environ.get('PATH', '')}")
    assert shutil.which("git") == str(bin_ / "git")
    code, a = schreib(speicher, "beispielreise", "art_definieren", {**IDA, "args": ART})              # mit Probebau
    assert code == 200 and a["ok"], a
    code, a = schreib(speicher, "beispielreise", "art_definieren", {**KARL, "args": ART})             # abgelehnt
    assert code == 422, a
    with Dienst(speicher.schreiber()) as d:
        assert d.get("beispielreise/buchung/B-01")[1]["gibt_es"] is True
        assert d.get("gesund", geheim=False) == (200, {"gesund": True})
    ordner = tmp_path / "bau" / "beispielreise"
    speicher.rs.exportieren("beispielreise", ordner)
    s = stand.fuer_seite(ordner, {})
    assert s and s["nummer"] == speicher.rs.stand_nummer("beispielreise")
    assert not marke.exists(), marke.read_text()


# ---------- AC-21: neue Texte in allen Sprachen ----------

NEUE_SCHLUESSEL = ("speicher_nicht_erreichbar", "reise_nicht_im_speicher", "reise_im_speicher", "stand_geaendert")


def test_neue_schluessel_in_allen_sprachen(monkeypatch):
    import texte
    monkeypatch.setenv("FR_TEXTE_ZUSATZ", "xx")   # die Pseudo-Sprache der Tests zählt mit
    sprachen = texte.sprachen()
    assert {"de", "en", "xx"} <= set(sprachen)
    for sp in sprachen:
        for k in NEUE_SCHLUESSEL:
            schluessel = f"schreiben.dienst.{k}"
            assert schluessel in texte.sprache(sp).TEXTE, (sp, schluessel)
            assert texte.t(sp, schluessel).strip() not in ("", schluessel), (sp, schluessel)
    assert len({texte.t("de", f"schreiben.dienst.{k}") for k in NEUE_SCHLUESSEL}) == len(NEUE_SCHLUESSEL)


# ---------- AC-24: Messlauf ----------

@pytest.mark.parametrize("weg", ["speicher", "git"])
def test_messlauf_skript_gibt_kennzahlen_aus(weg, tmp_path):
    skript = WURZEL / "betrieb" / "messlauf-schreibweg.py"
    assert skript.exists()
    env = {k: v for k, v in os.environ.items() if not k.startswith(("FR_", "SB_", "KN_", "RM_"))}
    env["TMPDIR"] = str(tmp_path)
    r = subprocess.run([sys.executable, str(skript), "--weg", weg, "--anzahl", "2"], capture_output=True, text=True,
                       env=env, cwd=tmp_path, timeout=600)
    assert r.returncode == 0, r.stderr[-2000:]
    aus = r.stdout
    for wort in ("nacheinander", "parallel", "Anzahl", "Mittel", "p50", "p90", "p99", "Maximum", "504", "429", "5xx"):
        assert wort in aus, (wort, aus)
    assert re.search(r"Anzahl\D*\d+", aus)


# ---------- AC-25: Doku ----------

def test_doku_nennt_schalter_und_vorbedingungen():
    betrieb = (WURZEL / "docs" / "betrieb.md").read_text(encoding="utf-8")
    for wort in ("FR_SPEICHERREISEN", "Speicherweg", "Stufe 3", "sicherung/"):
        assert wort in betrieb, wort
    assert re.search(r"Nachprüfung[^\n]*(lokal|im Speicher)|(lokal|im Speicher)[^\n]*Nachprüfung", betrieb)
    adr = (WURZEL / "docs" / "adr" / "0009-reisespeicher.md").read_text(encoding="utf-8")
    assert "FR_SPEICHERREISEN" in adr and "Stufe 2" in adr and "schreiben_git" in adr and "Stufe 5" in adr
    zeitgrenzen = (WURZEL / "docs" / "specs" / "betrieb" / "schreibweg-zeitgrenzen.md").read_text(encoding="utf-8")
    assert "Speicherweg" in zeitgrenzen and "#347" in zeitgrenzen
    assert re.search(r"^#?FR_SPEICHERREISEN=", (WURZEL / "betrieb" / "einstellungen.beispiel").read_text(encoding="utf-8"), re.M)
