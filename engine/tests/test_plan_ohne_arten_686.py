"""#686: Plan-Werkzeuge in Reisen ohne Arten lehnen ab, Arten tragen den Plan sofort ein (Spec
docs/specs/konnektor/plan-ohne-arten-686.md). Nur erfundene Daten: frische Reisen aus der Vorlage (Ida, Karl) und Kopien der
beiden Beispielreisen (beispielreise: Ida, Karl; stadtwochenende: Tom, Lea), alles unter tmp_path."""
import datetime
import json
import shutil
import sys
from pathlib import Path

import pytest
import yaml

ENGINE = Path(__file__).resolve().parents[1]
BEISPIEL = ENGINE.parent / "beispiel" / "reisen"
sys.path.insert(0, str(ENGINE))
import bauen  # noqa: E402
import neu  # noqa: E402
import schreiben  # noqa: E402
import texte  # noqa: E402
from test_schreiben_speicher import schreib, speicher, zustand  # noqa: E402,F401  (Fixture des Speicherwegs)

SCHLUESSEL = "schreiben.plan.ohne_arten"
IDA = {"name": "Ida", "rolle": "organisator", "person": "ida"}
PERSONEN = {"ida": {"name": "Ida", "rolle": "organisator"}, "karl": {"name": "Karl", "rolle": "mitwirkend"}}
WAHLSTELLE = {"titel": "Hütte für die zweite Nacht",
              "optionen": [{"titel": "Obere Hütte", "quelle": "Gespräch"}, {"titel": "Untere Hütte", "quelle": "Gespräch"}]}
ART = {"bezeichnung": "Hütte", "grundform": "aufenthalt", "buchbar": True}   # Beispielwert

# Werkzeuge des Konnektors (englisch) mit ihrem Schreibweg und gültigen Angaben für eine frische Reise
PLAN_WERKZEUGE = {
    "item_create": ("ding_anlegen", {"was": "ort", "titel": "Oberstdorf", "quelle": "Gespräch"}),
    "start_end_set": ("start_ende_setzen", {"ende_datum": "2027-02-12", "grund": "Im Gespräch"}),
    "day_create": ("tag_anlegen", {"titel": "Anreise"}),
    "fixed_date_set": ("termin_setzen", {"datum": "2027-02-07", "titel": "Skikurs", "quelle": "Gespräch"}),
}


def frische_reise(tmp_path):
    """Reise aus der Vorlage, wie trip_create sie anlegt: ohne Arten, ohne plan/routen.yaml, ohne routen in reise.json."""
    r = neu.anlegen(tmp_path / "reisen", titel="Skiurlaub im Tal", von=datetime.date(2027, 2, 6),
                    bis=datetime.date(2027, 2, 13), personen=PERSONEN, wer="Ida", ziel="Oberstdorf",
                    heute=datetime.date(2026, 10, 27))
    assert not schreiben.arten_laden(r) and "routen" not in reise_json(r)
    return r


def reise_json(r):
    return json.loads((r / "reise.json").read_text(encoding="utf-8"))


def beispiel_kopie(tmp_path, name="beispielreise"):
    r = tmp_path / name
    shutil.copytree(BEISPIEL / name, r)
    return r


def altlast(r):
    """Der Zustand, den der Fehler hinterlassen hat: Arten und plan/routen.yaml, aber kein routen in reise.json."""
    cfg = reise_json(r)
    del cfg["routen"]
    (r / "reise.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    assert schreiben.arten_laden(r) and (r / "plan/routen.yaml").exists()
    return r


def plan_eingetragen(r):
    routen = reise_json(r).get("routen") or {}
    return routen.get("datei") == "plan/routen.yaml" and bool(routen.get("tagesplan")) and bool(routen.get("unterkuenfte"))


# ---------- AC-1: Wahlstelle ohne Arten ----------

def test_wahlstelle_ohne_arten_wird_abgelehnt(tmp_path):
    """AC-1: choice_create in einer Reise ohne Arten meldet keinen Erfolg, sondern lehnt mit dem Weg über die Arten ab."""
    r = frische_reise(tmp_path)
    with pytest.raises(schreiben.Ablehnung) as e:
        schreiben.WERKZEUGE["wahlstelle_anlegen"](r, IDA, WAHLSTELLE)
    assert e.value.schluessel == SCHLUESSEL, str(e.value)
    assert "routen" not in reise_json(r)


def als_text(inhalt):
    return inhalt.decode("utf-8") if isinstance(inhalt, bytes) else (inhalt or "")


def test_wahlstelle_ohne_arten_laesst_den_speicher_unveraendert(speicher, monkeypatch):
    """AC-1 über den Schreibweg des Dienstes: die frisch angelegte Reise bekommt keine neue Fassung, und die im selben Vorgang
    schon angelegte offene Frage verschwindet mit der Arbeitskopie."""
    from test_schreiben_speicher import _auftrag
    reise = "skiwoche-allgaeu-2027"
    monkeypatch.setenv("FR_SPEICHERREISEN", f"beispielreise,stadtwochenende,{reise}")
    wer = {"person": "ida", "name": "Ida", "rolle": "organisator"}
    code, a = schreib(speicher, reise, "reise_anlegen", {"person": None, "name": "Ida", "rolle": "organisator",
                                                         "args": {"auftrag": _auftrag(reise)}})
    assert code == 200 and a["ok"], a
    bausteine = yaml.safe_load(als_text(speicher.rs.aktueller_stand(reise)["reise.yaml"])).get("bausteine") or []
    code, a = schreib(speicher, reise, "einstellung_setzen", {**wer, "args": {"bausteine": [*bausteine, "varianten"]}})
    assert code == 200 and a["ok"], a
    vorher = zustand(speicher, reise)
    code, a = schreib(speicher, reise, "wahlstelle_anlegen", {**wer, "args": WAHLSTELLE})
    assert code == 422 and a["ok"] is False and a.get("fehler_code") == SCHLUESSEL, (code, a)
    assert zustand(speicher, reise) == vorher
    # die Vorlage bringt schon ihre eigene Frage F-01 mit; es darf nur keine Frage zur abgelehnten Wahlstelle dazukommen
    assert WAHLSTELLE["titel"] not in als_text(speicher.rs.aktueller_stand(reise).get("offene-fragen.md"))


# ---------- AC-2: übrige Plan-Werkzeuge ohne Arten ----------

@pytest.mark.parametrize("werkzeug", sorted(PLAN_WERKZEUGE))
def test_plan_werkzeuge_ohne_arten_werden_abgelehnt(tmp_path, werkzeug):
    """AC-2: item_create, start_end_set, day_create, fixed_date_set lehnen in einer Reise ohne Arten mit demselben Text ab."""
    r = frische_reise(tmp_path)
    name, args = PLAN_WERKZEUGE[werkzeug]
    with pytest.raises(schreiben.Ablehnung) as e:
        schreiben.WERKZEUGE[name](r, IDA, dict(args))
    assert e.value.schluessel == SCHLUESSEL, (werkzeug, str(e.value))
    assert "routen" not in reise_json(r)


# ---------- AC-3: Text in allen Sprachen ----------

def test_ablehnung_in_allen_sprachen():
    """AC-3: Der Text steht in jeder Sprachdatei und nennt den Weg über die Arten (kinds_adopt, kind_define)."""
    for k in texte._dateien():
        modul = texte.sprache(k)
        assert SCHLUESSEL in modul.TEXTE, k
        text = modul.TEXTE[SCHLUESSEL]
        assert "kinds_adopt" in text and "kind_define" in text, (k, text)
    assert str(schreiben.Ablehnung(SCHLUESSEL)) != SCHLUESSEL


# ---------- AC-4: Arten tragen einen vorhandenen Plan ein ----------

def geruest_ohne_eintrag(tmp_path):
    r = frische_reise(tmp_path)
    schreiben.plan_sicherstellen(r)   # Gerüst wie bisher beim ersten Plan-Werkzeug, ohne Eintrag
    assert (r / "plan/routen.yaml").exists() and "routen" not in reise_json(r)
    return r


def test_arten_uebernehmen_traegt_vorhandenen_plan_ein(tmp_path):
    """AC-4: kinds_adopt (Vorlagen) trägt einen schon liegenden Plan sofort in reise.json ein; choice_create gelingt danach."""
    r = geruest_ohne_eintrag(tmp_path)
    schreiben.WERKZEUGE["arten_uebernehmen"](r, IDA, {"vorlage": True})
    assert plan_eingetragen(r), reise_json(r).get("routen")
    schreiben.WERKZEUGE["wahlstelle_anlegen"](r, IDA, WAHLSTELLE)
    assert "V-01" in (yaml.safe_load((r / "plan/routen.yaml").read_text(encoding="utf-8")).get("wahlstellen") or {})


def test_art_definieren_traegt_plan_ein(tmp_path):
    """AC-4: kind_define trägt einen schon liegenden Plan sofort in reise.json ein."""
    r = geruest_ohne_eintrag(tmp_path)
    schreiben.WERKZEUGE["art_definieren"](r, IDA, dict(ART))
    assert plan_eingetragen(r), reise_json(r).get("routen")
    assert schreiben.warnungen_des_baus(r) == []


def test_arten_ohne_plan_legen_keinen_plan_an(tmp_path):
    """AC-4, Abgrenzung: Ohne plan/routen.yaml bleibt es nach der ersten Art wie bisher (der Plan entsteht beim ersten
    Plan-Werkzeug)."""
    r = frische_reise(tmp_path)
    schreiben.WERKZEUGE["art_definieren"](r, IDA, dict(ART))
    assert not (r / "plan/routen.yaml").exists()


# ---------- AC-5: mit Arten ist der Plan nach dem ersten Werkzeug sichtbar ----------

def test_plan_nach_erstem_werkzeug_sofort_sichtbar(tmp_path):
    """AC-5: Reise mit Arten, noch ohne Plan: choice_create trägt den Plan ein, der Bau enthält die Wahlstelle."""
    r = frische_reise(tmp_path)
    schreiben.WERKZEUGE["art_definieren"](r, IDA, dict(ART))
    schreiben.WERKZEUGE["wahlstelle_anlegen"](r, IDA, WAHLSTELLE)
    assert plan_eingetragen(r)
    route = bauen.bauen(r, tmp_path / "dist")["route"]
    assert "V-01" in json.dumps(route, ensure_ascii=False, default=str)


@pytest.mark.parametrize("werkzeug", sorted(PLAN_WERKZEUGE))
def test_plan_werkzeuge_mit_arten_tragen_plan_ein(tmp_path, werkzeug):
    """AC-5: Auch die Werkzeuge ohne Probebau (Tag, Termin, Start und Ende, Ort) tragen den Plan ein, sobald es Arten gibt."""
    r = frische_reise(tmp_path)
    schreiben.WERKZEUGE["art_definieren"](r, IDA, dict(ART))
    name, args = PLAN_WERKZEUGE[werkzeug]
    schreiben.WERKZEUGE[name](r, IDA, dict(args))
    assert plan_eingetragen(r), (werkzeug, reise_json(r).get("routen"))
    assert schreiben.warnungen_des_baus(r) == [], werkzeug


# ---------- AC-6: nachziehen heilt die Altlast ----------

def meldungen_routen(meldungen):
    return [m for m in meldungen if "reise.json" in m and "routen" in m]


def test_nachziehen_heilt_altlast(tmp_path):
    """AC-6: Reise mit Arten und Plan, aber ohne Eintrag: nachziehen trägt ihn ein und meldet es; ein zweiter Lauf meldet dazu
    nichts mehr; die Vorschau schreibt nichts, meldet es aber."""
    vorschau = altlast(beispiel_kopie(tmp_path / "a"))
    vorher = (vorschau / "reise.json").read_bytes()
    assert meldungen_routen(neu.nachziehen(vorschau, schreiben=False, betrieb=False))
    assert (vorschau / "reise.json").read_bytes() == vorher

    r = altlast(beispiel_kopie(tmp_path / "b"))
    assert meldungen_routen(neu.nachziehen(r, betrieb=False))
    assert plan_eingetragen(r)
    nachher = (r / "reise.json").read_bytes()
    assert not meldungen_routen(neu.nachziehen(r, betrieb=False))
    assert (r / "reise.json").read_bytes() == nachher
    bauen.bauen(r, tmp_path / "dist")


def test_nachziehen_meldet_bei_gesunder_reise_nichts(tmp_path):
    """AC-6, Gegenprobe: Die Beispielreisen haben ihren Eintrag; nachziehen meldet dazu nichts und lässt reise.json gleich."""
    for name in ("beispielreise", "stadtwochenende"):
        r = beispiel_kopie(tmp_path, name)
        vorher = (r / "reise.json").read_bytes()
        assert not meldungen_routen(neu.nachziehen(r, betrieb=False)), name
        assert (r / "reise.json").read_bytes() == vorher, name


def test_nachziehen_speicher_beim_veroeffentlichen_heilt_altlast(speicher, tmp_path):
    """AC-6: Dieselbe Altlast im Reisespeicher wird beim Veröffentlichen (nachziehen-speicher) geheilt, ohne Handschritt."""
    r = altlast(beispiel_kopie(tmp_path / "quelle"))
    speicher.rs.importieren(r, "altlast-686", wer="Ida", grund="Beispiel")
    code, zeilen = neu.nachziehen_speicher("altlast-686", tmp_path / "bau")
    assert code == 0, zeilen
    cfg = json.loads(als_text(speicher.rs.aktueller_stand("altlast-686")["reise.json"]))
    assert (cfg.get("routen") or {}).get("datei") == "plan/routen.yaml", zeilen


# ---------- AC-7: die rohe Schreibstelle lehnt nie ab ----------

def test_roh_schreiben_ohne_arten_erlaubt(tmp_path):
    """AC-7: Gerüst (plan_sicherstellen), die rohe Funktion und nachziehen schreiben in einer Reise ohne Arten ohne Ablehnung."""
    r = frische_reise(tmp_path)
    schreiben.plan_sicherstellen(r)
    roh = schreiben.routen_laden(r)
    roh["route"] = []
    schreiben.routen_datei_schreiben(r, roh)
    neu.nachziehen(r, betrieb=False)
    assert neu.umbrechen(r, schreiben=True) == []
    assert "routen" not in reise_json(r)


# ---------- AC-8: Beispielreisen wie bisher ----------

@pytest.mark.parametrize("name, wer", [("beispielreise", IDA), ("stadtwochenende", {"name": "Tom", "rolle": "organisator",
                                                                                    "person": "tom"})])
def test_beispielreisen_unveraendert(tmp_path, name, wer):
    """AC-8: In den Beispielreisen (mit Arten und Eintrag) gelingt ein Plan-Werkzeug wie bisher; reise.json bleibt byte-gleich."""
    r = beispiel_kopie(tmp_path, name)
    vorher, warnungen = (r / "reise.json").read_bytes(), schreiben.warnungen_des_baus(r)
    schreiben.WERKZEUGE["termin_setzen"](r, wer, {"datum": str(yaml.safe_load((r / "plan/routen.yaml").read_text(encoding="utf-8"))
                                                                    ["start"]["datum"]),
                                                  "titel": "Treffen am Bahnhof", "quelle": "Gespräch"})
    assert (r / "reise.json").read_bytes() == vorher
    assert schreiben.warnungen_des_baus(r) == warnungen
