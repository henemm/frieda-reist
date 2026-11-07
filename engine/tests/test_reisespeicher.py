"""Tests für engine/reisespeicher.py (Reisespeicher Stufe 1, #346, Epic #345, ADR-0009): Reisedaten als unveränderliche
Versionen in SQLite, nur anhängen. Ohne Git, alles unter tmp_path; die Reisen sind die beiden erfundenen Beispielreisen
oder erfundene Testdaten.

Das Modul wird je Test im Fixture `rs` geladen (nicht oben in der Datei): Fehlt es, scheitert jeder Test einzeln.

Befehle von main (diese Tests legen die Form fest, positionell wie in konten.py):
  importieren <ordner> <reise> <wer> [--grund TEXT] [--ab N]     Ausgabe: "stand N"
  exportieren <reise> <ziel> [--bis N]
  verlauf <reise> [n]                                            je Vorgang eine Zeile, neueste zuerst, beginnt mit dem Stand
  zuruecksetzen <reise> <bis> <wer> <grund>                      Ausgabe: "stand N"
  pruefen [reise]                                                in Ordnung: "ok", Exitcode 0; sonst je Abweichung eine Zeile
  sichern                                                        Ausgabe: Pfad des Schnappschusses
Exitcode 0 bei Erfolg, 1 bei unbekanntem Befehl (mit Hilfe, „Aufrufe:“), sonst ungleich 0 bei Fehler oder Abweichung.
"""
import os
import re
import shutil
import sqlite3
import stat
import sys
from contextlib import closing
from pathlib import Path

import pytest

ENGINE = Path(__file__).resolve().parents[1]
WURZEL = ENGINE.parent
BEISPIEL = WURZEL / "beispiel" / "reisen"
sys.path.insert(0, str(ENGINE))


@pytest.fixture
def rs(tmp_path, monkeypatch):
    monkeypatch.setenv("FR_SPEICHER", str(tmp_path / "_speicher"))
    import reisespeicher
    return reisespeicher


def _baum(ordner):
    """Pfad (POSIX, relativ) -> Bytes aller regulären Dateien, ohne .git."""
    ordner = Path(ordner)
    return {p.relative_to(ordner).as_posix(): p.read_bytes() for p in sorted(ordner.rglob("*"))
            if p.is_file() and ".git" not in p.relative_to(ordner).parts}


def _ordner(wurzel, dateien):
    wurzel = Path(wurzel)
    for pfad, inhalt in dateien.items():
        (wurzel / pfad).parent.mkdir(parents=True, exist_ok=True)
        (wurzel / pfad).write_bytes(inhalt)
    return wurzel


def _roh(rs):
    """Verbindung an db() vorbei: ohne Authorizer, mit rekursiven Triggern (wie jemand, der die Datei selbst öffnet)."""
    v = sqlite3.connect(rs.pfad())
    v.execute("PRAGMA recursive_triggers = ON")
    return v


def _inhalt_der_tabellen(rs):
    with closing(sqlite3.connect(rs.pfad())) as v:
        return ([tuple(z) for z in v.execute("SELECT * FROM vorgaenge ORDER BY nummer")],
                [tuple(z) for z in v.execute("SELECT * FROM versionen ORDER BY vorgang, pfad")])


def _schreiben(rs, reise, dateien, **weiter):
    werte = {"wer": "Ida", "werkzeug": "item_update", "titel": "Beispieländerung", **weiter}
    return rs.vorgang_schreiben(reise, dateien, **werte)


A1, A2, B1, B2, C1 = b"a: 1\n", b"a: 2\n", b"b: 1\n", b"b: 2\n", b"c: 1\n"


@pytest.fixture
def drei(rs, tmp_path):
    """Erfundene Reise: Stand 1 Import (a, b), Stand 2 a geändert, Stand 3 b gelöscht, Stand 4 b kehrt wieder."""
    quelle = _ordner(tmp_path / "quelle" / "probe", {"reise.yaml": b"titel: Probe\n", "plan/a.md": A1, "inhalt/b.md": B1})
    s = [rs.importieren(quelle, "probe", wer="Ida")]
    s.append(_schreiben(rs, "probe", {"plan/a.md": A2}))
    s.append(_schreiben(rs, "probe", {"inhalt/b.md": None}, werkzeug="item_delete", titel="b weg"))
    s.append(_schreiben(rs, "probe", {"inhalt/b.md": B2}))
    return s


# ---------- Test 1: Import und Export Byte-gleich (AC-1) ----------

@pytest.mark.parametrize("reise", ["beispielreise", "stadtwochenende"])
def test_beispielreise_geht_byte_gleich_durch_import_und_export(rs, tmp_path, reise):
    v = rs.importieren(BEISPIEL / reise, reise, wer="Ida", grund="Probe")
    assert v.stand == 1 and rs.stand_nummer(reise) == 1
    rs.exportieren(reise, tmp_path / "aus")
    assert _baum(tmp_path / "aus") == _baum(BEISPIEL / reise)
    assert rs.aktueller_stand(reise) == _baum(BEISPIEL / reise)
    eintrag = rs.verlauf(reise)[0]
    assert eintrag["werkzeug"] == "importieren" and eintrag["wer"] == "Ida" and eintrag["grund"] == "Probe"
    with closing(sqlite3.connect(rs.pfad())) as roh:
        assert roh.execute("SELECT herkunft FROM vorgaenge").fetchone()[0] == f"import:{reise}"


def test_import_nimmt_versteckte_und_binaere_dateien_ohne_git_und_leere_ordner(rs, tmp_path):
    """Byte-gleich heißt gleiche Pfadmenge und gleiche Bytes: kein Umwandeln von Zeilenenden, versteckte Dateien zählen,
    .git und leere Ordner nicht (ADR-0009)."""
    quelle = _ordner(tmp_path / "probe", {"reise.yaml": b"titel: Probe\r\n", "medien/.gitkeep": b"",
                                          "medien/bild.bin": bytes(range(256)) + b"\r\n\x00", "reise.json": b"{}",
                                          ".git/HEAD": b"ref: refs/heads/main\n"})
    (quelle / "leer").mkdir()
    rs.importieren(quelle, "probe", wer="Ida")
    rs.exportieren("probe", tmp_path / "aus")
    erwartet = _baum(quelle)
    assert ".git/HEAD" not in erwartet and "medien/.gitkeep" in erwartet
    assert _baum(tmp_path / "aus") == erwartet
    assert not (tmp_path / "aus" / ".git").exists() and not (tmp_path / "aus" / "leer").exists()


def test_export_rechte_und_leeres_ziel(rs, tmp_path):
    rs.importieren(_ordner(tmp_path / "probe", {"plan/a.md": A1}), "probe", wer="Ida")
    (tmp_path / "leer").mkdir()
    rs.exportieren("probe", tmp_path / "leer")                       # leerer Ordner ist erlaubt
    assert stat.S_IMODE((tmp_path / "leer" / "plan" / "a.md").stat().st_mode) == 0o644
    assert stat.S_IMODE((tmp_path / "leer" / "plan").stat().st_mode) == 0o755


def test_erneuter_import_wirkt_wie_ein_vorgang(rs, tmp_path):
    quelle = _ordner(tmp_path / "probe", {"plan/a.md": A1, "inhalt/b.md": B1})
    rs.importieren(quelle, "probe", wer="Ida")
    (quelle / "inhalt" / "b.md").unlink()
    (quelle / "plan" / "a.md").write_bytes(A2)
    v = rs.importieren(quelle, "probe", wer="Karl")
    assert v.stand == 2 and rs.aktueller_stand("probe") == {"plan/a.md": A2}
    assert sorted(rs.verlauf("probe")[0]["dateien"]) == ["inhalt/b.md", "plan/a.md"]
    with pytest.raises(ValueError):                                   # nichts geändert: kein Vorgang
        rs.importieren(quelle, "probe", wer="Karl")
    assert rs.stand_nummer("probe") == 2


# ---------- Test 2: alter Stand mit Löschung und Wiederkehr (AC-2) ----------

def test_export_eines_alten_stands(rs, tmp_path, drei):
    assert [v.stand for v in drei] == [1, 2, 3, 4]
    basis = {"reise.yaml": b"titel: Probe\n"}
    erwartet = {1: {**basis, "plan/a.md": A1, "inhalt/b.md": B1}, 2: {**basis, "plan/a.md": A2, "inhalt/b.md": B1},
                3: {**basis, "plan/a.md": A2}, 4: {**basis, "plan/a.md": A2, "inhalt/b.md": B2}}
    for s, inhalt in erwartet.items():
        rs.exportieren("probe", tmp_path / f"stand{s}", bis=s)
        assert _baum(tmp_path / f"stand{s}") == inhalt, f"Stand {s}"
        assert rs.aktueller_stand("probe", bis=s) == inhalt
    assert rs.aktueller_stand("probe") == erwartet[4]
    with pytest.raises(KeyError):
        rs.aktueller_stand("probe", bis=99)
    with pytest.raises(KeyError):
        rs.aktueller_stand("gibtsnicht")
    with pytest.raises(KeyError):
        rs.exportieren("gibtsnicht", tmp_path / "nichts")
    assert not (tmp_path / "nichts").exists() or not any((tmp_path / "nichts").iterdir())


def test_tombstone_hat_weder_inhalt_noch_pruefsumme(rs, drei):
    with closing(sqlite3.connect(rs.pfad())) as v:
        z = v.execute("SELECT inhalt, pruefsumme FROM versionen WHERE vorgang = ? AND pfad = 'inhalt/b.md'",
                      (drei[2].nummer,)).fetchone()
    assert z == (None, None)


# ---------- Test 3: nur anhängen (AC-3) ----------

def test_verlauf_laesst_sich_ueber_db_weder_aendern_noch_loeschen(rs, drei):
    vorher = _inhalt_der_tabellen(rs)
    v = rs.db()
    trigger = [z[0] for z in v.execute("SELECT name FROM sqlite_master WHERE type = 'trigger'")]
    assert len(trigger) >= 4                                          # UPDATE und DELETE auf beiden Tabellen
    anweisungen = [
        "UPDATE vorgaenge SET titel = 'anders'",
        "DELETE FROM vorgaenge",
        "UPDATE versionen SET inhalt = x'00'",
        "DELETE FROM versionen",
        f"INSERT OR REPLACE INTO versionen (vorgang, reise, pfad, inhalt, pruefsumme) "
        f"VALUES ({drei[0].nummer}, 'probe', 'plan/a.md', x'00', '00')",
        "INSERT OR REPLACE INTO vorgaenge (nummer, reise, stand, wann, wer, werkzeug, titel) "
        f"VALUES ({drei[0].nummer}, 'probe', 1, '2026-01-01T00:00:00Z', 'x', 'x', 'x')",
        "DROP TABLE versionen",
        "DROP TABLE vorgaenge",
        "ALTER TABLE vorgaenge ADD COLUMN extra TEXT",
        "PRAGMA writable_schema = ON",
    ] + [f"DROP TRIGGER {t}" for t in trigger]
    for a in anweisungen:
        with pytest.raises(sqlite3.DatabaseError):
            v.execute(a)
            v.commit()
        v.rollback()
    v.close()
    assert _inhalt_der_tabellen(rs) == vorher


def test_trigger_schuetzen_auch_ohne_authorizer(rs, drei):
    """Zweite Schicht: Wer an db() vorbei schreibt (Software-Fehler mit eigener Verbindung), scheitert an den Triggern."""
    vorher = _inhalt_der_tabellen(rs)
    with closing(_roh(rs)) as v:
        for a in ["UPDATE vorgaenge SET titel = 'anders'", "DELETE FROM vorgaenge",
                  "UPDATE versionen SET inhalt = x'00'", "DELETE FROM versionen",
                  f"INSERT OR REPLACE INTO versionen (vorgang, reise, pfad, inhalt, pruefsumme) "
                  f"VALUES ({drei[0].nummer}, 'probe', 'plan/a.md', x'00', '00')"]:
            with pytest.raises(sqlite3.DatabaseError):
                v.execute(a)
                v.commit()
            v.rollback()
    assert _inhalt_der_tabellen(rs) == vorher


def test_db_legt_datei_geschuetzt_an(rs):
    v = rs.db()
    assert v.row_factory is sqlite3.Row
    assert v.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    assert v.execute("PRAGMA user_version").fetchone()[0] == 1
    assert v.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    v.close()
    assert rs.pfad() == Path(os.environ["FR_SPEICHER"]) / "reisen.db"
    assert stat.S_IMODE(rs.pfad().stat().st_mode) == 0o600
    assert stat.S_IMODE(rs.pfad().parent.stat().st_mode) == 0o700
    rs.db().close()                                                   # zweites Öffnen: Schema mit IF NOT EXISTS


def test_pragma_mit_wert_und_attach_scheitern_ueber_db(rs, drei, tmp_path):
    """Befund F001: Über db() lässt sich der Schutz nicht per PRAGMA abschalten (recursive_triggers=OFF hätte
    INSERT OR REPLACE an den Triggern vorbeigelassen) und die Datei nicht ein zweites Mal ohne Schutz anhängen."""
    vorher = _inhalt_der_tabellen(rs)
    v = rs.db()
    for a in ["PRAGMA recursive_triggers = OFF", "PRAGMA foreign_keys = OFF", "PRAGMA ignore_check_constraints = ON",
              "PRAGMA trusted_schema = ON", "PRAGMA writable_schema = ON", "PRAGMA writable_schema",
              f"ATTACH DATABASE '{rs.pfad()}' AS zweit", "DETACH DATABASE main"]:
        with pytest.raises(sqlite3.DatabaseError):
            v.execute(a)
    assert v.execute("PRAGMA recursive_triggers").fetchone()[0] == 1        # lesende PRAGMAs bleiben erlaubt
    assert v.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    for a in [f"INSERT OR REPLACE INTO vorgaenge (nummer, reise, stand, wann, wer, werkzeug, titel) "
              f"VALUES ({drei[0].nummer}, 'probe', 1, '2026-01-01T00:00:00Z', 'x', 'x', 'x')",
              f"INSERT OR REPLACE INTO versionen (vorgang, reise, pfad, inhalt, pruefsumme) "
              f"VALUES ({drei[0].nummer}, 'probe', 'plan/a.md', x'00', '00')"]:
        with pytest.raises(sqlite3.DatabaseError):
            v.execute(a)
            v.commit()
        v.rollback()
    v.close()
    assert _inhalt_der_tabellen(rs) == vorher
    _schreiben(rs, "probe", {"plan/a.md": A1})                         # der normale Weg geht weiter
    assert rs.stand_nummer("probe") == 5


# ---------- Test 4: Kennung idempotent (AC-4) ----------

def test_bekannte_kennung_schreibt_nichts(rs):
    v1 = _schreiben(rs, "probe", {"plan/a.md": A1}, kennung="vorgang-0001")
    assert v1._fields == ("nummer", "stand") and v1.stand == 1
    vorher = _inhalt_der_tabellen(rs)
    with pytest.raises(rs.VorgangVorhanden) as e:
        _schreiben(rs, "probe", {"plan/a.md": A2}, kennung="vorgang-0001")
    assert (e.value.nummer, e.value.stand) == (v1.nummer, v1.stand)
    assert isinstance(e.value, Exception)
    assert _inhalt_der_tabellen(rs) == vorher
    assert rs.aktueller_stand("probe") == {"plan/a.md": A1}
    assert rs.vorgang_eingetragen("vorgang-0001") == v1
    assert rs.vorgang_eingetragen("vorgang-unbekannt") is None
    _schreiben(rs, "probe", {"plan/a.md": A2})                       # ohne Kennung: mehrere erlaubt
    _schreiben(rs, "probe", {"plan/a.md": A1})
    assert rs.stand_nummer("probe") == 3


# ---------- Test 5: Stand-Nummer (AC-5) ----------

def test_stand_nummer_zaehlt_vorgaenge_ab_uebernommener_zahl(rs, tmp_path):
    assert rs.stand_nummer("probe") is None
    v = rs.importieren(_ordner(tmp_path / "probe", {"plan/a.md": A1}), "probe", wer="Ida", ab=40)
    assert v.stand == 41 and rs.stand_nummer("probe") == 41
    assert _schreiben(rs, "probe", {"plan/a.md": A2, "inhalt/b.md": B1, "inhalt/c.md": C1}).stand == 42
    assert _schreiben(rs, "probe", {"inhalt/c.md": None}).stand == 43
    assert rs.stand_nummer("probe") == 43
    anders = _schreiben(rs, "andere", {"plan/a.md": A1})            # Stand je Reise, Vorgangs-Nummer global
    assert anders.stand == 1 and anders.nummer > v.nummer
    assert rs.stand_nummer("probe") == 43 and rs.stand_nummer("gibtsnicht") is None


def test_wann_wird_gespeichert_sonst_jetzt_in_utc(rs):
    _schreiben(rs, "probe", {"plan/a.md": A1}, wann="2026-11-05T08:00:00Z", rolle="organisator", herkunft="probe")
    _schreiben(rs, "probe", {"plan/a.md": A2})
    alt, neu = rs.verlauf("probe")[::-1]
    assert alt["zeit"] == "2026-11-05T08:00:00Z"
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", neu["zeit"])
    with closing(sqlite3.connect(rs.pfad())) as v:
        assert v.execute("SELECT rolle, herkunft FROM vorgaenge WHERE stand = 1").fetchone() == ("organisator", "probe")


# ---------- Test 6: Unverändertes wird übersprungen (AC-6) ----------

def test_unveraenderte_dateien_ergeben_keine_zeile(rs, drei):
    vorher = _inhalt_der_tabellen(rs)
    with pytest.raises(ValueError):
        _schreiben(rs, "probe", {"plan/a.md": A2})                    # gleiche Bytes wie im aktuellen Stand
    with pytest.raises(ValueError):
        _schreiben(rs, "probe", {"inhalt/fehlt.md": None})            # Löschen einer ohnehin fehlenden Datei
    with pytest.raises(ValueError):
        _schreiben(rs, "probe", {})
    assert _inhalt_der_tabellen(rs) == vorher and rs.stand_nummer("probe") == 4
    v = _schreiben(rs, "probe", {"plan/a.md": A2, "inhalt/c.md": C1, "inhalt/fehlt.md": None})
    with closing(sqlite3.connect(rs.pfad())) as roh:
        pfade = [z[0] for z in roh.execute("SELECT pfad FROM versionen WHERE vorgang = ?", (v.nummer,))]
    assert pfade == ["inhalt/c.md"] and rs.verlauf("probe")[0]["dateien"] == ["inhalt/c.md"]


# ---------- Test 7: Zurücksetzen und Verlauf (AC-7) ----------

def test_zuruecksetzen_ist_ein_neuer_vorgang(rs, drei):
    alt = rs.aktueller_stand("probe", bis=1)
    v = rs.zuruecksetzen("probe", bis=1, wer="Ida", grund="Versehen rückgängig")
    assert v.stand == 5 and rs.stand_nummer("probe") == 5
    assert rs.aktueller_stand("probe") == alt
    verlauf = rs.verlauf("probe")
    assert [e["nummer"] for e in verlauf] == [5, 4, 3, 2, 1]          # nichts gekürzt, neueste zuerst
    e = verlauf[0]
    assert set(e) >= {"nummer", "zeit", "was", "wer", "vorgang", "werkzeug", "grund", "dateien"}
    assert (e["werkzeug"], e["wer"], e["grund"], e["vorgang"]) == ("zuruecksetzen", "Ida", "Versehen rückgängig", v.nummer)
    assert sorted(e["dateien"]) == ["inhalt/b.md", "plan/a.md"]
    with closing(sqlite3.connect(rs.pfad())) as roh:
        assert roh.execute("SELECT herkunft FROM vorgaenge WHERE nummer = ?", (v.nummer,)).fetchone()[0] == "zuruecksetzen:1"
    assert len(rs.verlauf("probe", n=2)) == 2


def test_zuruecksetzen_ohne_abweichung_oder_ohne_angaben_scheitert(rs, drei):
    vorher = _inhalt_der_tabellen(rs)
    with pytest.raises(ValueError):
        rs.zuruecksetzen("probe", bis=4, wer="Ida", grund="nichts zu tun")
    with pytest.raises(ValueError):
        rs.zuruecksetzen("probe", bis=1, wer="Ida", grund="")
    with pytest.raises(ValueError):
        rs.zuruecksetzen("probe", bis=1, wer="", grund="Grund")
    with pytest.raises(KeyError):
        rs.zuruecksetzen("probe", bis=99, wer="Ida", grund="Grund")
    assert _inhalt_der_tabellen(rs) == vorher


def test_zuruecksetzen_auf_stand_mit_geloeschter_datei(rs, drei):
    rs.zuruecksetzen("probe", bis=3, wer="Karl", grund="b war richtig weg")
    assert "inhalt/b.md" not in rs.aktueller_stand("probe")


# ---------- Test 8: Pfade und Ziele (AC-8) ----------

def test_symlink_bricht_den_import_ab(rs, tmp_path):
    quelle = tmp_path / "kopie"
    shutil.copytree(BEISPIEL / "stadtwochenende", quelle)
    (quelle / "inhalt").mkdir(exist_ok=True)
    (quelle / "inhalt" / "verweis.md").symlink_to(tmp_path / "anderswo.md")
    with pytest.raises((ValueError, OSError)):
        rs.importieren(quelle, "stadtwochenende", wer="Tom")
    assert rs.stand_nummer("stadtwochenende") is None


@pytest.mark.parametrize("pfad", ["../aus.md", "plan/../../aus.md", "/aus.md", "plan/a\x00.md", "", "plan//a.md",
                                  "plan/", ".", "plan/./a.md"])
def test_schlechte_pfade_im_vorgang(rs, pfad):
    with pytest.raises(ValueError):
        _schreiben(rs, "probe", {pfad: A1})
    assert rs.stand_nummer("probe") is None


@pytest.mark.parametrize("pfad", ["../aus.md", "plan/a\x00.md"])
def test_export_prueft_pfade_und_schreibt_nichts_ausserhalb(rs, tmp_path, pfad):
    """Ein Pfad, der an den Regeln vorbei in die Datei kam (rohe Verbindung, INSERT ist erlaubt), wird beim Export
    abgelehnt, bevor irgendetwas geschrieben wird."""
    v = _schreiben(rs, "probe", {"plan/a.md": A1})
    with closing(_roh(rs)) as roh:
        n = roh.execute("INSERT INTO vorgaenge (reise, stand, wann, wer, werkzeug, titel) "
                        "VALUES ('probe', ?, '2026-11-05T08:00:00Z', 'x', 'x', 'x')", (v.stand + 1,)).lastrowid
        roh.execute("INSERT INTO versionen (vorgang, reise, pfad, inhalt, pruefsumme) VALUES (?, 'probe', ?, ?, ?)",
                    (n, pfad, b"boese", "0" * 64))
        roh.commit()
    ziel = tmp_path / "exp" / "ziel"
    with pytest.raises(ValueError):
        rs.exportieren("probe", ziel)
    assert not (tmp_path / "exp" / "aus.md").exists() and not (tmp_path / "aus.md").exists()
    assert not ziel.exists() or not any(ziel.rglob("*"))


def test_export_in_nicht_leeres_ziel_scheitert(rs, tmp_path):
    _schreiben(rs, "probe", {"plan/a.md": A1})
    ziel = _ordner(tmp_path / "ziel", {"plan/a.md": b"eigenes"})
    with pytest.raises(FileExistsError):
        rs.exportieren("probe", ziel)
    assert _baum(ziel) == {"plan/a.md": b"eigenes"}
    (tmp_path / "datei").write_bytes(b"x")
    with pytest.raises(FileExistsError):
        rs.exportieren("probe", tmp_path / "datei")


@pytest.mark.parametrize("pfad", ["plan\\a.md", "..\\aus.md", ".git/HEAD", "plan/.git/config", ".git"])
def test_backslash_und_git_pfade_im_vorgang(rs, pfad):
    """Befund F003: Backslashes und ein Teil .git werden abgelehnt (der Import lässt .git aus, der Export legt es nie an)."""
    with pytest.raises(ValueError):
        _schreiben(rs, "probe", {pfad: A1})
    assert rs.stand_nummer("probe") is None


def test_datei_und_ordner_gleichen_namens_werden_abgelehnt(rs, tmp_path):
    """Befund F004: q und q/r zugleich ließen sich nicht exportieren; schon der Vorgang lehnt das ab, auch gegen den
    aktuellen Stand. Nach dem Löschen von q geht q/r."""
    with pytest.raises(ValueError):
        _schreiben(rs, "probe", {"q": A1, "q/r": B1})
    assert rs.stand_nummer("probe") is None
    _schreiben(rs, "probe", {"q": A1})
    vorher = _inhalt_der_tabellen(rs)
    with pytest.raises(ValueError):
        _schreiben(rs, "probe", {"q/r": B1})
    with pytest.raises(ValueError):
        _schreiben(rs, "probe", {"p/q": B1, "p": A1})
    assert _inhalt_der_tabellen(rs) == vorher
    assert _schreiben(rs, "probe", {"q": None, "q/r": B1}).stand == 2
    assert rs.aktueller_stand("probe") == {"q/r": B1}


def test_export_mit_kollision_schreibt_nichts(rs, tmp_path):
    """Befund F004: Kam eine Kollision an den Regeln vorbei in die Datei (rohe Verbindung), prüft der Export alle
    Zielpfade vorher und schreibt nichts."""
    v = _schreiben(rs, "probe", {"a/b.md": A1, "q": A2})
    with closing(_roh(rs)) as roh:
        n = roh.execute("INSERT INTO vorgaenge (reise, stand, wann, wer, werkzeug, titel) "
                        "VALUES ('probe', ?, '2026-11-05T08:00:00Z', 'x', 'x', 'x')", (v.stand + 1,)).lastrowid
        roh.execute("INSERT INTO versionen (vorgang, reise, pfad, inhalt, pruefsumme) VALUES (?, 'probe', 'q/r', ?, ?)",
                    (n, B1, "0" * 64))
        roh.commit()
    ziel = tmp_path / "ziel"
    with pytest.raises(ValueError):
        rs.exportieren("probe", ziel)
    assert not ziel.exists() or not any(ziel.rglob("*"))


def test_export_in_symlink_als_ziel_scheitert(rs, tmp_path):
    """Befund F005: Ein Ziel, das ein Symlink ist (auch auf einen leeren Ordner), wird abgelehnt."""
    _schreiben(rs, "probe", {"plan/a.md": A1})
    fremd = tmp_path / "fremd"
    fremd.mkdir()
    (tmp_path / "verweis").symlink_to(fremd)
    with pytest.raises(ValueError):
        rs.exportieren("probe", tmp_path / "verweis")
    assert not any(fremd.iterdir())


# ---------- Test 9: Sicherung und Rückspieltest (AC-9) ----------

def test_sichern_und_zurueckspielen(rs, tmp_path, monkeypatch):
    assert rs.sichern() is None                                       # noch keine Datenbank: nichts zu sichern
    for reise in ("beispielreise", "stadtwochenende"):
        rs.importieren(BEISPIEL / reise, reise, wer="Ida")
    _schreiben(rs, "stadtwochenende", {"inhalt/neu.md": C1})
    ziel = rs.sichern()
    assert ziel == Path(os.environ["FR_SPEICHER"]) / "sicherung" / "reisen.db"
    assert stat.S_IMODE(ziel.stat().st_mode) == 0o600
    with closing(sqlite3.connect(ziel)) as v:
        assert v.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert v.execute("PRAGMA journal_mode").fetchone()[0] == "delete"
    assert sorted(p.name for p in ziel.parent.iterdir()) == ["reisen.db"]   # keine Temp-Datei übrig
    erwartet = {r: rs.aktueller_stand(r) for r in ("beispielreise", "stadtwochenende")}
    # Rückspieltest: der Schnappschuss als Datenbank einer neuen Instanz
    anders = tmp_path / "zurueck"
    anders.mkdir()
    shutil.copy(ziel, anders / "reisen.db")
    monkeypatch.setenv("FR_SPEICHER", str(anders))
    for reise, inhalt in erwartet.items():
        rs.exportieren(reise, tmp_path / f"aus-{reise}")
        assert _baum(tmp_path / f"aus-{reise}") == inhalt
    rs.exportieren("stadtwochenende", tmp_path / "alt", bis=1)
    assert _baum(tmp_path / "alt") == _baum(BEISPIEL / "stadtwochenende")
    assert rs.pruefen() == []


# ---------- Test 10: Prüfen (AC-10) ----------

def test_pruefen_findet_verfaelschte_pruefsumme(rs, drei):
    assert rs.pruefen() == [] and rs.pruefen("probe") == []
    with closing(_roh(rs)) as roh:
        for (name,) in roh.execute("SELECT name FROM sqlite_master WHERE type = 'trigger' AND tbl_name = 'versionen'").fetchall():
            roh.execute(f"DROP TRIGGER {name}")
        roh.execute("UPDATE versionen SET pruefsumme = ? WHERE pfad = 'plan/a.md' AND vorgang = ?", ("0" * 64, drei[1].nummer))
        roh.commit()
    funde = rs.pruefen()
    assert funde and any("probe" in str(f) and "plan/a.md" in str(f) for f in funde)
    assert rs.pruefen("probe") and rs.pruefen("andere") == []


def test_pruefen_findet_inhalt_in_tombstone(rs, drei):
    with closing(_roh(rs)) as roh:
        n = roh.execute("INSERT INTO vorgaenge (reise, stand, wann, wer, werkzeug, titel) "
                        "VALUES ('probe', 5, '2026-11-05T08:00:00Z', 'x', 'x', 'x')").lastrowid
        roh.execute("INSERT INTO versionen (vorgang, reise, pfad, inhalt, pruefsumme) "
                    "VALUES (?, 'probe', 'plan/z.md', x'41', NULL)", (n,))
        roh.commit()
    funde = rs.pruefen()
    assert any("plan/z.md" in str(f) for f in funde)


# ---------- Test 11: Befehle (AC-16) ----------

def test_befehle(rs, tmp_path, capsys):
    assert "Aufrufe:" in rs.__doc__

    def befehl(*a):
        code = rs.main(list(a))
        return code, capsys.readouterr().out

    quelle = _ordner(tmp_path / "probe", {"plan/a.md": A1, "inhalt/b.md": B1})
    code, aus = befehl("importieren", str(quelle), "probe", "Ida", "--grund", "Probe", "--ab", "10")
    assert code == 0 and re.search(r"\bstand 11\b", aus)
    _schreiben(rs, "probe", {"plan/a.md": A2})
    code, aus = befehl("verlauf", "probe")
    zeilen = aus.strip().splitlines()
    assert code == 0 and len(zeilen) == 2 and zeilen[0].startswith("12") and zeilen[1].startswith("11")
    code, aus = befehl("verlauf", "probe", "1")
    assert code == 0 and len(aus.strip().splitlines()) == 1
    code, _ = befehl("exportieren", "probe", str(tmp_path / "aus"), "--bis", "11")
    assert code == 0 and _baum(tmp_path / "aus") == _baum(quelle)
    code, _ = befehl("exportieren", "probe", str(tmp_path / "aus"))                # Ziel nicht leer
    assert code not in (0, None)
    code, aus = befehl("zuruecksetzen", "probe", "11", "Ida", "Versehen")
    assert code == 0 and re.search(r"\bstand 13\b", aus) and rs.aktueller_stand("probe") == _baum(quelle)
    code, _ = befehl("zuruecksetzen", "probe", "11", "Ida", "")                    # kein Grund
    assert code not in (0, None)
    code, aus = befehl("pruefen")
    assert code == 0 and "ok" in aus
    code, aus = befehl("pruefen", "probe")
    assert code == 0
    code, aus = befehl("sichern")
    assert code == 0 and aus.strip().endswith("reisen.db") and Path(aus.strip()).exists()
    code, aus = befehl("quatsch")
    assert code == 1 and "Aufrufe:" in aus
    code, _ = befehl("exportieren", "gibtsnicht", str(tmp_path / "leer"))
    assert code not in (0, None)


def test_befehl_pruefen_meldet_abweichung(rs, drei, capsys):
    with closing(_roh(rs)) as roh:
        for (name,) in roh.execute("SELECT name FROM sqlite_master WHERE type = 'trigger' AND tbl_name = 'versionen'").fetchall():
            roh.execute(f"DROP TRIGGER {name}")
        roh.execute("UPDATE versionen SET pruefsumme = ? WHERE pfad = 'plan/a.md'", ("0" * 64,))
        roh.commit()
    assert rs.main(["pruefen"]) not in (0, None)
    assert "plan/a.md" in capsys.readouterr().out


# ---------- Test 12: Ort (AC-11) ----------

def test_ort_des_speichers(rs, tmp_path, monkeypatch):
    import instanz
    monkeypatch.setenv("FR_SPEICHER", str(tmp_path / "hier"))
    assert instanz.speicher() == tmp_path / "hier" and rs.pfad() == tmp_path / "hier" / "reisen.db"
    monkeypatch.delenv("FR_SPEICHER")
    monkeypatch.setenv("FR_SEITEN", str(tmp_path / "seiten"))
    assert instanz.speicher() == tmp_path / "seiten" / "_speicher"
    wurzel = tmp_path / "instanz"
    (wurzel / "betrieb").mkdir(parents=True)
    (wurzel / "betrieb" / "einstellungen.env").write_text(f"FR_SPEICHER={tmp_path / 'aus-datei'}\n", encoding="utf-8")
    monkeypatch.setenv("FR_WURZEL", str(wurzel))
    assert instanz.speicher() == tmp_path / "aus-datei"


def test_einstellungen_beispiel_nennt_den_speicher():
    beispiel = (WURZEL / "betrieb" / "einstellungen.beispiel").read_text(encoding="utf-8")
    assert re.search(r"^#?FR_SPEICHER=", beispiel, re.M)
    assert "FR_SPEICHER" in (ENGINE / "instanz.py").read_text(encoding="utf-8").split('"""')[1]   # im Kopfkommentar


# ---------- Test 14: nur Schreibweg und Stand binden den Speicher ein (Stufe 2, #347, AC-23) ----------

def test_jede_modulliste_mit_stand_traegt_reisespeicher():
    """Ersetzt den Stufe-2-Test (AC-23) mit Stufe 3 (#348, AC-19): stand.py lädt den Speicher mit einem normalen Import,
    deshalb trägt jede Modulliste in deploy.sh, die stand.py enthält, auch reisespeicher.py. Konnektor und Rückmeldedienst
    lesen den Speicher weiter nicht selbst (sie gehen über stand)."""
    stand_text = (ENGINE / "stand.py").read_text(encoding="utf-8")
    assert re.search(r"^\s*import reisespeicher\b", stand_text, re.M) and "importlib" not in stand_text
    assert "reisespeicher" in (ENGINE / "schreiben.py").read_text(encoding="utf-8")
    for datei in ("konnektor.py", "rueckmeldungen.py"):
        assert "reisespeicher" not in (ENGINE / datei).read_text(encoding="utf-8"), datei
    deploy = (WURZEL / "betrieb" / "deploy.sh").read_text(encoding="utf-8")
    listen = dict(re.findall(r'^([A-Z]{2}_MODULE)="([^"]*)"', deploy, re.M))
    assert {"RM_MODULE", "KN_MODULE", "SB_MODULE", "PS_MODULE"} <= set(listen)
    for name, inhalt in listen.items():
        module = inhalt.split()
        if "stand.py" in module:
            assert "reisespeicher.py" in module, name


# ---------- Stufe 2 (#347): Zusätze der Schnittstelle ----------

def test_erwartet_schuetzt_vor_verlorenen_aenderungen(rs, drei):
    """AC-1: erwartet= ist die Stand-Nummer, von der der Schreiber ausging. Nur bei Gleichheit entsteht ein Vorgang;
    sonst StandGeaendert(erwartet, aktuell) ohne Zeile. Die Kennungsprüfung hat Vorrang; None prüft nichts (Stufe 1)."""
    assert issubclass(rs.StandGeaendert, Exception)
    vorher = _inhalt_der_tabellen(rs)
    for erwartet in (3, 5, 0):                                          # darunter, darüber, „noch kein Stand“
        with pytest.raises(rs.StandGeaendert) as e:
            _schreiben(rs, "probe", {"plan/a.md": A1}, erwartet=erwartet)
        assert (e.value.erwartet, e.value.aktuell) == (erwartet, 4)
    assert _inhalt_der_tabellen(rs) == vorher and rs.stand_nummer("probe") == 4
    v = _schreiben(rs, "probe", {"plan/a.md": A1}, erwartet=4)          # gleich: geht
    assert v.stand == 5 and rs.aktueller_stand("probe")["plan/a.md"] == A1
    assert _schreiben(rs, "probe", {"plan/a.md": A2}, erwartet=None).stand == 6     # ohne Prüfung wie Stufe 1
    assert _schreiben(rs, "probe", {"plan/a.md": A1}).stand == 7
    # neue Reise: erwartet=0 heißt „es gibt noch keinen Stand“
    assert _schreiben(rs, "neu", {"plan/a.md": A1}, erwartet=0).stand == 1
    with pytest.raises(rs.StandGeaendert) as e:
        _schreiben(rs, "neu", {"plan/a.md": A2}, erwartet=0)
    assert (e.value.erwartet, e.value.aktuell) == (0, 1)
    with pytest.raises(rs.StandGeaendert):
        _schreiben(rs, "gibtsnicht", {"plan/a.md": A1}, erwartet=3)
    assert rs.stand_nummer("gibtsnicht") is None
    # Kennung vor Stand: eine Wiederholung bleibt ungefährlich, auch wenn der Stand inzwischen weiter ist
    w = _schreiben(rs, "probe", {"plan/a.md": A2}, kennung="k-347", erwartet=7)
    with pytest.raises(rs.VorgangVorhanden) as e:
        _schreiben(rs, "probe", {"plan/a.md": B1}, kennung="k-347", erwartet=7)
    assert (e.value.nummer, e.value.stand) == (w.nummer, w.stand)


def test_db_timeout_richtet_sich_nach_dem_parameter(rs):
    """AC-2: db(timeout) ist die Wartezeit auf die Schreibsperre in Sekunden (Vorgabe 10). Hält eine andere Verbindung die
    Sperre, kommt sqlite3.OperationalError nach etwa timeout Sekunden. Unter WAL blockieren Leser nicht; geprüft wird
    deshalb ein zweiter Schreiber (BEGIN IMMEDIATE)."""
    import inspect
    import time
    assert inspect.signature(rs.db).parameters["timeout"].default == 10
    _schreiben(rs, "probe", {"plan/a.md": A1})
    halter = sqlite3.connect(rs.pfad(), timeout=0)
    halter.execute("BEGIN IMMEDIATE")
    try:
        with closing(rs.db(timeout=0.2)) as v:
            start = time.monotonic()
            with pytest.raises(sqlite3.OperationalError):
                v.execute("BEGIN IMMEDIATE")
            dauer = time.monotonic() - start
        assert 0.1 <= dauer < 2, dauer
    finally:
        halter.rollback()
        halter.close()
    with closing(rs.db(timeout=0.2)) as v:                              # Sperre frei: geht sofort
        v.execute("BEGIN IMMEDIATE")
        v.rollback()


def test_datei_und_reisen(rs, drei):
    """AC-3: datei(reise, pfad, bis=None) liefert die Bytes genau einer Datei, ohne die übrigen zu laden; reisen() alle
    Reisen mit mindestens einem Vorgang, sortiert."""
    assert rs.reisen() == ["probe"]
    rs.importieren(BEISPIEL / "stadtwochenende", "stadtwochenende", wer="Tom")
    assert rs.reisen() == ["probe", "stadtwochenende"]
    routen = (BEISPIEL / "stadtwochenende" / "plan" / "routen.yaml").read_bytes()
    assert rs.datei("stadtwochenende", "plan/routen.yaml") == routen
    assert isinstance(rs.datei("stadtwochenende", "plan/routen.yaml"), bytes)
    assert rs.datei("probe", "plan/a.md") == A2
    assert rs.datei("probe", "plan/a.md", bis=1) == A1
    assert rs.datei("probe", "inhalt/b.md", bis=1) == B1
    assert rs.datei("probe", "inhalt/b.md") == B2
    for reise, p, bis in (("gibtsnicht", "plan/a.md", None), ("probe", "plan/a.md", 99),
                          ("probe", "inhalt/b.md", 3),                  # in Stand 3 gelöscht (Tombstone)
                          ("probe", "plan/fehlt.md", None)):
        with pytest.raises(KeyError):
            rs.datei(reise, p, bis=bis)
    with pytest.raises(ValueError):
        rs.datei("probe", "../reise.yaml")
    vorher = _inhalt_der_tabellen(rs)
    rs.reisen()
    assert _inhalt_der_tabellen(rs) == vorher                          # liest nur


def test_ordner_als_vorgang(rs, tmp_path, drei):
    """AC-4: Der Baustein vergleicht einen Ordner (nachher) mit aktueller_stand(reise, basis) (vorher) und schreibt die
    Unterschiede als genau einen Vorgang, fehlende Dateien als Tombstone, mit erwartet=basis. Ohne Unterschied ValueError;
    basis=0 legt eine neue Reise an."""
    rs.exportieren("probe", tmp_path / "kopie", bis=4)
    kopie = tmp_path / "kopie"
    (kopie / "plan" / "a.md").write_bytes(A1)                           # geändert
    (kopie / "inhalt" / "b.md").unlink()                                # fehlt
    (kopie / "inhalt" / "c.md").write_bytes(C1)                         # neu
    v = rs.ordner_als_vorgang("probe", kopie, basis=4, wer="Karl", werkzeug="item_update", titel="Probe geändert",
                              grund="Probe", kennung="k-ordner", rolle="mitwirkend")
    assert v.stand == 5 and rs.stand_nummer("probe") == 5
    assert rs.aktueller_stand("probe") == {"reise.yaml": b"titel: Probe\n", "plan/a.md": A1, "inhalt/c.md": C1}
    e = rs.verlauf("probe", n=1)[0]
    assert (e["was"], e["wer"], e["werkzeug"], e["grund"], e["vorgang"]) == ("Probe geändert", "Karl", "item_update", "Probe",
                                                                             v.nummer)
    assert sorted(e["dateien"]) == ["inhalt/b.md", "inhalt/c.md", "plan/a.md"]
    with closing(sqlite3.connect(rs.pfad())) as roh:
        assert roh.execute("SELECT rolle, kennung FROM vorgaenge WHERE nummer = ?", (v.nummer,)).fetchone() == \
            ("mitwirkend", "k-ordner")
        assert roh.execute("SELECT inhalt FROM versionen WHERE vorgang = ? AND pfad = 'inhalt/b.md'",
                           (v.nummer,)).fetchone() == (None,)
    vorher = _inhalt_der_tabellen(rs)
    with pytest.raises(ValueError):                                     # ohne Unterschied
        rs.ordner_als_vorgang("probe", kopie, basis=5, wer="Karl", werkzeug="item_update", titel="nichts", grund="",
                              kennung=None, rolle="")
    (kopie / "plan" / "a.md").write_bytes(A2)
    with pytest.raises(rs.StandGeaendert):                              # veraltete Basis: nichts geschrieben
        rs.ordner_als_vorgang("probe", kopie, basis=4, wer="Karl", werkzeug="item_update", titel="alt", grund="",
                              kennung=None, rolle="")
    assert _inhalt_der_tabellen(rs) == vorher
    # neue Reise mit basis=0: die Beispielreise als erster Vorgang
    n = rs.ordner_als_vorgang("stadtwochenende", BEISPIEL / "stadtwochenende", basis=0, wer="Tom", werkzeug="reise_anlegen",
                              titel="Neue Reise", grund="", kennung=None, rolle="organisator")
    assert n.stand == 1 and rs.aktueller_stand("stadtwochenende") == _baum(BEISPIEL / "stadtwochenende")


# ---------- Test 15: Dokumentation (AC-14) ----------

def test_adr_und_betriebsdoku():
    adr = WURZEL / "docs" / "adr" / "0009-reisespeicher.md"
    assert adr.exists()
    text = adr.read_text(encoding="utf-8")
    for abschnitt in ("Status", "Kontext", "Entscheidung", "Begründung", "Konsequenzen", "Verlauf"):
        assert re.search(rf"^##\s+{abschnitt}\b", text, re.M), abschnitt
    assert "Schreibzugriff auf die Datei" in text and "0001" in text
    index = (WURZEL / "docs" / "adr" / "README.md").read_text(encoding="utf-8")
    assert any("(0009-reisespeicher.md)" in z for z in index.splitlines())
    betrieb = (WURZEL / "docs" / "betrieb.md").read_text(encoding="utf-8")
    assert "FR_SPEICHER" in betrieb and "reisespeicher.py sichern" in betrieb


# ---------- Test 16: ohne Git, ohne Instanzwerte (AC-11, AC-15) ----------

def test_laeuft_ohne_git(rs, tmp_path, monkeypatch):
    leer = tmp_path / "leerer-pfad"
    leer.mkdir()
    monkeypatch.setenv("PATH", str(leer))
    assert shutil.which("git") is None
    rs.importieren(BEISPIEL / "stadtwochenende", "stadtwochenende", wer="Tom")
    _schreiben(rs, "stadtwochenende", {"inhalt/neu.md": C1}, wer="Lea")
    rs.exportieren("stadtwochenende", tmp_path / "aus", bis=1)
    assert _baum(tmp_path / "aus") == _baum(BEISPIEL / "stadtwochenende")
    assert rs.sichern().exists()


def test_quelltext_ohne_instanzwerte():
    quelle = (ENGINE / "reisespeicher.py").read_text(encoding="utf-8")
    assert "subprocess" not in quelle
    for praefix in ("/srv", "/home", "/var", "/etc", "/tmp", "/mnt", "/root", "/usr", "/opt"):
        assert praefix + "/" not in quelle and f'"{praefix}"' not in quelle, praefix
    assert "environ" not in quelle and "getenv" not in quelle         # Werte nur über instanz
    assert not re.search(r"[\w.+-]+@[\w-]+\.[a-z]{2,}", quelle)        # keine Mail-Adressen
    assert not re.search(r"\b[\w-]+\.(?:com|de|org|net|invalid|eu)\b", quelle)   # keine Domains


# ---------- Tempo-Umbau (#347): _stand in zwei Stufen, ordner_als_vorgang über Prüfsummen ----------

def _referenz_stand(rs, reise, bis, spalte):
    """Die Abfrage in der alten Form (vor dem Umbau, #347): Verhalten, an dem der Umbau gemessen wird."""
    with closing(sqlite3.connect(rs.pfad())) as v:
        zeilen = v.execute(f"""
            SELECT pfad, {spalte} FROM (
              SELECT s.pfad, s.{spalte}, s.inhalt IS NULL AS weg,
                     ROW_NUMBER() OVER (PARTITION BY s.pfad ORDER BY s.vorgang DESC) AS rang
              FROM versionen s JOIN vorgaenge g ON g.nummer = s.vorgang
              WHERE g.reise = ? AND g.stand <= ?)
            WHERE rang = 1 AND NOT weg ORDER BY pfad""", (reise, bis))
        return {z[0]: z[1] for z in zeilen}


def _stand_roh(rs, reise, bis=None, spalte="inhalt"):
    with closing(rs.db()) as v:
        return rs._stand(v, reise, bis, spalte)


def test_stand_holt_inhalt_nur_fuer_neueste_versionen(rs, drei):
    """AC-1: Zwei Stufen in einer Abfrage: Die Fenster-Unterabfrage sieht den Inhalt nicht; die gewünschte Spalte wird
    erst für die Gewinner-Zeilen über den Primärschlüssel (vorgang, pfad) von versionen gelesen."""
    gesehen = []
    with closing(rs.db()) as v:
        v.set_trace_callback(gesehen.append)
        rs._stand(v, "probe", None, "inhalt")
        abfragen = [s for s in gesehen if "ROW_NUMBER" in s.upper()]
        assert len(abfragen) == 1, "eine Abfrage, keine Schleife je Pfad"
        plan = " | ".join(z[3] for z in v.execute("EXPLAIN QUERY PLAN " + abfragen[0]))
    assert "sqlite_autoindex_versionen" in plan, plan                  # Gewinner-Zeilen per Primärschlüssel nachgeschlagen
    innen = abfragen[0].upper().split("ROW_NUMBER")[0]
    assert "INHALT" not in innen.replace("INHALT IS NULL", ""), "Inhalt darf nicht in der Fenster-Unterabfrage stehen"


@pytest.mark.parametrize("spalte", ["inhalt", "pruefsumme"])
def test_stand_gleich_referenz(rs, drei, spalte):
    for bis in (1, 2, 3, 4):
        erwartet = _referenz_stand(rs, "probe", bis, spalte)
        assert erwartet and list(_stand_roh(rs, "probe", bis, spalte).items()) == list(erwartet.items())
    assert _stand_roh(rs, "probe", None, spalte) == _referenz_stand(rs, "probe", 4, spalte)


def test_stand_tombstone_und_neu_angelegt(rs, drei):
    assert "inhalt/b.md" not in _stand_roh(rs, "probe", 3)             # gelöscht
    assert _stand_roh(rs, "probe", 4)["inhalt/b.md"] == B2             # gelöscht, danach neu angelegt


def test_stand_leere_datei_ist_nicht_geloescht(rs, tmp_path):
    import hashlib
    rs.importieren(_ordner(tmp_path / "q", {"leer.md": b"", "voll.md": b"x"}), "probe", wer="Ida")
    assert _stand_roh(rs, "probe")["leer.md"] == b""
    assert _stand_roh(rs, "probe", spalte="pruefsumme")["leer.md"] == hashlib.sha256(b"").hexdigest()


def test_stand_bis_und_unbekannt(rs, drei):
    assert _stand_roh(rs, "probe", 2) == _referenz_stand(rs, "probe", 2, "inhalt")
    for reise, bis in (("gibtsnicht", None), ("probe", 99)):
        with pytest.raises(KeyError):
            _stand_roh(rs, reise, bis)


def test_ordner_als_vorgang_ohne_aenderung(rs, tmp_path, drei):
    rs.exportieren("probe", tmp_path / "kopie")
    with pytest.raises(rs.NichtsGeaendert):
        rs.ordner_als_vorgang("probe", tmp_path / "kopie", basis=4, wer="Karl", werkzeug="item_update", titel="nichts",
                              grund="", kennung=None, rolle="")


def test_ordner_als_vorgang_aenderung_und_loeschung(rs, tmp_path, drei):
    rs.exportieren("probe", tmp_path / "kopie")
    kopie = tmp_path / "kopie"
    (kopie / "plan" / "a.md").write_bytes(A1)
    (kopie / "inhalt" / "b.md").unlink()
    (kopie / "inhalt" / "c.md").write_bytes(C1)
    v = rs.ordner_als_vorgang("probe", kopie, basis=4, wer="Karl", werkzeug="item_update", titel="t", grund="",
                              kennung=None, rolle="")
    assert sorted(rs.verlauf("probe", n=1)[0]["dateien"]) == ["inhalt/b.md", "inhalt/c.md", "plan/a.md"]
    with closing(sqlite3.connect(rs.pfad())) as roh:
        assert roh.execute("SELECT inhalt FROM versionen WHERE vorgang = ? AND pfad = 'inhalt/b.md'",
                           (v.nummer,)).fetchone() == (None,)


def test_ordner_als_vorgang_unbekannte_basis_und_basis_null(rs, tmp_path):
    n = rs.ordner_als_vorgang("neu", BEISPIEL / "stadtwochenende", basis=0, wer="Tom", werkzeug="reise_anlegen",
                              titel="Neu", grund="", kennung=None, rolle="organisator")
    assert n.stand == 1 and rs.aktueller_stand("neu") == _baum(BEISPIEL / "stadtwochenende")
    with pytest.raises(rs.StandGeaendert):                             # unbekannte Basis: Vorher leer, Schutz greift wie bisher
        rs.ordner_als_vorgang("unbekannt", BEISPIEL / "stadtwochenende", basis=7, wer="Tom", werkzeug="x", titel="x",
                              grund="", kennung=None, rolle="")


def test_ordner_als_vorgang_holt_keine_inhalte_des_vorher_standes(rs, tmp_path, drei, monkeypatch):
    rs.exportieren("probe", tmp_path / "kopie")
    (tmp_path / "kopie" / "plan" / "a.md").write_bytes(A1)
    aufrufe = []
    echt = rs._stand

    def spur(v, reise, bis=None, spalte="inhalt"):
        aufrufe.append(spalte)
        return echt(v, reise, bis, spalte)

    monkeypatch.setattr(rs, "_stand", spur)
    monkeypatch.setattr(rs, "aktueller_stand", lambda *a, **k: pytest.fail("aktueller_stand holt alle Bytes"))
    rs.ordner_als_vorgang("probe", tmp_path / "kopie", basis=4, wer="Karl", werkzeug="item_update", titel="t", grund="",
                          kennung=None, rolle="")
    assert "pruefsumme" in aufrufe and "inhalt" not in aufrufe
