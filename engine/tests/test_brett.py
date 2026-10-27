"""Tests für Paket G: Wunsch-Brett (Spalten, Punkte im Kontingent, eingeplant, erlebt, Bilanz) gegen die Beispielreise."""
import json
import shutil
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bauen  # noqa: E402
import konten  # noqa: E402
import rueckmeldungen as rm  # noqa: E402
from test_regeln import BEISPIEL, anfrage, umgebung  # noqa: E402,F401  (umgebung: Fixture)

VORSCHLAG = "R-20261021-091500-a1b2"   # steht in beispiel/…/plan/wuensche.yaml


def wunsch(u, name, text):
    code, e = anfrage(f"{u.rurl}/beispielreise/rueckmeldungen", {"name": name, "art": "Wunsch", "text": text})
    assert code == 201, e
    return e["id"]


def aendern(u, rid, **roh):
    """Wie der Konnektor: mit dem Dienst-Geheimnis, der Name ist die erkannte Person."""
    import urllib.error
    import urllib.request
    req = urllib.request.Request(f"{u.rurl}/beispielreise/rueckmeldungen/{rid}", data=json.dumps(roh).encode(),
                                 method="PATCH", headers={"Content-Type": "application/json",
                                                          "X-Frieda-Dienst": konten.dienst_geheimnis()})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")


def brett(u):
    code, b = anfrage(f"{u.rurl}/beispielreise/brett", methode="GET")
    assert code == 200, b
    return b


def spalten(u):
    return {w["id"]: w["spalte"] for w in brett(u)["wuensche"]}


def setze(rid, status):
    rm.setze("beispielreise", rid, status, "Test")


def test_spalten_und_bilanz(umgebung, capsys):
    u = umgebung()
    a = wunsch(u, "Karl", "Einmal Kirnitzschtalbahn fahren")
    b = wunsch(u, "Ida", "Abends in Hohnstein essen")
    c = wunsch(u, "Karl", "Baden in der Elbe")
    assert set(spalten(u).values()) == {"eingebracht"}
    setze(a, "uebernommen")
    setze(c, "verworfen")
    assert spalten(u) == {a: "geprueft", b: "eingebracht", c: "passt_nicht"}
    bl = {z["name"]: z for z in brett(u)["bilanz"]}
    # Alle, die Wünsche einbringen dürfen, stehen in der Bilanz (Kim reist nur mit und liest)
    assert set(bl) == {"Ida", "Karl", "Max"}
    assert bl["Karl"]["wuensche"] == 2 and bl["Karl"]["geprueft"] == 1 and bl["Karl"]["passt_nicht"] == 1
    assert bl["Max"] == {"name": "Max", "wuensche": 0, "eingebracht": 0, "geprueft": 0, "eingeplant": 0, "erlebt": 0,
                         "passt_nicht": 0, "punkte": 0, "frei": 10}
    assert [s["id"] for s in brett(u)["spalten"]] == list(rm.SPALTEN)


def test_punkte_nur_eigene_und_im_kontingent(umgebung):
    u = umgebung()
    a = wunsch(u, "Karl", "Kirnitzschtalbahn")
    b = wunsch(u, "Karl", "Bastei bei Sonnenaufgang")
    assert aendern(u, a, name="Karl", punkte=6)[0] == 200
    code, f = aendern(u, b, name="Karl", punkte=5)
    assert code == 409 and "noch 4 von 10" in f["fehler"]
    assert aendern(u, b, name="karl", punkte=4)[0] == 200          # Name ohne Rücksicht auf Groß/klein
    code, f = aendern(u, a, name="Ida", punkte=1)                   # fremde Wünsche: nein, auch nicht als Bestimmer
    assert code == 403 and "Karl" in f["fehler"]
    assert aendern(u, a, name="Karl", punkte=2)[0] == 200          # umverteilen
    bl = {z["name"]: z for z in brett(u)["bilanz"]}
    assert bl["Karl"]["punkte"] == 6 and bl["Karl"]["frei"] == 4
    # Ein Wunsch, der nicht passt, gibt seine Punkte frei und nimmt keine mehr
    setze(b, "verworfen")
    assert aendern(u, a, name="Karl", punkte=10)[0] == 200
    assert aendern(u, b, name="Karl", punkte=1)[0] == 409
    for falsch in (-1, 101, True, "3", 2.5):
        assert aendern(u, a, name="Karl", punkte=falsch)[0] == 400
    w = next(x for x in brett(u)["wuensche"] if x["id"] == a)
    assert w["punkte"] == 10 and [e["felder"]["punkte"] for e in w["verlauf"]] == [[0, 6], [6, 2], [2, 10]]


def test_erlebt_alle_unterwegs_und_danach(umgebung):
    u = umgebung()
    a = wunsch(u, "Ida", "Kirnitzschtalbahn")
    code, f = aendern(u, a, name="Karl", erlebt=True)
    assert code == 409 and "unterwegs" in f["fehler"]                # vor der Reise noch nicht

    u = umgebung("unterwegs")
    a = wunsch(u, "Ida", "Kirnitzschtalbahn")
    assert aendern(u, a, name="Karl", erlebt=True)[0] == 200        # alle Einbringer, auch fremde Wünsche
    assert aendern(u, a, name="Karl", erlebt=True)[0] == 200        # noch einmal (Nachreichen ohne Netz): keine Änderung
    w = brett(u)["wuensche"][0]
    assert w["spalte"] == "erlebt" and w["erlebt"]["wer"] == "Karl" and len(w["verlauf"]) == 1
    assert aendern(u, a, name="Kim", erlebt=False)[0] == 403        # reisend: nur lesen
    code, f = anfrage(f"{u.rurl}/beispielreise/rueckmeldungen/{a}", methode="DELETE")
    assert code == 409 and "Brett" in f["fehler"]                   # Abgehaktes wird nicht zurückgezogen
    assert aendern(u, a, name="Ida", erlebt=False, kommentar="doch nicht gefahren")[0] == 200
    w = brett(u)["wuensche"][0]
    assert w["spalte"] == "eingebracht" and w["verlauf"][-1]["kommentar"] == "doch nicht gefahren"

    u = umgebung("danach")                                            # Nachlese: abhaken ja, neue Wünsche nein
    assert anfrage(f"{u.rurl}/beispielreise/rueckmeldungen", {"name": "Ida", "art": "Wunsch", "text": "x"})[0] == 403
    (u.o / "eingang.jsonl").write_text(json.dumps({"id": VORSCHLAG, "name": "Karl", "art": "Wunsch", "ziel": "wuensche",
                                                   "text": "Kirnitzschtalbahn", "quelle": "", "erstellt": "2026-10-21T09:15:00+00:00"}) + "\n")
    assert aendern(u, VORSCHLAG, name="Karl", erlebt=True)[0] == 200
    assert aendern(u, VORSCHLAG, name="Karl", punkte=3)[0] == 403
    assert aendern(u, VORSCHLAG, name="Ida", eingeplant=True)[0] == 403

    u = umgebung("archiv")
    (u.o / "eingang.jsonl").write_text(json.dumps({"id": VORSCHLAG, "name": "Karl", "art": "Wunsch", "ziel": "wuensche",
                                                   "text": "x", "erstellt": "2026-10-21T09:15:00+00:00"}) + "\n")
    assert aendern(u, VORSCHLAG, name="Karl", erlebt=True)[0] == 403


def test_einplanen_nur_bestimmer(umgebung):
    u = umgebung()
    a = wunsch(u, "Karl", "Abends in Hohnstein essen")
    code, f = aendern(u, a, name="Karl", eingeplant=True)
    assert code == 403 and "Bestimmer" in f["fehler"]
    assert aendern(u, a, name="Ida", bezug=["T-02"])[0] == 400       # bezug nur zusammen mit eingeplant
    assert aendern(u, a, name="Ida", eingeplant=True, bezug=["T-02"])[0] == 200
    w = brett(u)["wuensche"][0]
    assert w["spalte"] == "eingeplant" and w["eingeplant"] == {"wer": "Ida", "datum": w["eingeplant"]["datum"],
                                                               "bezug": ["T-02"]}
    assert aendern(u, a, name="Ida", eingeplant=True, bezug=["T-03"])[0] == 200   # andere Stelle: geändert
    # Ohne Dienst-Geheimnis ist es die Seite (auch ohne X-Forwarded-For): ein eingetippter Name plant nie ein
    for kopf in ({}, {"X-Forwarded-For": "203.0.113.5"}, {"X-Frieda-Dienst": "falsch"}):
        import urllib.error
        import urllib.request
        req = urllib.request.Request(f"{u.rurl}/beispielreise/rueckmeldungen/{a}", method="PATCH",
                                     data=json.dumps({"name": "Ida", "eingeplant": False}).encode(),
                                     headers={"Content-Type": "application/json", **kopf})
        with pytest.raises(urllib.error.HTTPError) as f:
            urllib.request.urlopen(req)
        assert f.value.code == 403 and "Bestimmer" in json.loads(f.value.read())["fehler"]
    assert brett(u)["wuensche"][0]["eingeplant"]["bezug"] == ["T-03"]
    assert len(brett(u)["wuensche"][0]["verlauf"]) == 2
    assert aendern(u, "R-20991231-000000-0000", name="Ida", eingeplant=True)[0] == 404
    assert aendern(u, a, name="Ida")[0] == 400                        # nichts zu ändern


def test_vorschlag_aus_dem_repo(umgebung):
    u = umgebung()
    (u.o / "eingang.jsonl").write_text(json.dumps({"id": VORSCHLAG, "name": "Karl", "art": "Wunsch", "ziel": "wuensche",
                                                   "text": "Kirnitzschtalbahn", "quelle": "",
                                                   "erstellt": "2026-10-21T09:15:00+00:00"}) + "\n")
    w = brett(u)["wuensche"][0]
    assert w["vorschlag"]["bezug"] == ["T-05", "V-01"] and w["vorschlag"]["option"] == "V-01.b"
    assert w["vorschlag"]["gewaehlt"] is False and w["spalte"] == "eingebracht"
    # Wählt ein Bestimmer die Option, die aus dem Wunsch wurde, ist er eingeplant
    assert rm.spalte({"status": "uebernommen"}, {}, {**w["vorschlag"], "gewaehlt": True}) == "eingeplant"
    assert rm.spalte({"status": "verworfen"}, {"erlebt": {"wer": "Karl"}}, None) == "passt_nicht"


def test_kontingent_anzahl(umgebung):
    u = umgebung(regeln={"kontingent": {"art": "anzahl", "je_person": 1}})
    a = wunsch(u, "Karl", "Kirnitzschtalbahn")
    code, f = anfrage(f"{u.rurl}/beispielreise/rueckmeldungen", {"name": "Karl", "art": "Wunsch", "text": "Bastei"})
    assert code == 409 and "Höchstens 1" in f["fehler"]
    # Dasselbe noch einmal senden (Ausgang ohne Netz) ist kein neuer Wunsch
    code, e = anfrage(f"{u.rurl}/beispielreise/rueckmeldungen", {"name": "Karl", "art": "Wunsch", "text": "Kirnitzschtalbahn"})
    assert code == 200 and e["id"] == a
    assert wunsch(u, "Ida", "Bastei")                                 # jede Person hat ihr eigenes Kontingent
    code, f = aendern(u, a, name="Karl", punkte=1)
    assert code == 400 and "keine Punkte" in f["fehler"]
    bl = {z["name"]: z for z in brett(u)["bilanz"]}
    assert bl["Karl"]["frei"] == 0 and "punkte" not in bl["Karl"]
    setze(a, "verworfen")                                             # passt nicht: Platz für einen neuen
    assert wunsch(u, "Karl", "Bastei")


def test_baustein_aus(umgebung):
    u = umgebung(bausteine=["varianten", "rueckmeldungen"])
    (u.o / "eingang.jsonl").write_text(json.dumps({"id": VORSCHLAG, "name": "Karl", "art": "Wunsch", "ziel": "wuensche",
                                                   "text": "x", "erstellt": "2026-10-21T09:15:00+00:00"}) + "\n")
    code, f = aendern(u, VORSCHLAG, name="Karl", punkte=1)
    assert code == 403 and "wuensche" in f["fehler"]


def test_vorschlaege_werden_geprueft(tmp_path):
    q = tmp_path / "q"
    shutil.copytree(BEISPIEL, q)
    datei = q / "plan" / "wuensche.yaml"
    datei.write_text(yaml.safe_dump({"R-1": {"bezug": ["T-01"]},
                                     "R-20261021-091500-a1b3": {"bezug": ["T-99"], "option": "V-09.z"},
                                     "R-20261021-091500-a1b4": {"bezug": ["T-01"], "punkte": 3}}), encoding="utf-8")
    with pytest.raises(bauen.BauFehler) as f:
        bauen.bauen(q, tmp_path / "s")
    t = "\n".join(f.value.meldungen)
    assert "R-1: Schlüssel muss eine Wunsch-ID sein" in t
    assert "T-99 gibt es nicht" in t and "Option V-09.z gibt es an keiner Wahlstelle" in t
    assert "a1b4: erlaubt sind bezug" in t
    # Gewählte Option: der Wunsch gilt als eingeplant
    datei.write_text(yaml.safe_dump({VORSCHLAG: {"bezug": ["T-03"], "option": "V-03.a"}}), encoding="utf-8")
    bauen.bauen(q, tmp_path / "s2")
    d = json.loads((tmp_path / "s2" / "daten.json").read_text(encoding="utf-8"))
    assert d["wunsch_vorschlaege"][VORSCHLAG] == {"bezug": ["T-03"], "notiz": "", "option": "V-03.a", "gewaehlt": True}


# ---------- Claude-App (Konnektor) ----------

def test_brett_in_der_claude_app(umgebung):
    from test_regeln import IDA, KARL, KIM
    u = umgebung()
    assert {"wuensche", "wunsch_aendern"} <= u.werkzeuge(KARL)
    assert "wuensche" in u.werkzeuge(KIM) and "wunsch_aendern" not in u.werkzeuge(KIM)   # reisend: nur lesen
    t, f = u.werkzeug(KARL, "rueckmeldung_geben", art="Wunsch", text="Einmal Kirnitzschtalbahn fahren")
    assert not f, t
    rid = rm.wuensche(u.o)[0]["id"]
    t, f = u.werkzeug(KARL, "wunsch_aendern", id=rid, punkte=4)
    assert not f and "4 Punkte" in t, t
    t, f = u.werkzeug(IDA, "wunsch_aendern", id=rid, punkte=1)
    assert f and "Karl" in t                                           # fremde Punkte: nein
    t, f = u.werkzeug(KARL, "wunsch_aendern", id=rid, eingeplant=True)
    assert f and "Bestimmer" in t
    t, f = u.werkzeug(IDA, "wunsch_aendern", id=rid, eingeplant=True, bezug=["T-99"])
    assert f and "T-99" in t
    t, f = u.werkzeug(IDA, "wunsch_aendern", id=rid, eingeplant=True, bezug=["T-03"])
    assert not f and "eingeplant" in t, t
    # Link ohne Person: Einplanen ist eine Entscheidung und gehört genau einer Person
    import konnektor as kn
    kn.zugaenge_pfad().write_text(json.dumps({**kn.zugaenge(), "b" * 32: {"reise": "beispielreise", "rolle": "bestimmer"}}))
    t, f = u.werkzeug("b" * 32, "wunsch_aendern", id=rid, eingeplant=False)
    assert f and "persönlichen Link" in t
    t, f = u.werkzeug(KARL, "wunsch_aendern", id="R-1", punkte=1)
    assert f and "R-…" in t
    t, _ = u.werkzeug(KIM, "wuensche")
    assert "### Eingeplant (1)" in t and f"{rid} · Karl · 4 Punkte: Einmal Kirnitzschtalbahn fahren" in t
    assert "Eingeplant von Ida" in t and "T-03 " in t and "- Karl: 1 Wünsche, 1 eingeplant, 0 erlebt, 6 von 10 Punkten frei" in t
    t, _ = u.werkzeug(KARL, "ueberblick")
    assert "## Wünsche: 1 (eingeplant 1) (Werkzeug wuensche)" in t


def test_brett_in_der_claude_app_ausgeschaltet(umgebung):
    from test_regeln import IDA
    u = umgebung(bausteine=["varianten", "rueckmeldungen"])
    assert not {"wuensche", "wunsch_aendern"} & u.werkzeuge(IDA)
    t, f = u.werkzeug(IDA, "wuensche")
    assert f and "ausgeschaltet" in t
    assert "Wünsche" not in u.werkzeug(IDA, "ueberblick")[0]


def test_liste_zeigt_punkte_fuer_das_einarbeiten(umgebung, capsys):
    u = umgebung()
    a = wunsch(u, "Karl", "Kirnitzschtalbahn")
    assert aendern(u, a, name="Karl", punkte=7)[0] == 200
    capsys.readouterr()
    rm.liste("beispielreise", False)
    t = capsys.readouterr().out
    assert "WUNSCH (7 Punkte von Karl)" in t and "plan/wuensche.yaml" in t and "nie einplanen" in t
