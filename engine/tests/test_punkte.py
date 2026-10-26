"""Etappen-Karten: Punkte aus plan/punkte.yaml prüfen und Namen im Etappentext verknüpfen."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import bauen  # noqa: E402

WURZEL = Path(__file__).resolve().parent.parent.parent


def test_verlinken_erste_nennung_ganze_woerter_nicht_in_links():
    punkte = [{"name": "Burgcafé"}, {"name": "Gasthaus an der Brandaussicht"}, {"name": "Brandaussicht"}, {"name": ""}]
    html = ('<p>Von Burgcafé zum <strong>Gasthaus an der Brandaussicht (7)</strong>, wieder Burgcafé. '
            '<a href="https://x">Burgcafé</a> Burgcaféxyz</p>')
    aus = bauen.punkte_verlinken(html, "E-02", punkte)
    assert aus.count('data-p="E-02:0"') == 1                       # nur die erste Nennung
    assert '<a class="kp" href="#E-02" data-p="E-02:1">Gasthaus an der Brandaussicht</a>' in aus  # längster Name gewinnt
    assert 'data-p="E-02:2"' not in aus                            # „Brandaussicht“ steckt im längeren Namen
    assert '<a href="https://x">Burgcafé</a>' in aus and "Burgcaféxyz" in aus


def test_verlinken_nicht_in_tags():
    aus = bauen.punkte_verlinken('<img alt="Burgcafé"> Burgcafé', "E-02", [{"name": "Burgcafé"}])
    assert aus.startswith('<img alt="Burgcafé">') and aus.endswith('data-p="E-02:0">Burgcafé</a>')


@pytest.mark.parametrize("zeile, meldung", [
    ("  E-99:\n  - {name: X, kat: einkehr, lage: [50.95, 14.1], quelle: q}", "Strecke E-99"),
    ("  E-04:\n  - {name: X, kat: kneipe, lage: [50.95, 14.1], quelle: q}", "kat muss"),
    ("  E-04:\n  - {name: X, kat: einkehr, lage: [50.95], quelle: q}", "lage braucht"),
    ("  E-04:\n  - {name: X, kat: einkehr, lage: [50.95, 14.1]}", "quelle fehlt"),
])
def test_punkte_pruefung(tmp_path, zeile, meldung):
    import shutil
    r = tmp_path / "beispielreise"
    shutil.copytree(WURZEL / "beispiel/reisen/beispielreise", r)
    (r / "plan/punkte.yaml").write_text("strecken:\n" + zeile + "\n", encoding="utf-8")
    with pytest.raises(bauen.BauFehler) as e:
        bauen.Bauer(r, tmp_path / "dist").daten()
    assert meldung in str(e.value)
