"""Allgemeines Feld dinge: je Möglichkeit einer Wahlstelle (#453, Variante b aus #353,
Spec docs/specs/routen/dinge-als-moeglichkeit-453.md, AC-1 bis AC-19).

Eine Möglichkeit verweist über ein einziges Feld dinge: [U-…|A-…|O-…|E-…] auf ihre Dinge (Präfix = Grundform) statt über die
vier Felder unterkuenfte, aufenthalte, orte, strecken; folge bleibt eigenes Feld. Beim Laden teilt routen.dinge_aufteilen die
Liste in die bisherigen Gruppen auf, die Seitendaten bleiben gleich. Testdaten: erfundene Abwandlungen der beiden Beispielreisen,
als Daten über yaml (nicht über Textanker).
RED: dinge gibt es noch nicht (weder beim Laden noch im Schreibweg, im Konnektor oder beim Nachziehen)."""
import copy
import pathlib
import shutil
import sys

import pytest
import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import bauen  # noqa: E402
import konnektor as kn  # noqa: E402
import neu  # noqa: E402
import schnittstelle  # noqa: E402
import schreiben as sb  # noqa: E402
import texte  # noqa: E402
from conftest import meldet  # noqa: E402
from routen import KURZ_TEXT  # noqa: E402
from test_option_orte import B, HEUTE, WERT, kopie, option, wahl_von, wahlstelle  # noqa: E402
from test_schreiben import KARL, repo, routen_auf_main, schreiber  # noqa: E402,F401

REISEN = pathlib.Path(__file__).resolve().parents[2] / "beispiel" / "reisen"
GRUPPEN = ("unterkuenfte", "aufenthalte", "orte", "strecken")
PRAEFIX = {"U": "unterkuenfte", "A": "aufenthalte", "O": "orte", "E": "strecken"}


# ---------- Hilfen ----------

def dinge_zu_alt(r):
    """Abwandlung: alle Optionen mit dinge auf die früheren vier Felder zurückstellen (für die Tests des Formatwechsels).
    Das erste alte Feld steht an der Stelle von dinge; jede Gruppe in der Reihenfolge der Eingabe."""
    for w in (r.get("wahlstellen") or {}).values():
        for i, o in enumerate(w.get("optionen") or []):
            if "dinge" not in o:
                continue
            gruppen = {}
            for did in o["dinge"]:
                gruppen.setdefault(PRAEFIX[did.split("-")[0]], []).append(did)
            neu_ = {}
            for k, v in o.items():
                if k == "dinge":
                    neu_.update(gruppen)
                else:
                    neu_[k] = v
            w["optionen"][i] = neu_


def alt_kopie(tmp, reise="beispielreise"):
    """Kopie einer Beispielreise im früheren Format (Optionen mit unterkuenfte/orte …), wie eine Reise vor dem Software-Wechsel."""
    return kopie(tmp, reise=reise, routen=dinge_zu_alt, ort_merkmal=False)


def gebaut(tmp, **abwandlung):
    return bauen.bauen(kopie(tmp, **abwandlung), tmp / "web" / "b")


def baufehler(tmp, **abwandlung):
    with pytest.raises(bauen.BauFehler) as e:
        gebaut(tmp, **abwandlung)
    a = e.value.args[0]
    return [str(m) for m in a] if isinstance(a, (list, tuple)) else str(a).splitlines()


def optionsfehler(meldungen):
    """Meldungen, die einer der Prüfschlüssel pruefung.routen.option_* erzeugt (unbekanntes Ding, Präfix, altes Feld)."""
    schluessel = [k for k in texte.sprache("de").TEXTE if k.startswith("pruefung.routen.option_")]
    return [m for m in meldungen if any(meldet(m, k) for k in schluessel)]


def gruppen_von(o):
    return {k: o.get(k) for k in (*GRUPPEN, "folge")}


def routen_von(q):
    return yaml.safe_load((q / "plan" / "routen.yaml").read_text(encoding="utf-8"))


def option_roh(r, oid):
    return next(o for w in r["wahlstellen"].values() for o in w["optionen"] if o["id"] == oid)


# Stand der Seitendaten der Wanderung vor der Umstellung (gebaut mit den alten Feldern, 17.11.2026): die Gruppen je Möglichkeit
SEITE_VORHER = {
    "V-01.a": {"unterkuenfte": None, "aufenthalte": None, "orte": None, "strecken": None, "folge": ["T-04"]},
    "V-01.b": {"unterkuenfte": None, "aufenthalte": None, "orte": None, "strecken": None, "folge": ["T-05"]},
    "V-01.c": {"unterkuenfte": None, "aufenthalte": None, "orte": None, "strecken": None, "folge": ["T-06"]},
    "V-02.a": {"unterkuenfte": None, "aufenthalte": None, "orte": None, "strecken": None, "folge": []},
    "V-02.b": {"unterkuenfte": None, "aufenthalte": None, "orte": None, "strecken": None, "folge": []},
    "V-06.a": {"unterkuenfte": None, "aufenthalte": None, "orte": ["O-04"], "strecken": None, "folge": []},
    "V-06.b": {"unterkuenfte": None, "aufenthalte": None, "orte": ["O-06"], "strecken": None, "folge": []},
    "V-03.a": {"unterkuenfte": ["U-02"], "aufenthalte": None, "orte": None, "strecken": None, "folge": []},
    "V-03.b": {"unterkuenfte": ["U-03"], "aufenthalte": None, "orte": None, "strecken": None, "folge": []},
}

# Nachmittag an Tag 3 (erfunden): Strecke, Aufenthalt und Ort zusammen gegen einen Ort allein
V91 = wahlstelle("V-91",
                 option("V-91.a", "Burg und Altendorf (Beispiel)", dinge=["E-02", "A-01", "O-04"]),
                 option("V-91.b", "Zum Lichtenhainer Wasserfall (Beispiel)", dinge=["O-06"]))


# ---------- Laden und Prüfen ----------

def test_dinge_aufteilen_nach_praefix():
    """dinge_aufteilen (einzige Stelle, die die Präfixe kennt): U, A, O, E in ihre Gruppen, Reihenfolge je Gruppe wie eingegeben."""
    from routen import dinge_aufteilen
    g = dinge_aufteilen(["O-06", "E-02", "A-01", "O-04", "E-01"])
    assert g["orte"] == ["O-06", "O-04"] and g["strecken"] == ["E-02", "E-01"] and g["aufenthalte"] == ["A-01"]
    assert not g.get("unterkuenfte")
    assert dinge_aufteilen(["U-02"])["unterkuenfte"] == ["U-02"]


def test_dinge_wird_in_gruppen_aufgeteilt_und_baut(tmp_path):
    """AC-1: dinge: [E-02, A-01, O-04] steht in der Ausgabe als strecken, aufenthalte, orte, ohne Fehler."""
    d = gebaut(tmp_path, wahl=[V91])
    a, b = wahl_von(d, "V-91")["optionen"]
    assert a.get("strecken") == ["E-02"] and a.get("aufenthalte") == ["A-01"] and a.get("orte") == ["O-04"], gruppen_von(a)
    assert b.get("orte") == ["O-06"] and not b.get("strecken") and not b.get("aufenthalte") and not b.get("unterkuenfte")


def test_dinge_bewahrt_eingabereihenfolge(tmp_path):
    """AC-2: dinge: [O-06, O-04] bleibt in der Gruppe orte in dieser Reihenfolge."""
    v = wahlstelle("V-91", option("V-91.a", "Zwei Orte (Beispiel)", dinge=["O-06", "O-04"]),
                   option("V-91.b", "Ein Ort (Beispiel)", dinge=["O-04"]))
    d = gebaut(tmp_path, wahl=[v])
    assert wahl_von(d, "V-91")["optionen"][0]["orte"] == ["O-06", "O-04"]


def test_unbekannter_praefix_ist_ein_fehler(tmp_path):
    """AC-3: dinge: [X-01] ist genau ein Prüffehler mit Wahlstelle, Möglichkeit und ID."""
    v = wahlstelle("V-91", option("V-91.a", "Unbekannt (Beispiel)", dinge=["X-01"]), option("V-91.b", "Ort (Beispiel)", dinge=["O-06"]))
    meldungen = baufehler(tmp_path, wahl=[v])
    treffer = [m for m in meldungen if "X-01" in m]
    assert len(treffer) == 1, meldungen
    assert "V-91" in treffer[0] and "V-91.a" in treffer[0]
    assert optionsfehler(treffer), f"Text kommt aus einem Schlüssel pruefung.routen.option_*: {treffer}"


@pytest.mark.parametrize("did", ["U-99", "E-99", "A-99", "O-99"])
def test_unbekanntes_ding_je_praefix_ist_ein_fehler(tmp_path, did):
    """AC-4: unbekanntes Ding je Präfix ist ein Prüffehler, auch für U und E (vorher ungeprüft)."""
    v = wahlstelle("V-91", option("V-91.a", "Nirgendwo (Beispiel)", dinge=[did]), option("V-91.b", "Ort (Beispiel)", dinge=["O-06"]))
    meldungen = baufehler(tmp_path, wahl=[v])
    treffer = [m for m in meldungen if did in m]
    assert len(treffer) == 1, meldungen
    assert "V-91" in treffer[0] and "V-91.a" in treffer[0] and optionsfehler(treffer), treffer


@pytest.mark.parametrize("feld, wert", [("unterkuenfte", ["U-02"]), ("aufenthalte", ["A-01"]), ("orte", ["O-04"]), ("strecken", ["E-02"])])
@pytest.mark.parametrize("neben_dinge", [False, True])
def test_altes_feld_an_option_ist_pruefehler(tmp_path, feld, wert, neben_dinge):
    """AC-5: ein altes Feld an einer Option (allein oder neben dinge) ist ein Prüffehler mit Hinweis auf dinge; folge bleibt erlaubt."""
    felder = {feld: wert, **({"dinge": ["O-06"]} if neben_dinge else {})}
    v = wahlstelle("V-91", option("V-91.a", "Altes Feld (Beispiel)", **felder), option("V-91.b", "Ort (Beispiel)", dinge=["O-06"]))
    meldungen = baufehler(tmp_path, wahl=[v])
    treffer = [m for m in optionsfehler(meldungen) if "V-91.a" in m]
    assert treffer and any(feld in m and "dinge" in m for m in treffer), meldungen


def test_folge_bleibt_eigenes_feld(tmp_path):
    """AC-5, zweiter Teil: die Wanderung mit folge (V-01) baut ohne Optionsfehler."""
    d = bauen.bauen(REISEN / "beispielreise", tmp_path / "web" / "b")
    assert [o["folge"] for o in wahl_von(d, "V-01")["optionen"]] == [["T-04"], ["T-05"], ["T-06"]]


@pytest.mark.parametrize("inhalt, gueltig", [
    ({"dinge": ["U-02"]}, True),
    ({"folge": ["T-04"]}, True),
    ({"dinge": ["E-04"]}, True),
    ({"dinge": ["A-01"]}, True),
    ({"dinge": ["O-04"]}, True),
    ({"dinge": ["E-04", "A-01"]}, True),
    ({"dinge": ["O-04", "E-04"]}, True),
    ({"dinge": ["A-01", "O-04"]}, True),
    ({"dinge": ["E-04", "A-01", "O-04"]}, True),
    ({"dinge": ["U-02", "U-03"]}, True),
    ({"dinge": ["U-02", "O-04"]}, False),
    ({"dinge": ["U-02", "E-04"]}, False),
    ({"dinge": ["A-01", "U-02"]}, False),
    ({"dinge": ["O-04"], "folge": ["T-04"]}, False),
    ({"dinge": ["U-02"], "folge": ["T-04"]}, False),
    ({"dinge": [], "folge": []}, False),
    ({"dinge": []}, False),
])
def test_praefixregel_u_allein_folge_allein_e_a_o_zusammen(inhalt, gueltig):
    """AC-6: {U} allein, folge allein, {E, A, O} in jeder Teilmenge; Mischungen mit U oder folge und leerer Inhalt sind ungültig."""
    assert sb.option_inhalt_ok({"dinge": inhalt.get("dinge", []), "folge": inhalt.get("folge", [])}) is gueltig


def test_praefixregel_beim_bauen(tmp_path):
    """AC-6 im handgepflegten YAML: dinge: [U-02, O-04] ist ein Prüffehler der Möglichkeit."""
    v = wahlstelle("V-91", option("V-91.a", "Unterkunft und Ort (Beispiel)", dinge=["U-02", "O-04"]),
                   option("V-91.b", "Ort (Beispiel)", dinge=["O-06"]))
    meldungen = baufehler(tmp_path, wahl=[v])
    assert any("V-91.a" in m for m in meldungen), meldungen


# ---------- Schreibweg ----------

def test_schreibweg_nimmt_dinge_und_verlauf_hat_wechsel(repo):
    """AC-7: choice_create und option_create schreiben dinge als Liste der IDs in Eingabereihenfolge (ohne Anführungszeichen);
    unbekanntes Ding und ungültige Mischung werden abgelehnt."""
    _, origin, _, _ = repo
    s = schreiber(repo)
    a = s.schreiben("beispielreise", "wahlstelle_anlegen", {**KARL, "args": {
        "titel": "Nachmittag: Burg oder Wasserfall (Beispiel)", "wann": "unterwegs", "an": ["T-03"],
        "optionen": [{"titel": "Burg und Altendorf (Beispiel)", "dinge": ["O-04", "A-01"], "quelle": B},
                     {"titel": "Wasserfall (Beispiel)", "dinge": ["O-06"], "quelle": B}]}})
    assert a["ok"]
    r, text = routen_auf_main(origin)
    _, w = next((k, v) for k, v in r["wahlstellen"].items() if v["titel"].startswith("Nachmittag: Burg oder Wasserfall"))
    assert [o.get("dinge") for o in w["optionen"]] == [["O-04", "A-01"], ["O-06"]], "Eingabereihenfolge bleibt"
    assert not any(o.get(g) for o in w["optionen"] for g in GRUPPEN), "keine alten Felder mehr"
    assert "dinge: [O-04, A-01]" in text, "Listenwert ohne Anführungszeichen"
    s.vorbereiten()
    a = s.schreiben("beispielreise", "option_anlegen", {**KARL, "args": {"wahlstelle": "V-03", "titel": "Dritte Pension (Beispiel)",
                                                                         "dinge": ["U-04"], "quelle": B}})
    assert a["ok"]
    r, _ = routen_auf_main(origin)
    assert option_roh(r, "V-03.c")["dinge"] == ["U-04"]
    assert option_roh(r, "V-03.a")["dinge"] == ["U-02"], "nichts wird überschrieben"
    s.vorbereiten()
    with pytest.raises(sb.Ablehnung, match="O-77"):
        s.schreiben("beispielreise", "option_anlegen", {**KARL, "args": {"wahlstelle": "V-02", "titel": "X", "dinge": ["O-77"], "quelle": "x"}})
    with pytest.raises(sb.Ablehnung) as e:
        s.schreiben("beispielreise", "option_anlegen", {**KARL, "args": {"wahlstelle": "V-02", "titel": "X", "dinge": ["U-02", "O-04"], "quelle": "x"}})
    assert e.value.schluessel == "schreiben.option_bauen.2"


def test_option_update_dinge_setzen_ersetzen_leeren(repo):
    """AC-8: option_update setzt, ersetzt und leert dinge; Präfixregel auf dem zusammengeführten Stand; nur dinge ist eine Änderung
    (nicht option_aendern.8) und steht als Wechsel in der Antwort; die Entscheider-Sperre option_aendern.9 bleibt."""
    _, origin, _, _ = repo
    s = schreiber(repo)
    a = s.schreiben("beispielreise", "option_anlegen", {**KARL, "args": {"wahlstelle": "V-02", "titel": "Rast in Hohnstein (Beispiel)",
                                                                         "dinge": ["O-03"], "quelle": B}})
    assert a["ok"]
    s.vorbereiten()
    a = s.schreiben("beispielreise", "option_aendern", {**KARL, "args": {"ziel": "V-02.c", "dinge": ["O-03", "A-01"]}})
    assert a["ok"] and not meldet(a["text"], "schreiben.option_aendern.8")
    assert "A-01" in a["text"], f"der Wechsel von dinge steht in der Antwort: {a['text']}"
    r, _ = routen_auf_main(origin)
    assert option_roh(r, "V-02.c")["dinge"] == ["O-03", "A-01"]
    s.vorbereiten()
    a = s.schreiben("beispielreise", "option_aendern", {**KARL, "args": {"ziel": "V-02.c", "dinge": ["O-06"]}})
    r, _ = routen_auf_main(origin)
    assert option_roh(r, "V-02.c")["dinge"] == ["O-06"], "ersetzt"
    s.vorbereiten()
    s.schreiben("beispielreise", "option_aendern", {**KARL, "args": {"ziel": "V-02.c", "dinge": []}})
    r, _ = routen_auf_main(origin)
    assert not option_roh(r, "V-02.c").get("dinge"), "geleert"
    s.vorbereiten()
    with pytest.raises(sb.Ablehnung) as e:
        s.schreiben("beispielreise", "option_aendern", {**KARL, "args": {"ziel": "V-06.a", "dinge": ["U-02", "O-04"]}})
    assert e.value.schluessel == "schreiben.option_aendern.5"
    with pytest.raises(sb.Ablehnung) as e:   # V-03.a ist gewählt, Karl wirkt nur mit
        s.schreiben("beispielreise", "option_aendern", {**KARL, "args": {"ziel": "V-03.a", "dinge": ["U-03"]}})
    assert e.value.schluessel == "schreiben.option_aendern.9"


# ---------- Konnektor ----------

def test_konnektor_schema_hat_things_mit_alias_dinge():
    """AC-9: OPTION_FELDER hat dinge (Liste von Strings, Beschreibung aus dem Katalog), keines der alten Felder; nach außen heißt es things."""
    f = kn.OPTION_FELDER.get("dinge")
    assert f and f["type"] == "array" and f["items"]["type"] == "string"
    assert f["description"] == "@konnektor.feld.option_felder.dinge"
    assert not set(GRUPPEN) & set(kn.OPTION_FELDER), "die alten Felder stehen nicht mehr im Schema"
    assert "folge" in kn.OPTION_FELDER
    for werkzeug in ("option_anlegen", "option_aendern"):
        assert schnittstelle.parameter_zu_englisch(werkzeug).get("dinge") == "things"
    aussen = schnittstelle.aussen([kn.OPTION_ANLEGEN, kn.OPTION_AENDERN, kn.WAHLSTELLE_ANLEGEN])
    props = {w["name"]: w["inputSchema"]["properties"] for w in aussen}
    assert "things" in props["option_create"] and "things" in props["option_update"]
    assert "things" in props["choice_create"]["options"]["items"]["properties"]
    assert not {"accommodations", "stays", "places", "legs"} & set(props["option_create"])


OPTION_WERKZEUGE = [kn.OPTION_ANLEGEN, kn.OPTION_AENDERN, kn.WAHLSTELLE_ANLEGEN]


@pytest.mark.parametrize("sprache", ["en", "de"])
def test_konnektor_alte_parameter_werden_uebersetzt(repo, sprache):
    """AC-10: alte Parameter (englisch und deutsch) werden angenommen und als dinge geschrieben, in der Reihenfolge Unterkünfte,
    Aufenthalte, Orte, Strecken; das Ergebnis ist dasselbe wie mit things."""
    _, origin, _, _ = repo
    s = schreiber(repo)
    if sprache == "en":
        args = {"choice": "V-02", "title": "Rast (Beispiel)", "source": B, "legs": ["E-04"], "places": ["O-03"], "stays": ["A-01"]}
    else:
        args = {"wahlstelle": "V-02", "titel": "Rast (Beispiel)", "quelle": B, "strecken": ["E-04"], "orte": ["O-03"], "aufenthalte": ["A-01"]}
    name, intern = kn.aufruf_intern(OPTION_WERKZEUGE, "option_create" if sprache == "en" else "option_anlegen", args)
    assert name == "option_anlegen"
    a = s.schreiben("beispielreise", name, {**KARL, "args": intern})
    assert a["ok"]
    r, _ = routen_auf_main(origin)
    o = option_roh(r, "V-02.c")
    assert o["dinge"] == ["A-01", "O-03", "E-04"] and not any(o.get(g) for g in GRUPPEN), o
    s.vorbereiten()
    name, intern = kn.aufruf_intern(OPTION_WERKZEUGE, "option_create", {"choice": "V-02", "title": "Rast 2 (Beispiel)", "source": B,
                                                                    "things": ["A-01", "O-03", "E-04"]})
    s.schreiben("beispielreise", name, {**KARL, "args": intern})
    r, _ = routen_auf_main(origin)
    assert option_roh(r, "V-02.d")["dinge"] == o["dinge"], "gleiches Ergebnis wie mit things"
    s.vorbereiten()
    name, intern = kn.aufruf_intern(OPTION_WERKZEUGE, "option_update", {"target": "V-02.d", "places": ["O-06"]})
    s.schreiben("beispielreise", name, {**KARL, "args": intern})
    r, _ = routen_auf_main(origin)
    assert option_roh(r, "V-02.d")["dinge"] == ["O-06"], "auch option_update nimmt die alten Parameter"


@pytest.mark.parametrize("args", [
    {"choice": "V-02", "title": "Rast (Beispiel)", "source": B, "things": ["O-03"], "stays": ["A-01"]},
    {"choice": "V-02", "title": "Rast (Beispiel)", "source": B, "dinge": ["O-03"], "orte": ["O-04"]},
    {"choice": "V-02", "title": "Rast (Beispiel)", "source": B, "things": ["E-04"], "accommodations": ["U-02"]},
])
def test_konnektor_mischung_alt_und_neu_wird_abgelehnt(repo, args):
    """AC-11: things/dinge zusammen mit einem alten Parameter wird mit Begründung aus dem Katalog abgelehnt; nichts wird geschrieben."""
    _, origin, _, _ = repo
    s = schreiber(repo)
    vorher = routen_auf_main(origin)[1]
    with pytest.raises(sb.Ablehnung) as e:
        name, intern = kn.aufruf_intern(OPTION_WERKZEUGE, "option_create", args)
        s.schreiben("beispielreise", name, {**KARL, "args": intern})
    assert e.value.schluessel and texte.t("de", e.value.schluessel) != e.value.schluessel, "Begründung aus dem Katalog"
    assert "dinge" in str(e.value) or "things" in str(e.value)
    assert routen_auf_main(origin)[1] == vorher


# ---------- Formatwechsel (#250) ----------

def test_nachziehen_stellt_optionen_auf_dinge_um(tmp_path):
    """AC-12: nachziehen stellt alte Felder auf dinge um (an der Stelle des ersten alten Felds, Reihenfolge Unterkünfte, Aufenthalte,
    Orte, Strecken), folge und andere Felder bleiben, Meldung aus texte; die Reise baut danach mit gleichen Seitendaten."""
    q = alt_kopie(tmp_path)

    def gemischt(r):   # eine erfundene Option mit drei alten Feldern an Tag 3, nach plus (Reihenfolge der Schlüssel zählt)
        r["wahlstellen"]["V-91"] = {"titel": "V-91: erfundenes Beispiel", "wann": "unterwegs", "optionen": [
            {"id": "V-91.a", "titel": "Burg (Beispiel)", "plus": ["x"], "strecken": ["E-02"], "orte": ["O-04"], "aufenthalte": ["A-01"],
             "quelle": B, "verlauf": [{"datum": HEUTE, "status": "vorgeschlagen", "wer": "Claude"}]},
            {"id": "V-91.b", "titel": "Wasserfall (Beispiel)", "orte": ["O-06"], "quelle": B,
             "verlauf": [{"datum": HEUTE, "status": "vorgeschlagen", "wer": "Claude"}]}]}
        r["tage"]["T-03"]["wahl"] = list(r["tage"]["T-03"].get("wahl") or []) + ["V-91"]
    r = routen_von(q)
    gemischt(r)
    (q / "plan" / "routen.yaml").write_text(yaml.safe_dump(r, allow_unicode=True, sort_keys=False), encoding="utf-8")
    vorher = routen_von(q)
    assert "unterkuenfte" in option_roh(vorher, "V-03.a"), "Ausgangslage: altes Format"
    meldungen = neu.nachziehen(q, betrieb=False)
    nachher = routen_von(q)
    for w in nachher["wahlstellen"].values():
        for o in w["optionen"]:
            assert not set(GRUPPEN) & set(o), (o["id"], list(o))
    assert option_roh(nachher, "V-03.a")["dinge"] == ["U-02"] and option_roh(nachher, "V-06.b")["dinge"] == ["O-06"]
    a = option_roh(nachher, "V-91.a")
    assert a["dinge"] == ["A-01", "O-04", "E-02"], "Reihenfolge der alten Felder: Unterkünfte, Aufenthalte, Orte, Strecken"
    assert list(a) == ["id", "titel", "plus", "dinge", "quelle", "verlauf"], "dinge an der Stelle des ersten alten Felds"
    assert [o["folge"] for o in nachher["wahlstellen"]["V-01"]["optionen"]] == [["T-04"], ["T-05"], ["T-06"]]
    assert option_roh(nachher, "V-03.a")["verlauf"] == option_roh(vorher, "V-03.a")["verlauf"]
    assert meldet(meldungen, "pruefung.neu.nachziehen.dinge"), meldungen
    d = bauen.bauen(q, tmp_path / "web" / "b")
    for w in d["route"]["wahlstellen"]:
        for o in w["optionen"]:
            if o["id"] in SEITE_VORHER:
                assert gruppen_von(o) == SEITE_VORHER[o["id"]], o["id"]


def test_nachziehen_ist_idempotent(tmp_path):
    """AC-13: ein zweiter Lauf ändert nichts (byte-gleich) und meldet nichts zu dinge."""
    q = alt_kopie(tmp_path)
    neu.nachziehen(q, betrieb=False)
    stand = (q / "plan" / "routen.yaml").read_bytes()
    meldungen = neu.nachziehen(q, betrieb=False)
    assert (q / "plan" / "routen.yaml").read_bytes() == stand
    assert not meldet(meldungen, "pruefung.neu.nachziehen.dinge"), meldungen
    assert "dinge" in option_roh(routen_von(q), "V-03.a")


def test_nachziehen_speicher_stellt_um_und_ist_idempotent(tmp_path, monkeypatch):
    """AC-14: im Reisespeicher steht die umgestellte Fassung als neue, angehängte Version; ein zweiter Lauf legt keine weitere an."""
    monkeypatch.setenv("FR_SPEICHER", str(tmp_path / "_speicher"))
    import reisespeicher as rs
    q = alt_kopie(tmp_path)
    rs.importieren(q, "beispielreise", "Test", grund="Anfang")
    n = rs.stand_nummer("beispielreise")
    code, ausgabe = neu.nachziehen_speicher("beispielreise", tmp_path / "bau")
    assert code == 0, ausgabe
    assert rs.stand_nummer("beispielreise") > n, "die Umstellung steht als neue Version"
    rs.materialisieren("beispielreise", tmp_path / "frisch")
    r = routen_von(tmp_path / "frisch")
    assert option_roh(r, "V-03.a")["dinge"] == ["U-02"] and "unterkuenfte" not in option_roh(r, "V-03.a")
    n2 = rs.stand_nummer("beispielreise")
    code, ausgabe = neu.nachziehen_speicher("beispielreise", tmp_path / "bau2")
    assert code == 0 and rs.stand_nummer("beispielreise") == n2, ausgabe


# ---------- Beispielreisen und Seite ----------

def test_beispielreise_wanderung_nutzt_dinge_und_baut_gleich(tmp_path):
    """AC-15: V-03 und V-06 der Wanderung nutzen dinge; Summen der Reise und der Pläne sind unverändert."""
    r = routen_von(REISEN / "beispielreise")
    assert [o.get("dinge") for o in r["wahlstellen"]["V-03"]["optionen"]] == [["U-02"], ["U-03"]]
    assert [o.get("dinge") for o in r["wahlstellen"]["V-06"]["optionen"]] == [["O-04"], ["O-06"]]
    assert not any(set(GRUPPEN) & set(o) for w in r["wahlstellen"].values() for o in w["optionen"])
    d = bauen.bauen(REISEN / "beispielreise", tmp_path / "web" / "b")
    s = d["route"]["summe"]
    assert (s["min"], s["km"], s["auf"], s["ab"]) == (595, 25.4, 1075, 1025)
    assert {p["id"]: p["summe"]["min"] for p in d["route"]["plaene"]} == {"P-A": 610, "P-B": 595}


A90 = {"name": "Zoo von Beispielstadt (erfunden)", "ort": "O-02", "art": "museum", "quelle": B}


def test_stadtwochenende_baut_unveraendert_und_erfundene_wahlstelle_a_gegen_a(tmp_path):
    """AC-16: das Stadtwochenende baut ohne Fehler und Warnung; eine erfundene Wahlstelle am Sonntag (Stadtmuseum gegen ein
    erfundenes zweites Ziel) mit dinge baut ebenso; die Beispielreise selbst bleibt unverändert."""
    vorher = (REISEN / "stadtwochenende" / "plan" / "routen.yaml").read_bytes()
    d = bauen.bauen(REISEN / "stadtwochenende", tmp_path / "web" / "a")
    assert d["route"].get("warnungen") == [] and not d["route"].get("wahlstellen")
    v90 = wahlstelle("V-90", option("V-90.a", "Ins Stadtmuseum (Beispiel)", dinge=["A-02"]),
                     option("V-90.b", "In den Zoo (Beispiel)", dinge=["A-90"]))
    d2 = gebaut(tmp_path / "zwei", reise="stadtwochenende", wahl=[v90], tag="T-03", ort_merkmal=False, aufenthalte={"A-90": A90})
    a, b = wahl_von(d2, "V-90")["optionen"]
    assert a.get("aufenthalte") == ["A-02"] and b.get("aufenthalte") == ["A-90"]
    assert (REISEN / "stadtwochenende" / "plan" / "routen.yaml").read_bytes() == vorher


def test_seitendaten_unveraendert_gegen_vorher(tmp_path):
    """AC-17: die Seitendaten der Wanderung (R.wahlstellen[].optionen[]) haben dieselben Gruppen wie vor der Umstellung."""
    assert "dinge" in option_roh(routen_von(REISEN / "beispielreise"), "V-06.a"), "Wanderung ist umgestellt (AC-15)"
    d = bauen.bauen(REISEN / "beispielreise", tmp_path / "web" / "b")
    ist = {o["id"]: gruppen_von(o) for w in d["route"]["wahlstellen"] for o in w["optionen"]}
    assert ist == SEITE_VORHER


def test_arten_ableiten_und_art_der_option_ueber_dinge(tmp_path):
    """AC-18: arten_ableiten nimmt die Art der Wahlstelle aus dem ersten Ding mit Art in dinge; aufraeumen kennt die Art der Option
    (ein lang erlaubtes Merkmal der Unterkunftsart wird nicht als zu lang gemeldet)."""
    o92 = {"name": "Ort mit Pensionsart (erfunden)", "art": "pension", "quelle": B}
    v96 = wahlstelle("V-96", option("V-96.a", "Ort (Beispiel)", dinge=["O-92"], merkmale={"ausblick": WERT("ja")}),
                     option("V-96.b", "Wasserfall (Beispiel)", dinge=["O-06"]))
    v97 = wahlstelle("V-97", option("V-97.a", "Altendorf (Beispiel)", dinge=["O-04"]),
                     option("V-97.b", "Gasthof (Beispiel)", dinge=["U-03"], merkmale={"hausschuhe": WERT("ja")}))
    q = kopie(tmp_path, wahl=[v96, v97], orte={"O-92": o92}, ort_merkmal=False)
    gasthof = routen_von(q)["unterkuenfte"]["U-03"].get("art")
    a = yaml.safe_load(neu.arten_ableiten(q, schreiben=False))["arten"]
    assert "ausblick" in (a["pension"].get("merkmale") or {}), "Merkmal der Möglichkeit landet an der Art des ersten Orts mit Art"
    assert "hausschuhe" in (a[gasthof].get("merkmale") or {}), "die Art der Unterkunft bleibt die Art der Wahlstelle"

    def lang(r):
        o = option_roh(r, "V-03.a")
        o.setdefault("merkmale", {})["einschaetzung"] = WERT("lang " * (KURZ_TEXT // 4 + 5))
    q2 = kopie(tmp_path / "zwei", routen=lang, ort_merkmal=False)
    assert option_roh(routen_von(q2), "V-03.a").get("dinge") == ["U-02"]
    assert not [x for x in neu.aufraeumen(q2) if x.startswith("V-03.a einschaetzung")], "Art pension erlaubt lange Einschätzung"


# ---------- Texte ----------

def test_neue_schluessel_in_allen_sprachen():
    """AC-19: die neuen Schlüssel stehen in allen Sprachen (dinge im Konnektor, Prüffehler, Nachziehmeldung)."""
    for sp in texte.SPRACHEN:
        katalog = texte.sprache(sp).TEXTE
        assert "konnektor.feld.option_felder.dinge" in katalog, sp
        assert "pruefung.neu.nachziehen.dinge" in katalog, sp
        for alt in GRUPPEN:
            assert f"konnektor.feld.option_felder.{alt}" not in katalog, f"{sp}: Beschreibung des alten Felds {alt} entfällt"
    de = texte.sprache("de").TEXTE
    assert "dinge" in de["schreiben.option_bauen.2"] and "dinge" in de["schreiben.option_aendern.5"], "Ablehnungen nennen die Präfixregel an dinge"
