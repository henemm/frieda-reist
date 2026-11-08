"""Tests für Stufe 4 des Reisespeichers (#349, Epic #345, ADR-0009): Medien in einer Dateiablage nach Prüfsumme.
Spec: docs/specs/betrieb/speicher-349-stufe4.md (AC-1 bis AC-22, AC-25, AC-26 und AC-10/AC-28 für den Katalog).
Ohne Git, alles unter tmp_path; Reisen sind die beiden erfundenen Beispielreisen (stadtwochenende hat keine Medien,
der Test ergänzt erfundene Dateien).

Die Shell-Läufe (AC-23, AC-24) stehen in test_betrieb.py.
RED: Ablage, Spalte ausgelagert, AblageFehlt/AblageFehler, ablage_pfad und die Umstellung gibt es noch nicht.
"""
import hashlib
import os
import re
import shutil
import sqlite3
import subprocess
import sys
from contextlib import closing
from pathlib import Path

import pytest

ENGINE = Path(__file__).resolve().parents[1]
WURZEL = ENGINE.parent
BEISPIEL = WURZEL / "beispiel" / "reisen"
sys.path.insert(0, str(ENGINE))

REISEN = ["beispielreise", "stadtwochenende"]
PNG = b"\x89PNG\r\n\x1a\n" + b"erfundenes Foto " * 50
GPX = b'<?xml version="1.0"?><gpx version="1.1"><trk><trkseg></trkseg></trk></gpx>'

ALT_SCHEMA = """
CREATE TABLE vorgaenge (
  nummer INTEGER PRIMARY KEY AUTOINCREMENT, reise TEXT NOT NULL, stand INTEGER NOT NULL, wann TEXT NOT NULL,
  wer TEXT NOT NULL, rolle TEXT NOT NULL DEFAULT '', werkzeug TEXT NOT NULL, titel TEXT NOT NULL,
  grund TEXT NOT NULL DEFAULT '', kennung TEXT UNIQUE, herkunft TEXT NOT NULL DEFAULT '',
  UNIQUE (reise, stand), UNIQUE (nummer, reise));
CREATE TABLE versionen (
  vorgang INTEGER NOT NULL, reise TEXT NOT NULL, pfad TEXT NOT NULL, inhalt BLOB, pruefsumme TEXT,
  PRIMARY KEY (vorgang, pfad), FOREIGN KEY (vorgang, reise) REFERENCES vorgaenge (nummer, reise));
CREATE TRIGGER versionen_kein_update BEFORE UPDATE ON versionen
  BEGIN SELECT RAISE(ABORT, 'append only: versionen'); END;
"""


@pytest.fixture
def rs(tmp_path, monkeypatch):
    monkeypatch.setenv("FR_SPEICHER", str(tmp_path / "_speicher"))
    import reisespeicher
    return reisespeicher


def _summe(b):
    return hashlib.sha256(b).hexdigest()


def _ablage(tmp_path):
    return tmp_path / "_speicher" / "ablage"


def _ablage_dateien(tmp_path):
    return sorted(p for p in _ablage(tmp_path).rglob("*") if p.is_file())


def _baum(ordner):
    ordner = Path(ordner)
    return {p.relative_to(ordner).as_posix(): p.read_bytes() for p in sorted(ordner.rglob("*"))
            if p.is_file() and ".git" not in p.relative_to(ordner).parts}


def _quelle(tmp_path, reise):
    """Kopie der Beispielreise; stadtwochenende bekommt erfundene Medien (hat selbst keine)."""
    q = tmp_path / "q" / reise
    shutil.copytree(BEISPIEL / reise, q, ignore=shutil.ignore_patterns(".git"))
    if reise == "stadtwochenende":
        (q / "medien").mkdir(exist_ok=True)
        (q / "medien" / "foto.png").write_bytes(PNG)
        (q / "medien" / "strecke.gpx").write_bytes(GPX)
    return q


def _importiert(rs, tmp_path, reise):
    q = _quelle(tmp_path, reise)
    rs.importieren(q, reise, "Test", grund="Anfang")
    return q


def _zeilen(rs, reise):
    with closing(sqlite3.connect(rs.pfad())) as v:
        return v.execute("SELECT pfad, inhalt, pruefsumme, ausgelagert FROM versionen WHERE reise = ? "
                         "ORDER BY vorgang, pfad", (reise,)).fetchall()


def _alt_speicher(rs, tmp_path, reise):
    """Speicher im Format der Stufe 3: user_version 1, keine Spalte, Medien als BLOB. -> Quellordner."""
    q = _quelle(tmp_path, reise)
    p = rs.pfad()
    p.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(p)) as v:
        v.executescript(ALT_SCHEMA)
        v.execute("INSERT INTO vorgaenge (nummer, reise, stand, wann, wer, werkzeug, titel) "
                  "VALUES (1, ?, 1, '2026-11-01T10:00:00+00:00', 'Test', 'test', 'Anfang')", (reise,))
        for f in sorted(q.rglob("*")):
            if f.is_file():
                b = f.read_bytes()
                v.execute("INSERT INTO versionen VALUES (1, ?, ?, ?, ?)",
                          (reise, f.relative_to(q).as_posix(), b, _summe(b)))
        v.execute("PRAGMA user_version = 1")
        v.commit()
    return q


def _cli(rs, *a):
    p = subprocess.run([sys.executable, str(ENGINE / "reisespeicher.py"), *a], capture_output=True, text=True,
                       env={**os.environ, "FR_SPEICHER": os.environ["FR_SPEICHER"]})
    return p.returncode, p.stdout


def _weg(rs, summe):
    """Ablagedatei entfernen (nur der Test; die Software löscht nie)."""
    f = rs.ablage_pfad(summe)
    os.chmod(f.parent, 0o700)
    f.unlink()


# ---------- AC-1 ----------

def test_schema_wird_auf_version_2_gehoben(rs, tmp_path):
    _alt_speicher(rs, tmp_path, "beispielreise")
    with closing(sqlite3.connect(rs.pfad())) as v:
        vorher = [tuple(z) for z in v.execute("SELECT pfad, inhalt, pruefsumme FROM versionen ORDER BY pfad")]
    for _ in range(2):   # zweites Öffnen ändert nichts
        with closing(rs.db()) as v:
            assert v.execute("PRAGMA user_version").fetchone()[0] == 2
            spalten = {z[1]: z for z in v.execute("PRAGMA table_info(versionen)")}
            assert "ausgelagert" in spalten and spalten["ausgelagert"][4] == "0"
            nachher = [tuple(z) for z in v.execute("SELECT pfad, inhalt, pruefsumme FROM versionen ORDER BY pfad")]
            assert nachher == vorher
            assert v.execute("SELECT COUNT(*) FROM versionen WHERE ausgelagert != 0").fetchone()[0] == 0
            with pytest.raises(sqlite3.DatabaseError):
                v.execute("UPDATE versionen SET pruefsumme = 'x'")


# ---------- AC-2, AC-3, AC-4 ----------

def test_nur_medien_mit_endung_werden_ausgelagert(rs):
    dateien = {"medien/a.png": PNG + b"a", "medien/b.JPG": PNG + b"b", "medien/c.gpx": GPX,
               "medien/d.pmtiles": b"pm" * 20, "medien/icon.svg": b"<svg/>", "medien/icon.png": PNG + b"i",
               "reise.yaml": b"name: x\n", "plan/x.md": b"# x\n", "bilder/e.png": PNG + b"e"}
    rs.vorgang_schreiben("t", dateien, "Test", "test", "Anfang")
    z = {r[0]: r for r in _zeilen(rs, "t")}
    for p in ("medien/a.png", "medien/b.JPG", "medien/c.gpx", "medien/d.pmtiles"):
        assert z[p][3] == 1 and z[p][1] is None and z[p][2] == _summe(dateien[p]), p
    for p in ("medien/icon.svg", "medien/icon.png", "reise.yaml", "plan/x.md", "bilder/e.png"):
        assert z[p][3] == 0 and bytes(z[p][1]) == dateien[p], p
    assert {"png", "jpg", "jpeg", "webp", "gif", "gpx", "pmtiles"} <= set(rs.AUSLAGERN)


def test_ablage_ort_name_und_rechte(rs, tmp_path):
    rs.vorgang_schreiben("t", {"medien/a.png": PNG}, "Test", "test", "Anfang")
    s = _summe(PNG)
    f = _ablage(tmp_path) / s[:2] / s
    assert f.read_bytes() == PNG and f.stat().st_mode & 0o777 == 0o400
    assert (_ablage(tmp_path) / s[:2]).stat().st_mode & 0o777 == 0o700
    assert _zeilen(rs, "t")[0][1] is None
    assert rs.ablage_pfad(s) == f


def test_doppelte_liegen_nur_einmal_in_der_ablage(rs, tmp_path):
    rs.vorgang_schreiben("t", {"medien/a.png": PNG, "medien/b.png": PNG}, "Test", "test", "Anfang")
    rs.vorgang_schreiben("t", {"medien/a.png": PNG + b"x"}, "Test", "test", "geändert")
    rs.vorgang_schreiben("t", {"medien/a.png": PNG}, "Test", "test", "zurück")
    rs.vorgang_schreiben("u", {"medien/z.png": PNG}, "Test", "test", "andere Reise")
    assert len([p for p in _ablage_dateien(tmp_path) if p.name == _summe(PNG)]) == 1
    assert len(_ablage_dateien(tmp_path)) == 2   # PNG und PNG+x
    assert {r[2] for r in _zeilen(rs, "u")} == {_summe(PNG)}


# ---------- AC-5, AC-6 ----------

@pytest.mark.parametrize("reise", REISEN)
def test_export_und_materialisieren_byte_gleich_beide_reisen(rs, tmp_path, reise):
    q = _importiert(rs, tmp_path, reise)
    assert any(r[3] == 1 for r in _zeilen(rs, reise))
    rs.exportieren(reise, tmp_path / "ex")
    assert _baum(tmp_path / "ex") == _baum(q)
    rs.materialisieren(reise, tmp_path / "mat")
    assert _baum(tmp_path / "mat") == _baum(q)
    if reise == "beispielreise":
        assert (tmp_path / "mat" / "medien" / "skizze-felsen.png").exists()
        assert len(list((tmp_path / "mat" / "medien").rglob("*.gpx"))) == 4


def test_materialisieren_hardlink_und_kopie_rueckfall(rs, tmp_path, monkeypatch):
    rs.vorgang_schreiben("t", {"medien/a.png": PNG}, "Test", "test", "Anfang")
    rs.materialisieren("t", tmp_path / "m1")
    assert os.stat(tmp_path / "m1" / "medien" / "a.png").st_ino == rs.ablage_pfad(_summe(PNG)).stat().st_ino

    def kein_link(*a, **k):
        raise OSError("anderes Dateisystem")
    monkeypatch.setattr(os, "link", kein_link)
    rs.materialisieren("t", tmp_path / "m2")
    k = tmp_path / "m2" / "medien" / "a.png"
    assert k.read_bytes() == PNG and k.stat().st_ino != rs.ablage_pfad(_summe(PNG)).stat().st_ino


# ---------- AC-7, AC-8 ----------

def test_datei_wird_vor_der_datenbank_abgelegt(rs, tmp_path):
    rs.vorgang_schreiben("t", {"reise.yaml": b"a\n"}, "Test", "test", "Anfang")
    with pytest.raises(rs.StandGeaendert):
        rs.vorgang_schreiben("t", {"medien/a.png": PNG}, "Test", "test", "zu spät", erwartet=99)
    assert [r for r in _zeilen(rs, "t") if r[0] == "medien/a.png"] == []
    assert rs.ablage_pfad(_summe(PNG)).is_file()   # Datei zuerst, Zeile nie: verwaist, aber harmlos
    rs.vorgang_schreiben("t", {"medien/b.png": PNG + b"b"}, "Test", "test", "gut")
    for r in _zeilen(rs, "t"):
        if r[3] == 1:
            assert rs.ablage_pfad(r[2]).is_file()


def test_ablage_nicht_beschreibbar_schreibt_nichts(rs, tmp_path):
    rs.vorgang_schreiben("t", {"reise.yaml": b"a\n"}, "Test", "test", "Anfang")
    _ablage(tmp_path).mkdir(parents=True, exist_ok=True)
    os.chmod(_ablage(tmp_path), 0o500)
    try:
        if os.access(_ablage(tmp_path), os.W_OK):
            pytest.skip("läuft als Benutzer, der Modi ignoriert")
        n = rs.stand_nummer("t")
        with pytest.raises(OSError):
            rs.vorgang_schreiben("t", {"medien/a.png": PNG}, "Test", "test", "x")
        assert rs.stand_nummer("t") == n
    finally:
        os.chmod(_ablage(tmp_path), 0o700)


def test_ablage_wird_nie_geaendert_oder_geloescht(rs, tmp_path):
    rs.vorgang_schreiben("t", {"medien/a.png": PNG}, "Test", "test", "Anfang")
    alt = rs.ablage_pfad(_summe(PNG))
    mtime = alt.stat().st_mtime_ns
    rs.vorgang_schreiben("t", {"medien/a.png": PNG + b"neu"}, "Test", "test", "ersetzt")
    rs.vorgang_schreiben("t", {"medien/a.png": None}, "Test", "test", "gelöscht")
    assert alt.read_bytes() == PNG and alt.stat().st_mtime_ns == mtime
    rs.zuruecksetzen("t", 1, "Test", "zurück")
    assert rs.datei("t", "medien/a.png") == PNG
    quelle = (ENGINE / "reisespeicher.py").read_text(encoding="utf-8")
    assert "rmtree" not in quelle and not re.search(r"ablage_pfad\([^)]*\)\.unlink|os\.(remove|unlink)\(ablage", quelle)


# ---------- AC-9 bis AC-13 ----------

def test_fehlende_ablagedatei_bricht_export_ohne_halben_ordner(rs, tmp_path):
    rs.vorgang_schreiben("t", {"reise.yaml": b"a\n", "medien/a.png": PNG, "medien/b.png": PNG + b"b"}, "T", "t", "A")
    _weg(rs, _summe(PNG + b"b"))
    with pytest.raises(rs.AblageFehlt) as e:
        rs.exportieren("t", tmp_path / "ziel")
    assert _summe(PNG + b"b") in str(e.value) and "medien/b.png" in str(e.value)
    assert not (tmp_path / "ziel").exists()
    (tmp_path / "bau").mkdir()
    (tmp_path / "bau" / "alt.txt").write_text("bleibt")
    with pytest.raises(rs.AblageFehlt):
        rs.materialisieren("t", tmp_path / "bau")
    assert (tmp_path / "bau" / "alt.txt").read_text() == "bleibt"
    assert not Path(str(tmp_path / "bau") + ".neu").exists()


def _sprachen():
    import texte
    return list(texte.SPRACHEN)


@pytest.mark.parametrize("kuerzel", _sprachen())
def test_fehlende_datei_bricht_den_bau_mit_katalogtext_in_allen_sprachen_ab(kuerzel):
    """pruefung.bauen.79/.80 stehen in jeder Sprache; die Platzhalter {w1}, {ziel}, {summe} werden ersetzt."""
    import texte
    mod = texte.sprache(kuerzel)
    for schluessel in ("pruefung.bauen.79", "pruefung.bauen.80"):
        assert schluessel in mod.TEXTE, (kuerzel, schluessel)
        assert "{w1}" in mod.TEXTE[schluessel] and "{ziel}" in mod.TEXTE[schluessel]
    assert "{summe}" in mod.TEXTE["pruefung.bauen.79"]
    s = str(texte.satz("pruefung.bauen.79", w1="reise-a", ziel="medien/a.png", summe="ab" * 32))
    assert "reise-a" in s and "medien/a.png" in s and "ab" * 32 in s and "{" not in s


@pytest.mark.parametrize("art", ["fehlt", "beschaedigt"])
@pytest.mark.parametrize("kuerzel", _sprachen())
def test_materialisieren_meldet_ablagefehler_mit_katalogtext_und_exit_2(rs, tmp_path, capsys, kuerzel, art):
    """AC-10/AC-11 zur Laufzeit: Der Befehl materialisieren (Bau aus dem Speicher in veroeffentlichen.sh) endet bei einer
    fehlenden oder beschädigten Ablagedatei mit Exit 2 und pruefung.bauen.79/.80 in der Sprache des Aufrufs, als Zeile
    „ - …“ (so liest veroeffentlichen.sh einen roten Bau); kein Ordner entsteht."""
    import texte
    rs.vorgang_schreiben("t", {"reise.yaml": b"a\n", "medien/a.png": PNG}, "T", "t", "A")
    s = _summe(PNG)
    if art == "fehlt":
        _weg(rs, s)
    else:
        f = rs.ablage_pfad(s)
        os.chmod(f, 0o600)
        f.write_bytes(b"kaputt")
    schluessel = "pruefung.bauen.79" if art == "fehlt" else "pruefung.bauen.80"
    erwartet = texte.t(kuerzel, schluessel, w1="t", ziel="medien/a.png", summe=s)
    texte.aufruf_sprache(kuerzel)
    try:
        code = rs.main(["materialisieren", "t", str(tmp_path / "bau")])
    finally:
        texte.aufruf_sprache(texte.VORGABE_REISE)
    aus = capsys.readouterr().out
    assert code == 2 and f" - {erwartet}" in aus.splitlines(), aus
    assert "{" not in aus and "medien/a.png" in aus and (s in aus or art != "fehlt")
    assert not (tmp_path / "bau").exists()


def test_bau_uebersetzt_ablagefehler_in_katalogtext(rs):
    """bauen.ablage_meldung(fehler, w1) macht aus AblageFehlt/AblageFehler den Satz pruefung.bauen.79/.80;
    der Speicher-Bau von bauen.py endet damit mit Exit 2 (AC-10)."""
    import bauen
    s = _summe(PNG)
    assert bauen.ablage_meldung(rs.AblageFehlt("medien/a.png", s), "t").schluessel == "pruefung.bauen.79"
    assert bauen.ablage_meldung(rs.AblageFehler("medien/a.png", s), "t").schluessel == "pruefung.bauen.80"


def test_beschaedigte_ablagedatei_wird_erkannt_und_nicht_repariert(rs, tmp_path):
    rs.vorgang_schreiben("t", {"medien/a.png": PNG}, "T", "t", "A")
    f = rs.ablage_pfad(_summe(PNG))
    os.chmod(f, 0o600)
    f.write_bytes(PNG[:-1] + b"X")
    os.chmod(f, 0o400)
    kaputt = f.read_bytes()
    with pytest.raises(rs.AblageFehler):
        rs.datei("t", "medien/a.png")
    with pytest.raises(rs.AblageFehler):
        rs.aktueller_stand("t")
    with pytest.raises(rs.AblageFehler):
        rs.exportieren("t", tmp_path / "ex")
    assert not (tmp_path / "ex").exists()
    assert any("store checksum mismatch" in x for x in rs.pruefen())
    assert f.read_bytes() == kaputt


def test_vorhandene_ablagedatei_mit_falschem_inhalt_wird_nicht_ueberschrieben(rs, tmp_path):
    s = _summe(PNG)
    ziel = _ablage(tmp_path) / s[:2] / s
    ziel.parent.mkdir(parents=True)
    ziel.write_bytes(b"zu kurz")
    with pytest.raises(rs.AblageFehler):
        rs.vorgang_schreiben("t", {"medien/a.png": PNG}, "T", "t", "A")
    assert ziel.read_bytes() == b"zu kurz"
    assert "t" not in rs.reisen()


def test_ablage_pfad_nur_aus_summe_und_symlink_abgewiesen(rs, tmp_path):
    for schlecht in ("../x", "abc", _summe(b"x").upper(), _summe(b"x") + "0", ""):
        with pytest.raises(ValueError):
            rs.ablage_pfad(schlecht)
    rs.vorgang_schreiben("t", {"medien/a.png": PNG}, "T", "t", "A")
    f = rs.ablage_pfad(_summe(PNG))
    echt = tmp_path / "echt.png"
    echt.write_bytes(PNG)
    _weg(rs, _summe(PNG))
    f.symlink_to(echt)
    with pytest.raises((rs.AblageFehler, rs.AblageFehlt)):
        rs.datei("t", "medien/a.png")
    with pytest.raises((rs.AblageFehler, rs.AblageFehlt)):
        rs.exportieren("t", tmp_path / "ex")
    with pytest.raises(ValueError):
        rs.vorgang_schreiben("u", {"medien/../../x.png": PNG}, "T", "t", "A")
    assert "u" not in rs.reisen()


# ---------- AC-14, AC-15 ----------

def test_vergleichen_braucht_keine_ablagedatei(rs, tmp_path, monkeypatch):
    q = _importiert(rs, tmp_path, "beispielreise")
    assert any(r[3] == 1 for r in _zeilen(rs, "beispielreise"))

    def falle(*a, **k):
        raise AssertionError("Ablagezugriff")
    monkeypatch.setattr(rs, "ablage_lesen", falle)
    monkeypatch.setattr(os, "link", falle)
    assert not rs.vergleichen("beispielreise", q)   # leere Liste: gleich
    rs.stand_nummer("beispielreise")


def test_verweis_zaehlt_nicht_als_tombstone(rs):
    rs.vorgang_schreiben("t", {"medien/a.png": PNG, "medien/b.png": PNG + b"b"}, "T", "t", "A")
    rs.vorgang_schreiben("t", {"medien/b.png": None}, "T", "t", "weg")
    assert [r for r in _zeilen(rs, "t") if r[0] == "medien/a.png"][0][3] == 1   # Verweis: inhalt NULL, Summe gesetzt
    with closing(rs.db()) as v:
        st = rs._stand(v, "t", spalte="pruefsumme")
    assert "medien/a.png" in st and "medien/b.png" not in st


# ---------- AC-16 bis AC-19 ----------

def _roh(rs, sql, *werte):
    """Zeile an Trigger und Authorizer vorbei (nur im Test; eigene Verbindung ohne Authorizer)."""
    with closing(sqlite3.connect(rs.pfad())) as v:
        v.execute(sql, werte)
        v.commit()


def test_pruefen_prueft_die_ablage(rs, tmp_path):
    rs.vorgang_schreiben("t", {"medien/a.png": PNG, "medien/b.png": PNG + b"b", "reise.yaml": b"a\n"}, "T", "t", "A")
    assert rs.pruefen() == []
    _weg(rs, _summe(PNG))
    f = rs.ablage_pfad(_summe(PNG + b"b"))
    os.chmod(f, 0o600)
    f.write_bytes(b"kaputt")
    _roh(rs, "INSERT INTO vorgaenge (nummer, reise, stand, wann, wer, werkzeug, titel) "
             "VALUES (50, 't', 50, 'x', 'T', 't', 'roh')")
    _roh(rs, "INSERT INTO versionen (vorgang, reise, pfad, inhalt, pruefsumme, ausgelagert) "
             "VALUES (50, 't', 'medien/c.png', x'00', ?, 1)", _summe(b"\x00"))
    _roh(rs, "INSERT INTO versionen (vorgang, reise, pfad, inhalt, pruefsumme, ausgelagert) "
             "VALUES (50, 't', 'medien/d.png', NULL, NULL, 1)")
    funde = "\n".join(rs.pruefen())
    assert "t medien/a.png (operation 1): file missing in store" in funde
    assert "t medien/b.png (operation 1): store checksum mismatch" in funde
    assert "medien/c.png (operation 50)" in funde and "medien/d.png (operation 50)" in funde


def test_zustand_meldet_fehlende_ablagedateien(rs):
    rs.vorgang_schreiben("t", {"medien/a.png": PNG}, "T", "t", "A")
    _, aus = _cli(rs, "zustand")
    assert "ablage_fehlt 0" in aus
    _weg(rs, _summe(PNG))
    n = rs.stand_nummer("t")
    code, aus = _cli(rs, "zustand")
    assert "ablage_fehlt 1" in aus and code == 1 and rs.stand_nummer("t") == n


def test_sichern_verlangt_vollstaendige_ablage(rs):
    rs.vorgang_schreiben("t", {"medien/a.png": PNG}, "T", "t", "A")
    gut = rs.sichern()
    with closing(sqlite3.connect(gut)) as v:
        assert v.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    vorher = gut.read_bytes()
    rs.vorgang_schreiben("t", {"medien/b.png": PNG + b"b"}, "T", "t", "B")
    _weg(rs, _summe(PNG + b"b"))
    with pytest.raises(Exception):
        rs.sichern()
    assert gut.read_bytes() == vorher
    assert _cli(rs, "sichern")[0] != 0


def test_wiederherstellung_aus_schnappschuss_und_ablage(rs, tmp_path, monkeypatch):
    q = _importiert(rs, tmp_path, "beispielreise")
    snap = rs.sichern()
    neu = tmp_path / "wieder"
    neu.mkdir()
    shutil.copy(snap, neu / "reisen.db")
    shutil.copytree(_ablage(tmp_path), neu / "ablage")
    monkeypatch.setenv("FR_SPEICHER", str(neu))
    assert rs.pruefen() == []
    assert not rs.vergleichen("beispielreise", q)
    rs.materialisieren("beispielreise", tmp_path / "mat")
    assert _baum(tmp_path / "mat") == _baum(q)
    for d in (neu / "ablage").iterdir():
        os.chmod(d, 0o700)
    shutil.rmtree(neu / "ablage")
    assert any("file missing in store" in x for x in rs.pruefen())   # Sicherung ohne Ablage ist wertlos


# ---------- AC-20 bis AC-22 ----------

@pytest.mark.parametrize("reise", REISEN)
def test_nachziehen_speicher_lagert_bestehende_medien_aus(rs, tmp_path, reise):
    import neu
    q = _alt_speicher(rs, tmp_path, reise)
    code, ausgabe = neu.nachziehen_speicher(reise, tmp_path / "bau" / reise)
    assert code == 0, ausgabe
    with closing(rs.db()) as v:
        vorgaenge = [tuple(x) for x in v.execute(
            "SELECT wer, werkzeug, titel FROM vorgaenge WHERE titel = 'ablage-umstellung'")]
    assert vorgaenge == [("Software-Nachziehen", "nachziehen", "ablage-umstellung")]
    medien = [r for r in _zeilen(rs, reise) if r[3] == 1]
    assert medien and all(rs.ablage_pfad(r[2]).is_file() for r in medien)
    rs.exportieren(reise, tmp_path / "ex")
    # Byte-gleich mit dem Stand davor, nicht mit dem Quellordner: Der Formatvorgang der Stufe 3 davor stellt in der
    # beispielreise plan/arten.yaml um (bestehendes Verhalten von neu.py nachziehen, unabhängig von Stufe 4).
    n = rs.stand_nummer(reise)
    with closing(rs.db()) as v:
        assert v.execute("SELECT titel FROM vorgaenge WHERE reise = ? AND stand = ?", (reise, n)).fetchone()[0] \
            == "ablage-umstellung"
    rs.exportieren(reise, tmp_path / "davor", bis=n - 1)
    assert _baum(tmp_path / "ex") == _baum(tmp_path / "davor")
    assert {p: b for p, b in _baum(tmp_path / "ex").items() if p.startswith("medien/")} == \
        {p: b for p, b in _baum(q).items() if p.startswith("medien/")}
    _weg(rs, medien[0][2])   # alle Wege lesen aus der Ablage, nicht mehr aus dem alten BLOB
    with pytest.raises(rs.AblageFehlt):
        rs.exportieren(reise, tmp_path / "ex2")


@pytest.mark.parametrize("reise", REISEN)
def test_nachziehen_speicher_ablage_ist_idempotent(rs, tmp_path, reise):
    import neu
    _alt_speicher(rs, tmp_path, reise)
    neu.nachziehen_speicher(reise, tmp_path / "bau" / reise)
    n = rs.stand_nummer(reise)
    code, ausgabe = neu.nachziehen_speicher(reise, tmp_path / "bau" / reise)
    assert code == 0 and "nichts umzustellen" in " ".join(ausgabe) and rs.stand_nummer(reise) == n


def test_nachziehen_speicher_ohne_medien_erzeugt_keinen_vorgang(rs, tmp_path):
    import neu
    q = tmp_path / "q"
    shutil.copytree(BEISPIEL / "stadtwochenende", q, ignore=shutil.ignore_patterns(".git"))
    shutil.rmtree(q / "medien", ignore_errors=True)
    rs.importieren(q, "stadtwochenende", "Test", grund="Anfang")
    n = rs.stand_nummer("stadtwochenende")
    neu.nachziehen_speicher("stadtwochenende", tmp_path / "bau")
    assert rs.stand_nummer("stadtwochenende") == n and not _ablage(tmp_path).exists()


def test_nachziehen_speicher_ablage_wiederholt_bei_wettlauf(rs, tmp_path, monkeypatch):
    import neu
    _alt_speicher(rs, tmp_path, "beispielreise")
    aufrufe = []

    def wettlauf(*a, **k):
        aufrufe.append(1)
        raise rs.StandGeaendert(1, 2)
    monkeypatch.setattr(rs, "auslagern", wettlauf)
    code, _ = neu.nachziehen_speicher("beispielreise", tmp_path / "bau")
    assert code == 1 and len(aufrufe) == 3
    assert not [r for r in _zeilen(rs, "beispielreise") if r[3] == 1]


# ---------- AC-25, AC-26 ----------

def test_schreibweg_track_in_ablage_symbol_in_datenbank(rs, tmp_path):
    rs.vorgang_schreiben("t", {"reise.yaml": b"a\n"}, "T", "t", "A")
    rs.vorgang_schreiben("t", {"medien/gpx/E-01.gpx": GPX, "medien/icon.png": PNG}, "T", "schreibweg", "Track")
    z = {r[0]: r for r in _zeilen(rs, "t")}
    assert z["medien/gpx/E-01.gpx"][3] == 1 and rs.ablage_pfad(_summe(GPX)).is_file()
    assert z["medien/icon.png"][3] == 0 and bytes(z["medien/icon.png"][1]) == PNG
    rs.materialisieren("t", tmp_path / "m")
    assert (tmp_path / "m" / "medien" / "gpx" / "E-01.gpx").read_bytes() == GPX


def test_ohne_speicherreisen_entsteht_keine_ablage(rs, tmp_path, monkeypatch):
    import instanz
    monkeypatch.setenv("FR_SPEICHERREISEN", "")
    assert instanz.speicher_ablage() == instanz.speicher() / "ablage"
    rs.vorgang_schreiben("t", {"reise.yaml": b"a\n", "medien/icon.svg": b"<svg/>"}, "T", "t", "A")
    assert not _ablage(tmp_path).exists()
