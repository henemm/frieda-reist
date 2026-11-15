"""Tests für #587: Meldungen aus der Claude-App sofort als Issue für die Entwicklung, ohne persönliche Daten.

Nur erfundene Daten (beispielreise mit Ida und Karl, stadtwochenende mit Tom und Lea, Adressen unter beispiel.invalid).
Es geht nie ein Aufruf an GitHub hinaus: entwicklung._senden ist in jedem Test ersetzt; ein echter Aufruf macht den Test rot.
"""
import json
import sys
from pathlib import Path

import pytest

ENGINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import entwicklung  # noqa: E402
import konnektor as kn  # noqa: E402
import konten  # noqa: E402
import schnittstelle  # noqa: E402
from conftest import meldet  # noqa: E402
from test_anmeldung import welt  # noqa: E402,F401  (Fixture, von zwei gebraucht)
from test_trennung import zwei, IDA  # noqa: E402,F401  (zwei: Fixture)
from test_betreiber_meldung import (betreiber_anlegen, db_welt, konto_neu, mails, melden, nummer,  # noqa: E402,F401
                                    werkzeug_von, zeilen, FEHLER_TEXT, ZUSAMMENHANG, BETR_DE, BETR_EN)

REPO = "beispiel-besitzer/beispiel-software"
TOKEN = "beispielwert-kein-echter-schluessel"
OEFFENTLICH = "Beispielwert: Nach dem Öffnen eines Tages lädt die Karte nicht, es bleibt eine graue Fläche."
ADRESSE = f"https://github.com/{REPO}/issues/4711"


class GitHub:
    """Ersatz für entwicklung._senden: merkt sich jeden Aufruf und antwortet nach Vorgabe."""
    def __init__(self, antworten=None):
        self.aufrufe = []
        self.antworten = list(antworten or [(201, {"html_url": ADRESSE})])

    def __call__(self, url, kopf, daten):
        self.aufrufe.append((url, kopf, json.loads(json.dumps(daten))))
        a = self.antworten.pop(0) if len(self.antworten) > 1 else self.antworten[0]
        if isinstance(a, Exception):
            raise a
        return a


@pytest.fixture(autouse=True)
def kein_netz(monkeypatch):
    """Ohne Einstellung und mit einem Ersatz, der jeden unerwarteten Aufruf meldet."""
    for n in ("FR_MELDUNGEN_REPO", "FR_MELDUNGEN_TOKEN"):
        monkeypatch.delenv(n, raising=False)

    def verboten(*a, **kw):
        raise AssertionError("echter Aufruf an GitHub")
    monkeypatch.setattr(entwicklung, "_senden", verboten)


@pytest.fixture
def angebunden(monkeypatch):
    monkeypatch.setenv("FR_MELDUNGEN_REPO", REPO)
    monkeypatch.setenv("FR_MELDUNGEN_TOKEN", TOKEN)
    gh = GitHub()
    monkeypatch.setattr(entwicklung, "_senden", gh)
    return gh


# ---------- ohne Einstellung: alles wie vor #587 ----------

def test_ohne_einstellung_unveraendert(zwei, db_welt):
    u = zwei()
    betreiber_anlegen()
    assert not entwicklung.eingerichtet()
    w = werkzeug_von(u.a)
    assert "oeffentlicher_text" not in w["inputSchema"]["properties"]
    assert w["description"] == kn.texte.t(u.a["sprache"], "konnektor.werkzeug.an_frieda_melden")
    t, fehler = melden(u.a, art="Fehler", text=FEHLER_TEXT, oeffentlicher_text=OEFFENTLICH + " Karl")
    assert fehler is False and meldet(t, "konnektor.an_frieda_melden.angekommen"), t
    z = zeilen(u.a["id"])
    assert len(z) == 1 and z[0]["issue"] is None


def test_nur_repo_oder_nur_token_ist_nicht_eingerichtet(monkeypatch):
    monkeypatch.setenv("FR_MELDUNGEN_REPO", REPO)
    assert not entwicklung.eingerichtet()
    monkeypatch.delenv("FR_MELDUNGEN_REPO")
    monkeypatch.setenv("FR_MELDUNGEN_TOKEN", TOKEN)
    assert not entwicklung.eingerichtet()
    monkeypatch.setenv("FR_MELDUNGEN_REPO", "keine form")
    assert not entwicklung.eingerichtet()


def test_ohne_einstellung_mail_wie_bisher(db_welt):
    betreiber_anlegen()
    t, fehler = melden(db_welt["ida"], art="Wunsch", text=FEHLER_TEXT, oeffentlicher_text=OEFFENTLICH)
    assert fehler is False and meldet(t, "konnektor.an_frieda_melden.angekommen")
    assert sorted(m["an"] for m in mails(db_welt["mails"])) == [BETR_DE, BETR_EN]


# ---------- mit Einstellung ----------

def test_werkzeug_mit_oeffentlicher_fassung(zwei, angebunden):
    u = zwei()
    w = werkzeug_von(u.a)
    props = w["inputSchema"]["properties"]
    assert "oeffentlicher_text" in props and set(w["inputSchema"]["required"]) == {"text", "art"}
    assert meldet(w["description"], "konnektor.werkzeug.an_frieda_melden.entwicklung", u.a["sprache"])
    assert schnittstelle.PARAMETER.get("oeffentlicher_text") == "public_text"
    ok = lambda r: {"result": r}   # noqa: E731
    aussen = kn.frieda_antwort({"konto_id": u.a["id"]}, 1, "tools/list", {}, ok)["result"]["tools"]
    w_en = next(x for x in aussen if x["name"] == "report_to_frieda")
    assert "public_text" in w_en["inputSchema"]["properties"]
    en = kn.frieda_antwort({"konto_id": u.a["id"]}, 2, "tools/call", {"name": "report_to_frieda", "arguments": {
        "text": FEHLER_TEXT, "art": "Fehler", "context": ZUSAMMENHANG, "public_text": OEFFENTLICH}}, ok)["result"]
    assert en["isError"] is False and len(angebunden.aufrufe) == 1


@pytest.mark.parametrize("reise", ["beispielreise", "stadtwochenende"])
def test_issue_wird_angelegt_und_meldung_abgehakt(zwei, angebunden, reise, tmp_path):
    u = zwei()
    betreiber_anlegen()
    k = u.a if reise == "beispielreise" else u.b
    t, fehler = melden(k, art="Fehler", text=FEHLER_TEXT + " (bei " + k["name"] + ")", reise=reise,
                       zusammenhang=ZUSAMMENHANG, oeffentlicher_text="  " + OEFFENTLICH + "  ")
    assert fehler is False and meldet(t, "konnektor.an_frieda_melden.issue", k["sprache"]), t
    assert ADRESSE in t
    z = zeilen(k["id"])
    assert len(z) == 1 and z[0]["issue"] == ADRESSE and nummer(t.replace(ADRESSE, "")) == z[0]["id"]
    assert z[0]["text"].startswith(FEHLER_TEXT) and z[0]["zusammenhang"] == ZUSAMMENHANG and z[0]["reise"] == reise
    assert konten.betreiber_meldungen() == []   # abgehakt: nicht mehr offen
    # keine Mail an den Betreiber, wenn das Issue steht
    assert mails(Path(tmp_path) / "mails.jsonl") == []
    (url, kopf, daten), = angebunden.aufrufe
    assert url == f"https://api.github.com/repos/{REPO}/issues"
    assert kopf["Authorization"] == "Bearer " + TOKEN
    assert daten["labels"] == ["aus der App", "Fehler"]   # Sprache des ältesten Betreiber-Kontos (de)
    assert daten["title"].startswith("Fehler: Beispielwert: Nach dem Öffnen") and len(daten["title"]) <= 80
    assert OEFFENTLICH in daten["body"] and meldet(daten["body"], "konto.betreiber_meldung.issue_fuss")
    # nichts Persönliches und keine Kennung von Konto oder Instanz im Issue
    alles = json.dumps(daten, ensure_ascii=False)
    for geheim in (k["id"], k["email"], k["name"], reise, FEHLER_TEXT, ZUSAMMENHANG, TOKEN, "4711"):
        assert geheim not in alles, geheim


def test_etiketten_in_der_sprache_des_betreibers(db_welt, angebunden):
    konto_neu("k-betr-en", BETR_EN, "Betrieb English", "en", "betreiber")
    t, fehler = melden(db_welt["ida"], art="Wunsch", text=FEHLER_TEXT, oeffentlicher_text=OEFFENTLICH)
    assert fehler is False
    assert angebunden.aufrufe[0][2]["labels"] == ["from the app", "wish"]


@pytest.mark.parametrize("fall", ["mitreisende", "eigener_name", "titel", "ordner", "ort", "unterkunft", "mail",
                                  "gross_klein", "stadt_person", "stadt_unterkunft"])
def test_persoenliche_angaben_werden_abgelehnt(zwei, angebunden, fall):
    u = zwei()
    k = u.b if fall.startswith("stadt") else u.a
    wort = {"mitreisende": "Karl", "eigener_name": "Ida", "titel": "Beispielreise – Malerweg in vier Tagen",
            "ordner": "beispielreise", "ort": "Hohnstein", "unterkunft": "Pension Burgblick",
            "mail": "jemand@beispiel.invalid", "gross_klein": "KARL", "stadt_person": "Lea",
            "stadt_unterkunft": "Gästezimmer bei Tante Anna"}[fall]
    t, fehler = melden(k, art="Fehler", text=FEHLER_TEXT, oeffentlicher_text=f"{OEFFENTLICH} Gesehen bei {wort}.")
    assert fehler is True and meldet(t, "konnektor.an_frieda_melden.persoenlich", k["sprache"]), t
    assert angebunden.aufrufe == [] and zeilen(k["id"]) == []   # nichts angelegt, zählt nicht in die Grenze


def test_teil_eines_wortes_ist_kein_treffer(zwei, angebunden):
    u = zwei()
    t, fehler = melden(u.a, art="Wunsch", text=FEHLER_TEXT,
                       oeffentlicher_text="Beispielwert: Karlsruhe und Idaho wären als Beispiele schön.")
    assert fehler is False, t
    assert len(angebunden.aufrufe) == 1


def test_github_fehler_meldung_geht_per_mail(db_welt, monkeypatch, capsys):
    monkeypatch.setenv("FR_MELDUNGEN_REPO", REPO)
    monkeypatch.setenv("FR_MELDUNGEN_TOKEN", TOKEN)
    betreiber_anlegen()
    for antwort in ([(500, {})], [(401, {"message": "Bad credentials"})], [OSError("kein Netz")],
                    [entwicklung.EntwicklungFehler("URLError")], [(201, {})]):
        gh = GitHub(antwort)
        monkeypatch.setattr(entwicklung, "_senden", gh)
        vorher = len(mails(db_welt["mails"]))
        t, fehler = melden(db_welt["ida"], art="Fehler", text=FEHLER_TEXT, oeffentlicher_text=OEFFENTLICH)
        assert fehler is False and meldet(t, "konnektor.an_frieda_melden.angekommen"), (antwort, t)
        assert len(mails(db_welt["mails"])) == vorher + 2
        assert zeilen("k-ida")[-1]["issue"] is None
    err = [z for z in capsys.readouterr().err.splitlines() if z.startswith("operator report")]
    assert err and all(": issue failed:" in z and TOKEN not in z and FEHLER_TEXT not in z for z in err)


def test_etiketten_abgelehnt_zweiter_versuch_ohne(db_welt, monkeypatch):
    monkeypatch.setenv("FR_MELDUNGEN_REPO", REPO)
    monkeypatch.setenv("FR_MELDUNGEN_TOKEN", TOKEN)
    gh = GitHub([(422, {"message": "Validation Failed"}), (201, {"html_url": ADRESSE})])
    monkeypatch.setattr(entwicklung, "_senden", gh)
    t, fehler = melden(db_welt["ida"], art="Frage", text=FEHLER_TEXT, oeffentlicher_text=OEFFENTLICH)
    assert fehler is False and ADRESSE in t
    assert [("labels" in d) for _, _, d in gh.aufrufe] == [True, False]


def test_ohne_oeffentliche_fassung_wie_bisher(db_welt, angebunden):
    betreiber_anlegen()
    t, fehler = melden(db_welt["ida"], art="Fehler", text=FEHLER_TEXT)
    assert fehler is False and meldet(t, "konnektor.an_frieda_melden.angekommen")
    assert angebunden.aufrufe == [] and len(mails(db_welt["mails"])) == 2


def test_grenzen_wie_bisher(db_welt, angebunden):
    t, fehler = melden(db_welt["ida"], art="Fehler", text=FEHLER_TEXT, oeffentlicher_text="x" * 2001)
    assert fehler is True and meldet(t, "konto.betreiber_meldung.zu_lang") and angebunden.aufrufe == []
    for i in range(konten.JE_KONTO_MELDUNGEN[0]):
        assert melden(db_welt["ida"], art="Wunsch", text=f"Beispielwert {i}", oeffentlicher_text=OEFFENTLICH)[1] is False
    t, fehler = melden(db_welt["ida"], art="Wunsch", text="elfte", oeffentlicher_text=OEFFENTLICH)
    assert fehler is True and meldet(t, "konto.betreiber_meldung.grenze")
    assert len(angebunden.aufrufe) == konten.JE_KONTO_MELDUNGEN[0]


def test_ungueltige_art_legt_nichts_an(db_welt, angebunden):
    t, fehler = melden(db_welt["ida"], art="Lob", text=FEHLER_TEXT, oeffentlicher_text=OEFFENTLICH)
    assert fehler is True and angebunden.aufrufe == []


def test_issue_text_ohne_erwaehnungen_und_html(db_welt, angebunden):
    boese = "Beispielwert: @jemand ```\n<img src=x> ![b](https://beispiel.invalid/b.png)"
    melden(db_welt["ida"], art="Fehler", text=FEHLER_TEXT, oeffentlicher_text=boese)
    body = angebunden.aufrufe[0][2]["body"]
    zaun = body.split("text\n", 1)[0]
    assert len(zaun) >= 4 and set(zaun) == {"`"} and body.count(zaun) == 2   # Codeblock länger als jede Folge im Text


def test_titel_wird_gekuerzt(db_welt, angebunden):
    melden(db_welt["ida"], art="Fehler", text=FEHLER_TEXT, oeffentlicher_text="Beispielwert " * 20 + "\nzweite Zeile")
    titel = angebunden.aufrufe[0][2]["title"]
    assert len(titel) <= entwicklung.TITEL_MAX and titel.endswith("…") and "zweite" not in titel


def test_token_nie_aus_der_einstellungsdatei(tmp_path, monkeypatch):
    datei = tmp_path / "einstellungen.env"
    datei.write_text(f"FR_MELDUNGEN_REPO={REPO}\nFR_MELDUNGEN_TOKEN={TOKEN}\n", encoding="utf-8")
    monkeypatch.setattr(entwicklung.instanz, "einstellungen", lambda: {"FR_MELDUNGEN_REPO": REPO, "FR_MELDUNGEN_TOKEN": TOKEN})
    assert entwicklung.repo() == REPO and entwicklung.token() == "" and not entwicklung.eingerichtet()
