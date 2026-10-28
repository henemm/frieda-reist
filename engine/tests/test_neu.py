"""Neue Reise anlegen, IDs vergeben, Prüfung vor dem Bau (Paket H, engine/neu.py, docs/neue-reise.md)."""
import datetime
import json
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import bauen  # noqa: E402
import neu  # noqa: E402

VON, BIS = datetime.date(2027, 2, 6), datetime.date(2027, 2, 13)
PERSONEN = {"ida": {"name": "Ida", "rolle": "organisator"}, "karl": {"name": "Karl", "rolle": "mitwirkend"},
            "mo": {"name": "Mo", "rolle": "gast", "reist": False}}


def anlegen(tmp_path, **kw):
    args = {"titel": "Skiurlaub im Tal", "von": VON, "bis": BIS, "personen": PERSONEN, "wer": "Ida",
            "ziel": "Oberstdorf", "heute": datetime.date(2026, 10, 27), **kw}
    return neu.anlegen(tmp_path / "reisen", **args)


def test_neue_reise_baut_im_status_idee(tmp_path):
    r = anlegen(tmp_path)
    assert r.name == "skiurlaub-im-tal-2027"
    d = bauen.bauen(r, tmp_path / "dist")
    e = d["reise"]
    assert e["titel"] == "Skiurlaub im Tal" and e["untertitel"] == "Oberstdorf, 6.–13. Februar 2027"
    assert e["zeitraum"] == {"von": "2027-02-06", "bis": "2027-02-13"}
    assert e["status"]["wert"] == "idee" and e["status"]["verlauf"] == [
        {"datum": "2026-10-27", "wert": "idee", "wer": "Ida", "grund": "Reise angelegt (Gespräch in Claude Code)"}]
    assert [(p["name"], p["rolle"], p["reist"]) for p in e["personen"]] == \
        [("Ida", "organisator", True), ("Karl", "mitwirkend", True), ("Mo", "gast", False)]
    assert e["bausteine"] == neu.BAUSTEINE_IDEE and e["verhalten"]["warnungen"] is False
    ids = [a["id"] for a in d["abschnitte"]]
    assert ids == ["W-01", "W-02", "W-03"] and [z["id"] for z in d["fragen"]["zeilen"]] == ["F-01"]
    assert "route" not in d or not d["route"]
    # Vorlage ausgefüllt, nichts bleibt als Platzhalter stehen
    for f in r.rglob("*.md"):
        assert "$" not in f.read_text(encoding="utf-8"), f
    assert "Ida (organisiert), Karl (bringt ein), Mo (liest mit, reist nicht mit)" in (r / "plan/plan.md").read_text(encoding="utf-8")
    assert yaml.safe_load((r / "ids.yaml").read_text(encoding="utf-8")) == {"W": 3, "F": 1}
    assert (r / "medien").is_dir() and (r / "kontext/herkunft.md").exists()


def test_eigener_pfad_herkunft_und_ueberblick(tmp_path):
    r = anlegen(tmp_path, pfad="ski-2027", herkunft="Auftrag A-1 aus der Claude-App", ueberblick="Ein Tal mit Schnee.",
                ziel=None)
    assert r.name == "ski-2027"
    assert "Ein Tal mit Schnee." in (r / "inhalt/wissen.md").read_text(encoding="utf-8")
    assert "Auftrag A-1 aus der Claude-App" in (r / "kontext/herkunft.md").read_text(encoding="utf-8")
    assert yaml.safe_load((r / "reise.yaml").read_text(encoding="utf-8"))["untertitel"] == "6.–13. Februar 2027"
    bauen.bauen(r, tmp_path / "dist")


@pytest.mark.parametrize("kw, text", [
    ({"titel": " "}, "braucht einen Titel"),
    ({"bis": datetime.date(2027, 2, 1)}, "liegt vor dem Anfang"),
    ({"personen": {"karl": {"name": "Karl", "rolle": "mitwirkend"}}}, "Rolle organisator"),
    ({"wer": "Karl"}, "Anlegen darf nur, wer auf der Reise bestimmt"),
    ({"pfad": "Ski Urlaub"}, "nur Kleinbuchstaben"),
])
def test_anlegen_lehnt_ab(tmp_path, kw, text):
    with pytest.raises(neu.Fehler, match=text):
        anlegen(tmp_path, **kw)


def test_vorhandene_reise_wird_nie_ueberschrieben(tmp_path):
    r = anlegen(tmp_path)
    (r / "CLAUDE.md").write_text("eigene Notizen", encoding="utf-8")
    with pytest.raises(neu.Fehler, match="gibt es schon"):
        anlegen(tmp_path)
    assert (r / "CLAUDE.md").read_text(encoding="utf-8") == "eigene Notizen"


@pytest.mark.parametrize("text, erwartet", [
    ("Hanna:mitwirkend", ("hanna", {"name": "Hanna", "rolle": "mitwirkend"})),
    ("b=Ben:gast:nicht", ("b", {"name": "Ben", "rolle": "gast", "reist": False})),
    ("Jörg:organisator:reist", ("joerg", {"name": "Jörg", "rolle": "organisator", "reist": True})),
])
def test_person_aus_text(text, erwartet):
    assert neu.person_aus_text(text) == erwartet


@pytest.mark.parametrize("text", ["Hanna", "Hanna:chef", "Hanna:mitwirkend:vielleicht"])
def test_person_aus_text_fehler(text):
    with pytest.raises(neu.Fehler):
        neu.person_aus_text(text)


def test_ids_werden_nie_neu_vergeben(tmp_path):
    r = anlegen(tmp_path)
    assert neu.naechste_id(r, "W") == "W-04"
    assert neu.naechste_id(r, "W") == "W-05"        # die Marke steigt, auch ohne dass W-04 irgendwo steht
    # Was irgendwo in der Reise steht, zählt mit, auch im Verlauf von Verworfenem
    (r / "plan/routen-notiz.md").write_text("verworfen: V-07.b, siehe O-12 und W-19\n", encoding="utf-8")
    assert neu.naechste_id(r, "W") == "W-20" and neu.naechste_id(r, "V") == "V-08" and neu.naechste_id(r, "O") == "O-13"
    # Abschnitt gelöscht: Seine Nummer kommt trotzdem nicht wieder
    (r / "plan/routen-notiz.md").unlink()
    assert neu.naechste_id(r, "W") == "W-21"
    assert neu.naechste_id(r, "F") == "F-02"
    with pytest.raises(neu.Fehler, match="vergibt dieses Skript nicht"):
        neu.naechste_id(r, "P")


def test_ids_in_reise_mit_id_liste(tmp_path):
    """Führt eine Reise in ids.yaml alle IDs als Liste je Art, kommt die neue ID dazu; nichts geht verloren."""
    r = tmp_path / "liste"
    r.mkdir()
    (r / "ids.yaml").write_text("# Feste IDs der Reise\n# W-09 wird nicht neu vergeben.\nids:\n"
                                "  T: [T-01, T-02]\n  W: [W-01, W-08, W-10]\n", encoding="utf-8")
    assert neu.naechste_id(r, "W") == "W-11" and neu.naechste_id(r, "F") == "F-01"
    text = (r / "ids.yaml").read_text(encoding="utf-8")
    assert text.startswith("# Feste IDs der Reise\n# W-09 wird nicht neu vergeben.\n")
    assert yaml.safe_load(text) == {"ids": {"T": ["T-01", "T-02"], "W": ["W-01", "W-08", "W-10", "W-11"], "F": ["F-01"]}}
    assert "  T: [T-01, T-02]\n" in text


def test_ids_in_bestehender_reise_ohne_marke(tmp_path):
    """Für Reisen von vor Paket H: ohne ids.yaml zählt die höchste Nummer im Text; Fotos zählen nicht."""
    r = tmp_path / "alt"
    (r / "medien").mkdir(parents=True)
    (r / "reise.json").write_text(json.dumps({"abschnitte": {"a.md": {"X": ["W-09", "wissen"]}}}), encoding="utf-8")
    (r / "medien/W-50.md").write_text("W-50", encoding="utf-8")
    (r / "notiz.md").write_text("AW-77 ist kein W, T-3 schon", encoding="utf-8")
    assert neu.naechste_id(r, "W") == "W-10" and neu.naechste_id(r, "T") == "T-04"


def test_abschnitt_mit_neuer_id(tmp_path):
    r = anlegen(tmp_path)
    assert neu.abschnitt(r, "Skigebiet", text="Eigene Worte.\n\n### Pisten\nViele.") == "W-04"
    assert neu.abschnitt(r, "Anreise mit dem Zug", gruppe="praxis", datei="inhalt/praxis.md") == "W-05"
    cfg = json.loads((r / "reise.json").read_text(encoding="utf-8"))
    assert cfg["abschnitte"]["inhalt/wissen.md"]["Skigebiet"] == ["W-04", "wissen"]
    assert cfg["abschnitte"]["inhalt/praxis.md"] == {"Anreise mit dem Zug": ["W-05", "praxis"]}
    assert '"Eckdaten": ["W-01", "plan"]' in (r / "reise.json").read_text(encoding="utf-8")   # Listen bleiben in einer Zeile
    d = bauen.bauen(r, tmp_path / "dist")
    ids = {a["id"]: a for a in d["abschnitte"]}
    assert ids["W-04"]["typ"] == "wissen" and [b["id"] for b in ids["W-04"]["bloecke"]] == ["W-04.pisten"]
    assert ids["W-05"]["typ"] == "praxis"
    with pytest.raises(neu.Fehler, match="schon einen Abschnitt"):
        neu.abschnitt(r, "Skigebiet")
    (r / "inhalt/wissen.md").write_text((r / "inhalt/wissen.md").read_text(encoding="utf-8") + "\n## Ohne ID\n", encoding="utf-8")
    with pytest.raises(neu.Fehler, match="ohne ID"):
        neu.abschnitt(r, "Ohne ID")
    with pytest.raises(neu.Fehler, match="Gruppe"):
        neu.abschnitt(r, "Neu", gruppe="geschichte")


def test_pruefen(tmp_path):
    r = anlegen(tmp_path)
    assert neu.pruefen(r) == (True, [])
    rj = r / "reise.json"
    gut = rj.read_text(encoding="utf-8")
    rj.write_text(gut.replace('"plan/plan.md",', '"plan/plan.md"', 1), encoding="utf-8")
    ok, m = neu.pruefen(r)
    assert not ok and "reise.json ist nicht lesbar (Zeile 3" in m[0] and "Komma" in m[0]
    rj.write_text(gut.replace("offene-fragen.md", "fragen.md"), encoding="utf-8")
    ok, m = neu.pruefen(r)
    assert m == ["reise.json nennt die Datei fragen.md, die es nicht gibt. Datei anlegen oder den Eintrag entfernen."]
    rj.write_text(gut, encoding="utf-8")
    ry = r / "reise.yaml"
    ry.write_text(ry.read_text(encoding="utf-8").replace("pfad: ", "pfad "), encoding="utf-8")
    ok, m = neu.pruefen(r)
    assert not ok and m[0].startswith("reise.yaml ist nicht lesbar (Zeile")
    ry.write_text(ry.read_text(encoding="utf-8").replace("pfad ", "pfad: "), encoding="utf-8")
    (r / "inhalt/wissen.md").write_text("## Fremd\nText\n", encoding="utf-8")     # Bau-Fehler kommen durch
    ok, m = neu.pruefen(r)
    assert not ok and any("Überblick" in x for x in m), m
    assert neu.pruefen(tmp_path / "gibt-es-nicht") == (False, [f"Den Ordner {tmp_path / 'gibt-es-nicht'} gibt es nicht."])


def test_aufruf(tmp_path, capsys):
    rc = neu.main(["neu.py", "reise", str(tmp_path), "--titel", "Ski", "--von", "2027-02-06", "--bis", "2027-02-13",
                   "--person", "Ida:organisator", "--person", "Karl:mitwirkend", "--wer", "Ida", "--ziel", "Oberstdorf"])
    assert rc == 0 and "Angelegt: " in capsys.readouterr().out
    r = tmp_path / "ski-2027"
    assert neu.main(["neu.py", "id", str(r), "O"]) == 0 and capsys.readouterr().out.strip() == "O-01"
    (tmp_path / "text.md").write_text("Eigene Worte.", encoding="utf-8")
    assert neu.main(["neu.py", "abschnitt", str(r), "--titel", "Tal", "--text-datei", str(tmp_path / "text.md")]) == 0
    assert capsys.readouterr().out.strip() == "W-04"
    assert neu.main(["neu.py", "pruefen", str(r)]) == 0 and "In Ordnung: Ski baut ohne Fehler." in capsys.readouterr().out
    (r / "reise.json").write_text("{", encoding="utf-8")
    assert neu.main(["neu.py", "pruefen", str(r)]) == 1 and "1 Punkt zu beheben" in capsys.readouterr().out
    assert neu.main(["neu.py", "reise", str(tmp_path), "--titel", "Ski", "--von", "2027-02-06", "--bis", "2027-02-13",
                     "--person", "Ida:organisator", "--wer", "Ida"]) == 2
    assert "Nicht möglich: Eine Reise „ski-2027“ gibt es schon" in capsys.readouterr().out


def test_aus_auftrag_der_claude_app(tmp_path):
    from reise import neue_reise_pruefen
    daten, _ = neue_reise_pruefen({"titel": "Ski im Tal", "von": "2027-02-06", "bis": "2027-02-13", "ziel": "Oberstdorf",
                                   "personen": [{"vorname": "Karl"}], "notiz": "Hütte am Ort, laut Karl schön."}, "Ida")
    a = {"id": "A-20261027-120000-ab12", "erstellt": "2026-10-27T12:00:00+00:00", "daten": {"neue_reise": daten}}
    r = neu.aus_auftrag(tmp_path, a, heute=datetime.date(2026, 10, 27))
    assert r.name == "ski-im-tal-2027"
    e = bauen.bauen(r, tmp_path / "dist")["reise"]
    assert e["status"]["verlauf"][0]["grund"] == "Reise angelegt (Auftrag A-20261027-120000-ab12 aus der Claude-App)"
    assert [(p["name"], p["rolle"]) for p in e["personen"]] == [("Ida", "organisator"), ("Karl", "mitwirkend")]
    assert "Notiz von Ida aus der Claude-App (27.10.2026):\n\nHütte am Ort, laut Karl schön." in \
        (r / "inhalt/wissen.md").read_text(encoding="utf-8")
    with pytest.raises(neu.Fehler, match="gibt es schon"):
        neu.aus_auftrag(tmp_path, a)
    with pytest.raises(neu.Fehler, match="kein Auftrag"):
        neu.aus_auftrag(tmp_path, {"id": "A-1", "daten": {}})
