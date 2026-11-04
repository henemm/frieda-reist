"""item_create und item_update auf die Form (ADR-0007, Schritt c, frieda-reist#284): wenige Parameter, die Sonderfelder stehen in
merkmale; value_set, location_set und track_attach (deutsch wert_eintragen, lage_eintragen, track_anhaengen) sind Aliase und
kommen beim Schreibweg als item_update an."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import schreiben as sb  # noqa: E402
from test_konnektor import ALT_ORGANISATOR, KARL, Schreibweg, dienst, rpc, schreibweg, seiten, werkzeug  # noqa: E402,F401
from test_schreiben import IDA, KARL as KARL_S, repo, routen_auf_main, schreiber  # noqa: E402,F401

ALIASE = (
    ("value_set", dict(target="U-02", attribute="preis", value="95 €", source="Website", checked="2026-10-29"),
     {"ziel": "U-02", "merkmal": "preis", "wert": "95 €", "quelle": "Website", "geprueft": "2026-10-29"}),
    ("wert_eintragen", dict(ziel="U-02", merkmal="preis", wert="95 €", quelle="Website", geprueft="2026-10-29"),
     {"ziel": "U-02", "merkmal": "preis", "wert": "95 €", "quelle": "Website", "geprueft": "2026-10-29"}),
    ("location_set", dict(target="U-02", address="Am Markt 3", coordinates="50.97, 14.1", source="Website"),
     {"ziel": "U-02", "adresse": "Am Markt 3", "koordinaten": "50.97, 14.1", "quelle": "Website"}),
    ("lage_eintragen", dict(ziel="U-02", adresse="Am Markt 3", koordinaten="50.97, 14.1", quelle="Website"),
     {"ziel": "U-02", "adresse": "Am Markt 3", "koordinaten": "50.97, 14.1", "quelle": "Website"}),
    ("track_attach", dict(target="E-20", gpx_text="<gpx/>", source="Aufzeichnung"),
     {"ziel": "E-20", "gpx": "<gpx/>", "quelle": "Aufzeichnung"}),
    ("track_anhaengen", dict(ziel="E-20", gpx="<gpx/>", quelle="Aufzeichnung"),
     {"ziel": "E-20", "gpx": "<gpx/>", "quelle": "Aufzeichnung"}),
)


@pytest.mark.parametrize("name, args, erwartet", ALIASE)
def test_alias_kommt_als_item_update_an(schreibweg, monkeypatch, name, args, erwartet):
    basis, _ = schreibweg
    monkeypatch.setattr(Schreibweg, "antwort", (200, {"ok": True, "text": "ok"}))   # der Stummel ist klassenweit: nach dem Test zurück
    t, f = werkzeug(basis, KARL, name, **args)
    pfad, _, body = Schreibweg.anfragen[-1]
    assert not f and pfad == "/beispielreise/ding_aendern", (t, pfad)
    assert body["args"] == erwartet


def test_alte_parameter_von_item_create_gelten_weiter(schreibweg, monkeypatch):
    """Laufende Gespräche: ort, von, nach, ab, an, beginn, adresse … (deutsch und englisch) stehen nicht mehr im Schema, werden aber
    angenommen und unverändert an den Schreibweg gegeben."""
    basis, _ = schreibweg
    monkeypatch.setattr(Schreibweg, "antwort", (200, {"ok": True, "text": "ok"}))
    werkzeug(basis, KARL, "item_create", what="strecke", title="Bus", kind="bus", from_place="O-01", to_place="O-02", departure="09:00", arrival="10:00",
             source="Fahrplan")
    a = Schreibweg.anfragen[-1][2]["args"]
    assert (a["von"], a["nach"], a["ab"], a["an"], a["art"]) == ("O-01", "O-02", "09:00", "10:00", "bus")
    werkzeug(basis, KARL, "ding_anlegen", was="aufenthalt", titel="X", ort="O-03", art="besichtigung", beginn="10:00", quelle="q")
    a = Schreibweg.anfragen[-1][2]["args"]
    assert (a["ort"], a["beginn"]) == ("O-03", "10:00")


def test_item_update_aendert_felder_und_merkmale_in_einem_aufruf(repo):
    _, origin, _, _ = repo
    s = schreiber(repo)
    a = s.schreiben("beispielreise", "ding_aendern", {**KARL_S, "args": {
        "ziel": "U-02", "quelle": "Website", "geprueft": "2026-11-03", "hinweis": "neu",
        "merkmale": {"adresse": "Am Markt 3", "koordinaten": [50.97, 14.1], "preis": "95 €"}}})
    assert a["ok"]
    r, _ = routen_auf_main(origin)
    u = r["unterkuenfte"]["U-02"]
    assert u["hinweis"] == "neu" and u["merkmale"]["preis"]["wert"] == "95 €"
    assert u["merkmale"]["adresse"]["wert"] == "Am Markt 3" and u["merkmale"]["koordinaten"]["wert"] == [50.97, 14.1]
    assert u["quelle"] == "erfunden (Beispiel)"   # quelle gehört mit merkmale den Angaben, nicht dem Ding


def test_item_update_mit_gestalten_der_alten_werkzeuge(repo):
    _, origin, _, _ = repo
    s = schreiber(repo)
    # Gestalt von wert_eintragen
    s.schreiben("beispielreise", "ding_aendern", {**KARL_S, "args": {"ziel": "U-02", "merkmal": "preis", "wert": "99 €", "quelle": "Website", "geprueft": "2026-11-03"}})
    r, _ = routen_auf_main(origin)
    assert r["unterkuenfte"]["U-02"]["merkmale"]["preis"]["wert"] == "99 €"
    s.vorbereiten()
    # Gestalt von lage_eintragen
    s.schreiben("beispielreise", "ding_aendern", {**KARL_S, "args": {"ziel": "O-01", "koordinaten": "51.04, 13.73", "quelle": "OSM"}})
    r, _ = routen_auf_main(origin)
    assert r["orte"]["O-01"]["merkmale"]["koordinaten"]["wert"] == [51.04, 13.73]
    s.vorbereiten()
    with pytest.raises(sb.Ablehnung):   # ohne Herkunft
        s.schreiben("beispielreise", "ding_aendern", {**KARL_S, "args": {"ziel": "U-02", "merkmale": {"adresse": "Am Markt 3"}}})


def test_item_create_nimmt_ort_zeit_und_festes_in_merkmale(repo):
    _, origin, _, _ = repo
    s = schreiber(repo)
    s.schreiben("beispielreise", "ding_anlegen", {**KARL_S, "args": {
        "was": "aufenthalt", "titel": "Café am Markt", "art": "besichtigung", "quelle": "Beispiel",
        "merkmale": {"ort": "O-03", "zeit": "morgens", "zeitraum": "08:00-10:00", "koordinaten": "50.97, 14.1"}}})
    r, _ = routen_auf_main(origin)
    a = next(x for x in r["aufenthalte"].values() if x["name"] == "Café am Markt")
    assert a["ort"] == "O-03" and a["zeit"] == "morgens" and a["merkmale"]["zeitraum"]["wert"] == {"beginn": "08:00", "ende": "10:00"}
    s.vorbereiten()
    s.schreiben("beispielreise", "ding_anlegen", {**KARL_S, "args": {
        "was": "strecke", "titel": "Bus", "art": "bus", "quelle": "Fahrplan",
        "merkmale": {"von": "O-01", "nach": "O-02", "abfahrt": "09:00", "ankunft": "10:15"}}})
    r, _ = routen_auf_main(origin)
    e = next(x for x in r["strecken"].values() if x.get("titel") == "Bus")
    assert (e["von"], e["nach"]) == ("O-01", "O-02") and e["merkmale"]["abfahrt"]["wert"] == "09:00" and e["merkmale"]["ankunft"]["wert"] == "10:15"
    s.vorbereiten()
    with pytest.raises(sb.Ablehnung):   # ort doppelt: oben und in merkmale
        s.schreiben("beispielreise", "ding_anlegen", {**KARL_S, "args": {"was": "aufenthalt", "titel": "Y", "art": "besichtigung", "quelle": "q",
                                                                          "ort": "O-03", "merkmale": {"ort": "O-01"}}})


def test_item_update_nimmt_koordinaten_heraus(repo):
    """Leerer Text entfernt einen Wert, auch die Koordinaten (PO 4.11.2026): Das Ding bleibt mit Adresse, steht aber nicht mehr
    auf der Karte; der alte Wert steht in der Antwort und im Verlauf (Commit)."""
    _, origin, _, _ = repo
    s = schreiber(repo)
    s.schreiben("beispielreise", "ding_aendern", {**KARL_S, "args": {"ziel": "A-01", "quelle": "Test",
                "merkmale": {"adresse": "Burgweg 1, 01848 Hohnstein", "koordinaten": [50.9785, 14.114]}}})
    s.vorbereiten()
    a = s.schreiben("beispielreise", "ding_aendern", {**KARL_S, "args": {"ziel": "A-01", "quelle": "Ida im Gespräch (Test)",
                    "grund": "zu weit weg", "merkmale": {"koordinaten": ""}}})
    assert a["ok"] and "50.9785, 14.114" in a["text"] and "nicht mehr auf der Karte" in a["text"], a["text"]
    assert "fehlen noch Koordinaten" not in a["text"]
    r, _ = routen_auf_main(origin)
    m = r["aufenthalte"]["A-01"]["merkmale"]
    assert not any(isinstance(v, dict) and v.get("typ") == "koordinaten" for v in m.values()), m
    assert "punkt" not in r["aufenthalte"]["A-01"] and m["adresse"]["wert"] == "Burgweg 1, 01848 Hohnstein"
    s.vorbereiten()
    with pytest.raises(sb.Ablehnung):   # ohne Koordinaten gibt es nichts herauszunehmen
        s.schreiben("beispielreise", "ding_aendern", {**KARL_S, "args": {"ziel": "A-01", "quelle": "x", "merkmale": {"koordinaten": ""}}})
