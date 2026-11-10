"""Tests für die Packliste (ADR-0010, Issue #370): Gegenstand als Grundform (G-…), Kategorien als Arten, Summen je Merkmal,
Schreibweg, Übernahme aus einer früheren Reise, Packstand beim Rückmeldedienst, Konnektor. Gegen beide Beispielreisen
(Wanderung mit Gewicht und Raum, Städtewochenende ohne beides)."""
import datetime
import functools
import http.server
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bauen  # noqa: E402
import konnektor as kn  # noqa: E402
import packliste  # noqa: E402
import reise as rg  # noqa: E402
import konten  # noqa: E402
import rueckmeldungen as rm  # noqa: E402
import schreiben as sb  # noqa: E402
from conftest import meldet  # noqa: E402
from playwright_pfad import PLAYWRIGHT  # noqa: E402
from test_konnektor import ALT_ORGANISATOR, GAST, KARL, dienst, rpc, schreibweg, seiten, werkzeug, Schreibweg  # noqa: E402,F401
from test_regeln import anfrage, umgebung  # noqa: E402,F401  (umgebung: Fixture)

WURZEL = Path(__file__).resolve().parent.parent.parent
WANDERUNG = WURZEL / "beispiel" / "reisen" / "beispielreise"
STADT = WURZEL / "beispiel" / "reisen" / "stadtwochenende"
IDA = {"name": "Ida", "rolle": "organisator"}
KARL_ = {"name": "Karl", "rolle": "mitwirkend"}


def bau(ordner):
    with tempfile.TemporaryDirectory() as t:
        return bauen.Bauer(ordner, t).daten()


def meldungen_beim_bau(ordner):
    with tempfile.TemporaryDirectory() as t:
        with pytest.raises(bauen.BauFehler) as e:
            bauen.Bauer(ordner, t).daten()
    return e.value.meldungen


@pytest.fixture
def wanderung(tmp_path):
    ziel = tmp_path / "beispielreise"
    shutil.copytree(WANDERUNG, ziel)
    return ziel


@pytest.fixture
def stadt(tmp_path):
    ziel = tmp_path / "stadtwochenende"
    shutil.copytree(STADT, ziel)
    return ziel


def packdatei(ordner, **aenderungen):
    """packliste.yaml der Kopie: aenderungen sind (id -> Felder) oder eine neue Liste (gegenstaende=[…])."""
    p = ordner / "plan" / "packliste.yaml"
    roh = yaml.safe_load(p.read_text(encoding="utf-8"))
    if "gegenstaende" in aenderungen:
        roh["gegenstaende"] = aenderungen["gegenstaende"]
    for gid, felder in aenderungen.items():
        if gid == "gegenstaende":
            continue
        g = next(x for x in roh["gegenstaende"] if x["id"] == gid)
        for k, v in felder.items():
            if v is None:
                g.pop(k, None)
            else:
                g[k] = v
    p.write_text(yaml.safe_dump(roh, allow_unicode=True, sort_keys=False), encoding="utf-8")


# ---------- Modell und Bau ----------

def test_beispielreise_wanderung_kategorien_summen_und_bezug():
    d = bau(WANDERUNG)["packliste"]
    assert [k["art"] for k in d["kategorien"]] == ["kleidung", "ausruestung", "apotheke"]
    je = {g["id"]: g for g in d["gegenstaende"]}
    # Gewicht (zahl, g) und Anschaffung (geld) sind zwei summierte Merkmale einer Art; weggelassene zählen nicht mit
    summen = {k["art"]: {s["merkmal"]: s["summen"] for s in k["summen"]} for k in d["kategorien"]}
    assert summen["kleidung"] == {"gewicht": [{"wert": 1560.0, "einheit": "g"}]}
    assert summen["ausruestung"] == {"gewicht": [{"wert": 750.0, "einheit": "g"}], "preis": [{"wert": 70.0, "einheit": "€"}]}
    assert summen["apotheke"] == {"gewicht": [{"wert": 380.0, "einheit": "g"}]}      # ohne die Sonnencreme (entfaellt)
    assert {(s["merkmal"], s["einheit"]): s["wert"] for s in d["summen"]} == {("gewicht", "g"): 2690.0, ("preis", "€"): 70.0}
    assert je["G-09"]["status"] == "entfaellt" and je["G-01"]["status"] == "aktiv"
    # ein gemeinsamer Gegenstand mit wer, einer an einer Strecke, einer an einer Unterkunft
    assert je["G-07"]["wer"] == "Ida" and je["G-05"]["an"] == "E-01" and je["G-05"]["an_name"].startswith("Stadt Wehlen")
    assert je["G-06"]["an"] == "U-04"
    # Merkmale tragen Typ und Einheit der Art; die Rolle summe steht am Merkmal
    gewicht = next(m for m in d["kategorien"][0]["merkmale"] if m["id"] == "gewicht")
    assert gewicht["summe"] is True and gewicht["einheit"] == "g"
    assert "summe" not in next(m for m in d["kategorien"][0]["merkmale"] if m["id"] == "raum")


def test_beispielreise_stadtwochenende_ohne_gewicht_und_raum():
    d = bau(STADT)["packliste"]
    assert [k["art"] for k in d["kategorien"]] == ["papiere", "kleidung"]
    assert d["summen"] == [] and all(not k["summen"] for k in d["kategorien"])
    assert not any(m["id"] in ("gewicht", "raum") for k in d["kategorien"] for m in k["merkmale"])
    je = {g["id"]: g for g in d["gegenstaende"]}
    assert je["G-01"]["an"] == "E-01" and je["G-03"]["an"] == "A-01" and je["G-02"]["wer"] == "Lea"


def test_reise_ohne_packliste_hat_keine():
    # beide Beispielreisen haben eine; eine Reise ohne Art mit Grundform gegenstand und ohne Datei baut ohne
    with tempfile.TemporaryDirectory() as t:
        ziel = Path(t) / "r"
        shutil.copytree(STADT, ziel)
        (ziel / "plan" / "packliste.yaml").unlink()
        arten = yaml.safe_load((ziel / "plan" / "arten.yaml").read_text(encoding="utf-8"))
        arten["arten"] = {k: v for k, v in arten["arten"].items() if v["grundform"] != "gegenstand"}
        (ziel / "plan" / "arten.yaml").write_text(yaml.safe_dump(arten, allow_unicode=True, sort_keys=False), encoding="utf-8")
        assert bau(ziel)["packliste"] is None


@pytest.mark.parametrize("aenderung, schluessel", [
    ({"G-01": {"art": "hotel"}}, "pruefung.packliste.art"),
    ({"G-01": {"art": "gibtsnicht"}}, "pruefung.packliste.art"),
    ({"G-01": {"titel": ""}}, "pruefung.packliste.titel"),
    ({"G-01": {"an": "T-01"}}, "pruefung.packliste.an_art"),
    ({"G-01": {"an": "W-01"}}, "pruefung.packliste.an_art"),
    ({"G-01": {"an": "E-99"}}, "pruefung.packliste.an_unbekannt"),
    ({"G-01": {"wer": "Niemand"}}, "pruefung.packliste.wer"),
    ({"G-01": {"status": "weg"}}, "pruefung.packliste.status"),
    ({"G-01": {"unbekannt": 1}}, "pruefung.packliste.felder"),
    ({"G-01": {"verlauf": [{"wer": "Ida"}]}}, "pruefung.packliste.verlauf"),
    ({"G-01": {"merkmale": {"gibtsnicht": 1}}}, "pruefung.routen.83"),
    ({"G-01": {"merkmale": {"gewicht": "viel"}}}, "pruefung.routen.90"),
    ({"G-01": {"merkmale": {"raum": "Keller"}}}, "pruefung.routen.89"),
])
def test_bau_lehnt_unstimmiges_ab(wanderung, aenderung, schluessel):
    packdatei(wanderung, **aenderung)
    assert meldet(meldungen_beim_bau(wanderung), schluessel)


def test_bau_doppelte_id_und_form(wanderung):
    liste = yaml.safe_load((wanderung / "plan" / "packliste.yaml").read_text(encoding="utf-8"))["gegenstaende"]
    packdatei(wanderung, gegenstaende=liste + [dict(liste[0])])
    assert meldet(meldungen_beim_bau(wanderung), "pruefung.packliste.doppelt")
    packdatei(wanderung, gegenstaende=[{"id": "X-1", "art": "kleidung", "titel": "x"}])
    assert meldet(meldungen_beim_bau(wanderung), "pruefung.packliste.id")


def test_gegenstand_an_verworfener_option_wird_gemeldet_und_markiert(wanderung):
    packdatei(wanderung, **{"G-06": {"an": "U-03"}})     # U-03 steht nur in der verworfenen Option V-03.b
    d = bau(wanderung)
    g = next(x for x in d["packliste"]["gegenstaende"] if x["id"] == "G-06")
    assert g["an_verworfen"] is True
    assert meldet([w["text"] for w in d["route"]["warnungen"]], "pruefung.packliste.an_verworfen")
    assert not next(x for x in d["packliste"]["gegenstaende"] if x["id"] == "G-05").get("an_verworfen")


def test_veraenderliches_merkmal_behaelt_pruefdatum(wanderung):
    arten = yaml.safe_load((wanderung / "plan" / "arten.yaml").read_text(encoding="utf-8"))
    arten["arten"]["ausruestung"]["merkmale"]["preis"]["veraenderlich"] = True
    (wanderung / "plan" / "arten.yaml").write_text(yaml.safe_dump(arten, allow_unicode=True, sort_keys=False), encoding="utf-8")
    d = bau(wanderung)
    preis = next(g for g in d["packliste"]["gegenstaende"] if g["id"] == "G-05")["merkmale"]["preis"]
    assert preis["ungeprueft"] is True            # ohne Prüfdatum, aber ohne Quelle: kein Fehler
    packdatei(wanderung, **{"G-05": {"merkmale": {"gewicht": 480, "preis": {"wert": "45 €", "geprueft": datetime.date(2026, 11, 1)}, "raum": "Rucksack"}}})
    assert next(g for g in bau(wanderung)["packliste"]["gegenstaende"] if g["id"] == "G-05")["merkmale"]["preis"]["ungeprueft"] is False


# ---------- Rolle summe ----------

def test_rolle_summe_und_alias_kosten():
    import routen
    assert routen.rolle_typen("summe") == ("zahl", "geld") and routen.rolle_typen("kosten") == ("geld",)
    assert "summe" in routen.ROLLEN_MEHRFACH and "kosten" not in routen.ROLLEN_MEHRFACH
    # kosten (Alias) wird weiter als Preis der Nacht gelesen; ein summe-Merkmal vom Typ geld ebenso
    a = bau(WANDERUNG)["route"]["arten"]
    assert a["hotel"]["kosten"] == "preis" and a["hotel"].get("summen") == ["preis"]
    assert a["ausruestung"]["kosten"] == "preis" and a["ausruestung"]["summen"] == ["gewicht", "preis"]
    assert a["kleidung"]["kosten"] is None and a["kleidung"]["summen"] == ["gewicht"]


def test_rolle_summe_braucht_zahl_oder_geld_und_darf_mehrfach_sein(wanderung):
    arten = yaml.safe_load((wanderung / "plan" / "arten.yaml").read_text(encoding="utf-8"))
    arten["arten"]["kleidung"]["merkmale"]["anzahl"]["rolle"] = "summe"      # zwei summe-Merkmale: erlaubt
    (wanderung / "plan" / "arten.yaml").write_text(yaml.safe_dump(arten, allow_unicode=True, sort_keys=False), encoding="utf-8")
    assert [s["merkmal"] for s in bau(wanderung)["packliste"]["kategorien"][0]["summen"]] == ["gewicht", "anzahl"]
    arten["arten"]["kleidung"]["merkmale"]["raum"]["rolle"] = "summe"        # auswahl: nicht erlaubt
    (wanderung / "plan" / "arten.yaml").write_text(yaml.safe_dump(arten, allow_unicode=True, sort_keys=False), encoding="utf-8")
    assert meldet(meldungen_beim_bau(wanderung), "pruefung.routen.78")
    with pytest.raises(sb.Ablehnung):
        sb.rolle_pruefen({}, "raum", "summe", "auswahl")
    sb.rolle_pruefen({"gewicht": {"rolle": "summe"}}, "preis", "summe", "geld")      # zweite summe: keine Ablehnung
    with pytest.raises(sb.Ablehnung):                                                # kosten bleibt einmalig
        sb.rolle_pruefen({"preis": {"rolle": "kosten"}}, "betrag", "kosten", "geld")


def test_summen_mit_geld_in_zwei_waehrungen_und_unlesbaren_werten():
    gs = [{"id": "G-1", "merkmale": {"preis": {"wert": "35 €"}}}, {"id": "G-2", "merkmale": {"preis": {"wert": "12,50 €"}}},
          {"id": "G-3", "merkmale": {"preis": {"wert": "1.200 CHF"}}}, {"id": "G-4", "merkmale": {"preis": {"wert": "gratis"}}},
          {"id": "G-5", "status": "entfaellt", "merkmale": {"preis": {"wert": "99 €"}}}]
    s, unleserlich = packliste.summieren(gs, {"id": "preis", "typ": "geld"})
    assert {z["einheit"]: z["wert"] for z in s} == {"€": 47.5, "CHF": 1200.0} and unleserlich == 1
    assert packliste.zahl_text(47.5, "de") == "47,5" and packliste.zahl_text(1200, "en") == "1200"
    assert packliste.betrag("ca. 30–40 €") is None and packliste.betrag("80 €/Nacht") == (80.0, "€")


# ---------- Regeln (Rollen, Bausteine, Status) ----------

def test_regeln_rollen_baustein_und_status():
    alle = rg.BAUSTEINE
    for aktion in ("gegenstand", "packen"):
        assert rg.erlaubt(aktion, "mitwirkend", "planung", alle)[0] and rg.erlaubt(aktion, "organisator", "planung", alle)[0]
        assert not rg.erlaubt(aktion, "gast", "planung", alle)[0]
        assert not rg.erlaubt(aktion, "mitwirkend", "planung", [b for b in alle if b != "packliste"])[0]
        # in jedem Status schreibbar, auch unterwegs; in der Nachlese ebenfalls, im Archiv nicht
        for status in ("idee", "planung", "fest", "unterwegs", "danach"):
            assert rg.erlaubt(aktion, "mitwirkend", status, alle)[0], (aktion, status)
        assert not rg.erlaubt(aktion, "mitwirkend", "archiv", alle)[0]
    assert rg.erlaubt("packliste_uebernehmen", "organisator", "planung", alle)[0]
    assert not rg.erlaubt("packliste_uebernehmen", "mitwirkend", "planung", alle)[0]
    assert "packliste" in rg.BAUSTEINE and rg.LESE_BAUSTEIN["packliste"] == "packliste"


# ---------- Schreibweg ----------

def test_gegenstand_anlegen_schreibt_mit_neuer_id_und_verlauf(wanderung):
    titel, text = sb.gegenstand_anlegen(wanderung, KARL_, {"art": "kleidung", "titel": "Mütze",
                                                           "merkmale": {"gewicht": 60, "raum": "Rucksack"}, "an": "E-02", "wer": "karl"})
    assert titel.startswith("G-10 Mütze")           # die ID steht am Anfang des Titels: der Schreibweg gibt sie an den Konnektor
    g = yaml.safe_load((wanderung / "plan" / "packliste.yaml").read_text(encoding="utf-8"))["gegenstaende"][-1]
    assert g["id"] == "G-10" and g["art"] == "kleidung" and g["merkmale"] == {"gewicht": 60, "raum": "Rucksack"}
    assert g["an"] == "E-02" and g["wer"] == "Karl"
    assert g["verlauf"][0]["wer"] == "Karl" and g["verlauf"][0]["was"] == "angelegt"
    assert "quelle" not in g and "quelle" not in g["merkmale"]     # Ausnahme von der Herkunftspflicht
    assert bau(wanderung)["packliste"]["gegenstaende"][-1]["id"] == "G-10"


@pytest.mark.parametrize("args, schluessel", [
    ({"art": "gibtsnicht", "titel": "x"}, "schreiben.gegenstand.art_unbekannt"),
    ({"art": "hotel", "titel": "x"}, "schreiben.gegenstand.art_unbekannt"),             # Art mit anderer Grundform
    ({"art": "kleidung", "titel": "x", "an": "T-01"}, "schreiben.gegenstand.an_form"),   # kein Tag
    ({"art": "kleidung", "titel": "x", "an": "E-99"}, "schreiben.gegenstand.an_unbekannt"),
    ({"art": "kleidung", "titel": "x", "wer": "Niemand"}, "schreiben.gegenstand.wer_unbekannt"),
    ({"art": "kleidung", "titel": "x", "merkmale": {"raum": "Keller"}}, "schreiben.wert_eintraege.2"),
    ({"art": "kleidung", "titel": "x", "merkmale": {"gewicht": "viel"}}, "schreiben.wert_eintraege.3"),
    ({"art": "kleidung", "titel": "x", "merkmale": {"farbe": "rot"}}, "schreiben.merkmale_werte.1"),
    ({"art": "kleidung", "titel": "x", "merkmale": {"gewicht": [{"wert": 1, "gilt": "2027-05-13"}]}}, "schreiben.gegenstand.gilt"),
])
def test_gegenstand_anlegen_lehnt_ab(wanderung, args, schluessel):
    vorher = (wanderung / "plan" / "packliste.yaml").read_text(encoding="utf-8")
    with pytest.raises(sb.Ablehnung) as e:
        sb.gegenstand_anlegen(wanderung, IDA, args)
    assert e.value.schluessel == schluessel
    assert (wanderung / "plan" / "packliste.yaml").read_text(encoding="utf-8") == vorher


def test_gegenstand_anlegen_ohne_kategorie_und_name_statt_schluessel(stadt):
    # Name der Kategorie statt Schlüssel; Kategorie ohne Merkmale
    sb.gegenstand_anlegen(stadt, IDA, {"art": "Papiere", "titel": "Reiseführer"})
    (stadt / "plan" / "packliste.yaml").unlink()
    arten = yaml.safe_load((stadt / "plan" / "arten.yaml").read_text(encoding="utf-8"))
    arten["arten"] = {k: v for k, v in arten["arten"].items() if v["grundform"] != "gegenstand"}
    (stadt / "plan" / "arten.yaml").write_text(yaml.safe_dump(arten, allow_unicode=True, sort_keys=False), encoding="utf-8")
    with pytest.raises(sb.Ablehnung) as e:
        sb.gegenstand_anlegen(stadt, IDA, {"art": "papiere", "titel": "x"})
    assert e.value.schluessel == "schreiben.gegenstand.keine_arten"


def test_gegenstand_anlegen_in_reise_ohne_datei(stadt):
    (stadt / "plan" / "packliste.yaml").unlink()
    sb.gegenstand_anlegen(stadt, IDA, {"art": "papiere", "titel": "Ausweis"})
    text = (stadt / "plan" / "packliste.yaml").read_text(encoding="utf-8")
    assert text.startswith("#") and "gegenstaende:" in text and bau(stadt)["packliste"]["gegenstaende"][0]["id"] == "G-01"


def test_gegenstand_aendern_verlauf_merkmale_und_weglassen(wanderung):
    sb.gegenstand_aendern(wanderung, IDA, {"ziel": "G-01", "titel": "Regenjacke (neu)", "merkmale": {"gewicht": 380, "raum": ""},
                                           "notiz": "Gore-Tex", "grund": "neue Jacke"})
    g = next(x for x in yaml.safe_load((wanderung / "plan" / "packliste.yaml").read_text(encoding="utf-8"))["gegenstaende"] if x["id"] == "G-01")
    assert g["titel"] == "Regenjacke (neu)" and g["merkmale"] == {"gewicht": 380} and g["notiz"] == "Gore-Tex"
    assert g["verlauf"][-1]["wer"] == "Ida" and g["verlauf"][-1]["grund"] == "neue Jacke"
    assert list(g)[-1] == "verlauf"                                   # der Verlauf bleibt am Ende des Eintrags
    # Weglassen braucht einen Grund, löscht nie und lässt sich zurückholen
    with pytest.raises(sb.Ablehnung) as e:
        sb.gegenstand_aendern(wanderung, IDA, {"ziel": "G-01", "status": "entfaellt"})
    assert e.value.schluessel == "schreiben.gegenstand.status_grund"
    titel, text = sb.gegenstand_aendern(wanderung, IDA, {"ziel": "G-01", "status": "entfaellt", "grund": "bleibt zu Hause"})
    assert meldet(text, "schreiben.antwort.gegenstand.nicht_geloescht")
    d = bau(wanderung)["packliste"]
    assert next(x for x in d["gegenstaende"] if x["id"] == "G-01")["status"] == "entfaellt"
    assert {s["merkmal"]: s["summen"][0]["wert"] for k in d["kategorien"] if k["art"] == "kleidung" for s in k["summen"]} == {"gewicht": 1140.0}
    sb.gegenstand_aendern(wanderung, IDA, {"ziel": "G-01", "status": "aktiv", "grund": "doch"})
    assert next(x for x in bau(wanderung)["packliste"]["gegenstaende"] if x["id"] == "G-01")["status"] == "aktiv"
    with pytest.raises(sb.Ablehnung) as e:
        sb.gegenstand_aendern(wanderung, IDA, {"ziel": "G-01", "titel": "Regenjacke (neu)"})   # nichts zu ändern
    assert e.value.schluessel == "schreiben.gegenstand.nichts_geaendert"


def test_gegenstand_aendern_mitwirkende_nur_eigene(wanderung):
    # G-06 hat Karl angelegt, G-07 ist Ida zugewiesen, G-01 gehört Ida
    sb.gegenstand_aendern(wanderung, KARL_, {"ziel": "G-06", "notiz": "mit Ersatzbatterie"})
    with pytest.raises(sb.Ablehnung) as e:
        sb.gegenstand_aendern(wanderung, KARL_, {"ziel": "G-01", "notiz": "x"})
    assert e.value.schluessel == "schreiben.gegenstand.fremd"
    sb.gegenstand_aendern(wanderung, IDA, {"ziel": "G-06", "wer": "karl", "grund": "Karl nimmt sie mit"})
    sb.gegenstand_aendern(wanderung, KARL_, {"ziel": "G-06", "wer": ""})            # eigener Eintrag, auch zugewiesen: erlaubt
    sb.gegenstand_aendern(wanderung, IDA, {"ziel": "G-01", "wer": "karl", "grund": "x"})
    sb.gegenstand_aendern(wanderung, KARL_, {"ziel": "G-01", "notiz": "meins"})     # ihm zugewiesen: erlaubt


def test_gegenstand_aendern_kategorie_wechseln(wanderung):
    with pytest.raises(sb.Ablehnung) as e:
        sb.gegenstand_aendern(wanderung, IDA, {"ziel": "G-05", "art": "kleidung"})   # preis kennt kleidung nicht
    assert e.value.schluessel == "schreiben.gegenstand.art_merkmale"
    sb.gegenstand_aendern(wanderung, IDA, {"ziel": "G-05", "art": "kleidung", "merkmale": {"preis": ""}})


def test_gegenstand_an_bezug_aendern_und_loesen(wanderung):
    sb.gegenstand_aendern(wanderung, IDA, {"ziel": "G-05", "an": "U-01"})
    assert next(x for x in bau(wanderung)["packliste"]["gegenstaende"] if x["id"] == "G-05")["an"] == "U-01"
    sb.gegenstand_aendern(wanderung, IDA, {"ziel": "G-05", "an": ""})
    assert next(x for x in bau(wanderung)["packliste"]["gegenstaende"] if x["id"] == "G-05")["an"] is None
    with pytest.raises(sb.Ablehnung):
        sb.gegenstand_aendern(wanderung, IDA, {"ziel": "G-05", "an": "T-01"})


def test_ids_werden_nie_neu_vergeben(wanderung):
    sb.gegenstand_aendern(wanderung, IDA, {"ziel": "G-09", "status": "aktiv", "grund": "x"})
    sb.gegenstand_aendern(wanderung, IDA, {"ziel": "G-09", "status": "entfaellt", "grund": "y"})
    sb.gegenstand_anlegen(wanderung, IDA, {"art": "kleidung", "titel": "a"})
    sb.gegenstand_anlegen(wanderung, IDA, {"art": "kleidung", "titel": "b"})
    ids = [g["id"] for g in bau(wanderung)["packliste"]["gegenstaende"]]
    assert ids[-2:] == ["G-10", "G-11"] and len(ids) == len(set(ids))


def test_werkzeuge_haengen_am_schreibweg_mit_rolle_und_baustein():
    for w in ("gegenstand_anlegen", "gegenstand_aendern", "packliste_uebernehmen"):
        assert w in sb.WERKZEUGE and w in sb.AKTIONEN and sb.AKTIONEN[w] in rg.AKTIONEN
        assert w in kn.ONTOLOGIE_WERKZEUGE and kn.ONTOLOGIE_AKTION[w] == sb.AKTIONEN[w]


# ---------- Übernahme aus einer früheren Reise ----------

def test_packliste_uebernehmen_als_vorschlag(tmp_path):
    reisen = tmp_path / "reisen"
    alt, neu = reisen / "beispielreise", reisen / "stadtwochenende"
    shutil.copytree(WANDERUNG, alt)
    shutil.copytree(STADT, neu)
    # Die Stadtreise hat die Kategorie Kleidung schon (nur mit dem Merkmal Anzahl); Apotheke fehlt ihr und kommt mit
    titel, text = sb.packliste_uebernehmen(neu, IDA, {"von_reise": "beispielreise", "arten": ["kleidung", "apotheke"], "grund": "wie damals"})
    d = bau(neu)["packliste"]
    assert [g["id"] for g in d["gegenstaende"]] == ["G-01", "G-02", "G-03", "G-04", "G-05", "G-06", "G-07", "G-08", "G-09"]   # neue IDs nach den vorhandenen
    je_titel = {g["titel"]: g for g in d["gegenstaende"]}
    assert set(je_titel) - {"Fahrkarte hin und zurück", "Personalausweis", "Etwas Schickes fürs Abendessen", "Bequeme Schuhe"} == \
        {"Regenjacke", "Wanderschuhe", "Wandersocken", "Erste-Hilfe-Set", "Blasenpflaster"}   # ohne die weggelassene Sonnencreme
    neue = [g for g in d["gegenstaende"] if g["id"] >= "G-05"]
    assert all(g["an"] is None and g["wer"] is None for g in neue)   # ohne Bezug (E-01 gibt es hier nicht) und ohne Person (Ida packt das Erste-Hilfe-Set)
    assert "apotheke" in [k["art"] for k in d["kategorien"]]                     # die fehlende Kategorie kommt mit
    # das Merkmal Gewicht gibt es in der vorhandenen Kategorie Kleidung der Stadtreise nicht: der Wert entfällt, das steht in der Antwort
    assert "gewicht" not in je_titel["Regenjacke"]["merkmale"] and meldet(text, "schreiben.antwort.packliste.verloren")
    assert je_titel["Wandersocken"]["merkmale"]["anzahl"]["wert"] == "3" and "gewicht" in je_titel["Blasenpflaster"]["merkmale"]
    assert je_titel["Regenjacke"]["verlauf"][0]["wer"] == "Ida" and "beispielreise" in je_titel["Regenjacke"]["verlauf"][0]["was"]
    # ein zweites Mal gibt es nur noch Gegenstände (die Kategorien sind da)
    with pytest.raises(sb.Ablehnung) as e:
        sb.packliste_uebernehmen(neu, IDA, {"von_reise": "beispielreise", "arten": ["gibtsnicht"]})
    assert e.value.schluessel == "schreiben.packliste_uebernehmen.3"
    with pytest.raises(sb.Ablehnung) as e:
        sb.packliste_uebernehmen(neu, IDA, {"von_reise": "stadtwochenende"})
    assert e.value.schluessel == "schreiben.packliste_uebernehmen.1"
    with pytest.raises(sb.Ablehnung) as e:
        sb.packliste_uebernehmen(neu, IDA, {"von_reise": "gibtsnicht"})
    assert e.value.schluessel == "schreiben.packliste_uebernehmen.2"


# ---------- Packstand beim Rückmeldedienst ----------

def haken(u, name, gepackt, methode="PATCH", pfad="packstand"):
    import urllib.error
    import urllib.request
    import konten
    req = urllib.request.Request(f"{u.rurl}/beispielreise/{pfad}", data=json.dumps({"name": name, "gepackt": gepackt}).encode(), method=methode,
                                 headers={"Content-Type": "application/json", "X-Frieda-Dienst": konten.dienst_geheimnis()})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")


def stand(u):
    code, s = anfrage(f"{u.rurl}/beispielreise/packstand", methode="GET")
    assert code == 200
    return s


def test_packstand_abhaken_zuruecknehmen_und_je_person(umgebung):
    u = umgebung(bausteine=["packliste"])
    assert stand(u) == {}
    code, s = haken(u, "Karl", {"G-01": True, "G-02": True})
    assert code == 200 and set(s) == {"G-01", "G-02"} and list(s["G-01"]) == ["Karl"]
    assert haken(u, "Ida", {"G-01": True})[0] == 200
    assert sorted(stand(u)["G-01"]) == ["Ida", "Karl"]                       # ohne wer packt jede Person für sich
    zeit = stand(u)["G-02"]["Karl"]
    haken(u, "Karl", {"G-02": True})                                         # Nachreichen: nichts ändert sich
    assert stand(u)["G-02"]["Karl"] == zeit
    assert haken(u, "Karl", {"G-01": False, "G-02": False})[0] == 200
    assert stand(u) == {"G-01": {"Ida": stand(u)["G-01"]["Ida"]}}            # ohne Haken verschwindet der Eintrag
    assert haken(u, "Karl", True, pfad="packstand/G-03")[0] == 200            # ein Gegenstand über seine Adresse
    assert "Karl" in stand(u)["G-03"]


def test_packstand_pruefungen(umgebung):
    u = umgebung(bausteine=["packliste"])
    for falsch in ({}, {"X-1": True}, {"G-01": "ja"}, [], "G-01", {"G-01": 1}):
        assert haken(u, "Karl", falsch)[0] == 400, falsch
    assert haken(u, "Karl", {f"G-{i:02d}": True for i in range(1, 502)})[0] == 400
    assert haken(u, "", {"G-01": True})[0] == 400                              # ohne Name
    assert stand(u) == {}


def test_packstand_rechte_nach_rolle_baustein_und_status(umgebung):
    u = umgebung(bausteine=["packliste"])
    assert haken(u, "Kim", {"G-01": True})[0] == 403                           # Kim ist Gast (reist nur mit und liest)
    u2 = umgebung(bausteine=["fragen"])
    code, f = haken(u2, "Karl", {"G-01": True})
    assert code == 403 and "packliste" in f["fehler"]                          # Baustein aus
    assert haken(umgebung(status="unterwegs", bausteine=["packliste"]), "Karl", {"G-01": True})[0] == 200
    assert haken(umgebung(status="danach", bausteine=["packliste"]), "Karl", {"G-01": True})[0] == 200
    assert haken(umgebung(status="archiv", bausteine=["packliste"]), "Karl", {"G-01": True})[0] == 403


def test_packstand_gegenstand_mit_wer_und_weggelassene(umgebung):
    u = umgebung(bausteine=["packliste"])
    veroeffentlicht = u.seiten / "beispielreise" / "daten.json"
    d = json.loads(veroeffentlicht.read_text(encoding="utf-8"))
    d["packliste"] = bau(WANDERUNG)["packliste"]
    veroeffentlicht.write_text(json.dumps(d, default=str), encoding="utf-8")
    code, f = haken(u, "Karl", {"G-07": True})                                 # G-07 packt Ida
    assert code == 403 and "Ida" in f["fehler"]
    assert haken(u, "Ida", {"G-07": True})[0] == 200
    assert haken(u, "Karl", {"G-07": False})[0] == 200                         # Zurücknehmen des eigenen (nicht vorhandenen) Hakens: harmlos
    assert haken(u, "Karl", {"G-09": True})[0] == 409                          # weggelassen
    assert haken(u, "Karl", {"G-99": True})[0] == 200                          # noch nicht veröffentlicht: wird angenommen


def test_packstand_text_zaehlt_pro_person():
    p = bau(WANDERUNG)["packliste"]
    stand_ = {"G-01": {"Karl": "z"}, "G-07": {"Ida": "z"}, "G-09": {"Karl": "z"}}
    # aktive Gegenstände: 8; G-07 hat wer Ida, der Rest zählt für jede Person
    assert packliste.packstand_zeilen(p, stand_, "Karl") == (1, 7)      # G-07 packt Ida: kein Gegenstand von Karl
    assert packliste.packstand_zeilen(p, stand_, "Ida") == (1, 8)       # G-07 und alle ohne wer; Karls Haken zählen für Ida nicht
    assert packliste.packstand_zeilen(p, stand_, None) == (1, 1)        # ohne Person zählen nur die zugewiesenen


# ---------- Konnektor ----------

def test_konnektor_packliste_lesen(dienst):
    basis, ablage = dienst
    t, f = werkzeug(basis, ALT_ORGANISATOR, "packliste")
    assert not f
    assert "Kleidung (kleidung)" in t and "G-05 Wanderstöcke" in t and "gehört zu E-01 Stadt Wehlen" in t
    assert "Gewicht 1560 g" in t and "Anschaffung 70 €" in t and "Gesamt:" in t
    assert "gewicht = Gewicht (zahl, g, wird summiert)" in t           # die Schlüssel, die gegenstand_anlegen annimmt
    assert "Ida packt: noch offen" in t and "Sonnencreme" not in t and meldet(t, "konnektor.packliste.weggelassen.one")
    t, _ = werkzeug(basis, ALT_ORGANISATOR, "packliste", alle=True)
    assert "Sonnencreme" in t and "weggelassen" in t
    t, f = werkzeug(basis, ALT_ORGANISATOR, "packliste", art="Apotheke")
    assert "Blasenpflaster" in t and "Regenjacke" not in t and "Gesamt:" not in t
    t, f = werkzeug(basis, ALT_ORGANISATOR, "packliste", art="gibtsnicht")
    assert meldet(t, "konnektor.packliste.keine_kategorie")


def test_konnektor_zeige_gegenstand_und_mitnehmen_am_ding(dienst):
    basis, _ = dienst
    t, f = werkzeug(basis, ALT_ORGANISATOR, "zeige", id="G-05")
    assert not f and "Wanderstöcke" in t and "Kategorie: Ausrüstung" in t and "Gewicht 480 g" in t and "Anschaffung 45 €" in t
    assert "gehört zu E-01" in t and "Verlauf:" in t and "angelegt" in t and "noch von niemandem gepackt" in t
    t, _ = werkzeug(basis, ALT_ORGANISATOR, "zeige", id="E-01")
    assert "Mitnehmen: G-05 Wanderstöcke" in t                          # Zeile am Ding, an dem der Gegenstand hängt
    t, _ = werkzeug(basis, ALT_ORGANISATOR, "zeige", id="G-09")
    assert "weggelassen" in t
    t, _ = werkzeug(basis, ALT_ORGANISATOR, "ueberblick")
    assert meldet(t, "konnektor.packliste.ueberblick.other") and "Gewicht 2690 g" in t
    t, _ = werkzeug(basis, ALT_ORGANISATOR, "suche", begriff="Wanderstöcke")
    assert "G-05" in t


def test_konnektor_gegenstand_packen_und_stand_in_packliste(dienst):
    basis, ablage = dienst
    t, f = werkzeug(basis, KARL, "gegenstand_packen", ziel="G-01, G-03")
    assert not f and meldet(t, "konnektor.gegenstand.gepackt")
    assert sorted(rm.packstand_lesen(ablage / "beispielreise")) == ["G-01", "G-03"]
    t, _ = werkzeug(basis, KARL, "packliste")
    assert "2 von 7 für Karl gepackt" in t and "gepackt von Karl" in t
    t, f = werkzeug(basis, ALT_ORGANISATOR, "gegenstand_packen", ziel="G-07")        # Ida packt G-07
    assert not f
    t, f = werkzeug(basis, KARL, "gegenstand_packen", ziel="G-07")
    assert f and "Ida" in t                                                           # Karl darf ihn nicht abhaken
    t, f = werkzeug(basis, KARL, "gegenstand_packen", ziel="G-01", gepackt=False)
    assert not f and meldet(t, "konnektor.gegenstand.zurueckgenommen") and list(rm.packstand_lesen(ablage / "beispielreise")) == ["G-03", "G-07"]
    t, f = werkzeug(basis, KARL, "gegenstand_packen", ziel="Regenjacke")
    assert f and meldet(t, "konnektor.gegenstand.ziel")
    t, f = werkzeug(basis, KARL, "gegenstand_packen", ziel="G-77")
    assert f and meldet(t, "konnektor.gegenstand.unbekannt")
    t, f = werkzeug(basis, GAST, "gegenstand_packen", ziel="G-01")
    assert f                                                                          # Gast liest nur
    t, _ = werkzeug(basis, ALT_ORGANISATOR, "zeige", id="G-07")
    assert "Ida packt: gepackt" in t


def test_konnektor_werkzeuge_je_rolle(schreibweg):
    basis, _ = schreibweg
    namen = lambda token: {t["name"] for t in rpc(basis, token, "tools/list")["tools"]}
    assert {"packliste", "gegenstand_packen", "gegenstand_anlegen", "gegenstand_aendern", "packliste_uebernehmen"} <= namen(ALT_ORGANISATOR)
    assert {"packliste", "gegenstand_packen", "gegenstand_anlegen", "gegenstand_aendern"} <= namen(KARL)
    assert "packliste_uebernehmen" not in namen(KARL)
    assert "packliste" in namen(GAST) and not {"gegenstand_packen", "gegenstand_anlegen", "gegenstand_aendern"} & namen(GAST)
    anleitung = rpc(basis, ALT_ORGANISATOR, "initialize")["instructions"]
    assert "gear_create" in anleitung and "packing_list" in anleitung      # die Anleitung nennt die Werkzeuge mit ihren Namen am Rand


def test_konnektor_schreibt_gegenstaende_ueber_den_schreibweg(schreibweg, monkeypatch):
    import konten
    basis, _ = schreibweg
    monkeypatch.setattr(Schreibweg, "antwort", (200, {"ok": True, "text": "Gegenstand G-10 angelegt."}))   # der Zustand der Klasse gilt für alle Tests
    t, f = werkzeug(basis, KARL, "gegenstand_anlegen", art="kleidung", titel="Mütze", merkmale={"gewicht": 60}, an="E-02")
    assert not f and "G-10" in t
    pfad, geheim, body = Schreibweg.anfragen[-1]
    assert pfad == "/beispielreise/gegenstand_anlegen" and geheim == konten.dienst_geheimnis()
    assert body == {"person": "karl", "name": "Karl", "rolle": "mitwirkend",
                    "args": {"art": "kleidung", "titel": "Mütze", "merkmale": {"gewicht": 60}, "an": "E-02"}}
    t, f = werkzeug(basis, GAST, "gegenstand_anlegen", art="kleidung", titel="x")
    assert f
    t, f = werkzeug(basis, KARL, "packliste_uebernehmen", von_reise="stadtwochenende")
    assert f                                                                          # nur Organisator:innen
    t, f = werkzeug(basis, ALT_ORGANISATOR, "packliste_uebernehmen", von_reise="gibtsnicht")
    assert f and "gibtsnicht" in t


def test_rolle_summe_ist_im_werkzeug_waehlbar(schreibweg, monkeypatch):
    """Ohne die Rolle summe im Schema konnte der AI-Client das Gewicht einer Packliste nie als summiert markieren, die Seite
    zeigte keine Summe; attribute_define bietet sie an (englisch sum) und gibt sie als summe an den Schreibweg."""
    basis, _ = schreibweg
    liste = rpc(basis, ALT_ORGANISATOR, "tools/list")
    schema = next(w for w in liste["tools"] if w["name_aussen"] == "attribute_define")["inputSchema"]["properties"]["role"]
    assert "sum" in schema["enum"] and "summe:" in schema["description"]
    monkeypatch.setattr(Schreibweg, "antwort", (200, {"ok": True, "text": "ok"}))
    werkzeug(basis, ALT_ORGANISATOR, "attribute_define", kind="kleidung", attribute="gewicht", role="sum")
    pfad, _, body = Schreibweg.anfragen[-1]
    assert pfad == "/beispielreise/merkmal_definieren" and body["args"]["rolle"] == "summe"


def test_englische_namen_der_werkzeuge(schreibweg):
    import schnittstelle
    assert {schnittstelle.NAMEN[e] for e in ("packing_list", "gear_create", "gear_update", "gear_pack", "packing_list_adopt")} == \
        {"packliste", "gegenstand_anlegen", "gegenstand_aendern", "gegenstand_packen", "packliste_uebernehmen"}
    tab = schnittstelle.parameter_zu_englisch("gegenstand_anlegen")
    assert tab["an"] == "parent" and tab["wer"] == "packer" and schnittstelle.parameter_zu_englisch("gegenstand_packen")["gepackt"] == "packed"
    assert schnittstelle.parameter_zu_intern("gegenstand_aendern")["parent"] == "an"


# ---------- Seite im Browser ----------

@pytest.mark.skipif(not PLAYWRIGHT.exists() or not shutil.which("node"), reason="Playwright fehlt")
@pytest.mark.parametrize("browser", ["chromium", "webkit"])
def test_packliste_im_browser(tmp_path, monkeypatch, browser):
    """Reiter Packliste mit dem echten Rückmeldedienst: Planen (Tabellen, Summen), Packen (Gruppen nach Raum, Haken je Person, ohne Netz
    abhaken und zurücknehmen, nachreichen), Zeile „Mitnehmen“ am Ding, Kennung als Sprungziel; nichts steht am Handy über."""
    from test_regeln import reise_bauen, starten
    seiten = reise_bauen(tmp_path, fest=True)
    o = tmp_path / "ablage" / "beispielreise"
    o.mkdir(parents=True)
    monkeypatch.setenv("RM_ABLAGE", str(tmp_path / "ablage"))
    monkeypatch.setenv("KN_SEITEN", str(seiten))
    rm._zeiten.clear()
    dienst, durl = starten(rm.Dienst)

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(seiten)))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    try:
        aus = subprocess.run(["node", str(Path(__file__).parent / "seiten_packliste.mjs"), str(PLAYWRIGHT),
                              f"http://127.0.0.1:{s.server_address[1]}/beispielreise/", durl, "Karl"],
                             capture_output=True, text=True, timeout=240,
                             env={**os.environ, "RH_BROWSER": browser, "FR_TEST_DIENST": konten.dienst_geheimnis()})
    finally:
        s.shutdown()
        dienst.shutdown()
    assert aus.returncode == 0, aus.stderr[-2000:]
    e = json.loads(aus.stdout.strip().splitlines()[-1])
    assert e["fehler"] == []
    # Planen
    assert e["planen"]["reiter"] == "#packliste"
    assert e["planen"]["kategorien"] == ["Kleidung (3)", "Ausrüstung (3)", "Apotheke (2)"]
    assert e["planen"]["gesamt"] == ["Gewicht 2690 g Anschaffung 70 €"]
    assert e["planen"]["spalten"][:2] == ["Gegenstand", "Gewicht"]
    assert e["planen"]["summen"] == ["Summe 1560 g", "Summe 750 g 70 €", "Summe 380 g"]
    assert e["planen"]["weggelassen"] == ["1 weggelassen"] and not e["planen"]["breit"]
    # Packen: Karl packt alles außer dem Erste-Hilfe-Set, das Ida trägt; es gibt dort keinen Haken für ihn
    assert e["packen"]["gruppen"][0].startswith("Kleidung") and e["packen"]["haekchenFuerKarl"] == 7 and e["packen"]["ohneHakenIda"] == 0
    h = e["haken"]
    assert h["gepackt"] == ["Regenjacke"] and h["checked"] == "true" and e["nachNeuladen"] == ["Regenjacke"]
    # Gepacktes rutscht in seiner Gruppe nach unten, die Liste zuckt nicht, der Fokus bleibt am Haken (#501)
    assert h["vorher"][0].startswith("Regenjacke") and h["nachher"][-1].startswith("Regenjacke")
    assert [t.split("G-")[0] for t in h["nachher"][:2]] == [t.split("G-")[0] for t in h["vorher"][1:3]]
    assert h["zuckt"] == 0 and h["fokus"] == "G-01"
    assert e["fortschritt"] == ["Karl: 1 von 7 gepackt"]
    assert [g.split(" ")[0] for g in e["raum"]["gruppen"]] == ["am", "Tagesrucksack", "Rucksack"] and e["raum"]["mitRaum"] == 0
    assert e["raum"]["summen"][1] == "Gewicht 980 g"                        # Tagesrucksack: Jacke 420, Flasche 180, Set 350, Pflaster 30
    # ohne Netz: abhaken und zurücknehmen werden gemerkt, dann nachgereicht
    assert e["offline"]["ausgang"] == 2 and e["offline"]["gepackt"] == ["Wanderstöcke"] and "wird nachgereicht" in e["offline"]["nachreichen"]
    assert e["nachgereicht"] == {"ausgang": 0, "gepackt": ["Wanderstöcke"]}
    assert list(rm.packstand_lesen(o)) == ["G-05"] and list(rm.packstand_lesen(o)["G-05"]) == ["Karl"]
    # Mitnehmen und Kennung
    assert e["mitnehmen"]["text"] == ["Mitnehmen: Wanderstöcke"] and e["mitnehmen"]["href"] == "#packliste" and e["mitnehmen"]["danach"] == "#packliste"
    assert e["kennung"] == {"reiter": "#packliste", "da": 1} and not e["breit"]


def test_anleitung_nennt_ausgeschaltete_packliste_und_wie_man_sie_einschaltet(dienst):
    """Ist der Baustein aus, fehlen die Werkzeuge; die Anleitung sagt dem AI-Client, dass er aus ist und wie ein:e Organisator:in ihn einschaltet."""
    import copy
    d = copy.deepcopy(kn.daten("beispielreise"))
    zugang = {"reise": "beispielreise", "person": "ida", "sprache": "de"}
    assert "packliste" in d["reise"]["bausteine"]
    an = kn.anleitung(zugang, d)
    d["reise"]["bausteine"] = [b for b in d["reise"]["bausteine"] if b != "packliste"]
    aus = kn.anleitung(zugang, d).split("Bei dieser Reise ausgeschaltet", 1)[1].split(".", 1)[0]
    assert "packliste" in aus and "einstellung_setzen" in aus and "vollständigen Liste" in aus
    assert "Bei dieser Reise ausgeschaltet" not in an or "packliste" not in an.split("Bei dieser Reise ausgeschaltet", 1)[1].split(".", 1)[0]


def test_grundform_im_text_nennt_den_wert_des_schemas():
    """Der Client sieht im Schema nur basic_form gear: Hinweise sagen nicht „grundform gegenstand“, das er nicht übergeben kann."""
    import schnittstelle
    assert schnittstelle.namen_im_text("art_definieren mit grundform gegenstand") == "kind_define mit basic_form gear"
    assert schnittstelle.namen_im_text("grundform ort", streng=True) == "basic_form place"
