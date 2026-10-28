"""Tests für engine/routen.py: Wahlstellen, Status, Prüfungen, Datum und Summen."""
import copy
import datetime
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from routen import Routen  # noqa: E402

D = datetime.date

BASIS = {
    "entscheider": ["Ida"],
    "start": {"datum": D(2027, 3, 1), "ort": "O-01"},
    "ende": {"datum": D(2027, 3, 3), "ort": "O-03"},
    "orte": {"O-01": {"name": "A"}, "O-02": {"name": "B"}, "O-03": {"name": "C"}, "O-04": {"name": "Abzweig"}},
    "strecken": {
        "E-01": {"titel": "A → B", "von": "O-01", "nach": "O-02", "art": "wandern",
                 "kennzahlen": {"Gehzeit": "3:30 h", "Aufstieg (Hm)": "400", "Abstieg (Hm)": "100", "Länge (km)": "10,5 km"}},
        "E-02": {"titel": "B → C", "von": "O-02", "nach": "O-03", "art": "wandern",
                 "kennzahlen": {"Gehzeit": "2:00 h", "Aufstieg (Hm)": "100", "Abstieg (Hm)": "300", "Länge (km)": "6 km"}},
        "E-02V": {"titel": "Abzweig → C", "von": "O-04", "nach": "O-03", "zweig_von": "E-02", "rolle": "alternative"},
        "E-03": {"titel": "Bus B → C", "von": "O-02", "nach": "O-03", "art": "bus"},
    },
    "unterkuenfte": {
        "U-01": {"name": "Hotel B1", "ort": "O-02", "typ": "Hotel"},
        "U-02": {"name": "Hotel B2", "ort": "O-02", "typ": "Hotel"},
        "U-03": {"name": "Hütte C", "ort": "O-03", "typ": "Hütte", "frage": "F-02"},
    },
    "tage": {
        "T-01": {"titel": "A nach B", "strecken": ["E-01"], "nacht": "V-02"},
        "T-02": {"titel": "B nach C", "strecken": ["V-03"], "nacht": "U-03"},
        "T-03": {"titel": "Abreise"},
        "T-04": {"titel": "Bus nach C", "strecken": ["E-03"], "nacht": "U-03"},
        "T-05": {"titel": "Ruhetag in C", "nacht": "U-03"},
    },
    "route": [{"teil": "Alles", "folge": ["V-01"]}],
    "wahlstellen": {
        "V-01": {"titel": "Route", "art": "planung", "frage": "F-01", "optionen": [
            {"id": "V-01.a", "titel": "Zu Fuß", "folge": ["T-01", "T-02", "T-03"]},
            {"id": "V-01.b", "titel": "Mit Bus", "folge": ["T-04", "T-05"]},
        ]},
        "V-02": {"titel": "Hotel in B", "art": "planung", "frage": "F-01", "optionen": [
            {"id": "V-02.a", "titel": "B1", "unterkuenfte": ["U-01"]},
            {"id": "V-02.b", "titel": "B2", "unterkuenfte": ["U-02"]},
        ]},
        "V-03": {"titel": "Abzweig nehmen?", "art": "unterwegs", "optionen": [
            {"id": "V-03.a", "titel": "Hauptweg", "strecken": ["E-02"]},
            {"id": "V-03.b", "titel": "Abzweig", "strecken": ["E-02V"], "ausloeser": "bei gutem Wetter"},
        ]},
    },
}
FRAGEN = {"F-01": "offen", "F-02": "offen"}


def roh():
    return copy.deepcopy(BASIS)


def laufe(r, fragen=FRAGEN):
    fehler, ids = [], {}

    def anlegen(i, wo):
        if i in ids:
            fehler.append(f"Doppelte ID {i}")
        ids[i] = wo
    erg = Routen(r, {}, fragen, fehler, anlegen).bauen()
    return erg, fehler


def ok(r, fragen=FRAGEN):
    erg, fehler = laufe(r, fragen)
    assert fehler == [], fehler
    return erg


def nur_fehler(r):
    _, fehler = laufe(r)
    assert fehler
    return "\n".join(fehler)


def verlauf(*eintraege):
    return [{"datum": D(2026, 10, i + 1), "status": s, "wer": w, **extra} for i, (s, w, extra) in enumerate(eintraege)]


def option(r, oid):
    vid = oid.split(".")[0]
    return next(o for o in r["wahlstellen"][vid]["optionen"] if o["id"] == oid)


def aktiv(erg, vid):
    return next(o["id"] for w in erg["wahlstellen"] if w["id"] == vid for o in w["optionen"] if o["aktiv"])


def texte(erg):
    return [w["text"] for w in erg["warnungen"]]


# ---------- Auswahl und Status ----------
def test_ohne_entscheidung_gilt_erste_option():
    r = roh()
    r["tage"]["T-03"]["strecken"] = []
    erg = ok(r)
    assert [t["id"] for t in erg["tage"]] == ["T-01", "T-02", "T-03"]
    assert aktiv(erg, "V-01") == "V-01.a"
    assert next(w for w in erg["wahlstellen"] if w["id"] == "V-01")["offen"]


def test_gewaehlt_vor_favorisiert_vor_erster():
    r = roh()
    option(r, "V-01.b")["verlauf"] = verlauf(("favorisiert", "Claude", {"grund": "passt besser"}))
    assert aktiv(ok(r), "V-01") == "V-01.b"
    option(r, "V-01.a")["verlauf"] = verlauf(("gewaehlt", "Ida", {}))
    erg = ok(r, {"F-01": "erledigt", "F-02": "offen"})
    assert aktiv(erg, "V-01") == "V-01.a"
    assert not next(w for w in erg["wahlstellen"] if w["id"] == "V-01")["offen"]


def test_verwerfen_nach_wahl_und_wieder_hervorholen():
    r = roh()
    option(r, "V-01.a")["verlauf"] = verlauf(("gewaehlt", "Ida", {}), ("verworfen", "Ida", {"grund": "zu weit"}))
    erg = ok(r)
    assert aktiv(erg, "V-01") == "V-01.b"
    assert [t["id"] for t in erg["tage"]] == ["T-04", "T-05"]
    va = next(o for w in erg["wahlstellen"] for o in w["optionen"] if o["id"] == "V-01.a")
    assert va["status"] == "verworfen" and len(va["verlauf"]) == 2  # Verlauf bleibt erhalten
    option(r, "V-01.a")["verlauf"] += [{"datum": D(2026, 10, 9), "status": "vorgeschlagen", "wer": "Claude"}]
    assert aktiv(ok(r), "V-01") == "V-01.a"


def test_ersetzt_braucht_durch():
    r = roh()
    option(r, "V-01.a")["verlauf"] = verlauf(("ersetzt", "Ida", {}))
    assert "braucht „durch“" in nur_fehler(r)
    option(r, "V-01.a")["verlauf"] = verlauf(("ersetzt", "Ida", {"durch": "V-01.b"}))
    assert aktiv(ok(r), "V-01") == "V-01.b"


def test_nur_entscheider_darf_waehlen_und_verwerfen():
    r = roh()
    option(r, "V-01.a")["verlauf"] = verlauf(("gewaehlt", "Claude", {}))
    assert "darf nur Ida" in nur_fehler(r)
    option(r, "V-01.a")["verlauf"] = verlauf(("verworfen", "Mitreisende", {}))
    assert "darf nur Ida" in nur_fehler(r)


def test_alle_verworfen_ist_fehler():
    r = roh()
    for o in r["wahlstellen"]["V-02"]["optionen"]:
        o["verlauf"] = verlauf(("verworfen", "Ida", {}))
    assert "alle Optionen sind verworfen" in nur_fehler(r)


def test_zwei_gewaehlt_ist_fehler():
    r = roh()
    for o in r["wahlstellen"]["V-02"]["optionen"]:
        o["verlauf"] = verlauf(("gewaehlt", "Ida", {}))
    assert "mehrere Optionen gewählt" in nur_fehler(r)


def test_unbekannter_status_und_unsortierter_verlauf():
    r = roh()
    option(r, "V-02.a")["verlauf"] = [{"datum": D(2026, 10, 5), "status": "vielleicht", "wer": "Claude"}]
    assert "unbekannt" in nur_fehler(r)
    option(r, "V-02.a")["verlauf"] = [{"datum": D(2026, 10, 5), "status": "vorgeschlagen"},
                                      {"datum": D(2026, 10, 1), "status": "favorisiert"}]
    assert "nicht zeitlich sortiert" in nur_fehler(r)


# ---------- Offene Fragen: nur eine Quelle ----------
def test_offene_planungswahl_braucht_f_frage():
    r = roh()
    del r["wahlstellen"]["V-02"]["frage"]
    assert "braucht eine F-Frage" in nur_fehler(r)


def test_unterwegs_wahl_braucht_keine_f_frage():
    ok(roh())  # V-03 hat keine Frage


def test_f_status_passt_nicht_zur_wahl():
    r = roh()
    erg = ok(r, {"F-01": "erledigt", "F-02": "offen"})
    assert any("V-02 ist noch offen, aber F-01" in t for t in texte(erg))
    option(r, "V-02.a")["verlauf"] = verlauf(("gewaehlt", "Ida", {}))
    erg = ok(r)
    assert any("V-02 ist entschieden, aber F-01" in t for t in texte(erg))


# ---------- Ablauf: Lücken, Abzweig, Datum, Fixpunkte ----------
def test_teilstueck_alternative_zweigt_ab():
    r = roh()
    option(r, "V-03.b")["verlauf"] = verlauf(("favorisiert", "Claude", {"grund": "passt besser"}))
    erg = ok(r)
    assert erg["tage"][1]["strecken"] == [{"id": "E-02V", "wahl": "V-03"}]
    assert erg["warnungen"] == []


def test_luecke_ist_warnung_kein_fehler():
    r = roh()
    r["tage"]["T-02"]["strecken"] = []
    erg = ok(r)
    assert "T-02: Der Weg von B nach C fehlt." in texte(erg)
    r = roh()
    r["tage"]["T-01"]["strecken"] = ["E-02"]
    assert any("Lücke" in t for t in texte(ok(r)))


def test_datum_wird_berechnet_und_ids_bleiben():
    r = roh()
    r["wahlstellen"]["V-04"] = {"titel": "Ruhetag?", "art": "planung", "frage": "F-01", "optionen": [
        {"id": "V-04.a", "titel": "Ohne"}, {"id": "V-04.b", "titel": "Mit Ruhetag in B", "folge": ["T-06"]}]}
    r["tage"]["T-06"] = {"titel": "Ruhetag in B", "nacht": "V-02"}
    option(r, "V-01.a")["folge"] = ["T-01", "V-04", "T-02", "T-03"]
    erg = ok(r)
    assert [(t["id"], t["datum"]) for t in erg["tage"]] == [("T-01", "2027-03-01"), ("T-02", "2027-03-02"), ("T-03", "2027-03-03")]
    option(r, "V-04.b")["verlauf"] = verlauf(("gewaehlt", "Ida", {}))
    erg = ok(r)
    assert [(t["id"], t["datum"]) for t in erg["tage"]] == [
        ("T-01", "2027-03-01"), ("T-06", "2027-03-02"), ("T-02", "2027-03-03"), ("T-03", "2027-03-04")]
    assert any("endet am 04.03." in t and "+1 Tag" in t for t in texte(erg))


def test_fixpunkt_ort_verfehlt():
    r = roh()
    r["fixpunkte"] = [{"datum": D(2027, 3, 2), "ort": "O-01", "titel": "Treffen in A"}]
    erg = ok(r)
    assert any("Treffen in A" in t and "nicht in A" in t for t in texte(erg))
    assert erg["tage"][1]["fixpunkte"] == ["Treffen in A"]
    r["fixpunkte"] = [{"datum": D(2027, 3, 2), "ort": "O-02", "titel": "Treffen in B"}]
    assert ok(r)["warnungen"] == []  # T-02 startet in B


def test_fixpunkt_ausserhalb_des_plans():
    r = roh()
    r["fixpunkte"] = [{"datum": D(2027, 4, 1), "titel": "später"}]
    assert any("außerhalb des Plans" in t for t in texte(ok(r)))


# ---------- Struktur ----------
def test_tag_in_zwei_optionen_ist_fehler():
    r = roh()
    option(r, "V-01.b")["folge"] = ["T-01", "T-04"]
    assert "steht in mehreren Optionen" in nur_fehler(r)


def test_tote_verweise():
    r = roh()
    r["tage"]["T-01"]["strecken"] = ["E-99"]
    r["tage"]["T-02"]["nacht"] = "U-99"
    option(r, "V-01.a")["folge"].append("T-99")
    m = nur_fehler(r)
    assert "E-99" in m and "U-99" in m and "T-99" in m


def test_option_id_muss_zur_wahlstelle_passen():
    r = roh()
    option(r, "V-02.b")["id"] = "V-05.b"
    assert "muss V-02.a" in nur_fehler(r)


def test_unbekannte_frage_an_unterkunft():
    r = roh()
    r["unterkuenfte"]["U-01"]["frage"] = "F-77"
    assert "F-77" in nur_fehler(r)


def test_kandidaten_in_verschiedenen_orten():
    r = roh()
    r["unterkuenfte"]["U-02"]["ort"] = "O-03"
    assert any("verschiedenen Orten" in t for t in texte(ok(r)))


def test_unbenutzter_tag_und_wahlstelle_sind_warnungen():
    r = roh()
    r["tage"]["T-09"] = {"titel": "vergessen"}
    r["wahlstellen"]["V-09"] = {"titel": "lose", "art": "unterwegs", "optionen": [{"id": "V-09.a", "titel": "x"}]}
    t = texte(ok(r))
    assert any("T-09 kommt in keiner Option vor" in x for x in t)
    assert any("V-09 wird nirgends verwendet" in x for x in t)


# ---------- Summen ----------
def test_summen_gesamt_und_je_option():
    erg = ok(roh())
    s = erg["summe"]
    assert (s["tage"], s["naechte"], s["min"], s["auf"], s["ab"], s["km"]) == (3, 2, 330, 500, 400, 16.5)
    assert s["unterkunftstypen"] == {"Hotel": 1, "Hütte": 1}
    b = next(o for w in erg["wahlstellen"] for o in w["optionen"] if o["id"] == "V-01.b")
    assert b["summe"]["tage"] == 2 and b["summe"]["km"] == 0  # Bus zählt nicht als Gehstrecke


def test_unterkunft_naechte_und_kandidaten():
    erg = ok(roh())
    assert erg["unterkuenfte"]["U-01"]["naechte"] == ["T-01"]
    assert erg["unterkuenfte"]["U-02"]["naechte"] == ["T-01"]  # Kandidat derselben Nacht
    assert erg["unterkuenfte"]["U-03"]["buchung"] == "offen"
    assert erg["tage"][0]["nacht"] == {"ort": "O-02", "wahl": "V-02", "unterkunft": "U-01"}


@pytest.mark.parametrize("status", ["gewaehlt", "verworfen", "ersetzt"])
def test_entscheider_liste_leer(status):
    r = roh()
    r["entscheider"] = []
    option(r, "V-02.a")["verlauf"] = verlauf((status, "Ida", {"durch": "V-02.b"}))
    assert "darf nur" in nur_fehler(r)


def test_entscheider_von_aussen():
    """Die Organisator:innen aus reise.yaml kommen als Parameter und ersetzen „entscheider“ im YAML."""
    r = roh()
    option(r, "V-02.a")["verlauf"] = verlauf(("gewaehlt", "Hanna", {}))
    fehler = []
    Routen(r, {}, FRAGEN, fehler, lambda *a: None, entscheider=["Hanna"]).bauen()
    assert not [f for f in fehler if "darf nur" in f]
    fehler = []
    Routen(r, {}, FRAGEN, fehler, lambda *a: None, entscheider=[]).bauen()
    assert any("darf nur" in f for f in fehler)


# ---------- Benannte Pläne ----------
def test_plan_erzwingt_auch_verworfene_option():
    r = roh()
    option(r, "V-01.a")["verlauf"] = verlauf(("gewaehlt", "Ida", {}))
    option(r, "V-01.b")["verlauf"] = verlauf(("verworfen", "Ida", {}))
    r["plaene"] = [{"id": "P-A", "kurz": "Zu Fuß", "auswahl": ["V-01.a"]},
                   {"id": "P-B", "kurz": "Bus", "auswahl": ["V-01.b", "V-02.b"]}]
    erg = ok(r, {"F-01": "erledigt", "F-02": "offen"})
    a, b = erg["plaene"]
    assert [t["id"] for t in a["tage"]] == ["T-01", "T-02", "T-03"] and a["aktuell"]
    assert [t["id"] for t in b["tage"]] == ["T-04", "T-05"] and not b["aktuell"]
    assert b["tage"][0]["nacht"]["unterkunft"] == "U-03"
    assert any("Lücke" in w["text"] for w in b["warnungen"])        # Bus startet in B, Plan startet in A
    assert not any(w["bezug"].startswith("V-") for w in b["warnungen"])
    assert aktiv(erg, "V-01") == "V-01.a"                            # der aktuelle Plan bleibt unberührt


def test_plan_fehler():
    r = roh()
    r["plaene"] = [{"id": "P-A", "auswahl": ["V-01.x"]}]
    assert "Option V-01.x gibt es nicht" in nur_fehler(r)
    r["plaene"] = [{"id": "P-A", "auswahl": ["V-01.a", "V-01.b"]}]
    assert "zwei Optionen für V-01" in nur_fehler(r)
    r["plaene"] = [{"id": "Plan A", "auswahl": []}]
    assert "muss P-" in nur_fehler(r)


def test_laengster_tag_und_nacht_ohne_unterkunft():
    r = roh()
    r["tage"]["T-02"]["nacht"] = {"ort": "O-03", "typ": "Hotel", "hinweis": "noch offen"}
    s = ok(r)["summe"]
    assert s["laengster"] == {"min": 210, "nr": 1, "id": "T-01"}
    assert s["unterkunftstypen"] == {"Hotel": 2}


GRUND = {"unterkunft": {"preis": {"name": "Preis", "typ": "geld", "veraenderlich": True},
                        "fruehstueck": {"name": "Frühstück", "typ": "auswahl", "werte": ["inklusive", "keins"]}},
         "strecke": {"gehzeit": {"name": "Gehzeit", "auto": "gehzeit"}, "schwierigkeit": {"name": "Schwierigkeit"}},
         "route": {"tage": {"name": "Tage", "auto": "tage"}},
         "faehre": {"preis": {"name": "Preis", "typ": "geld", "veraenderlich": True}, "dauer": {"name": "Dauer"}}}


def mk_bauen(r):
    fehler = []
    erg = Routen(r, {}, FRAGEN, fehler, lambda *a: None, grund=GRUND).bauen()
    return erg, fehler


def test_merkmale_bereich_und_werte():
    r = roh()
    r["unterkuenfte"]["U-01"]["merkmale"] = {"preis": {"wert": "120 €", "geprueft": D(2026, 10, 26)}, "fruehstueck": "inklusive"}
    r["unterkuenfte"]["U-02"]["merkmale"] = {"preis": "99 €"}
    r["wahlstellen"]["V-03"]["optionen"][1]["merkmale"] = {"schwierigkeit": "Kettenstelle"}
    erg, fehler = mk_bauen(r)
    assert fehler == []
    w = {x["id"]: x for x in erg["wahlstellen"]}
    assert (w["V-01"]["bereich"], w["V-02"]["bereich"], w["V-03"]["bereich"]) == ("route", "unterkunft", "strecke")
    a, b = w["V-02"]["optionen"]
    assert a["merkmale"]["preis"]["geprueft"] == "2026-10-26" and not a["merkmale"]["preis"]["ungeprueft"]
    assert b["merkmale"]["preis"]["ungeprueft"] and b["fehlt"] == ["fruehstueck"]
    assert w["V-03"]["optionen"][0]["merkmale"]["gehzeit"] == {"wert": "2:00 h", "auto": True}
    assert w["V-03"]["optionen"][1]["merkmale"]["schwierigkeit"]["wert"] == "Kettenstelle"
    assert w["V-01"]["optionen"][0]["merkmale"]["tage"]["wert"] == "3 Tage"
    assert erg["unterkuenfte"]["U-01"]["merkmale"]["fruehstueck"]["wert"] == "inklusive"
    assert [k["id"] for k in erg["merkmale"]["unterkunft"]] == ["preis", "fruehstueck"]


def test_merkmale_ergaenzen_reise_und_wahlstelle():
    r = roh()
    r["merkmale"] = {"unterkunft": {"pool": {"name": "Pool", "typ": "auswahl", "werte": ["ja", "nein"]}}}
    r["wahlstellen"]["V-02"]["merkmale"] = {"laerm": {"name": "Lärm"}}
    r["unterkuenfte"]["U-01"]["merkmale"] = {"pool": True, "laerm": "Straße"}
    erg, fehler = mk_bauen(r)
    assert fehler == []
    o = next(x for x in erg["wahlstellen"] if x["id"] == "V-02")["optionen"][0]
    assert o["merkmale"]["pool"]["wert"] == "ja" and o["merkmale"]["laerm"]["wert"] == "Straße"


@pytest.mark.parametrize("aendern, meldung", [
    (lambda r: r["unterkuenfte"]["U-01"].update(merkmale={"gibtsnicht": "x"}), "gibt es hier nicht"),
    (lambda r: r["unterkuenfte"]["U-01"].update(merkmale={"fruehstueck": "vielleicht"}), "erlaubt"),
    (lambda r: r["unterkuenfte"]["U-01"].update(merkmale={"preis": {"wert": "1 €", "preis": 2}}), "unbekannte Felder"),
    (lambda r: r["unterkuenfte"]["U-01"].update(merkmale={"preis": {"wert": "1 €", "geprueft": "gestern"}}), "Datum"),
    (lambda r: r["wahlstellen"]["V-03"]["optionen"][0].update(merkmale={"gehzeit": "3 h"}), "berechnet"),
    (lambda r: r.update(merkmale={"hotel": {}}), "Bereich"),
    (lambda r: r.update(merkmale={"route": {"x": {"name": "X", "auto": "tage"}}}), "nur in der Grundliste"),
    (lambda r: r["wahlstellen"]["V-02"].update(merkmale={"preis": {"name": "Preis"}}), "schon"),
    (lambda r: r["wahlstellen"]["V-02"]["optionen"][0].update(
        verlauf=[{"datum": D(2026, 10, 26), "status": "favorisiert", "wer": "Claude"}]), "Begründung"),
])
def test_merkmale_fehler(aendern, meldung):
    r = roh()
    aendern(r)
    _, fehler = mk_bauen(r)
    assert any(meldung in f for f in fehler), fehler


def test_favorisiert_mit_grund_ok():
    r = roh()
    r["wahlstellen"]["V-02"]["optionen"][0]["verlauf"] = [
        {"datum": D(2026, 10, 26), "status": "favorisiert", "wer": "Claude", "grund": "günstiger, Frühstück inklusive"}]
    assert mk_bauen(r)[1] == []


def test_unterkunft_kategorie_aus_typ_oder_ausdruecklich():
    r = roh()
    r["unterkuenfte"]["U-02"].update(typ="Refugi")
    r["unterkuenfte"]["U-03"].update(typ="Tempel", kategorie="gasthaus")
    r["unterkuenfte"]["U-04"] = {"name": "Iglu", "ort": "O-03", "typ": "Iglu"}
    r["tage"]["T-05"]["nacht"] = {"ort": "O-03", "typ": "Nachtzug"}
    u = ok(r)["unterkuenfte"]
    assert [u[k]["kategorie"] for k in ("U-01", "U-02", "U-03", "U-04")] == ["hotel", "huette", "gasthaus", "sonstige"]
    assert u["U-02"]["typ"] == "Refugi"   # die eigene Bezeichnung der Reise bleibt
    r["unterkuenfte"]["U-01"]["kategorie"] = "schloss"
    assert "kategorie muss" in nur_fehler(r)


def test_freie_nacht_bekommt_kategorie():
    from routen import kategorie
    assert kategorie({"typ": "Ryokan"}) == "gasthaus"
    assert kategorie({"an_bord": True}) == "unterwegs"
    assert kategorie({"typ": " berghütte "}) == "huette"
    assert kategorie({"typ": "Hotel", "kategorie": "privat"}) == "privat"


# ---------- Arten, Werte je Datum, „an“ (Paket 1 der Alternativen, Issue frieda-reist#18) ----------
def mit_faehren():
    r = roh()
    r["strecken"]["E-10"] = {"titel": "Fähre A", "von": "O-02", "nach": "O-03", "art": "faehre",
                             "merkmale": {"dauer": {"wert": "ca. 11 h", "quelle": "Beispiel"}}}
    r["strecken"]["E-11"] = {"titel": "Fähre B", "von": "O-02", "nach": "O-03", "art": "faehre"}
    r["wahlstellen"]["V-04"] = {"titel": "Überfahrt", "art": "planung", "frage": "F-01", "an": ["T-02"], "optionen": [
        {"id": "V-04.a", "titel": "Fähre A", "strecken": ["E-10"], "merkmale": {"preis": "80 €"}},
        {"id": "V-04.b", "titel": "Fähre B", "strecken": ["E-11"], "merkmale": {"dauer": "ca. 10 h"}}]}
    return r


def test_art_der_strecken_bestimmt_die_liste_und_werte_stehen_an_strecke_oder_option():
    erg, fehler = mk_bauen(mit_faehren())
    assert fehler == []
    w = next(x for x in erg["wahlstellen"] if x["id"] == "V-04")
    assert w["bereich"] == "faehre" and [k["id"] for k in w["kriterien"]] == ["preis", "dauer"]
    a, b = w["optionen"]
    assert a["merkmale"]["dauer"]["wert"] == "ca. 11 h" and a["merkmale"]["preis"]["wert"] == "80 €"
    assert b["merkmale"]["dauer"]["wert"] == "ca. 10 h" and b["fehlt"] == ["preis"]
    # Wanderstrecken und gemischte Arten bleiben beim Bereich „strecke“
    w3 = next(x for x in erg["wahlstellen"] if x["id"] == "V-03")
    assert w3["bereich"] == "strecke"


def test_gemischte_arten_nehmen_strecke():
    r = mit_faehren()
    r["wahlstellen"]["V-04"]["optionen"][1]["strecken"] = ["E-03"]
    r["wahlstellen"]["V-04"]["optionen"][0]["merkmale"] = r["wahlstellen"]["V-04"]["optionen"][1]["merkmale"] = {}
    erg, fehler = mk_bauen(r)
    assert fehler == []
    assert next(x for x in erg["wahlstellen"] if x["id"] == "V-04")["bereich"] == "strecke"


def test_werte_je_datum():
    r = roh()
    r["unterkuenfte"]["U-01"]["merkmale"] = {"preis": [
        {"wert": "100 €", "gilt": D(2027, 3, 1), "geprueft": D(2026, 10, 26)},
        {"wert": "120 €", "gilt": [D(2027, 3, 3), D(2027, 3, 4)], "geprueft": D(2026, 10, 27)},
        {"wert": "90 €"}]}
    erg, fehler = mk_bauen(r)
    assert fehler == []
    m = next(x for x in erg["wahlstellen"] if x["id"] == "V-02")["optionen"][0]["merkmale"]["preis"]
    assert m["wert"] == "90 €" and "gilt" not in m and len(m["je_datum"]) == 2
    from routen import gilt_am
    assert gilt_am(m, "2027-03-01")["wert"] == "100 €"
    assert gilt_am(m, "2027-03-04")["wert"] == "120 €"
    assert gilt_am(m, "2027-03-02")["wert"] == "90 €"


def test_werte_je_datum_ohne_standardwert():
    r = roh()
    r["unterkuenfte"]["U-01"]["merkmale"] = {"preis": [{"wert": "100 €", "gilt": D(2027, 3, 1)}]}
    erg, _ = mk_bauen(r)
    m = next(x for x in erg["wahlstellen"] if x["id"] == "V-02")["optionen"][0]["merkmale"]["preis"]
    from routen import gilt_am
    assert gilt_am(m, "2027-03-02") is None and gilt_am(m, "2027-03-01")["wert"] == "100 €"
    assert m["wert"] == "100 €" and m["gilt"] == ["2027-03-01"]   # für Ansichten ohne Datum


@pytest.mark.parametrize("preis, meldung", [
    ([{"wert": "1 €", "gilt": D(2027, 3, 1)}, {"wert": "2 €", "gilt": D(2027, 3, 1)}], "zwei Werten"),
    ([{"wert": "1 €"}, {"wert": "2 €"}], "ohne „gilt“"),
    ([{"wert": "1 €", "gilt": "morgen"}], "gilt muss"),
    ([{"wert": "1 €", "gilt": []}], "gilt muss"),
])
def test_werte_je_datum_fehler(preis, meldung):
    r = roh()
    r["unterkuenfte"]["U-01"]["merkmale"] = {"preis": preis}
    assert any(meldung in f for f in mk_bauen(r)[1])


def test_neue_art_der_reise_und_wahlstelle_an_beliebiger_id():
    r = roh()
    r["merkmale"] = {"restaurant": {"kueche": {"name": "Küche"}, "preis": {"name": "Preis", "typ": "geld"}}}
    r["wahlstellen"]["V-05"] = {"titel": "Abendessen in B", "art": "planung", "frage": "F-01", "bereich": "restaurant",
                                "an": ["O-02", "U-01", "E-01"], "optionen": [
        {"id": "V-05.a", "titel": "Gasthaus", "merkmale": {"kueche": "regional", "preis": "25 €"}},
        {"id": "V-05.b", "titel": "Pizzeria", "merkmale": {"kueche": "italienisch"}}]}
    erg, fehler = mk_bauen(r)
    assert fehler == []
    w = next(x for x in erg["wahlstellen"] if x["id"] == "V-05")
    assert w["bereich"] == "restaurant" and w["an_ids"] == ["O-02", "U-01", "E-01"] and w["an"] == []
    assert w["optionen"][1]["fehlt"] == ["preis"]
    assert [k["id"] for k in erg["merkmale"]["restaurant"]] == ["kueche", "preis"]
    assert not any("nirgends verwendet" in x["text"] for x in erg["warnungen"] if x["bezug"] == "V-05")


@pytest.mark.parametrize("an, meldung", [(["T-99"], "gibt es nicht"), (["X-1"], "weder Tag"), ("T-01", "Liste")])
def test_an_fehler(an, meldung):
    r = roh()
    r["wahlstellen"]["V-03"]["an"] = an
    assert any(meldung in f for f in mk_bauen(r)[1])


def test_neue_art_ohne_merkmale_ist_fehler():
    r = roh()
    r["merkmale"] = {"restaurant": {}}
    assert any("Bereich" in f for f in mk_bauen(r)[1])


# ---------- Regeln zwischen Optionen und Anschluss (Paket 4, #18) ----------
def opt_aus(erg, oid):
    return next(o for w in erg["wahlstellen"] for o in w["optionen"] if o["id"] == oid)


def test_erfordert_verletzt_im_plan_und_in_benanntem_plan():
    r = roh()
    option(r, "V-03.b")["erfordert"] = ["V-02.b"]
    r["plaene"] = [{"id": "P-A", "auswahl": ["V-01.a", "V-03.b"]}]
    erg = ok(r)
    # V-03.b steht nicht im Plan: keine Verletzung, aber die Seite kennt die Regel
    assert not [t for t in texte(erg) if "voraus" in t]
    assert opt_aus(erg, "V-03.b")["erfordert"] == [{"id": "V-02.b", "titel": "B2", "wahl": "V-02", "im_plan": False,
                                                    "gueltig": True}]
    # im benannten Plan schon: die Warnung geht nicht im Filter für Wahlstellen-Hinweise verloren
    p = erg["plaene"][0]
    assert any("V-03.b „Abzweig“ setzt V-02.b „B2“ voraus, im Plan ist V-02.a." == w["text"] for w in p["warnungen"])
    option(r, "V-03.b")["verlauf"] = verlauf(("gewaehlt", "Ida", {}))
    erg = ok(r)
    assert "V-03.b „Abzweig“ setzt V-02.b „B2“ voraus, im Plan ist V-02.a." in texte(erg)
    assert next(w for w in erg["warnungen"] if "voraus" in w["text"])["bezug"] == "plan"
    assert opt_aus(erg, "V-03.b")["im_plan"] and not opt_aus(erg, "V-03.a")["im_plan"]


def test_erfordert_wahlstelle_ausserhalb_des_plans():
    r = roh()
    option(r, "V-01.b")["erfordert"] = ["V-02.b"]
    option(r, "V-01.b")["verlauf"] = verlauf(("gewaehlt", "Ida", {}))
    erg = ok(r)
    # V-02 hängt an T-01, das mit V-01.b nicht im Plan ist: dort zählt die Auswahl nicht
    assert "V-01.b „Mit Bus“ setzt V-02.b „B2“ voraus, V-02 liegt nicht im Plan." in texte(erg)
    assert not opt_aus(erg, "V-02.a")["im_plan"] and not opt_aus(erg, "V-03.a")["im_plan"]


def test_schliesst_aus_gilt_in_beide_richtungen():
    r = roh()
    option(r, "V-02.a")["schliesst_aus"] = ["V-03.a"]
    erg = ok(r)
    assert "V-02.a „B1“ und V-03.a „Hauptweg“ schließen sich aus, stehen aber beide im Plan." in texte(erg)
    assert [x["id"] for x in opt_aus(erg, "V-03.a")["schliesst_aus"]] == ["V-02.a"]
    option(r, "V-02.b")["verlauf"] = verlauf(("gewaehlt", "Ida", {}))
    assert not [t for t in texte(ok(r)) if "schließen sich aus" in t]


def test_regeln_fehler_und_hinweise():
    r = roh()
    option(r, "V-01.a")["erfordert"] = ["V-09.a", "V-01.b", "V-02.a", "V-02.b"]
    option(r, "V-01.b")["schliesst_aus"] = "V-02.a"
    option(r, "V-03.a")["erfordert"] = ["V-02.a"]
    option(r, "V-03.a")["schliesst_aus"] = ["V-02.a"]
    f = nur_fehler(r)
    assert "V-01.a: erfordert V-09.a – diese Option gibt es nicht." in f
    assert "V-01.a: erfordert V-01.b gehört zur selben Wahlstelle V-01" in f
    assert "V-01.a: erfordert V-02.a, V-02.b – von V-02 kann nur eine Option im Plan stehen." in f
    assert "V-01.b: schliesst_aus muss eine Liste" in f
    assert "V-03.a: V-02.a steht unter erfordert und schliesst_aus." in f
    r = roh()
    option(r, "V-03.b")["erfordert"] = ["V-02.b"]
    option(r, "V-02.b")["verlauf"] = verlauf(("verworfen", "Ida", {}))
    erg = ok(r)
    assert {"bezug": "V-03.b", "text": "V-03.b setzt V-02.b voraus, aber V-02.b ist verworfen."} in erg["warnungen"]
    assert opt_aus(erg, "V-03.b")["erfordert"][0]["gueltig"] is False


def anschluss(erg, oid):
    return (opt_aus(erg, oid)["merkmale"].get("anschluss") or {}).get("wert")


def test_anschluss_zeigt_luecken_wie_der_plan():
    r = roh()
    r["wahlstellen"]["V-01"]["optionen"] += [{"id": "V-01.c", "titel": "Gleich nach C", "folge": []},
                                            {"id": "V-01.d", "titel": "Noch nicht ausgearbeitet"}]
    erg = ok(r)
    assert anschluss(erg, "V-01.a") == "nahtlos"
    # T-04 beginnt mit dem Bus in B, der Plan steht davor in A (Reisebeginn)
    assert anschluss(erg, "V-01.b") == "Lücke am Anfang: A → B"
    assert anschluss(erg, "V-01.c") == "Lücke: A → C"          # ohne Tage: davor A, danach Reiseende in C
    assert anschluss(erg, "V-01.d") is None                      # ohne folge: nichts zu berechnen
    assert opt_aus(erg, "V-01.a")["merkmale"]["anschluss"]["notiz"] == \
        "Berechnet aus dem aktuellen Plan: davor Reisebeginn in A, danach Reiseende in C."
    assert "anschluss" not in opt_aus(erg, "V-01.d")["fehlt"]
    # Dieselbe Lücke meldet der Plan, sobald die Option gilt
    option(r, "V-01.b")["verlauf"] = verlauf(("gewaehlt", "Ida", {}))
    erg = ok(r)
    assert anschluss(erg, "V-01.b") == "Lücke am Anfang: A → B"
    assert "T-04: Lücke – der Tag steht in A, E-03 beginnt in B." in texte(erg)


def test_anschluss_verschachtelt_und_nur_im_plan():
    r = roh()
    r["tage"]["T-05"]["nacht"] = None
    r["tage"]["T-06"] = {"titel": "Ruhetag in C", "nacht": "U-03"}
    r["wahlstellen"]["V-01"]["optionen"][1]["folge"] = ["T-04", "V-04"]
    r["wahlstellen"]["V-04"] = {"titel": "Noch ein Tag?", "art": "planung", "frage": "F-01", "optionen": [
        {"id": "V-04.a", "titel": "Ruhetag", "folge": ["T-06"]},
        {"id": "V-04.b", "titel": "Weiter nach B", "folge": ["T-05"]}]}
    r["tage"]["T-05"] = {"titel": "Zurück nach B", "nacht": "U-01"}
    erg = ok(r)
    # V-04 liegt in V-01.b; mit V-01.a im Plan gibt es dort keinen Anschluss
    assert anschluss(erg, "V-04.a") is None and anschluss(erg, "V-04.b") is None
    option(r, "V-01.b")["verlauf"] = verlauf(("gewaehlt", "Ida", {}))
    erg = ok(r)
    assert anschluss(erg, "V-04.a") == "nahtlos"
    assert anschluss(erg, "V-04.b") == "Lücke am Anfang: C → B; Lücke am Ende: B → C"


def test_anschluss_stimmt_mit_den_warnungen_der_beispielreise():
    """Für die Optionen im Plan: „Lücke am Anfang“ genau dann, wenn der Plan am ersten Tag eine Lücke meldet."""
    import yaml
    wurzel = Path(__file__).resolve().parent.parent.parent / "beispiel/reisen/beispielreise"
    roh_ = yaml.safe_load((wurzel / "plan/routen.yaml").read_text(encoding="utf-8"))
    for oid in ("V-01.a", "V-01.b", "V-01.c"):
        r = copy.deepcopy(roh_)
        v = next(o for o in r["wahlstellen"]["V-01"]["optionen"] if o["id"] == oid)
        v["verlauf"] = (v.get("verlauf") or []) + [{"datum": D(2026, 10, 30), "status": "gewaehlt", "wer": "Ida"}]
        fehler = []
        erg = Routen(r, {}, {"F-01": "offen", "F-02": "geklärt"}, fehler, lambda *a: None, entscheider=["Ida"]).bauen()
        erster = opt_aus(erg, oid)["tage"][0]
        luecke = any(w["bezug"] == erster and ("Lücke" in w["text"] or "fehlt" in w["text"]) for w in erg["warnungen"])
        assert ("Lücke am Anfang" in anschluss(erg, oid)) == luecke, (oid, erg["warnungen"])
