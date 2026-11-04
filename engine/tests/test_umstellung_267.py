"""#267 (Teil 3 von #215), PR b: neu.py nachziehen trägt `sprache: de` in reise.yaml ein, wenn das Feld fehlt oder leer ist
(Spec docs/specs/betrieb/altformen-entfernen-267.md, Festlegungen für PR b). Nur erfundene Daten: die beiden Beispielreisen."""
import re
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bauen  # noqa: E402
import neu  # noqa: E402
import reise  # noqa: E402
import texte  # noqa: E402
import texte_de  # noqa: E402
import texte_en  # noqa: E402
from test_umstellung_250 import WERTE, ausgefuellt  # noqa: E402

WURZEL = Path(__file__).resolve().parent.parent.parent
BEISPIELE = ["beispielreise", "stadtwochenende"]
SCHLUESSEL = "inhalt.nachziehen.sprache_eingetragen"
SPRACHZEILE = re.compile(r"^sprache:.*\n", re.M)


def kopie(tmp_path, name="beispielreise", sprache="fehlt"):
    """Kopie einer Beispielreise; sprache: fehlt | leer | none | tilde | blank | Wert (z. B. en, xx)."""
    ziel = tmp_path / name
    shutil.copytree(WURZEL / "beispiel" / "reisen" / name, ziel)
    y = ziel / "reise.yaml"
    text = y.read_text(encoding="utf-8")
    assert SPRACHZEILE.search(text)
    zeile = {"fehlt": "", "leer": "sprache:\n", "none": "sprache: null\n", "tilde": "sprache: ~\n",
             "blank": 'sprache: "  "\n'}.get(sprache, f"sprache: {sprache}\n")
    y.write_text(SPRACHZEILE.sub(lambda _m: zeile, text, count=1), encoding="utf-8")
    return ziel


def stand(ordner):
    """Alle Dateien der Reise -> {relativer Pfad: Bytes}."""
    return {str(p.relative_to(ordner)): p.read_bytes() for p in sorted(Path(ordner).rglob("*")) if p.is_file()}


def katalog(modul):
    return next(v for v in vars(modul).values() if isinstance(v, dict) and "pruefung.reise.20" in v)


@pytest.mark.parametrize("modul", [texte_de, texte_en])
def test_katalog_hat_den_schluessel(modul):
    assert SCHLUESSEL in katalog(modul)


@pytest.mark.parametrize("wie", ["fehlt", "leer", "none", "tilde", "blank"])
def test_fehlende_oder_leere_sprache_wird_eingetragen(tmp_path, wie):
    """AC-3: fehlt oder leer (Schlüssel fehlt, None, "", nur Leerzeichen) -> sprache: de und eine Meldung."""
    r = kopie(tmp_path, sprache=wie)
    m = neu.nachziehen(r)
    erwartet = texte.t("de", SCHLUESSEL)
    assert erwartet != SCHLUESSEL
    assert erwartet in m
    roh = (r / "reise.yaml").read_text(encoding="utf-8")
    assert len(re.findall(r"^sprache:", roh, re.M)) == 1               # ersetzt, nicht doppelt eingefügt
    assert re.search(r"^sprache:\s*['\"]?de['\"]?\s*(#.*)?$", roh, re.M)
    assert reise.sprache_von(r) == "de"


def test_meldung_nennt_die_gesetzte_sprache_in_beiden_katalogen():
    assert "„de“" in texte.t("de", SCHLUESSEL)
    assert texte.t("en", SCHLUESSEL) != SCHLUESSEL and texte.t("en", SCHLUESSEL) != texte.t("de", SCHLUESSEL)


def test_position_hinter_pfad(tmp_path):
    """Reihenfolge wie neu.anlegen: titel, untertitel, ziel, pfad, sprache, zeitraum."""
    r = kopie(tmp_path, "stadtwochenende", sprache="fehlt")
    neu.nachziehen(r)
    schluessel = re.findall(r"^([a-z_]+):", (r / "reise.yaml").read_text(encoding="utf-8"), re.M)
    assert schluessel.index("sprache") == schluessel.index("pfad") + 1


def test_ohne_pfad_hinter_dem_letzten_vorgaenger(tmp_path):
    r = kopie(tmp_path, "stadtwochenende")
    y = r / "reise.yaml"
    y.write_text(re.sub(r"^pfad:.*\n", "", y.read_text(encoding="utf-8"), flags=re.M), encoding="utf-8")
    neu.nachziehen(r)
    schluessel = re.findall(r"^([a-z_]+):", y.read_text(encoding="utf-8"), re.M)
    assert schluessel.index("sprache") == schluessel.index("titel") + 1


def test_ohne_alle_vorgaenger_als_erster_schluessel_nach_dem_kopfkommentar(tmp_path):
    r = kopie(tmp_path, "stadtwochenende")
    y = r / "reise.yaml"
    y.write_text(re.sub(r"^(titel|untertitel|ziel|pfad):.*\n", "", y.read_text(encoding="utf-8"), flags=re.M), encoding="utf-8")
    neu.nachziehen(r)
    text = y.read_text(encoding="utf-8")
    zeilen = [z for z in text.splitlines() if z.strip() and not z.startswith("#")]
    assert zeilen[0].startswith("sprache:")
    assert text.startswith("#")                                         # Kopfkommentar bleibt oben


@pytest.mark.parametrize("name", BEISPIELE)
def test_zweiter_lauf_aendert_nichts(tmp_path, name):
    """AC-4: direkt danach keine Meldung und alle Dateien der Reise byte-gleich."""
    r = kopie(tmp_path, name)
    assert neu.nachziehen(r)
    vorher = stand(r)
    assert neu.nachziehen(r) == []
    assert stand(r) == vorher


@pytest.mark.parametrize("wert", ["de", "en", "xx", "fr"])
def test_vorhandene_sprache_bleibt_byte_gleich(tmp_path, wert):
    """AC-3: gültig oder unbekannt: die Datei wird nicht angefasst, es gibt keine Meldung dazu."""
    r = kopie(tmp_path, sprache=wert)
    vorher = stand(r)
    m = neu.nachziehen(r)
    assert texte.t("de", SCHLUESSEL) not in m and texte.t("en", SCHLUESSEL) not in m
    assert stand(r)["reise.yaml"] == vorher["reise.yaml"]


@pytest.mark.parametrize("zeile", ["sprache: [de, en]\n", "sprache: 3\n"])
def test_fremde_eingabe_bleibt_unberuehrt(tmp_path, zeile):
    r = kopie(tmp_path, sprache=zeile.strip().split(": ", 1)[1])
    y = r / "reise.yaml"
    vorher = y.read_bytes()
    neu.nachziehen(r)
    assert y.read_bytes() == vorher


def test_kommentare_und_form_bleiben(tmp_path):
    """Nur die eine Zeile kommt hinzu; alles andere in reise.yaml ist danach byte-gleich."""
    r = kopie(tmp_path, "stadtwochenende")
    y = r / "reise.yaml"
    vorher = y.read_text(encoding="utf-8")
    neu.nachziehen(r)
    nachher = y.read_text(encoding="utf-8")
    ohne = "".join(z for z in nachher.splitlines(keepends=True) if not z.startswith("sprache:"))
    assert ohne == vorher
    assert "# Eckdaten, Zeitraum, Status" in nachher


def test_probelauf_meldet_und_schreibt_nichts(tmp_path):
    r = kopie(tmp_path)
    vorher = stand(r)
    m = neu.nachziehen(r, schreiben=False)
    assert texte.t("de", SCHLUESSEL) in m
    assert stand(r) == vorher


@pytest.mark.parametrize("name", BEISPIELE)
def test_beispielreisen_melden_nichts_zur_sprache(name):
    """Beide Beispielreisen tragen sprache: de; die Umstellung meldet dazu nichts. (Die Spec nennt „keine Meldung“ für beide;
    die Beispielreise hat aber schon vor #267 eine offene Umstellung, arten.yaml herberge: rolle kosten. Das ist ein
    eigener Befund und gehört nicht zu diesem PR; hier zählt nur die Sprache.)"""
    m = neu.nachziehen(WURZEL / "beispiel" / "reisen" / name, schreiben=False)
    assert texte.t("de", SCHLUESSEL) not in m and texte.t("en", SCHLUESSEL) not in m
    assert all("sprache" not in x for x in m)
    if name == "stadtwochenende":
        assert m == []


def test_reise_ohne_reise_yaml_wird_uebergangen(tmp_path):
    """Ohne reise.yaml tut die Umstellung nichts (der Bau meldet den Fehler, PR a)."""
    r = kopie(tmp_path)
    (r / "reise.yaml").unlink()
    assert texte.t("de", SCHLUESSEL) not in neu.nachziehen(r)
    assert not (r / "reise.yaml").exists()


def test_sprache_nachziehen_ist_eine_eigene_funktion(tmp_path):
    """Festlegung: neu.sprache_nachziehen(reise_dir, schreiben) -> Liste der Meldungen."""
    r = kopie(tmp_path)
    assert neu.sprache_nachziehen(r, False) == [texte.t("de", SCHLUESSEL)]
    assert not re.search(r"^sprache:", (r / "reise.yaml").read_text(encoding="utf-8"), re.M)
    assert neu.sprache_nachziehen(r, True) == [texte.t("de", SCHLUESSEL)]
    assert neu.sprache_nachziehen(r, True) == []


def test_sprache_steht_vor_den_schritten_die_sie_nutzen(tmp_path, monkeypatch):
    """Reihenfolge: das Eintragen läuft vor eckdaten_nachziehen und reste_nachziehen."""
    r = kopie(tmp_path)
    gesehen = []
    for name in ("eckdaten_nachziehen", "reste_nachziehen"):
        orig = getattr(neu, name)

        def wrap(*a, _o=orig, _n=name, **k):
            gesehen.append((_n, bool(re.search(r"^sprache:\s*de", (r / "reise.yaml").read_text(encoding="utf-8"), re.M))))
            return _o(*a, **k)
        monkeypatch.setattr(neu, name, wrap)
    neu.nachziehen(r)
    assert gesehen and all(da for _, da in gesehen)


def test_reste_nachziehen_liest_nach_dem_eintragen_nicht_falsch(tmp_path):
    """Eine Rest-Datei der früheren deutschen Vorlage wird nach dem Eintragen noch erkannt."""
    r = kopie(tmp_path)
    (r / "CLAUDE.md").write_text(ausgefuellt("de", "CLAUDE.md", **WERTE), encoding="utf-8")
    m = neu.nachziehen(r)
    assert texte.t("de", SCHLUESSEL) in m
    assert not (r / "CLAUDE.md").exists()


@pytest.mark.parametrize("name", BEISPIELE)
def test_kopie_ohne_sprache_wird_umgestellt_und_baut_danach(tmp_path, name):
    """Ende zu Ende: die Umstellung meldet, danach baut die Reise und nachziehen ist still."""
    r = kopie(tmp_path, name)
    assert texte.t("de", SCHLUESSEL) in neu.nachziehen(r)
    assert neu.nachziehen(r) == []
    bauen.Bauer(r, tmp_path / "dist").daten()


def test_alle_altformen_in_einem_lauf(tmp_path):
    """Reise ohne sprache, mit Rest der früheren Vorlage: ein Lauf stellt alles um, danach ist Ruhe und der Bau läuft."""
    r = kopie(tmp_path)
    (r / "CLAUDE.md").write_text(ausgefuellt("de", "CLAUDE.md", **WERTE), encoding="utf-8")
    m = neu.nachziehen(r)
    assert texte.t("de", SCHLUESSEL) in m and len(m) >= 2
    assert neu.nachziehen(r) == []
    bauen.Bauer(r, tmp_path / "dist").daten()


@pytest.mark.parametrize("wie", ["fehlt", "leer"])
def test_crlf_bleibt_erhalten(tmp_path, wie):
    """F001: reise.yaml mit CRLF behält alle Zeilenenden; nur die eine Zeile sprache: de kommt dazu (bzw. ersetzt die leere),
    mit CRLF; ein zweiter Lauf ändert kein Byte."""
    r = kopie(tmp_path, sprache=wie)
    y = r / "reise.yaml"
    vorher = y.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    y.write_bytes(vorher)
    assert neu.sprache_nachziehen(r)
    nachher = y.read_bytes()
    assert nachher.count(b"\n") == nachher.count(b"\r\n")
    alt, neu_z = vorher.split(b"\r\n"), nachher.split(b"\r\n")
    if wie == "fehlt":
        assert len(neu_z) == len(alt) + 1
        i = neu_z.index(b"sprache: de")
        assert neu_z[:i] + neu_z[i + 1:] == alt
    else:
        assert len(neu_z) == len(alt)
        abweichend = [k for k, (a, b) in enumerate(zip(alt, neu_z)) if a != b]
        assert len(abweichend) == 1 and neu_z[abweichend[0]] == b"sprache: de"
    assert neu.sprache_nachziehen(r) == []
    assert y.read_bytes() == nachher


def test_sprache_ohne_wert_liest_nicht_die_naechste_zeile_319(tmp_path, monkeypatch):
    """#319: „sprache:“ ohne Wert gilt als fehlend (Rückfall), statt den Schlüssel der nächsten Zeile als Sprache zu lesen."""
    monkeypatch.setattr(texte, "VORGABE_REISE", "en")
    (tmp_path / "reise.yaml").write_text("titel: Test\nsprache:\nde: erfundener Schlüssel\n", encoding="utf-8")
    assert reise.sprache_von(tmp_path) == texte.VORGABE_REISE
    (tmp_path / "reise.yaml").write_text("titel: Test\nsprache:   de  \n", encoding="utf-8")
    assert reise.sprache_von(tmp_path) == "de"
