"""Tests für engine/rueckmeldungen.py: HTTP-Dienst und Kommandozeile."""
import json
import sys
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import rueckmeldungen as rm  # noqa: E402

GUT = {"name": "Ida", "art": "Kommentar", "ziel": "T-01", "text": "Wir landen erst 21 Uhr."}


@pytest.fixture
def dienst(tmp_path, monkeypatch):
    monkeypatch.setenv("RM_ABLAGE", str(tmp_path))
    (tmp_path / "beispielreise").mkdir()
    rm._zeiten.clear()
    s = ThreadingHTTPServer(("127.0.0.1", 0), rm.Dienst)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{s.server_address[1]}", tmp_path
    s.shutdown()


def anfrage(url, methode="GET", daten=None, roh=None):
    body = roh if roh is not None else (json.dumps(daten).encode() if daten is not None else None)
    req = urllib.request.Request(url, data=body, method=methode, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")


def post(basis, **aenderung):
    return anfrage(basis + "/beispielreise/rueckmeldungen", "POST", {**GUT, **aenderung})


def test_senden_und_lesen(dienst):
    basis, ablage = dienst
    code, e = post(basis)
    assert code == 201 and e["status"] == "neu" and rm.RID_MUSTER.match(e["id"])
    code, liste = anfrage(basis + "/beispielreise/rueckmeldungen")
    assert code == 200 and [x["id"] for x in liste] == [e["id"]]
    zeile = json.loads((ablage / "beispielreise/eingang.jsonl").read_text(encoding="utf-8"))
    assert set(zeile) == {"name", "art", "ziel", "text", "quelle", "id", "erstellt"}


def test_fremde_felder_werden_nicht_gespeichert(dienst):
    basis, ablage = dienst
    code, e = post(basis, status="uebernommen", kommentar="selbst gesetzt", id="R-x")
    assert code == 201 and e["status"] == "neu" and e["kommentar"] == ""
    assert "selbst gesetzt" not in (ablage / "beispielreise/eingang.jsonl").read_text(encoding="utf-8")


@pytest.mark.parametrize("aenderung,meldung", [
    ({"art": "These"}, "unbekannte Art"),
    ({"ziel": "../etc"}, "ungültige ID"),
    ({"ziel": ""}, "ungültige ID"),
    ({"text": "   "}, "Text fehlt"),
    ({"name": ""}, "Name fehlt"),
    ({"name": "a\nb"}, "einer Zeile"),
    ({"name": "x" * 81}, "name zu lang"),
    ({"text": 5}, "muss Text sein"),
])
def test_ungueltige_eingaben(dienst, aenderung, meldung):
    code, e = post(dienst[0], **aenderung)
    assert code == 400 and meldung in e["fehler"]


def test_wunsch_ohne_ziel(dienst):
    code, e = post(dienst[0], art="Wunsch", ziel="", text="Rehe in Nara")
    assert code == 201 and e["ziel"] == rm.WUNSCH_ZIEL and e["art"] == "Wunsch"


def test_zu_gross_und_kaputtes_json(dienst):
    basis = dienst[0]
    code, _ = anfrage(basis + "/beispielreise/rueckmeldungen", "POST", roh=b"x" * (rm.MAX_BODY + 1))
    assert code == 413
    code, e = anfrage(basis + "/beispielreise/rueckmeldungen", "POST", roh=b"{kaputt")
    assert code == 400 and "JSON" in e["fehler"]


def test_doppelklick_und_erneutes_senden_aus_dem_ausgang(dienst):
    basis, ablage = dienst
    c1, e1 = post(basis)
    c2, e2 = post(basis)
    assert (c1, c2) == (201, 200) and e1["id"] == e2["id"]
    assert len((ablage / "beispielreise/eingang.jsonl").read_text(encoding="utf-8").splitlines()) == 1


def test_mengenbegrenzung(dienst):
    basis = dienst[0]
    for i in range(rm.MAX_JE_MINUTE):
        assert post(basis, text=f"Nr. {i}")[0] == 201
    code, e = post(basis, text="eine zu viel")
    assert code == 429


def test_unbekannte_reise_und_pfade(dienst):
    basis = dienst[0]
    assert anfrage(basis + "/andere-reise/rueckmeldungen")[0] == 404   # Ordner fehlt
    assert anfrage(basis + "/../beispielreise/rueckmeldungen")[0] == 404
    assert anfrage(basis + "/beispielreise/etwas")[0] == 404
    assert anfrage(basis + "/rueckmeldungen")[0] == 404


def test_gesund(dienst):
    code, e = anfrage(dienst[0] + "/beispielreise/gesund")
    assert code == 200 and e == {"gesund": True}


def test_zurueckziehen_nur_solange_neu(dienst, capsys):
    basis, _ = dienst
    _, a = post(basis, text="erste")
    _, b = post(basis, text="zweite")
    assert anfrage(basis + "/beispielreise/rueckmeldungen/" + a["id"], "DELETE")[0] == 200
    assert anfrage(basis + "/beispielreise/rueckmeldungen/" + a["id"], "DELETE")[0] == 404
    rm.setze("beispielreise", b["id"], "uebernommen", "eingetragen")
    assert anfrage(basis + "/beispielreise/rueckmeldungen/" + b["id"], "DELETE")[0] == 409
    assert anfrage(basis + "/beispielreise/rueckmeldungen/R-unsinn", "DELETE")[0] == 404
    _, liste = anfrage(basis + "/beispielreise/rueckmeldungen")
    assert [(x["text"], x["status"], x["kommentar"]) for x in liste] == [("zweite", "uebernommen", "eingetragen")]


def test_kommandozeile(dienst, capsys):
    basis, _ = dienst
    _, e = post(basis)
    assert rm.main(["liste", "beispielreise"]) == 0
    aus = capsys.readouterr().out
    assert e["id"] in aus and "Wir landen erst 21 Uhr." in aus and "1 Rückmeldung(en)" in aus
    rm.main(["setze", "beispielreise", e["id"], "rueckfrage", "Welche", "Uhrzeit?"])
    rm.main(["liste", "beispielreise"])
    assert "Keine neuen Rückmeldungen" in capsys.readouterr().out
    rm.main(["liste", "beispielreise", "--alle"])
    assert "→ Welche Uhrzeit?" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        rm.setze("beispielreise", e["id"], "erledigt", "")
    with pytest.raises(SystemExit):
        rm.setze("beispielreise", "R-20260101-000000-abcd", "verworfen", "")
    with pytest.raises(SystemExit):
        rm.liste("gibtsnicht", False)


# ---------- Aufgaben ----------

AG = {"name": "Ida", "titel": "Pension Burgblick buchen", "bezug": ["U-02", "T-02"],
      "zustaendig": "Ida", "prioritaet": "hoch", "ab": "2026-11-03", "frist": "2026-11-10"}


def ag(basis, **aenderung):
    return anfrage(basis + "/beispielreise/aufgaben", "POST", {**AG, **aenderung})


def test_aufgabe_anlegen_und_lesen(dienst):
    basis, ablage = dienst
    code, a = ag(basis)
    assert code == 201 and a["id"] == "AG-01" and a["status"] == "offen" and a["erstellt_von"] == "Ida"
    assert a["bezug"] == ["U-02", "T-02"] and a["verlauf"][0]["was"] == "angelegt"
    code, b = ag(basis, titel="Fähre prüfen", bezug="E-22, T-10", prioritaet="normal", ab="", frist="")
    assert b["id"] == "AG-02" and b["bezug"] == ["E-22", "T-10"]
    code, liste = anfrage(basis + "/beispielreise/aufgaben")
    assert code == 200 and [x["id"] for x in liste] == ["AG-01", "AG-02"]
    assert json.loads((ablage / "beispielreise" / "aufgaben.json").read_text())["naechste"] == 3


@pytest.mark.parametrize("aenderung, fehler", [
    ({"titel": ""}, "Titel"), ({"name": ""}, "Name"), ({"frist": "10.11.2026"}, "Datum"),
    ({"frist": "2026-02-30"}, "Datum"), ({"prioritaet": "dringend"}, "Priorität"), ({"status": "fertig"}, "Status"),
    ({"bezug": ["T-01", "kein gültiges!"]}, "ID"), ({"bezug": [f"T-{i:02d}" for i in range(11)]}, "Bezüge"),
    ({"titel": "x" * 201}, "zu lang"), ({"zustaendig": 5}, "Text"),
])
def test_aufgabe_abgelehnt(dienst, aenderung, fehler):
    basis, _ = dienst
    code, a = ag(basis, **aenderung)
    assert code == 400 and fehler in a["fehler"]


def test_aufgabe_aendern_mit_verlauf(dienst):
    basis, _ = dienst
    ag(basis)
    url = basis + "/beispielreise/aufgaben/AG-01"
    code, a = anfrage(url, "PATCH", {"name": "Karl", "status": "erledigt", "kommentar": "gebucht, Bestätigung per Mail"})
    assert code == 200 and a["status"] == "erledigt" and a["erledigt"]
    v = a["verlauf"][-1]
    assert v["wer"] == "Karl" and v["felder"] == {"status": ["offen", "erledigt"]} and "gebucht" in v["kommentar"]
    code, a = anfrage(url, "PATCH", {"name": "Ida", "status": "offen", "frist": ""})
    assert a["erledigt"] == "" and a["frist"] == "" and len(a["verlauf"]) == 3
    code, a = anfrage(url, "PATCH", {"name": "Ida", "status": "offen"})   # nichts geändert: kein Verlaufseintrag
    assert len(a["verlauf"]) == 3
    assert anfrage(url, "PATCH", {"status": "erledigt"})[0] == 400                 # ohne Name
    assert anfrage(basis + "/beispielreise/aufgaben/AG-99", "PATCH", {"name": "H", "status": "erledigt"})[0] == 404
    assert anfrage(basis + "/beispielreise/aufgaben/X-1", "PATCH", {"name": "H"})[0] == 404
    assert anfrage(basis + "/beispielreise/rueckmeldungen/AG-01", "PATCH", {"name": "H"})[0] == 404


def test_aufgaben_ohne_loeschen(dienst):
    basis, _ = dienst
    ag(basis)
    assert anfrage(basis + "/beispielreise/aufgaben/AG-01", "DELETE")[0] == 404


def test_aufgaben_cli(dienst, capsys):
    basis, _ = dienst
    ag(basis, frist="2020-01-01")
    ag(basis, titel="Erledigtes", status="erledigt", prioritaet="niedrig")
    rm.aufgaben_liste("beispielreise", False)
    aus = capsys.readouterr().out
    assert "AG-01" in aus and "ÜBERFÄLLIG" in aus and "Erledigtes" not in aus
    rm.aufgaben_liste("beispielreise", True)
    assert "Erledigtes" in capsys.readouterr().out
