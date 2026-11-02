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
import schreiben  # noqa: E402
from conftest import meldet  # noqa: E402

VON, BIS = datetime.date(2027, 2, 6), datetime.date(2027, 2, 13)
PERSONEN = {"ida": {"name": "Ida", "rolle": "organisator"}, "karl": {"name": "Karl", "rolle": "mitwirkend"},
            "mo": {"name": "Mo", "rolle": "gast", "reist": False}}


def anlegen(tmp_path, **kw):
    args = {"titel": "Skiurlaub im Tal", "von": VON, "bis": BIS, "personen": PERSONEN, "wer": "Ida",
            "ziel": "Oberstdorf", "heute": datetime.date(2026, 10, 27), **kw}
    return neu.anlegen(tmp_path / "reisen", **args)


def test_neue_reise_mit_sprache(tmp_path):
    r = anlegen(tmp_path, sprache="en")
    assert yaml.safe_load((r / "reise.yaml").read_text(encoding="utf-8"))["sprache"] == "en"
    assert bauen.bauen(r, tmp_path / "dist")["reise"]["sprache"] == "en"
    # ohne Angabe gilt der Rückfall (Test unten); eine unbekannte Sprache lehnt das Anlegen ab
    r2 = anlegen(tmp_path, pfad="zweite-reise")
    assert yaml.safe_load((r2 / "reise.yaml").read_text(encoding="utf-8"))["sprache"] == "de"
    with pytest.raises(neu.Fehler, match="sprache: unbekannt"):
        anlegen(tmp_path, pfad="dritte-reise", sprache="klingonisch")


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
    # Eckdaten nur in reise.yaml; die Seite zeigt sie im Abschnitt W-01, den der Generator daraus baut (#217)
    assert "Ida" not in (r / "plan/plan.md").read_text(encoding="utf-8")
    w01 = d["abschnitte"][0]["intro"]
    assert "Zeitraum: 6.–13. Februar 2027" in w01 and "Ziel: Oberstdorf" in w01 and meldet(w01, "inhalt.eckdaten.idee")
    assert "Ida (organisiert), Karl (bringt ein), Mo (liest mit, reist nicht mit)" in w01
    roh = yaml.safe_load((r / "reise.yaml").read_text(encoding="utf-8"))
    assert roh["ziel"] == "Oberstdorf" and "untertitel" not in roh
    assert yaml.safe_load((r / "ids.yaml").read_text(encoding="utf-8")) == {"W": 3, "F": 1}
    assert (r / "medien").is_dir()
    assert not (r / "CLAUDE.md").exists() and not (r / "kontext").exists()   # Reste von vor ADR-0001 (#217)


def test_eckdaten_folgen_reise_yaml(tmp_path):
    """#217: Zeitraum, Ziel, Status und Personen ändern sich im Gespräch; Untertitel und Eckdaten zeigen danach den neuen Stand,
    ein eigener Untertitel bleibt, was eine Person unter die Eckdaten schreibt, bleibt darunter stehen (erfundene Testdaten)."""
    r = anlegen(tmp_path)
    wer = {"name": "Ida", "rolle": "organisator", "person": "ida"}
    heute = datetime.date(2026, 11, 2)
    schreiben.reise_aendern(r, wer, {"von": "2027-03-01", "bis": "2027-03-05", "ziel": "Kleinwalsertal", "grund": "Schnee später"}, heute=heute)
    schreiben.reise_status_setzen(r, wer, {"status": "planung", "grund": "Es geht los"}, heute=heute)
    schreiben.person_schreiben(r, wer, {"schluessel": "ben", "vorname": "Ben", "rolle": "mitwirkend"}, heute=heute)
    plan = r / "plan/plan.md"
    plan.write_text(plan.read_text(encoding="utf-8") + "\nAnreise mit dem Zug ist gesetzt.\n", encoding="utf-8")
    d = bauen.bauen(r, tmp_path / "dist")
    assert d["reise"]["untertitel"] == "Kleinwalsertal, 1.–5. März 2027"
    w01 = d["abschnitte"][0]["intro"]
    assert "Zeitraum: 1.–5. März 2027" in w01 and "Ziel: Kleinwalsertal" in w01 and "Status: planung" in w01
    assert "Ben (bringt ein)" in w01 and "Idee" not in w01
    assert w01.index("Status: planung") < w01.index("Anreise mit dem Zug ist gesetzt.")
    schreiben.reise_aendern(r, wer, {"untertitel": "Skiwoche mit Freunden", "grund": "eigener Untertitel"}, heute=heute)
    assert bauen.bauen(r, tmp_path / "dist")["reise"]["untertitel"] == "Skiwoche mit Freunden"
    schreiben.reise_aendern(r, wer, {"untertitel": "", "ziel": "", "grund": "zurück"}, heute=heute)
    d = bauen.bauen(r, tmp_path / "dist")
    assert d["reise"]["untertitel"] == "1.–5. März 2027" and "Ziel: noch offen" in d["abschnitte"][0]["intro"]


def test_eckdaten_abschnitt_muss_es_geben(tmp_path):
    r = anlegen(tmp_path)
    cfg = json.loads((r / "reise.json").read_text(encoding="utf-8"))
    cfg["eckdaten"] = "W-09"
    (r / "reise.json").write_text(json.dumps(cfg), encoding="utf-8")
    with pytest.raises(bauen.BauFehler, match="W-09"):
        bauen.bauen(r, tmp_path / "dist")


@pytest.mark.parametrize("sprache", neu.texte.sprachen())
def test_kopf_von_reise_yaml_ist_lesbar(tmp_path, sprache):
    """#218: Jede Zeile des Kopfkommentars beginnt mit „#“, keine enthält „\\n“ als Text."""
    r = anlegen(tmp_path, sprache=sprache)
    kopf = (r / "reise.yaml").read_text(encoding="utf-8").split("\n\n", 1)[0].splitlines()
    assert len(kopf) >= 2
    for zeile in kopf:
        assert zeile.startswith("#") and "\\n" not in zeile, zeile


def test_eigener_pfad_herkunft_und_ueberblick(tmp_path):
    r = anlegen(tmp_path, pfad="ski-2027", herkunft="Auftrag A-1 aus der Claude-App", ueberblick="Ein Tal mit Schnee.",
                ziel=None)
    assert r.name == "ski-2027"
    assert "Ein Tal mit Schnee." in (r / "inhalt/wissen.md").read_text(encoding="utf-8")
    roh = yaml.safe_load((r / "reise.yaml").read_text(encoding="utf-8"))
    assert roh["status"]["verlauf"][0]["grund"] == "Reise angelegt (Auftrag A-1 aus der Claude-App)"
    assert "untertitel" not in roh and "ziel" not in roh
    assert bauen.bauen(r, tmp_path / "dist")["reise"]["untertitel"] == "6.–13. Februar 2027"
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
    assert rc == 0 and "Created: " in capsys.readouterr().out
    r = tmp_path / "ski-2027"
    for befehl in (["id", str(r), "O"], ["abschnitt", str(r), "--titel", "Tal"], ["reise", str(tmp_path), "--ueberblick", "x"]):
        with pytest.raises(SystemExit):     # Inhalte entstehen nur im AI-Client über den Konnektor (ADR-0001, #219)
            neu.main(["neu.py", *befehl])
    capsys.readouterr()
    assert neu.main(["neu.py", "pruefen", str(r)]) == 0 and "OK: Ski builds without errors." in capsys.readouterr().out
    (r / "reise.json").write_text("{", encoding="utf-8")
    assert neu.main(["neu.py", "pruefen", str(r)]) == 1 and "1 point to fix" in capsys.readouterr().out
    assert neu.main(["neu.py", "reise", str(tmp_path), "--titel", "Ski", "--von", "2027-02-06", "--bis", "2027-02-13",
                     "--person", "Ida:organisator", "--wer", "Ida"]) == 2
    assert "Not possible: Eine Reise „ski-2027“ gibt es schon" in capsys.readouterr().out


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


def test_reise_aus_der_vorlage_im_gespraech_fuellen(tmp_path):
    """Eine frische Reise aus der Vorlage (ohne plan/routen.yaml und ohne Arten) lässt sich allein über den Schreibweg füllen,
    wie im Gespräch in der Claude-App: Arten, Orte, Unterkunft, Strecke, Start, erster Tag, Wissen mit Herkunft. Nach jedem
    Schritt baut sie ohne Warnung (erfundene Testdaten)."""
    r = anlegen(tmp_path)
    wer = {"name": "Ida", "rolle": "organisator", "person": "ida"}
    schritte = [
        ("art_definieren", {"bezeichnung": "Hotel", "grundform": "aufenthalt", "buchbar": True}),
        ("art_definieren", {"bezeichnung": "Zugfahrt", "grundform": "bewegung"}),
        ("ding_anlegen", {"was": "ort", "titel": "Münster", "quelle": "Gespräch", "ausserhalb": True}),
        ("ding_anlegen", {"was": "ort", "titel": "Oberstdorf", "quelle": "Gespräch"}),
        ("ding_anlegen", {"was": "unterkunft", "titel": "Hotel am Ort", "ort": "O-02", "art": "hotel", "quelle": "Gespräch"}),
        ("ding_anlegen", {"was": "strecke", "titel": "Anreise", "von": "O-01", "nach": "O-02", "art": "zugfahrt",
                          "quelle": "Gespräch"}),
        ("start_ende_setzen", {"start_datum": "2027-02-06", "start_ort": "O-01", "ende_ort": "O-01", "grund": "Im Gespräch"}),
        ("tag_anlegen", {"titel": "Anreise", "nacht": "U-01", "strecken": ["E-01"]}),
        ("wissen_schreiben", {"titel": "Loipen", "text": "Am Ort beginnen zwei Loipen.", "quelle": "Erfundenes Buch, S. 3"}),
    ]
    for name, args in schritte:
        schreiben.WERKZEUGE[name](r, wer, args)
        assert schreiben.warnungen_des_baus(r) == [], name
    assert neu.pruefen(r) == (True, [])
    route = bauen.bauen(r, tmp_path / "dist")["route"]
    assert [(t["id"], t["datum"]) for t in route["tage"]] == [("T-01", "2027-02-06")]
    assert (len(route["orte"]), len(route["unterkuenfte"]), len(route["strecken"])) == (2, 1, 1)
    wissen = (r / "inhalt/wissen.md").read_text(encoding="utf-8")
    assert "## Loipen" in wissen and "*Herkunft: Erfundenes Buch, S. 3;" in wissen
    marken = yaml.safe_load((r / "ids.yaml").read_text(encoding="utf-8"))
    assert {k: marken[k] for k in "OUET"} == {"O": 2, "U": 1, "E": 1, "T": 1}


def test_nachziehen_nur_schluessel(tmp_path):
    """Abgleich 29.10.2026 (docs/abgleich-2026-10-29.md): neu.py nachziehen bringt eine Reise mit den alten Schlüsseln
    (typ an Unterkunft und Nacht, bereich und art: planung an Wahlstellen) auf den Stand, ohne eine ID oder einen Wert zu
    ändern; eine Strecke ohne Art wird gemeldet oder bekommt die angegebene; das Merkmal preis bekommt rolle kosten."""
    import shutil
    beispiel = Path(__file__).resolve().parents[2] / "beispiel/reisen/beispielreise"
    r = tmp_path / "bsp"
    shutil.copytree(beispiel, r)
    p = r / "plan/routen.yaml"
    alt = p.read_text(encoding="utf-8")
    alt = alt.replace("    art: hotel\n", "    typ: Hotel\n").replace("    art: pension\n", "    typ: Pension\n")
    alt = alt.replace("    wann: planung   # art: (die Art der Dinge) kommt hier aus den Optionen: die Art der ersten Unterkunft\n",
                      "    art: planung\n    bereich: pension\n")
    alt = alt.replace("    wann: unterwegs\n", "    art: unterwegs\n")
    alt = alt.replace("  E-23: {titel: \"Bus Bad Schandau → Dresden\", von: O-05, nach: O-01, art: bus, quelle",
                      "  E-23: {titel: \"Bus Bad Schandau → Dresden\", von: O-05, nach: O-01, quelle")
    p.write_text(alt, encoding="utf-8")
    a = r / "plan/arten.yaml"
    a.write_text(a.read_text(encoding="utf-8").replace(", rolle: kosten", ""), encoding="utf-8")
    cfg = json.loads((r / "reise.json").read_text(encoding="utf-8"))
    cfg.pop("etappen_ebenen")
    (r / "reise.json").write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with pytest.raises(bauen.BauFehler, match="E-23: art fehlt"):      # keine Vorgabe-Art mehr (ADR-0001)
        bauen.Bauer(r, tmp_path / "v0").daten()
    m = neu.nachziehen(r, schreiben=False)
    assert any(t.startswith("OPEN E-23") for t in m) and "U-01: typ “Hotel” → art hotel" in m and "V-03: art planung → wann planung" in m
    assert "V-03: bereich pension → art pension" in m and "V-02: art unterwegs → wann unterwegs" in m
    assert "arten.yaml hotel: attribute preis gets rolle kosten" in m and any(t.startswith("reise.json") for t in m)
    p.write_text(alt.replace("nach: O-01, quelle", "nach: O-01, art: bus, quelle"), encoding="utf-8")
    vorher = bauen.Bauer(r, tmp_path / "v").daten()   # baut über die Brücke der alten Schlüssel
    p.write_text(alt, encoding="utf-8")
    m = neu.nachziehen(r, {"E-23": "bus"})
    assert "E-23: art bus (given)" in m and not [t for t in m if t.startswith("OPEN")]
    text = p.read_text(encoding="utf-8")
    assert "typ:" not in text and "bereich:" not in text and "art: planung" not in text
    assert "# Alle Unterkünfte sind erfunden" in text                     # Kommentare bleiben
    nachher = bauen.Bauer(r, tmp_path / "n").daten()
    assert nachher["route"]["unterkuenfte"] == vorher["route"]["unterkuenfte"]
    assert [w["id"] for w in nachher["route"]["wahlstellen"]] == [w["id"] for w in vorher["route"]["wahlstellen"]]
    assert nachher["route"]["arten"]["hotel"]["kosten"] == "preis" and nachher["route"]["arten"]["herberge"]["kosten"] == "preis"   # pauschal; „pro Person“ nimmt die Organisator:in mit merkmal_definieren (rolle keine) heraus
    assert json.loads((r / "reise.json").read_text(encoding="utf-8"))["etappen_ebenen"]["unterwegs"][0] == "Höhenprofil"
    assert neu.nachziehen(r) == []                                        # zweiter Lauf: nichts mehr zu tun


def test_frage_schliessen_schreibt_in_der_sprache_der_reise(tmp_path):
    """Was der Schreibweg in offene-fragen.md schreibt, folgt der Sprache der Reise (ADR-0006, Punkt 5): auf Englisch „resolved“."""
    for sprache, wort, datum in (("en", "resolved", "30/10/2026"), ("de", "geklärt", "30.10.2026")):
        r = anlegen(tmp_path, pfad=f"reise-{sprache}", sprache=sprache)
        titel, text = schreiben.frage_schliessen(r, {"name": "Ida"}, {"frage": "F-01", "ergebnis": "Tal gewählt"}, heute=datetime.date(2026, 10, 30))
        zeile = [z for z in (r / "offene-fragen.md").read_text(encoding="utf-8").splitlines() if z.startswith("| F-01")][0]
        assert f"{wort} {datum}: Ida, Tal gewählt" in zeile, zeile
        assert titel.startswith("F-01")


# ---------- Rückfall der Software und Bestand (texte.VORGABE_REISE, texte.BESTAND_REISE) ----------

@pytest.mark.echter_rueckfall
def test_rueckfall_ist_englisch_und_neue_reisen_tragen_die_sprache_ausdruecklich(tmp_path):
    import texte
    assert texte.VORGABE_REISE == "en" and texte.BESTAND_REISE == "de"
    r = anlegen(tmp_path)   # ohne Angabe
    roh = yaml.safe_load((r / "reise.yaml").read_text(encoding="utf-8"))
    assert roh["sprache"] == "en"                                    # steht in der Datei, kein stilles Verlassen auf eine Vorgabe
    assert "February 2027" in neu.zeitraum_text(VON, BIS)            # ohne Sprache: Rückfall
    assert bauen.bauen(r, tmp_path / "dist")["reise"]["sprache"] == "en"


@pytest.mark.echter_rueckfall
def test_reise_ohne_feld_sprache_bleibt_deutsch(tmp_path):
    import reise
    r = anlegen(tmp_path, sprache="de")
    y = r / "reise.yaml"
    y.write_text("".join(z for z in y.read_text(encoding="utf-8").splitlines(True) if not z.startswith("sprache:")), encoding="utf-8")
    assert "sprache:" not in y.read_text(encoding="utf-8")
    assert reise.sprache_von(r) == "de"                              # Bestand von vor ADR-0006
    assert bauen.bauen(r, tmp_path / "dist")["reise"]["sprache"] == "de"
    y.write_text(y.read_text(encoding="utf-8") + "sprache: xx-unbekannt\n", encoding="utf-8")
    assert reise.sprache_von(r) == "en"                              # unbekannte Sprache: Rückfall, nicht Deutsch
    assert reise.sprache_von(tmp_path / "gibt-es-nicht") == "en"     # keine lesbare Datei: Rückfall


def test_nachziehen_eckdaten_einer_reise_von_vor_217(tmp_path):
    """Eine Reise aus der alten Vorlage (Eckdaten als Text in plan.md, Untertitel als Kopie, CLAUDE.md) kommt mit
    neu.py nachziehen auf den neuen Stand: Text weg, Ziel in reise.yaml, Untertitel entsteht beim Bau, eigene Zeilen
    bleiben, keine ID ändert sich (erfundene Testdaten)."""
    r = anlegen(tmp_path)
    cfg = json.loads((r / "reise.json").read_text(encoding="utf-8"))
    del cfg["eckdaten"]
    (r / "reise.json").write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    ry = (r / "reise.yaml").read_text(encoding="utf-8").replace("ziel: Oberstdorf\n", "untertitel: Oberstdorf, 6.–13. Februar 2027\n")
    (r / "reise.yaml").write_text(ry, encoding="utf-8")
    (r / "plan/plan.md").write_text(
        "# Skiurlaub im Tal – Plan\n\n## Eckdaten\n\n- Zeitraum: 6.–13. Februar 2027\n- Ziel: Oberstdorf\n"
        "- Wer: Ida (organisiert), Karl (bringt ein), Mo (liest mit, reist nicht mit)\n"
        "- Die Reise ist eine Idee. Einen Plan mit Tagen, Wegen und Unterkünften gibt es ab der Planung.\n"
        "- Skipass für alle über die Unterkunft.\n", encoding="utf-8")
    (r / "CLAUDE.md").write_text("# Skiurlaub im Tal\n", encoding="utf-8")
    assert bauen.bauen(r, tmp_path / "dist")["reise"]["untertitel"] == "Oberstdorf, 6.–13. Februar 2027"

    m = neu.nachziehen(r, schreiben=False)
    assert any("W-01" in x for x in m) and any("Oberstdorf" in x for x in m)
    assert not any(x.startswith(("OFFEN", "OPEN")) for x in m)    # eigene CLAUDE.md: kein Rest, nichts offen (#250)
    assert "Zeitraum" in (r / "plan/plan.md").read_text(encoding="utf-8")         # Probelauf schreibt nichts

    neu.nachziehen(r)
    assert (r / "plan/plan.md").read_text(encoding="utf-8") == \
        "# Skiurlaub im Tal – Plan\n\n## Eckdaten\n\n- Skipass für alle über die Unterkunft.\n"
    roh = yaml.safe_load((r / "reise.yaml").read_text(encoding="utf-8"))
    assert roh["ziel"] == "Oberstdorf" and "untertitel" not in roh
    assert list(json.loads((r / "reise.json").read_text(encoding="utf-8")))[:2] == ["plan", "eckdaten"]
    d = bauen.bauen(r, tmp_path / "dist")
    assert d["reise"]["untertitel"] == "Oberstdorf, 6.–13. Februar 2027"
    w01 = d["abschnitte"][0]["intro"]
    assert w01.count("Zeitraum:") == 1 and "Skipass für alle" in w01
    assert (r / "CLAUDE.md").read_text(encoding="utf-8") == "# Skiurlaub im Tal\n"  # eigene Datei bleibt (#250)
    assert neu.nachziehen(r) == []                                                # ein zweiter Lauf ändert nichts
