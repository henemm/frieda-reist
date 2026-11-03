"""Typisierte Merkmale der Grundformen (ADR-0007, Schritt b, frieda-reist#283): Lage, Zeit und Track als Merkmale mit Typ statt
fester Felder. Lesen (alte und neue Form bauen gleich), Umstellung (neu.py nachziehen), Schreibweg. Erfundene Testdaten."""
import datetime
import shutil
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import bauen  # noqa: E402
import neu  # noqa: E402
import routen  # noqa: E402
import schreiben as sb  # noqa: E402
from conftest import meldet  # noqa: E402
from test_schreiben import IDA, KARL, repo, routen_auf_main, schreiber  # noqa: E402,F401

WURZEL = Path(__file__).resolve().parent.parent.parent
BEISPIELE = WURZEL / "beispiel" / "reisen"
ALT = ("adresse", "punkt", "gpx", "beginn", "ende", "ab", "an", "buchungslink")


def kopie(tmp_path, reise="beispielreise"):
    q = tmp_path / "quelle"
    shutil.copytree(BEISPIELE / reise, q)
    return q


def alte_form(q, extra=None):
    """Die Reise im Format vor ADR-0007: Lage, Zeit und Link als feste Felder (die typisierten Merkmale zurückgefaltet). extra:
    {ID: {Feld: Wert}} kommt dazu."""
    datei = q / "plan" / "routen.yaml"
    roh = yaml.safe_load(datei.read_text(encoding="utf-8"))
    for gruppe in ("orte", "strecken", "unterkuenfte", "aufenthalte"):
        for did, d in (roh.get(gruppe) or {}).items():
            roh[gruppe][did] = routen.lage_merkmale_falten(d, did, lambda *a, **k: None)
    for did, felder in (extra or {}).items():
        gruppe = {"O": "orte", "E": "strecken", "U": "unterkuenfte", "A": "aufenthalte"}[did[0]]
        roh[gruppe][did].update(felder)
    datei.write_text(yaml.safe_dump(roh, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return roh


EXTRA = {"O-03": {"punkt": {"wert": [50.96, 14.07], "quelle": "erfunden (Beispiel)", "geprueft": datetime.date(2026, 11, 1)}},
         "U-02": {"adresse": {"wert": "Am Markt 3, 01848 Hohnstein", "quelle": "erfunden (Beispiel)"},
                  "punkt": {"wert": [50.97, 14.1], "quelle": "erfunden (Beispiel)"}, "buchungslink": "https://burgblick.example/buchen"},
         "A-01": {"punkt": {"wert": [50.98, 14.11], "quelle": "erfunden (Beispiel)"}}}


def route_ohne_katalog(d):
    r = dict(d["route"])
    for k in ("arten", "merkmale"):
        r.pop(k, None)
    return r


@pytest.mark.parametrize("reise", ["beispielreise", "stadtwochenende"])
def test_alte_und_neue_form_bauen_gleich(tmp_path, reise):
    """Eine Reise mit alten festen Feldern baut unverändert; nach nachziehen stehen dieselben Werte in merkmale:, die Seite ist gleich."""
    q = kopie(tmp_path, reise)
    alte_form(q, EXTRA if reise == "beispielreise" else None)
    roh_alt = yaml.safe_load((q / "plan" / "routen.yaml").read_text(encoding="utf-8"))
    assert any(f in d for g in ("orte", "strecken", "unterkuenfte", "aufenthalte") for d in roh_alt[g].values() for f in ALT)
    alt = bauen.bauen(q, tmp_path / "wa" / "x")
    meldungen = neu.nachziehen(q)
    assert any("typisiert" in m for m in meldungen)
    roh = yaml.safe_load((q / "plan" / "routen.yaml").read_text(encoding="utf-8"))
    for g in ("orte", "strecken", "unterkuenfte", "aufenthalte"):
        for did, d in roh[g].items():
            assert not [f for f in ALT if f in d and not (f == "an" and routen.ist_eltern(d[f]))], (did, d)
    neu_ = bauen.bauen(q, tmp_path / "wb" / "x")
    assert route_ohne_katalog(alt) == route_ohne_katalog(neu_)
    assert neu.nachziehen(q) == []   # zweimal nichts zu tun


def test_nachziehen_gibt_herkunft_und_pruefdatum_weiter(tmp_path):
    q = kopie(tmp_path)
    alte_form(q, EXTRA)
    neu.nachziehen(q)
    roh = yaml.safe_load((q / "plan" / "routen.yaml").read_text(encoding="utf-8"))
    mk = roh["orte"]["O-03"]["merkmale"]["koordinaten"]
    assert mk["typ"] == "koordinaten" and mk["wert"] == [50.96, 14.07] and mk["quelle"] == "erfunden (Beispiel)" and str(mk["geprueft"]) == "2026-11-01"
    link = roh["unterkuenfte"]["U-02"]["merkmale"]["buchungslink"]
    assert (link["typ"], link["rolle"], link["wert"]) == ("link", "buchung", "https://burgblick.example/buchen")
    assert link["quelle"] == roh["unterkuenfte"]["U-02"]["quelle"]   # Herkunft des Dings, wo die Aussage keine hatte
    z = roh["aufenthalte"]["A-01"]["merkmale"]["zeitraum"]
    assert (z["typ"], z["wert"]) == ("zeitraum", {"beginn": "16:00", "ende": "18:00"})


def test_name_ist_gleich_nur_typ_und_rolle_zaehlen(tmp_path):
    """Die Software liest Typ und Rolle, nie den Namen des Merkmals."""
    q = kopie(tmp_path)
    routen_umbenennen = lambda t: t.replace("      zeitraum: {typ: zeitraum", "      meine_zeiten: {typ: zeitraum")
    datei = q / "plan" / "routen.yaml"
    datei.write_text(routen_umbenennen(datei.read_text(encoding="utf-8")), encoding="utf-8")
    d = bauen.bauen(q, tmp_path / "web" / "x")
    assert d["route"]["aufenthalte"]["A-01"]["beginn"] == "16:00" and "meine_zeiten" not in d["route"]["aufenthalte"]["A-01"]["merkmale"]


@pytest.mark.parametrize("alt, neu_, schluessel", [
    ('{typ: zeitraum, wert: {beginn: "16:00", ende: "18:00"}', '{typ: zeitraum, wert: {beginn: "16 Uhr"}', "pruefung.routen.lage_wert"),
    ('{typ: adresse, wert: "Terrassenufer 1, 01067 Dresden"', '{typ: adresse, wert: ""', "pruefung.routen.lage_wert"),
    ('{typ: adresse, wert: "Terrassenufer 1, 01067 Dresden"', '{typ: adresse, wert: 5', "pruefung.routen.lage_wert"),
    ('{typ: zeitraum, wert: {beginn: "16:00", ende: "18:00"}', '{typ: uhrzeit, wert: "16:00"', "pruefung.routen.lage_rolle"),
])
def test_form_der_typisierten_merkmale_wird_geprueft(tmp_path, alt, neu_, schluessel):
    q = kopie(tmp_path)
    datei = q / "plan" / "routen.yaml"
    t = datei.read_text(encoding="utf-8")
    assert alt in t
    datei.write_text(t.replace(alt, neu_), encoding="utf-8")
    with pytest.raises(bauen.BauFehler) as e:
        bauen.bauen(q, tmp_path / "web" / "x")
    assert meldet(e.value.args[0], schluessel)


def test_feld_und_merkmal_zugleich_ist_ein_fehler(tmp_path):
    q = kopie(tmp_path)
    datei = q / "plan" / "routen.yaml"
    t = datei.read_text(encoding="utf-8")
    datei.write_text(t.replace("    name: Burg Hohnstein\n", '    name: Burg Hohnstein\n    beginn: "09:00"\n', 1), encoding="utf-8")
    with pytest.raises(bauen.BauFehler) as e:
        bauen.bauen(q, tmp_path / "web" / "x")
    assert meldet(e.value.args[0], "pruefung.routen.lage_doppelt")


def test_merkmal_der_art_mit_neuem_typ_wird_geprueft_und_gezeigt(tmp_path):
    """Die Reise darf ein gewöhnliches Merkmal mit einem der neuen Typen definieren (zweite Adresse); es zeigt sich als Merkmal."""
    q = kopie(tmp_path)
    arten = q / "plan" / "arten.yaml"
    a = yaml.safe_load(arten.read_text(encoding="utf-8"))
    a["arten"]["hotel"]["merkmale"]["parkplatz"] = {"name": "Parkplatz", "typ": "adresse", "stufe": "angeboten"}
    arten.write_text(yaml.safe_dump(a, allow_unicode=True, sort_keys=False), encoding="utf-8")
    datei = q / "plan" / "routen.yaml"
    t = datei.read_text(encoding="utf-8")
    datei.write_text(t.replace("      fruehstueck: {wert: inklusive", '      parkplatz: {wert: "Elbstraße 2, Dresden", quelle: "erfunden (Beispiel)"}\n      fruehstueck: {wert: inklusive', 1), encoding="utf-8")
    d = bauen.bauen(q, tmp_path / "web" / "x")
    w = d["route"]["unterkuenfte"]["U-01"]["merkmale"]["parkplatz"]
    assert w["typ"] == "adresse" and w["wert"] == "Elbstraße 2, Dresden"
    datei.write_text(datei.read_text(encoding="utf-8").replace('wert: "Elbstraße 2, Dresden"', "wert: 7"), encoding="utf-8")
    with pytest.raises(bauen.BauFehler) as e:
        bauen.bauen(q, tmp_path / "web2" / "x")
    assert meldet(e.value.args[0], "pruefung.routen.lage_wert")


# ---------- Schreibweg ----------

def test_item_create_mit_merkmalen_legt_die_lage_an(repo):
    _, origin, _, _ = repo
    s = schreiber(repo)
    s.schreiben("beispielreise", "ding_anlegen", {**KARL, "args": {
        "was": "aufenthalt", "titel": "Bäckerei am Markt", "ort": "O-03", "art": "besichtigung", "quelle": "Beispiel",
        "merkmale": {"adresse": "Am Markt 1, Hohnstein", "koordinaten": [50.97, 14.1], "zeitraum": "07:00-12:00"}}})
    r, _ = routen_auf_main(origin)
    a = next(x for x in r["aufenthalte"].values() if x["name"] == "Bäckerei am Markt")
    assert "adresse" not in a and "punkt" not in a and "beginn" not in a
    mk = a["merkmale"]
    assert mk["adresse"]["typ"] == "adresse" and mk["adresse"]["quelle"] == "Beispiel"
    assert mk["koordinaten"]["wert"] == [50.97, 14.1]
    assert mk["zeitraum"]["wert"] == {"beginn": "07:00", "ende": "12:00"}


def test_item_create_ohne_quelle_und_falsche_form_werden_abgelehnt(repo):
    s = schreiber(repo)
    basis = {"was": "aufenthalt", "titel": "X", "ort": "O-03", "art": "besichtigung"}
    with pytest.raises(sb.Ablehnung) as e:
        s.schreiben("beispielreise", "ding_anlegen", {**KARL, "args": {**basis, "merkmale": {"adresse": "Am Markt 1"}}})
    assert "quelle" in str(e.value)
    for merkmale in ({"koordinaten": "keine Zahl"}, {"zeitraum": "morgens"}, {"gpx": "x"}):
        with pytest.raises(sb.Ablehnung):
            s.schreiben("beispielreise", "ding_anlegen", {**KARL, "args": {**basis, "quelle": "q", "merkmale": merkmale}})
        s.vorbereiten()


def test_lage_eintragen_ersetzt_das_merkmal(repo):
    _, origin, _, _ = repo
    s = schreiber(repo)
    s.schreiben("beispielreise", "lage_eintragen", {**KARL, "args": {"ziel": "U-02", "koordinaten": "50.97, 14.1", "adresse": "Am Markt 3", "quelle": "Beispiel"}})
    r, _ = routen_auf_main(origin)
    u = r["unterkuenfte"]["U-02"]
    assert u["merkmale"]["koordinaten"]["wert"] == [50.97, 14.1] and u["merkmale"]["adresse"]["wert"] == "Am Markt 3"
    s.vorbereiten()
    s.schreiben("beispielreise", "lage_eintragen", {**KARL, "args": {"ziel": "U-02", "koordinaten": "50.98, 14.2", "quelle": "Beispiel 2"}})
    r, _ = routen_auf_main(origin)
    k = r["unterkuenfte"]["U-02"]["merkmale"]["koordinaten"]
    assert k["wert"] == [50.98, 14.2] and k["quelle"] == "Beispiel 2"
    assert sum(1 for v in r["unterkuenfte"]["U-02"]["merkmale"].values() if isinstance(v, dict) and v.get("typ") == "koordinaten") == 1


def test_item_update_zeiten_und_link_als_merkmale(repo):
    _, origin, _, _ = repo
    s = schreiber(repo)
    s.schreiben("beispielreise", "ding_aendern", {**KARL, "args": {"ziel": "E-20", "ab": "08:15", "an": "08:45"}})
    r, _ = routen_auf_main(origin)
    e = r["strecken"]["E-20"]
    assert "ab" not in e and e["merkmale"]["abfahrt"]["wert"] == "08:15" and e["merkmale"]["ankunft"]["wert"] == "08:45"
    s.vorbereiten()
    s.schreiben("beispielreise", "ding_aendern", {**KARL, "args": {"ziel": "U-02", "buchungslink": "https://burgblick.example"}})
    r, _ = routen_auf_main(origin)
    assert r["unterkuenfte"]["U-02"]["merkmale"]["buchungslink"]["rolle"] == "buchung" and "buchungslink" not in r["unterkuenfte"]["U-02"]
    s.vorbereiten()
    s.schreiben("beispielreise", "ding_aendern", {**KARL, "args": {"ziel": "U-02", "buchungslink": ""}})
    r, _ = routen_auf_main(origin)
    assert "buchungslink" not in r["unterkuenfte"]["U-02"].get("merkmale", {})
