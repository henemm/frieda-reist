"""Übergang der Rollennamen (Issue #80, 28.10.2026): reisend, einbringer, bestimmer (und mitreisend) gelten weiter als
gast, mitwirkend, organisator. Gelesen werden die alten Schlüssel überall, geschrieben nur noch die neuen."""
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import konten  # noqa: E402
import reise as rg  # noqa: E402
import rueckmeldungen as rm  # noqa: E402


def test_rolle_neu():
    assert [rg.rolle_neu(r) for r in ("reisend", "einbringer", "bestimmer", "mitreisend")] == \
        ["gast", "mitwirkend", "organisator", "mitwirkend"]
    assert [rg.rolle_neu(r) for r in rg.ROLLEN] == list(rg.ROLLEN)
    assert rg.rolle_neu("chef") == "chef" and rg.rolle_neu(None) is None


def test_rechte_mit_alten_namen():
    assert rg.darf("bestimmer", "organisator") and rg.darf("organisator", "einbringer")
    assert not rg.darf("reisend", "mitwirkend") and not rg.darf("einbringer", "bestimmer")
    assert rg.mindestrolle("einladen", {"einladen": "einbringer"}) == "mitwirkend"
    assert rg.erlaubt("einladen", "einbringer", "planung", None, regeln={"einladen": "einbringer"})[0]
    assert rg.erlaubt("entscheiden", "bestimmer", "planung", None)[0]


def test_reise_yaml_mit_alten_namen():
    """Eine reise.yaml mit den alten Schlüsseln baut weiter und liefert die neuen."""
    d = {"titel": "Test", "status": {"wert": "planung", "verlauf": [{"wert": "planung", "datum": "2026-10-26",
                                                                       "wer": "Ida"}]},
         "personen": {"ida": {"name": "Ida", "rolle": "bestimmer"}, "karl": {"name": "Karl", "rolle": "einbringer"},
                      "kim": {"name": "Kim", "rolle": "reisend"}},
         "regeln": {"einladen": "einbringer"}}
    fehler = []
    r = rg.Reise(d, {}, fehler, [])
    assert [p["rolle"] for p in r.personen()] == ["organisator", "mitwirkend", "gast"]
    assert r.organisator_namen() == {"Ida"} and r.regeln()["einladen"] == "mitwirkend"
    assert fehler == []


def test_eingeladene_mit_alter_rolle(tmp_path, monkeypatch):
    monkeypatch.setenv("RM_ABLAGE", str(tmp_path))
    o = tmp_path / "beispielreise"
    o.mkdir()
    (o / "einladungen.json").write_text(json.dumps({"mo": {"name": "Mo", "rolle": "einbringer"}}), encoding="utf-8")
    p = rm.personen_mit_einladungen([{"schluessel": "ida", "name": "Ida", "rolle": "bestimmer"}], o)
    assert [(x["name"], x["rolle"]) for x in p] == [("Ida", "organisator"), ("Mo", "mitwirkend")]


def test_konto_einladung_mit_alter_rolle(tmp_path, monkeypatch):
    monkeypatch.setenv("RM_ABLAGE", str(tmp_path / "ablage"))
    monkeypatch.setenv("FR_MAIL_DATEI", str(tmp_path / "mails.jsonl"))
    monkeypatch.setenv("FR_BASIS", "https://frieda.beispiel.invalid")
    konten.einladen("sommer", "karl", "karl@beispiel.invalid", "einbringer", "Karl", "Ida")   # alt rein, neu gespeichert
    text = json.loads((tmp_path / "mails.jsonl").read_text().splitlines()[-1])["text"]
    token = text.split("/einladung/")[1].split()[0]
    assert konten.einladung(token)["rolle"] == "mitwirkend"
    with sqlite3.connect(konten.pfad()) as v:              # Zeile von vor der Umstellung
        v.execute("UPDATE einladungen SET rolle = 'bestimmer'")
    assert konten.einladung(token)["rolle"] == "organisator"
