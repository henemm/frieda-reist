"""Software-Wechsel ohne Handarbeit (#250): neu.py nachziehen stellt Reisen vollständig um, eine neue Reise hat nichts
nachzuziehen, die Eckdaten nennen den Status in Worten. Erfundene Testdaten (Ida, Karl, Mo)."""
import datetime
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import neu  # noqa: E402
import reise  # noqa: E402
import texte  # noqa: E402

VORLAGE_ALT = Path(__file__).resolve().parents[1] / "altformen" / "vorlage-vor-217"
VON, BIS = datetime.date(2027, 2, 6), datetime.date(2027, 2, 13)
PERSONEN = {"ida": {"name": "Ida", "rolle": "organisator"}, "karl": {"name": "Karl", "rolle": "mitwirkend"}}


def anlegen(tmp_path, **kw):
    args = {"titel": "Skiurlaub im Tal", "von": VON, "bis": BIS, "personen": PERSONEN, "wer": "Ida",
            "ziel": "Oberstdorf", "heute": datetime.date(2026, 10, 27), **kw}
    return neu.anlegen(tmp_path / "reisen", **args)


def ausgefuellt(sprache, datei, **werte):
    """Die frühere Vorlage, ausgefüllt wie neu.py sie bis #217 schrieb."""
    text = (VORLAGE_ALT / sprache / datei).read_text(encoding="utf-8")
    for k, v in werte.items():
        text = text.replace("$" + k, v)
    return text


WERTE = {"titel": "Skiurlaub im Tal", "zeitraum_text": "6.–13. Februar 2027", "ziel_text": "Oberstdorf",
         "personen_text": "Ida (organisiert), Karl (bringt ein)", "heute_text": "27.10.2026", "wer": "Ida",
         "herkunft": "Auftrag A-1 aus der Claude-App"}


@pytest.mark.parametrize("sprache", ["de", "en"])
def test_neue_reise_hat_nichts_nachzuziehen(tmp_path, sprache):
    """AC-6: Vorlage und Umstellung laufen nie auseinander."""
    r = anlegen(tmp_path, sprache=sprache)
    assert neu.nachziehen(r) == []


@pytest.mark.parametrize("sprache", ["de", "en"])
def test_ausgefuellte_vorlagen_reste_werden_entfernt(tmp_path, sprache):
    """AC-6: CLAUDE.md und kontext/herkunft.md, die nur die ausgefüllte frühere Vorlage sind, entfernt die Umstellung."""
    r = anlegen(tmp_path, sprache=sprache)
    (r / "CLAUDE.md").write_text(ausgefuellt(sprache, "CLAUDE.md", **WERTE), encoding="utf-8")
    (r / "kontext").mkdir(exist_ok=True)
    (r / "kontext" / "herkunft.md").write_text(ausgefuellt(sprache, "kontext/herkunft.md", **WERTE), encoding="utf-8")

    m = neu.nachziehen(r, schreiben=False)
    assert len(m) == 2 and (r / "CLAUDE.md").exists()                 # Probelauf schreibt nichts
    assert not any(x.startswith(("OFFEN", "OPEN")) for x in m)

    neu.nachziehen(r)
    assert not (r / "CLAUDE.md").exists() and not (r / "kontext").exists()
    assert neu.nachziehen(r) == []


def test_eigene_reste_bleiben_ohne_meldung(tmp_path):
    """AC-6: Eine CLAUDE.md mit eigenem Inhalt ist kein Rest der Vorlage; sie bleibt, und nichts ist offen."""
    r = anlegen(tmp_path)
    eigen = ausgefuellt("de", "CLAUDE.md", **WERTE).replace("Noch nichts festgehalten.", "- Nur Pistenskilauf (Ida).")
    (r / "CLAUDE.md").write_text(eigen, encoding="utf-8")
    (r / "kontext").mkdir(exist_ok=True)
    herkunft = ausgefuellt("de", "kontext/herkunft.md", **WERTE) + "- 28.10.2026: Status Planung (Ida).\n"
    (r / "kontext" / "herkunft.md").write_text(herkunft, encoding="utf-8")
    assert neu.nachziehen(r) == []
    assert (r / "CLAUDE.md").read_text(encoding="utf-8") == eigen
    assert (r / "kontext" / "herkunft.md").read_text(encoding="utf-8") == herkunft


def test_kopfkommentar_mit_woertlichem_zeilenumbruch(tmp_path):
    """AC-6: Rest von #218, der Kopfkommentar der reise.yaml bekommt echte Zeilenumbrüche; der Inhalt bleibt."""
    r = anlegen(tmp_path)
    y = r / "reise.yaml"
    text = y.read_text(encoding="utf-8")
    kopf = text.split("\n\n", 1)[0]
    assert kopf.count("\n") >= 1
    kaputt = kopf.replace("\n", "\\n", 1) + "\n\n" + text.split("\n\n", 1)[1]
    y.write_text(kaputt, encoding="utf-8")

    m = neu.nachziehen(r)
    assert len(m) == 1 and "reise.yaml" in m[0]
    assert y.read_text(encoding="utf-8") == text
    assert yaml.safe_load(text) == yaml.safe_load(kaputt)
    assert neu.nachziehen(r) == []


@pytest.mark.parametrize("sprache,wort", [("de", "Status: Planung"), ("en", "Status: Planning")])
def test_eckdaten_status_in_worten(sprache, wort):
    """AC-7: Der Status steht in Worten, nicht als Datenwert."""
    d = {"sprache": sprache, "zeitraum": {"von": "2027-02-06", "bis": "2027-02-13"}, "ziel": "Oberstdorf",
         "personen": {}, "status": {"wert": "planung"}}
    assert wort in reise.eckdaten_text(d)


def test_jeder_status_hat_ein_wort_in_jeder_sprache():
    for sp in texte.sprachen():
        for wert in reise.STATUS:
            if wert == "idee":
                continue
            assert texte.t(sp, f"inhalt.eckdaten.status.{wert}") != f"inhalt.eckdaten.status.{wert}"


def stand_der_reise(r):
    """Alle Dateien der Reise mit Inhalt, für den Vergleich vor und nach einem Lauf."""
    return {str(p.relative_to(r)): p.read_bytes() for p in sorted(r.rglob("*")) if p.is_file()}


@pytest.mark.parametrize("sprache", ["de", "en"])
def test_zweiter_lauf_aendert_keine_datei(tmp_path, sprache):
    """AC-2, AC-6: Nach der Umstellung (Reste und Kopfkommentar) ändert ein zweiter Lauf keine Datei der Reise."""
    r = anlegen(tmp_path, sprache=sprache)
    (r / "CLAUDE.md").write_text(ausgefuellt(sprache, "CLAUDE.md", **WERTE), encoding="utf-8")
    y = r / "reise.yaml"
    kopf, rest = y.read_text(encoding="utf-8").split("\n\n", 1)
    y.write_text(kopf.replace("\n", "\\n", 1) + "\n\n" + rest, encoding="utf-8")
    assert len(neu.nachziehen(r)) == 2
    vorher = stand_der_reise(r)
    assert neu.nachziehen(r) == []
    assert stand_der_reise(r) == vorher


def test_rest_mit_crlf_und_leerzeilen_am_ende(tmp_path):
    """AC-6: Normalisiert wird CRLF zu LF und Leerzeilen am Ende; die Datei gilt dann als ausgefüllte Kopie."""
    r = anlegen(tmp_path)
    (r / "CLAUDE.md").write_text(ausgefuellt("de", "CLAUDE.md", **WERTE).replace("\n", "\r\n") + "\r\n\r\n",
                                 encoding="utf-8", newline="")
    neu.nachziehen(r)
    assert not (r / "CLAUDE.md").exists()


def test_platzhalter_steht_fuer_beliebigen_text(tmp_path):
    """AC-6: Jeder Platzhalter $wort darf durch beliebigen Text ersetzt sein (hier andere Werte als oben)."""
    r = anlegen(tmp_path)
    andere = {k: f"Irgendwas {i} mit $ und Sonderzeichen (?)" for i, k in enumerate(WERTE)}
    (r / "CLAUDE.md").write_text(ausgefuellt("de", "CLAUDE.md", **andere), encoding="utf-8")
    neu.nachziehen(r)
    assert not (r / "CLAUDE.md").exists()


@pytest.mark.parametrize("inhalt", ["", "\n", "nur eine Zeile\n"])
def test_leere_oder_fremde_datei_ist_kein_rest(tmp_path, inhalt):
    """AC-6: Eine leere Datei passt nie; eine Datei mit anderer Zeilenzahl ist eine eigene."""
    r = anlegen(tmp_path)
    (r / "CLAUDE.md").write_text(inhalt, encoding="utf-8")
    assert neu.nachziehen(r) == []
    assert (r / "CLAUDE.md").read_text(encoding="utf-8") == inhalt


def test_jede_datei_fuer_sich(tmp_path):
    """AC-6: CLAUDE.md ist ein Rest, kontext/herkunft.md hat eine eigene Zeile: nur CLAUDE.md geht, kontext/ bleibt."""
    r = anlegen(tmp_path)
    (r / "CLAUDE.md").write_text(ausgefuellt("de", "CLAUDE.md", **WERTE), encoding="utf-8")
    (r / "kontext").mkdir(exist_ok=True)
    herkunft = ausgefuellt("de", "kontext/herkunft.md", **WERTE) + "- 28.10.2026: Status Planung (Ida).\n"
    (r / "kontext" / "herkunft.md").write_text(herkunft, encoding="utf-8")
    m = neu.nachziehen(r)
    assert len(m) == 1 and "CLAUDE.md" in m[0]
    assert not (r / "CLAUDE.md").exists()
    assert (r / "kontext" / "herkunft.md").read_text(encoding="utf-8") == herkunft


def test_kontext_mit_weiterer_datei_bleibt(tmp_path):
    """AC-6: Entfernt wird kontext/ nur, wenn der Ordner durch das Entfernen leer wird."""
    r = anlegen(tmp_path)
    (r / "kontext").mkdir(exist_ok=True)
    (r / "kontext" / "herkunft.md").write_text(ausgefuellt("de", "kontext/herkunft.md", **WERTE), encoding="utf-8")
    (r / "kontext" / "notizen.md").write_text("Eigenes\n", encoding="utf-8")
    neu.nachziehen(r)
    assert not (r / "kontext" / "herkunft.md").exists() and (r / "kontext" / "notizen.md").exists()


def test_neue_reise_jeder_sprache_hat_nichts_nachzuziehen(tmp_path):
    """AC-6: in jeder Sprache, die die Software kennt, nicht nur de und en."""
    for sp in texte.sprachen():
        r = anlegen(tmp_path / sp, sprache=sp)
        assert neu.nachziehen(r) == [], sp
