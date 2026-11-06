"""Der Ort als Station (ADR-0008, Schritt a, frieda-reist #335): Art am Ort freiwillig, Merkmale erst mit Art, ein Ort liegt
nur in einem Ort (an: O-…, nur Anzeige), Konnektor zeigt Art, „liegt in“ und die Orte darin. Erfundene Testdaten der beiden
Beispielreisen."""
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import bauen  # noqa: E402
import konnektor as kn  # noqa: E402
import schreiben as sb  # noqa: E402
from conftest import meldet  # noqa: E402
from test_schreiben import IDA, KARL, repo, routen_auf_main, schreiber  # noqa: E402,F401

BEISPIELE = Path(__file__).resolve().parent.parent.parent / "beispiel" / "reisen"


def kopie(tmp_path, reise="beispielreise"):
    q = tmp_path / "quelle"
    shutil.copytree(BEISPIELE / reise, q)
    return q


def aendern(datei, fn):
    datei.write_text(fn(datei.read_text(encoding="utf-8")), encoding="utf-8")


def test_beispielreise_orte_mit_und_ohne_art(tmp_path):
    d = bauen.bauen(kopie(tmp_path), tmp_path / "web" / "b")
    orte = d["route"]["orte"]
    assert orte["O-01"]["art"] == "stadt" and orte["O-03"]["art"] == "ort_am_weg"
    assert orte["O-06"]["art"] is None   # freiwillig
    assert d["route"]["arten"]["stadt"]["grundform"] == "ort"


def test_stadtwochenende_ohne_ortsarten_bleibt_wie_es_ist(tmp_path):
    d = bauen.bauen(kopie(tmp_path, "stadtwochenende"), tmp_path / "web" / "s")
    assert all(o["art"] is None for o in d["route"]["orte"].values())


def test_unbekannte_oder_fremde_art_am_ort(tmp_path):
    for art in ("gibtsnicht", "hotel"):   # hotel ist eine Aufenthalts-Art
        q = kopie(tmp_path / art)
        aendern(q / "plan" / "routen.yaml", lambda t: t.replace("O-01: {name: Dresden, art: stadt,", f"O-01: {{name: Dresden, art: {art},"))
        with pytest.raises(bauen.BauFehler) as e:
            bauen.bauen(q, tmp_path / art / "web")
        assert meldet(e.value.args[0], "pruefung.routen.ort_art"), art


def test_ort_mit_merkmal_seiner_art(tmp_path):
    q = kopie(tmp_path)
    aendern(q / "plan" / "arten.yaml", lambda t: t.replace(
        "    name: Stadt\n    farbe: schiefer\n",
        "    name: Stadt\n    farbe: schiefer\n    merkmale:\n      markttag: {name: Markttag, typ: text, stufe: angeboten}\n"))
    aendern(q / "plan" / "routen.yaml", lambda t: t.replace(
        'O-01: {name: Dresden, art: stadt, quelle: "OpenStreetMap"}',
        'O-01: {name: Dresden, art: stadt, quelle: "OpenStreetMap", merkmale: {markttag: {wert: "Samstag (Beispielwert)", quelle: "erfunden"}}}'))
    d = bauen.bauen(q, tmp_path / "web" / "b")
    assert d["route"]["orte"]["O-01"]["merkmale"]["markttag"]["wert"] == "Samstag (Beispielwert)"


def test_ort_liegt_nur_in_einem_ort(tmp_path):
    q = kopie(tmp_path, "stadtwochenende")
    aendern(q / "plan" / "routen.yaml", lambda t: t.replace(
        'O-02: {name: Beispielstadt, quelle: "erfunden (Beispiel)"}', 'O-02: {name: Beispielstadt, an: O-01, quelle: "erfunden (Beispiel)"}'))
    d = bauen.bauen(q, tmp_path / "web" / "ok")
    assert d["route"]["eltern"]["O-02"] == "O-01"
    # Anschluss bleibt exakte Gleichheit: die Tage rechnen wie vorher
    vorher = bauen.bauen(kopie(tmp_path / "v", "stadtwochenende"), tmp_path / "web" / "v")
    assert [t.get("end_ort") for t in d["route"]["tage"]] == [t.get("end_ort") for t in vorher["route"]["tage"]]
    q2 = kopie(tmp_path / "x", "stadtwochenende")
    aendern(q2 / "plan" / "routen.yaml", lambda t: t.replace(
        'O-02: {name: Beispielstadt, quelle: "erfunden (Beispiel)"}', 'O-02: {name: Beispielstadt, an: E-01, quelle: "erfunden (Beispiel)"}'))
    with pytest.raises(bauen.BauFehler) as e:
        bauen.bauen(q2, tmp_path / "web" / "x")
    assert meldet(e.value.args[0], "pruefung.routen.eltern_ort")


def test_konnektor_zeigt_art_liegt_in_und_orte_darin(tmp_path):
    q = kopie(tmp_path)
    aendern(q / "plan" / "routen.yaml", lambda t: t.replace(
        '    name: Lichtenhainer Wasserfall\n', '    name: Lichtenhainer Wasserfall\n    an: O-05\n', 1))
    h = kn.Handbuch(bauen.bauen(q, tmp_path / "web" / "b"))
    _, t5 = h.eintraege["O-05"]
    _, t6 = h.eintraege["O-06"]
    _, t1 = h.eintraege["O-01"]
    assert meldet(t1, "konnektor.ausgabe.ort.art") and "Stadt (stadt)" in t1
    assert meldet(t6, "konnektor.ausgabe.ort.liegt_in") and "Bad Schandau (O-05)" in t6
    assert meldet(t5, "konnektor.ausgabe.ort.orte_darin") and "Lichtenhainer Wasserfall (O-06)" in t5


def test_item_create_ort_mit_art_und_an(repo):
    _, origin, _, _ = repo
    s = schreiber(repo)
    a = s.schreiben("beispielreise", "ding_anlegen", {**IDA, "args": {"was": "ort", "titel": "Rathen", "art": "ort_am_weg", "an": "O-05",
                                                                    "quelle": "Beispiel"}})
    assert a["ok"]
    r, _ = routen_auf_main(origin)
    neu_ = [o for o in r["orte"].values() if o["name"] == "Rathen"]
    assert neu_ and neu_[0]["art"] == "ort_am_weg" and neu_[0]["an"] == "O-05"


def test_item_create_ort_lehnt_ab(repo):
    s = schreiber(repo)
    for args, schluessel in (({"art": "hotel"}, "schreiben.ding_anlegen.ort_art"),
                             ({"an": "E-01"}, "schreiben.ding_aendern.an_ort"),
                             ({"an": "A-01"}, "schreiben.ding_aendern.an_ort")):
        with pytest.raises(sb.Ablehnung) as e:
            s.schreiben("beispielreise", "ding_anlegen", {**IDA, "args": {"was": "ort", "titel": "Rathen", "quelle": "Beispiel", **args}})
        assert meldet(str(e.value), schluessel), args
        s.vorbereiten()


def test_item_update_ort_art_an_und_merkmal(repo):
    _, origin, _, _ = repo
    s = schreiber(repo)
    s.schreiben("beispielreise", "ding_aendern", {**IDA, "args": {"ziel": "O-06", "art": "ort_am_weg", "an": "O-05"}})
    r, _ = routen_auf_main(origin)
    assert r["orte"]["O-06"]["art"] == "ort_am_weg" and r["orte"]["O-06"]["an"] == "O-05"
    s.vorbereiten()
    with pytest.raises(sb.Ablehnung) as e:
        s.schreiben("beispielreise", "ding_aendern", {**IDA, "args": {"ziel": "O-06", "an": "W-05"}})
    assert meldet(str(e.value), "schreiben.ding_aendern.an_ort")
    s.vorbereiten()
    with pytest.raises(sb.Ablehnung) as e:   # die Art eines Orts ändert nur eine Organisatorin
        s.schreiben("beispielreise", "ding_aendern", {**KARL, "args": {"ziel": "O-06", "art": "stadt"}})
    assert meldet(str(e.value), "schreiben.ding_aendern.4")


def test_merkmal_an_ort_ohne_art_wird_abgelehnt(repo):
    s = schreiber(repo)
    with pytest.raises(sb.Ablehnung) as e:
        s.schreiben("beispielreise", "wert_eintragen", {**IDA, "args": {"ziel": "O-06", "merkmal": "markttag", "wert": "x", "quelle": "Beispiel"}})
    assert meldet(str(e.value), "schreiben.wert_eintragen.ort_ohne_art")
