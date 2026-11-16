"""Tagestext mit Markdown und Vorlage „Aktivität“ (#593, Product Owner 16.11.2026, Entwurf freigegeben): Der Text eines Tags
ist ein Langtext (#594): Absätze und Listen, keine Zwischenüberschriften (Product Owner 16.11.2026, fett reicht); Frieda bietet eine Vorlage
für Aufenthalte ohne Nacht wie Kurs, Führung oder Termin an. Gegen beide Beispielreisen."""
import shutil
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import bauen  # noqa: E402
import schreiben as sb  # noqa: E402

WURZEL = Path(__file__).resolve().parent.parent.parent
ORGA = {"beispielreise": {"name": "Ida", "rolle": "organisator"}, "stadtwochenende": {"name": "Tom", "rolle": "organisator"}}
MD = ("Ein ruhiger Tag.\n\n**Vormittag:** Kurs, danach Mittag auf dem Markt.\n\n**Nachmittag:**\n\n"
      "- Kaffee\n- Spaziergang am Fluss\n- **Abends:** gemeinsam kochen\n\n1. erstens\n2. zweitens")


def kopie(tmp_path, reise):
    q = tmp_path / reise
    shutil.copytree(WURZEL / "beispiel/reisen" / reise, q)
    return q


def tage(reise_dir):
    return yaml.safe_load((reise_dir / "plan" / "routen.yaml").read_text(encoding="utf-8"))["tage"]


@pytest.mark.parametrize("reise", ["beispielreise", "stadtwochenende"])
def test_tagestext_behaelt_absaetze_und_listen(tmp_path, reise):
    q = kopie(tmp_path, reise)
    sb.tag_aendern(q, ORGA[reise], {"ziel": "T-01", "text": MD + "\n\n\n\nEnde.  "})
    assert tage(q)["T-01"]["text"] == MD + "\n\nEnde."
    sb.tag_anlegen(q, ORGA[reise], {"titel": "Zusatztag", "text": MD})
    assert any(t.get("titel") == "Zusatztag" and t.get("text") == MD for t in tage(q).values())


@pytest.mark.parametrize("reise", ["beispielreise", "stadtwochenende"])
def test_tagestext_bleibt_sauber_geprueft(tmp_path, reise):
    """Mehrzeilig, aber wie jeder sichtbare Text ohne Kennungen (#476) und höchstens 4000 Zeichen."""
    q = kopie(tmp_path, reise)
    with pytest.raises(sb.Ablehnung):
        sb.tag_aendern(q, ORGA[reise], {"ziel": "T-01", "text": "Erst klären:\n\n- siehe F-01"})
    with pytest.raises(sb.Ablehnung):
        sb.tag_aendern(q, ORGA[reise], {"ziel": "T-01", "text": "x" * 4001})


@pytest.mark.parametrize("reise", ["beispielreise", "stadtwochenende"])
def test_tagestext_ohne_zwischenueberschriften(tmp_path, reise):
    """Product Owner 16.11.2026 (#594): im Tagestext keine Überschriften; der Schreibweg sagt, was stattdessen geht."""
    q = kopie(tmp_path, reise)
    with pytest.raises(sb.Ablehnung, match="fett"):
        sb.tag_aendern(q, ORGA[reise], {"ziel": "T-01", "text": "### Vormittag\n\nKurs"})


@pytest.mark.parametrize("reise", ["beispielreise", "stadtwochenende"])
def test_tagestext_bleibt_markdown_fuer_die_seite(tmp_path, reise):
    """Die Seite zeigt den Text mit dem Atom langtext; die Daten tragen ihn unverändert (test_textform.py prüft die Seite)."""
    q = kopie(tmp_path, reise)
    sb.tag_aendern(q, ORGA[reise], {"ziel": "T-01", "text": MD})
    d = bauen.bauen(q, tmp_path / "web" / reise)
    t = next(t for t in d["route"]["tage"] if t["id"] == "T-01")
    assert t["text"] == MD and "text_html" not in t


def test_vorlage_aktivitaet_in_jeder_sprache():
    for sp, name in (("de", "Aktivität"), ("en", "Activity")):
        a = yaml.safe_load((WURZEL / "engine" / "artvorlagen" / f"{sp}.yaml").read_text(encoding="utf-8"))["arten"]["aktivitaet"]
        assert a["grundform"] == "aufenthalt" and a["name"] == name
        assert set(a["merkmale"]) == {"anbieter", "treffpunkt", "preis", "anmeldung", "mitbringen", "webseite"}
        assert a["merkmale"]["preis"]["rolle"] == "kosten"


@pytest.mark.parametrize("reise", ["beispielreise", "stadtwochenende"])
def test_aktivitaet_uebernehmen_und_mit_uhrzeit_und_lesetext_zeigen(tmp_path, reise):
    """Übernommen ist die Vorlage eine Art der Reise; ein Aufenthalt dieser Art hat Uhrzeit und Lesetext wie jeder andere."""
    q = kopie(tmp_path, reise)
    wer = ORGA[reise]
    sb.arten_uebernehmen(q, wer, {"vorlage": True, "arten": ["aktivitaet"]})
    arten = yaml.safe_load((q / "plan" / "arten.yaml").read_text(encoding="utf-8"))["arten"]
    assert arten["aktivitaet"]["grundform"] == "aufenthalt"
    vorher = set(yaml.safe_load((q / "plan" / "routen.yaml").read_text(encoding="utf-8")).get("aufenthalte") or {})
    sb.ding_anlegen(q, wer, {"was": "aufenthalt", "titel": "Töpferkurs", "art": "aktivitaet", "ort": "O-01", "quelle": "erfunden (Test)",
                             "merkmale": {"zeitraum": {"beginn": "10:00", "ende": "12:30"}, "mitbringen": "Schürze"}})
    aid = (set(yaml.safe_load((q / "plan" / "routen.yaml").read_text(encoding="utf-8"))["aufenthalte"]) - vorher).pop()
    sb.lesetext_schreiben(q, wer, {"ziel": aid, "quelle": "erfunden (Test)", "text": "Zwei Stunden.\n\n1. Ton\n2. Drehen"})
    sb.tag_aendern(q, wer, {"ziel": "T-01", "aufenthalte": [aid]})
    d = bauen.bauen(q, tmp_path / "web" / reise)
    a = d["route"]["aufenthalte"][aid]
    assert a["art"] == "aktivitaet" and a["beginn"] == "10:00" and a["ende"] == "12:30"
    assert "<ol>" in a["lesetext"]
