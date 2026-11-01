"""Tests für engine/bauen.py: kleine synthetische Reise plus Volllauf mit der Beispielreise (beispiel/reisen/beispielreise)."""
import copy
import datetime
import json
import shutil
import re
import sys
from pathlib import Path

import pytest
import yaml
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import bauen  # noqa: E402

WURZEL = Path(__file__).resolve().parent.parent.parent

DOSSIER = """# Titel
Vorspann

## Übersicht
Text mit Liste:
- eins
- zwei

| A | B |
|---|---|
| 1 | 2 |

## Etappe 1: Anfang – Mitte
*Untertitel*

### Eckdaten
| Merkmal | Wert |
|---|---|
| Gehzeit | 5:00 h |

### Höhenprofil
![Profil](../medien/gross.jpg)

### Karten
- [Karte1](../medien/klein.png) (Quelle X)

## Etappe 2V: Variante
### Zusammenfassung
Kurz.

## Quellen zu Dingen (Recherche)
- [Link](https://example.org)
"""

UNTERKUENFTE = """# U
## Etappe 1: Anfang – Mitte
| Name | Typ |
|---|---|
| Hotel A | Hotel |

## Hütten – Übersicht aus dem Buch
### Überblick
Text.
"""

PLAN = """# Plan
Stand heute.

## Eckdaten
Acht Tage.

## Tagesplan
Vorher.

| Tag | Datum | Etappe | Übernachtung |
|---|---|---|---|
| 1 | Do 1.1. | Ankunft | Hotel |
| 2 | Fr 2.1. | Wandern \\| mit Strich | Hütte |

Nachher.

## Unterkünfte
| Nacht | Ort | Unterkunft |
|---|---|---|
| Do | A | Hotel A |
| Fr | B | Hütte B |
"""

FRAGEN = """# Fragen
| ID | Was | Status |
|---|---|---|
| F-01 | Buchen | offen |
"""

CFG = {
    "titel": "Test", "untertitel": "x", "pfad": "test", "plan": "plan/plan.md",
    "fragen": "fragen.md", "etappen_dossier": "inhalt/e.md", "unterkuenfte_dossier": "inhalt/u.md",
    "bilder_max_breite": 1600,
    "abschnitte": {
        "inhalt/e.md": {"Übersicht": ["W-01", "uebersicht"], "Quellen zu Dingen": ["W-02", "quelle"]},
        "inhalt/u.md": {"Hütten – Übersicht": ["W-03", "praxis"]},
        "plan/plan.md": {"Eckdaten": ["W-04", "plan"]},
    },
    "tabellen": {"Tagesplan": ["W-05", "plan", "tage"], "Unterkünfte": ["W-06", "plan", "unterkuenfte"]},
    "etappen_kennzahlen": ["Gehzeit"],
    "gruppen": {"wissen": "Wissen"},
}


@pytest.fixture
def reise(tmp_path):
    r = tmp_path / "reise"
    for rel, text in {"inhalt/e.md": DOSSIER, "inhalt/u.md": UNTERKUENFTE, "plan/plan.md": PLAN,
                      "fragen.md": FRAGEN}.items():
        (r / rel).parent.mkdir(parents=True, exist_ok=True)
        (r / rel).write_text(text, encoding="utf-8")
    (r / "medien").mkdir()
    Image.new("RGB", (2400, 1200), "red").save(r / "medien/gross.jpg")
    Image.new("RGB", (400, 200), "blue").save(r / "medien/klein.png")
    (r / "reise.json").write_text(json.dumps(CFG, ensure_ascii=False), encoding="utf-8")
    return r


def setze(reise, aendere):
    cfg = json.loads((reise / "reise.json").read_text(encoding="utf-8"))
    aendere(cfg)
    (reise / "reise.json").write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")


def baue(reise, tmp_path):
    return bauen.bauen(reise, tmp_path / "dist")


def meldungen(reise, tmp_path):
    with pytest.raises(bauen.BauFehler) as e:
        baue(reise, tmp_path)
    return "\n".join(e.value.meldungen)


def alle_ids(d):
    ids = []
    for a in d["abschnitte"]:
        ids.append(a["id"])
        ids += [b["id"] for b in a["bloecke"]]
        if "tabelle" in a:
            ids += [z["id"] for z in a["tabelle"]["zeilen"]]
    ids += [z["id"] for z in d["fragen"]["zeilen"]]
    r = d.get("route")
    if r:
        # Orte mit Beschreibung (typ „ort“) stehen schon oben als Abschnitt, gleiche ID für denselben Ort
        beschrieben = {a["id"] for a in d["abschnitte"] if a["typ"] == "ort"}
        ids += [o for o in r["orte"] if o not in beschrieben] + list(r["unterkuenfte"]) + [t for t in r["strecken"] if not r["strecken"][t]["dossier"]]
        ids += [t["id"] for t in r["tage"]] + list(r["weitere_tage"])
        ids += [w["id"] for w in r["wahlstellen"]] + [o["id"] for w in r["wahlstellen"] for o in w["optionen"]]
        ids += [p["id"] for p in r["plaene"]]
    return ids


# ---------- Synthetische Reise ----------
def test_ids(reise, tmp_path):
    d = baue(reise, tmp_path)
    ids = alle_ids(d)
    assert len(ids) == len(set(ids))
    for i in ["W-01", "W-02", "W-03", "W-04", "W-05", "W-06", "E-01", "E-02V", "E-01.eckdaten",
              "E-01.hoehenprofil", "E-01.unterkuenfte-liste", "W-03.ueberblick", "T-01", "T-02",
              "U-01", "U-02", "F-01"]:
        assert i in ids, i
    for i in ids:
        assert bauen.ZIEL_ID.match(i), i


def test_etappe_kennzahlen(reise, tmp_path):
    d = baue(reise, tmp_path)
    e = {a["id"]: a for a in d["abschnitte"] if a["typ"] == "etappe"}
    assert e["E-01"]["kennzahlen"] == {"Gehzeit": "5:00 h"}
    assert d["route"] is None


def test_tabellen_zeilen_und_pipe_im_text(reise, tmp_path):
    d = baue(reise, tmp_path)
    tage = next(a for a in d["abschnitte"] if a["id"] == "W-05")
    assert [z["id"] for z in tage["tabelle"]["zeilen"]] == ["T-01", "T-02"]
    assert tage["tabelle"]["zeilen"][1]["zellen"][2] == "Wandern | mit Strich"
    assert "Vorher" in tage["intro"] and "Nachher" in tage["nach"]


def test_tabellen_und_listen_werden_html(reise, tmp_path):
    d = baue(reise, tmp_path)
    uebersicht = next(a for a in d["abschnitte"] if a["id"] == "W-01")
    html = uebersicht["intro"]
    assert html.count('<dl class="textmerkmale">') == 1 and html.count("<li>") == 2


def test_tabellen_aus_text_lesbar():
    """B2 (#54): zweispaltig wird Merkmalliste ohne Kopf, „/“ darf umbrechen (nicht im Link); breit bleibt Tabelle mit
    Spaltenkopf je Zelle, leere Zellen heißen „leer“; Sonderzeichen im Kopf werden nicht doppelt maskiert."""
    md = bauen.markdown.Markdown(extensions=["tables"])
    zwei = bauen.tabellen_ordnen(md.convert("| Merkmal | Wert |\n|---|---|\n| Ein-/Ausstieg | [hier](https://x.de/a/b) |\n| Gehzeit | 3:40 h |"))
    assert zwei == ('<div class="tabelle merkmale"><dl class="textmerkmale"><div><dt>Ein-/<wbr>Ausstieg</dt>'
                    '<dd><a href="https://x.de/a/b">hier</a></dd></div><div><dt>Gehzeit</dt><dd>3:40 h</dd></div></dl></div>')
    breit = bauen.tabellen_ordnen(md.reset().convert("| Name | Typ & Art | Preis |\n|:--|---|--:|\n| A | – | 85 € |\n| B | Hütte | |"))
    assert breit.startswith('<div class="tabelle stapel"><table><thead><tr><th style="text-align: left;">Name</th>')
    assert '<td data-spalte="Typ &amp; Art" class="leer">–</td>' in breit
    assert '<td style="text-align: right;" data-spalte="Preis" class="leer"></td>' in breit
    assert '<td data-spalte="Typ &amp; Art">Hütte</td>' in breit and "<th" not in breit.split("<tbody>")[1]


def test_bilder_verkleinert_und_umgeschrieben(reise, tmp_path):
    d = baue(reise, tmp_path)
    gross = Image.open(tmp_path / "dist/medien/gross.jpg")
    assert gross.width == 1600 and gross.height == 800
    klein = Image.open(tmp_path / "dist/medien/klein.png")
    assert klein.width == 400  # nicht hochskaliert
    assert Image.open(reise / "medien/gross.jpg").width == 2400  # Original unverändert
    e1 = next(a for a in d["abschnitte"] if a["id"] == "E-01")
    profil = next(b for b in e1["bloecke"] if b["id"] == "E-01.hoehenprofil")["html"]
    karten = next(b for b in e1["bloecke"] if b["id"] == "E-01.karten")["html"]
    assert 'src="medien/gross.jpg"' in profil
    assert 'href="medien/klein.png"' in karten and "../" not in karten


def test_seite_eingebettet_und_script_ende_escaped(reise, tmp_path):
    (reise / "inhalt/e.md").write_text(DOSSIER.replace("Kurz.", "Kurz </script> Ende."), encoding="utf-8")
    baue(reise, tmp_path)
    seite = (tmp_path / "dist/index.html").read_text(encoding="utf-8")
    assert "/*__DATEN__*/null" not in seite
    vorlage = (Path(bauen.__file__).parent / "vorlage.html").read_text(encoding="utf-8")
    assert seite.count("</script>") == vorlage.count("</script>")   # Inhalt beendet kein Skript
    assert (tmp_path / "dist/daten.json").exists()


def _git(ordner, *args):
    import subprocess
    return subprocess.run(["git", "-C", str(ordner), *args], check=True, capture_output=True, text=True).stdout.strip()


def test_release_aus_git(tmp_path):
    """Release = Zahl der Commits und kurzer Hash; im flachen Klon nur der Hash, ohne Git nichts (Product Owner 1.11.2026)."""
    voll = tmp_path / "voll"
    voll.mkdir()
    _git(voll, "init", "-q")
    for i in range(3):
        (voll / "f").write_text(str(i))
        _git(voll, "add", "f")
        _git(voll, "-c", "user.name=Ida", "-c", "user.email=ida@example.org", "commit", "-qm", f"Stand {i}")
    kennung = _git(voll, "rev-parse", "--short=7", "HEAD")
    assert bauen.software_release(voll) == (3, kennung)
    flach = tmp_path / "flach"
    _git(tmp_path, "clone", "-q", "--depth=1", f"file://{voll}", str(flach))
    assert bauen.software_release(flach) == (None, kennung)
    assert bauen.software_release(tmp_path / "ohne") == (None, None)


def test_release_im_fuss_jeder_seite(reise, tmp_path, monkeypatch):
    monkeypatch.setattr(bauen, "software_release", lambda: (412, "9b4a397"))
    baue(reise, tmp_path)
    seite = (tmp_path / "dist/index.html").read_text(encoding="utf-8")
    assert '<footer class="fuss" id="release">Frieda Release 412 · 9b4a397</footer>' in seite
    monkeypatch.setattr(bauen, "software_release", lambda: (None, None))
    baue(reise, tmp_path)
    assert '<footer class="fuss" id="release"></footer>' in (tmp_path / "dist/index.html").read_text(encoding="utf-8")


def test_symbole_eingebettet_mit_lizenz(reise, tmp_path):
    baue(reise, tmp_path)
    seite = (tmp_path / "dist/index.html").read_text(encoding="utf-8")
    assert "<!--__SYMBOLE__-->" not in seite
    assert "Lucide 1.55.0, ISC-Lizenz" in seite
    definiert = set(re.findall(r'<symbol id="i-([a-z]+)"', seite))
    assert definiert == set(bauen.SYMBOLE)
    assert set(re.findall(r'href="#i-([a-z]+)"', seite)) <= definiert   # feste Knöpfe
    assert {"plan", "wissen"} <= definiert                               # Kategorien (per JS)
    assert (Path(bauen.__file__).parent / "vendor" / bauen.LUCIDE / "LICENSE").exists()


# ---------- Prüfungen ----------
def test_fehler_ueberschrift_fehlt_im_text(reise, tmp_path):
    setze(reise, lambda c: c["abschnitte"]["inhalt/e.md"].update({"Gibt es nicht": ["W-09", "wissen"]}))
    assert "Gibt es nicht" in meldungen(reise, tmp_path)


def test_fehler_ueberschrift_ohne_id(reise, tmp_path):
    setze(reise, lambda c: c["abschnitte"]["inhalt/e.md"].pop("Übersicht"))
    assert "hat keine ID" in meldungen(reise, tmp_path)


def test_fehler_doppelte_id(reise, tmp_path):
    setze(reise, lambda c: c["abschnitte"]["inhalt/e.md"].update({"Quellen zu Dingen": ["W-01", "quelle"]}))
    assert "Doppelte ID W-01" in meldungen(reise, tmp_path)


def test_fehler_doppelter_unterabschnitt(reise, tmp_path):
    (reise / "inhalt/e.md").write_text(DOSSIER + "\n## Etappe 3: X\n### Eckdaten\na\n### Eckdaten\nb\n", encoding="utf-8")
    assert "Doppelte ID E-03.eckdaten" in meldungen(reise, tmp_path)


def test_fehler_unbekannte_etappe_in_unterkuenften(reise, tmp_path):
    (reise / "inhalt/u.md").write_text(UNTERKUENFTE + "\n## Etappe 9: Nirgends\n| a |\n|---|\n| b |\n", encoding="utf-8")
    assert "Etappe 9: Nirgends" in meldungen(reise, tmp_path)


def test_fehler_bildlink_ohne_datei(reise, tmp_path):
    (reise / "inhalt/e.md").write_text(DOSSIER.replace("gross.jpg", "fehlt.jpg"), encoding="utf-8")
    assert "fehlt.jpg" in meldungen(reise, tmp_path)


def test_fehler_html_im_text(reise, tmp_path):
    # Reisetexte sind Fließtext: eigenes HTML mit Stil, Klasse oder Skript umgeht das Designsystem (docs/design.md)
    (reise / "inhalt/e.md").write_text(DOSSIER.replace("Kurz.", 'Kurz <span class="rot" onclick="x()">rot</span>.\n\n'
                                                       '<div style="color:red">Kasten</div>'), encoding="utf-8")
    m = meldungen(reise, tmp_path)
    assert "e.md: HTML im Text" in m
    assert all(x in m for x in ["<span>", "<span class>", "<span onclick>", "<div>", "<div style>"]), m


def test_markdown_tabelle_mit_ausrichtung_ist_erlaubt(reise, tmp_path):
    (reise / "inhalt/e.md").write_text(DOSSIER.replace("Kurz.", "Kurz.\n\n| a | b |\n|:--|--:|\n| 1 | 2 |\n"), encoding="utf-8")
    baue(reise, tmp_path)


def test_pfad_in_backticks_ist_kein_bildlink(reise, tmp_path):
    (reise / "inhalt/e.md").write_text(DOSSIER.replace("Vorspann", "Siehe `../medien/karten/` hier."), encoding="utf-8")
    baue(reise, tmp_path)


def test_praefix_mehrdeutig(reise, tmp_path):
    setze(reise, lambda c: c["abschnitte"]["inhalt/e.md"].update({"Quellen zu": ["W-09", "quelle"]}))
    assert "mehrere Einträge" in meldungen(reise, tmp_path)


def test_mehrere_fehler_auf_einmal(reise, tmp_path):
    def aendere(c):
        c["abschnitte"]["inhalt/e.md"].update({"Gibt es nicht": ["W-09", "wissen"], "Auch nicht": ["W-10", "wissen"]})
    setze(reise, aendere)
    assert meldungen(reise, tmp_path).count("diese Überschrift fehlt") == 2


def test_reise_ohne_etappen(reise, tmp_path):
    (reise / "inhalt/e.md").write_text("## Übersicht\nNur Text.\n\n## Quellen zu Dingen\n- x\n", encoding="utf-8")
    (reise / "inhalt/u.md").write_text("## Hütten – Übersicht\nText\n", encoding="utf-8")
    d = baue(reise, tmp_path)
    assert not [a for a in d["abschnitte"] if a["typ"] == "etappe"]


def test_ignorierte_ueberschrift_und_zusatzdatei(reise, tmp_path):
    (reise / "extra.md").write_text("## Titel der Datei\negal\n\n## 1. Kapitel\n### Teil\nText\n", encoding="utf-8")

    def aendere(c):
        c["abschnitte"]["extra.md"] = {"1. Kapitel": ["W-20", "wissen"]}
        c["ignorieren"] = {"extra.md": ["Titel der Datei"]}
    setze(reise, aendere)
    d = baue(reise, tmp_path)
    assert "W-20.teil" in alle_ids(d)


def test_zusatzdatei_ueberschrift_ohne_id(reise, tmp_path):
    (reise / "extra.md").write_text("## Unbekannt\nText\n", encoding="utf-8")
    setze(reise, lambda c: c["abschnitte"].update({"extra.md": {}}))
    assert "Unbekannt" in meldungen(reise, tmp_path)


def test_reise_ohne_dossiers_und_plan_tabellen(reise, tmp_path):
    (reise / "extra.md").write_text("## Alles\nText\n", encoding="utf-8")

    def aendere(c):
        for k in ("etappen_dossier", "unterkuenfte_dossier", "plan", "tabellen", "etappen_kennzahlen"):
            c.pop(k, None)
        c["abschnitte"] = {"extra.md": {"Alles": ["W-01", "wissen"]}}
    setze(reise, aendere)
    d = baue(reise, tmp_path)
    assert alle_ids(d) == ["W-01", "F-01"]


REISE_YAML = {
    "titel": "Test", "untertitel": "x", "pfad": "test",
    "status": {"wert": "planung", "verlauf": [{"datum": datetime.date(2026, 10, 26), "wert": "planung", "wer": "Hanna"}]},
    "personen": {"hanna": {"name": "Hanna", "rolle": "organisator"},
                 "ben": {"name": "Ben", "rolle": "mitwirkend", "reist": False, "notiz": "kennt die Gegend"},
                 "kim": {"name": "Kim", "rolle": "gast"}},
    "bausteine": ["varianten", "fragen", "wuensche"],
    "regeln": {"kontingent": {"je_person": 4}},
    "darstellung": {"gruppen": {"wissen": "Wissen"}, "varianten_titel": "Pläne"},
}


def mit_reise_yaml(reise, aendere=None):
    """Eckdaten und Darstellung aus reise.json nach reise.yaml (neue Form, docs/produkt.md)."""
    r = copy.deepcopy(REISE_YAML)
    if aendere:
        aendere(r)
    (reise / "reise.yaml").write_text(yaml.safe_dump(r, allow_unicode=True, sort_keys=False), encoding="utf-8")
    setze(reise, lambda c: [c.pop(k, None) for k in ("titel", "untertitel", "pfad", "gruppen")])


def test_alte_form_ohne_reise_yaml(reise, tmp_path):
    """Ohne reise.yaml kommen Eckdaten aus reise.json; Status planung, keine Personen, Hinweis."""
    d = baue(reise, tmp_path)
    r = d["reise"]
    assert r["titel"] == "Test" and r["status"] == {"wert": "planung", "verlauf": []} and r["personen"] == []
    assert "wuensche" not in r["bausteine"] and "varianten" in r["bausteine"]
    assert r["regeln"]["kontingent"] == {"art": "punkte", "je_person": 10} and "sammelzeit_minuten" not in r["regeln"]
    setze(reise, lambda c: c.update(funktionen=["wuensche"]))
    mit_reise_yaml(reise)
    assert "„funktionen“ steht noch in reise.json" in meldungen(reise, tmp_path)


def test_reise_yaml(reise, tmp_path):
    mit_reise_yaml(reise)
    r = baue(reise, tmp_path)["reise"]
    assert r["titel"] == "Test" and r["varianten_titel"] == "Pläne" and r["gruppen"] == {"wissen": "Wissen"}
    assert r["status"]["wert"] == "planung" and r["status"]["verlauf"][0]["datum"] == "2026-10-26"
    assert r["zeitraum"] is None
    mit_reise_yaml(reise, lambda x: x.update(zeitraum={"von": datetime.date(2027, 2, 6), "bis": datetime.date(2027, 2, 13)}))
    assert baue(reise, tmp_path)["reise"]["zeitraum"] == {"von": "2027-02-06", "bis": "2027-02-13"}
    assert [(p["schluessel"], p["rolle"], p["reist"]) for p in r["personen"]] == \
        [("hanna", "organisator", True), ("ben", "mitwirkend", False), ("kim", "gast", True)]
    # Wer nur einen Teil mitreist, hat von/bis (Reiseüberblick: „Kim ab 8.2.“)
    mit_reise_yaml(reise, lambda x: x["personen"]["kim"].update(von=datetime.date(2027, 2, 8)))
    assert baue(reise, tmp_path)["reise"]["personen"][2]["von"] == "2027-02-08"
    assert r["bausteine"] == ["varianten", "fragen", "wuensche"]
    assert r["regeln"]["kontingent"] == {"art": "punkte", "je_person": 4} and r["regeln"]["einladen"] == "organisator"
    # Manifest nimmt den Titel aus reise.yaml
    assert json.loads((tmp_path / "dist" / "manifest.json").read_text(encoding="utf-8"))["name"] == "Test"


@pytest.mark.parametrize("aendere, text", [
    (lambda r: r["status"].update(wert="fertig"), "status.wert muss eines von"),
    (lambda r: r["status"]["verlauf"][0].update(wer="Ben"), "darf nur ein:e Organisator:in setzen"),
    (lambda r: r["status"]["verlauf"][0].update(wert="fest"), "passt nicht zum letzten Verlaufseintrag"),
    (lambda r: r["status"].update(verlauf=[]), "braucht einen Verlauf"),
    (lambda r: r["personen"]["hanna"].update(rolle="mitwirkend"), "Mindestens eine Person braucht die Rolle organisator"),
    (lambda r: r["personen"]["ben"].update(rolle="chef"), "rolle muss eines von"),
    (lambda r: r["personen"]["kim"].update(bis="Ende Mai"), "bis muss ein Datum sein"),
    (lambda r: r["personen"]["ben"].update(name="Hanna"), "kommt zweimal vor"),
    (lambda r: r["personen"]["ben"].update(alter=40), "unbekannte Felder alter"),
    (lambda r: r.update(bausteine=["zauberei"]), "unbekannter Baustein „zauberei“"),
    (lambda r: r.pop("bausteine"), "bausteine fehlt"),
    (lambda r: r.update(regeln={"zauber": 1}), "unbekannte Regel „zauber“"),
    (lambda r: r.update(regeln={"konflikt": "münze"}), "regeln.konflikt muss eines von"),
    (lambda r: r.update(regeln={"kontingent": {"art": "sterne"}}), "kontingent.art muss"),
    (lambda r: r.update(darstellung={"farbe": "rot"}), "darstellung: unbekannter Schlüssel „farbe“"),
    (lambda r: r.update(bonus=1), "unbekannter Schlüssel „bonus“"),
    (lambda r: r.pop("titel"), "„titel“ fehlt"),
    (lambda r: r.pop("pfad"), "„pfad“ fehlt"),
    # Zeitraum (Paket H)
    (lambda r: r.update(zeitraum={"von": datetime.date(2027, 2, 6)}), "zeitraum muss {von: JJJJ-MM-TT, bis: JJJJ-MM-TT} sein"),
    (lambda r: r.update(zeitraum={"von": "8.1.", "bis": "17.1."}), "zeitraum muss"),
    (lambda r: r.update(zeitraum={"von": datetime.date(2027, 2, 6), "bis": datetime.date(2027, 2, 1)}), "liegt vor von"),
    # Verlauf des Status
    (lambda r: r["status"].update(verlauf=["gestern"]), "Eintrag muss {datum, wert, wer, grund} sein"),
    (lambda r: r["status"]["verlauf"][0].update(wert="zauber"), "Status „zauber“ unbekannt"),
    (lambda r: r["status"]["verlauf"][0].update(datum="gestern"), "Eintrag ohne gültiges Datum"),
    (lambda r: r["status"].update(verlauf=[
        {"datum": datetime.date(2026, 10, 26), "wert": "idee", "wer": "Hanna"},
        {"datum": datetime.date(2026, 10, 20), "wert": "planung", "wer": "Hanna"}]), "nicht zeitlich sortiert"),
    # Personen
    (lambda r: r.update(personen=["Hanna"]), "personen muss"),
    (lambda r: r["personen"]["ben"].pop("name"), "Person „ben“ braucht einen Namen"),
    # Bausteine
    (lambda r: r.update(bausteine="fragen"), "bausteine muss eine Liste sein"),
    (lambda r: r.update(bausteine=["fragen", "fragen"]), "Baustein „fragen“ steht zweimal"),
    # Spielregeln
    (lambda r: r.update(regeln=["konflikt"]), "regeln muss „regel: wert“ sein"),
    (lambda r: r.update(regeln={"einladen": "alle"}), "regeln.einladen muss eines von"),
    (lambda r: r.update(regeln={"kontingent": {"je_person": -1}}), "kontingent.je_person muss eine ganze Zahl ab 0"),
    (lambda r: r.update(regeln={"waechter_frist_tage": 0}), "regeln.waechter_frist_tage muss eine ganze Zahl ab 1"),
    (lambda r: r.update(regeln={"meldekanal": "app"}), "regeln.meldekanal muss eine Liste"),
    (lambda r: r.update(regeln={"meldekanal": ["email"]}), "email gibt es nicht"),
    (lambda r: r.update(darstellung="bunt"), "darstellung muss „schluessel: wert“ sein"),
])
def test_reise_yaml_fehler(reise, tmp_path, aendere, text):
    mit_reise_yaml(reise, aendere)
    assert text in meldungen(reise, tmp_path)


@pytest.mark.parametrize("schluessel", ["titel", "untertitel", "pfad", "gruppen", "funktionen"])
def test_reise_yaml_alte_eckdaten_in_reise_json(reise, tmp_path, schluessel):
    """Mit reise.yaml dürfen Eckdaten, Darstellung und funktionen nicht mehr zusätzlich in reise.json stehen."""
    mit_reise_yaml(reise)
    setze(reise, lambda c: c.update({schluessel: "alt"}))
    assert f"„{schluessel}“ steht noch in reise.json" in meldungen(reise, tmp_path)


def test_reise_yaml_hinweise(reise, tmp_path, capsys):
    mit_reise_yaml(reise, lambda r: r.update(bausteine=["plan", "profile"]))
    b = bauen.Bauer(reise, tmp_path / "dist")
    b.daten()
    assert any("„plan“ ist Kern" in h for h in b.hinweise) and any("noch nicht gebaut" in h for h in b.hinweise)


def test_alte_regeln_des_einarbeitens_bauen_weiter(reise, tmp_path):
    """ADR-0001, O-3: regeln.entscheidungsweg und sammelzeit_minuten gibt es nicht mehr. Eine reise.yaml, die sie noch
    nennt, baut mit Hinweis; die Werte kommen nicht in die Seite."""
    mit_reise_yaml(reise, lambda r: r.update(regeln={"entscheidungsweg": "auftrag", "sammelzeit_minuten": 5}))
    b = bauen.Bauer(reise, tmp_path / "dist")
    d = b.daten()
    assert sum("gibt es seit dem 29.10.2026 nicht mehr" in h for h in b.hinweise) == 2
    assert "entscheidungsweg" not in d["reise"]["regeln"] and "sammelzeit_minuten" not in d["reise"]["regeln"]


def test_slug_ascii():
    assert bauen.slug("Unterkünfte & Kontakte") == "unterkuenfte-kontakte"
    assert bauen.slug("Straße à la Carte") == "strasse-a-la-carte"
    assert len(bauen.slug("x" * 200)) <= 60


def test_zusatzdatei_vorspann(reise, tmp_path):
    """Text unter der Hauptüberschrift geht nicht stillschweigend verloren (Recherche-Dateien, #8)."""
    (reise / "extra.md").write_text("# Große Überschrift\n\nDie Zusammenfassung.\n\n---\n\n## 1. Kapitel\nText\n", encoding="utf-8")
    setze(reise, lambda c: c["abschnitte"].update({"extra.md": {"1. Kapitel": ["W-20", "wissen"]}}))
    assert "Text vor der ersten ##-Überschrift" in meldungen(reise, tmp_path)
    setze(reise, lambda c: c["abschnitte"]["extra.md"].update({"#": ["W-21", "wissen"]}))
    d = baue(reise, tmp_path)
    a = next(x for x in d["abschnitte"] if x["id"] == "W-21")
    assert a["titel"] == "Große Überschrift" and "Die Zusammenfassung." in a["intro"] and "<hr" not in a["intro"]
    setze(reise, lambda c: (c["abschnitte"]["extra.md"].pop("#"), c.setdefault("ignorieren", {}).update({"extra.md": ["#"]})))
    assert "W-21" not in alle_ids(baue(reise, tmp_path))


def test_fussnoten_je_block(reise, tmp_path):
    """Definitionen am Dateiende, Verweise in anderen Abschnitten: jeder Block bekommt seine Nachweise (25.10.2026)."""
    (reise / "extra.md").write_text(
        "## 1. Kapitel\n### 1.1 Teil\nAussage.[^2] Noch eine[^1]: und Tabelle\n\n| A |\n|---|\n| x[^2][^1] |\n\n"
        "## 9. Quellen\n1. Liste\n\n[^1]: Buch A | https://example.org/a/b | 2026\n[^2]: Notiz | /mnt/intern.md | 23.10.2026\n",
        encoding="utf-8")
    setze(reise, lambda c: c["abschnitte"].update({"extra.md": {"1. Kapitel": ["W-20", "wissen"], "9. Quellen": ["W-21", "wissen"]}}))
    d = baue(reise, tmp_path)
    b = next(x for x in d["abschnitte"] if x["id"] == "W-20")["bloecke"][0]["html"]
    assert "[^" not in b and b.count('<sup class="fn">') == 4
    liste = b.split('<ol class="fussnoten">')[1]
    assert liste.index('value="2"') < liste.index('value="1"')  # Reihenfolge der ersten Nennung, jede nur einmal
    assert liste.count("<li") == 2 and 'href="https://example.org/a/b">example.org</a>' in liste and "projektintern" in liste
    assert "[^" not in next(x for x in d["abschnitte"] if x["id"] == "W-21")["intro"]
    (reise / "extra.md").write_text("## 1. Kapitel\nText[^7]\n## 9. Quellen\nx\n", encoding="utf-8")
    assert "Fußnote [^7] hat keinen Nachweis" in meldungen(reise, tmp_path)


def test_wissen_karte(reise, tmp_path, capsys):
    """Orte je Recherche-Block auf regionalen Grundkarten; Namen im Text werden Kartenlinks (Issue #64)."""
    (reise / "extra.md").write_text("## 1. Kapitel\n### Teil\nIn Neustadt und Loschwitz, dann Leipzig und Nirgendwo.\n",
                                    encoding="utf-8")
    (reise / "medien/karte").mkdir(parents=True)
    (reise / "medien/karte/dresden.pmtiles").write_bytes(b"PMTiles\x03" + bytes(93) + b"\x0e" + bytes(25))
    (reise / "plan/kategorien.yaml").write_text("""
kategorien:
  schauplatz: {gruppe: wissen, name: Schauplatz, farbe: '#c62a2a'}
  einkehr_ort: {gruppe: wissen, name: Essen, farbe: rosa}
  verkehr: {gruppe: wissen, name: Bahnhof, farbe: grau, symbol: bus}
""", encoding="utf-8")
    (reise / "wp.yaml").write_text("""
grundkarten:
  dresden: {titel: Dresden, rahmen: {nord: 51.2, sued: 50.9, west: 13.5, ost: 14.0}}
  leipzig: {titel: Leipzig, rahmen: {nord: 51.5, sued: 51.2, west: 12.2, ost: 12.6}}
bloecke:
  W-20.teil:
  - {name: Neustadt, kat: schauplatz, lage: [51.07, 13.75], quelle: 'OSM node/1, Stand 2026-10-25'}
  - {name: Nirgendwo, kat: einkehr_ort}
  - {name: Leipzig, kat: verkehr, lage: [51.34, 12.37], quelle: 'OSM node/2, Stand 2026-10-25'}
  - {name: Loschwitz, kat: schauplatz, hinweis: geschlossen, lage: [51.05, 13.82], quelle: 'OSM node/3, Stand 2026-10-25'}
""", encoding="utf-8")
    setze(reise, lambda c: (c["abschnitte"].update({"extra.md": {"1. Kapitel": ["W-20", "wissen"]}}),
                            c.update({"wissen_punkte": "wp.yaml"})))
    d = baue(reise, tmp_path)
    wk = d["wissen_karte"]
    assert list(wk["grundkarten"]) == ["dresden"] and wk["grundkarten"]["dresden"]["maxzoom"] == 14
    assert [p["name"] for p in wk["punkte"]["W-20.teil"]] == ["Neustadt", "Loschwitz"]
    assert wk["punkte"]["W-20.teil"][1]["hinweis"] == "geschlossen"
    html = next(b for a in d["abschnitte"] for b in a["bloecke"] if b["id"] == "W-20.teil")["html"]
    assert 'data-p="W-20.teil:0">Neustadt</a>' in html and 'data-p="W-20.teil:1">Loschwitz</a>' in html
    assert "Leipzig</a>" not in html
    aus = capsys.readouterr().out
    assert "Grundkarten fehlen: leipzig" in aus and "Nirgendwo" in aus
    assert wk["punkte"]["W-20.teil"][0]["kat"] == "schauplatz" and d["kategorien"]["verkehr"]["symbol"] == "bus"
    assert "karte-dresden.pmtiles" in (tmp_path / "dist/sw.js").read_text() and (tmp_path / "dist/karte-dresden.pmtiles").exists()
    assert "protomaps-leaflet" in (tmp_path / "dist/index.html").read_text()
    (reise / "wp.yaml").write_text("bloecke:\n  W-99.x:\n  - {name: A, kat: quatsch, lage: [1, 2], quelle: x}\n", encoding="utf-8")
    assert "Block W-99.x gibt es nicht" in meldungen(reise, tmp_path)
    (reise / "wp.yaml").write_text("bloecke:\n  W-20.teil:\n  - {name: A, kat: quatsch, lage: [1, 2], quelle: x}\n", encoding="utf-8")
    assert "kat muss eine von schauplatz, einkehr_ort, verkehr sein" in meldungen(reise, tmp_path)
    (reise / "plan/kategorien.yaml").unlink()
    assert "die Reise hat keine Kategorien der Gruppe wissen" in meldungen(reise, tmp_path)


def test_kategorien_form(reise, tmp_path):
    """plan/kategorien.yaml: nur die Form wird geprüft (Gruppe, Farbe, Symbol, Felder), kein Katalog in der Software."""
    k = reise / "plan/kategorien.yaml"
    k.write_text("kategorien:\n  a: {gruppe: mitte, name: A, farbe: blau}\n  b: {gruppe: punkt, name: B, farbe: rot}\n"
                 "  c: {gruppe: punkt, name: C, farbe: '#12345', symbol: nix, quatsch: 1}\n"
                 "  D: {gruppe: punkt, name: D, farbe: blau}\n", encoding="utf-8")
    m = meldungen(reise, tmp_path)
    assert "kategorien.yaml a: gruppe muss punkt oder wissen sein" in m and "kategorien.yaml b: farbe muss" in m
    assert "c: farbe muss" in m and "c: symbol muss" in m and "c: unbekannte Felder quatsch" in m and "D: Schlüssel nur" in m


# ---------- Volllauf mit der Beispielreise (erfunden, beispiel/reisen/beispielreise) ----------
BEISPIEL = WURZEL / "beispiel/reisen/beispielreise"


def test_volllauf_beispiel(tmp_path):
    b = bauen.Bauer(BEISPIEL, tmp_path / "beispiel")
    d = b.daten()   # Fehler kämen hier als BauFehler
    b.schreiben(d)
    assert b.hinweise == []
    ids = alle_ids(d)
    assert len(ids) == len(set(ids)) and all(bauen.ZIEL_ID.match(i) for i in ids)
    assert [a["id"] for a in d["abschnitte"]] == (
        ["W-01", "E-01", "E-02", "E-03", "E-04"] + [f"W-{n:02d}" for n in range(2, 8)] + ["O-01", "O-03"])
    r = d["route"]
    assert r["warnungen"] == []
    p = {x["id"]: x for x in r["plaene"]}
    assert list(p) == ["P-A", "P-B"]
    for x in p.values():
        assert x["warnungen"] == [] and (x["summe"]["tage"], x["summe"]["naechte"]) == (4, 3)
    # Punkte je Wanderetappe, alle mit Quelle
    assert set(r["punkte"]) == {"E-01", "E-02", "E-03", "E-04"}
    assert all(r["punkte"][e] and all(x.get("quelle") for x in r["punkte"][e]) for e in r["punkte"])
    html = "".join(a.get("intro", "") + a.get("nach", "") + "".join(x["html"] for x in a["bloecke"])
                   for a in d["abschnitte"])
    assert '<sup class="fn">' in html and '<ol class="fussnoten">' in html
    # Skizze in Etappe 1: Link umgeschrieben, Datei kopiert
    assert 'src="medien/skizze-felsen.png"' in html and "../medien" not in html
    assert (tmp_path / "beispiel/medien/skizze-felsen.png").exists()
    assert (tmp_path / "beispiel/index.html").exists()


def test_unbekannte_unterkunftsart_ist_fehler(tmp_path):
    """Eine Art, die die Reise nicht in plan/arten.yaml definiert hat, ist ein Baufehler (docs/ontologie.md)."""
    kopie = tmp_path / "bsp"
    shutil.copytree(BEISPIEL, kopie)
    p = kopie / "plan" / "routen.yaml"
    p.write_text(p.read_text(encoding="utf-8").replace("art: herberge", "art: baumhaus", 1), encoding="utf-8")
    with pytest.raises(bauen.BauFehler) as e:
        bauen.Bauer(kopie, tmp_path / "aus").daten()
    assert "Art „baumhaus“ steht nicht in plan/arten.yaml" in str(e.value) and "gibt es hier nicht" not in str(e.value)
    d = bauen.Bauer(BEISPIEL, tmp_path / "aus2").daten()
    assert d["route"]["arten"]["herberge"]["name"] == "Herberge" and "kategorien" not in d["route"]
    assert {u["art"] for u in d["route"]["unterkuenfte"].values()} == {"hotel", "pension", "gasthof", "herberge"}


def test_ebenen_der_etappen(reise, tmp_path):
    """B2 (#53): Jeder Abschnitt einer Etappe gehört zu einer Ebene der Tagesseite, nach dem Titelanfang; reise.json
    etappen_ebenen gilt vor der Vorgabe; eine unbekannte Ebene ist ein Baufehler."""
    ebene = lambda d: {b["id"]: b["ebene"] for a in d["abschnitte"] if a["typ"] == "etappe" for b in a["bloecke"]}
    # Vorgabe nur für die Form (ADR-0001, kein Wandervokabular in der Software): Zusammenfassung, Eckdaten, Unterkünfte-Liste,
    # Quellen; was eine Reise sonst unterwegs nachschlagen will (Höhenprofil …), sagt sie in reise.json
    assert ebene(baue(reise, tmp_path)) == {"E-01.eckdaten": "unterwegs", "E-01.hoehenprofil": "hintergrund", "E-01.karten": "quellen",
                                            "E-01.unterkuenfte-liste": "unterwegs", "E-02V.zusammenfassung": "weg"}
    setze(reise, lambda c: c.update({"etappen_ebenen": {"unterwegs": ["höhen"], "hintergrund": ["Karten"]}}))
    e = ebene(baue(reise, tmp_path / "b"))
    assert e["E-01.hoehenprofil"] == "unterwegs" and e["E-01.karten"] == "hintergrund"
    setze(reise, lambda c: c.update({"etappen_ebenen": {"lesen": ["Eckdaten"]}}))
    assert "Ebene „lesen“ gibt es nicht" in meldungen(reise, tmp_path / "c")
    setze(reise, lambda c: c.update({"etappen_ebenen": {"weg": "Eckdaten"}}))
    assert "etappen_ebenen: erwartet" in meldungen(reise, tmp_path / "d")


def test_lesetext_stichworte_gegen_gliederung(tmp_path):
    """Stichworte im Lesetext einer Etappe gehören zur Gliederung ihrer Art; ein fremdes Stichwort ist ein Hinweis."""
    r = tmp_path / "beispielreise"
    shutil.copytree(BEISPIEL, r)
    e = r / "inhalt/etappen.md"
    e.write_text(e.read_text(encoding="utf-8").replace("**Ankommen.**", "**Abends.**", 1), encoding="utf-8")
    b = bauen.Bauer(r, tmp_path / "dist")
    d = b.daten()
    assert any(h.startswith("E-01: Stichwort „Abends“") and "Charakter, Verlauf" in h for h in b.hinweise), b.hinweise
    weg = next(x for x in d["abschnitte"] if x["id"] == "E-01")["bloecke"][0]
    assert weg["ebene"] == "weg" and "<strong>Charakter.</strong>" in weg["html"]
