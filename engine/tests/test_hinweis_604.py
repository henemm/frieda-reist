"""Geplättete Hinweise (#604): Bis #601 zog der Schreibweg jeden Zeilenumbruch eines Hinweises (bis #594 auch eines Tagestexts)
zu einem Leerzeichen; Listen standen danach in einer Zeile. show (zeige) und die Seite ziehen selbst nichts zusammen; show liest
die veröffentlichte Seite und sagt jetzt, wenn ein neuerer Stand gesichert ist. neu.py umbrechen bricht geplättete Listen wieder
um (Vorschau, dann ein Vorgang im Reisespeicher). Erfundene Testdaten beider Beispielreisen."""
import json
import shutil
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import bauen  # noqa: E402
import konnektor as kn  # noqa: E402
import neu  # noqa: E402
import schreiben as sb  # noqa: E402
import stand  # noqa: E402
import textform  # noqa: E402
from conftest import meldet  # noqa: E402

BEISPIELE = Path(__file__).resolve().parent.parent.parent / "beispiel" / "reisen"
IDA = {"name": "Ida", "rolle": "organisator"}
REISEN = ["beispielreise", "stadtwochenende"]
HINWEIS = "Ablauf (erfunden, Beispielwert):\n\n1. **Schwelle:** kurz innehalten\n2. **Intention:** ein Wort für den Tag\n3. *Weg* mit Blick ins Tal"
FLACH = " ".join(HINWEIS.split())   # so hat der Schreibweg bis #601 gespeichert


def kopie(tmp_path, reise="beispielreise"):
    q = tmp_path / reise
    shutil.copytree(BEISPIELE / reise, q)
    return q


def routen(q):
    return yaml.safe_load((q / "plan" / "routen.yaml").read_text(encoding="utf-8"))


def erstes(q, gruppe):
    return next(iter(routen(q)[gruppe]))


# ---------- umbrechen: was erkannt wird und was bleibt ----------

@pytest.mark.parametrize("flach, erwartet", [
    (FLACH, HINWEIS),
    ("1. **Ankommen:** Spaziergang ohne Handy, das Davor bleibt draußen. 2. **Vorsatz:** einen Satz aufschreiben (z. B. kein neues "
     "Projekt). 3. **Brief:** Was erhoffe ich mir? Erst am Ende öffnen.",
     "1. **Ankommen:** Spaziergang ohne Handy, das Davor bleibt draußen.\n2. **Vorsatz:** einen Satz aufschreiben (z. B. kein neues "
     "Projekt).\n3. **Brief:** Was erhoffe ich mir? Erst am Ende öffnen."),
    ("Mitnehmen: - 2 Liter Wasser je Person - Stirnlampe - Brot", "Mitnehmen:\n\n- 2 Liter Wasser je Person\n- Stirnlampe\n- Brot"),
    ("- Pass - Fahrkarte", "- Pass\n- Fahrkarte"),
    ("Route Dorf - Stadt. Packen: - Pass - Fahrkarte", "Route Dorf - Stadt. Packen:\n\n- Pass\n- Fahrkarte"),
])
def test_umbrechen_erkennt_geplaettete_listen(flach, erwartet):
    assert textform.umbrechen(flach) == erwartet
    assert textform.umbrechen(erwartet) == erwartet   # schon mit Zeilen: unverändert


@pytest.mark.parametrize("text", [
    "Wir gehen am 1. Tag zur Burg und am 2. Tag ins Tal.",   # Ordnungszahl im Satz, keine Liste
    "Treffen am 1. 2. 2027 um 10 Uhr.",                      # Datum
    "Dorf - Stadt - Hafen",                                  # Strecke mit Strichen
    "Ein Satz ohne Liste.",
    "",
])
def test_umbrechen_laesst_text_ohne_liste(text):
    assert textform.umbrechen(text) == text


# ---------- show (zeige) zieht nichts zusammen ----------

@pytest.mark.parametrize("reise", REISEN)
def test_zeige_gibt_den_hinweis_mit_zeilen_aus(tmp_path, reise):
    q = kopie(tmp_path, reise)
    for gruppe in ("aufenthalte", "unterkuenfte"):
        did = erstes(q, gruppe)
        sb.ding_aendern(q, IDA, {"ziel": did, "hinweis": HINWEIS, "quelle": "erfunden (Test)"})
        assert routen(q)[gruppe][did]["hinweis"] == HINWEIS
    h = kn.Handbuch(bauen.bauen(q, tmp_path / "web"))
    for gruppe in ("aufenthalte", "unterkuenfte"):
        aus, fehler = h.zeige(erstes(q, gruppe))
        assert fehler is None and HINWEIS in aus, aus


def test_zeige_sagt_wenn_die_seite_hinter_dem_gesicherten_stand_ist(tmp_path, monkeypatch):
    q = kopie(tmp_path)
    seiten = tmp_path / "seiten"
    d = bauen.bauen(q, seiten / "beispielreise")
    d["reise_stand"] = {**(d.get("reise_stand") or {}), "nummer": 5}
    (seiten / "beispielreise" / "daten.json").write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setenv("KN_SEITEN", str(seiten))
    monkeypatch.setenv("FR_DIENST", str(tmp_path / "_dienst"))
    zugang = {"reise": "beispielreise", "person": "karl"}
    t, fehler = kn.werkzeug(zugang, "zeige", {"id": "A-01"})
    assert not fehler and not meldet(t, "konnektor.zeige.seite_zurueck")   # kein gesicherter Stand bekannt: kein Satz
    stand.gesichert_schreiben("beispielreise", 5)
    t, _ = kn.werkzeug(zugang, "zeige", {"id": "A-01"})
    assert not meldet(t, "konnektor.zeige.seite_zurueck")                  # Seite auf dem Stand
    stand.gesichert_schreiben("beispielreise", 7)
    t, _ = kn.werkzeug(zugang, "zeige", {"id": "A-01"})
    assert meldet(t, "konnektor.zeige.seite_zurueck") and "7" in t and "5" in t


# ---------- neu.py umbrechen ----------

def flach_machen(q):
    """Wie vor #601/#594: ein Hinweis, ein Lesetext und ein Tagestext in einer Zeile."""
    r = routen(q)
    aid, tid = erstes(q, "aufenthalte"), erstes(q, "tage")
    p = q / "plan" / "routen.yaml"
    from ruamel.yaml.scalarstring import DoubleQuotedScalarString
    roh = sb.routen_laden(q)
    roh["aufenthalte"][aid]["hinweis"] = DoubleQuotedScalarString(FLACH)
    roh["aufenthalte"][aid]["lesetext"] = {"text": "Ablauf: - Ankommen am Tor - Umschauen im Hof", "quelle": "erfunden (Test)",
                                           "geschrieben": r["start"]["datum"], "wer": "Ida"}
    roh["tage"][tid]["text"] = DoubleQuotedScalarString("Mitnehmen: - 2 Liter Wasser - Stirnlampe")
    sb.routen_speichern(q, roh)
    return aid, tid, p.read_text(encoding="utf-8")


@pytest.mark.parametrize("reise", REISEN)
def test_umbrechen_im_ordner_erst_vorschau_dann_schreiben(tmp_path, reise, capsys):
    q = kopie(tmp_path, reise)
    aid, tid, vorher = flach_machen(q)
    assert neu.main(["umbrechen", str(q)]) == 0
    aus = capsys.readouterr().out
    assert f"{aid} hinweis:" in aus and f"{aid} lesetext:" in aus and f"{tid} text:" in aus and "--schreiben" in aus
    assert (q / "plan" / "routen.yaml").read_text(encoding="utf-8") == vorher   # Vorschau ändert nichts
    assert neu.main(["umbrechen", str(q), "--schreiben"]) == 0
    r = routen(q)
    assert r["aufenthalte"][aid]["hinweis"] == HINWEIS
    assert r["aufenthalte"][aid]["lesetext"]["text"].strip() == "Ablauf:\n\n- Ankommen am Tor\n- Umschauen im Hof"
    assert r["tage"][tid]["text"] == "Mitnehmen:\n\n- 2 Liter Wasser\n- Stirnlampe"
    alt = yaml.safe_load(vorher)   # sonst ändert sich nichts
    for x in (alt, r):
        x["aufenthalte"][aid].pop("hinweis"), x["aufenthalte"][aid].pop("lesetext"), x["tage"][tid].pop("text")
    assert alt == r
    bauen.bauen(q, tmp_path / "web")
    assert neu.umbrechen(q) == []   # ein zweiter Lauf ändert nichts
    capsys.readouterr()
    assert neu.main(["umbrechen", str(q)]) == 0 and "Nothing" in capsys.readouterr().out


@pytest.fixture
def speicher(tmp_path, monkeypatch):
    monkeypatch.setenv("FR_SPEICHER", str(tmp_path / "_speicher"))
    import reisespeicher
    return reisespeicher


@pytest.mark.parametrize("reise", REISEN)
def test_umbrechen_im_speicher_ein_vorgang_mit_den_alten_texten(tmp_path, speicher, reise, capsys):
    q = kopie(tmp_path, reise)
    aid, tid, _ = flach_machen(q)
    speicher.importieren(q, reise, "Test", grund="vor #601 (erfunden)")
    n = speicher.stand_nummer(reise)
    assert neu.main(["umbrechen", reise, "--speicher", str(tmp_path / "a1")]) == 0   # Vorschau
    assert f"{aid} hinweis:" in capsys.readouterr().out and speicher.stand_nummer(reise) == n
    assert neu.main(["umbrechen", reise, "--speicher", str(tmp_path / "a2"), "--schreiben", "--wer", "Ida"]) == 0
    assert "written" in capsys.readouterr().out
    assert speicher.stand_nummer(reise) == n + 1
    letzter = speicher.verlauf(reise, 1)[0]
    assert letzter["wer"] == "Ida" and letzter["werkzeug"] == "umbrechen" and FLACH in letzter["grund"]   # alter Text im Verlauf
    r = yaml.safe_load(speicher.datei(reise, "plan/routen.yaml").decode("utf-8"))
    assert r["aufenthalte"][aid]["hinweis"] == HINWEIS and r["tage"][tid]["text"].startswith("Mitnehmen:\n\n- ")
    assert neu.main(["umbrechen", reise, "--speicher", str(tmp_path / "a3"), "--schreiben"]) == 0
    assert "Nothing" in capsys.readouterr().out and speicher.stand_nummer(reise) == n + 1


def test_umbrechen_im_speicher_schreibt_nichts_bei_rotem_bau(tmp_path, speicher, monkeypatch, capsys):
    q = kopie(tmp_path)
    flach_machen(q)
    speicher.importieren(q, "beispielreise", "Test", grund="vor #601 (erfunden)")
    n = speicher.stand_nummer("beispielreise")

    def rot(ordner):
        raise ValueError("Bau gescheitert (Test)")
    monkeypatch.setattr(neu, "probebau", rot)
    assert neu.main(["umbrechen", "beispielreise", "--speicher", str(tmp_path / "a"), "--schreiben"]) == 2
    assert "Bau gescheitert" in capsys.readouterr().out and speicher.stand_nummer("beispielreise") == n
