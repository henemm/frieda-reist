"""Kein Startpfad der Vorlage erreicht eine spaeter angelegte const/let/class (frieda-reist#387).

Der Fehler von #387: Eine Startanweisung (Heimat, „Ohne Tag“) rief über heimat → vorgabeEltern → ortSeiteZu → unterorte eine
const auf, die erst 700 Zeilen weiter unten stand. Die Seite brach beim Laden ab und blieb leer. Der Browsertest
(test_seite_startet.py) findet das nur, wenn die Beispielreise den Fall enthält; dieser Test findet es an der Vorlage selbst,
ohne Daten. Kein JavaScript-Parser (engine/tests/start_reihenfolge.py): bei einem Fehlalarm die Definition vor die Startanweisung
ziehen oder als function schreiben, das ist auch die Lösung."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import start_reihenfolge as sr  # noqa: E402

VORLAGE = Path(__file__).resolve().parent.parent / "vorlage.html"


def test_vorlage_startanweisungen_erreichen_keine_spaeter_angelegte_const():
    js, _ = sr.skript_der_vorlage(VORLAGE.read_text(encoding="utf-8"))
    assert sr.finde(js) == []


def test_pruefung_findet_den_fehler_von_387():
    """Die Prüfung selbst: der Aufbau von #387 in klein (Startanweisung → Funktion → Funktion → spaeter angelegte const)."""
    js = """
const R = {};
const OHNE = R ? [1].filter(id => !heimat(id)) : [];
function heimat(id) { return seite(id); }
function seite(id) { return unter(id).length; }
const unter = oid => [oid];
"""
    funde = sr.finde(js)
    assert len(funde) == 1 and funde[0].startswith("unter (Zeile 6)") and "heimat" in funde[0], funde


def test_pruefung_laesst_function_rueckrufe_und_async_in_ruhe():
    js = """
function heimat(id) { return unter(id); }
function unter(oid) { return [oid]; }
const OHNE = [1].filter(id => !heimat(id));
document.addEventListener("click", () => spaeter());
window.onload = () => spaeter();
async function laden() { await fetch("x"); spaeter(); }
laden();
const text = `a ${spaeter} b`;
const spaeter = () => 1;
"""
    # „spaeter“ im Template-Text steht in ${…} und läuft sofort: das ist ein Fund; die Rückrufe und der Teil nach await nicht
    funde = sr.finde(js)
    assert len(funde) == 1 and "spaeter (Zeile 10)" in funde[0] and "direkt" in funde[0], funde
